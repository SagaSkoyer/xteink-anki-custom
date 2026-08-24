# Custom .bin Builds

Flashable CrossPoint firmware with the Xteink Anki functionality of this
repository, built on the **CrossPoint 1.6.0 beta RC** base for the **Xteink X4
and X3**.

| File | Description |
| --- | --- |
| `crosspoint-1.6.0rc-xteink-anki-x4_x3.bin` | Ready-to-flash firmware image (X4 + X3). |
| `patches/crosspoint-1.6.0rc-anki.patch` | The Anki patch against upstream tag `1.6.0rc`. |
| `prepare.sh` / `build.sh` | Reproduce the image from upstream sources. |
| `SHA256SUMS` | Checksums for the image and the patch. |

Upstream base: <https://github.com/crosspoint-reader/crosspoint-reader>

- Tag: `1.6.0rc` (the 1.6.0 beta RC line)
- Commit: `6a501bba544d9e80598811dbdf2134d1bcb1ebd2`
- Reported firmware version: `1.6.0rc-anki-2.5.7`

## Device compatibility

Upstream's `gh_release` environment compiles `FREEINK_DEVICE_X4` and
`FREEINK_DEVICE_X3` into a single ESP32-C3 binary and selects the board profile
at runtime, so **this one image covers both the X4 and the X3**. It uses the
CrossPoint 1.6 partition layout (`app0`/`app1`, 0x640000 each) and must not be
flashed over a firmware with a different layout.

The `sticky`, `x4pro`, and `papermono` targets are ESP32-S3 devices and need a
separate binary; they are out of scope for this build.

## Anki functionality

The full feature set of the 1.4.1-based build carries over — Anki entry in the
home menu, NDJSON deck pull, on-device deck selection, offline review with
persistent per-deck queues, undo and bury, flags, progress that counts only
completed cards, card font with German plus modern and polytonic Greek, font
size / orientation / handedness, per-deck and total card limits, mDNS server
discovery, and the web settings page under **Anki Offline Sync**.

Setup on the device and via `http://crosspoint.local/settings` is unchanged from
the 1.4.1 build; see `../firmware/README.md` for the walkthrough.

## Flashing

Easiest: choose the file as a **Custom .bin** in the official CrossPoint web
flasher. Alternatively copy it to the SD card and install it from
**Settings → Firmware from SD**. Keep power and the SD card connected for the
whole update.

## Building from source

Requires Git, Python 3.10+, and pioarduino/PlatformIO (`pio` on `PATH` or at
`~/.platformio/penv/bin/pio`).

```bash
./custom-bin-builds/build.sh
```

`prepare.sh` clones the pinned upstream tag into `.firmware-build/`, verifies the
commit, and applies the patch; `build.sh` then runs the `gh_release` environment
and verifies that the card fonts carry the required German/Greek/romanization
glyphs before copying the image here.

## Notes on the 1.4.1 → 1.6.0rc port

- Combining-mark placement became anchor-aware upstream
  (`combiningMark::anchorFor` / `anchorOver`); the Anki card renderer was ported
  to that API.
- Home-menu wiring, `silentRestartToAnki`, the `Anki` UI icon, and the i18n keys
  were re-merged against 1.6's restructured sources.
- The web settings page moved to a sequential async loader upstream; the Anki
  section hooks into it rather than the old fire-and-forget init.
- The UI fonts were **regenerated**, not text-merged: 1.6 added Arabic shaping
  coverage to `ubuntu_10/12`, so `ubuntu_12_{regular,bold}` are rebuilt with
  1.6's Ubuntu + Hebrew + Arabic + Vietnamese stack **plus** the Anki Greek
  (U+0370–03FF), polytonic (U+1F00–1FFF), and Latin Extended Additional
  (U+1E00–1E9F) ranges. `ubuntu_18_{regular,bold}` are new (the Anki card
  medium size) and deliberately skip the Arabic presentation forms — UI_18 is
  never used for menus, and those forms cost roughly 700 KB of flash the app
  partition cannot spare.
- Build footprint: RAM 16.8% (54,996 B static), Flash 78.5% (5,144,705 B of the
  6,553,600-byte app partition — about 1.34 MB free).
- Verified by rebuilding from a fresh clone with only the committed patch: same
  size and same flash figure, differing in 101 bytes of the ESP app descriptor
  (project name, build timestamp, and the trailing image digest), so the
  checksum in `SHA256SUMS` is the one for the committed image rather than a
  reproducible-build fingerprint.

## Deliberate removals

Two pieces of upstream content are left out to keep the app partition roomy;
both are reader-side features, and neither affects the Anki functionality.

- **NotoSerif reader family (all 16 faces, ~1.05 MB).** NotoSans is the only
  built-in reader family; the serif option is gone from the on-device font
  picker and the web settings. The `FONT_FAMILY` enum lost its `NOTOSERIF`
  member, so `BUILTIN_FONT_COUNT` and every SD-font index derived from it stay
  consistent, and a settings file that still names the serif family is clamped
  to NotoSans on load. SD-card font families are unaffected and are still
  offered after the built-in one.
- **German hyphenation trie (~206 KB).** By far the largest of the ten tries.
  German text still renders and wraps, it just is not hyphenated, so
  justified German columns have looser spacing. The other nine languages
  (en, fr, ru, es, it, pl, sv, uk, fi) are untouched.

To restore either one, revert its hunks in
`patches/crosspoint-1.6.0rc-anki.patch` and rebuild; the image returns to about
98% of the partition with both back in.

## Chinese and other CJK

CJK is **not** built into the firmware — CrossPoint 1.6 serves it from an
SD-card font family, which `SdCardFontSystem` registers as a size-matched
fallback for the built-in UI fonts. Upload a CJK family under **Fonts** in the
web UI.

All three Anki card sizes render CJK from that fallback:

- **Medium** (UI_18) is registered in the fallback table (`kUiFontSizes` in
  `src/SdCardFontSystem.cpp`), which upstream stops at 12 pt. The SD family must
  ship an 18 pt `.cpfont`; if it does not, the size is skipped and Medium falls
  back to missing glyphs while Small and Large still work.
- **Large** (UI_12 block-upscaled) resolves the fallback in the Anki card
  renderer's own glyph loop via `GfxRenderer::resolveTextFontId`, which this
  patch makes public for that caller. `getTextWidth` already resolved
  internally, so before the fix the layout reserved space for CJK glyphs the
  draw loop then dropped.
- Card text is prewarmed in both regular and bold, so a card costs one batched
  SD read per style instead of a file open per glyph on every repaint.

Setting **Anki → Anki settings → Card font → Reader / SD font** still works and
points cards straight at the SD family, bypassing the UI-font fallback entirely.
