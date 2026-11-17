# Annahmen, Datenlücken und Abweichungen

Verantwortlich: AP2 (Katalog), Inhalte von allen Paketen. Jede Annahme wird hier eingetragen, bevor sie im Code oder in `config/` verwendet wird. Befunde mit Nummer B-… stehen in [datenmodell-mes.md](datenmodell-mes.md).

## 1. Datenlücken

| Nr. | Lücke | Folge | Wer klärt | Stand |
|---|---|---|---|---|
| L-01 | **Referenzpaket fehlt im Repo.** Die Aufgabenstellung verweist auf ein Referenzpaket mit Daten, Formaten, Produktionsabschnitt, festen Umgebungsregeln und einem SimPy-Grundgerüst. Vorgegeben sein sollen: Warte- und Übergaberegel bei vollem Zielpuffer, Weiterfahr- und Wiederkehrregel bei Materialmangel, Montagepriorität, Auftragsfreigabe, Fahrzeugzuordnung, Leerboxrückführung | Die Referenzregeln in `src/matsim/referenz/` sind nur Signaturen. Eigene Festlegungen wären erfunden | Team beim Dozenten anfragen | offen, blockiert AP3 ab Meilenstein M2 |
| L-02 | Bandlaufzeiten und Umlaufzeit eines Werkstücks sind nicht aufgezeichnet. `tblfinstep.TransportTime` ist im geprüften Ablauf 0 | Wiederkehrzeit nach Weiterfahrt nicht belegbar | AP1; sonst Messung im Labor oder Szenarioannahme | offen |
| L-03 | Fahrten der Robotinos (Ressourcen 20 bis 25) erscheinen nicht als Schritte in `tblfinstep`. Die Zeit „Ende letzter Pick bis Box an Station“ (B-14) enthält Warten auf Fahrzeug, Fahrt und Übergabe | Keine reine Fahrzeit, keine Rückfahrzeit, keine Fahrzeugbelegung aus Daten | AP1 prüft `tblmachinereport` (L-06) | offen |
| L-04 | Zustandstabellen ohne Historie (`tblorder`, `tblorderpos`, `tblstep`, `tblbufferpos`, `tblboxpos`, `tblbox`, `tblcarrier`) | Bestandsverläufe nur als sechs Momentaufnahmen; keine Rekonstruktion historischer Bestandsfolgen | als Datenlücke ausweisen | festgestellt |
| L-05 | Gebuchte Pufferplätze an der Kommissionierstation ohne Auftrag (`Booked = 1`, `ONo = 0`, B-12) und 26 verwaiste Zeilen in `tblstepparameter` | Kapazität des Kommissionierplatzes ungeklärt; gebuchte Plätze gelten nicht als frei | AP1, Rückfrage beim Dozenten | offen |
| L-06 | Bedeutung von `tblmachinereport` (62 540 Zeilen mit `Busy`-Kennzeichen je Ressource, auch für die Robotinos) ist nicht dokumentiert | Mögliche Quelle für Fahrzeugbelegung, bisher ungenutzt | AP1 | offen |
| L-07 | Box 11 im Snapshot 15:57 doppelt verortet (B-11) | Boxbestand je Ort nicht eindeutig | AP1 | offen |
| L-08 | Verfügbarer Boxbestand: Stammdaten nennen 40 Boxen, verortet sind 21, davon 8 leer (B-09, B-10) | Boxbestand der Simulation ist eine Annahme (A-03) | AP1, Zählung im Labor | offen |
| L-09 | Bedarfseingang: In den Daten gibt es nur den einen Ablauf mit drei Produkten; ein Bedarfsmuster für Basis- und Stressfall ist nicht ableitbar | Bedarfsmuster sind Szenarioannahmen | AP5 | festgestellt |
| L-10 | Live-Zugriff im Labornetz wurde in diesem Durchlauf nicht ausgeführt | `matsim.daten.live` ist ungetestet gegen die echte Datenbank | AP1 im Labor | offen |

## 2. Annahmen

| Nr. | Annahme | Begründung und Beleg | Wirkung | Zu bestätigen durch |
|---|---|---|---|---|
| A-01 | Ein Werkstück ohne vollständigen Satz an der Station fährt weiter und kommt nach einem Umlauf wieder | Aufgabenstellung, Team C: „Fehlt Material, fährt das Werkstück weiter“; Topologie mit geschlossener Schleife (B-02); Bearbeitungsreihenfolge an RASS1 weicht von der Auslagerreihenfolge ab (B-08) | bestimmt verpasste Bearbeitungsmöglichkeiten | Referenzpaket (L-01) |
| A-02 | Anfangsbestand der Simulation = freie Teile in verorteten Boxen | Teile in nicht verorteten Boxen sind nicht nachweislich zugreifbar (B-10) | begrenzt die Zahl versorgbarer Sätze; Kandidat für die Sensitivitätsanalyse | AP1 |
| A-03 | Transportboxen = leere verortete Boxen (7 ohne die Box am AASS1-Cache) | B-09, B-10 | bestimmt Stress 2 | Zählung im Labor |
| A-04 | Der Kommissionierplatz bearbeitet eine Charge zur Zeit | Am 09.11.2026 überlappen sich keine OpNo-220-Schritte; die drei Aufträge liefen nacheinander (B-08) | Engpass der Versorgung | AP1 über die gesamte Historie |
| A-05 | Zwei Fahrzeuge im Basisfall | Stammdaten nennen sechs Robotinos; am Nachmittag des 09.11.2026 meldeten nur die Ressourcen 24 und 25 | Fahrzeugkonkurrenz | Dozent |
| A-06 | Eine Charge enthält nur Sätze einer Station | abgeleitet aus dem Materialpfad (datenmodell-mes.md, Abschnitt 5); keine MES-Sperre | schränkt zulässige Kombinationen ein | Dozent oder Referenzpaket |
| A-07 | Hintransport als Festwert 130 s im Hauptvergleich | Median aus B-14; enthält Wartezeit | überschätzt die reine Fahrzeit | Sensitivität im Szenario `unsicherheit` |
| A-08 | Alle Zahlenwerte in `config/szenarien/` sind Entwürfe | L-09 | Versuchsergebnisse | AP5 mit Begründung im Versuchsplan |
| A-09 | V0 bedient die Stationen zyklisch in der Folge RASS1, RASS2, RASS3 und beginnt danach wieder bei RASS1. Passen die offenen Sätze einer Station nicht in eine Box (mehr als 8 Positionen), wird die Box in Eingangsfolge gefüllt und der Rest in der nächsten Runde versorgt | Beobachtet ist nur ein Durchlauf mit je drei Sätzen (B-08); historische Kommissionieraufträge haben höchstens 8 Positionen (B-15). Die Reihum-Regel verhindert, dass eine Station mit hohem Bedarf die anderen dauerhaft verdrängt | bestimmt V0 in Bedarfsspitze und Stressfällen; für die Validierung am 09.11.2026 ohne Wirkung | Dozent oder Referenzpaket (L-01) |

## 3. Abweichungen zwischen Projektauftrag und Repo

Regel: Wenn eine Angabe aus dem Projektauftrag nicht zu den Dateien passt, gilt die Datei.

| Nr. | Angabe im Projektauftrag | Tatsächlicher Stand | Umgang |
|---|---|---|---|
| D-01 | `docs/00-…` bis `docs/14-…` liegen im Repo | Zu Beginn nicht vorhanden; während des Durchlaufs vom Team ergänzt, inhaltlich identisch mit dem Repo der Lehrmaterialsammlung | unverändert übernommen |
| D-02 | Sechs Dumps in `MES_database_snapschots/MES_database_snapschots/` | Im Repo lag nur der Dump von 15:57 und die `Readme.md`. Die übrigen fünf wurden aus dem lokalen Download-Ordner kopiert | alle sechs liegen in `data/raw/mes_snapshots/`; der Ursprungsordner ist entfallen |
| D-03 | `.gitignore` schließt `*.sql`, `*.db`, `*.pdf`, Office-Dateien und Archive aus | Die `.gitignore` war die Python-Standardvorlage ohne diese Einträge. Versioniert waren nur `.gitignore` und `README.md` | Einträge ergänzt |
| D-04 | `CONTRIBUTING.md`, `NOTICE.md`, `LICENSE.md`, `CITATION.cff`, `assets/`, `.editorconfig`, `.gitattributes` vorhanden | In diesem Repo nicht vorhanden (nur in der Lehrmaterialsammlung) | `CONTRIBUTING.md`, `.editorconfig`, `.gitattributes` neu angelegt; Lizenzdateien nicht kopiert (Teamentscheidung) |
| D-05 | README beschreibt die Lehrmaterialsammlung | README bestand aus Titel und einem Satz zum Projekt | ersetzt |
| D-06 | Aufgabenstellung nur als Text zu Team A | Das PDF der Prüfungsprojekte liegt im Repo-Ordner und enthält zusätzlich gemeinsame Anforderungen und Abgaben (Befundregister, Enumeration, unabhängige Prüfung, feste Dauern im Hauptvergleich) sowie den Verweis auf ein Referenzpaket | in `aufgabenstellung.md` und der Anforderungsmatrix aufgenommen; PDF wird nicht versioniert |
| D-07 | Mehrere Replikationen für jedes Szenario | Laut PDF verwendet der Hauptvergleich feste Dauern; Wiederholungen sind nur bei zufälligen Dauern nötig | Basis- und Stressfälle mit einer Replikation, `unsicherheit` mit zehn |
| D-08 | Bandumlauf mit Weiche an Station 10 zurück zu 1 oder 8 | Station 10 hat drei Ausgänge (1, 8, 11); die Montagestationen liegen in einer geschlossenen Schleife (B-02) | Topologie aus der Datei übernommen |
| D-09 | Pufferplätze tragen eine Zone, die auf eine Materialgruppe verweist | Alle Box-Pufferplätze tragen Zone 7 („Boxes“), alle Boxplätze Gruppe 9 (B-05) | Stationsreinheit als abgeleitete Regel (A-06) |
| D-10 | Stichprobengrößen und Kennwerte der Zeitansätze | Mediane stimmen; n weicht um wenige Fälle ab, die indirekte Transportzeit deutlicher (B-13, B-14) | Werte aus der eigenen Auswertung mit dokumentiertem Filter |
| D-11 | 21 bis 22 Boxen verortet | 21 Boxen in jedem Snapshot; die 22 im letzten Snapshot sind Zeilen, weil Box 11 doppelt steht (B-11) | Befund aufgenommen |
| D-12 | Snapshot-`Readme.md` bleibt | In `Readme_Dozent.md` umbenannt, weil daneben die eigene `README.md` liegt und Windows Groß- und Kleinschreibung nicht unterscheidet | Inhalt unverändert |

## 4. Offene Entscheidungen des Teams

1. Referenzpaket beim Dozenten anfordern (L-01). Ohne es bleiben die Referenzregeln offen.
2. Eigene Verbesserung V4 aus den drei Kandidaten in [planungsverfahren.md](planungsverfahren.md) wählen.
3. Zweiter Stressfall: knappe Boxen, knappe Übergabeplätze oder beide.
4. Sensitivitätsanalyse: unsichere Zeitansätze oder die Bereinigungsentscheidung zum Anfangsbestand (A-02).
5. Lizenz des Projektcodes und Übernahme von `LICENSE.md`, `NOTICE.md`, `CITATION.cff` für die Lehrunterlagen in `docs/`.
6. Format und Werkzeug der Hausarbeit (Markdown, LaTeX oder Word).
7. Weitergabe der Dumps im Team (Kursplattform oder gemeinsamer Ordner außerhalb des Repos).
