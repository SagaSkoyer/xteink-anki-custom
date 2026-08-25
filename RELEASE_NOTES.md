# v2.9.0 — keep studying offline: the batch comes back each day

## Firmware

A pulled batch was a single pass. Once you had walked each deck's queue to the
end, the device was done until the next pull — so a week away from Wi-Fi meant
one day of study and six idle days.

- **Cards resurface daily:** when the local calendar date moves on, every deck's
  queue is rebuilt from the cards the pull gave it, and you loop through the
  whole batch again. Uploading reviews ends the loop, as it always did — the
  next pull starts a fresh batch.
- Within a pass nothing changes: **Again** and **Hard** on a learning card
  re-queue exactly as before.
- **Every answer is kept.** Three days offline means three reviews per card in
  the push, not one. That is the point — Anki's scheduler and FSRS get the whole
  history rather than only your last verdict.
- **Reviews now carry the time they were given** (`answered_at`), read from the
  device's RTC. A Tuesday pass lands in Anki as Tuesday instead of collapsing
  into the moment you pushed. Nothing changes on a device whose clock has never
  been synced: the field stays empty and Anki applies at push time, exactly as
  before — and so does resurfacing, which stays switched off there.
- **Buried cards stay buried** for the rest of the batch, not just the current
  pass. They come back with the next pull.
- The Anki menu header shows which pass you are on once cards have resurfaced.
- **Local review log is capped at 4000 rows.** At the cap the device asks you to
  upload before starting another pass; grading the current pass still works.

Two supporting fixes this required:

- Each pass writes its own `system-answers/<batch>-pNN.ndjson`. The add-on's SD
  import keys its duplicate guard on the filename stem, so reusing one name
  across days would have made every pass after the first import a silent no-op.
- Undoing a review no longer reads the whole review log into memory to drop one
  line — with a multi-day log that was the largest allocation in the Anki path.

## Add-on

- `parse_answers_ndjson()` now keeps `answered_at`, so the SD-card import path
  backdates reviews the same way a network push does.
- SD import applies a batch's passes in pass order. Plain filename sorting put
  `<batch>-p01` ahead of `<batch>`, which would have replayed a card's reviews
  out of order.
- `max_reviews_per_push` 500 → 5000 and `max_request_bytes` 256 KB → 2 MB, sized
  for a batch reviewed over several days.

## Known limits

- Resurfacing needs the device RTC to be set (**Settings → Clock**, NTP sync
  over Wi-Fi). Without it the loop never starts and reviews carry no timestamp.
- The day boundary is local **midnight**, not Anki's 4am rollover. Crossing it
  mid-session is not disruptive: the new pass appears the next time you open
  Anki, never underneath the card you are looking at.
- Re-answering a card that Anki has already scheduled forward is an early
  review. Drilling a card daily for a week will land it on a different interval
  than leaving it alone would have — that is what asking for the loop means.

# v2.8.0 — wake straight back into the card you were on

## Firmware

Sleeping in the middle of a review (power button, or the auto-sleep timeout) and
waking up dropped you on the home menu, so every interruption cost two menu
levels — Home → Anki → Learn — before the card came back.

- **Resume review on wake:** if an Anki card was on screen when the device went
  to sleep, the wake opens that same card again instead of the home screen.
  The side is restored too: asleep on the answer, awake on the answer.
- Nothing is re-scheduled or re-drawn from scratch: the deck queue and its
  cursor already live in `anki-state.json`, so the resumed card *is* the card
  that was pending — the review timer simply restarts at the wake.
- **Escape hatch:** hold **Back** while waking to go to the home screen instead
  (same convention as the reader's resume). The resume flag is one-shot, so a
  reboot after a crash also lands on home.
- Sleeping anywhere else — Anki menu, deck list, settings, reader, home —
  behaves exactly as before.
- Flash required.

# v2.7.0 — fast card flips with an SD (CJK) font

## Firmware

Flipping front → back could take ~8 s with a CJK card font while back → next
card stayed under a second. Both directions run the same `renderCard()`, so the
asymmetry was never the side — it was that the back holds more text and the
renderer's cost grew far faster than linearly in it. Four changes, all in the
Anki card renderer:

- **Measurement no longer touches glyph bitmaps.** `baseTextWidth()` measured
  with `GfxRenderer::getTextWidth`, which goes through `getTextBounds` →
  `getGlyph`: every glyph missing from the SD font's resident arena cost a full
  `.cpfont` file open in `SdCardFont::onGlyphMiss`, cached in a ring of only
  eight. It now measures with `GfxRenderer::getTextAdvanceX`, which reads the
  advance-only table — a RAM binary search, no bitmaps, no SD. That is also the
  measure `drawText` lays out with, so wrapping and pen advance now agree
  exactly (it is advance width, not the ink bounding box).
- **The advance table is primed per card and accumulates over the deck.**
  `loadCurrentCard()` calls `ensureSdCardFontReady()` for both sides. The table
  is ~8 bytes per codepoint, is not subject to the arena's `MAX_PAGE_GLYPHS`
  cap, and survives `clearCache()`, so it converges over a session: one batched
  SD pass for a new script, nothing at all once the deck's characters are in.
  The lookup resolves the UI font's *fallback* id first — the CJK family is
  registered with `setFallbackFont`, so priming the raw card font id would
  quietly build nothing.
- **Line breaking is searched, not walked.** The wrap scan re-measured
  `lineStart..next` once per codepoint, so a line of L glyphs cost L
  measurements of O(L) each. Prefix width is monotonic, so the same predicate is
  now galloped and bisected: 2.5–4.7× fewer measurement calls and 2–4.8× fewer
  codepoints walked on a full card side, with identical break positions
  (verified against the old algorithm over ~40,000 randomized cases covering
  CJK, bold markers, table controls, tabs and Greek).
- **Bitmap prewarm is bounded to what is drawn.** A card is one screen with no
  paging, but the prewarm walked the whole side — so a long back paid a full SD
  pass, and spent its share of the arena's glyph budget, on text below the fold
  that is never rendered. Overshooting that budget is what drops the font back
  to per-glyph faulting. Bold is now warmed only when the visible text uses it.

No behaviour change for Latin cards on the built-in font, and no layout change
beyond sub-pixel differences from measuring advance width instead of the ink
box. Flash required.

# v2.6.0 — stripped-down review pane

## Firmware

- **No header on cards** — the review pane drops the progress bar, the
  `12/50 · 76%` stats line, the deck name and the answer-side front preview.
  A card is now just its text.
- **No paging** — text that does not fit is clipped at the bottom. The
  `Side buttons: pages` hint is gone (`STR_ANKI_SIDE_PAGES` removed).
- **Button 3 (Left):** flag toggle only. The ~0.55 s long-press-to-bury gesture
  and its hold timer are gone.
- **Button 4 (Right):** **Bury** (was: scroll) — skips the card for this
  session without grading it, exactly as the old long-press did.
- **Flag icon** moved to the bottom-right corner of the card, drawn only when
  the card is flagged.
- Progress is still tracked for the deck menu and sync; it is simply no longer
  drawn on the card.
- Flash required.

# v2.5.7 — flag gesture works on X4 hardware

## Firmware

- **Fix: Flag toggle broken** — Up+Down cannot be detected together (one ADC ladder).
- **New gestures:**
  - **Confirm + Up/Down** (chord), or
  - **Long-press Up or Down ~0.55 s** (short press pages on release)
- Flash required.

# v2.5.6 — firmware version in Anki menu

## Firmware

- **Version visible in Anki:** header subtitle on **Anki menu** and **Anki settings**
  (same pattern as CrossPoint Settings). Boot still shows it too.
- Release string: **`1.4.1-anki-2.5.7`** (`CROSSPOINT_VERSION` / `XTEINK_ANKI_FW_VERSION`).
- Flash required to see the label.

# v2.5.5 — flag placement landscape/portrait

## Firmware

- **Flag layout** (approved mocks):
  - **Landscape:** right of progress bar; flag top on bar bottom edge; above grades
  - **Portrait:** right column; bar + deck name shift left; flag bottom-aligned with status
- Flash required.

# v2.5.4 — flag chord Up+Down + progress without Again/Hard requeues

## Firmware

- **Flag-Chord:** **Hoch + Runter** gleichzeitig (statt Page+Down) → Rotflag 0↔1
- **Progress-Bar / Zähler:** nur Karten, die die Session verlassen (kein Requeue).
  **Nochmal** und **Schwer** auf Lernkarten werden **nicht** als Fortschritt gezählt.
- Flash required.

# v2.5.3 — accept pull protocol v3

## Firmware

- Fix: **Unsupported or invalid Anki batch** when add-on sends `protocol_version: 3`
  (flags release). Device now accepts pull meta **v2 and v3**.
- Flash required if you already installed add-on 2.5.x.

# v2.5.2 — offer mDNS search when Anki unreachable

## Firmware

- After **pull/push network failure**: dialog  
  **„Anki nicht erreichbar“** —  
  **Bestätigen** = Mac-Server per mDNS suchen und erneut versuchen;  
  **Abbrechen** = Anki läuft (URL/Token prüfen, Netzwerk-Hinweis).
- Shared helper `AnkiMdns::discoverServerUrl` (Settings + error path).
- Flash required.

# v2.5.1 — LAN mDNS discovery

## Add-on + Firmware

- Mac add-on advertises **`_xteink-anki._tcp`** on the configured **port** (default 5050)
  - macOS: `dns-sd -R`; optional `zeroconf` package elsewhere
  - Config: `mdns_enabled`, `mdns_name`, `port` — **token not published**
- X4 **Anki → Anki-Einstellungen → Mac-Server suchen**: mDNS browse → writes `http://IP:port`
- Token still entered manually (Auth)
- Flash firmware + reload add-on 2.5.1

# v2.5.0 — card flag toggle (Page + Down) + sync

## Firmware + Mac add-on (**breaks old CSV-only push clients**)

- **Chord:** side **Page** + **Down** together toggles Anki **red flag** (0 ↔ 1) on the current card
- **UI:** solid mini flag **right of the progress bar** (bar shortens; no white inner line)
- **Pull:** each card includes `"flag": 0–7` from Anki `card.flags`
- **Push:** JSON only — `{"batch_id","reviews":[…],"flags":[{"card_id","flag"}]}`
  - Flags-only upload allowed (empty `reviews`)
  - Menu **Upload** shows when reviews **or** dirty flags are pending
- Local dirty flags: `/.crosspoint/anki-flags.csv` (cleared on successful push / new pull)
- Protocol version **3**; add-on **2.5.0**
- Flash firmware + reinstall/reload add-on + re-pull cards

# v2.4.11 — vector figures (stem / stress / timeline)

## Firmware + Mac converter

- New **vector figures** next to tables (same `\x04…` family, 1px lines, stack-only):
  - **stem** — `[stem] + [ending]` → `[result]`
  - **stress** — syllable boxes with stress mark (`s=N`)
  - **timeline** — horizontal ticks + diamond marker (`m=N`) + optional event label
- Authoring (converted on pull):
  - `[fig:stem|λυ-|-ω|λύω]`
  - `[fig:stress:2|κα|λη|μέ|ρα]`
  - `[fig:timeline:1|Verg.|Jetzt|Zukunft|Aorist?]`
  - or fenced ` ```fig stem ` … ` ``` `
- API: `emit_fig_stem` / `emit_fig_stress` / `emit_fig_timeline` in `textutil.py`
- Flash firmware + reload add-on + re-pull cards.
- Binary: `dist/crosspoint-1.4.1-xteink-anki.bin`.

# v2.4.10 — 25px gap between card areas

## Firmware

- **Between new areas** (blank lines in card text: lemma↔memory, memory↔paradigm, …):
  fixed **25 px** advance on every font size (front & back).
- Text line pitch: at least 25 px, but never below font advance (no glyph overlap).
- Flash required. Re-pull cards after helper push so section blanks match layout.

# v2.4.9 — tight EN/DE front spacing

## Firmware + Helper

- Front no longer inserts a **blank row** between English and 2nd language — consecutive lines only.
- Medium/large: remaining empty lines (section gaps) use **~¼ line height**; text pad slightly tighter.
- Flash firmware + re-push cards (or re-export) so Front fields lose the old blank line.
- Preview: `dist/line-spacing-en-de-before-after.png`

# v2.4.8 — tighter blank lines for medium/large

## Firmware

- **Medium & large:** empty lines / section gaps use **0.5× line height** (not a full
  line slot that felt like ~1.5× / 2× of air). Small keeps full blank-line height.
- Text lines still use the font’s advance + a small pad (no glyph overlap).
- Binary: `dist/crosspoint-1.4.1-xteink-anki.bin` (flash required).

# v2.4.7 — vector line tables (low RAM)

## Firmware + Mac converter

- Compact tables (2–4 cols, ≤12 single-line rows) ship as a **vector table block**
  (`\x04table …` / cell sep `\x06`) instead of ASCII `+---+` boxes.
- X4 measures cells in **pixels** (proportional fonts / Greek) and draws **1 px**
  grid lines via existing `drawLine` — **no heap**, only `colW[4]` on the stack.
- Styles: **C** conjugation (internal verticals only), **H** header underline + box,
  **B** simple box. Wide tables still **stack** / compact on the Mac.
- Paging: mid-table row continue; whole table deferred to next page when it would
  leave a lonely strip at the bottom.
- **Flash** firmware + **reload add-on** + **re-pull** cards so new blocks are on device.
- Binary: `dist/crosspoint-1.4.1-xteink-anki.bin`.

# v2.4.6 — native medium font (UI_18) with Greek

## Firmware

- **Mittel** uses a new built-in **UI_18** (Ubuntu 18 px) with the same Greek +
  romanization coverage as UI_12 — drawn **native 1×**, not soft 1.5× upscale.
- Sizes (unchanged product intent):
  | Setting | Rendering |
  | --- | --- |
  | Klein | UI_12 @ **1×** |
  | Mittel | UI_18 @ **1×** (native ~1.5× of 12, sharp) |
  | Groß | UI_12 @ **2×** |
- Binary: `dist/crosspoint-1.4.1-xteink-anki.bin` (flash required).

# v2.4.5 — status strip joins multi-line Front as EN / DE (view only)

## Firmware

- Answer-side status strip: multi-line Front (`EN` + blank + `DE`) is shown as a
  **compact view** `EN / DE` (truncated). Display only — card **Back** data stays free of EN/DE.
- Binary: `dist/crosspoint-1.4.1-xteink-anki.bin` (flash required for the join).

# v2.4.4 — front prompt in status row (between progress and deck)

## Firmware

- Answer side: EN/L2 **front** is no longer a line *above* the bar.
- It sits **in the status row**: progress left · front (truncated, centered in middle) · deck name right.
- Same **UI_10** font as progress/deck. Simulated portrait + landscape before build.
- Binary: `dist/crosspoint-1.4.1-xteink-anki.bin` (flash required).

# v2.4.3 — ASCII box tables on pull (Mac converter)

## Add-on / `textutil` (no firmware flash required)

- Markdown/HTML tables convert to a clear **ASCII box** layout (`+`, `-`, `|`) so paradigms read as tables on the X4.
- Wide tables still **stack** as `Header: value` lines when they exceed the width budget.
- UI_12 has **no Unicode box-drawing** glyphs; ASCII is intentional and portable.
- Rebuild/reinstall the Anki add-on (or restart Anki so `textutil.py` reloads), then **pull** cards again.

# v2.4.2 — answer-side front preview in status strip

## Firmware

- **Answer side:** English / second-language **front** text is shown **centered** in the status band (above the progress bar), same **UI_10** font as the progress stats.
- Long fronts are **truncated** to the full status width (especially useful in **landscape**).
- Landscape uses **tighter top gaps** so the wide top area is used for the prompt while body lines stay usable.
- Layout simulated for portrait + landscape before rebuild (`scripts/simulate_anki_layout.py`).

## Markdown / XFD on the X4

Mac add-on converts XFD/Markdown → plain lines (+ bold markers, **vector table blocks** or stacked fallback) on `/pull`. The X4 does **not** parse Markdown; it draws converted text, bold runs (STX/ETX or `**` fallback), and 1 px table grids.


# v2.4.1 — softer Anki menu refresh + font sizes 1× / 1.5× / 2×

## Assets

| File | Purpose |
| --- | --- |
| `xteink_sync.ankiaddon` | Anki Desktop add-on **2.4.0** (unchanged) |
| `crosspoint-1.4.1-xteink-anki.bin` | Xteink X4 firmware (rebuild required) |
| `SHA256SUMS` | Checksums |

## Firmware changes

### Menu e-ink flash (DE: „Flashen“)
- **Before:** every Anki menu selection used `HALF_REFRESH` (heavy full-ish flash).
- **Now:** menu uses the same cadence as cards — mostly **FAST**, `HALF` only every *N* paints (CrossPoint refresh setting).

### Card font sizes
| Setting | Old | New |
| --- | --- | --- |
| **Klein / Small** | 1× | **1×** (unchanged) |
| **Mittel / Medium** | 2× | **1.5×** (new step between old small & medium) |
| **Groß / Large** | 3× | **2×** (= old medium) |

Legacy configs migrate: old medium/large → new large (2×). Saved as `font_scale_scheme: 2`.

### Greek / romanization glyphs
- UI_12 font now includes **Latin Extended Additional** `U+1E00–U+1E9F` (e.g. **ṓ** U+1E53 used in Greek pronunciation), on top of modern Greek `U+0370–U+03FF` and polytonic `U+1F00–U+1FFF`.

## Highlights (EN) — still from v2.4.0

- **XFD** dialect, bold on device, multi-deck pull, Greek UI font

## Highlights (DE) — weiterhin aus v2.4.0

- XFD, Fett auf dem Gerät, Multi-Stapel, griechische UI-Schrift

## Install

1. Firmware neu bauen/flashen (`firmware/build.sh` → Bin auf X4)  
2. Add-on nur bei Bedarf aktualisieren (2.4.0 reicht für diese Änderung)  
3. Schriftgröße in Anki-Settings am Gerät einmal durchschalten (Klein → Mittel → Groß)
