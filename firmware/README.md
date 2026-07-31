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
- Download aller fälligen Stapel als speicherschonendes NDJSON,
- Auswahl und Wechsel zwischen geladenen Stapeln am Gerät,
- persistente Karten, pro-Stapel-Warteschlangen und Bewertungen auf der SD-Karte,
- Offline-Anzeige von Frage und Antwort mit mehrseitigem Text,
- Konfigurierbare Schriftgröße (Klein/Mittel/Groß) und Ausrichtung
  (Hochkant/Quer) in den Anki-Einstellungen,
- Händigkeit (links/rechts) in den Anki-Einstellungen,
- Blättern über die Seitentasten (Page Up/Down),
- Platzhalter bei leeren Kartenseiten; Mac-Add-on mit Feld-Fallback,
- deutsche sowie moderne und polytonische griechische Schriftzeichen in der
  eingebetteten Anki-Schrift,
- Bewertungen `Nochmal`, `Schwer`, `Gut` und `Einfach`,
- erneute lokale Einplanung von Lernkarten nach `Nochmal`/`Schwer`,
- fehlertoleranten Upload mit Batch-ID sowie
- Eingabe von Mac-Serveradresse und API-Token am X4 oder komfortabel im
  CrossPoint-Webzugang.

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

Der Checkout-Pfad enthält einen kurzen Hash des Patches. Dadurch bleiben
aufeinanderfolgende Firmware-Stände getrennt und ein älterer Build-Ordner kann
keine Konflikte beim Anwenden eines neueren Patches verursachen.

## Flashen

Die Binärdatei ist für einen Xteink X4 mit dem Partitionslayout von CrossPoint
1.4.1 bestimmt. Sie darf nicht auf einen X3 oder eine abweichend partitionierte
Firmware geflasht werden.

Am einfachsten wird sie im offiziellen CrossPoint-Web-Flasher als
**Custom .bin** gewählt. Alternativ kann CrossPoint 1.4.1 die Datei von der
SD-Karte über **Einstellungen → Firmware von SD** installieren. Während des
Updates müssen Stromversorgung und SD-Karte verbunden bleiben.

## X4 über den Webzugang einrichten

1. Am X4 **Datentransfer → Netzwerk beitreten** öffnen.
2. Am Mac die auf dem X4 angezeigte Adresse oder
   `http://crosspoint.local/settings` öffnen.
3. Unter **Anki Offline Sync** eintragen:
   - `Mac server URL`, zum Beispiel `http://192.168.1.23:5050`
   - `API token` aus **Werkzeuge → Xteink Status** in Anki
   - `Max cards per deck` und `Max cards total` (werden beim Pull mitgeschickt)
4. **Save Anki settings** wählen.

Kartentext nutzt die **Reader-Schrift** von CrossPoint (Noto oder SD-Fonts unter
**Fonts**). So sind beliebige Sprachen möglich, nicht nur griechische Glyphen
in der UI-Schrift.

Das Token ist im Webzugang nur beschreibbar: Ein gespeichertes Token wird
nicht an den Browser zurückgesendet. Ein leeres Tokenfeld behält den bisherigen
Wert. Die Daten bleiben auf der SD-Karte über Neustarts hinweg gespeichert.

Die Serveradresse bleibt ebenfalls gespeichert, die IP-Adresse des Macs kann
sich durch DHCP jedoch ändern. Für eine dauerhaft gleiche Adresse empfiehlt
sich eine DHCP-Reservierung für den Mac im Router.

## Alternative Eingabe am Gerät

In **Anki → Anki-Einstellungen** werden eingetragen:

- `Mac-Serveradresse`: zum Beispiel `http://192.168.1.23:5050`
- `API-Token`: aus **Werkzeuge → Xteink Status** in Anki

Danach:

1. **Heutige Karten laden** – lädt alle fälligen Top-Level-Stapel
2. Bei mehreren Stapeln den gewünschten **Stapel wählen**; während des
   Lernens mit Zurück ins Menü und einen anderen Stapel wählen
3. **Karten lernen** (bei nur einem Stapel) – ohne WLAN
4. **Bewertungen übertragen**, sobald alle Stapel fertig sind und Anki auf
   dem Mac geöffnet ist

Die lokalen Dateien liegen unter `/.crosspoint/anki-*`. Offene Bewertungen
werden erst gelöscht, wenn der Mac den Batch eindeutig bestätigt hat.
