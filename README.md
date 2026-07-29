# Xteink X4 ↔ Anki Offline Sync

Dieses Projekt enthält ein Anki-Desktop-Add-on, das den Mac als Scheduler und
AnkiWeb-Sync-Instanz nutzt. Der Xteink X4 lädt morgens einen begrenzten
Tagesstapel, lernt offline und sendet anschließend sein Bewertungsprotokoll an
den Mac zurück.

## Datenfluss

1. Anki auf dem Mac synchronisiert sich mit AnkiWeb.
2. Der X4 ruft `GET /pull` ab und speichert die Karten sowie `pull_id`.
3. Der X4 lernt offline und protokolliert jede Bewertung in Reihenfolge.
4. Der X4 sendet die Bewertungen mit `POST /push` zurück. `pull_id` wird dabei
   als `batch_id` verwendet.
5. Das Add-on übernimmt die Bewertungen über Ankís Scheduler und stößt danach
   den normalen AnkiWeb-Sync an.

Das Add-on greift nicht direkt schreibend auf SQLite zu. Collection-Zugriffe
laufen über Ankís serialisierte Hintergrundoperationen.

## Installation auf dem Mac

Die fertige Datei `dist/xteink_sync.ankiaddon` in Anki über
**Werkzeuge → Erweiterungen → Aus Datei installieren** installieren und Anki
neu starten.

Danach unter **Werkzeuge → Xteink Status** die LAN-Adresse und den automatisch
generierten API-Token ablesen. Der Mac und der X4 müssen einander im lokalen
Netz erreichen können; die macOS-Firewall muss eingehende Verbindungen für
Anki erlauben.

Die Konfiguration kann unter **Werkzeuge → Erweiterungen → Xteink X4 E-Ink
Offline Sync → Konfiguration** geändert werden.

## Installation auf dem X4

Für CrossPoint 1.4.1 liegt die gebaute X4-Firmware unter
`dist/crosspoint-1.4.1-xteink-anki.bin`. Nach dem Flashen erscheint **Anki**
als eigener Punkt im CrossPoint-Hauptmenü. Serveradresse und API-Token werden
bequem über **Datentransfer → Netzwerk beitreten** und anschließend
`http://crosspoint.local/settings` eingetragen. Die Eingabe direkt am X4 bleibt
als Alternative erhalten.

Die Verbindungseinstellungen bleiben auf der SD-Karte gespeichert. Damit sich
die IP-Adresse des Macs nicht durch DHCP ändert, sollte sie im Router für den
Mac reserviert werden.

Der vollständige, reproduzierbare Build- und Flash-Ablauf steht in
[`firmware/README.md`](firmware/README.md). Das Firmware-Binary ist nur für den
Xteink X4 auf Basis von CrossPoint 1.4.1 vorgesehen.

## HTTP-API

Standardadresse: `http://<MAC-IP>:5050`

Geschützte Endpunkte erwarten einen der folgenden Header:

```http
Authorization: Bearer <API-TOKEN>
```

oder:

```http
X-Xteink-Token: <API-TOKEN>
```

### Status

```http
GET /health
```

Dieser Endpunkt benötigt keinen Token und liefert nur Dienst- und
Bereitschaftsinformationen.

### Tageskarten laden

```http
GET /pull
Authorization: Bearer <API-TOKEN>
```

Beispielantwort:

```json
{
  "status": "success",
  "protocol_version": 2,
  "pull_id": "e6b4f2c58b954f77956792816ca17db3",
  "server_time": 1785349777,
  "cards": [
    {
      "id": "1700000000000",
      "front": "Question",
      "back": "Answer",
      "card_type": "review",
      "is_learning": false,
      "queue": 2,
      "reps": 12,
      "mod": 1785300000
    }
  ]
}
```

Der X4 fordert denselben Endpunkt mit
`Accept: application/x-ndjson` an. Dann wird der Stapel als Kopfzeile, eine
JSON-Zeile pro Karte und eine Abschlusszeile übertragen. Dadurch kann die
Firmware die Antwort direkt auf die SD-Karte streamen, ohne den gesamten
Tagesstapel im knappen ESP32-C3-Arbeitsspeicher zu halten. Andere Clients
erhalten weiterhin unverändert die JSON-Antwort oben.

Die Auswahl stammt aus Ankís echter Scheduler-Queue und berücksichtigt damit
den aktuell gewählten Stapel, Reihenfolge und Tageslimits. Karten werden aus
ihren Templates gerendert; das funktioniert auch mit Cloze- und
benutzerdefinierten Notiztypen ohne feste Feldnamen wie `Front` und `Back`.

### Bewertungen zurücksenden

Empfohlenes Format:

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

`ease` entspricht Anki: `1=Again`, `2=Hard`, `3=Good`, `4=Easy`. Die
Reihenfolge im Array ist verbindlich. Eine Karte darf mehrfach vorkommen,
damit lokale Lernschritte übertragen werden können.

`batch_id` macht Wiederholungsversuche sicher: Ein bereits vollständig
bearbeiteter Batch wird als `duplicate` bestätigt und nicht erneut gewertet.
Der X4 sollte deshalb die beim Pull erhaltene `pull_id` unverändert verwenden.

Das bisherige CSV-Format bleibt standardmäßig kompatibel:

```text
1700000000000,3
1700000000001,1
```

Optional sind Zeit und Bearbeitungsdauer möglich:

```text
card_id,ease,answered_at,duration_ms
1700000000000,3,1785391200,4200
```

Für zuverlässige Wiederholungsversuche sollte CSV zusätzlich den Header
`X-Xteink-Batch-ID: <pull_id>` senden.

## Wichtige Grenze des Offline-Modells

Ein morgendlicher Snapshot kann nicht vollständig vorhersagen, welche
Lernkarten durch `Again` oder `Hard` später am selben Tag erneut erscheinen
sollen. Der X4 muss solche Wiederholungen entweder lokal planen und mehrfach
protokollieren, oder die Karte erscheint beim nächsten Pull wieder. Die
endgültige Terminierung jeder übertragenen Bewertung berechnet stets der
Anki-Scheduler auf dem Mac.

## Entwicklung

Protokolltests:

```bash
python3 -m unittest discover -s tests -v
```

Syntaxprüfung:

```bash
python3 -m py_compile xteink_sync/__init__.py xteink_sync/protocol.py
```
