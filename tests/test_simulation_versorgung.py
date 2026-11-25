"""Versorgungskette des Simulationskerns (Bauplan, Schritte 2 bis 5).

Die Planung (Schritt 6) gibt es noch nicht. Die Tests binden Chargen deshalb von Hand, so wie es
die Planung später tut: Box aus dem Regal nehmen und reservieren, Bestand abziehen, Charge bilden.
Erwartete Zeiten mit Festwerten: Vorlauf 264 s, Pick 23 s je Teil, Quellboxwechsel 62 s,
Fahrauftrag 96 s, Rückfahrt der leeren Box 96 s. Die Montage (Schritt 7) ersetzt
``montage_leert_box_bei``.
"""

from __future__ import annotations

import pytest
import simpy

from matsim.experimente.szenario import lade_alle
from matsim.kennzahlen.ereignisprotokoll import Ereignistyp
from matsim.kennzahlen.pruefung import satz_vollstaendig_in_box
from matsim.modell.anlage import lade_anlage
from matsim.modell.simulation import (
    BOX,
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
    sim.chargen_in_versorgung += 1
    return charge, box


def mit_abweichungen(anlage, szenarien, **abweichungen):
    """Basisfall mit geänderten Anlagenwerten, Pfade mit __ statt Punkt."""
    pfade = {pfad.replace("__", "."): neu for pfad, neu in abweichungen.items()}
    szenario = {**szenarien["basis"], "name": "test", "anlage_abweichungen": pfade}
    return Simulation(anlage, szenario, erzeuge("V1"), seed=1)


def fahrzeug_belegt_bis(sim, ende_s, ab_s=0.0):
    """Ein fremder Auftrag hält ab ab_s das vorderste freie Fahrzeug bis ende_s fest."""

    def fremder_auftrag():
        yield sim.env.timeout(ab_s)
        fahrzeug = yield sim.fahrzeuge.get()
        yield sim.env.timeout(ende_s - sim.env.now)
        yield sim.fahrzeuge.put(fahrzeug)

    sim.env.process(fremder_auftrag())


def montage_leert_box_bei(sim, box, zeit_s):
    """Ersatz für die Montage (Schritt 7): nimmt alle Teile heraus und startet die Rückführung."""

    def montage():
        yield sim.env.timeout(zeit_s)
        platz = next(p for p, b in sim.box_an_platz.items() if b is box)
        box.plaetze.clear()
        sim.env.process(sim.leerboxrueckfuehrung(box, platz))

    sim.env.process(montage())


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


# --- Schritt 3: Hintransport und Lieferung -------------------------------------------------------


def test_rass1_satz_wird_nach_468_s_geliefert(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])

    sim.env.process(sim.versorgung(charge, box))
    sim.env.run()

    # 372 s Kommissionierung, dann sofort Platz und Fahrzeug, 96 s Fahrauftrag
    assert zeitpunkte(sim, Ereignistyp.TRANSPORT_BEGINN) == [372.0]
    assert zeitpunkte(sim, Ereignistyp.LIEFERUNG) == [468.0]
    assert box.zustand == BoxZustand.AN_STATION
    assert sim.box_an_platz == {"RASS1.platz_1": box}
    assert sim.chargen_in_versorgung == 0
    # Der Platz bleibt belegt, bis die leere Box abgeholt ist (Schritt 4).
    assert sim.uebergabeplaetze["RASS1"].items == ["RASS1.platz_2"]
    # Das Fahrzeug ist wieder frei und steht jetzt hinten im Regal.
    assert sim.fahrzeuge.items == ["fahrzeug_2", "fahrzeug_1"]


def test_rass3_satz_wird_nach_383_s_geliefert(sim):
    charge, box = binde_von_hand(sim, "RASS3", [1])

    sim.env.process(sim.versorgung(charge, box))
    sim.env.run()

    assert zeitpunkte(sim, Ereignistyp.LIEFERUNG) == [383.0]
    assert sim.box_an_platz == {"RASS3.platz_1": box}


def test_hintransport_steht_vollstaendig_im_protokoll(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])

    sim.env.process(sim.versorgung(charge, box))
    sim.env.run()

    # Die ersten sechs Zeilen gehören zur Kommissionierung (Schritt 2).
    assert [(z.zeit_s, z.ereignis, z.ressource) for z in sim.protokoll.ereignisse[6:]] == [
        (372.0, Ereignistyp.RESERVIERT, "RASS1.platz_1"),
        (372.0, Ereignistyp.RESERVIERT, "fahrzeug_1"),
        (372.0, Ereignistyp.TRANSPORT_BEGINN, "fahrzeug_1"),
        (468.0, Ereignistyp.TRANSPORT_ENDE, "fahrzeug_1"),
        (468.0, Ereignistyp.LIEFERUNG, "RASS1.platz_1"),
        (468.0, Ereignistyp.RESERVIERUNG_AUFGELOEST, "fahrzeug_1"),
    ]
    beginn = zeilen(sim, Ereignistyp.TRANSPORT_BEGINN)[0]
    assert (beginn.menge, beginn.zustand_alt, beginn.zustand_neu) == (
        2,
        "in_kommissionierung",
        "unterwegs",
    )
    lieferung = zeilen(sim, Ereignistyp.LIEFERUNG)[0]
    assert (lieferung.zustand_alt, lieferung.zustand_neu) == ("unterwegs", "an_station")
    assert all(z.charge_id == "C001" for z in sim.protokoll.ereignisse)
    assert all(z.box_id == str(box.id) for z in sim.protokoll.ereignisse)


def test_freies_fahrzeug_wird_als_anlass_gemeldet(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])

    sim.env.process(sim.versorgung(charge, box))
    sim.env.run()

    assert sim.anlaesse == [
        Anlass(Planungsanlass.KAPAZITAET_FREI, 372.0, KOMMISSIONIERPLATZ),
        Anlass(Planungsanlass.KAPAZITAET_FREI, 468.0, "fahrzeug_1"),
    ]


def test_zweite_box_kommt_auf_den_zweiten_platz(sim):
    erste, erste_box = binde_von_hand(sim, "RASS1", [1], nr=1)
    zweite, zweite_box = binde_von_hand(sim, "RASS1", [2], nr=2)

    sim.env.process(sim.versorgung(erste, erste_box))
    sim.env.process(sim.versorgung(zweite, zweite_box))
    sim.env.run()

    # Die zweite Charge ist bei 744 s fertig (Schritt 2) und fährt mit dem am längsten freien
    # Fahrzeug, also fahrzeug_2 (A-13).
    assert zeitpunkte(sim, Ereignistyp.LIEFERUNG) == [468.0, 840.0]
    assert [z.ressource for z in zeilen(sim, Ereignistyp.TRANSPORT_BEGINN)] == [
        "fahrzeug_1",
        "fahrzeug_2",
    ]
    assert sim.box_an_platz == {"RASS1.platz_1": erste_box, "RASS1.platz_2": zweite_box}
    assert sim.chargen_in_versorgung == 0


def test_box_wartet_auf_das_einzige_fahrzeug(anlage, szenarien):
    sim = mit_abweichungen(anlage, szenarien, fahrzeuge__anzahl=1)
    fahrzeug_belegt_bis(sim, 500)
    charge, box = binde_von_hand(sim, "RASS1", [1])

    sim.env.process(sim.versorgung(charge, box))
    sim.env.run()

    # Platz bei 372 s reserviert, Fahrzeug erst bei 500 s: 128 s Warten auf den Transport
    assert [(z.zeit_s, z.ressource) for z in zeilen(sim, Ereignistyp.RESERVIERT)] == [
        (0.0, KOMMISSIONIERPLATZ),
        (372.0, "RASS1.platz_1"),
        (500.0, "fahrzeug_1"),
    ]
    assert zeitpunkte(sim, Ereignistyp.LIEFERUNG) == [596.0]


def test_freies_fahrzeug_uebernimmt_den_aeltesten_auftrag(anlage, szenarien):
    sim = mit_abweichungen(anlage, szenarien, fahrzeuge__anzahl=1)
    fahrzeug_belegt_bis(sim, 1000)
    rass3, rass3_box = binde_von_hand(sim, "RASS3", [1], nr=1)
    rass1, rass1_box = binde_von_hand(sim, "RASS1", [1], nr=2)

    sim.env.process(sim.versorgung(rass3, rass3_box))
    sim.env.process(sim.versorgung(rass1, rass1_box))
    sim.env.run()

    # RASS3 ist bei 287 s fertig, RASS1 bei 659 s; das Fahrzeug ist erst bei 1000 s frei.
    # Es fährt zuerst den älteren Auftrag (A-13).
    assert [(z.zeit_s, z.charge_id) for z in zeilen(sim, Ereignistyp.LIEFERUNG)] == [
        (1096.0, "C001"),
        (1192.0, "C002"),
    ]


def test_volle_station_haelt_die_box_an_der_kommissionierung(anlage, szenarien):
    sim = mit_abweichungen(anlage, szenarien, stationen__RASS1__uebergabeplaetze=1)
    besetzt = sim.uebergabeplaetze["RASS1"].items.pop(0)  # dort steht noch eine andere Box
    charge, box = binde_von_hand(sim, "RASS1", [1])

    def platz_wird_frei():
        yield sim.env.timeout(600)
        yield sim.uebergabeplaetze["RASS1"].put(besetzt)

    sim.env.process(platz_wird_frei())
    sim.env.process(sim.versorgung(charge, box))
    sim.env.run(until=550)

    # Fertig bei 372 s, aber kein Platz frei: Die Box bleibt an der Kommissionierung, und beide
    # Fahrzeuge bleiben für andere Aufträge frei (A-12).
    assert zeitpunkte(sim, Ereignistyp.KOMMISSIONIERUNG_ENDE) == [372.0]
    assert box.zustand == BoxZustand.IN_KOMMISSIONIERUNG
    assert sim.fahrzeuge.items == ["fahrzeug_1", "fahrzeug_2"]
    assert zeilen(sim, Ereignistyp.TRANSPORT_BEGINN) == []

    sim.env.run()

    assert zeitpunkte(sim, Ereignistyp.TRANSPORT_BEGINN) == [600.0]
    assert zeitpunkte(sim, Ereignistyp.LIEFERUNG) == [696.0]


def test_zufaellige_fahrzeit_kommt_aus_dem_eigenen_strom(anlage, szenarien):
    # unsicherheit.yaml verteilt noch fahrzeuge.hintransport_s (Bauplan, Abschnitt 12, Punkt 16),
    # deshalb ein eigenes Szenario.
    zeiten = {"modus": "verteilung", "verteilt": ["fahrzeuge.fahrauftrag_s"]}
    szenario = {**szenarien["basis"], "name": "test", "zeiten": zeiten}
    sim = Simulation(anlage, szenario, erzeuge("V1"), seed=7)
    fahrt = Simulation(anlage, szenario, erzeuge("V1"), seed=7).dauer("fahrzeuge.fahrauftrag_s")
    charge, box = binde_von_hand(sim, "RASS1", [1])

    sim.env.process(sim.versorgung(charge, box))
    sim.env.run()

    assert zeitpunkte(sim, Ereignistyp.LIEFERUNG) == [372 + fahrt]


def test_unvollstaendige_box_wird_nicht_transportiert(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])
    box.plaetze.append(Boxplatz(1, 800, "A001-RASS1"))  # Teil 814 fehlt

    sim.env.process(sim.hintransport(charge, box))
    with pytest.raises(SimulationsFehler, match="nicht fertig kommissioniert"):
        sim.env.run()


# --- Schritt 4: Leerboxrückführung ---------------------------------------------------------------


def test_leere_box_ist_96_s_nach_der_abholung_wieder_frei(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])
    montage_leert_box_bei(sim, box, 600)

    sim.env.process(sim.versorgung(charge, box))
    sim.env.run()

    # Geliefert bei 468 s, geleert bei 600 s, sofort abgeholt, 96 s Rückfahrt
    assert zeitpunkte(sim, Ereignistyp.LEERBOX_RUECK_BEGINN) == [600.0]
    assert zeitpunkte(sim, Ereignistyp.LEERBOX_RUECK_ENDE) == [696.0]
    assert box.zustand == BoxZustand.FREI
    assert sim.box_an_platz == {}
    # Alles wieder frei; was zuletzt frei wurde, steht hinten im Regal.
    assert sim.uebergabeplaetze["RASS1"].items == ["RASS1.platz_2", "RASS1.platz_1"]
    assert sim.boxen.items[-1] is box
    assert len(sim.boxen.items) == 7
    assert sim.fahrzeuge.items == ["fahrzeug_1", "fahrzeug_2"]


def test_rueckfuehrung_steht_vollstaendig_im_protokoll(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])
    montage_leert_box_bei(sim, box, 600)

    sim.env.process(sim.versorgung(charge, box))
    sim.env.run()

    # fahrzeug_1 hat die Box gebracht; am längsten frei ist jetzt fahrzeug_2 (A-13).
    rueckfuehrung = [z for z in sim.protokoll.ereignisse if z.zeit_s >= 600]
    assert [(z.zeit_s, z.ereignis, z.ressource) for z in rueckfuehrung] == [
        (600.0, Ereignistyp.RESERVIERT, "fahrzeug_2"),
        (600.0, Ereignistyp.LEERBOX_RUECK_BEGINN, "fahrzeug_2"),
        (600.0, Ereignistyp.RESERVIERUNG_AUFGELOEST, "RASS1.platz_1"),
        (696.0, Ereignistyp.LEERBOX_RUECK_ENDE, "fahrzeug_2"),
        (696.0, Ereignistyp.RESERVIERUNG_AUFGELOEST, BOX),
        (696.0, Ereignistyp.RESERVIERUNG_AUFGELOEST, "fahrzeug_2"),
    ]
    assert all(z.box_id == str(box.id) for z in rueckfuehrung)
    beginn = zeilen(sim, Ereignistyp.LEERBOX_RUECK_BEGINN)[0]
    ende = zeilen(sim, Ereignistyp.LEERBOX_RUECK_ENDE)[0]
    assert (beginn.zustand_alt, beginn.zustand_neu) == ("an_station", "leer_zurueck")
    assert (ende.zustand_alt, ende.zustand_neu) == ("leer_zurueck", "frei")


def test_platz_box_und_fahrzeug_werden_als_anlass_gemeldet(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])
    montage_leert_box_bei(sim, box, 600)

    sim.env.process(sim.versorgung(charge, box))
    sim.env.run()

    assert [a for a in sim.anlaesse if a.zeit_s >= 600] == [
        Anlass(Planungsanlass.KAPAZITAET_FREI, 600.0, "RASS1.platz_1"),
        Anlass(Planungsanlass.KAPAZITAET_FREI, 696.0, BOX),
        Anlass(Planungsanlass.KAPAZITAET_FREI, 696.0, "fahrzeug_2"),
    ]


def test_leere_box_bleibt_auf_dem_platz_bis_ein_fahrzeug_kommt(anlage, szenarien):
    sim = mit_abweichungen(anlage, szenarien, fahrzeuge__anzahl=1)
    fahrzeug_belegt_bis(sim, 800, ab_s=500)  # nach der Lieferung bei 468 s
    charge, box = binde_von_hand(sim, "RASS1", [1])
    montage_leert_box_bei(sim, box, 600)

    sim.env.process(sim.versorgung(charge, box))
    sim.env.run()

    # Geleert bei 600 s, das einzige Fahrzeug ist aber erst bei 800 s frei. Bis dahin bleibt
    # der Übergabeplatz belegt.
    assert zeitpunkte(sim, Ereignistyp.LEERBOX_RUECK_BEGINN) == [800.0]
    assert zeitpunkte(sim, Ereignistyp.RESERVIERUNG_AUFGELOEST, ressource="RASS1.platz_1") == [
        800.0
    ]
    assert zeitpunkte(sim, Ereignistyp.LEERBOX_RUECK_ENDE) == [896.0]


def test_frei_gewordener_platz_geht_an_die_wartende_box(anlage, szenarien):
    sim = mit_abweichungen(anlage, szenarien, stationen__RASS1__uebergabeplaetze=1)
    erste, erste_box = binde_von_hand(sim, "RASS1", [1], nr=1)
    zweite, zweite_box = binde_von_hand(sim, "RASS1", [2], nr=2)
    montage_leert_box_bei(sim, erste_box, 900)

    sim.env.process(sim.versorgung(erste, erste_box))
    sim.env.process(sim.versorgung(zweite, zweite_box))
    sim.env.run()

    # Die zweite Box ist bei 744 s fertig und wartet auf den einzigen Platz. Bei 900 s holt
    # fahrzeug_2 die leere Box ab, im selben Moment bekommt die zweite den Platz und fährt
    # mit fahrzeug_1. Kein Verklemmen (A-12).
    assert [(z.zeit_s, z.charge_id) for z in zeilen(sim, Ereignistyp.LIEFERUNG)] == [
        (468.0, "C001"),
        (996.0, "C002"),
    ]
    assert zeitpunkte(sim, Ereignistyp.LEERBOX_RUECK_ENDE) == [996.0]
    assert sim.box_an_platz == {"RASS1.platz_1": zweite_box}


def test_volle_box_wird_nicht_zurueckgefuehrt(sim):
    charge, box = binde_von_hand(sim, "RASS1", [1])

    def rueckfuehrung_ohne_montage():
        yield sim.env.timeout(600)
        yield from sim.leerboxrueckfuehrung(box, "RASS1.platz_1")

    sim.env.process(sim.versorgung(charge, box))
    sim.env.process(rueckfuehrung_ohne_montage())
    with pytest.raises(SimulationsFehler, match="nicht leer"):
        sim.env.run()
