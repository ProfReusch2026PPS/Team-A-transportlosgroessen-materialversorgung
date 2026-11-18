# Aufbereitete Daten (versioniert)

Kleine Eingabe- und Ergebnistabellen (CSV, Parquet oder JSON), die aus den Dumps abgeleitet sind und von der Simulation oder der Hausarbeit gebraucht werden.

Regeln:

- keine personenbezogenen Daten; `tblcustomer` und `tblusercontrol` werden nie exportiert,
- keine vollständigen Tabellenkopien, nur ausgewertete oder stark verdichtete Daten,
- jede Datei wird von einem Skript oder Notebook im Repo erzeugt; Erzeuger und Snapshot stehen in der Tabelle unten.

| Datei | Erzeugt von | Quelle | Inhalt |
|---|---|---|---|
| `zeitverteilungen.json` | `python -m matsim.daten zeiten` (`matsim.daten.zeiten.leite_verteilungen_ab`) | Snapshot 2026-11-09_1557, `tblfinstep`, `tblfinstepparameter`, `tblmachinereport` | bereinigte Stichproben der Dauern je Parameter von `config/anlage.yaml`; Laden mit `matsim.daten.zeiten.verteilung(name)` |
