# Versuchsplan

Verantwortlich: AP5. Stand: Schema festgelegt, Zahlenwerte sind Entwürfe (A-08 in [annahmen-und-datenluecken.md](annahmen-und-datenluecken.md)).

## 1. Szenarien

| Szenario | Datei | Faktor gegenüber dem Basisfall | Zweck |
|---|---|---|---|
| Basis | `config/szenarien/basis.yaml` | gleichmäßige Bedarfe, feste Dauern | Abschlussprüfung |
| Stress 1 | `bedarfsspitze.yaml` | zeitlich gebündelte Bedarfe; RASS1 bis RASS3 konkurrieren um Kommissionierplatz, Boxen und Fahrzeuge | Abschlussprüfung |
| Stress 2a | `knappe_boxen.yaml` | weniger freie Transportboxen | Abschlussprüfung |
| Stress 2b | `knappe_uebergabeplaetze.yaml` | ein Übergabeplatz je Station statt zwei | Abschlussprüfung, Alternative zu 2a |
| Unsicherheit | `unsicherheit.yaml` | Kommissionier- und Transportzeit als Verteilung | Sensitivitätsanalyse |
| Kalibrierung | `kalibrierung.yaml` | eigener Bedarfsverlauf | Parameterwahl für V2 bis V4 |

Die Aufgabenstellung verlangt als zweiten Stressfall knappe Boxen **oder** Übergabeplätze. Beide Dateien liegen vor; das Team entscheidet, ob einer oder beide berichtet werden.

## 2. Vergleichsregeln

- Jedes Verfahren (V0 bis V4) läuft in jedem Szenario.
- Innerhalb eines Szenarios sind Eingangsdaten, Abläufe, Ressourcen und Referenzregeln identisch. Es ändern sich nur das Verfahren und die ausgewiesenen Parameter.
- Bedarfseingänge und Dauern werden je Seed **vorab** erzeugt und allen Verfahren unverändert vorgegeben (`erzeuge_verlaeufe` im Runner).
- Der Hauptvergleich (Basis, Stress 1, Stress 2) verwendet feste Dauern und eine Replikation. Nur das Szenario `unsicherheit` verwendet Verteilungen; dann sind mehrere Replikationen und Unsicherheitsangaben Pflicht.
- Parameter werden nur auf `kalibrierung` gewählt und danach für die Abschluss-Szenarien eingefroren.

## 3. Schema der Szenario-Dateien

Geprüft von `matsim.experimente.szenario.pruefe_szenario`.

| Schlüssel | Bedeutung |
|---|---|
| `schema_version` | derzeit 1 |
| `name`, `beschreibung` | eindeutiger Name, ein Satz |
| `zweck` | `abschlusspruefung` oder `parameterwahl` |
| `laufzeit.max_laufzeit_s` | harte Obergrenze der Simulationszeit |
| `laufzeit.einschwingphase_s` | von Zeitkennzahlen ausgeschlossene Anfangsphase |
| `laufzeit.endkriterium` | Bedingung für das reguläre Ende |
| `replikationen.anzahl`, `replikationen.seeds` | Seeds, paarweise verschieden, Anzahl muss passen |
| `bedarf.muster` | `gleichmaessig` oder `spitze`, dazu Mengen und Zwischenankunftszeiten |
| `zeiten.modus` | `fest` oder `verteilung`; bei `verteilung` die Liste der verteilten Parameter |
| `anlage_abweichungen` | Punktpfade aus `config/anlage.yaml` mit abweichendem Wert |
| `verfahren`, `verfahren_parameter` | Kurznamen und Parameter je Verfahren |

## 4. Offene Punkte für AP5

1. **Bedarfsmenge gegen Bestand:** Der belegte Anfangsbestand reicht für 4 bis 5 Produkte (`config/anlage.yaml`, A-02). Die Entwürfe sehen 12 Produkte vor. Entweder wird der Anfangsbestand als Szenarioannahme erhöht oder Bestandsmangel wird bewusst Teil des Versuchs. Die Entscheidung ist zu begründen, weil sie „Warten auf Bestand“ direkt bestimmt.
2. **Bedarfseingang:** Festlegen, ob der Bedarf mit der Auftragsfreigabe, mit dem Auslagern des Werkstücks oder mit einem Vorlauf vor der erwarteten Ankunft an der Station entsteht. Im MES entstand der Kommissionierauftrag für RASS2 erst nach Ablieferung der RASS1-Box (B-08).
3. **Laufdauer und Endkriterium:** Maximale Laufzeit so wählen, dass im Basisfall alle Anforderungen abgeschlossen werden; offene Arbeit und Stillstände ohne Fortschritt berichten.
4. **Einschwingphase:** Bei abschließenden Läufen (endlicher Auftragsvorrat) voraussichtlich 0; zu begründen.
5. **Verteilungen:** AP1 liefert sie aus `tblfinstep` (Kandidaten: empirische Verteilung der OpNo-220-Dauern; indirekte Transportzeit mit q10/q90 = 85/368 s). Die Transportzeit enthält Wartezeiten und ist als solche zu kennzeichnen (L-03).
6. **Stressniveaus:** Werte für knappe Boxen und die Bedarfsspitze so wählen, dass die Kapazitätsgrenze tatsächlich bindet, und das im Ergebnis zeigen.

## 5. Ergebnisablage

`results/<szenario>/<verfahren>/seed_<seed>/` mit `ereignisse.csv`, `kennzahlen.json` und `pruefbericht.json`. Der Ordner `results/` wird nicht versioniert; für die Hausarbeit ausgewählte, kleine Ergebnistabellen kommen nach `data/processed/`.
