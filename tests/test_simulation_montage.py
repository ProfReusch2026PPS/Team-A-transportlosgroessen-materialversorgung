"""Werkstückumlauf (#28) mit vorgegebenen Freigaben, Zufahrten und Lieferungen."""

import pytest

from matsim.experimente.szenario import lade_alle
from matsim.kennzahlen.ereignisprotokoll import Ereignistyp as E
from matsim.modell.anlage import lade_anlage
from matsim.modell.simulation import Simulation, SimulationsFehler
from matsim.modell.typen import (
    Anforderung,
    Boxplatz,
    BoxZustand,
    Charge,
    Materialsatz,
    Produktauftrag,
)
from matsim.regeln.verfahren import erzeuge


@pytest.fixture
def sim():
    szenario = {
        **lade_alle()["basis"],
        "anlage_abweichungen": {
            "werkstueckumlauf.auslagern_s": 3,
            "werkstueckumlauf.umlaufzeit_s": 20,
            "fahrzeuge.fahrauftrag_s": 5,
        },
    }
    return Simulation(lade_anlage(), szenario, erzeuge("V1"), seed=1)


def starte(sim, nr=1, freigabe=2, planbeginn=10):
    """Der spätere Bedarfseingang legt die Anforderungen vor der Freigabe an."""
    for station in sim.stationen:
        kennung = f"A{nr:03d}-{station}"
        satz = Materialsatz(kennung, station, sim.materialsatz[station])
        sim.anforderungen[kennung] = Anforderung(kennung, station, nr, 1, 0, planbeginn, satz)
    return sim.env.process(sim.werkstueckumlauf(Produktauftrag(nr, 0, freigabe), zufahrt_s=5))


def box_mit(sim, teile):
    box = sim.boxen.items.pop(0)
    box.plaetze.extend(Boxplatz(i, pno, kennung) for i, (pno, kennung) in enumerate(teile, 1))
    return box


def bereitstellen(sim, station, teile):
    box = box_mit(sim, teile)
    box.zustand = BoxZustand.AN_STATION
    platz = sim.uebergabeplaetze[station].items.pop(0)
    sim.box_an_platz[platz] = box
    return box


def zeilen(sim, typ):
    return [z for z in sim.protokoll.ereignisse if z.ereignis == typ]


@pytest.mark.parametrize(("lieferung", "beginn"), [(9, 10), (10, 10), (11, 30)])
def test_lieferzeit_wirkt_erst_bei_ankunft(sim, lieferung, beginn):
    starte(sim)
    kennung = "A001-RASS1"
    box = box_mit(sim, [(800, kennung), (814, kennung)])
    box.zustand = BoxZustand.IN_KOMMISSIONIERUNG
    charge = Charge("C001", "RASS1", box.id, (sim.anforderungen[kennung].satz,), 0, 0)
    sim.chargen_in_versorgung = 1

    def liefere():
        # Die Ankunft ist schon eingeplant, bevor der Liefertermin entsteht.
        yield sim.env.timeout(lieferung - 5)
        yield from sim.hintransport(charge, box)

    sim.env.process(liefere())
    sim.env.run(until=12)
    if lieferung == 11:
        assert not zeilen(sim, E.MONTAGE_BEGINN)
        assert not sim.montagestationen["RASS1"].queue and not sim.montagestationen["RASS1"].users
        assert sim.werkstuecke["W001"].abgeschlossene_stationen == 0
    sim.env.run(until=31)
    assert [z.zeit_s for z in zeilen(sim, E.WERKSTUECK_ANKUNFT)] == (
        [10, 30] if lieferung == 11 else [10]
    )
    assert [z.zeit_s for z in zeilen(sim, E.WEITERFAHRT_MATERIALMANGEL)] == (
        [10] if lieferung == 11 else []
    )
    (lieferzeile,) = zeilen(sim, E.LIEFERUNG)
    (montage,) = zeilen(sim, E.MONTAGE_BEGINN)
    assert (lieferzeile.zeit_s, montage.zeit_s) == (lieferung, beginn)
    assert lieferzeile.lfd_nr < zeilen(sim, E.WERKSTUECK_ANKUNFT)[-1].lfd_nr < montage.lfd_nr
    assert (montage.werkstueck_id, montage.anforderung_id, montage.box_id, montage.ressource) == (
        "W001", kennung, str(box.id), "RASS1"
    )


@pytest.mark.parametrize("fall", ["geteilt", "fremder Satz", "falsche Station", "unzulässiges Teil"])
def test_kein_verbrauch_ohne_zulaessige_box_mit_eigenem_satz(sim, fall):
    starte(sim)
    kennung = "A001-RASS1"
    teile = [(800, kennung), (814, kennung)]
    if fall == "geteilt":
        bereitstellen(sim, "RASS1", [teile.pop()])
    elif fall == "fremder Satz":
        teile[1] = (814, "A002-RASS1")
    elif fall == "unzulässiges Teil":
        teile.append((831, "A002-RASS3"))
    bereitstellen(sim, "RASS2" if fall == "falsche Station" else "RASS1", teile)
    vorher = {p: b.plaetze.copy() for p, b in sim.box_an_platz.items()}
    sim.env.run(until=31)
    assert [z.zeit_s for z in zeilen(sim, E.WEITERFAHRT_MATERIALMANGEL)] == [10, 30]
    assert not zeilen(sim, E.KOMPONENTE_VERBRAUCHT)
    assert {p: b.plaetze for p, b in sim.box_an_platz.items()} == vorher
    assert not sim.montagestationen["RASS1"].queue and not sim.montagestationen["RASS1"].users


def test_stationsfolge_verbrauch_und_rueckgabe_beim_letzten_teil(sim):
    prozess = starte(sim)
    boxen = [
        bereitstellen(sim, station, [(p, f"A001-{station}") for p, _ in sim.materialsatz[station]])
        for station in sim.stationen
    ]
    sim.env.run(until=50)
    assert boxen[0].plaetze == []
    assert boxen[0].zustand == BoxZustand.LEER_ZURUECK and boxen[0] not in sim.boxen.items
    assert sim.montagestationen["RASS1"].count == 1
    sim.env.run(until=prozess)
    assert sim.werkstuecke["W001"].abgeschlossene_stationen == 3
    assert [(z.ressource, z.zeit_s) for z in zeilen(sim, E.MONTAGE_BEGINN)] == [
        ("RASS1", 10), ("RASS2", 174), ("RASS3", 323)
    ]
    assert [z.zeit_s for z in zeilen(sim, E.MONTAGE_ENDE)] == [146, 295, 386]
    verbrauch = zeilen(sim, E.KOMPONENTE_VERBRAUCHT)
    assert [(z.zeit_s, z.pno, z.menge, z.anforderung_id) for z in verbrauch] == [
        (10, 800, 1, "A001-RASS1"), (49, 814, 1, "A001-RASS1"),
        (174, 813, 1, "A001-RASS2"), (214, 811, 1, "A001-RASS2"), (323, 831, 1, "A001-RASS3"),
    ]
    sim.env.run()
    assert [z.zeit_s for z in zeilen(sim, E.LEERBOX_RUECK_BEGINN)] == [49, 214, 323]
    assert [z.zeit_s for z in zeilen(sim, E.LEERBOX_RUECK_ENDE)] == [145, 310, 419]
    assert all(box.zustand == BoxZustand.FREI and box in sim.boxen.items for box in boxen)


def test_belegte_station_waehlt_nur_wartende_mit_material_nach_prioritaet(sim):
    for nr, freigabe, planbeginn in [(1, 2, 10), (3, 3, 50), (4, 4, 40), (2, 5, 40)]:
        starte(sim, nr, freigabe, planbeginn)
    box = bereitstellen(sim, "RASS1", [
        (p, f"A{nr:03d}-RASS1") for nr in (1, 2, 3, 4) for p in (800, 814)
    ])
    sim.env.run(until=51)
    assert len(sim.montagestationen["RASS1"].queue) == 3
    assert box.zustand == BoxZustand.AN_STATION and len(box.plaetze) == 6
    assert not zeilen(sim, E.LEERBOX_RUECK_BEGINN)
    sim.env.run(until=500)
    assert [(z.zeit_s, z.werkstueck_id) for z in zeilen(sim, E.MONTAGE_BEGINN)] == [
        (10, "W001"), (146, "W002"), (282, "W004"), (418, "W003"),
    ]
    assert len(zeilen(sim, E.KOMPONENTE_VERBRAUCHT)) == 8
    assert [z.zeit_s for z in zeilen(sim, E.LEERBOX_RUECK_BEGINN)] == [457]


def test_umlaufzeit_null_wird_statt_endloser_wiederkehr_gemeldet(sim):
    sim.anlage["werkstueckumlauf"]["umlaufzeit_s"]["wert"] = 0
    starte(sim)
    with pytest.raises(ValueError, match="Umlaufzeit"):
        sim.env.run(until=11)


def test_widerspruechliche_montagezeit_verbraucht_keine_teile(sim):
    sim.anlage["stationen"]["RASS1"]["belegung_je_werkstueck_s"]["wert"] = 60
    starte(sim)
    box = bereitstellen(sim, "RASS1", [(800, "A001-RASS1"), (814, "A001-RASS1")])
    with pytest.raises(SimulationsFehler, match="Stationsbelegung"):
        sim.env.run(until=11)
    assert len(box.plaetze) == 2 and not zeilen(sim, E.MONTAGE_BEGINN)
