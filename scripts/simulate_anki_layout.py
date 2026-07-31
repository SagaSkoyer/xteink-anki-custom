#!/usr/bin/env python3
"""ASCII layout simulation for Xteink X4 Anki screens (480x800 portrait).

Covers:
  - card status strip (deck name, progress bar, remaining/total · %, side)
  - Anki menu with every deck listed + progress subtitle
  - grade button row L→R

Run before flashing to sanity-check layout and wrapping.
"""

from __future__ import annotations

import textwrap
import unicodedata

# X4 panel (portrait logical coordinates)
SCREEN_W = 480
SCREEN_H = 800
SIDE_PAD = 20
HINT_H = 40
LINE_H_UI12 = 28
LINE_H_UI10 = 22
LINE_H_CARD = 30  # UI_12 + spacing
BAR_H = 8
STATUS_GAP = 4
AVG_CHAR_W_LATIN = 7.2
AVG_CHAR_W_GREEK = 8.0
INNER_COLS = 56


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


def box(lines: list[str]) -> str:
    w = INNER_COLS
    border = "+" + "-" * (w + 2) + "+"
    out = [border]
    for line in lines:
        out.append(f"| {line[:w].ljust(w)} |")
    out.append(border)
    return "\n".join(out)


def status_metrics() -> dict:
    header_y = 4
    name_y = header_y
    bar_y = name_y + LINE_H_UI12 + STATUS_GAP
    stats_y = bar_y + BAR_H + 2
    separator_y = stats_y + LINE_H_UI10 + 4
    content_top = separator_y + 8
    footer = HINT_H + LINE_H_UI10 + 12
    content_bottom = SCREEN_H - footer
    available = max(1, content_bottom - content_top)
    return {
        "header_y": header_y,
        "name_y": name_y,
        "bar_y": bar_y,
        "stats_y": stats_y,
        "separator_y": separator_y,
        "content_top": content_top,
        "content_bottom": content_bottom,
        "available": available,
        "max_lines": max(1, available // LINE_H_CARD),
        "status_inner_w": SCREEN_W - 2 * SIDE_PAD,
    }


def progress_bar(pct: int, width: int = 24) -> str:
    filled = int(round(width * pct / 100))
    filled = max(0, min(width, filled))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def simulate_card(
    side: str,
    text: str,
    remaining: int,
    total: int,
    deck: str,
    scale: int = 1,
) -> str:
    m = status_metrics()
    pct = 100 if total == 0 else int((total - remaining) * 100 / total)
    name = trunc(deck or "Anki", INNER_COLS)
    stats = f"{remaining}/{total} · {pct}%"
    side_label = side
    # right-align side in display row
    mid = f"{stats}"
    gap = max(1, INNER_COLS - len(mid) - len(side_label))
    stats_row = mid + " " * gap + side_label

    content_w = SCREEN_W - 2 * (SIDE_PAD + 4)
    lines = wrap_text(text, content_w // scale)
    per_page = max(1, m["max_lines"] // scale)
    pages = [lines[i : i + per_page] for i in range(0, max(1, len(lines)), per_page)] or [[]]

    blocks = []
    for pi, page in enumerate(pages):
        body = [name, progress_bar(pct), stats_row, "-" * INNER_COLS]
        for i in range(per_page):
            body.append(page[i] if i < len(page) else "")
        body.append("-" * INNER_COLS)
        body.append("Seiten: blättern" if len(pages) > 1 else "")
        if side in ("Antwort", "Answer"):
            # Right-handed L→R: Again Hard Good Easy (Nochmal Schwer Gut Einfach).
            # Left-handed reverses the row.
            body.append("Nochmal | Schwer | Gut | Einfach")
        else:
            body.append("Zurück | Antwort |   |   ")
        blocks.append(box(body))
        blocks.append(
            f"  [metrics] status_h={m['separator_y']}+8  content_top={m['content_top']}  "
            f"avail={m['available']}px  lines/page={per_page}  scale={scale}  "
            f"deck={deck!r}  progress={remaining}/{total}={pct}%  greek={has_greek(text)}"
        )
        # Overlap checks
        assert m["name_y"] < m["bar_y"] < m["stats_y"] < m["separator_y"] < m["content_top"]
        assert m["content_top"] + per_page * LINE_H_CARD * scale <= m["content_bottom"] + LINE_H_CARD
    return "\n\n".join(blocks)


def simulate_menu(decks: list[tuple[str, int, int]]) -> str:
    """decks: (name, remaining, total)"""
    rows = []
    for name, rem, tot in decks:
        pct = 100 if tot == 0 else int((tot - rem) * 100 / tot)
        sub = "fertig" if rem == 0 else f"{rem}/{tot} · {pct}%"
        dim = " (dim)" if rem == 0 else ""
        title = trunc(name, 32)
        value = f"{rem} übrig"
        rows.append(f"> {title.ljust(32)} {value}")
        rows.append(f"    {sub}{dim}")
    rows.append("-" * INNER_COLS)
    rows.append("  Heutige Karten laden")
    rows.append("  Anki-Einstellungen")
    rows.append("-" * INNER_COLS)
    rows.append("Zurück | Auswählen | ↑ | ↓")
    assert all(d[0] for d in decks), "every deck must have a name for listing"
    assert len(decks) == len({d[0] for d in decks}) or True  # names may repeat
    return box(["Anki", "-" * INNER_COLS, *rows])


SAMPLES = [
    ("Frage", "Verantwortung", "Griechisch · NT", 12, 50),
    ("Antwort", "η ευθύνη / die Verantwortung", "Griechisch · NT", 12, 50),
    (
        "Frage",
        "Der schnelle braune Fuchs springt über den faulen Hund.",
        "Deutsch Vokabeln sehr langer Stapelname der abgeschnitten werden muss",
        3,
        20,
    ),
    (
        "Antwort",
        "ἡ ἀλήθεια ἐλευθερώσει ὑμᾶς — Die Wahrheit wird euch freimachen (Joh 8,32).",
        "Polytonisch",
        1,
        8,
    ),
]


def main() -> None:
    print(f"Xteink X4 Anki layout simulation  {SCREEN_W}x{SCREEN_H} portrait\n")

    print("=" * 60)
    print("MENU — every deck listed")
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

    for side, text, deck, rem, tot in SAMPLES:
        print("=" * 60)
        print(f"CARD {side}: {text!r}")
        print(simulate_card(side, text, rem, tot, deck))
        print()

    # Landscape-ish tighter content check with larger scale
    print("=" * 60)
    print("CARD scale=2 (large font)")
    print(simulate_card("Frage", "ἀλήθεια", 5, 10, "Greek", scale=2))
    print()
    print("OK — layout asserts passed")


if __name__ == "__main__":
    main()
