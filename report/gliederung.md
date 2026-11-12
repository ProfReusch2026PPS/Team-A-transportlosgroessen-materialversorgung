# Gliederung der Hausarbeit

Verantwortlich: AP2 (Redaktion). Stand: Gliederung, noch kein Text. Format und Werkzeug der Abgabe sind eine offene Teamentscheidung. Die Gliederung folgt den geforderten Inhalten der Hausarbeit: Datenqualitätsanalyse, Entscheidungsmodell, begründete Verfahren, Simulationsmodell, Ergebnisse und Handlungsempfehlung mit Gültigkeitsbedingungen.

| Nr. | Kapitel | Inhalt | Quelle im Repo | Federführung |
|---|---|---|---|---|
| 1 | Einleitung und Problemstellung | Zielkonflikt Transportaufwand gegen Versorgungszeit, Planungsfrage, Aufbau | `docs/projekt/aufgabenstellung.md` | AP2 |
| 2 | Methodische Einordnung | Materialbereitstellung, Losgröße, Reservierung, Zielkonflikte | `docs/projekt/planungsverfahren.md`, Abschnitt 1 | AP2 |
| 3 | System und Daten | Anlage, Materialpfad, Datenmodell, Datenqualitätsanalyse mit Befundregister, Datenlücken, Parameterherkunft | `docs/projekt/datenmodell-mes.md`, `annahmen-und-datenluecken.md` | AP1 |
| 4 | Entscheidungsmodell | Entscheidungsgrößen, Ziele, Nebenbedingungen, Modellgrenzen, Entscheidungshorizont | `docs/projekt/planungsverfahren.md`, Abschnitt 2 | AP2 |
| 5 | Planungsverfahren | V0 bis V3, eigene Verbesserung V4, Restbedarfsregel, Enumeration eines kleinen Falls | `docs/projekt/planungsverfahren.md` | AP4 |
| 6 | Simulationsmodell | Prozessgrenze, Ressourcen, Kapazitäten, Ereignisse, Zustandsübergänge, Referenzregeln, Annahmen | `docs/projekt/logikstruktur.md` | AP3 |
| 7 | Verifikation und Validierung | unabhängige Prüfregeln, Nachweis an fehlerhaften Ergebnissen, Abgleich mit dem Ablauf vom 09.11.2026 | `docs/projekt/logikstruktur.md`, Abschnitt 5 | AP5 |
| 8 | Versuche | Basisfall, Stressfälle, Sensitivitätsanalyse, Parameterwahl | `docs/projekt/versuchsplan.md` | AP5 |
| 9 | Ergebnisse | Kennzahlen, Wartezeit-Zerlegung, verpasste Bearbeitungsmöglichkeiten und Stationsstillstand, offene Arbeit | `docs/projekt/kennzahlen.md`, `results/` | AP5 |
| 10 | Diskussion und Handlungsempfehlung | Empfehlung, Gültigkeitsbedingungen, Grenzen des Modells | alle | AP2 |
| A | Anhang | Anforderungsmatrix, Annahmenkatalog, Beispielaufruf, Reproduktionsanleitung | `docs/projekt/` | AP2 |

Hinweise:

- Eine Verbesserung im Modell belegt keine Verbesserung der realen Anlage. Ergebnisse gelten für die dokumentierte Modellgrenze.
- Überarbeitungen von Datenanalyse oder Modell werden mit Begründung dokumentiert.
- Präsentation: bisher nicht gefordert; bei Bedarf hier ergänzen.
