# v2.4.1 — softer Anki menu refresh + font sizes 1× / 1.5× / 2×

## Assets

| File | Purpose |
| --- | --- |
| `xteink_sync.ankiaddon` | Anki Desktop add-on **2.4.0** (unchanged) |
| `crosspoint-1.4.1-xteink-anki.bin` | Xteink X4 firmware (rebuild required) |
| `SHA256SUMS` | Checksums |

## Firmware changes

### Menu e-ink flash (DE: „Flashen“)
- **Before:** every Anki menu selection used `HALF_REFRESH` (heavy full-ish flash).
- **Now:** menu uses the same cadence as cards — mostly **FAST**, `HALF` only every *N* paints (CrossPoint refresh setting).

### Card font sizes
| Setting | Old | New |
| --- | --- | --- |
| **Klein / Small** | 1× | **1×** (unchanged) |
| **Mittel / Medium** | 2× | **1.5×** (new step between old small & medium) |
| **Groß / Large** | 3× | **2×** (= old medium) |

Legacy configs migrate: old medium/large → new large (2×). Saved as `font_scale_scheme: 2`.

### Greek / romanization glyphs
- UI_12 font now includes **Latin Extended Additional** `U+1E00–U+1E9F` (e.g. **ṓ** U+1E53 used in Greek pronunciation), on top of modern Greek `U+0370–U+03FF` and polytonic `U+1F00–U+1FFF`.

## Highlights (EN) — still from v2.4.0

- **XFD** dialect, bold on device, multi-deck pull, Greek UI font

## Highlights (DE) — weiterhin aus v2.4.0

- XFD, Fett auf dem Gerät, Multi-Stapel, griechische UI-Schrift

## Install

1. Firmware neu bauen/flashen (`firmware/build.sh` → Bin auf X4)  
2. Add-on nur bei Bedarf aktualisieren (2.4.0 reicht für diese Änderung)  
3. Schriftgröße in Anki-Settings am Gerät einmal durchschalten (Klein → Mittel → Groß)
