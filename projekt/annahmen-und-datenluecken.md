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

## 5. Verfahrensbezogene Ergänzungen aus AP2 (Arbeitsfassung 17.11.2026)

Die bisherigen Abschnitte 1–4 und Kennungen A-01–A-08, L-01–L-10 sowie D-01–D-12 bleiben unverändert. Historische Aussagen zu lokal vorhandenen Unterlagen sind keine Aussage über diesen Checkout: `docs/`, SQL-Dumps und das Referenzpaket fehlen hier. Keine dieser Datenlücken wird durch die Literaturrecherche geschlossen.

A-01–A-08 bleiben Annahmen mit den bereits genannten Bestätigungsbedarfen, keine validierten Anlagenfakten. Insbesondere gelten A-03/A-05 nicht als gemessene verfügbare Kapazitäten, A-06 nicht als technische MES-Sperre und A-07 nicht als reine Fahrzeit. L-06 betrifft laut Originalkatalog mögliche Fahrzeugbelegung; daraus ist keine Werkstückankunftsprognose belegt.

### Zusätzliche verfahrensbezogene Vorschläge A-V01 bis A-V11

Alle neuen Kennungen sind **bewusst von A-01 bis A-08 getrennt** und noch nicht beschlossen.

| Neue Kennung | Konkret vorgeschlagene Zusatzannahme bzw. Regel | Warum erforderlich? | Betroffene Verfahren | Status |
|---|---|---|---|---|
| **A-V01** | Bei gleichem verfügbaren Zeitpunkt werden offene Anforderungen deterministisch nach Eingang und ID geordnet, soweit keine implementierte andere Regel gilt. | Vergleichbare Auswahl, Schutz vor zufälliger Reihenfolge | V2, V3, V4; bei V1 bereits implementiert | Neuer Vorschlag für V2 bis V4 |
| **A-V02** | Die Füllschwelle zählt belegte **Boxpositionen**, nicht Satzanzahl; erreicht wird sie ab „mindestens F“, solange die Kapazität nicht überschritten wird. | Unterschiedliche Satzgrößen, unerreichbare Exaktfüllung | V2, K1, K3 | Präzisierung des dokumentierten Entwurfs / neuer Vorschlag für Nicht-Exakt-Regel |
| **A-V03** | Wenn ein größerer Satz nicht mehr in die Box passt, darf ein nachfolgender kleinerer erfüllbarer Satz derselben Station geprüft werden. | Reproduzierbarer Umgang mit variierender Belegung | V2, V3, V4 | Neuer Vorschlag |
| **A-V04** | Je Anforderung beginnt eine Frist beim ersten zulässigen Aufruf mit vollständiger Erfüllbarkeit aus freiem Bestand; fehlende Boxen verhindern den Start nicht. Einmal gesetzte Termine werden bei späterem Bestands- oder Boxmangel nicht verschoben; für den offenen Rest gilt der früheste verbliebene Termin. | Trennung von Fehlteilwartezeit und bewusstem Bündelungswarten | V2b, V3, K1/K2/K3 | Neuer Vorschlag, vor Teamentscheidung prüfen |
| **A-V05** | V2 erhält entweder eine verbindliche, tatsächlich auslösbare Restwartefrist oder ein zur Laufzeit bekanntes Bedarfsende. | Verhindert unendliches Zurückhalten kleiner Reste | V2 | Neuer Vorschlag; Alternative durch Team zu wählen |
| **A-V06** | Gleichzeitige freigabereife Stationschargen werden deterministisch nach frühestem Auslöser, bei Gleichstand nach Stationskennung betrachtet, ohne Fahrzeugzuordnung zu ändern. | Verfahrensvergleich bei Ressourcenkonkurrenz | V2, V3, V4 | Neuer Vorschlag |
| **A-V07** | Abgelaufene Wartefrist beendet nur absichtliches Regelwarten; fehlt Material oder Box, bleibt eine separat dokumentierte Blockade bestehen. | Keine falsche Aussage über maximale physische Lieferzeit | V2 bis V4 | Neuer Vorschlag zur expliziten Semantik |
| **A-V08** | Ankunftsprognosen dürfen nur für nachweislich bekannte Werkstücke verwendet werden; unbekannter künftiger Bedarf wird nicht aus dem Simulationsverlauf gelesen. | Vermeidung perfekter Zukunftsinformation | V3, K1, K2 | Neuer Vorschlag als Informationsprinzip |
| **A-V09** | Sobald für einen Satz eine Charge gebunden ist, werden Satzzuordnung, Bestand und Box bis zum vorgesehenen Ausführungsabschluss nicht mehr durch V0 bis V4 zurückgenommen. | Vermeidung verdeckter Neuoptimierung | Alle V | Explizite Präzisierung einer bestehenden Vorgabe |
| **A-V10** | Für unbekannte Bedarfstermine in K2 gilt im Abgrenzungsvorschlag dieselbe feste Basisfrist wie in der zeitbasierten V3-Variante. Ob diese Vergleichsbasis gewählt wird, ist offen. | K2 darf fehlende Information nicht ignorieren | K2 | Neuer Vorschlag |
| **A-V11** | Erstmals festgestellte Erfüllbarkeit und gesetzte Fristen müssen je Anforderung historisch verfügbar bleiben; interne Verfahrenshaltung oder Bereitstellung über `zusatz` ist mit AP3/AP4 zu vereinbaren. | Standardzustand enthält diesen Zeitpunkt nicht; kein Fristneustart nach Teilchargen | Zeitbasierte Regeln | Neuer Informations-/Verlaufsvorschlag, nicht implementiert |

**Hinweis zur Statusreinheit:** A-V04 darf nicht rückwirkend als implementiertes Verhalten von V1 gelesen werden. Die Tatsache, dass das Projekt V1 als implementiert beschreibt, beweist keine implementierte Zeitmessung oder einen Timer.

### Verfahrensbezogene Grenzen und Klärungsfragen

#### V0: begrenzte beobachtete MES-Referenz

**Dokumentierter Entwurf:** Je Station eine Charge aus offenen Sätzen, nacheinander RASS1, RASS2, RASS3; Start der nächsten Station erst nach Ablieferung der vorherigen Box. **Ungeklärt:** Überkapazität der ersten Stationscharge, RASS1 mit nicht erfüllbaren Anforderungen, Neustart der Reihenfolge, verlässlich beobachtetes Ende einer Ablieferung. **Abgrenzung:** Aus drei Produkten und sechs beschriebenen Snapshots darf keine generelle MES-Sperre oder MES-Ablaufregel geschlossen werden. **Betroffene Lücken:** L-01, L-04, L-09.

#### V1: implementierte Einzelversorgung

**Implementiert laut Projektkontext:** Nach Eingang/ID sortieren; pro verfügbarer und zulässiger Anforderung eine Einzelcharge; nicht verfügbare überspringen; verfügbare Bestände innerhalb des Aufrufs fortschreiben; bei fehlender Box keine Bindung; früheste Freigabe `jetzt`. **Risiko:** Übersprungene, wiederholt nicht bedienbare Anforderungen können altern und dauerhaft zurückstehen. **Nicht Gegenstand von AP2:** Eine neue Montagepriorität oder eine faire Optimierung der Reihenfolge. **Klärung:** Welches bestehende Ereignis prüft ältere Anforderungen nach Bestandsänderungen erneut? **Betroffene Lücken:** L-05, L-08, L-10.

#### V2: unvollständige Mengenschwellenregel

**Dokumentierter Entwurf:** Schwelle nach belegten Positionen. **Ungeklärt:** Auswahl bei nicht identischen Satzgrößen und unterkompletten Beständen; Restbedarf ohne weiteres Bedarfseingangsereignis. **Neue Vorschläge:** A-V02, A-V03, A-V05; bei Höchstwartezeit den Hybridcharakter offenlegen. **Klärung:** Soll V2a nur bei einem wirklich bekannten Endesignal oder V2b als Mengen-Zeit-Hybrid gelten? **Betroffene Lücken:** L-09 und L-10.

#### V3: Zeit oder Dringlichkeit

**Dokumentierter Entwurf:** Maximale bewusste Wartezeit und/oder Dringlichkeit aus bekanntem Werkstückbedarf. **Ungeklärt:** tatsächliche Ankunftsinformationen, Vorlauf, Sicherheit, Vollboxauslöser, Konkurrenz mehrerer Stationen. **Neue Vorschläge:** A-V04, A-V06, A-V07, A-V08. **Klärung:** Wie wird ein am Fristende mangels Box nicht bindbarer Satz behandelt? Eine spätere Lieferung verletzt nicht automatisch die Verfahrensfrist: Diese beendet nur das bewusste Zurückhalten und ist keine Liefergarantie. Ressourcenblockaden werden separat gemessen. **Betroffene Lücken:** L-02, L-03, L-05, L-06, L-08.

#### V4: Kandidaten ohne Auswahl

**K1:** zusätzliche prognostische Bedarfsinformation und saubere Definition der nächsten möglichen Lieferung nötig. **K2:** verifizierte Ankunftszeiten und realistischer Vorlauf zwingend; A-07 allein nicht ausreichend. **K3:** freie Ressourcen-Zähler liegen konzeptionell bereits vor, aber die Trennschärfe von „Engpass“ ist unklar; eine höhere Schwelle kann den Zustand verschlechtern. Alle Kandidaten müssen unter A-06 und ohne Änderung der Referenzregeln formuliert werden.

**Fachlich bedingte Auswahl zur Diskussion:** K2 kann nur als **Abstimmungsvorschlag** dienen, wenn zusätzlich zur Informationsvoraussetzung die Abgrenzung zu V3 beschlossen wird. Gegenüber einer bereits dringlichkeitsbasierten V3-Regel ist noch keine eigenständige Verbesserung beschrieben. Ist sie nicht erfüllt, darf K2 nicht durch versteckte Verwendung zukünftiger Ereignisse simuliert werden. K3 ist der am ehesten allein aus der aktuellen Schnittstelle formulierbare Kandidat, dessen Schwellwerte und Auswirkungen jedoch genauso unbewiesen bleiben. Keine finale Kandidatenwahl erfolgt in diesem Dokument.

### Informationsverfügbarkeit strikt unterscheiden

| Information | In der beschriebenen Standardschnittstelle? | Zulässige Verwendung |
|---|---|---|
| Aktuelle Zeit | Ja | Neuplanungs- und Fristbezug |
| Offene, noch nicht gebundene Anforderungen | Ja | Satz- und Chargenauswahl |
| Freier, nicht reservierter Bestand nach Teilenummer | Ja | Erfüllbarkeitsprüfung und Reservierung |
| Freie Boxen und weitere freie Ressourcen | Ja, als vorgesehene Felder | Zulässigkeit und aktuelle Kapazität, nicht gleichbedeutend mit garantierter Lieferung |
| Acht-Positions-Kapazität und stationsspezifisch zulässige Teile | Ja | Boxbelegung und Satzprüfung |
| Bekannte erwartete Ankunft eines bereits freigegebenen Werkstücks | **Nicht zugesichert** | Nur nach validierter Datenbereitstellung; denkbares Zusatzfeld |
| Künftig neu eingehende und derzeit unbekannte Anforderungen | Nein | Nicht vorwegnehmen |
| Reine Fahr-/Rückfahrzeit und belegbare kommissionier-/übergabespezifische Vorläufe | **Nicht vollständig gesichert** | Nur mit offen gekennzeichnetem Annahmenstatus |
| Zeitpunkt, ab dem eine zukünftige Materialanlieferung den Bestand erhöht | Nicht ausdrücklich zugesichert | Kein stillschweigendes zusätzliches Neuplanungsereignis erfinden |
| Vollständige historische MES-Zeitreihe | Nein | Kein historischer Wirksamkeitsnachweis |

### Explizite Nichtgleichsetzungen und daraus folgende Grenzen

1. **Materialsatz ist kein Einzelteil.** Fehlendes Display macht den gesamten zugehörigen Satz nicht erfüllbar, obwohl ein Mainboard existiert.
2. **Transportlos ist kein Produktionslos oder Transferlos.** Die hier gewählte Charge ist eine Versorgungseinheit und ändert keine Fertigungsauftragsmenge.
3. **Gebündelte Direktfahrt ist kein Milk-Run.** Die Verfahren entscheiden über Boxinhalt und früheste Freigabe, nicht über einen Mehrstopp-Fahrplan.
4. **Freigabe ist keine Lieferung.** Warten an Kommissionierung, Fahrzeug, Übergabe und auf Leerboxen fällt unter die nachgelagerte Logik.
5. **Reservierter Bestand ist nicht neu beschaffter Bestand.** Die einmal gebundenen Teile stehen nicht noch einmal anderen Anforderungen zur Verfügung.
6. **Maximale Bündelungswartezeit ist keine maximale Lieferzeit.** Ressourcenausfälle, Materialmangel und fehlende Boxen können nach Fristablauf weiter blockieren.
7. **Unbekannte Zukunft ist keine Prognose.** Das spätere Ereignisprotokoll der Simulation darf nicht rückwirkend einem Verfahren als bekannt zugerechnet werden.
8. **Einzelbeobachtung ist keine allgemeine Anlagenregel.** V0 ist als eng begrenzter Referenzentwurf zu dokumentieren.

### Priorisierter Klärungsbedarf für die Teamabstimmung

| Reihenfolge | Teamfrage | Betroffene Kennungen | Konsequenz für die Steckbriefe |
|---|---|---|---|
| 1 | Welche zusätzliche Ankunftsinformation steht **zum Entscheidungszeitpunkt** tatsächlich zur Verfügung? | L-02, L-06, L-10, A-V08 | Entscheidet, ob V3-Dringlichkeit und K1/K2 substanziell umsetzbar sind |
| 2 | Welcher reale Vorlauf besteht aus Kommissionierung, Robotino-Fahrt und Übergabe? | A-07, L-03, L-05 | Verhindert irreführende Rückwärtstermine |
| 3 | Welche Restregel erhält V2, und beginnt ihre Frist erst mit einem erfüllbaren Satz? | A-V04, A-V05, L-09 | Verhindert unbegrenzt zurückgehaltenen Rest |
| 4 | Wie ist die Boxenzahl nach Cache-Box- und Doppelverortungsproblem zu zählen? | A-03, L-07, L-08 | Maßgeblich für alle Bindungen, besonders K3 |
| 5 | Wie funktioniert die Referenz bei Stationsbedarf über acht Positionen? | L-01, L-09 | V0 nur dann außerhalb Beobachtungsfall eindeutig |
| 6 | Welche deterministische Regel gilt für konkurrierende Stationen bei knappen Boxen? | A-V06 | Reproduzierbare Chargenauswahl, keine Fahrzeugoptimierung |
| 7 | Welcher Kandidat soll V4 werden und auf welcher geprüften Informationsbasis? | A-V08, A-V10, L-02, L-03, L-06 | K1/K2/K3-Auswahl bleibt offen |
| 8 | Welche Ereignisart löst erneut die Prüfung vormals fehlteiliger Sätze aus? | L-10, A-02 | Vermeidet offen gebliebene Anforderungen ohne neue Prüfung |

### Präzisierung von Timer und Zuständigkeit

Die gemeinsame [Frist- und Zuständigkeitsbeschreibung](planungsverfahren.md#verfahrensfrist-messung-und-zuständigkeit) konkretisiert die Vorschläge A-V04, A-V07 und A-V11. Gemessene Bündelungswartezeit folgt weiterhin unverändert der bestehenden Rangfolge **Bestand → Box → Bündelung** in [kennzahlen.md](kennzahlen.md#2-wartezeit-zerlegung). Der Verlauf einer Frist ist keine Messung dieser Wartezeit. Das Verfahren verwendet lokale Arbeitszähler; erst die Simulation reserviert verbindlich.

### Offene Teamentscheidung zur V3/K2-Abgrenzung

Der [Abgrenzungsvorschlag](planungsverfahren.md#offene-teamentscheidung-abgrenzung-v3-und-k2) verwendet eine zeitbasierte V3-Basis und ergänzt in K2 die bedarfsabhängige Verkürzung ihrer festen Frist. Die bisherige V3-Dringlichkeitsvariante bleibt bis zur Entscheidung als dokumentierter Entwurf erkennbar. Wird sie als Vergleichsbasis beibehalten, fehlt K2 noch ein eigenständiger Verbesserungsmechanismus. Keine Auswahl oder Einschränkung ist hiermit beschlossen.
