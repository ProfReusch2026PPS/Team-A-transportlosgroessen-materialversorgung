"""Unabhängige Prüfregeln: absichtlich fehlerhafte Fälle müssen erkannt werden."""

from __future__ import annotations

from matsim.kennzahlen.pruefung import pruefe_charge, satz_vollstaendig_in_box
from matsim.modell.typen import Boxplatz, Charge, Materialsatz

ZULAESSIG = {
    "RASS1": frozenset({800, 814}),
    "RASS2": frozenset({811, 812, 813}),
    "RASS3": frozenset({831, 832, 833, 834}),
}


def rass1(anforderung: str) -> Materialsatz:
    return Materialsatz(anforderung, "RASS1", ((800, 1), (814, 1)))


def regeln(charge: Charge) -> set[str]:
    return {verstoss.regel for verstoss in pruefe_charge(charge, 8, ZULAESSIG)}


def test_vollstaendiger_satz_in_einer_box():
    assert satz_vollstaendig_in_box(rass1("A1"), [Boxplatz(1, 800, "A1"), Boxplatz(2, 814, "A1")])


def test_teillieferung_erfuellt_den_bedarf_nicht():
    assert not satz_vollstaendig_in_box(rass1("A1"), [Boxplatz(1, 800, "A1")])


def test_fremd_zugeordnetes_teil_zaehlt_nicht():
    plaetze = [Boxplatz(1, 800, "A1"), Boxplatz(2, 814, "A2")]
    assert not satz_vollstaendig_in_box(rass1("A1"), plaetze)


def test_reservierter_leerer_platz_ist_kein_teil():
    plaetze = [Boxplatz(1, 800, "A1"), Boxplatz(2, 0, "A1")]
    assert not satz_vollstaendig_in_box(rass1("A1"), plaetze)


def test_zulaessige_charge_mit_vier_rass1_saetzen():
    charge = Charge("C1", "RASS1", 1, tuple(rass1(f"A{i}") for i in range(4)), 0.0)
    assert charge.positionen == 8
    assert regeln(charge) == set()


def test_ueberfuellte_box_wird_erkannt():
    charge = Charge("C1", "RASS1", 1, tuple(rass1(f"A{i}") for i in range(5)), 0.0)
    assert regeln(charge) == {"boxkapazitaet"}


def test_stationsfremder_satz_wird_erkannt():
    fremd = Materialsatz("A9", "RASS3", ((831, 1),))
    charge = Charge("C1", "RASS1", 1, (rass1("A1"), fremd), 0.0)
    assert regeln(charge) == {"stationsreinheit", "zulaessiger_inhalt"}


def test_doppelte_anforderung_wird_erkannt():
    charge = Charge("C1", "RASS1", 1, (rass1("A1"), rass1("A1")), 0.0)
    assert regeln(charge) == {"zuordnung"}
