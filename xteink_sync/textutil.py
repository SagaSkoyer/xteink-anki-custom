"""Plain-text / XFD conversion for Anki cards (no aqt dependency).

XFD (*Xteink Flashcard Dialect*) maps a small HTML/Markdown subset to
device-ready plain text: tables, lists, titles, quotes, separators.

Phase B bold: HTML/Markdown emphasis becomes STX/ETX markers (U+0002 / U+0003)
in the pull payload. The X4 draws mixed regular/bold runs; it also accepts
visible ``**…**`` as a toggle fallback. Inline code markers are stripped.
"""

from __future__ import annotations

import html
import re
from typing import Dict, Iterable, List, Sequence, Tuple

EMPTY_SIDE_PLACEHOLDER = "[…]"

# Zero-width style markers for the X4 (not shown as glyphs).
BOLD_ON = "\x02"
BOLD_OFF = "\x03"

# Layout budgets for e-ink (character columns, not pixels).
MAX_TABLE_COLUMNS = 4
DEFAULT_WIDTH_BUDGET = 42
COL_GAP = 2

_BOLD_OPEN_TAG_RE = re.compile(r"<(?:b|strong)\b[^>]*>", flags=re.IGNORECASE)
_BOLD_CLOSE_TAG_RE = re.compile(r"</(?:b|strong)\s*>", flags=re.IGNORECASE)

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
_TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table>", flags=re.IGNORECASE | re.DOTALL)
_LIST_RE = re.compile(r"<(ul|ol)\b[^>]*>(.*?)</\1\s*>", flags=re.IGNORECASE | re.DOTALL)
_LI_RE = re.compile(r"<li\b[^>]*>(.*?)</li\s*>", flags=re.IGNORECASE | re.DOTALL)
_TR_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr\s*>", flags=re.IGNORECASE | re.DOTALL)
_CELL_RE = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]\s*>", flags=re.IGNORECASE | re.DOTALL)
_BLOCKQUOTE_RE = re.compile(
    r"<blockquote\b[^>]*>(.*?)</blockquote\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
_H12_RE = re.compile(r"<h([12])\b[^>]*>(.*?)</h\1\s*>", flags=re.IGNORECASE | re.DOTALL)
_H36_RE = re.compile(r"<h([3-6])\b[^>]*>(.*?)</h\1\s*>", flags=re.IGNORECASE | re.DOTALL)
_HR_RE = re.compile(r"<hr\b[^>]*/?>", flags=re.IGNORECASE)
_BR_RE = re.compile(r"<br\s*/?>", flags=re.IGNORECASE)
_BLOCK_OPEN_CLOSE_RE = re.compile(
    r"</?(?:p|div|section|article)\b[^>]*>",
    flags=re.IGNORECASE,
)

_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_MD_UL_RE = re.compile(r"^([-*+])\s+(.*)$")
_MD_OL_RE = re.compile(r"^(\d+)\.\s+(.*)$")
_MD_HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})\s*$")
_MD_SEP_CELL_RE = re.compile(r"^:?-{1,}:?$")
_BOLD_AST_RE = re.compile(r"\*\*(.+?)\*\*", flags=re.DOTALL)
_BOLD_UND_RE = re.compile(r"__(.+?)__", flags=re.DOTALL)
_CODE_RE = re.compile(r"`([^`]+)`")

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


def strip_style_markers(text: str) -> str:
    """Remove STX/ETX bold markers (for tests and plain comparisons)."""

    if not text:
        return ""
    return text.replace(BOLD_ON, "").replace(BOLD_OFF, "")


def _display_width(text: str) -> int:
    """Approximate glyph columns (markers have zero width)."""

    return len(strip_style_markers(text or ""))


def _clamp(text: str, limit: int) -> str:
    if limit > 0 and len(text) > limit:
        return text[: max(0, limit - 1)].rstrip() + "…"
    return text


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


def _html_bold_tags_to_markers(text: str) -> str:
    text = _BOLD_OPEN_TAG_RE.sub(BOLD_ON, text)
    text = _BOLD_CLOSE_TAG_RE.sub(BOLD_OFF, text)
    return text


def _md_bold_to_markers(text: str) -> str:
    """Convert ``**…**`` / ``__…__`` to STX/ETX (non-greedy, non-nested)."""

    def wrap(match: re.Match[str]) -> str:
        inner = match.group(1)
        if not inner:
            return ""
        return f"{BOLD_ON}{inner}{BOLD_OFF}"

    text = _BOLD_AST_RE.sub(wrap, text)
    text = _BOLD_UND_RE.sub(wrap, text)
    return text


def _apply_inline_styles(text: str) -> str:
    """Bold → markers; strip inline code backticks (content kept)."""

    text = _html_bold_tags_to_markers(text)
    text = _md_bold_to_markers(text)
    text = _CODE_RE.sub(r"\1", text)
    return text


def _compact_blank_lines(text: str) -> str:
    # Do not .strip() away style markers at line edges; only trim spaces/tabs.
    lines = [re.sub(r"[ \t]+", " ", line).strip(" \t") for line in text.split("\n")]
    compact: List[str] = []
    for line in lines:
        if line:
            compact.append(line)
        elif compact and compact[-1]:
            compact.append("")
    return "\n".join(compact).strip(" \t\n")


def _preprocess_media(text: str) -> str:
    text = _CLOZE_RE.sub(lambda match: match.group(1), text)
    text = _SOUND_RE.sub("", text)
    text = _RUBY_RT_RE.sub("", text)
    text = _IMG_TAG_RE.sub(lambda match: _img_placeholder(match.group(0)), text)
    text = _SCRIPT_STYLE_RE.sub("", text)
    return text


def _inline_to_text(fragment: str) -> str:
    """HTML fragment → single-line-ish plain text (no block structure)."""

    if not fragment:
        return ""
    text = str(fragment)
    text = _preprocess_media(text)
    text = _apply_inline_styles(text)
    text = _BR_RE.sub(" ", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text).replace("\r\n", "\n").replace("\xa0", " ")
    text = re.sub(r"[ \t\n]+", " ", text).strip(" \t")
    return text


def _normalize_rows(rows: List[List[str]]) -> List[List[str]]:
    if not rows:
        return []
    ncols = max((len(r) for r in rows), default=0)
    if ncols == 0:
        return []
    normalized = [list(r) + [""] * (ncols - len(r)) for r in rows]
    # Drop empty trailing columns.
    while ncols > 1 and all(not (r[ncols - 1] or "").strip() for r in normalized):
        ncols -= 1
        normalized = [r[:ncols] for r in normalized]
    # Drop fully empty rows (except keep a single empty edge case as nothing).
    normalized = [r for r in normalized if any((c or "").strip() for c in r)]
    return normalized


def _format_table_stacked(rows: List[List[str]]) -> str:
    """Wide tables: label + 'Header: value' lines (never silent crop)."""

    if not rows:
        return ""
    header = rows[0]
    body = rows[1:] if len(rows) > 1 else rows
    use_header = len(rows) > 1
    lines: List[str] = []
    for row in body:
        label = (row[0] or "").strip()
        if label:
            lines.append(label if label.endswith(".") else label)
        start = 1 if use_header or label else 0
        for index in range(start, len(row)):
            cell = (row[index] or "").strip()
            if not cell and use_header:
                continue
            if use_header and index < len(header) and (header[index] or "").strip():
                key = header[index].strip()
                lines.append(f"  {key}: {cell}" if cell else f"  {key}:")
            elif cell:
                lines.append(f"  {cell}")
    return "\n".join(lines)


def format_table(
    rows: List[List[str]],
    width_budget: int = DEFAULT_WIDTH_BUDGET,
    max_columns: int = MAX_TABLE_COLUMNS,
) -> str:
    """Layout a table as fixed columns or stacked key/value lines."""

    normalized = _normalize_rows(rows)
    if not normalized:
        return ""

    ncols = len(normalized[0])
    if ncols > max_columns:
        return _format_table_stacked(normalized)

    widths = [0] * ncols
    for row in normalized:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], _display_width(cell or ""))

    # Ensure at least 1 column width for empty header corner cells.
    widths = [max(w, 1) if any(r[i] for r in normalized) else max(w, 0) for i, w in enumerate(widths)]
    for index, width in enumerate(widths):
        if width == 0:
            widths[index] = 1

    total = sum(widths) + COL_GAP * max(0, ncols - 1)
    if total > width_budget and ncols > 2:
        # Prefer stacked over unreadable squash for grammar tables.
        return _format_table_stacked(normalized)

    gap = " " * COL_GAP

    def fmt_row(row: Sequence[str]) -> str:
        parts: List[str] = []
        for index, cell in enumerate(row):
            cell = cell or ""
            pad = widths[index] - _display_width(cell)
            parts.append(cell + (" " * max(0, pad)))
        return gap.join(parts).rstrip()

    lines = [fmt_row(normalized[0])]
    rule_width = min(sum(widths) + COL_GAP * max(0, ncols - 1), width_budget)
    lines.append("-" * max(3, rule_width))
    for row in normalized[1:]:
        lines.append(fmt_row(row))
    return "\n".join(lines)


def _parse_html_table(table_html: str) -> List[List[str]]:
    rows: List[List[str]] = []
    for tr_match in _TR_RE.finditer(table_html):
        cells = [_inline_to_text(cell) for cell in _CELL_RE.findall(tr_match.group(1))]
        if cells:
            rows.append(cells)
    return rows


def _replace_html_tables(text: str, width_budget: int) -> str:
    def repl(match: re.Match[str]) -> str:
        rows = _parse_html_table(match.group(0))
        laid = format_table(rows, width_budget=width_budget)
        return f"\n{laid}\n" if laid else "\n"

    return _TABLE_RE.sub(repl, text)


def _replace_html_lists(text: str) -> str:
    """Replace ul/ol blocks (innermost-first via repeated passes)."""

    for _ in range(12):

        def repl(match: re.Match[str]) -> str:
            tag = match.group(1).lower()
            body = match.group(2)
            items = _LI_RE.findall(body)
            if not items:
                return "\n"
            lines: List[str] = []
            for index, item in enumerate(items, start=1):
                # Nested lists already replaced in prior passes may leave lines.
                content = _inline_to_text(item)
                if not content:
                    # Preserve pre-converted nested bullet lines inside li.
                    inner = _preprocess_media(item)
                    inner = _TAG_RE.sub("\n", inner)
                    inner = html.unescape(inner)
                    content = _compact_blank_lines(inner)
                if tag == "ol":
                    lines.append(f"{index}. {content}" if content else f"{index}.")
                else:
                    lines.append(f"• {content}" if content else "•")
            return "\n" + "\n".join(lines) + "\n"

        new_text = _LIST_RE.sub(repl, text)
        if new_text == text:
            break
        text = new_text
    return text


def _replace_html_blockquotes(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        inner = _inline_to_text(match.group(1))
        if not inner:
            return "\n│\n"
        parts = [p.strip() for p in re.split(r"\n+", inner) if p.strip()]
        if not parts:
            parts = [inner]
        return "\n" + "\n".join(f"│ {p}" for p in parts) + "\n"

    return _BLOCKQUOTE_RE.sub(repl, text)


def _replace_html_headings(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        title = _inline_to_text(match.group(2))
        return f"\n{title}\n" if title else "\n"

    text = _H12_RE.sub(repl, text)
    text = _H36_RE.sub(repl, text)
    return text


def _is_md_separator_row(line: str) -> bool:
    """True for GFM table separator rows like `| --- | :---: |`."""

    stripped = line.strip()
    if not stripped:
        return False
    cells = _split_md_row(stripped)
    non_empty = [c for c in cells if c]
    if not non_empty:
        return False
    return all(_MD_SEP_CELL_RE.match(c.replace(" ", "")) for c in non_empty)


def _split_md_row(line: str) -> List[str]:
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [cell.strip() for cell in raw.split("|")]


def _looks_like_md_table(lines: Sequence[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    header = lines[index].strip()
    sep = lines[index + 1].strip()
    if "|" not in header:
        return False
    if not _is_md_separator_row(sep):
        return False
    # Separator should have roughly as many columns as header.
    return len(_split_md_row(sep)) >= 1


def _consume_md_table(
    lines: Sequence[str], start: int
) -> Tuple[List[List[str]], int]:
    rows = [_split_md_row(lines[start])]
    index = start + 2  # skip header + separator
    while index < len(lines):
        line = lines[index].strip()
        if not line or "|" not in line:
            break
        if _is_md_separator_row(line):
            break
        # Stop if line looks like a list/heading rather than a table row.
        if _MD_HEADING_RE.match(line) or _MD_UL_RE.match(line) or (
            _MD_OL_RE.match(line) and line.count("|") == 0
        ):
            break
        rows.append(_split_md_row(line))
        index += 1
    return rows, index


def _markdown_blocks(text: str, width_budget: int) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: List[str] = []
    index = 0
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()

        if _looks_like_md_table(lines, index):
            table_rows, next_index = _consume_md_table(lines, index)
            laid = format_table(table_rows, width_budget=width_budget)
            if laid:
                out.append(laid)
            index = next_index
            continue

        if not stripped:
            out.append("")
            index += 1
            continue

        heading = _MD_HEADING_RE.match(stripped)
        if heading:
            out.append(heading.group(2).strip())
            index += 1
            continue

        if _MD_HR_RE.match(stripped):
            out.append("────")
            index += 1
            continue

        if stripped.startswith(">"):
            quote = re.sub(r"^>\s?", "", stripped)
            out.append(f"│ {quote}" if quote else "│")
            index += 1
            continue

        unordered = _MD_UL_RE.match(stripped)
        if unordered:
            out.append(f"• {unordered.group(2)}")
            index += 1
            continue

        ordered = _MD_OL_RE.match(stripped)
        if ordered:
            out.append(f"{ordered.group(1)}. {ordered.group(2)}")
            index += 1
            continue

        out.append(raw)
        index += 1

    return "\n".join(out)


def to_device_text(
    source: str,
    limit: int = 4096,
    width_budget: int = DEFAULT_WIDTH_BUDGET,
) -> str:
    """Convert Anki HTML and/or XFD Markdown to e-ink plain text."""

    if not source:
        return ""

    text = str(source)
    text = _preprocess_media(text)
    # Bold tags before table/list extraction so cells keep emphasis.
    text = _html_bold_tags_to_markers(text)
    text = _replace_html_tables(text, width_budget=width_budget)
    text = _replace_html_lists(text)
    text = _replace_html_blockquotes(text)
    text = _replace_html_headings(text)
    text = _HR_RE.sub("\n────\n", text)
    text = _BR_RE.sub("\n", text)
    text = _BLOCK_OPEN_CLOSE_RE.sub("\n", text)
    # Leftover structural tags → line breaks; then drop remaining tags.
    text = _STRUCTURAL_TAG_RE.sub("\n", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text).replace("\r\n", "\n").replace("\xa0", " ")

    text = _markdown_blocks(text, width_budget=width_budget)
    # Markdown bold + code after block parse (lists/headings already handled).
    text = _md_bold_to_markers(text)
    text = _CODE_RE.sub(r"\1", text)
    text = _compact_blank_lines(text)
    return _clamp(text, limit)


def plain_text(card_html: str, limit: int = 4096) -> str:
    """Convert Anki card/field HTML to compact plain text for the e-ink device.

    Uses the XFD converter (tables, lists, headings, …). Kept as the stable
    public name used by the add-on and tests.
    """

    return to_device_text(card_html, limit=limit)


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
        plain = to_device_text(raw or "", limit=limit)
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
