# Aufgabenstellung

Quelle: „Prüfungsprojekte: Operations Management in der IoT Factory“, Stand 30. Oktober 2026 (PDF des Dozenten, liegt lokal vor und wird nicht versioniert). Der Text zu Team A ist wörtlich übernommen. Die gemeinsamen Anforderungen und Abgaben gelten für alle Teams und sind hier in den für uns relevanten Punkten zusammengefasst; maßgeblich bleibt das PDF.

## Rahmen

- Für eine Planungsentscheidung der Laborfabrik ist ein Python-Verfahren zu entwickeln und mit einer selbst erstellten SimPy-Simulation zu bewerten.
- Bearbeitungszeit acht Wochen, etwa fünf Personen je Team.
- Planungsentscheidung Team A: Wie viele vollständige Materialsätze werden gemeinsam zur Montagestation geliefert und wann?
- Die Bearbeitung erfolgt offline. Reservierungen, bereits freigegebene Aufträge und begonnene Vorgänge sind bindende Modellvorgaben. Änderungen am produktiven System sind nicht Teil der Aufgabe.
- Ein Referenzpaket stellt Daten, Formate, den betrachteten Produktionsabschnitt, feste Umgebungsregeln und ein kleines SimPy-Grundgerüst bereit. Das fachliche Simulationsmodell entwickelt jedes Team selbst.

Zwischenstände:

| Zeitpunkt | Inhalt |
|---|---|
| Ende Woche 2 | erste Datenqualitätsanalyse, Modellabgrenzung, Parameterherkunft und Arbeitsplan |
| Ende Woche 4 | lauffähiger Referenzplaner mit Simulation und Ereignisprotokoll |
| Wochen 5 bis 8 | eigene Verbesserung, Vergleichsversuche, Sensitivitätsanalyse, Ergebnisprüfung und Ausarbeitung |

## Team A: Transportlosgrößen und Materialversorgung (Originaltext)

### Ziel und Datenanalyse

Bündelung spart Transportaufwand je Materialsatz, kann jedoch die Versorgung verzögern. Entscheiden Sie über Anzahl und zulässige Kombination vollständiger Materialsätze in einer Box sowie den Bereitstellungs- und Versandzeitpunkt. Wägen Sie Transportaufwand, Bündelungswarten und verzögerte Montage gegeneinander ab.

Ein Materialsatz umfasst die gemeinsam bereitzustellenden Komponenten eines Montagevorgangs. Benötigt RASS1 Mainboard und Display, müssen beide in derselben Box ankommen; getrennte Teillieferungen erfüllen diesen Bedarf nicht. Mehrere vollständige Sätze dürfen nur gemeinsam transportiert werden, soweit Boxbelegung und Anlagenregeln dies erlauben. Prüfen Sie diese Regeln anhand des bereitgestellten Materialpfads.

Untersuchen Sie Komponentenbedarfe, Box- und Pufferbelegungen sowie Reservierungen. Vermeiden Sie Doppelzählungen von Box und Inhalt. Reservierungen ohne zuordenbaren Auftrag bleiben ungeklärt und gelten nicht automatisch als freier Bestand. Historische Bestandsfolgen sind nur bei geeigneten Aufzeichnungen zu rekonstruieren; weisen Sie sonst die Datenlücke aus.

### Planungsverfahren

Vergleichen Sie:

- frühestmögliche Versorgung jeweils eines vollständigen Materialsatzes;
- Bündelung vollständiger Sätze bis zu einer festgelegten Füllschwelle;
- Bündelung mit maximaler Wartezeit oder einer aus dem Produktionsbedarf abgeleiteten Dringlichkeitsgrenze.

Entwickeln Sie innerhalb mindestens einer Bündelungsregel eine eigene Verbesserung. Beachten Sie Komponentenstückzahlen, freie Bestände, Reservierungen, Boxkapazitäten und zulässige Inhalte. Jeder Satz bleibt seiner Anforderung zugeordnet. Auch bei nicht erreichter Füllschwelle muss Restbedarf bearbeitet werden.

### Erwartete Simulation

Modellieren Sie Materiallager, einen begrenzten Kommissionierplatz, endlichen Boxbestand, mindestens ein Transportfahrzeug und die Montagestationen des vorgegebenen Produktionsabschnitts mit begrenzten Übergabeplätzen. Mindestens zwei Stationen konkurrieren um Versorgungskapazität. Dies ist eine Mindestanforderung an den Vergleich, keine Angabe zur tatsächlichen Stationszahl der Factory.

Bilden Sie Bedarfseingang, Satz- und Chargenbildung, Reservierung, Kommissionierung, Hintransport, Lieferung, Montage mit Komponentenverbrauch und Leerboxrückführung ab. Prüfen Sie die Vollständigkeit des benötigten Satzes in der zulässigen Box. Fahrzeug, Boxen und Plätze bleiben während ihrer Nutzung gebunden. Für volle Zielpuffer gilt die vorgegebene Warte- und Übergaberegel.

Werkstückankünfte und Weiterfahrt bei Materialmangel folgen der vorgegebenen Anlagenlogik. Eine Lieferung muss beeinflussen können, ob und wann eine Montage stattfindet. Montageprioritäten, Auftragsfreigabe, Fahrzeugzuordnung und Leerboxrückführung folgen festen Referenzregeln. Neu geplant wird bei Bedarfseingang, Ablauf einer Wartefrist und Freigabe relevanter Kapazität. Gebundene Chargen und beauftragte Transporte werden nicht umgeplant.

**Versuche:** gleichmäßige Bedarfe als Basisfall; Bedarfsspitze mit konkurrierenden Stationen; knappe Boxen oder Übergabeplätze als zweiter Stressfall. Variieren Sie zusätzlich einen unsicheren Transport- oder Kommissionierzeitansatz.

**Auswertung:** Transportzahl, Fahrzeugbelegungszeit, Boxauslastung, Zeit bis zur Materialbereitstellung, materialbedingte Montageverzögerung und offener Restbedarf. Unterscheiden Sie Bündelungswarten von Warten auf Bestand, Boxen, Kommissionierung, Transport oder Stationskapazität. Verpasste Bearbeitungsmöglichkeiten sind getrennt von tatsächlichem Stationsstillstand auszuweisen. Die Mengenbilanz muss erhalten bleiben; eine Reservierung ist kein zusätzlicher Bestand.

## Gemeinsame Anforderungen (Zusammenfassung)

### 1. Datenqualität vor der Planung untersuchen

- Relevante MES-Tabellen und Felder selbstständig analysieren: Bedeutung, Einheiten, Zeitbezug, fehlende Werte, doppelte Schlüssel, widersprüchliche Statusangaben, Mengen- und Zeitplausibilität, fehlende Referenzen, Mehrfachzählungen.
- Je Befund dokumentieren: Prüfregel, geprüfte Datensatzanzahl, Anzahl und Anteil auffälliger Datensätze, Beispielreferenz, Behandlung und Modellfolge (Befundregister).
- Ausführbare Prüfungen und mindestens eine manuelle Datenstichprobe. Bereinigungen und Ausschlüsse reproduzierbar; Rohdaten bleiben unverändert.
- MES-Werte, abgeleitete Werte, ergänzende Beobachtungen und Szenarioannahmen unterscheiden. Ein Exportzustand belegt keine historische Bestands- oder Bewegungsfolge; eine Zeitstempeldifferenz ist nicht automatisch reine Bearbeitungs- oder Fahrzeit.

### 2. Entscheidung modellieren und Verfahren vergleichen

- Entscheidungsgrößen, Ziele, Nebenbedingungen und Modellgrenzen definieren.
- Referenzregeln mit der eigenen Verbesserung vergleichen.
- Für einen kleinen Fall durch vollständige Enumeration zulässiger Alternativen untersuchen, wie gut das Verfahren abschneidet. Entscheidungshorizont benennen.

### 3. Ablauf simulieren und unabhängig prüfen

- Planung, Simulation und Ergebnisprüfung getrennt aufrufbar.
- Die Simulation übernimmt keine geplanten Fertigstellungen als Ergebnis. Dynamische Regeln werden zu festgelegten Ereignissen mit dem dann bekannten Zustand aufgerufen.
- Prozessgrenze, Ressourcen, Kapazitäten, Ereignisse und Zustandsübergänge dokumentieren. Sekunden und eindeutige Regeln für gleichzeitige Ereignisse. Protokolliert werden Zeit, Ereignis, Identität, Ressource und Zustandsänderung.
- Materialsatzvollständigkeit und Weiterfahrt bei Materialmangel müssen erhalten bleiben.
- Verpflichtend: unabhängige Prüfregeln (Kapazitäten, Mengen, Vorgängerbeziehungen, Doppelbindungen) mit Nachweis an absichtlich fehlerhaften Ergebnissen; ein Basisfall und zwei Stressfälle mit identischen Eingangsdaten je Vergleich; eine Sensitivitätsanalyse zu einer wesentlichen Datenunsicherheit oder Bereinigungsentscheidung.
- Der Hauptvergleich verwendet feste Dauern. Zufällige Dauern sind optional, Verteilungen müssen belegt oder als Szenarioannahme gekennzeichnet sein; dann sind mehrere Wiederholungen und Unsicherheitsangaben nötig. Regeln werden mit denselben vorab erzeugten Eingangs- und Dauerverläufen verglichen.
- Reguläres Warten, verpasste Bearbeitungsmöglichkeiten und Verletzungen fester Plantermine unterscheiden. Unzulässige Doppelbindungen nicht stillschweigend reparieren. Endkriterium und maximale Laufzeit festlegen. Offene Arbeit und Stillstände ohne Fortschritt berichten.

### Gemeinsame Abgaben

- **Hausarbeit:** Datenqualitätsanalyse, Entscheidungsmodell mit Definition aller Größen, begründete Verfahren, Simulationsmodell, Ergebnisse und Handlungsempfehlung mit Gültigkeitsbedingungen.
- **Lauffähiger Python-Code:** Planung, SimPy-Simulation und unabhängige Prüfung mit dokumentierten Ein- und Ausgaben, Abhängigkeiten und Beispielaufruf.
- **Reproduzierbare Nachweise:** Datenherkunft und Aufbereitung, Befundregister, Parameter, Ereignisprotokolle, Basis- und Stressvergleiche sowie Sensitivitätsanalyse. Parameterwahl und abschließende Prüfung erfolgen auf getrennten Szenarien.
