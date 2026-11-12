# Notebooks

Explorative Analysen. Wiederverwendbare Logik gehört nach `src/matsim/`, nicht ins Notebook.

| Präfix | Paket | Beispiel |
|---|---|---|
| `01_` | AP1 Daten | `01_daten_zeitverteilungen.ipynb` |
| `02_` | AP2 Methodik | `02_methodik_zielkonflikte.ipynb` |
| `03_` | AP3 Simulationskern | `03_modell_handrechnung.ipynb` |
| `04_` | AP4 Planungsverfahren | `04_regeln_enumeration.ipynb` |
| `05_` | AP5 Auswertung | `05_auswertung_vergleich.ipynb` |

Jedes Paket ändert nur Notebooks mit dem eigenen Präfix. Installation: `pip install -e ".[notebooks]"`. Notebooks ohne Ausgaben speichern, wenn die Ausgaben Rohdaten zeigen.
