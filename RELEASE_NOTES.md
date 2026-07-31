# v2.3.1 — Greek UI font default + limits on device & web

## Assets

| File | Purpose |
| --- | --- |
| `xteink_sync.ankiaddon` | Anki Desktop add-on **2.3.0+** (config merge fix) |
| `crosspoint-1.4.1-xteink-anki.bin` | Xteink X4 firmware (CrossPoint 1.4.1 + Anki) |
| `SHA256SUMS` | Checksums |

## Highlights (EN)

- **Card font (default):** UI font with German + modern/polytonic Greek (fixes missing Greek after 2.3.0)
- **Optional:** reader/SD font for other languages (web toggle or device **Kartenschrift**; upload under **Fonts**)
- **Max cards per deck / total** on web UI **and** device Anki settings (`?max_cards=&max_total=` on pull)
- Add-on: missing config keys (e.g. `max_total_cards`) are written so they appear in Anki Config

## Highlights (DE)

- **Kartenschrift standardmäßig:** UI-Schrift mit Deutsch + modernem/polytonischem Griechisch
- **Optional:** Reader-/SD-Schrift für andere Sprachen (Web-Schalter oder Anki-Einstellungen → Kartenschrift; Upload unter **Fonts**)
- **Max. Karten pro Stapel / gesamt** in der Web-UI **und** in den Geräte-Anki-Einstellungen
- Add-on: fehlende Config-Keys werden ergänzt und erscheinen unter Erweiterungen → Config

## Install (short)

1. `.ankiaddon` installieren → Anki neu starten → **Werkzeuge → Xteink Status**
2. `.bin` nur auf **X4 / CrossPoint 1.4.1** flashen
3. WLAN → `http://crosspoint.local/settings` → Anki-URL, Token, Kartenlimits, Kartenschrift
4. Für andere Schriften: **Fonts** hochladen und Reader-Schalter an
5. Menü **Anki** → laden → lernen → Bewertungen übertragen

## Not in this release

- Official CrossPoint upstream merge
- AnkiWeb store listing (install from file / GitHub)
- X3 or non-1.4.1 partition support
