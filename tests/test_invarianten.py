"""Invarianten der Simulation (docs/projekt/logikstruktur.md, Abschnitt 2).

Die Tests sind bereits formuliert und schlagen erwartbar mit ``NotImplementedError`` fehl
(``xfail``), bis AP3, AP4 und AP5 die Simulation, die Verfahren und die Prüfung liefern.
Sobald ein Lauf möglich ist, werden sie ohne Änderung scharf.
"""

from __future__ import annotations

import pytest

from matsim.experimente.szenario import lade_alle
from matsim.kennzahlen import pruefung
from matsim.modell.anlage import lade_anlage
from matsim.modell.simulation import Simulation
from matsim.regeln.verfahren import VERFAHREN, erzeuge

NOCH_GERUEST = pytest.mark.xfail(raises=NotImplementedError, strict=True, reason="Gerüst")


def protokoll(verfahren: str):
    szenario = lade_alle()["basis"]
    simulation = Simulation(lade_anlage(), szenario, erzeuge(verfahren), seed=1)
    return simulation.laufe().ereignisse


ALLE_VERFAHREN = pytest.mark.parametrize("verfahren", sorted(VERFAHREN))


@NOCH_GERUEST
@ALLE_VERFAHREN
def test_mengenbilanz_bleibt_erhalten(verfahren):
    anfangsbestand = {
        pno: eintrag["wert"]
        for pno, eintrag in lade_anlage()["materiallager"]["anfangsbestand"].items()
    }
    assert pruefung.pruefe_mengenbilanz(protokoll(verfahren), anfangsbestand) == []


@NOCH_GERUEST
@ALLE_VERFAHREN
def test_keine_doppelbindung_von_fahrzeug_box_und_platz(verfahren):
    assert pruefung.pruefe_doppelbindungen(protokoll(verfahren)) == []


@NOCH_GERUEST
@ALLE_VERFAHREN
def test_kapazitaeten_werden_eingehalten(verfahren):
    assert pruefung.pruefe_kapazitaeten(protokoll(verfahren), lade_anlage()) == []


@NOCH_GERUEST
@ALLE_VERFAHREN
def test_vorgaengerfolge_je_satz(verfahren):
    assert pruefung.pruefe_vorgaenger(protokoll(verfahren)) == []


@NOCH_GERUEST
@ALLE_VERFAHREN
def test_jede_anforderung_geliefert_oder_als_restbedarf_ausgewiesen(verfahren):
    assert pruefung.pruefe_abschluss(protokoll(verfahren)) == []
