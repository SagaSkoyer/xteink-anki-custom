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

## Full offline sync: Tools → eInk (local)

No Wi-Fi pairing at all — plug the SD card into a reader and this reads/
writes its `system-due/` and `system-answers/` folders directly. In Anki:
**Tools → eInk (local)**.

**Export tab** — pick the SD card's mount point as the parent folder (e.g.
`/Volumes/SDCARD` on a Mac), check the decks you want, click **Export**. It
writes the checked decks' (+ subdecks') due cards into `<parent>/system-due/`
as a timestamped `.ndjson` file — the same wire format and the same
card-collection logic (`_collect_due_cards`) a device's normal "Download
today's cards" pull uses. On the device: **Anki → Load today's cards from
SD** picks up the newest file there and deletes it once installed.

**Import tab** — same parent folder, click **Import**. As you review on the
device, it appends one line per graded review or flag toggle into
`<parent>/system-answers/<batch-id>.ndjson` (`AnkiStore::appendAnswerEvent()`
in the firmware). Import reads every file there and applies it to your real
Anki collection through `apply_reviews()` — the exact same grading logic a
normal Wi-Fi "Upload reviews" push uses, just sourced from the SD card
instead of an HTTP request. Each file is deleted once successfully applied,
so re-running Import does not re-grade anything; a file that fails to parse
or was already processed is left in place rather than silently dropped.

Because the export carries real Anki card ids (not synthetic ones — see
`../sd-import/` for the CSV-based alternative that doesn't), reviewing these
cards and running Import *does* grade the real cards in your collection —
this is a genuine offline round trip, no network required on either side.

## Contents

`__init__.py`, `local_sync_dialog.py`, `protocol.py`, `textutil.py`,
`mdns_advertise.py`, `config.json`, `config.md`, `manifest.json`, and
`user_files/`.

## Rebuilding

```bash
./anki-addon/build.sh
```

The script compiles the sources, runs the repository's unit tests, and repacks
the archive.
