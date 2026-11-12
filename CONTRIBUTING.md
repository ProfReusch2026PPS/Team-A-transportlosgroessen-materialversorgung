# Arbeitsweise im Team

Diese Regeln gelten für alle fünf Arbeitspakete. Die Rollen stehen in der [README](README.md), die Pakete in [docs/projekt/arbeitspakete.md](docs/projekt/arbeitspakete.md).

## Branches und Pull Requests

- Kein direkter Commit auf `main`.
- Branch-Namen: `ap<Nummer>/<kurzbeschreibung>`, zum Beispiel `ap1/zeitverteilungen`, `ap3/kommissionierplatz`, `ap4/v2-fuellschwelle`. Paketübergreifendes: `team/<kurzbeschreibung>`.
- Ein Pull Request behandelt ein Thema und bleibt klein.
- Eine zweite Person gibt jeden Pull Request frei. Wer Dateien eines fremden Pakets berührt, braucht die Freigabe der dort verantwortlichen Person.
- Vor dem Pull Request lokal ausführen:

```text
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m matsim.smoke
```

## Ordnerhoheit

| Ordner oder Datei | Paket |
|---|---|
| `src/matsim/daten/`, `data/`, `docs/projekt/datenmodell-mes.md`, `notebooks/01_*` | AP1 |
| `docs/projekt/planungsverfahren.md`, `literatur-ergaenzung.md`, `annahmen-und-datenluecken.md`, `aufgabenstellung.md`, `anforderungsmatrix.md`, `report/` | AP2 |
| `src/matsim/modell/`, `src/matsim/referenz/`, `docs/projekt/logikstruktur.md` | AP3 |
| `src/matsim/regeln/`, `notebooks/04_*` | AP4 |
| `src/matsim/kennzahlen/`, `src/matsim/experimente/`, `config/szenarien/`, `results/`, `docs/projekt/kennzahlen.md`, `versuchsplan.md`, `notebooks/05_*` | AP5 |
| `config/anlage.yaml` | AP1 und AP3 gemeinsam |
| `README.md`, `CONTRIBUTING.md`, `pyproject.toml`, `.gitignore` | Team, Änderung nur per Pull Request mit zwei Freigaben |

Tests liegen in `tests/` und gehören dem Paket, dessen Code sie prüfen.

## Schnittstellen

Die vier Schnittstellen (Anlagenbeschreibung, Planungsschnittstelle, Ereignisprotokoll, Szenario-Schema) werden nur mit Zustimmung beider beteiligten Pakete geändert. Eine Änderung erhöht die jeweilige `schema_version` oder wird im Pull Request ausdrücklich als Schnittstellenänderung benannt.

## Daten und Zugangsdaten

- Keine SQL-Dumps, keine SQLite-Dateien, keine Laborunterlagen und keine PDFs im Repo.
- Zugangsdaten stehen nur in der lokalen `.env`. Sie gehören in keine versionierte Datei, auch nicht in Doku, Notebooks oder Commit-Nachrichten.
- Der Live-Zugriff ist ausschließlich lesend. Keine schreibenden SQL-Befehle, auch nicht zum Test.
- `tblcustomer` und `tblusercontrol` werden nicht exportiert.
- Rohdaten bleiben unverändert. Bereinigungen und Ausschlüsse stehen als Code im Repo und sind reproduzierbar.
- Notebooks vor dem Commit ohne Ausgaben speichern, wenn die Ausgaben Rohdaten zeigen.
- Vor jedem Commit `git status` prüfen.

## Belege und Annahmen

- Fachaussagen brauchen einen Kurzbeleg im Format der Lehrunterlagen, zum Beispiel `[Schmidt/Nyhuis 2021, S. 141-151]`.
- Seitenangaben nur, wenn sie so in `docs/` stehen oder am Volltext geprüft wurden. Neue Quellen zuerst in `docs/projekt/literatur-ergaenzung.md` eintragen.
- Was nicht aus Dateien belegbar ist, ist eine Annahme und kommt mit Begründung in `docs/projekt/annahmen-und-datenluecken.md`, bevor es im Code oder in `config/` verwendet wird.
- Jeder Wert in `config/anlage.yaml` trägt `herkunft` und `beleg`.
- Die Lehrunterlagen in `docs/00-…` bis `docs/14-…`, `docs/literatur.md` und `docs/README.md` werden nicht verändert.

## Code

- Python ab 3.11, Formatierung und Lint mit ruff, Tests mit pytest.
- Zeiten in Sekunden. Fachbegriffe im Code auf Deutsch, wie in `docs/projekt/logikstruktur.md`.
- Nicht umgesetzte Funktionen lösen `NotImplementedError` aus. Keine Platzhalterlogik, die Ergebnisse vortäuscht.
- Die Planungsverfahren kennen keine MES-Tabellen und keinen Simulationscode. Die Prüfung kennt weder Verfahren noch Simulation.

## Sprache

Deutsch, sachlich, Umlaute ausgeschrieben. Abkürzungen bei erster Verwendung erklären.
