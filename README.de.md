# CUPS meldet „abgeschlossen“, aber es wird nichts gedruckt

[English](README.md) · **Deutsch**

Ein dokumentierter Lösungsweg für den **HP OfficeJet Pro 8730 mit CUPS 2.x**: PDF-Seiten auf dem Rechner berechnen und als **URF-Rasterdaten** senden, einschließlich korrektem Duplexdruck über die lange Kante.

Das irreführende Fehlerbild: Ein PDF-Auftrag verschwindet als erfolgreich aus der Warteschlange, **es kommt überhaupt kein Papier heraus**, und es gibt **keine hilfreiche Fehlermeldung**. Im untersuchten Fall zählte CUPS neun abgeschlossene Seiten, während der Drucker selbst null gedruckte Seiten und null Blatt meldete.

Der Rasterdruck hat den untersuchten Fall behoben. Welches PDF-Merkmal oder welches interne Verhalten des Druckers den ursprünglichen Ausfall auslöst, ist weiterhin unbekannt. Dieses Repository beschreibt einen getesteten Lösungsweg und verspricht keine allgemeine Reparatur sämtlicher Drucker.

## Was sich ändert

Die vorhandene Warteschlange behält Druckeradresse, Papierformate, Farb- und Duplexoptionen. Entfernt wird nur die direkte Weitergabe von PDF an den Drucker. Die vorhandene URF-Ausgabe bleibt bestehen:

```text
Vorher: PDF -> pdftopdf -> PDF an den Drucker
Danach: PDF -> pdftopdf -> gstoraster -> URF an den Drucker
```

Damit berechnet der Rechner die Seiten vor der Übertragung. Im geprüften Aufbau ergab normale Qualität 300 dpi und hohe Qualität 600 dpi. Die Ausrichtung über die lange Kante wurde am tatsächlich gedruckten Blatt bestätigt.

Das Werkzeug unterstützt bewusst nur die hier verwendete PPD-Struktur: direkte PDF-Ausgabe, direkte URF-Ausgabe und optional direkte JPEG-Ausgabe. Andere Ausgabepfade werden abgelehnt. Es installiert keine Pakete, verändert keine CUPS-Einstellungen, kontaktiert keinen Drucker und löst keinen Druckauftrag aus.

## Voraussetzungen

- Eine **CUPS-2.x-Warteschlange mit PPD-Datei** und ein Drucker, der tatsächlich `image/urf` unterstützt. Diese Anleitung behandelt keine CUPS-3-Konfiguration mit Printer Applications.
- Eine funktionierende PDF-Verarbeitung auf dem Rechner. Auch der Rasterweg verwendet die PDF-Filter; ein defektes `pdftopdf` wird damit nicht repariert.
- Ein erreichbarer Drucker, der Bilder ausgeben kann. Papier-, Tinten-, Anmelde- oder Verbindungsprobleme werden durch diese Änderung nicht behoben.
- Python ab Version 3.10 und die üblichen CUPS-Werkzeuge. Das Python-Skript benötigt keine Zusatzpakete.

Auf dem untersuchten Rechner gab es zuvor zusätzlich eine eigenständige `libcupsfilters`-Regression. Die Abgrenzung steht im [Fallbericht](CASE-STUDY.md#deutsch). Leere Blätter, verdrehte Rückseiten und Aufträge ohne Papierausgabe können unterschiedliche Ursachen haben.

## Änderung vorbereiten und prüfen

Die Befehle werden im Verzeichnis dieses Repositories ausgeführt. Ersetze `YOUR_QUEUE` durch den Namen aus `lpstat -p` und wähle eine lokale Test-PDF. Das Arbeitsverzeichnis ist zugleich eine private, dauerhafte Sicherung im Benutzerverzeichnis.

```bash
PRINTER='YOUR_QUEUE'
PDF='/pfad/zur/testdatei.pdf'
CUPS_WORK_DIR="$HOME/cups-raster-$(date +%Y%m%d-%H%M%S)"
mkdir -m 700 "$CUPS_WORK_DIR"

curl --fail --show-error \
  "http://localhost:631/printers/${PRINTER}.ppd" \
  --output "$CUPS_WORK_DIR/original.ppd"

python3 prepare_ppd.py "$CUPS_WORK_DIR/original.ppd" --check
python3 prepare_ppd.py \
  "$CUPS_WORK_DIR/original.ppd" "$CUPS_WORK_DIR/raster.ppd"

cupstestppd -v "$CUPS_WORK_DIR/original.ppd" > "$CUPS_WORK_DIR/original-validation.txt"
cupstestppd -v "$CUPS_WORK_DIR/raster.ppd" > "$CUPS_WORK_DIR/raster-validation.txt"
cupsfilter --list-filters -p "$CUPS_WORK_DIR/raster.ppd" -e \
  -i application/pdf -m "printer/$PRINTER" "$PDF"
```

Bei Fehlern in der Vorbereitung oder Filterwegprüfung nicht mit der Installation fortfahren. Das Skript zeigt die genaue Änderung und überschreibt keine vorhandene Ausgabedatei. Seine Kompatibilitätsprüfung ist begrenzt. Beide Prüfprotokolle lesen: Automatisch erzeugte PPDs können bereits Konformitätsfehler enthalten. Hier meldeten beide Fassungen dieselben vorhandenen Übersetzungslücken und einen zu langen `ShortNickName`; neue Fehler kamen nicht hinzu. Neue Befunde sowie Struktur- oder Filterfehler vor der Installation untersuchen. Der Weg muss Rasterdaten erzeugen. Im getesteten Aufbau wurden `pdftopdf` und anschließend `gstoraster` ausgewählt.

Entfernt wurde in unserem Fall diese Regel:

```text
*cupsFilter2: "application/vnd.cups-pdf application/pdf 10 -"
```

Die vorhandene `image/urf`-Regel und **sämtliche Duplex- und Rückseiteneinstellungen bleiben erhalten**. `cupsBackSide: Rotated` nicht auf Verdacht durch `Normal` ersetzen, um einen falsch ausgerichteten Testdruck auszugleichen. Die mögliche Rückumwandlung in PDF wird weiter unten erläutert.

## Anwenden, testen und zurücknehmen

Nach erfolgreicher Prüfung die vorbereitete PPD auf die vorhandene Warteschlange anwenden:

```bash
sudo lpadmin -p "$PRINTER" -P "$CUPS_WORK_DIR/raster.ppd"
```

Der folgende Befehl druckt tatsächlich die ersten beiden Seiten, normalerweise auf einem Blatt. Bei Bedarf das Papierformat anpassen:

```bash
lp -d "$PRINTER" -n 1 -P 1-2 \
  -o media=A4 -o sides=two-sided-long-edge "$PDF"
```

Prüfen, ob beide Seiten bedruckt sind und beim Umblättern wie eine Buchseite aufrecht stehen. In den PDF-Viewern weiterhin diese eingerichtete Warteschlange wählen; ein zusätzlich automatisch gefundenes Druckerziel kann einen anderen Druckweg verwenden.

Rücknahme mit der eigenen gesicherten PPD:

```bash
sudo lpadmin -p "$PRINTER" -P "$CUPS_WORK_DIR/original.ppd"
```

Die Konfiguration bleibt nach Neustarts erhalten. Eine Neuerstellung der Warteschlange mit `-m everywhere` kann die PPD neu erzeugen und die Änderung aufheben. Die Sicherung deshalb aufbewahren. Rasterdruck kann mehr Rechenzeit und Übertragungsdaten benötigen.

## Stolperfalle: Rasterdaten können wieder zu PDF werden

Beim Senden einer vorberechneten `.urf`-Datei an die **alte** Warteschlange wählte CUPS den Weg `pwgtopdf -> pdftopdf` und sendete erneut PDF. Die bereits für den Rastertransport gedrehte Rückseite wurde dadurch falsch ausgegeben.

Mit der angepassten Warteschlange entfällt dieses native PDF-Ausgabeziel. Sowohl der direkte URF-Test als auch normale PDF-Aufträge über die endgültige Warteschlange wurden erfolgreich gedruckt. Die vom Drucker verlangte Ausrichtung der Rasterrückseite beibehalten und den tatsächlichen Filterweg prüfen.

## Den stillen Fehler erkennen

CUPS-Status, **Gerätezähler im Drucker** und tatsächliche Papierausgabe vergleichen. „Abgeschlossen“ allein war hier kein Nachweis für einen Ausdruck.

Der enthaltene IPP-Test liest ausschließlich Auftragsdaten. Er benötigt die IPP-Adresse des wirklichen Druckers, nicht die localhost-Adresse der CUPS-Warteschlange:

```bash
ipptool -T 10 -tv 'ipp://YOUR_PRINTER/ipp/print' get-printer-jobs.test
```

Nicht jeder Drucker speichert eine Historie oder liefert verlässliche Zähler. Der Test fordert absichtlich keine Benutzernamen oder Dokumenttitel an. Ausgaben vor einer Veröffentlichung trotzdem prüfen. Echte PPD-Dateien und Druckspool-Dateien können Gerätekennungen oder persönliche Dokumentinhalte enthalten.

## Nachweise und Mitarbeit

Der [Fallbericht auf Deutsch und Englisch](CASE-STUDY.md) enthält Versionen, Messergebnisse, verworfene Vermutungen und Verweise auf verwandte Fehlerberichte. Das ursprüngliche Dokument wird nicht veröffentlicht. Die Python-Tests verwenden künstliche PPD-Ausschnitte und prüfen das Werkzeug, nicht die Kompatibilität beliebiger Drucker-Firmware.

```bash
python3 -m unittest -v
```

Rückmeldungen auf Deutsch oder Englisch sind willkommen. Hilfreich sind Druckermodell, CUPS-/Filterversionen, relevante Filterregeln, der gewählte Filterweg und die tatsächlich beobachtete Ausgabe. Lokale Adressen, Seriennummern, Benutzernamen und Dokumentinhalte vor dem Teilen entfernen. Aus einem ähnlichen Symptom folgt noch kein identischer interner Fehler.

Technische Referenzen: [CUPS-Filterregeln und Rückseitenkonventionen](https://openprinting.github.io/cups/doc/spec-ppd.html#cupsFilter2), [Warteschlangenverwaltung mit lpadmin](https://openprinting.github.io/cups/doc/man-lpadmin.html).

[MIT-Lizenz](LICENSE).
