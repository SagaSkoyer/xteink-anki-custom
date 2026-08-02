#!/usr/bin/env python3
"""ASCII layout simulation for Xteink X4 Anki screens.

Covers portrait (480×800) and landscape (800×480):
  - card status strip (optional front preview, progress bar, stats, deck)
  - Anki menu with every deck listed + progress subtitle
  - grade button row

Run before flashing to sanity-check layout, truncation, and wrapping.
"""

from __future__ import annotations

import textwrap
import unicodedata
from dataclasses import dataclass

# X4 panel logical coordinates (device rotates for landscape)
PORTRAIT = (480, 800)
LANDSCAPE = (800, 480)
SIDE_PAD = 20
HINT_H = 40
LINE_H_UI12 = 28
LINE_H_UI10 = 22  # progress / front-preview font
LINE_H_CARD = 30  # UI_12 + spacing
BAR_H = 8
AVG_CHAR_W_LATIN = 7.2
AVG_CHAR_W_GREEK = 8.0


def has_greek(s: str) -> bool:
    return any("GREEK" in unicodedata.name(ch, "") for ch in s if ch.isalpha())


def char_width(s: str) -> float:
    return AVG_CHAR_W_GREEK if has_greek(s) else AVG_CHAR_W_LATIN


def wrap_text(text: str, max_width_px: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        cw = char_width(paragraph)
        max_chars = max(8, int(max_width_px / cw))
        lines.extend(textwrap.wrap(paragraph, width=max_chars, break_long_words=True) or [""])
    return lines


def trunc(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: max(0, n - 1)] + "…"


def trunc_px(s: str, max_width_px: int) -> str:
    """Approximate renderer.truncateText for UI_10 Latin/Greek mix."""
    if not s:
        return s
    cw = char_width(s)
    max_chars = max(1, int(max_width_px / cw))
    return trunc(s, max_chars)


def plain_status_preview(text: str) -> str:
    """Mirror firmware plainStatusPreview: strip ** / STX-ETX, first line, collapse space."""
    out: list[str] = []
    pending_space = False
    i = 0
    while i < len(text):
        c = text[i]
        if c in "\n\r":
            break
        if c in ("\x02", "\x03"):
            i += 1
            continue
        if c == "*" and i + 1 < len(text) and text[i + 1] == "*":
            i += 2
            continue
        if c in " \t":
            pending_space = bool(out)
            i += 1
            continue
        if pending_space:
            out.append(" ")
            pending_space = False
        out.append(c)
        i += 1
    return "".join(out)


def box(lines: list[str], cols: int) -> str:
    border = "+" + "-" * (cols + 2) + "+"
    out = [border]
    for line in lines:
        out.append(f"| {line[:cols].ljust(cols)} |")
    out.append(border)
    return "\n".join(out)


def progress_bar(pct: int, width: int) -> str:
    filled = int(round(width * pct / 100))
    filled = max(0, min(width, filled))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def center(s: str, width: int) -> str:
    s = s[:width]
    pad = max(0, width - len(s))
    left = pad // 2
    return " " * left + s + " " * (pad - left)


@dataclass
class StatusMetrics:
    screen_w: int
    screen_h: int
    landscape: bool
    status_inner_w: int
    cols: int
    header_y: int
    front_y: int | None
    bar_y: int
    stats_y: int
    separator_y: int
    content_top: int
    content_bottom: int
    available: int
    max_lines: int
    front_shown: str


def status_metrics(
    screen_w: int,
    screen_h: int,
    *,
    answer: bool,
    front: str,
    landscape: bool,
    deck: str = "",
    remaining: int = 12,
    total: int = 50,
) -> StatusMetrics:
    pad = SIDE_PAD
    status_inner_w = max(1, screen_w - 2 * pad)
    cols = max(20, int(status_inner_w / AVG_CHAR_W_LATIN))
    gap_after_header = 2 if landscape else 4
    gap_bar_stats = 2
    gap_stats_sep = 2 if landscape else 4
    gap_sep_content = 4 if landscape else 8
    footer = 18 if landscape else (HINT_H + LINE_H_UI10 + 12)

    # Front lives IN the stats row (between progress and deck), not above the bar.
    cursor = gap_after_header
    bar_y = cursor
    cursor = bar_y + BAR_H + gap_bar_stats
    stats_y = cursor
    front_y = stats_y if answer and plain_status_preview(front) else None

    stats = f"{remaining}/{total} · {100 if total == 0 else int((total - remaining) * 100 / total)}%"
    deck_cap = max(8, cols // 3)
    deck_fit = trunc(deck or "Anki", deck_cap) if deck else ""
    # Middle slot for front (char approx of firmware midMaxW).
    left_chars = len(stats) + 2
    right_chars = len(deck_fit) + 2 if deck_fit else 0
    mid_chars = max(0, cols - left_chars - right_chars)
    front_shown = ""
    if answer:
        plain = plain_status_preview(front)
        if plain and mid_chars > 4:
            front_shown = trunc_px(plain, int(mid_chars * AVG_CHAR_W_LATIN))

    cursor = stats_y + LINE_H_UI10 + gap_stats_sep
    separator_y = cursor
    content_top = separator_y + gap_sep_content
    content_bottom = screen_h - footer
    available = max(1, content_bottom - content_top)
    return StatusMetrics(
        screen_w=screen_w,
        screen_h=screen_h,
        landscape=landscape,
        status_inner_w=status_inner_w,
        cols=cols,
        header_y=gap_after_header,
        front_y=front_y,
        bar_y=bar_y,
        stats_y=stats_y,
        separator_y=separator_y,
        content_top=content_top,
        content_bottom=content_bottom,
        available=available,
        max_lines=max(1, available // LINE_H_CARD),
        front_shown=front_shown,
    )


def simulate_card(
    side: str,
    body: str,
    remaining: int,
    total: int,
    deck: str,
    *,
    front: str | None = None,
    landscape: bool = False,
    scale: int = 1,
) -> str:
    screen_w, screen_h = LANDSCAPE if landscape else PORTRAIT
    answer = side in ("Antwort", "Answer")
    # On answer, front is the EN/L2 prompt; if not given, treat body as back-only.
    front_text = front if front is not None else ("" if answer else body)
    m = status_metrics(
        screen_w,
        screen_h,
        answer=answer,
        front=front_text,
        landscape=landscape,
        deck=deck or "Anki",
        remaining=remaining,
        total=total,
    )
    pct = 100 if total == 0 else int((total - remaining) * 100 / total)
    cols = m.cols

    stats = f"{remaining}/{total} · {pct}%"
    deck_cap = max(8, cols // 3)
    deck_fit = trunc(deck or "Anki", deck_cap)
    # Build one status line: progress | centered front | deck
    mid = m.front_shown if m.front_shown else ""
    left = stats
    right = deck_fit
    used = len(left) + len(right) + (2 if mid else 0)
    space = max(0, cols - used)
    if mid:
        # pad around mid to fill middle
        pad_total = max(1, space)
        pad_l = pad_total // 2
        pad_r = pad_total - pad_l
        stats_row = left + " " * max(1, pad_l) + mid + " " * max(1, pad_r) + right
        if len(stats_row) > cols:
            stats_row = stats_row[:cols]
    else:
        gap = max(1, cols - len(stats) - len(deck_fit))
        stats_row = stats + " " * gap + deck_fit

    bar_w = max(12, min(cols, cols - 2))
    content_w = screen_w - 2 * (SIDE_PAD + 4)
    lines = wrap_text(body, content_w // scale)
    per_page = max(1, m.max_lines // scale)
    pages = [lines[i : i + per_page] for i in range(0, max(1, len(lines)), per_page)] or [[]]

    blocks = []
    for page in pages:
        body_lines: list[str] = []
        body_lines.append(progress_bar(pct, bar_w))
        body_lines.append(stats_row)
        body_lines.append("-" * cols)
        for i in range(per_page):
            body_lines.append(page[i] if i < len(page) else "")
        body_lines.append("-" * cols)
        body_lines.append("Seiten: blättern" if len(pages) > 1 else "")
        if answer:
            body_lines.append("Nochmal | Schwer | Gut | Einfach")
        else:
            body_lines.append("Zurück | Antwort |   |   ")
        blocks.append(box(body_lines, cols))
        blocks.append(
            f"  [metrics] {'LANDSCAPE' if landscape else 'PORTRAIT'} {screen_w}x{screen_h}  "
            f"status_h={m.separator_y}+{4 if landscape else 8}  content_top={m.content_top}  "
            f"avail={m.available}px  lines/page={per_page}  scale={scale}  "
            f"front={m.front_shown!r}  progress={remaining}/{total}={pct}%  greek={has_greek(body)}"
        )
        # Geometry invariants: front is on the stats row (same y as stats), not above bar
        if m.front_y is not None:
            assert m.front_y == m.stats_y
        assert m.bar_y < m.stats_y < m.separator_y < m.content_top
        assert m.content_top < m.content_bottom
        assert m.available >= LINE_H_CARD, f"content too tight: avail={m.available}"
        # Front fits middle slot (never full status width alone)
        if m.front_shown:
            assert len(m.front_shown) * char_width(m.front_shown) <= m.status_inner_w + AVG_CHAR_W_LATIN
    return "\n\n".join(blocks)


def simulate_menu(decks: list[tuple[str, int, int]]) -> str:
    cols = 56
    rows = []
    for name, rem, tot in decks:
        pct = 100 if tot == 0 else int((tot - rem) * 100 / tot)
        sub = "fertig" if rem == 0 else f"{rem}/{tot} · {pct}%"
        dim = " (dim)" if rem == 0 else ""
        title = trunc(name, 32)
        value = f"{rem} übrig"
        rows.append(f"> {title.ljust(32)} {value}")
        rows.append(f"    {sub}{dim}")
    rows.append("-" * cols)
    rows.append("  Heutige Karten laden")
    rows.append("  Anki-Einstellungen")
    rows.append("-" * cols)
    rows.append("Zurück | Auswählen | ↑ | ↓")
    return box(["Anki", "-" * cols, *rows], cols)


SAMPLES = [
    # side, body (shown), front (EN/L2), deck, rem, tot
    ("Frage", "responsibility / Verantwortung", None, "Griechisch · NT", 12, 50),
    (
        "Antwort",
        "η ευθύνη\nMemory: stem -ευθυν- ~ duty\n| Person | Form |\n| --- | --- |",
        "responsibility / Verantwortung",
        "Griechisch · NT",
        12,
        50,
    ),
    (
        "Antwort",
        "το ξενοδοχείο",
        "hotel / Hotel",
        "Vokabeln",
        3,
        20,
    ),
    (
        "Antwort",
        "ἀλήθεια",
        "truth / Wahrheit — a very long English and German prompt that must be truncated on the device",
        "Polytonisch mit langem Stapelnamen der abgeschnitten wird",
        1,
        8,
    ),
    (
        "Antwort",
        "γράφω\n| Person | Form |\n| --- | --- |\n| εγώ | γράφω |",
        "I write / ich schreibe",
        "Verben",
        7,
        40,
    ),
    (
        "Antwort",
        "short",
        "**bold** front\x02with\x03 markers and   spaces",
        "Markers",
        2,
        5,
    ),
]


def main() -> None:
    print("Xteink X4 Anki layout simulation — portrait + landscape, front preview on answer\n")

    print("=" * 60)
    print("MENU")
    print(
        simulate_menu(
            [
                ("Griechisch · NT", 12, 50),
                ("Deutsch", 0, 20),
                ("Polytonisch", 3, 8),
                ("Leerer Stapel", 0, 0),
            ]
        )
    )
    print()

    failures = 0
    for side, body, front, deck, rem, tot in SAMPLES:
        for landscape in (False, True):
            orient = "LANDSCAPE" if landscape else "PORTRAIT"
            print("=" * 60)
            print(f"CARD {orient} {side}: front={front!r} body={body[:40]!r}…")
            try:
                print(simulate_card(side, body, rem, tot, deck, front=front, landscape=landscape))
            except AssertionError as e:
                failures += 1
                print(f"  FAIL: {e}")
            print()

    # Large font stress (portrait + landscape answer)
    print("=" * 60)
    print("CARD scale=2 landscape answer")
    print(
        simulate_card(
            "Antwort",
            "ἀλήθεια",
            5,
            10,
            "Greek",
            front="truth / Wahrheit",
            landscape=True,
            scale=2,
        )
    )
    print()

    # Truncation unit checks — front is mid-status (same y as stats)
    long_front = "a" * 200
    plain = plain_status_preview("  **hello**  \x02world\x03\nignored")
    assert plain == "hello world", plain
    m = status_metrics(
        800, 480, answer=True, front=long_front, landscape=True, deck="Greek Preply Ian", remaining=12, total=50
    )
    assert m.front_y == m.stats_y
    assert m.front_shown.endswith("…") or len(m.front_shown) < 200
    assert m.available >= LINE_H_CARD, m.available

    # Landscape answer must leave usable body lines (no extra front row above bar)
    m2 = status_metrics(
        800, 480, answer=True, front="hotel / Hotel", landscape=True, deck="Greek", remaining=3, total=10
    )
    assert m2.front_y == m2.stats_y
    assert m2.max_lines >= 4, f"landscape answer too tight: max_lines={m2.max_lines}"
    m3 = status_metrics(
        480, 800, answer=True, front="hotel / Hotel", landscape=False, deck="Greek", remaining=3, total=10
    )
    assert m3.front_y == m3.stats_y
    assert m3.max_lines >= 8, f"portrait answer too tight: max_lines={m3.max_lines}"

    if failures:
        raise SystemExit(f"{failures} layout assertion(s) failed")
    print("OK — layout asserts passed (portrait + landscape, front preview, truncation)")


if __name__ == "__main__":
    main()
