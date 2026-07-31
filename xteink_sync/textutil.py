"""Plain-text extraction for Anki card HTML and note fields (no aqt dependency)."""

from __future__ import annotations

import html
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

EMPTY_SIDE_PLACEHOLDER = "[…]"

_ANSWER_SEPARATOR_RE = re.compile(
    r"<hr\b[^>]*\bid\s*=\s*([\"']?)answer\1[^>]*>",
    flags=re.IGNORECASE,
)
# Also match Anki's common unquoted / class-based answer separators.
_ANSWER_SEPARATOR_LOOSE_RE = re.compile(
    r"<hr\b[^>]*(?:\bid\s*=\s*([\"']?)answer\1|class\s*=\s*([\"'][^\"']*\banswer\b[^\"']*[\"']))[^>]*>",
    flags=re.IGNORECASE,
)
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
_STRUCTURAL_TAG_RE = re.compile(
    r"</?(?:br|div|p|li|tr|h[1-6]|section|article|blockquote|td|th)\b[^>]*>",
    flags=re.IGNORECASE,
)
_CLOZE_RE = re.compile(r"\{\{c\d+::(.*?)(?:::(.*?))?\}\}", flags=re.DOTALL)
_SOUND_RE = re.compile(r"\[sound:[^\]]+\]", flags=re.IGNORECASE)
_RUBY_RT_RE = re.compile(r"<rt\b[^>]*>.*?</rt>", flags=re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", flags=re.IGNORECASE)
_ATTR_RE = re.compile(
    r"""\b(alt|title|aria-label)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
    flags=re.IGNORECASE,
)

# Common field names across German/English note types.
_FRONT_FIELD_NAMES = (
    "Front",
    "Text",
    "Question",
    "Frage",
    "Vorderseite",
    "Word",
    "Wort",
    "Expression",
    "Term",
    "Begriff",
    "Greek",
    "Griechisch",
    "Lemma",
    "Prompt",
)
_BACK_FIELD_NAMES = (
    "Back",
    "Extra",
    "Answer",
    "Antwort",
    "Rückseite",
    "Meaning",
    "Definition",
    "Übersetzung",
    "Translation",
    "German",
    "Deutsch",
    "English",
    "Notes",
    "Notiz",
)


def _img_placeholder(tag: str) -> str:
    for match in _ATTR_RE.finditer(tag):
        value = match.group(2) or match.group(3) or match.group(4) or ""
        value = html.unescape(value).strip()
        if value:
            return f"[{value}]"
    # Keep a visible marker so media-only cards are not blank.
    if re.search(r"\bsrc\s*=", tag, flags=re.IGNORECASE):
        return "[Bild]"
    return ""


def plain_text(card_html: str, limit: int = 4096) -> str:
    """Convert Anki card/field HTML to compact plain text for the e-ink device."""

    if not card_html:
        return ""

    text = str(card_html)
    # Un-rendered cloze in fields: keep the answer text.
    text = _CLOZE_RE.sub(lambda match: match.group(1), text)
    text = _SOUND_RE.sub("", text)
    text = _RUBY_RT_RE.sub("", text)
    text = _IMG_TAG_RE.sub(lambda match: _img_placeholder(match.group(0)), text)
    text = _SCRIPT_STYLE_RE.sub("", text)
    text = _STRUCTURAL_TAG_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text).replace("\r\n", "\n").replace("\xa0", " ")

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    compact_lines: List[str] = []
    for line in lines:
        if line:
            compact_lines.append(line)
        elif compact_lines and compact_lines[-1]:
            compact_lines.append("")

    result = "\n".join(compact_lines).strip()
    if limit > 0 and len(result) > limit:
        return result[: max(0, limit - 1)].rstrip() + "…"
    return result


def answer_only(answer_html: str) -> str:
    """Return the back side after Anki's answer separator, if present."""

    if not answer_html:
        return ""
    for pattern in (_ANSWER_SEPARATOR_RE, _ANSWER_SEPARATOR_LOOSE_RE):
        split = pattern.split(answer_html, maxsplit=1)
        # Capturing groups from re.split produce extra list entries.
        if len(split) >= 2:
            return split[-1]
    return answer_html


def _first_named(fields: Dict[str, str], names: Sequence[str]) -> str:
    lower_map = {key.lower(): value for key, value in fields.items()}
    for name in names:
        value = lower_map.get(name.lower())
        if value:
            return value
    return ""


def field_map_from_pairs(pairs: Iterable[Tuple[str, str]], limit: int = 4096) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for name, raw in pairs:
        plain = plain_text(raw or "", limit)
        if plain:
            result[str(name)] = plain
    return result


def sides_from_fields(
    fields: Dict[str, str],
    text_limit: int = 4096,
    reverse: bool = False,
) -> Tuple[str, str]:
    """Pick front/back from named or ordered note fields."""

    if not fields:
        return "", ""

    front = _first_named(fields, _FRONT_FIELD_NAMES)
    back = _first_named(fields, _BACK_FIELD_NAMES)
    values = list(fields.values())

    if not front:
        front = values[0]
    if not back:
        # Prefer a field that differs from the front.
        back = next((value for value in values if value != front), values[-1])

    if reverse:
        front, back = back, front

    return front[:text_limit], back[:text_limit]


def dump_fields(fields: Dict[str, str], text_limit: int = 4096) -> str:
    if not fields:
        return ""
    lines = [f"{name}: {value}" for name, value in fields.items()]
    return "\n".join(lines)[:text_limit]


def combine_sides(
    rendered_front: str,
    rendered_back: str,
    fields: Dict[str, str],
    text_limit: int = 4096,
    reverse: bool = False,
) -> Tuple[str, str]:
    """Prefer rendered template text; fall back to note fields; never leave blank."""

    front = (rendered_front or "").strip()
    back = (rendered_back or "").strip()
    field_front, field_back = sides_from_fields(fields, text_limit, reverse=reverse)

    if not front:
        front = field_front
    if not back:
        back = field_back

    # If rendering produced only whitespace/media markers but fields have real words,
    # prefer fields when the rendered side is a weak placeholder.
    weak = {"", "[…]", "[Bild]", "[bild]"}
    if front in weak and field_front:
        front = field_front
    if back in weak and field_back:
        back = field_back

    if not front or not back:
        dumped = dump_fields(fields, text_limit)
        if not front:
            front = dumped
        if not back:
            back = dumped

    front = front.strip() or EMPTY_SIDE_PLACEHOLDER
    back = back.strip() or EMPTY_SIDE_PLACEHOLDER
    if len(front) > text_limit:
        front = front[: text_limit - 1].rstrip() + "…"
    if len(back) > text_limit:
        back = back[: text_limit - 1].rstrip() + "…"
    return front, back


def looks_reversed_template(template_name: str = "", note_type_name: str = "", ord_: int = 0) -> bool:
    tmpl = (template_name or "").lower()
    ntype = (note_type_name or "").lower()
    if "reverse" in tmpl or "umgekehrt" in tmpl or "rück" in tmpl:
        return True
    if ord_ == 1 and ("basic" in ntype or "basis" in ntype):
        return True
    return False
