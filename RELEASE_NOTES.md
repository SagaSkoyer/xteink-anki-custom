# v2.3.0 — multi-language fonts + pull limits in web UI

## Assets

| File | Purpose |
| --- | --- |
| `xteink_sync.ankiaddon` | Anki Desktop add-on **2.3.0** |
| `crosspoint-1.4.1-xteink-anki.bin` | Xteink X4 firmware (CrossPoint 1.4.1 + Anki) |
| `SHA256SUMS` | Checksums |

## Highlights

- **Card text** uses CrossPoint **reader fonts** (built-in Noto + SD fonts) — any language you have fonts for, not a Greek-only UI pack
- Web UI: **Max cards per deck** and **Max cards total** (stored on X4, sent as `?max_cards=&max_total=` on pull)
- Add-on accepts those query params (clamped 1–1000); defaults still in add-on config
- Multi-deck pull, grades Again·Hard·Good·Easy, NDJSON, batch-safe push

## Install (short)

1. Install `.ankiaddon` 2.3.0+ in Anki → restart → **Tools → Xteink Status**
2. Flash `.bin` on **X4 / CrossPoint 1.4.1 only**
3. Join Wi‑Fi → `http://crosspoint.local/settings` → Anki URL, token, card limits
4. For other scripts: CrossPoint **Font** settings / SD fonts
5. **Anki** menu → pull → study → push

## Not in this release

- Official CrossPoint upstream merge
- AnkiWeb store listing (install from file / GitHub)
- X3 or non-1.4.1 partition support
