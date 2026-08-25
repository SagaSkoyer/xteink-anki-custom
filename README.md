# Xteink ↔ Anki offline sync

**Offline Anki reviews on the [Xteink](https://xteink.com) e-ink reader (X3 tested)**, with scheduling and AnkiWeb sync still handled by Anki Desktop on your computer.

| Piece | Role |
| --- | --- |
| **Anki add-on** (`xteink_sync`) | Local LAN server: due cards out, reviews in, then normal AnkiWeb sync |
| **Firmware** (CrossPoint 1.4.1 patch) | Offline study UI: multi-deck, grades; DE/Greek UI font or reader/SD fonts |

> Community project — not an official Xteink or Anki product. Firmware is a **patch** on [CrossPoint](https://github.com/crosspoint-reader/crosspoint-reader) 1.4.1, not a full fork.

## Status (v2.4.0)

Working for daily use on Xteink (X3 tested) + Anki Desktop (macOS tested):

- Pull **all top-level decks with due cards** (not only the open deck)
- **Max cards per deck / total** on device web UI **and** device Anki settings (defaults 9999 / 9999)
- Deck select/switch on device, progress strip, landscape/portrait, handedness
- Grades: **Again · Hard · Good · Easy** (physical L→R)
- **Card font:** default UI font (German + modern/polytonic Greek); optional reader/SD font for other languages (**Fonts** page)
- Push reviews with batch id (safe retries); scheduler runs on the Mac
- **XFD converter** on pull: HTML/Markdown tables, lists, headings → e-ink plain text
- **Bold on e-ink (Phase B):** `**…**` / `<b>` → mixed bold/regular runs on the device
- **Sleep resumes the card:** waking from sleep during a review reopens that same card (hold **Back** while waking for the home screen)
- **Daily loop offline:** the pulled batch becomes due again each local day, so a week without Wi-Fi is a week of study (see **Daily loop** below)

Known limits of the offline model: learning steps after Again/Hard are re-queued **locally** on the device; final intervals always come from Anki’s scheduler after push.

### Daily loop

Without a sync, the device would otherwise run out of cards after one pass. So
each local day the whole pulled batch is made due again and you loop through it
once more:

- **Every card comes back**, however you graded it last time. Buried cards do
  not — they stay out until the next pull.
- **Every answer is kept and pushed.** Three days offline means three reviews
  per card reach Anki, each stamped with the day you actually gave it, so the
  scheduler and FSRS see the real history.
- **Uploading ends the loop** — the batch is cleared and the next pull starts a
  fresh one. The loop is what fills the gap *between* syncs.
- Needs the device clock: **Settings → Clock**, synced over Wi-Fi once. Without
  it nothing resurfaces and reviews carry no timestamp. The boundary is local
  midnight; a new pass never appears underneath the card you are looking at, only
  the next time you open Anki.
- The device holds up to 4000 local reviews; past that it asks you to upload
  before starting another pass.

Worth knowing: re-answering a card Anki has already scheduled forward is an
early review. Drilling a card daily for a week will leave it on a different
interval than letting it wait would have. That is the trade the loop makes.

## Quick start

### 1. Anki Desktop (Mac/Windows/Linux)

1. Download `xteink_sync.ankiaddon` from the [latest Release](https://github.com/jakovm/xteink-anki/releases/latest) (add-on **2.4.0+** recommended).
2. Anki → **Tools → Add-ons → Install from file…**
3. Restart Anki.
4. **Tools → Xteink Status** → note **LAN URL** and **API token**.
5. Allow Anki through the OS firewall for local network connections.

Optional config: **Tools → Add-ons → Xteink Offline Reviews → Config** (`max_cards`, port, …).

### 2. Xteink device

1. Download `crosspoint-1.4.1-xteink-anki.bin` from the same Release (check `SHA256SUMS`).
2. Flash **only** on a device with CrossPoint **1.4.1** layout (CrossPoint web flasher “Custom .bin”, or **Settings → Firmware from SD**).
3. On the device: **Data transfer → Join network**.
4. In a browser: `http://crosspoint.local/settings` → **Anki Offline Sync**
   - Mac server URL, e.g. `http://192.168.1.23:5050` — **or** on device:
     **Anki → Anki-Einstellungen → Mac-Server suchen** (mDNS `_xteink-anki._tcp`)
   - API token from Anki (**Tools → Xteink Status**; not auto-discovered)
   - Max cards per deck / total (sent on each pull)
   - Card font: leave **Use reader / SD font** off for Greek; turn on after uploading a font under **Fonts**
5. Home → **Anki** → load today’s cards, study, push reviews when back on Wi‑Fi.

With Anki open, the add-on advertises the LAN service on the configured `port`
(default 5050). Ensure Anki is allowed through the OS firewall.

Reserve a DHCP lease for the computer so the server IP stays stable.

Full firmware build/flash notes: [`firmware/README.md`](firmware/README.md).

## Data flow

```text
AnkiWeb ←→ Anki Desktop (scheduler) ←LAN→ Xteink (offline reviews)
                 │
                 ├─ GET  /pull   → due cards (JSON or NDJSON)
                 └─ POST /push   → review log (batch_id = pull_id)
```

The add-on does **not** write Anki’s SQLite directly. Collection access goes through Anki’s serialized ops; after a successful push it can trigger the normal AnkiWeb sync.

## E-ink flashcard dialect (XFD)

Anki cards are HTML on the desktop. The device has **no browser** and only draws **plain text lines** (plus optional bold for UI chrome). Full CommonMark or GFM would be wasted complexity and bad for short review sessions.

**XFD** (*Xteink Flashcard Dialect*) is a **small Markdown-inspired subset** aimed at grammar overviews and other structured cards—especially **tables**—that still fit a monochrome e-ink screen.

The **Mac-side converter** lives in `xteink_sync/textutil.py` (`to_device_text` / `plain_text`) and runs on every `/pull`. Write cards in this subset (or Anki HTML that maps to it); the device still only receives plain `front` / `back` strings—no Markdown parser on the device.

### Goals

| Goal | Implication |
| --- | --- |
| Readable paradigms | Small tables, short cells |
| Fast reviews | One idea per card; 1–2 screen pages max |
| Stable on ESP32 | No nested HTML, no images, no CSS |
| Grammar-first | Tables, lists, bold lemmas/endings beat prose |

### Supported syntax (authoring)

**Tier 1 — use freely**

| Construct | Markdown | On device (target) |
| --- | --- | --- |
| Paragraphs / line breaks | blank line, hard break | blank line / new line |
| **Bold** | `**lemma**` or `__lemma__` / `<b>` | STX/ETX markers in pull payload; device draws bold runs (also accepts raw `**…**`) |
| Unordered list | `- item` / `* item` | `• item` |
| Ordered list | `1. item` | `1. item` |
| Table | GFM pipe table, **2–4 columns** | **Vector grid** (`\x04table…`, 1px lines); wide → stacked |
| Figure | `[fig:stem|…]` / stress / timeline | **Vector fig** (`\x04fig t=…`, boxes + lines) |

**Tier 2 — optional**

| Construct | Markdown | On device (target) |
| --- | --- | --- |
| One title | `#` or `##` once at top | first line, slightly stronger |
| Inline code | `` `-ω, -εις` `` | monospaced if available, else `` `…` `` kept or plain |
| Block quote | `> tip` | `│ tip` or indented line |
| Separator | `---` | thin rule or blank + `────` |

**Not in XFD** (ignored or stripped): images, links as navigation, nested lists beyond one level, task lists, footnotes, HTML/CSS blocks, wide tables (>4 columns), long fenced code, YAML front matter.

### Tables (grammar)

Tables are the main reason XFD exists. Prefer **atomic paradigms**, not chapter dumps.

| Guideline | Recommendation |
| --- | --- |
| Columns | **2–4** (e.g. person × number, case × gender) |
| Cell length | ~1–2 words / ≤ ~12–20 characters |
| Header | first row = labels; first column may be row labels |
| Size that works | **2×3** ideal; **3×3** OK with short forms; **4×4** only with tiny cells |
| Card split | Sg on one card, Pl on another if it no longer fits one screen |
| Cloze-in-table | use `?` or Anki cloze in **one** cell; rest filled |

**Authoring example (Markdown → intended device layout):**

```markdown
## λύω — Present Active

|    | Sg     | Pl        |
| -- | ------ | --------- |
| 1  | λύω    | λύομεν    |
| 2  | λύεις  | λύετε     |
| 3  | λύει   | λύουσι(ν) |
```

**Figures (vector, no images):**

```text
[fig:stem|λυ-|-ω|λύω]
[fig:stress:2|κα|λη|μέ|ρα]
[fig:timeline:1|Verg.|Jetzt|Zukunft|Aorist?]
```

Or fenced: ` ```fig stem ` / `stress N` / `timeline N` with `|`-separated cells.

Target plain layout after conversion (ASCII box — UI_12 has no Unicode box glyphs):

```text
λύω — Present Active

+---+-------+----------+
|   | Sg    | Pl       |
+---+-------+----------+
| 1 | λύω   | λύομεν   |
| 2 | λύεις | λύετε    |
| 3 | λύει  | λύουσι(ν)|
+---+-------+----------+
```

**Card patterns that work well**

| Pattern | Front | Back |
| --- | --- | --- |
| Full paradigm | lemma + tense/voice label | small table |
| One form | “2 pl. pres. act. of λύω” | λύετε |
| Rule list | “Aorist passive marker?” | short `-` list |
| Contrast | “Imperfect vs aorist (aspect)” | 2-column mini table |
| Gap table | grid with one `?` | full cell + one-line hint |

### Converter (design)

The converter is the **Mac-side** step on pull (Anki add-on), not a second app on the device. Firmware stays a dumb line renderer until optional bold spans exist.

```text
Anki note / template
        │
        ▼
  render HTML (or raw field text)
        │
        ▼
  XFD converter  ──  xteink_sync (textutil + helpers)
        │
        ├─ strip scripts/styles/media noise
        ├─ map HTML structure → XFD constructs
        ├─ parse pipe tables / list-ish HTML
        ├─ layout tables to fixed columns
        ├─ bold/code → markers or plain
        └─ clamp length (max_text_chars)
        │
        ▼
  front / back strings in /pull JSON|NDJSON
        │
        ▼
  device draws wrapped lines
```

**Inputs the converter should accept**

1. **Normal Anki HTML** from `render_output` / templates (`<table>`, `<ul>`, `<b>`, `<p>`, …).  
2. **XFD-ish Markdown in fields** if the note stores Markdown (or a Markdown add-on left raw source)—detect pipe tables and `**bold**` when tags are absent.  
3. **Already plain text** with manual spacing—pass through with light cleanup.

**HTML → XFD mapping (core)**

| HTML | XFD / device text |
| --- | --- |
| `<p>`, `<div>`, `<br>` | paragraph / newline |
| `<b>`, `<strong>`, `<h1>`–`<h2>` | bold / title line |
| `<ul><li>` | `• …` |
| `<ol><li>` | `1. …` |
| `<table>` | column-aligned block + header rule |
| `<blockquote>` | `│ …` |
| `<code>`, `<tt>` | inline code treatment |
| `<img>` | `[alt]` or `[Bild]` (unchanged policy) |
| `<a href>` | link text only |
| nested junk | flatten one level; drop deeper chrome |

**Table layout algorithm (planned)**

1. Read header + body rows; drop empty trailing columns.  
2. If **>4 columns**, either split logically (if row labels suggest it) or fall back to **stacked lines** `Col: value` so nothing is silently cropped.  
3. Measure display width budget (portrait/landscape safe area, card font metrics later; v1: character budget, e.g. ~32–42 cols portrait).  
4. Pad cells; insert header underline (`────` / spaces).  
5. Prefer **row labels in column 0**; align numeric/short form columns to the left for mixed scripts (Greek + Latin).  
6. If the block still exceeds vertical budget, keep the table intact and let the existing **card pager** scroll—do not reflow mid-row.

**Bold and emphasis (Phase B — implemented)**

- Converter turns `**…**`, `__…__`, `<b>`, `<strong>` into zero-width markers **STX** (`U+0002`) / **ETX** (`U+0003`) inside `front`/`back`.  
- Device `drawTextPage` measures and paints **mixed regular/bold runs** (word-wrap aware).  
- Fallback on device: unpaired visible `**` toggles bold (for raw Markdown that skipped conversion).  
- Older firmware may show nothing or odd glyphs for STX/ETX — flash a bin that includes Phase B. Add-on-only update still keeps tables/lists readable.

**Where it lives in the repo**

| Piece | Role |
| --- | --- |
| `xteink_sync/textutil.py` | pure conversion (unit-tested, no `aqt`) |
| `xteink_sync/__init__.py` | call converter after Anki render on `/pull` |
| `tests/test_textutil.py` | dialect fixtures: tables, lists, Greek, overflow |
| Firmware | optional later: bold spans only; **no** full Markdown parser on device |

**Non-goals of the converter**

- Pixel-perfect CSS or Anki card themes  
- Shipping images or audio to the device  
- Round-trip editing of Markdown on the device  
- Guaranteeing huge “cheat sheet” notes—authors should split cards  

**Status:** dialect + converter **implemented** in `textutil` (tables, lists, headings, quotes, bold markers). Phase B bold drawing **implemented** in the firmware patch (`AnkiActivity::drawTextPage`).

### Author checklist

- [ ] One paradigm or rule per card  
- [ ] Table ≤ 4 columns, short cells  
- [ ] Fits roughly 1–2 e-ink pages  
- [ ] Front asks something; back is the table/list—not a textbook  
- [ ] No essential info only in images  

## HTTP API (summary)

Base URL: `http://<PC-IP>:5050`

| Endpoint | Auth | Purpose |
| --- | --- | --- |
| `GET /health` | no | Liveness |
| `GET /pull` | token | Due cards (`Accept: application/x-ndjson` for streaming) |
| `POST /push` | token | Reviews JSON or CSV |

Auth header: `Authorization: Bearer <token>` or `X-Xteink-Token: <token>`.

Ease values: `1=Again`, `2=Hard`, `3=Good`, `4=Easy`. Details and examples: see the German long-form API section below or the release notes.

## Repository layout

```text
xteink_sync/     Anki add-on source (pull/push; textutil = XFD converter)
firmware/        Patch + build scripts against CrossPoint 1.4.1
dist/            Prebuilt .ankiaddon + .bin + SHA256SUMS
tests/           Protocol / textutil (XFD) unit tests
scripts/         Layout helpers
```

Card content contract for grammar-style notes: **[E-ink flashcard dialect (XFD)](#e-ink-flashcard-dialect-xfd)**.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile xteink_sync/*.py

# Rebuild add-on package
rm -f dist/xteink_sync.ankiaddon
( cd xteink_sync && zip -r ../dist/xteink_sync.ankiaddon \
    __init__.py config.json config.md manifest.json \
    protocol.py textutil.py user_files )

# Rebuild firmware (needs PlatformIO / pioarduino)
./firmware/build.sh
```

## Sharing with Anki & Xteink communities

- **Anki users:** install the add-on only; any compatible client could use the HTTP API.
- **Xteink / CrossPoint:** use the release binary or rebuild from the patch; please report issues against *this* repo first, not upstream CrossPoint, unless the bug is in base CrossPoint.

Upstream merge into official CrossPoint is **not** assumed — this stays a community patch unless maintainers want it.

## License

MIT — see [`LICENSE`](LICENSE). CrossPoint upstream is MIT; Anki itself is AGPL-3.0 (runtime dependency of the add-on).

## Security

LAN-only, token-protected. See [`SECURITY.md`](SECURITY.md).
