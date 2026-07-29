# X4-Firmware für CrossPoint 1.4.1

Die X4-Seite ist als kleiner, nachvollziehbarer Patch gegen die unveränderte
CrossPoint-Version 1.4.1 abgelegt. Damit wird das große Upstream-Repository
nicht in dieses Projekt kopiert.

Basis:

- CrossPoint-Tag: `1.4.1`
- CrossPoint-Commit: `970b2c6ca13d663eff1bcee9778dc48359d2ab70`
- Patch: `patches/crosspoint-1.4.1-anki.patch`

Der Patch ergänzt:

- einen eigenen **Anki**-Eintrag im CrossPoint-Hauptmenü,
- Download des Tagesstapels als speicherschonendes NDJSON,
- persistente Karten, Warteschlange und Bewertungen auf der SD-Karte,
- Offline-Anzeige von Frage und Antwort mit mehrseitigem Text,
- Bewertungen `Nochmal`, `Schwer`, `Gut` und `Einfach`,
- erneute lokale Einplanung von Lernkarten nach `Nochmal`/`Schwer`,
- fehlertoleranten Upload mit Batch-ID sowie
- Eingabe von Mac-Serveradresse und API-Token am X4.

## Bauen

Benötigt werden Git, Python 3.10 oder neuer sowie pioarduino/PlatformIO.

```bash
./firmware/build.sh
```

Das Skript klont ausschließlich die festgelegte CrossPoint-Version in
`.firmware-build/`, prüft den exakten Commit, wendet den Patch an und erzeugt:

```text
dist/crosspoint-1.4.1-xteink-anki.bin
```

## Flashen

Die Binärdatei ist für einen Xteink X4 mit dem Partitionslayout von CrossPoint
1.4.1 bestimmt. Sie darf nicht auf einen X3 oder eine abweichend partitionierte
Firmware geflasht werden.

Am einfachsten wird sie im offiziellen CrossPoint-Web-Flasher als
**Custom .bin** gewählt. Alternativ kann CrossPoint 1.4.1 die Datei von der
SD-Karte über **Einstellungen → Firmware von SD** installieren. Während des
Updates müssen Stromversorgung und SD-Karte verbunden bleiben.

## X4 einrichten

In **Anki → Anki-Einstellungen** werden eingetragen:

- `Mac-Serveradresse`: zum Beispiel `http://192.168.1.23:5050`
- `API-Token`: aus **Werkzeuge → Xteink Status** in Anki

Danach:

1. **Heutige Karten laden**
2. **Karten lernen** – dies funktioniert ohne WLAN
3. **Bewertungen übertragen**, sobald Anki auf dem Mac geöffnet ist

Die lokalen Dateien liegen unter `/.crosspoint/anki-*`. Offene Bewertungen
werden erst gelöscht, wenn der Mac den Batch eindeutig bestätigt hat.
