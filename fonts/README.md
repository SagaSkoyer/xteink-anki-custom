# Fonts

SD-card fonts for the CrossPoint 1.6 build in `../custom-bin-builds/`, built
with the firmware's own converter
(`lib/EpdFont/scripts/fontconvert_sdcard.py`) rather than by hand.

| Folder | Contents |
| --- | --- |
| `input/` | Source `.ttf`/`.otf` files, one per family/style. |
| `output/<Family>/` | Generated `.cpfont` files, ready to copy to the SD card or upload through the web UI. |
| `prepare.sh` | Clones the pinned CrossPoint checkout that owns the converter. |
| `build.sh` | Runs the converter against `input/` and writes `output/`. |

## NotoSansSC

`input/NotoSansSC-Regular.ttf` and `input/NotoSansSC-Bold.ttf` (Google's Noto
Sans SC) were converted into `output/NotoSansSC/` — six `.cpfont` files
(8/10/12/14/16/18 pt), 49.3 MB total, regular + bold at every size, 22,073
glyphs each.

### Why this covers both "default" and Chinese-simplified

The request was for one family that works as the **default** reader/UI font
*and* renders Chinese-simplified — not a CJK-only font that needs a second
family to fall back to for everything else. `build.sh` defaults to
`--intervals latin-ext,greek,cyrillic,cjk`:

- `latin-ext,greek,cyrillic` is the same coverage the pre-built catalog
  families ship (see any entry's `"scripts"` in the crosspoint-fonts
  manifest) — full Latin (incl. German), Greek, Cyrillic. This is what makes
  the family usable as the **default**: selected under **Settings → Reader →
  Font Family**, it renders ordinary book/UI text on its own, no fallback
  needed.
- `cjk` adds CJK Unified Ideographs + Hiragana/Katakana/Fullwidth
  (~22,000 codepoints) — the Chinese-simplified half.

Both matter together: per `docs/sd-card-fonts.md` ("CJK in the User
Interface"), CrossPoint routes CJK UI text (titles, file names, list rows) to
whichever SD family is *currently selected as the reader font* — there's no
separate "CJK font" slot. A CJK-only family would leave everything else
(status bar, menus, non-Chinese titles) without a matching Latin/Greek/
Cyrillic fallback of its own.

Verified against the actual glyph tables before building (`fontTools`
`cmap`): both `.ttf` files cover ASCII, German ß/ä, Greek α/ω, Cyrillic А, and
CJK/Hiragana/Katakana/Fullwidth — Noto Sans SC ships that range natively, so
nothing here is a guess.

All six sizes were generated deliberately — see the comment at the top of
`build.sh` for why each one matters (8/10/12 back the UI and the CJK
fallback for it, 18 specifically backs Anki's Medium card size).

### Installing on the device

Either:

- Copy `output/NotoSansSC/` to the SD card as `/.fonts/NotoSansSC/` (or
  `/fonts/NotoSansSC/`), or
- Upload the six `.cpfont` files through **File Transfer → Fonts** in the web
  UI.

Then select it: **Settings → Reader → Font Family → NotoSansSC**. See
`../custom-bin-builds/SETUP.md` for the full walkthrough (flashing, Anki
pairing, card font settings).

## Rebuilding / adding another family

```bash
# Convert input/<FamilyName>-{Regular,Bold,Italic,BoldItalic}.{ttf,otf}
./fonts/build.sh <FamilyName>

# Override coverage or sizes:
./fonts/build.sh <FamilyName> --intervals latin-ext,cjk --sizes 12,14,16,18
```

Drop new `.ttf`/`.otf` files into `input/` first, named
`<FamilyName>-Regular.ttf` (plus `-Bold`/`-Italic`/`-BoldItalic` as
available) — `build.sh` only converts styles that exist.
