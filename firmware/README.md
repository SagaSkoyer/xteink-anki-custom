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
- **Kartenschrift:** Standard UI-Schrift mit Deutsch + modernem/polytonischem
  Griechisch; optional Reader-/SD-Schrift für weitere Sprachen,
- **Max. Karten pro Stapel** und **gesamt** in Geräte- und Web-Einstellungen
  (werden beim Pull an das Add-on gesendet),
- Schriftgröße (Klein/Mittel/Groß), Ausrichtung (Hochkant/Quer), Händigkeit,
- **Tastenbelegung im Lernmodus** (unten links nach rechts = Zurück, Bestätigen,
  Links, Rechts; oben = Seitentasten Hoch/Runter):
  - **Oben (Hoch/Runter):** auf der Frage beide **Umdrehen**; auf der Antwort
    Hoch = **Nochmal**, Runter = **Gut**,
  - **Unten 1 (Zurück):** Karte verlassen, zurück ins Stapelmenü — auf Frage
    und Antwort,
  - **Unten 2 (Bestätigen):** **Rückgängig** — letzte Bewertung zurücknehmen
    und zur vorherigen Karte (Frage) zurückkehren,
  - **Unten 3 (Links) kurz:** **Flag** umschalten; **lang halten (~0,55 s):**
    **Zurückstellen** (Bury) — Karte nur lokal für heute überspringen, ohne
    Bewertung; rein lokal und wird beim nächsten Pull verworfen,
  - **Unten 4 (Rechts):** in langen Karten nach unten **blättern**,
- **Flag:** Rotflag 0↔1 über Unten 3 (kurz); Icon rechts der Progress-Bar;
  Sync Pull/Push,
- **Progress:** zählt nur abgeschlossene Karten (Gut ohne Requeue); **Nochmal**
  füllt den Balken nicht; zurückgestellte (Bury) Karten zählen ebenfalls nicht,
- **Version:** Anki-Menü + Anki-Einstellungen zeigen Firmware-Version im Header
  (Release: `1.4.1-anki-2.5.7`; auch Boot/System-Einstellungen),
- Platzhalter bei leeren Kartenseiten; Mac-Add-on mit Feld-Fallback,
- Bewertungen am Gerät: `Nochmal` und `Gut` (Tasten oben); `Schwer`/`Einfach`
  entfallen mit der neuen Tastenbelegung,
- erneute lokale Einplanung von Lernkarten nach `Nochmal`,
- **Rückgängig:** letzte Bewertung einstufig zurücknehmen (Unten 2),
- fehlertoleranten Upload mit Batch-ID (JSON: Reviews + Flags) sowie
- Eingabe von Mac-Serveradresse und API-Token am X4 oder im CrossPoint-Webzugang.

## Bauen

Benötigt werden Git, Python 3.10 oder neuer sowie pioarduino/PlatformIO
(`pio` im PATH oder `~/.platformio/penv/bin/pio`).

**Agent/Release-Regel:** Nach jeder Firmware-Änderung (Patch, UI, Sync-Protokoll)
wird `./firmware/build.sh` ausgeführt und `dist/crosspoint-1.4.1-xteink-anki.bin`
(+ `dist/SHA256SUMS`) aktualisiert — nicht nur der Patch.

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
   - **Mac-Server-URL**, z. B. `http://192.168.1.23:5050`
   - **API-Token** aus **Werkzeuge → Xteink Status** in Anki
   - **Max. Karten pro Stapel** und **Max. Karten gesamt** (1–1000; werden
     beim Pull mitgeschickt)
   - **Kartenschrift / Use reader / SD font:** aus = UI-Schrift mit
     Deutsch/Griechisch; an = Reader- oder SD-Schrift
4. **Save Anki settings** wählen.

**Kartenschrift (Sprachen):**

- **Standard (empfohlen für Griechisch):** UI-Schrift mit Deutsch sowie
  modernem und polytonischem Griechisch. Am Gerät:
  **Anki → Anki-Einstellungen → Kartenschrift → UI (DE/Griechisch)**.
- **Andere Schriften/Sprachen:** Unter **Fonts** eine Schriftfamilie
  hochladen, in **Einstellungen → Schrift** wählen, dann in Anki
  **Kartenschrift → Reader / SD-Schrift** bzw. im Web den Schalter
  **Use reader / SD font** einschalten.

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
- `Max. Karten / Stapel` und `Max. Karten gesamt` (per Bestätigen durchschalten)
- `Kartenschrift`: UI (DE/Griechisch) oder Reader / SD-Schrift

Danach:

1. **Heutige Karten laden** – lädt alle fälligen Top-Level-Stapel
2. Bei mehreren Stapeln den gewünschten **Stapel wählen**; während des
   Lernens mit Zurück ins Menü und einen anderen Stapel wählen
3. **Karten lernen** (bei nur einem Stapel) – ohne WLAN
4. **Bewertungen übertragen**, sobald alle Stapel fertig sind und Anki auf
   dem Mac geöffnet ist

Die lokalen Dateien liegen unter `/.crosspoint/anki-*`. Offene Bewertungen
werden erst gelöscht, wenn der Mac den Batch eindeutig bestätigt hat.
