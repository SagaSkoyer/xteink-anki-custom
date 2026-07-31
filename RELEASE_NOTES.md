# v2.3.2 — offline push: queue-order fallback + clearer partial message

## Assets

| File | Purpose |
| --- | --- |
| `xteink_sync.ankiaddon` | Anki Desktop add-on **2.3.2** |
| `crosspoint-1.4.1-xteink-anki.bin` | Xteink X4 firmware |
| `SHA256SUMS` | Checksums |

## Highlights (EN)

- Push: if Anki says **not at top of queue**, fall back to legacy `answerCard` so offline grades still apply
- Partial push: short summary on device (`N ok, M skipped`), clear local session (batch is finished server-side)
- Still includes v2.3.1: Greek UI font default, max-card limits on device/web

## Highlights (DE)

- Upload: bei Anki-Fehler **not at top of queue** Fallback auf die Legacy-API, damit Offline-Bewertungen trotzdem ankommen
- Teil-Upload: kurze Meldung am Gerät (`N ok, M übersprungen`), lokale Session wird geleert
- Enthält weiterhin v2.3.1: Kartenschrift UI (DE/Griechisch), Max-Karten in Web und Geräte-Einstellungen

## Install

1. Add-on 2.3.2 installieren → Anki neu starten
2. Firmware-Bin flashen (X4 / CrossPoint 1.4.1)
3. Offline lernen → **Bewertungen übertragen**
