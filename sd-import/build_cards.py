#!/usr/bin/env python3
"""Convert a simple CSV of flashcards into an NDJSON file for the SD card's
system-due/ folder, which the "Load today's cards from SD" device menu
action reads (the newest *.ndjson file there -- see AnkiStore::
findNewestSdDueFile() in the firmware).

CSV columns: front,back[,deck]
- front, back: card text. Supports embedded commas/newlines via normal CSV
  quoting (wrap the field in double quotes).
- deck: optional; defaults to DEFAULT_DECK_NAME below. Rows sharing a deck
  name are grouped into one deck on the device.

Card ids are derived deterministically from (deck, front, back) so
regenerating from the same CSV keeps the same ids across runs -- re-importing
an unchanged CSV does not create duplicate-looking cards. They are offset well
above the range of real Anki card ids (epoch-millisecond timestamps, currently
~13 digits) so they can never collide with an id from an actual Anki sync.

These cards are NOT known to your Anki collection. Grading them on the device
still works locally (progress, bury, undo, flag), but "Upload reviews" cannot
sync that grading anywhere -- Anki's collection has no note to update for an
id it never created, so the add-on rejects those reviews individually rather
than erroring the whole batch. Use this for offline-only / throwaway study
content, not for cards you need graded in Anki itself.
"""

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Mirrors AnkiStore::MAX_CARD_LINE_BYTES / MAX_CARDS (src/anki/AnkiStore.h) --
# the firmware rejects a batch that exceeds either, so fail early here with a
# clear message instead of producing a file the device will bounce.
MAX_CARD_LINE_BYTES = 16384
MAX_CARDS = 1000

DEFAULT_DECK_NAME = "SD Import"
PROTOCOL_VERSION = 3

# Keeps synthetic ids far above real Anki card ids (epoch-ms timestamps,
# currently ~1.8e12) while staying a valid unsigned 64-bit value (max ~1.8e19).
SYNTHETIC_ID_OFFSET = 9_000_000_000_000_000_000
SYNTHETIC_ID_MODULUS = 900_000_000_000_000_000


def deck_key(name: str) -> str:
    # Any stable, non-empty string works -- the device only uses it to group
    # cards and as a fallback display name if "deck_name" were ever absent.
    return "sd:" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]


def card_id(deck: str, front: str, back: str) -> str:
    digest = hashlib.sha256(f"{deck}\x1f{front}\x1f{back}".encode("utf-8")).digest()
    value = SYNTHETIC_ID_OFFSET + (int.from_bytes(digest[:8], "big") % SYNTHETIC_ID_MODULUS)
    return str(value)


def read_rows(csv_path: Path):
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if rows and [c.strip().lower() for c in rows[0][:2]] == ["front", "back"]:
        rows = rows[1:]  # optional header row
    cards = []
    for line_number, row in enumerate(rows, start=1):
        if not row or all(not cell.strip() for cell in row):
            continue  # blank line
        if len(row) < 2:
            raise ValueError(f"{csv_path}:{line_number}: expected at least front,back columns")
        front, back = row[0], row[1]
        deck = row[2].strip() if len(row) > 2 and row[2].strip() else DEFAULT_DECK_NAME
        cards.append((deck, front, back))
    return cards


def build_ndjson(cards) -> bytes:
    if len(cards) > MAX_CARDS:
        raise ValueError(f"{len(cards)} cards exceeds the device limit of {MAX_CARDS}")

    decks_seen = {}  # deck name -> deck id, in first-seen order
    card_lines = []
    for deck_name, front, back in cards:
        did = decks_seen.setdefault(deck_name, deck_key(deck_name))
        record = {
            "type": "card",
            "id": card_id(did, front, back),
            "deck_id": did,
            "deck_name": deck_name,
            "front": front,
            "back": back,
        }
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        encoded_len = len(line.encode("utf-8")) + 1  # +1 for the newline readLine() consumes
        if encoded_len > MAX_CARD_LINE_BYTES:
            raise ValueError(
                f"Card \"{front[:40]}...\" is {encoded_len} bytes as JSON, "
                f"over the device's {MAX_CARD_LINE_BYTES}-byte line limit"
            )
        card_lines.append(line)

    meta = {
        "type": "meta",
        "status": "success",
        "protocol_version": PROTOCOL_VERSION,
        "pull_id": "sd-import-" + hashlib.sha256("\n".join(card_lines).encode("utf-8")).hexdigest()[:16],
        "card_count": len(cards),
        "decks": [{"id": did, "name": name} for name, did in decks_seen.items()],
    }
    lines = [json.dumps(meta, ensure_ascii=False, separators=(",", ":"))]
    lines.extend(card_lines)
    lines.append(json.dumps({"type": "end", "card_count": len(cards)}, ensure_ascii=False, separators=(",", ":")))
    return ("\n".join(lines) + "\n").encode("utf-8")


def default_output_path(script_dir: Path) -> Path:
    # Timestamp-prefixed so it sorts after any earlier export: the device
    # picks the lexicographically greatest *.ndjson in system-due/ as "most
    # recent" rather than relying on SD card file mtimes (see
    # AnkiStore::findNewestSdDueFile()).
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return script_dir / "output" / f"{timestamp}-cards.ndjson"


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path", nargs="?", default=str(script_dir / "input" / "cards.csv"))
    parser.add_argument("-o", "--output", default=None)
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    output_path = Path(args.output) if args.output else default_output_path(script_dir)
    if not csv_path.exists():
        print(f"No such file: {csv_path}", file=sys.stderr)
        return 1

    try:
        cards = read_rows(csv_path)
        ndjson = build_ndjson(cards)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(ndjson)

    deck_count = len({deck for deck, _, _ in cards})
    print(f"Wrote {output_path}: {len(cards)} card(s) across {deck_count} deck(s), {len(ndjson)} bytes")
    print(f"Copy this file to the SD card as system-due/{output_path.name}, then use")
    print('"Load today\'s cards from SD" in the device\'s Anki menu.')
    return 0


if __name__ == "__main__":
    sys.exit(main())
