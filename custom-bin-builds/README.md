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
- **Flash headroom is tight:** the image uses 98.1% of the 6,553,600-byte app
  partition (about 122 KB free). It flashes and OTA-updates fine, but further
  additions to this build will need font or feature trimming.
- Build footprint: RAM 16.8% (55,164 B static), Flash 98.1% (6,431,569 B).
