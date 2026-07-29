"""Anki add-on that exposes a small offline-review API for the Xteink X4."""

from __future__ import annotations

import hmac
import html
import json
import logging
import re
import secrets
import socket
import threading
import time
import uuid
from concurrent.futures import Future, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

import anki.lang
from anki.cards import Card
from anki.collection import OpChanges
from anki.consts import (
    CARD_TYPE_LRN,
    CARD_TYPE_NEW,
    CARD_TYPE_RELEARNING,
    CARD_TYPE_REV,
)
from anki.scheduler.v3 import CardAnswer
from anki.utils import strip_html
from aqt import gui_hooks, mw
from aqt.operations import CollectionOp, QueryOp
from aqt.qt import QAction, QTimer, qconnect
from aqt.utils import showInfo

from .protocol import ProtocolError, PushBatch, Review, parse_push_payload


ADDON_VERSION = "2.0.0"
PROTOCOL_VERSION = 2
LOGGER = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "bind_address": "0.0.0.0",
    "port": 5050,
    "api_token": "",
    "max_cards": 100,
    "max_text_chars": 4096,
    "max_reviews_per_push": 500,
    "max_request_bytes": 262144,
    "operation_timeout_seconds": 60,
    "sync_after_push": True,
    "allow_legacy_csv": True,
    "cors_allowed_origin": "*",
    "processed_batch_ids": [],
}

TRANSLATIONS = {
    "en": {
        "menu_action": "Xteink Status",
        "status_title": "Xteink API",
        "status_running": (
            "The Xteink API is running.\n\n"
            "Address: {address}\n"
            "Port: {port}\n"
            "API token: {token}\n"
            "Collection ready: {ready}"
        ),
        "status_stopped": "The Xteink API could not be started:\n{error}",
        "yes": "yes",
        "no": "no",
    },
    "de": {
        "menu_action": "Xteink Status",
        "status_title": "Xteink API",
        "status_running": (
            "Die Xteink API läuft.\n\n"
            "Adresse: {address}\n"
            "Port: {port}\n"
            "API-Token: {token}\n"
            "Sammlung bereit: {ready}"
        ),
        "status_stopped": "Die Xteink API konnte nicht gestartet werden:\n{error}",
        "yes": "ja",
        "no": "nein",
    },
    "el": {
        "menu_action": "Κατάσταση Xteink",
        "status_title": "Xteink API",
        "status_running": (
            "Το Xteink API εκτελείται.\n\n"
            "Διεύθυνση: {address}\n"
            "Θύρα: {port}\n"
            "API token: {token}\n"
            "Συλλογή έτοιμη: {ready}"
        ),
        "status_stopped": "Δεν ήταν δυνατή η εκκίνηση του Xteink API:\n{error}",
        "yes": "ναι",
        "no": "όχι",
    },
}

_ANSWER_SEPARATOR_RE = re.compile(
    r"<hr\b[^>]*\bid\s*=\s*([\"']?)answer\1[^>]*>",
    flags=re.IGNORECASE,
)
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
_STRUCTURAL_TAG_RE = re.compile(
    r"</?(?:br|div|p|li|tr|h[1-6])\b[^>]*>",
    flags=re.IGNORECASE,
)
_CARD_TYPE_NAMES = {
    int(CARD_TYPE_NEW): "new",
    int(CARD_TYPE_LRN): "learning",
    int(CARD_TYPE_REV): "review",
    int(CARD_TYPE_RELEARNING): "relearning",
}


class CollectionUnavailable(RuntimeError):
    pass


class OperationTimedOut(RuntimeError):
    pass


@dataclass
class ApplyResult:
    changes: OpChanges
    processed: int
    rejected: List[Dict[str, Any]]
    sync_requested: bool = False
    sync_reason: str = ""

    def response_payload(self, batch: PushBatch) -> Dict[str, Any]:
        return {
            "status": "success" if not self.rejected else "partial",
            "protocol_version": PROTOCOL_VERSION,
            "batch_id": batch.batch_id,
            "batch_id_derived": batch.derived_batch_id,
            "legacy_csv": batch.legacy_csv,
            "processed": self.processed,
            "rejected": self.rejected,
            "sync_requested": self.sync_requested,
            "sync_reason": self.sync_reason,
        }


def _t(key: str, **kwargs: Any) -> str:
    language = getattr(anki.lang, "current_lang", "en")
    base_language = str(language).replace("_", "-").split("-", 1)[0]
    strings = TRANSLATIONS.get(base_language, TRANSLATIONS["en"])
    text = strings.get(key, TRANSLATIONS["en"].get(key, f"[{key}]"))
    return text.format(**kwargs) if kwargs else text


def _int_config(config: Dict[str, Any], key: str) -> int:
    fallback = int(DEFAULT_CONFIG[key])
    try:
        return int(config.get(key, fallback))
    except (TypeError, ValueError):
        LOGGER.warning("Invalid %s in Xteink config; using %s", key, fallback)
        return fallback


def _plain_text(card_html: str, limit: int) -> str:
    without_code = _SCRIPT_STYLE_RE.sub("", card_html)
    with_breaks = _STRUCTURAL_TAG_RE.sub("\n", without_code)
    text = html.unescape(strip_html(with_breaks)).replace("\r\n", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]

    compact_lines = []
    for line in lines:
        if line:
            compact_lines.append(line)
        elif compact_lines and compact_lines[-1]:
            compact_lines.append("")

    result = "\n".join(compact_lines).strip()
    if len(result) > limit:
        return result[: max(0, limit - 1)].rstrip() + "…"
    return result


def _answer_only(answer_html: str) -> str:
    split = _ANSWER_SEPARATOR_RE.split(answer_html, maxsplit=1)
    # The capturing quote group is included by re.split().
    return split[-1] if len(split) >= 3 else answer_html


def _local_ipv4_addresses() -> List[str]:
    addresses = set()
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = item[4][0]
            if address and not address.startswith("127."):
                addresses.add(address)
    except OSError:
        pass
    return sorted(addresses)


class XteinkHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address: Tuple[str, int], addon: "XteinkAddon") -> None:
        self.addon = addon
        super().__init__(server_address, XteinkAPIHandler)


class XteinkAPIHandler(BaseHTTPRequestHandler):
    server_version = f"XteinkSync/{ADDON_VERSION}"
    protocol_version = "HTTP/1.1"

    @property
    def addon(self) -> "XteinkAddon":
        return self.server.addon  # type: ignore[attr-defined]

    def version_string(self) -> str:
        return self.server_version

    def log_message(self, format_string: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.client_address[0], format_string % args)

    def _path(self) -> str:
        path = urlsplit(self.path).path.rstrip("/")
        return path or "/"

    def _cors_headers(self) -> Dict[str, str]:
        configured = str(self.addon.config.get("cors_allowed_origin", "")).strip()
        request_origin = self.headers.get("Origin", "")
        if not configured:
            return {}
        if configured == "*":
            return {"Access-Control-Allow-Origin": "*"}
        if request_origin == configured:
            return {
                "Access-Control-Allow-Origin": configured,
                "Vary": "Origin",
            }
        return {}

    def _send_json(
        self,
        status: int,
        payload: Dict[str, Any],
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        for name, value in self._cors_headers().items():
            self.send_header(name, value)
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.close_connection = True
        try:
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionResetError):
            LOGGER.info("Client disconnected before receiving the response")

    def _error(self, status: int, code: str, message: str) -> None:
        self._send_json(
            status,
            {
                "status": "error",
                "error": code,
                "message": message,
                "protocol_version": PROTOCOL_VERSION,
            },
        )

    def _authenticated(self) -> bool:
        expected = self.addon.api_token
        authorization = self.headers.get("Authorization", "")
        if authorization.lower().startswith("bearer "):
            supplied = authorization[7:].strip()
        else:
            supplied = self.headers.get("X-Xteink-Token", "").strip()
        return bool(supplied) and hmac.compare_digest(supplied, expected)

    def _require_authentication(self) -> bool:
        if self._authenticated():
            return True
        self._error(401, "unauthorized", "A valid Xteink API token is required")
        return False

    def _handle_operation_error(self, error: Exception) -> None:
        if isinstance(error, CollectionUnavailable):
            self._error(503, "collection_unavailable", str(error))
        elif isinstance(error, OperationTimedOut):
            self._error(504, "operation_timeout", str(error))
        else:
            LOGGER.exception("Unhandled Xteink API error", exc_info=error)
            self._error(500, "internal_error", "The Anki operation failed")

    def do_OPTIONS(self) -> None:
        if self._path() not in {"/pull", "/push", "/health"}:
            self._error(404, "not_found", "Unknown endpoint")
            return
        self._send_json(
            200,
            {"status": "ok", "protocol_version": PROTOCOL_VERSION},
            {
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": (
                    "Authorization, Content-Type, X-Xteink-Token, "
                    "X-Xteink-Batch-ID"
                ),
                "Access-Control-Max-Age": "600",
            },
        )

    def do_GET(self) -> None:
        path = self._path()
        if path == "/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "protocol_version": PROTOCOL_VERSION,
                    "addon_version": ADDON_VERSION,
                    "collection_ready": self.addon.collection_ready(),
                    "server_time": int(time.time()),
                },
            )
            return

        if path != "/pull":
            self._error(404, "not_found", "Unknown endpoint")
            return
        if not self._require_authentication():
            return

        try:
            self._send_json(200, self.addon.pull_cards())
        except Exception as error:
            self._handle_operation_error(error)

    def do_POST(self) -> None:
        if self._path() != "/push":
            self._error(404, "not_found", "Unknown endpoint")
            return
        if not self._require_authentication():
            return
        if self.headers.get("Transfer-Encoding"):
            self._error(400, "unsupported_transfer_encoding", "Use Content-Length")
            return

        content_length_value = self.headers.get("Content-Length")
        if content_length_value is None:
            self._error(411, "length_required", "Content-Length is required")
            return
        try:
            content_length = int(content_length_value)
        except ValueError:
            self._error(400, "invalid_content_length", "Invalid Content-Length")
            return

        max_bytes = _int_config(self.addon.config, "max_request_bytes")
        if content_length < 1:
            self._error(400, "empty_body", "Request body must not be empty")
            return
        if content_length > max_bytes:
            self._error(
                413,
                "payload_too_large",
                f"Request body exceeds {max_bytes} bytes",
            )
            return

        body = self.rfile.read(content_length)
        if len(body) != content_length:
            self._error(400, "incomplete_body", "Request body ended unexpectedly")
            return

        try:
            batch = parse_push_payload(
                body=body,
                content_type=self.headers.get("Content-Type", "text/csv"),
                header_batch_id=self.headers.get("X-Xteink-Batch-ID"),
                max_reviews=_int_config(
                    self.addon.config, "max_reviews_per_push"
                ),
                allow_legacy_csv=bool(
                    self.addon.config.get("allow_legacy_csv", True)
                ),
            )
        except ProtocolError as error:
            self._error(error.status, error.code, error.message)
            return

        claim = self.addon.claim_batch(batch.batch_id)
        if claim == "duplicate":
            self._send_json(
                200,
                {
                    "status": "duplicate",
                    "protocol_version": PROTOCOL_VERSION,
                    "batch_id": batch.batch_id,
                    "processed": 0,
                    "rejected": [],
                    "sync_requested": False,
                },
            )
            return
        if claim == "pending":
            self._error(409, "batch_pending", "This batch is already being processed")
            return

        try:
            result = self.addon.apply_reviews(batch)
            self._send_json(200, result.response_payload(batch))
        except Exception as error:
            self._handle_operation_error(error)


class XteinkAddon:
    def __init__(self) -> None:
        loaded = mw.addonManager.getConfig(__name__) or {}
        self.config = dict(DEFAULT_CONFIG)
        self.config.update(loaded)

        token = str(self.config.get("api_token", "")).strip()
        if not token:
            token = secrets.token_urlsafe(32)
            self.config["api_token"] = token
            mw.addonManager.writeConfig(__name__, self.config)
        elif len(token) < 16:
            LOGGER.warning("The configured Xteink API token is shorter than 16 characters")
        self.api_token = token

        processed = self.config.get("processed_batch_ids", [])
        self._processed_batch_ids = [
            item for item in processed if isinstance(item, str)
        ][-100:]
        self._pending_batch_ids = set()  # type: set[str]
        self._batch_lock = threading.Lock()

        self.httpd = None  # type: Optional[XteinkHTTPServer]
        self.server_thread = None  # type: Optional[threading.Thread]
        self.start_error = ""

    def collection_ready(self) -> bool:
        return getattr(mw, "col", None) is not None

    def start_server(self) -> None:
        if self.httpd or self.server_thread:
            return

        address = str(self.config.get("bind_address", "0.0.0.0")).strip()
        port = _int_config(self.config, "port")

        def run() -> None:
            try:
                self.httpd = XteinkHTTPServer((address, port), self)
                LOGGER.info("Xteink API listening on %s:%s", address, port)
                self.httpd.serve_forever(poll_interval=0.25)
            except Exception as error:
                self.start_error = str(error)
                LOGGER.exception("Could not start the Xteink API")
            finally:
                if self.httpd:
                    self.httpd.server_close()
                self.httpd = None

        self.server_thread = threading.Thread(
            target=run,
            name="xteink-http-server",
            daemon=True,
        )
        self.server_thread.start()

    def _wait_for_future(self, future: Future) -> Any:
        timeout = _int_config(self.config, "operation_timeout_seconds")
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            raise OperationTimedOut(
                f"Anki did not finish the operation within {timeout} seconds"
            )

    def pull_cards(self) -> Dict[str, Any]:
        result = Future()

        def start_query() -> None:
            if not self.collection_ready():
                result.set_exception(
                    CollectionUnavailable("No Anki collection is currently open")
                )
                return

            operation = QueryOp(
                parent=mw,
                op=self._collect_due_cards,
                success=result.set_result,
            )
            operation.failure(result.set_exception).run_in_background()

        mw.taskman.run_on_main(start_query)
        cards = self._wait_for_future(result)
        return {
            "status": "success",
            "protocol_version": PROTOCOL_VERSION,
            "pull_id": uuid.uuid4().hex,
            "server_time": int(time.time()),
            "cards": cards,
        }

    def _collect_due_cards(self, collection: Any) -> List[Dict[str, Any]]:
        max_cards = max(1, min(_int_config(self.config, "max_cards"), 1000))
        text_limit = max(128, _int_config(self.config, "max_text_chars"))
        queued_cards = collection.sched.get_queued_cards(fetch_limit=max_cards).cards

        payload = []
        for queued_card in queued_cards:
            card = Card(collection, backend_card=queued_card.card)
            card_type = int(card.type)
            answer_html = _answer_only(card.answer())
            payload.append(
                {
                    "id": str(int(card.id)),
                    "front": _plain_text(card.question(), text_limit),
                    "back": _plain_text(answer_html, text_limit),
                    "card_type": _CARD_TYPE_NAMES.get(card_type, "unknown"),
                    # Kept for compatibility with the original X4 client.
                    "is_learning": card_type
                    in {
                        int(CARD_TYPE_NEW),
                        int(CARD_TYPE_LRN),
                        int(CARD_TYPE_RELEARNING),
                    },
                    "queue": int(card.queue),
                    "reps": int(card.reps),
                    "mod": int(card.mod),
                }
            )
        return payload

    def claim_batch(self, batch_id: str) -> str:
        with self._batch_lock:
            if batch_id in self._processed_batch_ids:
                return "duplicate"
            if batch_id in self._pending_batch_ids:
                return "pending"
            self._pending_batch_ids.add(batch_id)
            return "claimed"

    def release_batch(self, batch_id: str) -> None:
        with self._batch_lock:
            self._pending_batch_ids.discard(batch_id)

    def _complete_batch(self, batch_id: str) -> None:
        with self._batch_lock:
            self._pending_batch_ids.discard(batch_id)
            self._processed_batch_ids = [
                item for item in self._processed_batch_ids if item != batch_id
            ]
            self._processed_batch_ids.append(batch_id)
            self._processed_batch_ids = self._processed_batch_ids[-100:]

        self.config["processed_batch_ids"] = list(self._processed_batch_ids)
        try:
            mw.addonManager.writeConfig(__name__, self.config)
        except Exception:
            LOGGER.exception("Could not persist processed Xteink batch IDs")

    def apply_reviews(self, batch: PushBatch) -> ApplyResult:
        result = Future()

        def fail(error: Exception) -> None:
            self.release_batch(batch.batch_id)
            result.set_exception(error)

        def succeeded(apply_result: ApplyResult) -> None:
            self._complete_batch(batch.batch_id)
            (
                apply_result.sync_requested,
                apply_result.sync_reason,
            ) = self._request_ankiweb_sync(apply_result.processed)
            result.set_result(apply_result)

        def start_operation() -> None:
            if not self.collection_ready():
                fail(CollectionUnavailable("No Anki collection is currently open"))
                return

            operation = CollectionOp(
                parent=mw,
                op=lambda collection: self._apply_batch(collection, batch),
            )
            operation.success(succeeded).failure(fail).run_in_background(
                initiator=self
            )

        mw.taskman.run_on_main(start_operation)
        return self._wait_for_future(result)

    def _apply_batch(self, collection: Any, batch: PushBatch) -> ApplyResult:
        aggregate_changes = OpChanges()
        rejected = []
        processed = 0

        for index, review in enumerate(batch.reviews):
            try:
                changes = self._answer_card(collection, review)
                aggregate_changes.MergeFrom(changes)
                processed += 1
            except Exception as error:
                LOGGER.exception(
                    "Could not grade Xteink card %s", review.card_id
                )
                rejected.append(
                    {
                        "index": index,
                        "card_id": str(review.card_id),
                        "error": str(error),
                    }
                )

        return ApplyResult(
            changes=aggregate_changes,
            processed=processed,
            rejected=rejected,
        )

    def _answer_card(self, collection: Any, review: Review) -> OpChanges:
        card = collection.get_card(review.card_id)
        card.start_timer()
        if review.duration_ms:
            card.timer_started = time.time() - (review.duration_ms / 1000)

        scheduler = collection.sched
        if all(
            hasattr(scheduler, attribute)
            for attribute in ("build_answer", "answer_card")
        ):
            rating = {
                1: CardAnswer.AGAIN,
                2: CardAnswer.HARD,
                3: CardAnswer.GOOD,
                4: CardAnswer.EASY,
            }[review.ease]
            try:
                states = collection._backend.get_scheduling_states(card.id)
                answer = scheduler.build_answer(
                    card=card,
                    states=states,
                    rating=rating,
                )
                if review.answered_at_ms is not None:
                    answer.answered_at_millis = review.answered_at_ms
                answer.milliseconds_taken = review.duration_ms
            except Exception:
                LOGGER.warning(
                    "Falling back to Anki's legacy answerCard() API",
                    exc_info=True,
                )
            else:
                return scheduler.answer_card(answer)

        return scheduler.answerCard(card, review.ease)

    def _request_ankiweb_sync(self, processed: int) -> Tuple[bool, str]:
        if not processed:
            return False, "no_changes"
        if not bool(self.config.get("sync_after_push", True)):
            return False, "disabled"
        if not mw.pm.sync_auth():
            return False, "not_logged_in"
        if mw.media_syncer.is_syncing():
            return False, "already_syncing"

        QTimer.singleShot(0, mw.on_sync_button_clicked)
        return True, "scheduled"

    def show_status(self) -> None:
        if self.start_error:
            message = _t("status_stopped", error=self.start_error)
        else:
            configured_address = str(
                self.config.get("bind_address", "0.0.0.0")
            ).strip()
            addresses = _local_ipv4_addresses()
            display_address = (
                ", ".join(addresses)
                if configured_address == "0.0.0.0" and addresses
                else configured_address
            )
            message = _t(
                "status_running",
                address=display_address,
                port=_int_config(self.config, "port"),
                token=self.api_token,
                ready=_t("yes") if self.collection_ready() else _t("no"),
            )
        showInfo(message, title=_t("status_title"))


addon = XteinkAddon()

action = QAction(_t("menu_action"), mw)
qconnect(action.triggered, addon.show_status)
mw.form.menuTools.addAction(action)

gui_hooks.main_window_did_init.append(addon.start_server)
