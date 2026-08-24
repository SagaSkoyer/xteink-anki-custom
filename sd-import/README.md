# SD Card Import

Puts cards on the device without Wi-Fi, Anki, or the add-on running — write a
CSV, run one script, copy one file to the SD card.

This exists because pairing over Wi-Fi (mDNS discovery, matching subnets, VPN
interference — see the setup walkthrough) is sometimes more friction than it's
worth for a quick study session. This bypasses all of it.

| Folder | Contents |
| --- | --- |
| `input/cards.csv` | Your cards: `front,back[,deck]`. |
| `output/cards.ndjson` | Generated file — copy this to the SD card. |
| `build_cards.py` / `build.sh` | Converts the CSV to NDJSON. |

## Usage

1. Edit `input/cards.csv`. Columns are `front,back,deck` — `deck` is optional
   (defaults to "SD Import"); wrap a field in double quotes if it contains a
   comma or a newline.
2. Run `./sd-import/build.sh` (or `python3 sd-import/build_cards.py`). It
   writes `output/cards.ndjson` and fails loudly — before you copy anything —
   if a card would be rejected by the device (over the 1000-card limit, or a
   single card's JSON over 16 KB).
3. Copy `output/cards.ndjson` to the SD card as **`/Anki/cards.ndjson`** —
   inside an `Anki` folder at the SD card root, exact filename.
4. On the device: **Anki → Load today's cards from SD**.

Re-running the script after editing the CSV is safe to re-copy over — card ids
are derived from `(deck, front, back)`, so an unchanged row keeps the same id
across regenerations rather than appearing as a new card each time.

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
Use the add-on's own **eInk Reviews - Export to SD** (gear icon on any deck in
Anki's deck list) instead of this CSV workflow — see
`../anki-addon/README.md`. It writes real due cards straight from your
collection, so unlike the synthetic cards here, reviewing and later pushing
through a normal Wi-Fi sync grades the actual Anki cards.

## File format

`output/cards.ndjson` is one JSON object per line: a `meta` header, one `card`
line per row, then an `end` trailer — the exact wire format
`AnkiSyncClient::pull()` receives over HTTP (see
`xteink_sync/protocol.py::encode_pull_ndjson`), so
`AnkiStore::installFromSdImport()` on the device installs it through the
identical validation path (`installPulledBatch()`) a network pull uses. If you
want to generate this by hand or from another tool instead of the CSV script,
match that shape — the device applies the same checks either way (protocol
version 2 or 3, non-empty `pull_id`, card count under 1000, each line under
16 KB, `end.card_count` matching the number of `card` lines).
