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
- Reported firmware version: `1.6.0rc-anki-2.9.1`

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

## Getting a fresh image without building it

`.github/workflows/firmware.yml` builds the image on every push, on every pull
request, and on demand (**Actions → Firmware → Run workflow**), so a flashable
image never requires a local toolchain. There are three ways to get one:

- **Newest build of the default branch** — always at this unchanging address:

  ```text
  https://github.com/SagaSkoyer/xteink-anki-custom/releases/download/latest/crosspoint-1.6.0rc-xteink-anki-x4_x3.bin
  ```

  Every commit on `poc` replaces the `latest` prerelease with a fresh build of
  that commit, alongside its `SHA256SUMS`. No Actions UI, no zip, no expiry —
  the link goes straight to the file. Release assets are readable by anyone who
  can read the repository, so while this repository is private the download
  needs a signed-in account with access; it becomes an open link if the
  repository is ever made public. It is marked prerelease, so the "Latest
  release" badge still points at the newest `v*` tag. Because each build embeds
  its own timestamp and image digest, the file behind this link changes on
  every commit even when no code changed.

- **A specific commit, including branches and pull requests** — the run's
  **Artifacts**, named `firmware-<commit sha>`. These always require a GitHub
  login, download as a zip, and expire after 90 days.

- **A fixed release** — pushing a `v*` tag builds that commit and attaches the
  `.bin` and `SHA256SUMS` to the matching GitHub Release, which never changes
  afterwards.

Both release paths need **Settings → Actions → General → Workflow permissions**
set to *Read and write*; without it the build still succeeds and the artifact
still appears, but publishing fails with a 403.

## Building from source

Requires Git, Python 3.10+, and pioarduino/PlatformIO (`pio` on `PATH` or at
`~/.platformio/penv/bin/pio`).

```bash
./custom-bin-builds/build.sh
```

`prepare.sh` keeps one checkout of the pinned upstream tag at
`.firmware-build/crosspoint-reader-1.6.0rc/`, resets it to the pinned commit,
and applies the patch. The reset preserves `.pio`, `.cache`, and any
`platformio.local.ini`, so editing the patch costs an incremental rebuild
instead of a fresh clone and a cold build; **anything else left in that tree is
discarded, so do not keep work there**. Passing a directory
(`./custom-bin-builds/build.sh path/to/tree`) applies the patch onto that tree
as-is and never resets it.

`build.sh` then runs the `gh_release` environment, verifies that the card fonts
carry the required German/Greek/romanization glyphs, copies the image here, and
regenerates `SHA256SUMS` for the image and the patch.

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
- Build footprint: RAM 16.8% (55,004 B static), Flash 78.6% (5,153,053 B of the
  6,553,600-byte app partition — about 1.34 MB free).
- Verified by rebuilding from a fresh clone with only the committed patch: same
  size and same flash figure, differing only in a handful of bytes in the ESP
  app descriptor (project name, build timestamp, and the trailing image
  digest), so the checksum in `SHA256SUMS` is the one for the committed image
  rather than a reproducible-build fingerprint.

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
- Glyph bitmaps are prewarmed in one batched SD read instead of a file open per
  glyph, bounded to the text that fits on screen (a card has no paging, so
  prewarming a long back's invisible tail only spent the resident arena's glyph
  budget), and bold is warmed only when the visible text actually uses it.
- Layout measurement does not read bitmaps at all: `loadCurrentCard` primes the
  SD family's persistent advance-only table (`SdCardFont::buildAdvanceTable`,
  ~8 bytes per codepoint, no `MAX_PAGE_GLYPHS` cap, survives `clearCache()`) and
  the card renderer measures through `GfxRenderer::getTextAdvanceX`. Before
  this, every width query walked `getTextBounds` → `getGlyph`, so any glyph the
  arena was missing cost a `.cpfont` open in `SdCardFont::onGlyphMiss` — with an
  8-entry overflow ring, a CJK back thrashed it on every flip.

Setting **Anki → Anki settings → Card font → Reader / SD font** still works and
points cards straight at the SD family, bypassing the UI-font fallback entirely.
