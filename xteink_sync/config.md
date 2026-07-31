# Xteink X4 Offline Sync

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
- `port`: TCP-Port des lokalen Dienstes.
- `max_cards`: maximale Anzahl Karten **pro fälligem Stapel** im täglichen
  Pull (Standard 250). Es werden alle fälligen Top-Level-Stapel geladen
  (nicht nur der in Anki gerade ausgewählte). Gesamtlimit über alle Stapel:
  1000 Karten.
- `max_text_chars`: maximale Textlänge pro Karten-Seite.
- `max_reviews_per_push`: maximale Anzahl Bewertungen in einem Push.
- `max_request_bytes`: maximale Größe eines Push-Requests.
- `operation_timeout_seconds`: Wartezeit auf Ankis Collection-Operationen.
- `sync_after_push`: startet nach erfolgreicher Übernahme den AnkiWeb-Sync.
- `allow_legacy_csv`: akzeptiert weiterhin das alte CSV-Format.
- `cors_allowed_origin`: `*` erlaubt den Zugriff aus dem Xteink-Web-Connect-
  Plugin. Für eine strengere Konfiguration kann hier dessen genauer Origin
  eingetragen werden.
- `processed_batch_ids`: wird intern für die Erkennung wiederholter Pushes
  verwendet. Die Liste wird automatisch begrenzt.

Änderungen an Netzwerkoptionen werden nach einem Neustart von Anki aktiv.
