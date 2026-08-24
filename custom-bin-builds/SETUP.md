# Setup Walkthrough

Flash the firmware → install a font (only needed for Chinese/CJK) → install the
Anki add-on → pair the device with Anki → daily use.

## 1. Flash the firmware

The file to flash is `crosspoint-1.6.0rc-xteink-anki-x4_x3.bin` in this folder.
One image serves both the X4 and the X3 — CrossPoint detects the board at
runtime.

1. Put the `.bin` somewhere handy on your computer.
2. Open <https://crosspointreader.com/#flash-tools> in Chrome or Edge (the web
   flasher needs WebSerial; Safari and Firefox do not support it).
3. Select your device — **X3** or **X4**.
4. Choose **Custom .bin** and upload the file.
5. Connect the reader over USB-C and start the flash. Keep the cable connected
   until it finishes.

**If the flasher cannot talk to the device,** it is probably still locked from
the factory. Run the unlock tool at
<https://crosspointreader.com/#unlock-tool> first, then flash again.

**Alternative — update from the SD card:** if the device already runs
CrossPoint, copy the `.bin` to the SD card and use **Settings → System →
Firmware from SD**. Keep power and the SD card connected during the update.

To confirm the flash worked, open **Anki** from the home menu — the header shows
`1.6.0rc-anki-2.5.7`.

**To go back to stock,** flash an official release from the same page.

## 2. Install a Chinese (CJK) font

Skip this section if your cards are Latin/Greek only.

Chinese is **not** in the firmware — it is served from an SD-card font. Note
that the built-in downloader (**Settings → System → Manage Fonts**) currently
offers no CJK family: every family in the official catalog is Latin, Cyrillic
and Greek only. So you convert one yourself.

### Convert a CJK font

You need the CrossPoint source checkout (`prepare.sh` leaves one in
`.firmware-build/`) and a CJK font file — Noto Sans SC, Source Han Sans, or any
`.ttf`/`.otf` with the coverage you need.

```bash
python3 lib/EpdFont/scripts/fontconvert_sdcard.py \
  NotoSansSC-Regular.otf \
  --intervals cjk \
  --sizes 8,10,12,14,16,18 \
  --style regular \
  --name NotoSansSC \
  --output-dir ./NotoSansSC/
```

The `cjk` preset covers roughly 22,000 codepoints. Generate a `bold` pass into
the same folder if you want bold card text to stay Chinese.

**Include every size in that list.** The sizes are not interchangeable: 8/10/12
back the user interface, 12–18 back the reader, and **18 is what Anki's
*Medium* card size uses**. A family missing 18 pt shows boxes on Medium while
Small and Large still work.

### Put it on the device

Either copy the folder to the SD card at `/.fonts/NotoSansSC/` (or `/fonts/…`
if you prefer a visible folder), or upload the `.cpfont` files through
**File Transfer → Fonts** in the web interface.

Then select it: **Settings → Reader → Font Family → NotoSansSC**. That single
choice also arms the CJK fallback for the interface and for Anki cards.

## 3. Install the Anki add-on

1. In Anki: **Tools → Add-ons → Install from file…**
2. Choose `anki-addon/xteink_sync.ankiaddon` from this repository.
3. Restart Anki.
4. Open **Tools → Xteink Status**. It shows the server address and the API
   token (generated on first run). Keep this window open — you need both in the
   next step.

The add-on serves on port **5050** and advertises itself over mDNS, so the
address looks like `http://192.168.1.23:5050`.

Anki must be running for the device to pull cards or push reviews. Both devices
must be on the same network.

## 4. Pair the device with Anki

Either on the device or through the web interface — the settings are the same.

**On the device:** **Anki → Anki settings**

| Setting | Value |
| --- | --- |
| Mac server URL | `http://192.168.1.23:5050` (from Xteink Status) |
| Find Mac server | Searches the network over mDNS instead of typing the URL |
| API token | From **Tools → Xteink Status** |
| Max cards / deck, Max cards total | 1–1000; sent with each pull |
| Card font | **UI (DE/Greek)** or **Reader / SD font** |
| Handedness, Font size, Orientation | Layout preferences |

**In the browser:** open **Data transfer → Join network** on the device, then
visit the address it shows (or `http://crosspoint.local/settings`) and fill in
the **Anki Offline Sync** section. The token is write-only — a saved token is
never sent back to the browser, and leaving the field blank keeps the current
one.

Your router may hand the computer a new IP over time; a DHCP reservation keeps
the URL stable.

### Which card font to pick

- **UI (DE/Greek)** — the built-in font. Latin, German, and modern plus
  polytonic Greek. With an SD CJK family selected, Chinese renders through the
  fallback at all three card sizes.
- **Reader / SD font** — cards use the same font as your books. Pick this if
  you want the CJK font itself to draw every card, or if Medium shows boxes
  because your family has no 18 pt file.

## 5. Daily use

**Anki menu on the device:**

1. **Download today's cards** — pulls every due top-level deck as NDJSON.
   Needs Wi-Fi and Anki open.
2. Pick a deck if more than one was loaded.
3. **Learn cards** — fully offline; turn Wi-Fi off if you like.
4. **Upload reviews** — when you are done and Anki is open again.

Reviews live on the SD card under `/.crosspoint/anki-*` and are only deleted
once Anki confirms the batch, so a failed upload loses nothing.

**While reviewing** (bottom buttons left→right = Back, Confirm, Left, Right;
top = the two side page buttons):

| Button | On the question | On the answer |
| --- | --- | --- |
| Top (either side button) | Flip to the answer | Up = **Again**, Down = **Good** |
| Bottom 1 (Back) | Leave the card, back to the deck menu | same |
| Bottom 2 (Confirm) | **Undo** the last grade, back one card | same |
| Bottom 3 (Left), short press | Toggle the red **flag** | same |
| Bottom 3 (Left), hold ~0.55 s | **Bury** — skip locally for today, no grade | same |
| Bottom 4 (Right) | Scroll down a long card | same |

Only **Again** and **Good** exist; Hard and Easy were dropped for this button
layout. The progress bar counts finished cards only — **Again** and buried
cards do not fill it. Buries are local and are discarded at the next pull.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| Boxes instead of Chinese on **Medium** only | The SD family has no 18 pt `.cpfont`. Regenerate with `--sizes 8,10,12,14,16,18`, or switch Card font to **Reader / SD font**. |
| Boxes at every card size | No SD font selected. **Settings → Reader → Font Family**. |
| "Cannot reach Anki" | Anki closed, different network, or the computer's IP changed. Use **Find Mac server**, or re-check the URL. |
| Web flasher does not see the device | Locked from the factory — run the unlock tool. Or a browser without WebSerial. |
| German text no longer hyphenates | Expected: this build drops the German hyphenation trie for flash. See the README. |
| No serif option under Font Family | Expected: NotoSerif was dropped for flash. SD families still work. |
