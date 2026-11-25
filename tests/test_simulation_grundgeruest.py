"""Grundgerüst des Simulationskerns (Bauplan, Schritt 1).

Geprüft wird, was die späteren Prozesse voraussetzen: Ressourcen mit Namen, Szenario-
Abweichungen, Zeiten mit reproduzierbarem Zufall und die Reihenfolge gleichzeitiger Ereignisse.
"""

from __future__ import annotations

import pytest
import simpy

from matsim.experimente.szenario import lade_alle
from matsim.kennzahlen.ereignisprotokoll import Ereignistyp
from matsim.modell.anlage import AnlagenFehler, lade_anlage, mit_abweichungen, wert
from matsim.modell.simulation import (
    ANKUNFT,
    FREIGABE,
    LIEFERUNG,
    PLANUNG,
    Simulation,
    Termin,
)
from matsim.modell.typen import BoxZustand
from matsim.regeln.verfahren import erzeuge


@pytest.fixture(scope="module")
def anlage():
    return lade_anlage()


@pytest.fixture(scope="module")
def szenarien():
    return lade_alle()


def simulation(anlage, szenario, seed=1):
    return Simulation(anlage, szenario, erzeuge("V1"), seed=seed)


# --- Ressourcen und Zustand --------------------------------------------------------------------


def test_ressourcen_im_basisfall(anlage, szenarien):
    sim = simulation(anlage, szenarien["basis"])

    assert sim.stationen == ("RASS1", "RASS2", "RASS3")
    assert sim.kommissionierplatz.capacity == 1
    assert sim.fahrzeuge.items == ["fahrzeug_1", "fahrzeug_2"]
    assert [box.id for box in sim.boxen.items] == [1, 2, 3, 4, 5, 6, 7]
    assert all(box.positionen == 8 and box.zustand == BoxZustand.FREI for box in sim.boxen.items)
    assert sim.uebergabeplaetze["RASS1"].items == ["RASS1.platz_1", "RASS1.platz_2"]
    assert all(sim.montagestationen[s].capacity == 1 for s in sim.stationen)


def test_bestand_und_materialsaetze_aus_der_anlage(anlage, szenarien):
    sim = simulation(anlage, szenarien["basis"])

    assert sim.freier_bestand[800] == 4
    assert sim.freier_bestand[831] == 5
    assert sim.materialsatz == {
        "RASS1": ((800, 1), (814, 1)),
        "RASS2": ((813, 1), (811, 1)),
        "RASS3": ((831, 1),),
    }
    assert sim.zulaessige_teile["RASS1"] == frozenset({800, 814})
    assert sim.offene == {}
    assert sim.chargen_in_versorgung == 0


def test_szenario_abweichungen_werden_uebernommen(anlage, szenarien):
    assert len(simulation(anlage, szenarien["knappe_boxen"]).boxen.items) == 3

    sim = simulation(anlage, szenarien["knappe_uebergabeplaetze"])
    assert all(sim.uebergabeplaetze[s].items == [f"{s}.platz_1"] for s in sim.stationen)


def test_abweichungen_aendern_die_eingelesene_anlage_nicht(anlage):
    geaendert = mit_abweichungen(anlage, {"box.transportboxen_frei": 3}, "test")

    assert wert(anlage, "box.transportboxen_frei") == 7
    assert geaendert["box"]["transportboxen_frei"] == {
        "wert": 3,
        "herkunft": "annahme",
        "beleg": "Szenario test",
    }


@pytest.mark.parametrize(
    ("abweichung", "meldung"),
    [
        ({"box.positionen": 0}, "box.positionen"),
        ({"box.gibt_es_nicht": 1}, "kein Parameter"),
        ({"box": 1}, "kein Parameter"),
    ],
)
def test_unzulaessige_abweichung_wird_gemeldet(anlage, abweichung, meldung):
    with pytest.raises(AnlagenFehler, match=meldung):
        mit_abweichungen(anlage, abweichung, "test")


# --- Zeiten --------------------------------------------------------------------------------------


def test_feste_dauern_aus_der_anlage(anlage, szenarien):
    sim = simulation(anlage, szenarien["basis"])

    assert sim.dauer("kommissionierplatz.vorlauf_s") == 264
    assert sim.dauer("kommissionierplatz.pickzeit_je_teil_s") == 23
    assert sim.dauer("fahrzeuge.fahrauftrag_s") == 96


def test_offene_werte_sind_nicht_nutzbar(anlage, szenarien):
    sim = simulation(anlage, szenarien["basis"])

    with pytest.raises(AnlagenFehler, match="noch offen"):
        sim.dauer("werkstueckumlauf.wiederkehrregel")


def test_zufall_ist_reproduzierbar_und_je_zeitart_getrennt(anlage, szenarien):
    szenario = szenarien["unsicherheit"]
    pfad = "kommissionierplatz.pickzeit_je_teil_s"

    erste = simulation(anlage, szenario, seed=11)
    folge = [erste.dauer(pfad) for _ in range(20)]

    # Gleicher Seed, gleiche Folge.
    zweite = simulation(anlage, szenario, seed=11)
    assert [zweite.dauer(pfad) for _ in range(20)] == folge

    # Ziehungen einer anderen Zeitart dazwischen ändern die Folge nicht (eigener Strom).
    dritte = simulation(anlage, szenario, seed=11)
    andere = next(p for p in sorted(szenario["zeiten"]["verteilt"]) if p != pfad)
    gemischt = []
    for _ in range(20):
        dritte.dauer(andere)
        gemischt.append(dritte.dauer(pfad))
    assert gemischt == folge

    # Anderer Seed, andere Folge; nicht verteilte Zeiten bleiben fest.
    vierte = simulation(anlage, szenario, seed=12)
    assert [vierte.dauer(pfad) for _ in range(20)] != folge
    assert vierte.dauer("kommissionierplatz.vorlauf_s") == 264


# --- Gleichzeitige Ereignisse --------------------------------------------------------------------


def test_gleichzeitige_ereignisse_in_vereinbarter_reihenfolge():
    env = simpy.Environment()
    reihenfolge = []

    def melde(name, rang, nr=0):
        yield Termin(env, 10, rang, nr)
        reihenfolge.append(name)

    # absichtlich in falscher Reihenfolge angelegt
    for name, rang, nr in [
        ("Planung", PLANUNG, 0),
        ("Ankunft W002", ANKUNFT, 2),
        ("Ankunft W001", ANKUNFT, 1),
        ("Lieferung", LIEFERUNG, 0),
        ("Freigabe", FREIGABE, 0),
    ]:
        env.process(melde(name, rang, nr))
    env.run()

    assert env.now == 10
    assert reihenfolge == ["Freigabe", "Lieferung", "Ankunft W001", "Ankunft W002", "Planung"]


def test_frei_gewordene_ressource_wird_vor_der_lieferung_zugeteilt():
    env = simpy.Environment()
    platz = simpy.Resource(env, capacity=1)
    reihenfolge = []

    def belegt_bis_10():
        with platz.request() as anfrage:
            yield anfrage
            yield Termin(env, 10, FREIGABE)
        reihenfolge.append("frei")

    def wartet_auf_platz():
        yield env.timeout(5)
        with platz.request() as anfrage:
            yield anfrage
            reihenfolge.append("zugeteilt")

    def lieferung():
        yield Termin(env, 10, LIEFERUNG)
        reihenfolge.append("Lieferung")

    env.process(lieferung())
    env.process(wartet_auf_platz())
    env.process(belegt_bis_10())
    env.run()

    assert reihenfolge == ["frei", "zugeteilt", "Lieferung"]


@pytest.mark.parametrize(("verzoegerung", "nr"), [(-1, 0), (5, -1), (5, 100_000)])
def test_termin_lehnt_unsinnige_werte_ab(verzoegerung, nr):
    with pytest.raises(ValueError):
        Termin(simpy.Environment(), verzoegerung, FREIGABE, nr)


# --- Protokoll -----------------------------------------------------------------------------------


def test_protokolliere_schreibt_mit_der_simulationszeit(anlage, szenarien):
    sim = simulation(anlage, szenarien["basis"])

    def vorgang():
        yield sim.env.timeout(5)
        sim.protokolliere(
            Ereignistyp.BEDARF_EINGANG, anforderung_id="A001-RASS1", ressource="RASS1"
        )

    sim.env.process(vorgang())
    sim.env.run()

    (zeile,) = sim.protokoll.ereignisse
    assert (zeile.lfd_nr, zeile.zeit_s, zeile.ereignis) == (1, 5.0, Ereignistyp.BEDARF_EINGANG)
    assert zeile.anforderung_id == "A001-RASS1"
