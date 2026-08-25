# Xteink Offline Sync

Nach dem ersten Start erzeugt das Add-on automatisch einen zufälligen
`api_token`. Der Xteink muss ihn bei `/pull` und `/push` entweder als

```text
Authorization: Bearer <api_token>
```

oder als

```text
X-Xteink-Token: <api_token>
```

senden.

- `bind_address`: `0.0.0.0` macht den Dienst im lokalen Netzwerk erreichbar.
- `port`: TCP-Port des lokalen Dienstes (auch im mDNS-Record).
- `mdns_enabled`: `true` meldet den Server im LAN als `_xteink-anki._tcp`
  (macOS: `dns-sd`; sonst optional Python-Paket `zeroconf`). Der API-Token
  wird **nicht** veröffentlicht.
- `mdns_name`: Anzeigename der mDNS-Instanz (Standard: `Xteink Anki`).
- `max_cards`: Standard-Maximum **pro fälligem Stapel** (9999). Der X4 kann
  beim Pull mit `?max_cards=` überschreiben (Web-UI oder
  **Anki → Anki-Einstellungen → Max. Karten / Stapel**).
- `max_total_cards`: Standard-Gesamtlimit über alle Stapel (9999). X4 kann mit
  `?max_total=` überschreiben (**Max. Karten gesamt**). Harte Obergrenze 9999.
  Fehlt der Key in einer älteren Config, wird er beim Add-on-Start ergänzt.
- `max_text_chars`: maximale Textlänge pro Karten-Seite.
- `max_reviews_per_push`: maximale Anzahl Bewertungen in einem Push (Standard
  5000 - das Gerät legt jeden Tag ohne Sync eine weitere Runde über denselben
  Stapel, also enthält ein Push nach mehreren Tagen mehrere Bewertungen je Karte).
- `max_request_bytes`: maximale Größe eines Push-Requests (Standard 2 MB).
- `operation_timeout_seconds`: Wartezeit auf Ankis Collection-Operationen.
- `sync_after_push`: startet nach erfolgreicher Übernahme den AnkiWeb-Sync
  (auch nach Flag-Updates).
- `allow_legacy_csv`: optional altes Review-CSV (ohne Flags). X4 ab v2.5 sendet
  nur noch JSON: `reviews` + `flags` (`flag` 0–7, Gerät toggelt 0↔1).
- `cors_allowed_origin`: `*` erlaubt den Zugriff aus dem Xteink-Web-Connect-
  Plugin. Für eine strengere Konfiguration kann hier dessen genauer Origin
  eingetragen werden.
- `processed_batch_ids`: wird intern für die Erkennung wiederholter Pushes
  verwendet. Die Liste wird automatisch begrenzt.

Änderungen an Netzwerkoptionen werden nach einem Neustart von Anki aktiv.
