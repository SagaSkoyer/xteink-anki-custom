# Anki Add-on

The Anki Desktop side of the Xteink offline sync — the counterpart to the
firmware in `../custom-bin-builds/`. This is the same kind of artifact published
on the upstream release page:
<https://github.com/jakovm/xteink-anki/releases/tag/v2.4.0>

| File | Description |
| --- | --- |
| `xteink_sync.ankiaddon` | Installable add-on package (version **2.5.1**). |
| `build.sh` | Rebuild the package from `../xteink_sync/`. |
| `SHA256SUMS` | Checksum for the package. |

Built from this repository's `xteink_sync/` source rather than copied from the
upstream release, so it matches the firmware here. It is newer than the linked
v2.4.0 release: the source tree is at add-on version **2.5.1**.

> The older `../dist/xteink_sync.ankiaddon` is stale — its `textutil.py` predates
> the current source. Use this package instead.

## Installing

1. In Anki: **Tools → Add-ons → Install from file…**
2. Pick `xteink_sync.ankiaddon`.
3. Restart Anki.
4. Read the API token from **Tools → Xteink Status** and enter it on the device
   (**Anki → Anki settings**) or in the CrossPoint web settings under
   **Anki Offline Sync**, together with the Mac server URL
   (for example `http://192.168.1.23:5050`).

Both machines must be on the same network, and Anki must be running for the
device to pull cards or push reviews.

## Exporting a deck without Wi-Fi

Click the gear icon next to any deck on Anki's deck list → **eInk Reviews -
Export to SD**. Pick a save location and it writes that deck's (and its
subdecks') due cards to an `.ndjson` file — the same wire format and the same
card-collection logic (`_collect_due_cards`) a device's normal "Download
today's cards" pull uses, just written to a file you choose instead of served
over HTTP. No network pairing needed on either side.

Copy the result to the SD card as `/Anki/cards.ndjson` and use **Anki → Load
today's cards from SD** on the device (see `../custom-bin-builds/SETUP.md` and
`../sd-import/`). Note that cards exported this way still come from your real
Anki collection, so — unlike the CSV-based cards `sd-import/` builds —
reviewing them and later pushing reviews back through a normal Wi-Fi sync
*does* grade the real Anki cards, since the ids match.

## Contents

`__init__.py`, `protocol.py`, `textutil.py`, `mdns_advertise.py`,
`config.json`, `config.md`, `manifest.json`, and `user_files/`.

## Rebuilding

```bash
./anki-addon/build.sh
```

The script compiles the sources, runs the repository's unit tests, and repacks
the archive.
