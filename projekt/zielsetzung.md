# Zielsetzung

Projekt: Transportlosgrößen und Materialversorgung (Team A), Prüfungsprojekt im Modul Produktionsplanung und -steuerung, Operations Management in der IoT Factory.
Stand: Entwurf vom 24.11.2026. Das Team bestätigt den Entwurf gemeinsam. Bis dahin sind die als „Vorschlag“ markierten Punkte offen.

Dieses Dokument fasst zusammen, was das Projekt erreichen soll und woran wir den Erfolg messen. Wie wir dabei vorgehen, steht in den Fachdokumenten:

- Originalauftrag: [aufgabenstellung.md](aufgabenstellung.md)
- Zuordnung der Anforderungen R-01 bis R-53: [anforderungsmatrix.md](anforderungsmatrix.md)
- Verfahren: [planungsverfahren.md](planungsverfahren.md)
- Versuche: [versuchsplan.md](versuchsplan.md)
- Kennzahlen: [kennzahlen.md](kennzahlen.md)
- Arbeitspakete: [arbeitspakete.md](arbeitspakete.md)
- Annahmen und Datenlücken: [annahmen-und-datenluecken.md](annahmen-und-datenluecken.md)

## 1. Ausgangslage

Die Roboter-Montagestationen RASS1, RASS2 und RASS3 der Laborfabrik bekommen ihre Komponenten in Transportboxen. Die Boxen werden an einer Kommissionierstation gefüllt und von Robotinos (fahrerlosen Transportfahrzeugen) zur Station gebracht. Am 09.11.2026 hat das Festo-MES4 (Manufacturing Execution System) je Station alle offenen Materialsätze in eine Box gepackt und die Stationen nacheinander versorgt. Bei drei Produkten begann die erste Montage an RASS3 deshalb erst rund 36 Minuten nach dem Auslagern.

Dahinter steht ein klassischer Zielkonflikt der Losgrößenplanung:

- **Bündeln** spart Transporte und Boxen je Materialsatz. Dafür warten die Sätze, bis die Box voll genug ist, und das Material kommt später an der Station an.
- **Einzeln liefern** versorgt schnell, kostet aber mehr Fahrten, mehr Boxen und mehr Übergabeplätze.
- Kommt ein Werkstück an der Station an und der Satz fehlt, fährt das Werkstück weiter (A-01). Eine verspätete Lieferung verzögert also direkt die Montage.

Große Lose senken den Aufwand je Vorgang. Sie erhöhen aber Bestand und Durchlaufzeit und verschlechtern die Reaktionsfähigkeit [Schmidt/Nyhuis 2021, S. 141-151]. Der Versorgungstakt muss zur Verbrauchsrate an der Station passen [Schönsleben 2024, S. 293-334].

## 2. Leitfrage

> **Wie viele vollständige Materialsätze sollen gemeinsam in einer Box zu einer Montagestation geliefert werden, und wann sollen sie bereitgestellt und versendet werden, damit Transportaufwand, Bündelungswarten und materialbedingte Montageverzögerung in einem begründeten Verhältnis stehen?**

Aus der Leitfrage folgen vier Teilfragen:

1. **Daten:** Was lässt sich aus den MES-Daten belastbar über Materialpfad, Komponentenbedarfe, Box- und Pufferbelegung, Reservierungen und Zeitansätze sagen, und wo liegen Datenlücken?
2. **Entscheidung:** Wie lässt sich die Chargenbildung als Entscheidungsmodell beschreiben, also mit Entscheidungsgrößen, Zielen, Nebenbedingungen, Modellgrenze und Entscheidungshorizont?
3. **Verfahren:** Wie schneiden Einzelversorgung, Bündelung bis zu einer Füllschwelle und Bündelung mit Wartezeit- oder Dringlichkeitsgrenze im Vergleich ab, und wie viel bringt unsere eigene Verbesserung?
4. **Gültigkeit:** Unter welchen Bedingungen gilt das Ergebnis, also bei welcher Bedarfslage, welchem Box- und Platzangebot und welchen unsicheren Zeitansätzen?

## 3. Oberziel

Wir wollen eine **begründete Handlungsempfehlung für die Transportlosgröße und den Versandzeitpunkt** in der Materialversorgung von RASS1 bis RASS3 geben. Grundlage dafür ist:

- eine geprüfte Analyse der MES-Daten,
- austauschbare Planungsverfahren in Python,
- eine selbst entwickelte ereignisdiskrete SimPy-Simulation,
- eine unabhängige Prüfung der Simulationsergebnisse.

Die Empfehlung nennt ihre Gültigkeitsbedingungen. Sie ist so dokumentiert, dass Dritte jedes Ergebnis mit einem Befehl reproduzieren können.

## 4. Sachziele

### 4.1 Ergebnisziele (Abgaben)

| Nr. | Ziel | Erfüllt, wenn | Anforderungen |
|---|---|---|---|
| Z-E1 | **Hausarbeit** mit Datenqualitätsanalyse, Entscheidungsmodell, begründeten Verfahren, Simulationsmodell, Ergebnissen und Handlungsempfehlung | alle Gliederungspunkte aus `report/` sind ausgearbeitet; jede Fachaussage hat einen Kurzbeleg; die Empfehlung nennt Gültigkeitsbedingungen | R-02, R-46, R-47 |
| Z-E2 | **Lauffähiger Python-Code**: Planung, Simulation und Prüfung getrennt aufrufbar | auf einem frischen Klon laufen Installation, `pytest`, `ruff check .` und der Beispielaufruf je Baustein ohne Fehler; Ein- und Ausgaben sind dokumentiert | R-50 |
| Z-E3 | **Reproduzierbare Nachweise**: Datenherkunft, Befundregister, Parameter, Ereignisprotokolle, Basis- und Stressvergleiche, Sensitivitätsanalyse | ein Befehl erzeugt alle Läufe eines Szenarios neu; gleiche Seeds liefern identische Protokolle | R-44, R-51 bis R-53 |

### 4.2 Fachliche Teilziele

**T1 Datengrundlage (AP1)**

- Befundregister zu den relevanten MES-Tabellen mit Prüfregel, geprüfter Anzahl, Anzahl und Anteil auffälliger Datensätze, Beispielreferenz, Behandlung und Modellfolge.
- Ausführbare Prüfungen und mindestens eine manuelle Stichprobe. Die Rohdaten bleiben unverändert und sind über Prüfsummen belegt.
- Box und Inhalt werden nicht doppelt gezählt. Reservierungen ohne zuordenbaren Auftrag gelten nicht als freier Bestand.
- Jeder Wert in `config/anlage.yaml` hat `herkunft` und `beleg`. MES-Wert, abgeleiteter Wert, Beobachtung und Szenarioannahme sind unterschieden.
- Datenlücken (L-01 bis L-10) sind geklärt oder ausdrücklich als Lücke ausgewiesen.

**T2 Entscheidungsmodell und Methodik (AP2)**

- Entscheidungsmodell vollständig: Entscheidungsgrößen, Ziele mit Zielhierarchie, Nebenbedingungen, Modellgrenze und Entscheidungshorizont.
- Steckbrief je Verfahren nach dem Aufgabensteckbrief der Lehrunterlagen [Schmidt/Nyhuis 2021, S. 165-208].
- Gepflegter Annahmenkatalog. Jede Annahme, die in Code oder Konfiguration einfließt, steht dort mit Begründung.

**T3 Simulationsmodell (AP3)**

- Das SimPy-Modell bildet die ganze Prozesskette ab: Bedarfseingang, Satz- und Chargenbildung, Reservierung, Kommissionierung, Hintransport, Lieferung, Montage mit Komponentenverbrauch und Leerboxrückführung.
- Kommissionierplatz, Boxbestand, Fahrzeuge und Übergabeplätze sind begrenzt und bleiben während der Nutzung gebunden.
- Eine Lieferung beeinflusst nachweislich, ob und wann montiert wird.
- Fehlt ein Satz, fährt das Werkstück weiter.
- Geplant wird nur bei Bedarfseingang, Ablauf einer Wartefrist und Freigabe relevanter Kapazität. Gebundene Chargen werden nicht umgeplant.

**T4 Planungsverfahren (AP4)**

- V0 (beobachtetes MES-Verhalten), V1 (Einzelversorgung), V2 (Füllschwelle) und V3 (Wartezeit oder Dringlichkeit) laufen hinter der gemeinsamen Schnittstelle `entscheide(zustand, anlass)`.
- Jede Bündelungsregel hat eine verbindliche Restbedarfsregel: Kein Satz bleibt dauerhaft liegen.
- V4 ist eine eigene Verbesserung innerhalb von V2 oder V3, ausgewählt aus den Kandidaten K1 bis K3 und fachlich begründet.
- Ein kleiner Fall wird vollständig enumeriert, also alle zulässigen Chargenbildungen aufgezählt und mit dem Verfahren verglichen. Dokumentiert sind Alternativenzahl, Zielgröße und Horizont.

**T5 Versuche und Auswertung (AP5)**

- Basisfall, Bedarfsspitze und knappe Boxen oder Übergabeplätze, jeweils mit identischen, vorab erzeugten Eingangs- und Dauerverläufen für alle Verfahren.
- Sensitivitätsanalyse zu einem unsicheren Transport- oder Kommissionierzeitansatz, mit mehreren Replikationen und Unsicherheitsangaben.
- Die Kennzahlen K1 bis K9 werden nur aus dem Ereignisprotokoll berechnet. Die Wartezeit-Zerlegung geht vollständig auf.
- Unabhängige Prüfregeln (Kapazitäten, Mengenbilanz, Vorgängerbeziehungen, Doppelbindungen) erkennen jeden absichtlich eingebauten Fehler.
- V0 ist gegen den beobachteten Ablauf vom 09.11.2026 validiert.

## 5. Zielgrößen und Zielhierarchie

### 5.1 Zielgrößen

Die Verfahren werden an den Kennzahlen aus [kennzahlen.md](kennzahlen.md) gemessen.

| Zielrichtung | Kennzahl | Bedeutung für die Entscheidung |
|---|---|---|
| minimieren | K5 materialbedingte Montageverzögerung | Folge einer späten Versorgung für die Produktion |
| minimieren | K8 verpasste Bearbeitungsmöglichkeiten | Werkstücke, die wegen fehlenden Materials weiterfahren |
| minimieren | K4 Zeit bis zur Materialbereitstellung | Reaktionsfähigkeit der Versorgung (Median, Mittelwert, 90-%-Quantil je Station) |
| minimieren | K1 Transportzahl, K2 Fahrzeugbelegungszeit | Transportaufwand |
| maximieren | K3 Boxauslastung | Nutzung der knappen Boxen |
| muss 0 sein | K6 offener Restbedarf am Laufende im Basisfall | Vollständigkeit der Versorgung |
| erklären | K7 Wartezeit-Zerlegung, K9 Stationsstillstand | trennt Bündelungswarten von Warten auf Bestand, Box, Kommissionierung, Transport und Stationskapazität |

### 5.2 Zielhierarchie (Vorschlag, Entscheidung durch das Team)

1. **Restriktionen sind einzuhalten.** Es gibt nur vollständige Sätze in zulässigen Boxen. Die Mengenbilanz bleibt erhalten, und eine Reservierung ist kein zusätzlicher Bestand. Es gibt keine Doppelbindungen. Kein Restbedarf bleibt dauerhaft liegen. Ein Verfahren, das hier verletzt, scheidet aus.
2. **Hauptziel: die Montage nicht durch Material bremsen.** Das heißt K5 und K8 möglichst klein. Die Versorgung dient der Montage, und genau diese Folge bewertet die Aufgabenstellung.
3. **Nebenziel: Transportaufwand senken.** Das heißt K1 und K2 klein, K3 hoch, solange das Hauptziel nicht spürbar leidet.
4. **Erklärungsziel:** K4 und K7 zeigen, warum ein Verfahren besser oder schlechter abschneidet.

Die Verfahren werden nicht zu einer gewichteten Gesamtzahl verrechnet. Wir stellen die Ergebnisse als Abwägung dar, zum Beispiel als Gegenüberstellung von Transportzahl und Montageverzögerung je Verfahren und Szenario. Gewichte wären hier willkürlich gewählt und kaum zu begründen.

## 6. Rahmenbedingungen

Diese Punkte sind vorgegeben und nicht Gegenstand der Optimierung.

- Ein Materialsatz ist nur vollständig brauchbar. Benötigt RASS1 Mainboard und Display, müssen beide in derselben Box ankommen.
- Höchstens 8 Positionen je Box. Nur Sätze einer Station je Charge (A-06, Bestätigung offen).
- Jeder Satz bleibt seiner Anforderung zugeordnet.
- Montagepriorität, Auftragsfreigabe, Fahrzeugzuordnung, Leerboxrückführung, die Übergaberegel bei vollem Zielpuffer und die Weiterfahrt bei Materialmangel sind feste Referenzregeln. Sie sind in allen Vergleichen gleich.
- Die Bearbeitung erfolgt offline. Der Zugriff auf das MES ist nur lesend. Änderungen am produktiven System sind nicht Teil der Aufgabe.
- Der Hauptvergleich verwendet feste Dauern. Parameter werden nur auf dem Szenario `kalibrierung` gewählt und danach eingefroren.

## 7. Abgrenzung: was das Projekt nicht leistet

- **Keine Optimierung der Referenzregeln.** Reihenfolge, Freigabe, Fahrzeugzuordnung und Leerboxrückführung bleiben fest.
- **Kein Eingriff in das MES oder die Laborfabrik.** Es werden keine Regeln am produktiven System umgestellt und keine schreibenden Datenbankzugriffe gemacht.
- **Kein Nachweis eines global optimalen Ablaufs.** Die Enumeration bewertet eine einzelne Entscheidungssituation. Eine optimale Einzelentscheidung beweist keinen insgesamt optimalen Ablauf.
- **Keine Prognose künftiger Bedarfe.** Die Bedarfsmuster der Szenarien sind Szenarioannahmen (L-09), keine Vorhersage des Laborbetriebs.
- **Keine Rekonstruktion historischer Bestandsverläufe.** Dafür fehlen geeignete Aufzeichnungen (L-04).
- **Modellgrenze:** Produktionsabschnitt RASS1 bis RASS3 mit Kommissionierplatz, Boxen, Fahrzeugen und Übergabeplätzen. Vorgelagerte Fertigung und Lager werden nur als Bestand und Bedarfseingang abgebildet.

## 8. Qualitätsziele

- **Nachvollziehbarkeit:** Jede Zahl im Bericht lässt sich auf einen Lauf, einen Seed und ein Szenario zurückführen. Jeder Parameter hat Herkunft und Beleg.
- **Trennung der Rollen im Code:** Die Verfahren kennen weder MES-Tabellen noch Simulationscode. Die Prüfung kennt weder Verfahren noch Simulation. Kennzahlen stammen nur aus dem Ereignisprotokoll.
- **Ehrlichkeit der Ergebnisse:** Nicht umgesetzte Funktionen lösen `NotImplementedError` aus. Unzulässige Doppelbindungen werden gemeldet, nicht stillschweigend repariert. Offene Arbeit und Stillstände ohne Fortschritt werden berichtet.
- **Belegpflicht:** Fachaussagen im Kurzbelegformat der Lehrunterlagen. Seitenangaben nur, wenn sie geprüft sind.
- **Datenschutz:** Keine Dumps, keine Zugangsdaten und keine personenbezogenen Tabellen (`tblcustomer`, `tblusercontrol`) im Repo.

## 9. Terminziele

Wir orientieren uns an den Zwischenständen der Aufgabenstellung. Kalenderdaten legt das Team fest.

| Meilenstein | Anker | Ziel erreicht, wenn |
|---|---|---|
| M1 Datenstand und Modellabgrenzung | Ende Woche 2 | Befundregister, `anlage.yaml` mit Herkunft, Modellgrenze und Arbeitsplan liegen vor; V4 und der zweite Stressfall sind entschieden |
| M2 Durchstich | vor Woche 4 | die Simulation läuft mit V1 im Basisfall, schreibt ein Ereignisprotokoll, und die Invarianten-Tests sind scharf |
| M3 Referenzplaner | Ende Woche 4 | V0 bis V3 laufen; V0 ist gegen den 09.11.2026 validiert; die unabhängige Prüfung ist vollständig |
| M4 Verbesserung und Versuche | Wochen 5 bis 6 | V4 ist umgesetzt, die Parameter sind eingefroren, Basis- und Stressfälle sind gelaufen, die Enumeration ist dokumentiert |
| M5 Sensitivität und Auswertung | Woche 7 | das Unsicherheitsszenario mit Replikationen, Ergebnistabellen und Diagrammen liegt vor |
| M6 Abgabe | Ende Woche 8 | Hausarbeit, Code mit Beispielaufruf und reproduzierbare Nachweise sind abgegeben |

## 10. Erfolgskriterien

Das Projekt ist erfolgreich, wenn:

1. alle Anforderungen R-01 bis R-53 in der Anforderungsmatrix den Status „abgeschlossen“ oder eine begründete Ausnahme haben;
2. alle fünf Verfahren in allen Abschluss-Szenarien regulär enden, ohne Verstoß gegen eine Prüfregel und ohne offenen Restbedarf im Basisfall;
3. V0 den beobachteten Ablauf vom 09.11.2026 in Reihenfolge und Größenordnung der Zeitpunkte nachbildet und die Abweichungen erklärt sind;
4. der Vergleich zeigt, wo jedes Verfahren im Zielkonflikt zwischen Transportaufwand und Montageverzögerung steht, und K7 die Unterschiede ursächlich erklärt;
5. die eigene Verbesserung V4 gegenüber ihrem Grundverfahren in mindestens einem Szenario einen nachvollziehbaren Vorteil zeigt, oder begründet dargelegt ist, warum sie das nicht tut (auch ein ehrliches negatives Ergebnis ist ein Ergebnis);
6. die Handlungsempfehlung sagt, welches Verfahren mit welchen Parametern unter welchen Bedingungen zu bevorzugen ist, und wann nicht.

## 11. Risiken für die Zielerreichung

| Risiko | Auswirkung auf die Ziele | Gegenmaßnahme |
|---|---|---|
| Das Referenzpaket des Dozenten fehlt (L-01) | Referenzregeln und Übergabelogik sind unsicher; T3 und M2 verzögern sich | beim Dozenten anfragen; bis dahin dokumentierte Annahmen verwenden und später austauschen |
| Wenige Daten: nur ein Ablauf mit drei Produkten | Zeitansätze und Bedarfsmuster sind schwach belegt | Szenarioannahmen kennzeichnen; Sensitivitätsanalyse auf die unsicherste Größe legen (Transportzeit, A-07) |
| Der Anfangsbestand reicht nur für 4 bis 5 Produkte (A-02) | „Warten auf Bestand“ kann den Vergleich überlagern | im Versuchsplan bewusst entscheiden: Bestand als Annahme erhöhen oder Mangel als Versuchsfaktor ausweisen |
| Dringlichkeitsregeln (V3, V4-K2) brauchen eine Vorschau auf Werkstückankünfte | Verfahren sind ohne Vorschau nicht umsetzbar | Vorschau früh zwischen AP3 und AP4 über `zusatz` vereinbaren |
| Abhängigkeiten zwischen den Paketen (S1 bis S4) | Leerlauf in einzelnen Paketen | Schnittstellen sind festgelegt; AP4 und AP5 arbeiten bis M2 auf handgebauten Zuständen und Protokollen |
