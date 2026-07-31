# v2.2.6 — first public release

## Assets

| File | Purpose |
| --- | --- |
| `xteink_sync.ankiaddon` | Anki Desktop add-on |
| `crosspoint-1.4.1-xteink-anki.bin` | Xteink X4 firmware (CrossPoint 1.4.1 + Anki) |
| `SHA256SUMS` | Checksums |

## Highlights

- Multi-deck pull: all top-level decks with due cards
- Up to 250 cards per deck (default), 1000 total
- Device: deck list/switch, progress, landscape, handedness
- Grade row L→R: Again · Hard · Good · Easy
- Greek (modern + polytonic) and German card font support
- NDJSON pull for low-RAM streaming; batch-safe push
- Web UI config for server URL + API token on the X4

## Install (short)

1. Install `.ankiaddon` in Anki → restart → **Tools → Xteink Status**
2. Flash `.bin` on **X4 / CrossPoint 1.4.1 only**
3. Join Wi‑Fi → `http://crosspoint.local/settings` → Anki URL + token
4. **Anki** menu → pull → study → push

## Not in this release

- Official CrossPoint upstream merge
- AnkiWeb store listing (install from file / GitHub)
- X3 or non-1.4.1 partition support
