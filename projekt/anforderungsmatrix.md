# Anforderungsmatrix

Verantwortlich: AP2. Jede Anforderung aus [aufgabenstellung.md](aufgabenstellung.md) steht in genau einem Arbeitspaket. R-01 bis R-43 stammen aus dem Text zu Team A, R-44 bis R-53 aus den gemeinsamen Anforderungen und Abgaben.

Status: **erfüllt** = Abnahmekriterium des Pakets erreicht; **Schnittstelle** = als Typ, Datei oder Schema festgelegt; **teilweise** = lauffähiger Anfang vorhanden; **Gerüst** = Signatur ohne Logik; **Entwurf** = dokumentiert, noch nicht entschieden; **offen** = noch nichts vorhanden.

## Ziel und Datenanalyse

| Nr. | Anforderung | AP | Nachweis | Status |
|---|---|---|---|---|
| R-01 | Über Anzahl und zulässige Kombination vollständiger Sätze je Box sowie Bereitstellungs- und Versandzeitpunkt entscheiden | AP2 | Entscheidungsmodell in `planungsverfahren.md`, Abschnitt 2 | Entwurf |
| R-02 | Transportaufwand, Bündelungswarten und verzögerte Montage abwägen | AP2 | Zielhierarchie und Handlungsempfehlung in der Hausarbeit | offen |
| R-03 | Materialsatz nur vollständig in derselben Box; Teillieferungen erfüllen den Bedarf nicht | AP4 | `satz_vollstaendig_in_box`, `tests/test_pruefregeln.py`; Einhaltung durch jedes Verfahren | teilweise (Prüfregel fertig, Verfahren Gerüst) |
| R-04 | Mehrere Sätze nur gemeinsam, soweit Boxbelegung und Anlagenregeln es erlauben | AP4 | `pruefe_charge`; Unit-Tests je Verfahren | teilweise (Prüfregel fertig, Verfahren Gerüst) |
| R-05 | Regeln anhand des Materialpfads prüfen und belegen | AP2 | `datenmodell-mes.md`, Abschnitt 5; Annahme A-06 | Entwurf, Bestätigung offen |
| R-06 | Komponentenbedarfe untersuchen | AP1 | Befund B-04, `config/anlage.yaml` | erfüllt |
| R-07 | Box- und Pufferbelegungen untersuchen | AP1 | Befunde B-03, B-09 bis B-11, `matsim.daten.bestand` | erfüllt |
| R-08 | Reservierungen untersuchen | AP1 | Befund B-12, Abschnitt 7 in `datenmodell-mes.md` | erfüllt |
| R-09 | Doppelzählungen von Box und Inhalt vermeiden | AP1 | Zählregeln, `tests/test_dump_import.py` | erfüllt |
| R-10 | Reservierungen ohne zuordenbaren Auftrag bleiben ungeklärt, kein freier Bestand | AP1 | `reservierungen_ohne_auftrag`, Lücke L-05 | erfüllt |
| R-11 | Historische Bestandsfolgen nur bei geeigneten Aufzeichnungen; sonst Datenlücke ausweisen | AP1 | Lücke L-04 | erfüllt |

## Planungsverfahren

| Nr. | Anforderung | AP | Nachweis | Status |
|---|---|---|---|---|
| R-12 | Komponentenstückzahlen, freie Bestände, Reservierungen, Boxkapazitäten und zulässige Inhalte als Daten bereitstellen | AP1 | `config/anlage.yaml` mit Herkunft | erfüllt |
| R-13 | Zeitansätze für Kommissionierung, Transport und Montage ableiten | AP1 | Befunde B-13, B-14, `matsim.daten.zeiten` | erfüllt |
| R-14 | Vergleich: Einzelversorgung, Füllschwelle, Wartezeit oder Dringlichkeit | AP4 | V1, V2, V3 in `src/matsim/regeln/verfahren.py` | Gerüst |
| R-15 | Eigene Verbesserung innerhalb mindestens einer Bündelungsregel | AP4 | V4; Kandidaten in `planungsverfahren.md` | Entwurf, Teamentscheidung offen |
| R-16 | Restbedarf auch bei nicht erreichter Füllschwelle bearbeiten | AP4 | Restbedarfsregel, `naechste_wartefrist` | Schnittstelle, Regel offen |
| R-17 | Jeder Satz bleibt seiner Anforderung zugeordnet | AP2 | Begründung in `planungsverfahren.md`; Typen `Anforderung`, `Materialsatz` | Schnittstelle |

## Erwartete Simulation

| Nr. | Anforderung | AP | Nachweis | Status |
|---|---|---|---|---|
| R-18 | Materiallager modellieren | AP3 | `src/matsim/modell/simulation.py` | Gerüst |
| R-19 | Begrenzter Kommissionierplatz | AP3 | wie R-18; Annahme A-04 | Gerüst |
| R-20 | Endlicher Boxbestand | AP3 | wie R-18; Annahme A-03 | Gerüst |
| R-21 | Mindestens ein Transportfahrzeug | AP3 | wie R-18; Annahme A-05 | Gerüst |
| R-22 | Montagestationen des Produktionsabschnitts mit begrenzten Übergabeplätzen; mindestens zwei konkurrieren | AP3 | drei Stationen mit je zwei Plätzen in `anlage.yaml` | Schnittstelle |
| R-23 | Bedarfseingang, Satz- und Chargenbildung abbilden | AP3 | Prozesskette in `logikstruktur.md` | Gerüst |
| R-24 | Reservierung abbilden | AP3 | Typ `Reservierung` | Gerüst |
| R-25 | Kommissionierung und Hintransport abbilden | AP3 | wie R-23 | Gerüst |
| R-26 | Lieferung und Montage mit Komponentenverbrauch abbilden | AP3 | wie R-23 | Gerüst |
| R-27 | Leerboxrückführung abbilden | AP3 | wie R-23; Referenzregel offen | Gerüst |
| R-28 | Fahrzeug, Boxen und Plätze bleiben während der Nutzung gebunden | AP3 | Invariante I-4 | Gerüst |
| R-29 | Warte- und Übergaberegel bei vollem Zielpuffer | AP3 | `referenz.uebergabe_bei_vollem_zielpuffer` | Gerüst, Referenzpaket fehlt (L-01) |
| R-30 | Werkstückankünfte und Weiterfahrt bei Materialmangel nach Anlagenlogik | AP3 | `referenz.weiterfahrt_bei_materialmangel`; Annahme A-01 | Gerüst, Referenzpaket fehlt (L-01) |
| R-31 | Lieferung beeinflusst, ob und wann montiert wird | AP3 | Abnahmetest in AP3 | offen |
| R-32 | Montagepriorität, Auftragsfreigabe, Fahrzeugzuordnung, Leerboxrückführung als feste Referenzregeln | AP3 | `src/matsim/referenz/regeln.py` | Gerüst, Referenzpaket fehlt (L-01) |
| R-33 | Neuplanung nur bei Bedarfseingang, Ablauf einer Wartefrist, Freigabe relevanter Kapazität | AP3 | `Planungsanlass` | Schnittstelle |
| R-34 | Gebundene Chargen und beauftragte Transporte werden nicht umgeplant | AP3 | `Charge.gebunden_s`, Planungszustand ohne gebundene Chargen | Schnittstelle |
| R-35 | Vollständigkeit des Satzes in der zulässigen Box vor der Montage prüfen | AP3 | Aufruf von `satz_vollstaendig_in_box` in der Montage | Gerüst |

## Versuche und Auswertung

| Nr. | Anforderung | AP | Nachweis | Status |
|---|---|---|---|---|
| R-36 | Basisfall mit gleichmäßigen Bedarfen | AP5 | `config/szenarien/basis.yaml` | Schnittstelle, Werte Entwurf |
| R-37 | Bedarfsspitze mit konkurrierenden Stationen | AP5 | `bedarfsspitze.yaml` | Schnittstelle, Werte Entwurf |
| R-38 | Knappe Boxen oder Übergabeplätze | AP5 | `knappe_boxen.yaml`, `knappe_uebergabeplaetze.yaml` | Schnittstelle, Werte Entwurf |
| R-39 | Unsicheren Transport- oder Kommissionierzeitansatz variieren | AP5 | `unsicherheit.yaml` | Schnittstelle, Verteilungen offen |
| R-40 | Transportzahl, Fahrzeugbelegungszeit, Boxauslastung, Zeit bis zur Materialbereitstellung, materialbedingte Montageverzögerung, offener Restbedarf | AP5 | K1 bis K6 in `kennzahlen.md` und `kennzahlen.py` | Gerüst |
| R-41 | Bündelungswarten von Warten auf Bestand, Boxen, Kommissionierung, Transport, Stationskapazität unterscheiden | AP5 | `Warteursache`, Zuordnungsregel in `kennzahlen.md` | Schnittstelle, Berechnung Gerüst |
| R-42 | Verpasste Bearbeitungsmöglichkeiten getrennt von tatsächlichem Stationsstillstand | AP5 | K8, K9 | Gerüst |
| R-43 | Mengenbilanz bleibt erhalten; Reservierung ist kein zusätzlicher Bestand | AP5 | `pruefe_mengenbilanz`, Invariante I-1 | Gerüst (für die Snapshots bereits getestet) |

## Gemeinsame Anforderungen und Abgaben

| Nr. | Anforderung | AP | Nachweis | Status |
|---|---|---|---|---|
| R-44 | Datenqualitätsanalyse mit Befundregister, ausführbaren Prüfungen und manueller Stichprobe; Rohdaten unverändert | AP1 | `datenmodell-mes.md`, Abschnitt 4; Prüfsummen | erfüllt |
| R-45 | MES-Werte, abgeleitete Werte, Beobachtungen und Szenarioannahmen unterscheiden | AP1 | `herkunft` in `anlage.yaml` | erfüllt |
| R-46 | Entscheidungsgrößen, Ziele, Nebenbedingungen, Modellgrenzen und Entscheidungshorizont definieren | AP2 | `planungsverfahren.md`, Abschnitt 2 | Entwurf |
| R-47 | Hausarbeit mit Handlungsempfehlung und Gültigkeitsbedingungen | AP2 | `report/gliederung.md` | nur Gliederung |
| R-48 | Überarbeitungen von Datenanalyse oder Modell dokumentieren und begründen | AP2 | `annahmen-und-datenluecken.md` | Schnittstelle |
| R-49 | Vollständige Enumeration eines kleinen Falls | AP4 | `planungsverfahren.md`, Abschnitt 4 | offen |
| R-50 | Planung, Simulation und Ergebnisprüfung getrennt aufrufbar; unabhängige Prüfregeln mit Nachweis an fehlerhaften Ergebnissen | AP5 | `src/matsim/kennzahlen/pruefung.py`, `tests/test_pruefregeln.py` | teilweise |
| R-51 | Gleiche Eingangsdaten je Vergleich; vorab erzeugte Eingangs- und Dauerverläufe; feste Dauern im Hauptvergleich | AP5 | `runner.erzeuge_verlaeufe`, `versuchsplan.md` | Gerüst |
| R-52 | Sensitivitätsanalyse zu einer Datenunsicherheit oder Bereinigungsentscheidung; Parameterwahl und Abschlussprüfung auf getrennten Szenarien | AP5 | `unsicherheit.yaml`, `kalibrierung.yaml`, Feld `zweck` | Schnittstelle |
| R-53 | Ereignisprotokoll mit Zeit, Ereignis, Identität, Ressource, Zustandsänderung; Endkriterium und maximale Laufzeit; offene Arbeit berichten | AP5 | `ereignisprotokoll.py`, `laufzeit` im Szenario | Schnittstelle |

## Zusammenfassung

| Status | Anzahl |
|---|---:|
| teilweise | 12 |
| Schnittstelle (ggf. mit offenen Werten) | 14 |
| Gerüst | 19 |
| Entwurf | 4 |
| offen oder nur Gliederung | 4 |
| abgeschlossen | 0 |
