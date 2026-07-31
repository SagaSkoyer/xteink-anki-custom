# Xteink X4 ↔ Anki offline sync

**Offline Anki reviews on the [Xteink X4](https://xteink.com) e-ink reader**, with scheduling and AnkiWeb sync still handled by Anki Desktop on your computer.

| Piece | Role |
| --- | --- |
| **Anki add-on** (`xteink_sync`) | Local LAN server: due cards out, reviews in, then normal AnkiWeb sync |
| **X4 firmware** (CrossPoint 1.4.1 patch) | Offline study UI: multi-deck, grades; DE/Greek UI font or reader/SD fonts |

> Community project — not an official Xteink or Anki product. Firmware is a **patch** on [CrossPoint](https://github.com/crosspoint-reader/crosspoint-reader) 1.4.1, not a full fork.

## Status (v2.3.2)

Working for daily use on X4 + Anki Desktop (macOS tested):

- Pull **all top-level decks with due cards** (not only the open deck)
- **Max cards per deck / total** on X4 web UI **and** device Anki settings (defaults 250 / 1000)
- Deck select/switch on device, progress strip, landscape/portrait, handedness
- Grades: **Again · Hard · Good · Easy** (physical L→R)
- **Card font:** default UI font (German + modern/polytonic Greek); optional reader/SD font for other languages (**Fonts** page)
- Push reviews with batch id (safe retries); scheduler runs on the Mac

Known limits of the offline model: learning steps after Again/Hard are re-queued **locally** on the X4; final intervals always come from Anki’s scheduler after push.

## Quick start

### 1. Anki Desktop (Mac/Windows/Linux)

1. Download `xteink_sync.ankiaddon` from the [latest Release](https://github.com/jakovm/xteink-anki/releases/latest) (add-on **2.3.1+** recommended).
2. Anki → **Tools → Add-ons → Install from file…**
3. Restart Anki.
4. **Tools → Xteink Status** → note **LAN URL** and **API token**.
5. Allow Anki through the OS firewall for local network connections.

Optional config: **Tools → Add-ons → Xteink X4 E-Ink Offline Sync → Config** (`max_cards`, port, …).

### 2. Xteink X4

1. Download `crosspoint-1.4.1-xteink-anki.bin` from the same Release (check `SHA256SUMS`).
2. Flash **only** on an X4 with CrossPoint **1.4.1** layout (CrossPoint web flasher “Custom .bin”, or **Settings → Firmware from SD**).
3. On the device: **Data transfer → Join network**.
4. In a browser: `http://crosspoint.local/settings` → **Anki Offline Sync**
   - Mac server URL, e.g. `http://192.168.1.23:5050`
   - API token from Anki
   - Max cards per deck / total (sent on each pull)
   - Card font: leave **Use reader / SD font** off for Greek; turn on after uploading a font under **Fonts**
5. Home → **Anki** → load today’s cards, study, push reviews when back on Wi‑Fi.

Reserve a DHCP lease for the computer so the server IP stays stable.

Full firmware build/flash notes: [`firmware/README.md`](firmware/README.md).

## Data flow

```text
AnkiWeb ←→ Anki Desktop (scheduler) ←LAN→ Xteink X4 (offline reviews)
                 │
                 ├─ GET  /pull   → due cards (JSON or NDJSON)
                 └─ POST /push   → review log (batch_id = pull_id)
```

The add-on does **not** write Anki’s SQLite directly. Collection access goes through Anki’s serialized ops; after a successful push it can trigger the normal AnkiWeb sync.

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
xteink_sync/     Anki add-on source
firmware/        Patch + build scripts against CrossPoint 1.4.1
dist/            Prebuilt .ankiaddon + .bin + SHA256SUMS
tests/           Protocol / textutil unit tests
scripts/         Layout helpers
```

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

---

## Kurzanleitung (Deutsch)

### Anki am Rechner

1. `xteink_sync.ankiaddon` aus dem [Release](https://github.com/jakovm/xteink-anki/releases/latest) installieren (**2.3.1+** empfohlen).
2. Anki neu starten → **Werkzeuge → Xteink Status** → LAN-Adresse und API-Token notieren.
3. Optional unter **Werkzeuge → Erweiterungen → Config**: `max_cards`, `max_total_cards`, Port, …

### Xteink X4

1. Firmware-Bin flashen (nur X4 / CrossPoint **1.4.1**).
2. **Datentransfer → Netzwerk beitreten** → im Browser `http://crosspoint.local/settings`.
3. Unter **Anki Offline Sync**:
   - Mac-Server-URL und API-Token
   - **Max. Karten pro Stapel** / **gesamt**
   - Kartenschrift: für Griechisch den Reader-Schalter **aus** lassen
4. Für andere Sprachen: **Fonts** hochladen → Schrift wählen → **Use reader / SD font** an.
5. Am Gerät: **Anki** → heutige Karten laden → lernen → Bewertungen übertragen.

Am Gerät unter **Anki → Anki-Einstellungen** ebenfalls: Server, Token, Max-Karten, **Kartenschrift** (UI DE/Griechisch oder Reader/SD).

Details zum Bauen/Flashen: [`firmware/README.md`](firmware/README.md) (Deutsch).

---

## API details (DE / long form)

### Status

```http
GET /health
```

### Tageskarten laden

Optional Query: `?max_cards=250&max_total=1000` (vom X4 gesetzt; Grenzen 1–1000).

```http
GET /pull
Authorization: Bearer <API-TOKEN>
```

JSON-Beispiel:

```json
{
  "status": "success",
  "protocol_version": 2,
  "pull_id": "e6b4f2c58b954f77956792816ca17db3",
  "server_time": 1785349777,
  "decks": [
    {"id": "1512345678901", "name": "Greek", "card_count": 1}
  ],
  "cards": [
    {
      "id": "1700000000000",
      "front": "Question",
      "back": "Answer",
      "card_type": "review",
      "is_learning": false,
      "queue": 2,
      "reps": 12,
      "mod": 1785300000,
      "deck_id": "1512345678901",
      "deck_name": "Greek"
    }
  ]
}
```

Mit `Accept: application/x-ndjson` streamt der Server Kopfzeile, eine JSON-Zeile pro Karte und eine Abschlusszeile (ESP32-C3-freundlich).

### Bewertungen zurücksenden

```http
POST /push
Authorization: Bearer <API-TOKEN>
Content-Type: application/json

{
  "batch_id": "<pull_id>",
  "reviews": [
    {
      "card_id": "1700000000000",
      "ease": 3,
      "answered_at_ms": 1785391200123,
      "duration_ms": 4200
    }
  ]
}
```

`batch_id` macht Retries sicher (`duplicate` wenn schon verarbeitet). CSV bleibt kompatibel; optional `X-Xteink-Batch-ID`.

### Offline-Grenze

Ein morgendlicher Snapshot kennt Lernschritte nach Again/Hard nicht vollständig. Der X4 plant lokal nach und protokolliert mehrfach; die endgültige Terminierung macht immer Anki auf dem Rechner.
