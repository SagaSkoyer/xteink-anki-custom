# SD Card Import

Puts cards on the device without Wi-Fi, Anki, or the add-on running — write a
CSV, run one script, copy one file to the SD card.

This exists because pairing over Wi-Fi (mDNS discovery, matching subnets, VPN
interference — see the setup walkthrough) is sometimes more friction than it's
worth for a quick study session. This bypasses all of it.

| Folder | Contents |
| --- | --- |
| `input/cards.csv` | Your cards: `front,back[,deck]`. |
| `output/*.ndjson` | Generated file(s), timestamp-prefixed — copy the newest to the SD card. |
| `build_cards.py` / `build.sh` | Converts the CSV to NDJSON. |

## Usage

1. Edit `input/cards.csv`. Columns are `front,back,deck` — `deck` is optional
   (defaults to "SD Import"); wrap a field in double quotes if it contains a
   comma or a newline.
2. Run `./sd-import/build.sh` (or `python3 sd-import/build_cards.py`). It
   writes a new `output/<timestamp>-cards.ndjson` and fails loudly — before
   you copy anything — if a card would be rejected by the device (over the
   1000-card limit, or a single card's JSON over 16 KB).
3. Copy that file into **`system-due/`** at the SD card root (create the
   folder if it doesn't exist yet — the device also creates it automatically
   the first time you open the Anki menu).
4. On the device: **Anki → Load today's cards from SD**. It reads the
   lexicographically newest `*.ndjson` in `system-due/` — the timestamp
   prefix is what makes "newest filename" mean "most recent export" — and
   deletes it once installed, so old exports don't pile up on the card.

Re-running the script after editing the CSV keeps the same card ids across
regenerations (derived from `(deck, front, back)`), so an unchanged row never
looks like a new card — only the filename (and therefore "which export is
current") changes each run.

## What this is not

**These cards are not linked to your Anki collection.** They didn't come from
a `.apkg` import or a real Anki sync, so Anki has no note to update for them.

- Reviewing them on the device works normally — progress bar, flag, bury,
  undo all behave exactly as with a normal pull.
- **"Upload reviews" cannot sync that grading anywhere.** The add-on looks up
  each reviewed card by id in your Anki collection to grade it; an SD-import
  id was never created there, so the add-on rejects that review individually
  (visible as a partial-sync result) rather than updating anything. Nothing
  breaks, but nothing round-trips either.

Use this for offline flashcards, quizzes, or notes you don't need graded in
Anki — not as a substitute for pairing when you actually want spaced
repetition against your real Anki deck.

**Want real Anki cards on the SD card instead, with grading that syncs back?**
Use the add-on's own **Tools → eInk (local) → Export** instead of this CSV
workflow — see `../anki-addon/README.md`. It writes real due cards straight
from your collection into the same `system-due/` folder, and its **Import**
tab reads graded results back out of `system-answers/` into the real Anki
collection — a full offline round trip, unlike the synthetic cards here which
can only ever be graded locally.

## File format

Each `output/*.ndjson` file is one JSON object per line: a `meta` header, one
`card` line per row, then an `end` trailer — the exact wire format
`AnkiSyncClient::pull()` receives over HTTP (see
`xteink_sync/protocol.py::encode_pull_ndjson`), so
`AnkiStore::installFromSdImport()` on the device installs it through the
identical validation path (`installPulledBatch()`) a network pull uses. If you
want to generate this by hand or from another tool instead of the CSV script,
match that shape — the device applies the same checks either way (protocol
version 2 or 3, non-empty `pull_id`, card count under 1000, each line under
16 KB, `end.card_count` matching the number of `card` lines) — and name the
file so it sorts after any other file already in `system-due/`, since the
device picks the lexicographically newest `*.ndjson` there.
