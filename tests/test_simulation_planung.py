"""S2 am Simulationskern: reale Verfahren und bewusst fehlerhafte Planerantworten (#27)."""

from unittest.mock import Mock

import pytest

from matsim.experimente.szenario import lade_alle
from matsim.kennzahlen.ereignisprotokoll import Ereignistyp as E
from matsim.kennzahlen.ereignisprotokoll import Warteursache
from matsim.modell.anlage import lade_anlage
from matsim.modell.planung import Planungsfehler
from matsim.modell.simulation import Simulation
from matsim.modell.typen import Anforderung, BoxZustand, Materialsatz
from matsim.regeln.basis import Chargenentscheidung, Planungsanlass
from matsim.regeln.verfahren import CHARGEN_IN_VERSORGUNG, erzeuge


@pytest.fixture(scope="module")
def anlage():
    return lade_anlage()


def simulation(anlage, verfahren="V1", *, boxen=7, **parameter):
    szenario = {
        **lade_alle()["basis"],
        "anlage_abweichungen": {"box.transportboxen_frei": boxen},
    }
    return Simulation(anlage, szenario, erzeuge(verfahren, **parameter), seed=1)


def melde(sim, nr, zeit=0, station="RASS1"):
    kennung = f"A{nr:03d}-{station}"
    satz = Materialsatz(kennung, station, sim.materialsatz[station])
    sim.melde_bedarf(Anforderung(kennung, station, nr, 1, zeit, zeit + 100, satz))
    return kennung


def zeilen(sim, typ):
    return [z for z in sim.protokoll.ereignisse if z.ereignis == typ]


def test_v1_bindet_konkrete_boxen_auch_bei_belegten_ausfuehrungsressourcen(anlage):
    sim = simulation(anlage)
    platz = sim.kommissionierplatz.request()
    for _ in range(2):
        sim.fahrzeuge.get()
        sim.uebergabeplaetze["RASS1"].get()
    b = melde(sim, 2)
    a = melde(sim, 1)
    melde(sim, 3, zeit=500)
    vorher = sim.planungszustand()
    sim.env.run(until=1)

    assert vorher.offene_anforderungen == () and vorher.freier_bestand[800] == 4
    with pytest.raises(TypeError):
        vorher.freier_bestand[800] = 100
    assert set(sim.anforderungen) == {a, b}
    assert [z.anforderung_id for z in zeilen(sim, E.BEDARF_EINGANG)] == [a, b]
    assert [(z.zeit_s, z.menge) for z in zeilen(sim, E.PLANUNG_AUFRUF)] == [(0, 2)]
    assert [(z.anforderung_id, z.charge_id, z.box_id) for z in zeilen(sim, E.CHARGE_GEBUNDEN)] == [
        (a, "C001", "1"),
        (b, "C002", "2"),
    ]
    lager = [z for z in zeilen(sim, E.RESERVIERT) if z.ressource == "lager"]
    assert [(z.anforderung_id, z.pno, z.menge) for z in lager] == [
        (a, 800, 1),
        (a, 814, 1),
        (b, 800, 1),
        (b, 814, 1),
    ]
    zustand = sim.planungszustand()
    assert zustand.offene_anforderungen == () and zustand.freier_bestand[800] == 2
    assert zustand.freie_boxen == 5 and zustand.zusatz == {CHARGEN_IN_VERSORGUNG: 2}
    assert zustand.freie_kommissionierplaetze == zustand.freie_fahrzeuge == 0
    assert zustand.freie_uebergabeplaetze["RASS1"] == 0
    assert sim.kommissionierplatz.users == [platz] and len(sim.kommissionierplatz.queue) == 2
    assert not zeilen(sim, E.KOMMISSIONIERUNG_BEGINN)
    sim.kommissionierplatz.release(platz)
    sim.env.run(until=2)
    assert [z.charge_id for z in zeilen(sim, E.KOMMISSIONIERUNG_BEGINN)] == ["C001"]


@pytest.mark.parametrize(
    ("boxen", "bestand", "ursache"), [(1, 4, Warteursache.BOX), (7, 1, Warteursache.BESTAND)]
)
def test_zwei_anforderungen_koennen_letzte_einheit_nicht_doppelt_binden(
    anlage, boxen, bestand, ursache
):
    sim = simulation(anlage, boxen=boxen)
    sim.freier_bestand[800] = bestand
    spaeter = melde(sim, 2)
    zuerst = melde(sim, 1)
    sim.env.run(until=470)
    assert [z.anforderung_id for z in zeilen(sim, E.CHARGE_GEBUNDEN)] == [zuerst]
    assert list(sim.offene) == [spaeter] and sim.warteursache[spaeter] == ursache
    assert sim.freier_bestand[800] == bestand - 1
    assert sim.chargen["C001"].gebunden_s == 0


@pytest.mark.parametrize(
    ("fehlerfall", "meldung"),
    [
        ("doppelt", "mehrfach"),
        ("fremd", "unbekannt"),
        ("station", "Station"),
        ("bestand", "2 benötigt, nur 1 frei"),
        ("boxen", "nur 1 freie Box"),
        ("leer", "keinen Satz"),
        ("versand", "Versandzeitpunkt"),
        ("nicht endlich", "Versandzeitpunkt"),
        ("stationsgrenze", "zu viele Sätze"),
    ],
)
def test_fehlerhafte_liste_hinterlaesst_keine_teilbindung(anlage, fehlerfall, meldung):
    sim = simulation(anlage, boxen=1 if fehlerfall == "boxen" else 7)
    a = melde(sim, 1, zeit=5)
    b = melde(sim, 2, zeit=5)
    c = melde(sim, 3, zeit=5)
    if fehlerfall == "bestand":
        sim.freier_bestand[800] = 1
    if fehlerfall == "stationsgrenze":
        sim.anlage["beladung"]["max_saetze_je_box"]["RASS1"]["wert"] = 1
    vorher = sim.freier_bestand.copy()
    regal = tuple(sim.boxen.items)
    ids = {"doppelt": (a,), "fremd": ("unbekannt",), "leer": (), "stationsgrenze": (b, c)}.get(
        fehlerfall, (b,)
    )
    zeit = {"versand": 4, "nicht endlich": float("nan")}.get(fehlerfall, 5)
    sim.verfahren = Mock(wraps=sim.verfahren)
    sim.verfahren.entscheide.return_value = [
        Chargenentscheidung("RASS1", (a,), 5),
        Chargenentscheidung("RASS2" if fehlerfall == "station" else "RASS1", ids, zeit),
    ]
    with pytest.raises(Planungsfehler, match=meldung):
        sim.env.run()
    assert sim.freier_bestand == vorher and set(sim.offene) == {a, b, c}
    assert tuple(sim.boxen.items) == regal and all(box.zustand == BoxZustand.FREI for box in regal)
    assert not sim.chargen and sim.chargen_in_versorgung == 0
    assert not zeilen(sim, E.RESERVIERT) and not zeilen(sim, E.CHARGE_GEBUNDEN)
    assert "abgelehnt" in zeilen(sim, E.PLANUNG_AUFRUF)[0].bemerkung


def test_v2_bindet_restbedarf_bei_frist_ohne_neuen_bedarf(anlage):
    sim = simulation(anlage, "V2", fuellschwelle_positionen=4, hoechstwartezeit_s=20)
    a = melde(sim, 1)
    sim.env.run(until=21)
    assert [(z.zeit_s, z.menge) for z in zeilen(sim, E.PLANUNG_AUFRUF)] == [(0, 0), (20, 1)]
    assert [(z.zeit_s, z.anforderung_id) for z in zeilen(sim, E.CHARGE_GEBUNDEN)] == [(20, a)]
    assert [(z.zeit_s, z.ursache) for z in zeilen(sim, E.WARTEN_ENDE)] == [
        (20, Warteursache.BUENDELUNG)
    ]


def test_v2_neuer_bedarf_buendelt_beide_saetze_und_streicht_alte_frist(anlage):
    sim = simulation(anlage, "V2", fuellschwelle_positionen=4, hoechstwartezeit_s=20)
    a = melde(sim, 1)
    b = melde(sim, 2, zeit=8)
    sim.env.run(until=21)
    assert [(z.zeit_s, z.menge) for z in zeilen(sim, E.PLANUNG_AUFRUF)] == [(0, 0), (8, 1)]
    assert [(z.anforderung_id, z.charge_id, z.box_id) for z in zeilen(sim, E.CHARGE_GEBUNDEN)] == [
        (a, "C001", "1"),
        (b, "C001", "1"),
    ]
    assert len(sim.boxen.items) == 6 and sim.freier_bestand[814] == 2


def test_gebundener_satz_darf_nicht_neu_vergeben_werden(anlage):
    sim = simulation(anlage)
    a = melde(sim, 1)
    b = melde(sim, 2, zeit=5)
    sim.env.run(until=1)
    gebunden = sim.chargen["C001"]
    sim.verfahren = Mock(wraps=sim.verfahren)
    sim.verfahren.entscheide.return_value = [Chargenentscheidung("RASS1", (b, a), 5)]
    with pytest.raises(Planungsfehler, match="nicht offen"):
        sim.env.run(until=6)
    assert sim.chargen == {"C001": gebunden} and sim.chargen["C001"] is gebunden
    assert set(sim.offene) == {b} and sim.freier_bestand[800] == 3


def test_ersetzte_und_gestrichene_frist_bleiben_wirkungslos(anlage):
    sim = simulation(anlage, "V2", fuellschwelle_positionen=8, hoechstwartezeit_s=100)
    planer = Mock(wraps=sim.verfahren)
    sim.verfahren = planer
    planer.naechste_wartefrist.side_effect = [20, 30, None]
    for nr, zeit in enumerate((0, 5, 25), 1):
        melde(sim, nr, zeit=zeit)
    sim.env.run()
    assert [z.zeit_s for z in zeilen(sim, E.PLANUNG_AUFRUF)] == [0, 5, 25]
    assert not sim.chargen


@pytest.mark.parametrize("frist", [0, -1, float("inf"), float("nan")])
def test_ungueltige_frist_bricht_ab_statt_zur_selben_zeit_neu_zu_planen(anlage, frist):
    sim = simulation(anlage, "V2", fuellschwelle_positionen=4, hoechstwartezeit_s=20)
    sim.verfahren = Mock(wraps=sim.verfahren)
    sim.verfahren.naechste_wartefrist.return_value = frist
    melde(sim, 1)
    with pytest.raises(Planungsfehler, match="Wartefrist"):
        sim.env.run()
    assert len(zeilen(sim, E.PLANUNG_AUFRUF)) == 1


def test_v0_sieht_lieferung_freigabe_bedarf_und_frist_in_einem_aufruf(anlage):
    sim = simulation(anlage, "V0")
    planer = Mock(wraps=sim.verfahren)
    sim.verfahren = planer
    planer.naechste_wartefrist.side_effect = lambda z: 468 if z.zeit_s < 468 else None
    a = melde(sim, 1)
    b = melde(sim, 2, station="RASS3")
    c = melde(sim, 3, zeit=468, station="RASS2")
    sim.env.run(until=469)

    aufrufe = [c.args for c in planer.entscheide.call_args_list]
    assert [z.zeit_s for z, _ in aufrufe] == [0, 372, 468]
    vorher, _ = aufrufe[1]
    assert vorher.zusatz == {CHARGEN_IN_VERSORGUNG: 1} and vorher.freie_kommissionierplaetze == 1
    assert vorher.freie_fahrzeuge == 1 and [x.id for x in vorher.offene_anforderungen] == [b]
    jetzt, anlass = aufrufe[2]
    assert anlass.art == Planungsanlass.BEDARFSEINGANG
    assert all(art.value in anlass.detail for art in Planungsanlass)
    assert jetzt.freie_fahrzeuge == 2 and jetzt.zusatz == {CHARGEN_IN_VERSORGUNG: 0}
    assert [x.id for x in jetzt.offene_anforderungen] == [b, c]
    assert [(z.zeit_s, z.anforderung_id) for z in zeilen(sim, E.CHARGE_GEBUNDEN)] == [
        (0, a),
        (468, c),
    ]
    danach = planer.naechste_wartefrist.call_args.args[0]
    assert danach.zusatz == {CHARGEN_IN_VERSORGUNG: 1} and [
        x.id for x in danach.offene_anforderungen
    ] == [b]


def test_nullzeit_lieferung_verliert_den_kapazitaetsanlass_fuer_restbedarf_nicht(anlage):
    szenario = {
        **lade_alle()["basis"],
        "anlage_abweichungen": {
            "kommissionierplatz.vorlauf_s": 0,
            "kommissionierplatz.pickzeit_je_teil_s": 0,
            "kommissionierplatz.quellboxwechsel_s": 0,
            "fahrzeuge.fahrauftrag_s": 0,
        },
    }
    sim = Simulation(anlage, szenario, erzeuge("V0"), seed=1)
    a = melde(sim, 1)
    b = melde(sim, 2, station="RASS3")
    sim.env.run()
    assert [(z.zeit_s, z.anforderung_id) for z in zeilen(sim, E.CHARGE_GEBUNDEN)] == [
        (0, a),
        (0, b),
    ]
    assert len(zeilen(sim, E.LIEFERUNG)) == 2 and not sim.offene
