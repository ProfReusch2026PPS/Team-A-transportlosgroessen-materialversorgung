# Planungsverfahren

Verantwortlich: AP2 (Steckbriefe, Einordnung), AP4 (Umsetzung). Stand: Entwurf. Parameterwerte sind noch nicht festgelegt.

## 1. Einordnung

Die Entscheidung über die Anzahl gemeinsam gelieferter Materialsätze ist eine Losgrößenentscheidung für den innerbetrieblichen Transport. Die Lehrunterlagen liefern dafür drei Bezüge:

- **Materialbereitstellung:** Sie entscheidet, wann, wo und in welcher Menge Material an der Verbrauchsstelle verfügbar ist ([Kapitel 11](../11-produktionslogistik-materialfluss-und-synchrones-produktionssystem.md), Abschnitt „Materialbereitstellung“). Einzelversorgung entspricht einer bedarfssynchronen Bereitstellung mit geringen Puffern, Bündelung nähert sich einem Routenzug, dessen Takt zur Verbrauchsrate passen muss. Die Einordnung von JIT und bedarfssynchroner Versorgung stützt sich dort auf [Schönsleben 2024, S. 293-334].
- **Losgröße:** Lot-for-Lot hält den Bestand niedrig und erzeugt viele Vorgänge; feste Lose sind einfach, aber nicht bedarfsgerecht ([Kapitel 04](../04-produktionsbedarfs-und-mengenplanung.md), Abschnitt „Losgrößenverfahren“, mit Verweis auf [Schuh/Stich 2012a, S. 215-216]). V1 ist das Gegenstück zu Lot-for-Lot, V2 das zu einer festen Losgröße.
- **Zielkonflikte:** Große Lose senken Wechselkosten, erhöhen aber Bestand (Nr. 14) und verschlechtern Reaktionsfähigkeit und Durchlaufzeit (Nr. 15); hohe Auslastung erzeugt Warteschlangen (Nr. 16); Bestand schützt die termingerechte Bereitstellung (Nr. 7) ([Kapitel 13](../13-hannoveraner-lieferkettenmodell-und-logistische-zielkonflikte.md), Abschnitt „Die 19 zentralen PPS-Zielkonflikte“; Seitenanker dort: Nr. 6-8 [Schmidt/Nyhuis 2021, S. 115-124], Nr. 14-16 [Schmidt/Nyhuis 2021, S. 141-151]).

Übertragung auf unser Problem: Der „Auftragswechsel“ ist der Transport, der „Bestand“ ist Material, das in einer wartenden Box oder am Übergabeplatz gebunden ist, die „Logistikleistung“ ist die Zeit bis zur Materialbereitstellung. Diese Übertragung ist unsere Auslegung und in der Hausarbeit zu begründen.

Zwei weitere Bezüge sind für alle Verfahren bindend:

- **Reservierung:** Physisch vorhandenes Material ist nicht automatisch frei verfügbar; reservierter Bestand, der als frei behandelt wird, erzeugt Scheindeckung und spätere Fehlteile ([Kapitel 04](../04-produktionsbedarfs-und-mengenplanung.md), Abschnitt „Dispositives Konto und Reservierung“, mit [Scheer 2025, S. 97-99]).
- **Zuordnung:** Bei der Losbildung geht ohne Zusatzbeziehung verloren, welcher Bedarf welches Los verursacht hat ([Kapitel 04](../04-produktionsbedarfs-und-mengenplanung.md), Abschnitt „Bedarfsverfolgung und Pegging“, mit [Scheer 2025, S. 99-106]). Deshalb bleibt jeder Satz in der Charge seiner Anforderung zugeordnet.

Die Referenzregeln sind nicht Gegenstand des Vergleichs. Für ihre Einordnung dienen [Kapitel 05](../05-eigenfertigungsplanung-und-steuerung.md), Abschnitte „Vertiefung: Verfügbarkeitsprüfung und Fehlteile“ (Materialzustände frei, reserviert, unterwegs, fehlend), „Vertiefung: Auftragsfreigabe als WIP-Regelkreis“ und „Vertiefung: Reihenfolgeregeln richtig interpretieren“ (mit [Lödding 2016, S. 507-523]).

## 2. Entscheidungsmodell

| Element | Festlegung |
|---|---|
| Entscheidungsgrößen | je Planungsanlass: welche offenen Sätze bilden jetzt eine Charge, und ab wann darf sie bereitgestellt und versendet werden |
| Ziele | geringer Transportaufwand, kurze Zeit bis zur Materialbereitstellung, geringe materialbedingte Montageverzögerung; Zielhierarchie legt das Team fest |
| Nebenbedingungen | nur vollständige Sätze; höchstens 8 Boxpositionen; nur Sätze einer Station je Charge (A-06); nur freier, nicht reservierter Bestand; freie Box erforderlich; Satz bleibt seiner Anforderung zugeordnet |
| Entscheidungshorizont | der zum Anlass bekannte Zustand; keine Vorschau auf künftige Bedarfe |
| Modellgrenze | Produktionsabschnitt RASS1 bis RASS3; Referenzregeln fest |

## 3. Steckbriefe

Schema nach [Kapitel 13](../13-hannoveraner-lieferkettenmodell-und-logistische-zielkonflikte.md), Abschnitt „Aufgabensteckbrief als Lernschema“ (dort mit [Schmidt/Nyhuis 2021, S. 165-208]): Aufgabe, Eingaben, Ergebnis, Verfahren, Zielkonflikt, Rückkopplung.

### V0 Referenz (beobachtetes MES-Verhalten)

| Feld | Inhalt |
|---|---|
| Aufgabe | den Ablauf vom 09.11.2026 nachbilden, um das Modell zu validieren |
| Eingaben | offene Sätze je Station, freie Box |
| Ergebnis | je Station eine Charge mit allen offenen Sätzen; nächste Station erst nach Ablieferung der vorherigen Box |
| Verfahren | feste Stationsfolge RASS1, RASS2, RASS3, zyklisch |
| Zielkonflikt | wenige Transporte, aber spätere Stationen warten lange (erste Montage RASS3 rund 36 Minuten nach dem Auslagern) |
| Rückkopplung | Abweichung der simulierten von den beobachteten Zeitpunkten |

Umgesetzte Regel (`V0Referenz` in `src/matsim/regeln/verfahren.py`), je Planungsaufruf:

1. Warten, solange eine gebundene Charge noch nicht abgeliefert ist (`zusatz["chargen_in_versorgung"] > 0`, siehe [logikstruktur.md](logikstruktur.md), Abschnitt 4) oder keine Box frei ist.
2. Sonst die Stationen zyklisch durchsuchen, beginnend bei der Station nach der zuletzt bedienten. Bedient wird die erste Station mit mindestens einem versorgbaren Satz.
3. Die Box mit den offenen Sätzen dieser Station in Eingangsfolge füllen, solange Boxpositionen und freier Bestand den vollständigen Satz decken. Ein Satz ohne Bestand wird übersprungen.
4. Passen nicht alle Sätze in die Box, bleibt der Rest offen und kommt in der nächsten Runde an die Reihe (A-09).
5. Höchstens eine Charge je Aufruf, Versand sofort. V0 meldet keine Wartefrist an.

Parameter: `stationsfolge` (optional; ohne Angabe RASS1, RASS2, RASS3). Am Referenzfall mit je drei Sätzen je Station ergibt die Regel drei Chargen in der beobachteten Folge (Test `test_ablauf_09_11_je_station_eine_box_nacheinander`).

Was das MES tut, wenn mehr als 8 Positionen offen sind, ist aus einem Ablauf mit drei Produkten nicht ableitbar. Die historischen Auftragsgrößen enden bei 8 Positionen (B-15). Diese Lücke schließt die Annahme A-09; ebenso ist die Wiederaufnahme bei RASS1 nach RASS3 nicht beobachtet.

### V1 Einzelversorgung

| Feld | Inhalt |
|---|---|
| Aufgabe | jeden vollständigen Satz frühestmöglich versorgen |
| Eingaben | offene Sätze in Eingangsfolge, freier Bestand, freie Box |
| Ergebnis | je Satz eine Charge mit sofortigem Versand |
| Verfahren | Lot-for-Lot in Eingangsfolge |
| Zielkonflikt | kürzeste Bündelungswartezeit gegen höchste Transportzahl, höchsten Boxbedarf und geringste Boxauslastung |
| Rückkopplung | Transportzahl, Boxauslastung, Warten auf Box und Fahrzeug |

### V2 Füllschwelle

| Feld | Inhalt |
|---|---|
| Aufgabe | Sätze einer Station sammeln, bis eine festgelegte Füllschwelle erreicht ist |
| Eingaben | offene Sätze je Station, Füllschwelle in Positionen, freier Bestand, freie Box |
| Ergebnis | Charge, sobald die Schwelle erreicht ist |
| Verfahren | feste Losgröße in Boxpositionen |
| Zielkonflikt | hohe Boxauslastung und wenige Transporte gegen Bündelungswarten bei schwachem Bedarf |
| Rückkopplung | Bündelungswartezeit, Boxauslastung, verpasste Bearbeitungsmöglichkeiten |

**Restbedarfsregel (festzulegen, Pflicht):** Unterhalb der Schwelle muss Restbedarf trotzdem bearbeitet werden. Vorschlag zur Entscheidung durch AP4: Eine unvollständig gefüllte Charge wird versendet, wenn für die Station kein weiterer Bedarf mehr eingehen kann (Bedarfsende des Szenarios) oder wenn der älteste Satz eine Höchstwartezeit überschreitet. Die zweite Bedingung macht V2 zu einer Mischform mit V3; die Abgrenzung ist dann die Größe der Frist (bei V2 nur als Sicherheitsnetz). Die gewählte Regel wird hier mit Begründung eingetragen.

### V3 Wartezeit oder Dringlichkeit

| Feld | Inhalt |
|---|---|
| Aufgabe | bündeln, aber spätestens nach einer maximalen Wartezeit oder bei erreichter Dringlichkeitsgrenze versenden |
| Eingaben | offene Sätze mit Eingangszeit und Bedarfszeitpunkt, freier Bestand, freie Box |
| Ergebnis | Charge mit allen bis dahin offenen Sätzen der Station |
| Verfahren | Zeitschranke je ältestem Satz oder Dringlichkeit aus dem Produktionsbedarf |
| Zielkonflikt | begrenzte Versorgungszeit gegen schwankende Boxauslastung |
| Rückkopplung | Zeit bis zur Materialbereitstellung, materialbedingte Montageverzögerung |

Die Dringlichkeitsgrenze muss aus dem Produktionsbedarf abgeleitet sein, zum Beispiel aus der erwarteten nächsten Werkstückankunft an der Station abzüglich Kommissionier- und Transportzeit. Frei gesetzte Dringlichkeitspunkte sind nicht zulässig. Welche Vorschau auf Werkstückankünfte dem Verfahren zur Verfügung steht, vereinbaren AP3 und AP4 über das Feld `zusatz` des Planungszustands.

### V4 Eigene Verbesserung (Platzhalter)

Drei Kandidaten. Die Auswahl trifft das Team; danach wird der Steckbrief ausgefüllt.

| Kandidat | Idee | Begründung | Risiko |
|---|---|---|---|
| K1 Bedarfsgekoppelte Füllschwelle (in V2) | Die Schwelle ist nicht fest, sondern richtet sich nach den Werkstücken, die bis zur nächsten möglichen Lieferung an der Station erwartet werden | Eine feste Schwelle wartet bei schwachem Bedarf zu lange und versendet bei starkem Bedarf zu früh. Die Kopplung an den Bedarf folgt dem Gedanken, dass der Versorgungstakt zur Verbrauchsrate passen muss (Kapitel 11, Abschnitt „Materialbereitstellung“) | braucht eine belastbare Vorschau auf Werkstückankünfte |
| K2 Rückwärtsterminierte Dringlichkeit mit Auffüllen (in V3) | Versandzeitpunkt = spätester Zeitpunkt, zu dem der dringendste Satz noch rechtzeitig vor seinem Werkstück ankommt; bis dahin wird die Box mit weiteren Sätzen derselben Station aufgefüllt | nutzt die Wartezeit, die ohnehin unschädlich ist, zum Bündeln; trennt unschädliches von schädlichem Bündelungswarten | empfindlich gegen unsichere Transport- und Kommissionierzeiten; braucht einen Sicherheitszuschlag |
| K3 Engpassabhängige Bündelung (in V2 oder V3) | Bei freier Versorgungskapazität einzeln oder klein liefern, bei knappen Boxen, belegtem Kommissionierplatz oder belegten Fahrzeugen stärker bündeln | Bündeln lohnt sich dort, wo Transport- und Boxkapazität der Engpass ist; ohne Engpass verzögert es nur (Zielkonflikt Nr. 15 und 16) | Umschaltregel braucht Schwellen, die auf dem Kalibrierungsszenario gewählt werden müssen |

## 4. Enumeration eines kleinen Falls

Verpflichtend laut gemeinsamer Anforderung: Für einen kleinen Fall werden alle zulässigen Chargenbildungen vollständig aufgezählt und mit dem Ergebnis des Verfahrens verglichen. Vorschlag: vier bis sechs Sätze an zwei Stationen, eine Entscheidungssituation. Zu dokumentieren sind die Zahl der Alternativen, die Zielgröße und der Entscheidungshorizont. Eine optimale Einzelentscheidung beweist keinen insgesamt optimalen Ablauf.

## 5. Parameter

| Verfahren | Parameter | Wertebereich | Festlegung |
|---|---|---|---|
| V2 | `fuellschwelle_positionen` | 2 bis 8, je Station an der Satzgröße auszurichten | auf dem Szenario `kalibrierung` |
| V2 | Höchstwartezeit der Restbedarfsregel | offen | auf dem Szenario `kalibrierung` |
| V3 | `max_wartezeit_s` oder Dringlichkeitsregel | offen | auf dem Szenario `kalibrierung` |
| V4 | je nach Kandidat | offen | auf dem Szenario `kalibrierung` |

Parameterwahl und abschließende Prüfung erfolgen auf getrennten Szenarien.
