"""Versorgungskette des Simulationskerns (Bauplan, Schritte 2 bis 5).

Die Planung (Schritt 6) gibt es noch nicht. Die Tests binden Chargen deshalb von Hand, so wie es
die Planung später tut: Box aus dem Regal nehmen und reservieren, Bestand abziehen, Charge bilden.
Erwartete Zeiten mit Festwerten: Vorlauf 264 s, Pick 23 s je Teil, Quellboxwechsel 62 s.
"""

from __future__ import annotations

import pytest
import simpy

from matsim.experimente.szenario import lade_alle
from matsim.kennzahlen.ereignisprotokoll import Ereignistyp
from matsim.kennzahlen.pruefung import satz_vollstaendig_in_box
from matsim.modell.anlage import lade_anlage
from matsim.modell.simulation import (
    KOMMISSIONIERPLATZ,
    LIEFERUNG,
    Simulation,
    SimulationsFehler,
    Termin,
)
from matsim.modell.typen import Boxplatz, BoxZustand, Charge, Materialsatz
from matsim.regeln.basis import Anlass, Planungsanlass
from matsim.regeln.verfahren import erzeuge


@pytest.fixture(scope="module")
def anlage():
    return lade_anlage()


@pytest.fixture(scope="module")
def szenarien():
    return lade_alle()


@pytest.fixture
def sim(anlage, szenarien):
    return Simulation(anlage, szenarien["basis"], erzeuge("V1"), seed=1)


def binde_von_hand(sim, station, auftraege, nr=1, versand_s=0.0):
    """Bindet eine Charge wie die spätere Planung: je Auftrag ein Satz der Station."""
    saetze = tuple(
        Materialsatz(f"A{auftrag:03d}-{station}", station, sim.materialsatz[station])
        for auftrag in auftraege
    )
    box = sim.boxen.items.pop(0)
    box.zustand = BoxZustand.IN_KOMMISSIONIERUNG
    for satz in saetze:
        for pno, menge in satz.komponenten:
            sim.freier_bestand[pno] -= menge
    charge = Charge(f"C{nr:03d}", station, box.id, saetze, versand_s, gebunden_s=sim.env.now)
    sim.chargen[charge.id] = charge
    return charge, box


def zeilen(sim, ereignis, **felder):
    """Protokollzeilen eines Typs, auf Wunsch nach Feldern gefiltert."""
    return [
        zeile
        for zeile in sim.protokoll.ereignisse
        if zeile.ereignis == ereignis and all(getattr(zeile, k) == v for k, v in felder.items())
    ]


def zeitpunkte(sim, ereignis, **felder):
    return [zeile.zeit_s for zeile in zeilen(sim, ereignis, **felder)]


# --- Schritt 2: Kommissionierung -----------------------------------------------------------------


def test_rass1_satz_ist_nach_372_s_kommissioniert(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])

    sim.env.process(sim.kommissionierung(charge, box))
    sim.env.run()

    assert zeitpunkte(sim, Ereignistyp.KOMMISSIONIERUNG_BEGINN) == [0.0]
    # Vorlauf 264 s, dann je Teil 23 s, dann ein Quellboxwechsel von 62 s
    assert zeitpunkte(sim, Ereignistyp.TEIL_GEPICKT) == [287.0, 310.0]
    assert zeitpunkte(sim, Ereignistyp.KOMMISSIONIERUNG_ENDE) == [372.0]
    assert sim.kommissionierplatz.count == 0


def test_teile_liegen_ihrer_anforderung_zugeordnet_in_der_box(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])

    sim.env.process(sim.kommissionierung(charge, box))
    sim.env.run()

    assert box.plaetze == [Boxplatz(1, 800, "A001-RASS1"), Boxplatz(2, 814, "A001-RASS1")]
    assert satz_vollstaendig_in_box(charge.saetze[0], box.plaetze)
    # Die Box bleibt reserviert, bis sie abgeholt wird (Schritt 3).
    assert box.zustand == BoxZustand.IN_KOMMISSIONIERUNG


def test_rass3_einzelteil_braucht_keinen_quellboxwechsel(sim):
    charge, box = binde_von_hand(sim, "RASS3", [1])

    sim.env.process(sim.kommissionierung(charge, box))
    sim.env.run()

    assert zeitpunkte(sim, Ereignistyp.KOMMISSIONIERUNG_ENDE) == [287.0]


def test_mehrere_saetze_werden_satz_fuer_satz_gepickt(sim):
    # wie am 09.11.2026: eine RASS1-Box für drei Produkte
    charge, box = binde_von_hand(sim, "RASS1", [1, 2, 3])

    sim.env.process(sim.kommissionierung(charge, box))
    sim.env.run()

    assert [(p.pno, p.anforderung_id) for p in box.plaetze] == [
        (800, "A001-RASS1"),
        (814, "A001-RASS1"),
        (800, "A002-RASS1"),
        (814, "A002-RASS1"),
        (800, "A003-RASS1"),
        (814, "A003-RASS1"),
    ]
    assert all(satz_vollstaendig_in_box(satz, box.plaetze) for satz in charge.saetze)
    # 264 + 6 × 23 + 1 × 62
    assert zeitpunkte(sim, Ereignistyp.KOMMISSIONIERUNG_ENDE) == [464.0]


def test_zweite_charge_wartet_auf_den_kommissionierplatz(sim):
    erste, erste_box = binde_von_hand(sim, "RASS1", [1], nr=1)
    zweite, zweite_box = binde_von_hand(sim, "RASS1", [2], nr=2)

    sim.env.process(sim.kommissionierung(erste, erste_box))
    sim.env.process(sim.kommissionierung(zweite, zweite_box))
    sim.env.run()

    assert zeitpunkte(sim, Ereignistyp.KOMMISSIONIERUNG_BEGINN, charge_id="C002") == [372.0]
    assert zeitpunkte(sim, Ereignistyp.KOMMISSIONIERUNG_ENDE, charge_id="C002") == [744.0]


def test_spaeterer_versand_verschiebt_den_beginn(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1], versand_s=100.0)

    sim.env.process(sim.kommissionierung(charge, box))
    sim.env.run()

    assert zeitpunkte(sim, Ereignistyp.KOMMISSIONIERUNG_BEGINN) == [100.0]
    assert zeitpunkte(sim, Ereignistyp.KOMMISSIONIERUNG_ENDE) == [472.0]


def test_belegung_des_platzes_steht_im_protokoll(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])

    sim.env.process(sim.kommissionierung(charge, box))
    sim.env.run()

    assert [zeile.ereignis for zeile in sim.protokoll.ereignisse] == [
        Ereignistyp.RESERVIERT,
        Ereignistyp.KOMMISSIONIERUNG_BEGINN,
        Ereignistyp.TEIL_GEPICKT,
        Ereignistyp.TEIL_GEPICKT,
        Ereignistyp.KOMMISSIONIERUNG_ENDE,
        Ereignistyp.RESERVIERUNG_AUFGELOEST,
    ]
    assert all(zeile.charge_id == "C001" for zeile in sim.protokoll.ereignisse)
    assert all(zeile.box_id == str(box.id) for zeile in sim.protokoll.ereignisse)
    belegung = zeilen(sim, Ereignistyp.RESERVIERT) + zeilen(
        sim, Ereignistyp.RESERVIERUNG_AUFGELOEST
    )
    assert [(z.zeit_s, z.ressource) for z in belegung] == [
        (0.0, KOMMISSIONIERPLATZ),
        (372.0, KOMMISSIONIERPLATZ),
    ]
    assert [(z.pno, z.menge) for z in zeilen(sim, Ereignistyp.TEIL_GEPICKT)] == [(800, 1), (814, 1)]


def test_freier_platz_wird_als_anlass_gemeldet(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])

    sim.env.process(sim.kommissionierung(charge, box))
    sim.env.run()

    assert sim.anlaesse == [Anlass(Planungsanlass.KAPAZITAET_FREI, 372.0, KOMMISSIONIERPLATZ)]


def test_platz_ist_frei_bevor_eine_gleichzeitige_lieferung_kommt(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])
    gesehen = []

    def lieferung_zur_selben_zeit():
        yield Termin(sim.env, 372, LIEFERUNG)
        gesehen.append(sim.kommissionierplatz.count)

    sim.env.process(lieferung_zur_selben_zeit())
    sim.env.process(sim.kommissionierung(charge, box))
    sim.env.run()

    assert gesehen == [0]


def test_zufaellige_pickzeiten_kommen_aus_dem_eigenen_strom(anlage, szenarien):
    szenario = szenarien["unsicherheit"]
    sim = Simulation(anlage, szenario, erzeuge("V1"), seed=7)
    vergleich = Simulation(anlage, szenario, erzeuge("V1"), seed=7)
    picks = [vergleich.dauer("kommissionierplatz.pickzeit_je_teil_s") for _ in range(2)]
    charge, box = binde_von_hand(sim, "RASS1", [1])

    sim.env.process(sim.kommissionierung(charge, box))
    sim.env.run()

    assert zeitpunkte(sim, Ereignistyp.KOMMISSIONIERUNG_ENDE) == [264 + sum(picks) + 62]


def test_falsche_box_wird_gemeldet(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])
    box.plaetze.append(Boxplatz(1, 800, "A009-RASS1"))  # Box ist nicht leer

    sim.env.process(sim.kommissionierung(charge, box))
    with pytest.raises(SimulationsFehler, match="nicht die leere, reservierte Box"):
        sim.env.run()


def test_termin_und_timeout_vertragen_sich():
    # Zwischenschritte laufen mit env.timeout (Priorität 1) vor jedem eigenen Rang.
    env = simpy.Environment()
    reihenfolge = []

    def mit_termin():
        yield Termin(env, 5, LIEFERUNG)
        reihenfolge.append("Termin")

    def mit_timeout():
        yield env.timeout(5)
        reihenfolge.append("timeout")

    env.process(mit_termin())
    env.process(mit_timeout())
    env.run()

    assert reihenfolge == ["timeout", "Termin"]
