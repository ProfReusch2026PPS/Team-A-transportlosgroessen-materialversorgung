# Kennzahlen

Verantwortlich: AP5. Alle Kennzahlen werden ausschließlich aus dem Ereignisprotokoll berechnet (`src/matsim/kennzahlen/ereignisprotokoll.py`). Zeiten in Sekunden. Stand: Definitionen als Entwurf, Berechnung noch nicht umgesetzt.

Kennzahlen brauchen definierte Zeit-, Mengen- und Zustandsdaten; die Lehrunterlagen verweisen dafür auf [ISO 22400] ([Kapitel 12](../12-smart-factory-mes-und-zielorientierte-prozessverbesserung.md), Abschnitt „Ereignisdaten statt nur Bestandsaufnahme“). Zu jeder Kennzahl gehört die kritische Frage, was genau gezählt wird ([Kapitel 06](../06-auftragskoordination-bestand-controlling.md), Abschnitt „PPS-Controlling“).

## 1. Kennzahlen

| Nr. | Kennzahl | Definition | Formel | Abgrenzung |
|---|---|---|---|---|
| K1 | Transportzahl | Anzahl der Hintransporte im Auswertungszeitraum | Anzahl `transport_beginn` | Leerboxrückführungen werden getrennt gezählt (Anzahl `leerbox_rueck_beginn`) |
| K2 | Fahrzeugbelegungszeit | Zeit, in der Fahrzeuge an einen Auftrag gebunden sind | Summe über alle Fahrzeuge und Aufträge: Freigabe minus Bindung | enthält kein Warten vor vollem Zielpuffer: Die Box wartet darauf an der Kommissionierung, ohne Fahrzeug (A-12); Hin- und Rückfahrt getrennt ausweisen |
| K3 | Boxauslastung | Anteil belegter Boxpositionen je Hintransport | belegte Positionen / 8, gemittelt über die Hintransporte | zusätzlich Verteilung angeben, nicht nur den Mittelwert |
| K4 | Zeit bis zur Materialbereitstellung | je Anforderung: Zeit vom Bedarfseingang bis zur Lieferung am Übergabeplatz | t(`lieferung`) − t(`bedarf_eingang`) | Median, Mittel und 90-%-Quantil je Station |
| K5 | Materialbedingte Montageverzögerung | je Anforderung: Verzögerung des Montagebeginns, die auf fehlendes Material entfällt | t(`montage_beginn`) − t(erste `werkstueck_ankunft` an der Station), sofern bei der ersten Ankunft der Satz fehlte; sonst 0 | Verzögerung durch belegte Station oder laufende Vorgängerarbeit zählt nicht dazu |
| K6 | Offener Restbedarf | Anforderungen, die am Laufende nicht geliefert sind | Anzahl und Liste mit letztem Zustand | getrennt nach „nicht gebunden“, „in Kommissionierung“, „unterwegs“ |
| K7 | Wartezeit-Zerlegung | je Anforderung die Wartezeit je Ursache | Summe der Intervalle `warten_beginn` bis `warten_ende` je Ursache | Regel in Abschnitt 2 |
| K8 | Verpasste Bearbeitungsmöglichkeiten | je Station: Werkstückankünfte, bei denen der Satz fehlte | Anzahl `weiterfahrt_materialmangel` | getrennt von K9 |
| K9 | Tatsächlicher Stationsstillstand | je Station: Zeit ohne Arbeit | Laufzeit minus Summe der Intervalle `montage_beginn` bis `montage_ende` | zusätzlich der materialbedingte Anteil: Stillstandszeit, in der ein Werkstück verfügbar gewesen wäre und nur der Satz fehlte |

Ergänzend zu berichten: Zahl erledigter Montagevorgänge, Laufzeit bis zum Endkriterium, Stillstände ohne Fortschritt.

## 2. Wartezeit-Zerlegung

Jede Wartezeit eines Satzes wird genau einer Ursache zugeordnet. Die Zeit vom Bedarfseingang bis zur Lieferung zerfällt in Bearbeitung (Picken, Fahren) und Warten. Für das Warten gilt:

| Phase des Satzes | Mögliche Ursachen | Zuordnung |
|---|---|---|
| vor der Bindung in eine Charge | Bestand, Box, Bündelung | Rangfolge, siehe unten |
| gebunden, wartet auf den Kommissionierplatz und den Vorlauf | Kommissionierung | eindeutig |
| in der Box, während andere Teile der Charge gepickt werden | Kommissionierung | eindeutig; zusätzlich als „bündelungsbedingte Pickzeit“ auswertbar |
| Box fertig, kein Übergabeplatz frei (die Box wartet an der Kommissionierung, A-12) | Stationskapazität | eindeutig |
| Übergabeplatz reserviert, wartet auf ein Fahrzeug | Transport | eindeutig |

**Rangfolge vor der Bindung**, wenn mehrere Ursachen gleichzeitig vorliegen:

1. **Bestand:** Mindestens eine Komponente des Satzes ist nicht frei verfügbar.
2. **Box:** Bestand ist da, aber keine Box ist frei.
3. **Bündelung:** Bestand und Box sind da; der Satz könnte sofort als eigene Charge gebunden werden, das Verfahren wartet aber.

Begründung: Bündelungswarten ist die einzige freiwillige Wartezeit. Sie soll nur dann gezählt werden, wenn das Verfahren tatsächlich eine Wahl hatte. Die Simulation wechselt die Ursache, sobald sich die Lage ändert (`warten_ende` mit alter, `warten_beginn` mit neuer Ursache zum selben Zeitpunkt). Ein belegter Kommissionierplatz oder ein fehlendes Fahrzeug vor der Bindung zählt nicht als eigene Ursache, weil eine Charge auch bei belegtem Platz gebunden werden kann.

Prüfung: Für jede gelieferte Anforderung gilt K4 = Summe der Wartezeiten aller Ursachen + Pickzeit der eigenen Teile + Fahrzeit. Diese Gleichung ist Teil der unabhängigen Prüfung.

## 3. Verpasste Bearbeitungsmöglichkeit gegen Stationsstillstand

- **Verpasste Bearbeitungsmöglichkeit (K8):** Ein Werkstück war an der Station, der Satz fehlte, das Werkstück fuhr weiter. Das ist ein Ereignis am Werkstück.
- **Tatsächlicher Stationsstillstand (K9):** Die Station hatte keine Arbeit. Das ist ein Zustand der Station über die Zeit.

Beide fallen nicht zusammen: Eine Station kann eine Möglichkeit verpassen und trotzdem mit einem anderen Werkstück arbeiten; sie kann auch stillstehen, ohne dass Material fehlt, weil kein Werkstück da ist.

## 4. Auswertungsregeln

- Verglichen wird nur innerhalb eines Szenarios mit denselben Eingangs- und Dauerverläufen.
- Bei zufälligen Dauern: Mittelwert über die Replikationen mit Streuungsangabe; gepaarter Vergleich je Seed.
- Die Einschwingphase des Szenarios wird aus Zeitkennzahlen ausgeschlossen, nicht aus der Mengenbilanz.
- Kennzahlen eines Laufs werden nur berichtet, wenn die unabhängige Prüfung keinen Verstoß meldet.
