"""Smoke-Test des Gerüsts: ``python -m matsim.smoke``.

Prüft, dass die vereinbarten Schnittstellen zusammenpassen. Es wird nichts simuliert:

1. ``config/anlage.yaml`` lädt und erfüllt das Schema.
2. Alle Szenario-Dateien laden und erfüllen das Schema.
3. Alle Verfahren lassen sich über die gemeinsame Schnittstelle erzeugen.
4. SimPy ist installiert und läuft.
5. Das Ereignisprotokoll lässt sich schreiben und wieder lesen.
6. Die unabhängige Prüfung erkennt einen absichtlich fehlerhaften Fall.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import simpy

from matsim.experimente.szenario import lade_alle
from matsim.kennzahlen.ereignisprotokoll import Ereignisprotokoll, Ereignistyp, lade_csv
from matsim.kennzahlen.pruefung import pruefe_charge, satz_vollstaendig_in_box
from matsim.modell.anlage import lade_anlage, offene_parameter, wert
from matsim.modell.typen import Boxplatz, Charge, Materialsatz
from matsim.regeln.verfahren import VERFAHREN, erzeuge


def main() -> None:
    anlage = lade_anlage()
    offen = offene_parameter(anlage)
    print(f"[1] anlage.yaml geladen: {len(anlage['stationen'])} Stationen, "
          f"{len(offen)} offene Parameter")
    for pfad in offen:
        print(f"      offen: {pfad}")

    szenarien = lade_alle()
    print(f"[2] {len(szenarien)} Szenarien geladen: {', '.join(szenarien)}")

    for name in VERFAHREN:
        verfahren = erzeuge(name)
        assert verfahren.name == name
    print(f"[3] Verfahren erzeugt: {', '.join(VERFAHREN)} (Logik noch nicht implementiert)")

    env = simpy.Environment()
    env.timeout(1)
    env.run()
    print(f"[4] SimPy {simpy.__version__} läuft (Uhr bei {env.now} s)")

    protokoll = Ereignisprotokoll()
    protokoll.schreibe(0, Ereignistyp.BEDARF_EINGANG, anforderung_id="A1", ressource="RASS1")
    with tempfile.TemporaryDirectory() as ordner:
        datei = Path(ordner) / "ereignisse.csv"
        protokoll.speichere_csv(datei)
        assert lade_csv(datei) == protokoll.ereignisse
    print("[5] Ereignisprotokoll geschrieben und gelesen")

    positionen = wert(anlage, "box.positionen")
    zulaessig = {
        name: frozenset(station["zulaessige_teile"]["wert"])
        for name, station in anlage["stationen"].items()
    }
    satz_rass1 = Materialsatz("A1", "RASS1", ((800, 1), (814, 1)))
    nur_mainboard = [Boxplatz(1, 800, "A1")]
    assert not satz_vollstaendig_in_box(satz_rass1, nur_mainboard)
    gemischt = Charge("C1", "RASS1", 1, (satz_rass1, Materialsatz("A2", "RASS3", ((831, 1),))), 0.0)
    regeln = {verstoss.regel for verstoss in pruefe_charge(gemischt, positionen, zulaessig)}
    assert {"stationsreinheit", "zulaessiger_inhalt"} <= regeln
    print("[6] Prüfung erkennt Teillieferung und unzulässig gemischte Charge")
    print("Smoke-Test bestanden. Simulation, Verfahren und Kennzahlen sind noch Gerüst.")


if __name__ == "__main__":
    main()
