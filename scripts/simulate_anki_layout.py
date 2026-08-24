#!/usr/bin/env python3
"""ASCII layout simulation for Xteink Anki screens.

Covers portrait (480×800) and landscape (800×480):
  - card body (no header: cards are text only, clipped — no paging)
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
class CardMetrics:
    screen_w: int
    screen_h: int
    landscape: bool
    cols: int
    content_top: int
    content_bottom: int
    available: int
    max_lines: int


def card_metrics(screen_w: int, screen_h: int, *, landscape: bool) -> CardMetrics:
    """Mirror AnkiActivity::renderCard: no header, body starts at the safe-area top."""
    cols = max(20, int((screen_w - 2 * SIDE_PAD) / AVG_CHAR_W_LATIN))
    content_top = 2 if landscape else 4
    footer = 4 if landscape else (HINT_H + 8)
    content_bottom = screen_h - footer
    available = max(1, content_bottom - content_top)
    return CardMetrics(
        screen_w=screen_w,
        screen_h=screen_h,
        landscape=landscape,
        cols=cols,
        content_top=content_top,
        content_bottom=content_bottom,
        available=available,
        max_lines=max(1, available // LINE_H_CARD),
    )


def simulate_card(
    side: str,
    body: str,
    *,
    flagged: bool = False,
    landscape: bool = False,
    scale: int = 1,
) -> str:
    screen_w, screen_h = LANDSCAPE if landscape else PORTRAIT
    answer = side in ("Antwort", "Answer")
    m = card_metrics(screen_w, screen_h, landscape=landscape)
    cols = m.cols

    content_w = screen_w - 2 * (SIDE_PAD + 4)
    lines = wrap_text(body, content_w // scale)
    per_page = max(1, m.max_lines // scale)
    shown, clipped = lines[:per_page], max(0, len(lines) - per_page)

    body_lines: list[str] = []
    for i in range(per_page):
        line = shown[i] if i < len(shown) else ""
        # Flag pennant sits in the bottom-right corner of the content area.
        if flagged and i == per_page - 1:
            line = line[: cols - 2].ljust(cols - 2) + "|>"
        body_lines.append(line)
    body_lines.append("-" * cols)
    body_lines.append("Nochmal / Gut = Seitentasten" if answer else "Umdrehen = Seitentasten")
    body_lines.append("Zurück | Rückgängig | Flag | Zurückstellen")

    out = box(body_lines, cols)
    out += (
        f"\n  [metrics] {'LANDSCAPE' if landscape else 'PORTRAIT'} {screen_w}x{screen_h}  "
        f"content_top={m.content_top}  avail={m.available}px  lines={per_page}  scale={scale}  "
        f"clipped={clipped}  flag={flagged}  greek={has_greek(body)}"
    )
    assert m.content_top < m.content_bottom
    assert m.available >= LINE_H_CARD, f"content too tight: avail={m.available}"
    return out


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
    # side, body (shown), flagged
    ("Frage", "responsibility / Verantwortung", False),
    (
        "Antwort",
        "η ευθύνη\nMemory: stem -ευθυν- ~ duty\n| Person | Form |\n| --- | --- |",
        True,
    ),
    ("Antwort", "το ξενοδοχείο", False),
    ("Antwort", "ἀλήθεια", True),
    ("Antwort", "γράφω\n| Person | Form |\n| --- | --- |\n| εγώ | γράφω |", False),
    ("Antwort", "short", False),
    (
        "Antwort",
        # Long enough to be clipped in portrait: cards no longer page.
        " ".join(["λόγος Wort word Bedeutung meaning Beispiel example"] * 12),
        False,
    ),
]


def main() -> None:
    print("Xteink Anki layout simulation — portrait + landscape, header-less cards\n")

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
    for side, body, flagged in SAMPLES:
        for landscape in (False, True):
            orient = "LANDSCAPE" if landscape else "PORTRAIT"
            print("=" * 60)
            print(f"CARD {orient} {side}: flag={flagged} body={body[:40]!r}…")
            try:
                print(simulate_card(side, body, flagged=flagged, landscape=landscape))
            except AssertionError as e:
                failures += 1
                print(f"  FAIL: {e}")
            print()

    # Large font stress (landscape answer)
    print("=" * 60)
    print("CARD scale=2 landscape answer")
    print(simulate_card("Antwort", "ἀλήθεια", flagged=True, landscape=True, scale=2))
    print()

    # Geometry checks — no header means the body starts at the top of the screen.
    m_land = card_metrics(800, 480, landscape=True)
    m_port = card_metrics(480, 800, landscape=False)
    assert m_land.content_top <= 2, m_land.content_top
    assert m_land.max_lines >= 4, f"landscape too tight: max_lines={m_land.max_lines}"
    assert m_port.max_lines >= 8, f"portrait too tight: max_lines={m_port.max_lines}"

    # Dropping the status strip must not cost body lines.
    assert m_port.max_lines >= 24, f"portrait lost body lines: {m_port.max_lines}"

    # Overlong cards are clipped, never paged.
    long_body = " ".join(["wort"] * 400)
    rendered = simulate_card("Antwort", long_body, landscape=False)
    assert "clipped=" in rendered and "clipped=0" not in rendered, rendered[-200:]

    if failures:
        raise SystemExit(f"{failures} layout assertion(s) failed")
    print("OK — layout asserts passed (portrait + landscape, clipping, flag corner)")


if __name__ == "__main__":
    main()
