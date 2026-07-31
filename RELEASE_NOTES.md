# v2.4.0 — XFD flashcard dialect + bold on e-ink

## Assets

| File | Purpose |
| --- | --- |
| `xteink_sync.ankiaddon` | Anki Desktop add-on **2.4.0** |
| `crosspoint-1.4.1-xteink-anki.bin` | Xteink X4 firmware (Phase B bold) |
| `SHA256SUMS` | Checksums |

## Highlights (EN)

- **XFD** (*Xteink Flashcard Dialect*): HTML/Markdown tables, lists, headings, quotes → e-ink plain text on pull
- Grammar-friendly **pipe tables** and HTML `<table>` (2–4 columns; wider tables stack as key/value)
- **Bold on device (Phase B):** `**…**` / `<b>` become STX/ETX markers; firmware draws mixed regular/bold runs
- Fallback: raw `**` still toggles bold if markers were not applied
- Still includes v2.3.x: multi-deck pull, Greek UI font, queue-order push fallback, partial push summary

## Highlights (DE)

- **XFD**-Dialekt: Tabellen, Listen, Überschriften, Zitate beim Pull als Klartext fürs E-Ink
- Grammatik-Tabellen (Markdown/HTML), bei zu vielen Spalten gestapelt statt abgeschnitten
- **Fett auf dem Gerät:** Converter setzt Marker; Firmware zeichnet Bold/Regular-Läufe
- Fallback `**` am Gerät; weiterhin Multi-Stapel, griechische UI-Schrift, Push-Fallbacks aus v2.3.x

## Install

1. Add-on **2.4.0** installieren → Anki neu starten  
2. Firmware-Bin flashen (X4 / CrossPoint **1.4.1**) — nötig für sichtbares Bold  
3. Karten mit Tabellen/`**Lemma**` pullen und prüfen  
