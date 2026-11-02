# Case study / Fallbericht

[English](#english) · [Deutsch](#deutsch) · [Instructions](README.md) · [Anleitung](README.de.md)

## English

### Tested environment

Investigation completed on **2026-11-02**. These are observed versions, not a recommendation to install or pin them indefinitely.

| Component | Observed value |
|---|---|
| Printer | HP OfficeJet Pro 8730 |
| Reported firmware | WEBPDLPP1N001.2620A.00 |
| Host | CachyOS / Arch Linux family |
| CUPS | 2.4.20 (package `2:2.4.20-1`) |
| cups-filters | 2.0.1-3.1 |
| libppd | 2.1.1-2.1 |
| libcupsfilters after the earlier repair | 2.1.2, local package based on unmodified upstream source |
| QPDF | 12.4.2 |
| Ghostscript | 10.08.0 |
| Queue | Existing IPP Everywhere-generated PPD |
| Relevant advertised URF features | `RS300-600`, `SRGB24`, `DM3` |

### What was observed

| Test | Result at the physical printer |
|---|---|
| Original PDF through the native PDF route | No paper; device job marked completed with 0 impressions / 0 sheets |
| PDF with the malformed font compression repaired | Still no paper |
| First page rendered to JPEG | 1 impression / 1 sheet; device lifetime counter increased by 1 |
| Pre-rendered URF submitted through the old queue | 2 impressions / 1 sheet, but incorrect back-page orientation; filter graph selected `pwgtopdf -> pdftopdf` |
| Same URF sent directly with long-edge duplex | 2 impressions / 1 sheet; correct physical orientation confirmed |
| Ordinary PDF after the queue change | 2 impressions / 1 sheet for the selected pair of pages |
| Remaining five pages through the changed queue | Device confirmed 5 impressions / 3 sheets |

For the original failing PDF job, CUPS reported a successful completion and nine completed pages while the device reported zero. For the final odd-page job, CUPS and the device also disagreed about sheet count. The device's counters and the physical output were therefore checked independently.

The saved input and output of the failed print job had **no AcroForm or Widget annotations**. Interactive form fields were already converted to ordinary page content. A malformed compressed font stream was a real finding, but repairing it did not restore printing. Neither form fields nor that font defect were established as the root cause.

The results isolate a problem in the native PDF printing path for this document. They do **not** prove a specific firmware defect or identify the precise PDF construct that triggers it. A publicly shareable minimal reproducer of that silent failure has not been established.

### Why the first raster test flipped the back page

The original PPD advertised native PDF pass-through at cost 10 and URF pass-through at cost 100. The installed MIME graph also allowed URF-to-PDF conversion. The selected route for an already rasterized input was observed to be `pwgtopdf -> pdftopdf`, rather than direct URF.

The second raster page was already oriented for the device's raster convention (`cupsBackSide: Rotated`, matching `DM3`). Converting that page image back into a PDF produced the wrong physical orientation. Removing the native PDF output rule solved the routing issue; changing the raster back-side convention was unnecessary.

### Separate host-filter regressions

Before this investigation, a different installed library build (`libcupsfilters 2.2.1.r32.gd49e9284-1.1`) had caused incorrect long-edge PDF duplex orientation and blank output from compound-filter PDF streams. Replacing it with a tested build of upstream 2.1.2 resolved those earlier symptoms. The later silent native-PDF failure still occurred with that repaired host library.

Related upstream work: [duplex report #263](https://github.com/OpenPrinting/libcupsfilters/issues/263), [merged fix #265](https://github.com/OpenPrinting/libcupsfilters/pull/265), [compound-stream report #301](https://github.com/OpenPrinting/libcupsfilters/issues/301), and [the upstream 2.1.2 release explanation](https://openprinting.github.io/libcupsfilters-2.1.2). The duplex PR was already merged when this repository was prepared; a source fix and the packages installed on a particular machine are separate questions.

Prefer an appropriate maintained distribution package containing the relevant fixes. This repository does not distribute local binary packages or automate library downgrades. An unrepaired host filter can still fail before rasterization begins.

### Validation and limits

Strict `cupstestppd` validation reported the same pre-existing missing translations and overlong `ShortNickName` in both the original and modified PPD; it was not a clean conformance pass. The helper introduced no additional validator findings. CUPS accepted the configuration and the actual filter path was verified. Local conversion covered the nine-page form, another PDF, and a PostScript path corresponding to PDF-viewer printing. All inspected raster pages contained visible content. Raster headers were checked for simplex, long-edge and short-edge settings. Both PPD and IPP high-quality options generated 600 dpi; normal quality generated 300 dpi.

Long-edge orientation was physically checked. Short-edge mode was checked in raster headers only. No claim is made about every printer model, every application, or every unusual PDF.

The raster filter can emit `Unable to detect print-quality, using 'normal'!` for legacy PPD-style options. In this setup it was nonfatal, including when an independently checked raster header showed 600 dpi. This message is separate from the original silent native-PDF failure. A trial fixed IPP quality default was removed because it could override a different PPD quality selection.

The public repository contains newly written documentation, a preparation helper and synthetic tests. It excludes original PDFs, spool files, device PPDs, screenshots and raw diagnostic logs. Reports may reference this case, but no new upstream issue was filed automatically.

## Deutsch

### Geprüfter Aufbau

Die Untersuchung wurde am **02.11.2026** abgeschlossen. Die folgende Umgebung beschreibt den beobachteten Stand und ist keine Empfehlung, diese Versionen dauerhaft festzuschreiben:

- HP OfficeJet Pro 8730, gemeldete Firmware `WEBPDLPP1N001.2620A.00`.
- CachyOS aus der Arch-Linux-Familie; CUPS 2.4.20 (`2:2.4.20-1`), cups-filters 2.0.1-3.1 und libppd 2.1.1-2.1.
- Nach einer früheren Reparatur: libcupsfilters 2.1.2 aus unverändertem Upstream-Quellcode, QPDF 12.4.2 und Ghostscript 10.08.0.
- Vorhandene, durch IPP Everywhere erzeugte PPD; gemeldete URF-Merkmale unter anderem `RS300-600`, `SRGB24` und `DM3`.

### Beobachtungen

| Versuch | Ergebnis am wirklichen Drucker |
|---|---|
| Original-PDF über native PDF-Ausgabe | Kein Papier; Auftrag trotzdem abgeschlossen, 0 Seiten / 0 Blatt |
| PDF nach Reparatur der fehlerhaften Schriftkomprimierung | Weiterhin kein Papier |
| Erste Seite als JPEG | 1 Seite / 1 Blatt; Gerätezähler um 1 gestiegen |
| Vorberechnetes URF über die alte Warteschlange | 2 Seiten / 1 Blatt, Rückseite falsch ausgerichtet; Filterweg `pwgtopdf -> pdftopdf` |
| Dasselbe URF direkt mit langer Kante gesendet | 2 Seiten / 1 Blatt; Ausrichtung am Papier bestätigt |
| Normaler PDF-Auftrag nach der Umstellung | Ausgewählte zwei Seiten auf einem Blatt gedruckt |
| Verbleibende fünf Seiten über die umgestellte Warteschlange | Drucker bestätigte 5 Seiten / 3 Blatt |

CUPS meldete beim ursprünglichen Fehlversuch Erfolg und neun abgeschlossene Seiten, der Drucker dagegen null. Auch beim letzten Auftrag mit ungerader Seitenzahl unterschieden sich die Blattzähler. Deshalb wurden Gerätezähler und tatsächliche Ausgabe unabhängig vom CUPS-Status geprüft.

Die gespeicherten Druckdaten enthielten **keine AcroForm- oder Widget-Annotationen** mehr. Die Formularfelder waren bereits in normalen Seiteninhalt umgewandelt. Ein fehlerhaft komprimierter Schriftbestandteil war nachweisbar; seine Korrektur behob das Druckproblem jedoch nicht. Weder Formularfelder noch dieser Schriftfehler konnten als eigentliche Ursache bestätigt werden.

Damit ist der Fehler auf den nativen PDF-Druckweg dieses Dokuments eingegrenzt. Ein bestimmter Firmwarefehler oder ein konkretes auslösendes PDF-Merkmal ist **nicht bewiesen**. Ein öffentlich teilbares Minimalbeispiel, das den stillen Ausfall reproduziert, liegt bislang nicht vor.

### Warum der erste Rastertest falsch gewendet wurde

Die ursprüngliche PPD erlaubte native PDF-Ausgabe mit Kostenwert 10 und direkte URF-Ausgabe mit Kostenwert 100. Die installierten Konvertierungsregeln ließen außerdem URF nach PDF zu. Für den Rasterauftrag wurde tatsächlich `pwgtopdf -> pdftopdf` gewählt.

Die zweite Rasterseite war bereits entsprechend `cupsBackSide: Rotated` beziehungsweise `DM3` gedreht. Nach der Rückumwandlung dieses Seitenbilds in PDF stimmte die physische Ausrichtung nicht mehr. Das Entfernen des nativen PDF-Ausgabeziels beseitigte den unerwünschten Weg. Die Rückseitenkonvention selbst musste nicht verändert werden.

### Eigenständige frühere Filterfehler

Zuvor hatte die installierte Bibliotheksversion `libcupsfilters 2.2.1.r32.gd49e9284-1.1` bereits verdrehte Rückseiten bei langer Kante und leere Ausgabe bei PDF-Daten mit kombinierten Stream-Filtern verursacht. Ein geprüfter Build der Upstream-Version 2.1.2 behob diese früheren Symptome. Der spätere stille PDF-Ausfall trat auch mit dieser reparierten Bibliothek auf.

Verwandte Upstream-Arbeiten: [Duplexbericht #263](https://github.com/OpenPrinting/libcupsfilters/issues/263), [übernommene Korrektur #265](https://github.com/OpenPrinting/libcupsfilters/pull/265), [Bericht zu kombinierten Stream-Filtern #301](https://github.com/OpenPrinting/libcupsfilters/issues/301) und [Erläuterung zur Veröffentlichung 2.1.2](https://openprinting.github.io/libcupsfilters-2.1.2). Die Duplexkorrektur war bei Erstellung dieses Repositories bereits übernommen. Ob sie im konkret installierten Distributionspaket enthalten ist, muss gesondert geprüft werden.

Ein passendes, gepflegtes Distributionspaket mit den erforderlichen Korrekturen ist vorzuziehen. Dieses Repository verteilt keine lokal gebauten Binärpakete und führt keine automatischen Downgrades aus. Ein defekter Host-Filter kann auch vor einer Rasterausgabe scheitern.

### Prüfung und Grenzen

Die strenge Prüfung mit `cupstestppd` meldete in Original und angepasster PPD dieselben vorhandenen Übersetzungslücken und einen zu langen `ShortNickName`; ein fehlerfreier Konformitätstest war es somit nicht. Das Werkzeug verursachte keine zusätzlichen Befunde. CUPS akzeptierte die Konfiguration, und der tatsächliche Filterweg wurde geprüft. Lokal wurden das neunseitige Formular, eine weitere PDF und ein PostScript-Druckweg geprüft. Alle untersuchten Rasterseiten enthielten sichtbaren Inhalt. Die Rasterköpfe wurden für einseitigen Druck sowie lange und kurze Kante kontrolliert. Hohe Qualität erzeugte über PPD- und IPP-Optionen jeweils 600 dpi, normale Qualität 300 dpi.

Die lange Kante wurde am Ausdruck geprüft. Die kurze Kante wurde nur anhand der Rasterköpfe geprüft. Daraus folgt keine Zusicherung für sämtliche Druckermodelle, Programme oder ungewöhnlichen PDFs.

Bei klassischen PPD-Qualitätsoptionen kann der Rasterfilter `Unable to detect print-quality, using 'normal'!` protokollieren. Die Meldung verhinderte die Ausgabe hier nicht, auch wenn der geprüfte Rasterkopf 600 dpi auswies. Sie ist vom ursprünglichen stillen PDF-Fehler zu unterscheiden. Eine versuchsweise feste IPP-Qualitätsvorgabe wurde entfernt, weil sie eine abweichende PPD-Auswahl übersteuern konnte.

Das öffentliche Repository enthält neu geschriebene Dokumentation, ein Vorbereitungswerkzeug und künstliche Tests. Original-PDFs, Druckspool-Dateien, echte Geräte-PPDs, Bildschirmfotos und rohe Diagnoseprotokolle werden nicht veröffentlicht. Neue Upstream-Fehlerberichte wurden nicht automatisch eingestellt.
