"""V3 Wartezeit oder Dringlichkeit auf handgebauten Planungszuständen (AP4).

Materialsätze wie in config/anlage.yaml: RASS1 800 + 814, RASS2 811 + 813, RASS3 831.
Jede gelieferte Charge wird zusätzlich mit der unabhängigen Prüfung ``pruefe_charge`` geprüft.
"""

from __future__ import annotations

import pytest

from matsim.kennzahlen.pruefung import pruefe_charge
from matsim.modell.typen import Anforderung, Charge, Materialsatz
from matsim.regeln.basis import Anlass, Chargenentscheidung, Planungsanlass, Planungszustand
from matsim.regeln.verfahren import V3WartezeitDringlichkeit, erzeuge

ZULAESSIG = {
    "RASS1": frozenset({800, 814}),
    "RASS2": frozenset({811, 812, 813}),
    "RASS3": frozenset({831, 832, 833, 834}),
}
SATZ = {
    "RASS1": ((800, 1), (814, 1)),
    "RASS2": ((811, 1), (813, 1)),
    "RASS3": ((831, 1),),
}
VOLLER_BESTAND = {800: 20, 814: 20, 811: 20, 812: 20, 813: 20, 831: 20}
BEDARF = Anlass(Planungsanlass.BEDARFSEINGANG, 1000.0, "A1")
FRIST = 300.0
VORLAUF = 200.0


def anforderung(
    id_: str,
    station: str,
    eingang_s: float,
    bedarf_s: float | None = None,
    komponenten: tuple | None = None,
) -> Anforderung:
    satz = Materialsatz(id_, station, komponenten or SATZ[station])
    bedarf = eingang_s + 10_000.0 if bedarf_s is None else bedarf_s
    return Anforderung(id_, station, 1, 1, eingang_s, bedarf, satz)


def zustand(
    anforderungen: list[Anforderung],
    bestand: dict[int, int] | None = None,
    freie_boxen: int = 10,
    zeit_s: float = 1000.0,
) -> Planungszustand:
    return Planungszustand(
        zeit_s=zeit_s,
        offene_anforderungen=tuple(anforderungen),
        freier_bestand=dict(VOLLER_BESTAND if bestand is None else bestand),
        freie_boxen=freie_boxen,
        freie_kommissionierplaetze=1,
        freie_fahrzeuge=1,
        freie_uebergabeplaetze={"RASS1": 2, "RASS2": 2, "RASS3": 2},
        box_positionen=8,
        zulaessige_teile=ZULAESSIG,
    )


def wartezeit() -> V3WartezeitDringlichkeit:
    return V3WartezeitDringlichkeit(max_wartezeit_s=FRIST)


def dringlichkeit() -> V3WartezeitDringlichkeit:
    return V3WartezeitDringlichkeit(vorlauf_s=VORLAUF)


def ids(chargen: list[Chargenentscheidung]) -> list[tuple[str, ...]]:
    return [charge.anforderung_ids for charge in chargen]


def pruefe_alle(chargen: list[Chargenentscheidung], z: Planungszustand) -> None:
    """Unabhängige Prüfung jeder Charge und Bestandsdeckung über alle Chargen zusammen."""
    nach_id = {a.id: a for a in z.offene_anforderungen}
    verbrauch: dict[int, int] = {}
    for nr, entscheidung in enumerate(chargen):
        saetze = tuple(nach_id[i].satz for i in entscheidung.anforderung_ids)
        charge = Charge(
            f"C{nr}", entscheidung.station, nr, saetze, entscheidung.versand_fruehestens_s
        )
        assert pruefe_charge(charge, z.box_positionen, z.zulaessige_teile) == []
        for satz in saetze:
            for pno, menge in satz.komponenten:
                verbrauch[pno] = verbrauch.get(pno, 0) + menge
    assert all(menge <= z.freier_bestand.get(pno, 0) for pno, menge in verbrauch.items())
    assert len(chargen) <= z.freie_boxen


def rass1(anzahl: int, start_s: float = 900.0) -> list[Anforderung]:
    return [anforderung(f"R1-{nr}", "RASS1", start_s + nr) for nr in range(anzahl)]


# Höchstwartezeit


def test_vor_ablauf_der_wartezeit_wird_gebuendelt():
    assert wartezeit().entscheide(zustand(rass1(2), zeit_s=1000.0), BEDARF) == []


def test_nach_ablauf_der_wartezeit_alle_offenen_saetze_der_station_in_einer_box():
    offene = rass1(3, start_s=700.0)  # ältester Satz fällig bei 1000 s
    z = zustand(offene, zeit_s=1000.0)
    chargen = wartezeit().entscheide(z, Anlass(Planungsanlass.WARTEFRIST_ABGELAUFEN, 1000.0))
    assert ids(chargen) == [("R1-0", "R1-1", "R1-2")]
    assert chargen[0].versand_fruehestens_s == z.zeit_s
    pruefe_alle(chargen, z)


def test_volle_box_wird_sofort_versendet():
    z = zustand(rass1(5))  # 10 Positionen, keiner fällig: eine volle Box, Rest wartet
    chargen = wartezeit().entscheide(z, BEDARF)
    assert ids(chargen) == [("R1-0", "R1-1", "R1-2", "R1-3")]
    pruefe_alle(chargen, z)


def test_faellige_station_bekommt_mehrere_boxen():
    offene = rass1(6, start_s=600.0)  # 12 Positionen, alle fällig
    z = zustand(offene)
    chargen = wartezeit().entscheide(z, BEDARF)
    assert ids(chargen) == [("R1-0", "R1-1", "R1-2", "R1-3"), ("R1-4", "R1-5")]
    pruefe_alle(chargen, z)


def test_wartefrist_ist_der_frueheste_kuenftige_faelligkeitszeitpunkt():
    offene = [
        anforderung("A1", "RASS1", 900.0),
        anforderung("A2", "RASS2", 800.0),
        anforderung("A3", "RASS3", 500.0),  # bereits fällig: keine Frist mehr
    ]
    assert wartezeit().naechste_wartefrist(zustand(offene)) == 800.0 + FRIST


# Dringlichkeit


def test_dringlichkeit_versendet_bei_bedarfszeitpunkt_minus_vorlauf():
    offene = [anforderung("A1", "RASS3", 900.0, bedarf_s=1200.0)]  # fällig bei 1000 s
    assert dringlichkeit().entscheide(zustand(offene, zeit_s=999.0), BEDARF) == []
    z = zustand(offene, zeit_s=1000.0)
    assert ids(dringlichkeit().entscheide(z, BEDARF)) == [("A1",)]


def test_dringender_satz_nimmt_juengere_saetze_derselben_station_mit():
    offene = [
        anforderung("A1", "RASS3", 900.0),
        anforderung("A2", "RASS3", 950.0, bedarf_s=1100.0),  # dringend
        anforderung("A3", "RASS1", 920.0),
    ]
    z = zustand(offene)
    chargen = dringlichkeit().entscheide(z, BEDARF)
    assert ids(chargen) == [("A1", "A2")]
    pruefe_alle(chargen, z)


def test_wartefrist_folgt_dem_bedarfszeitpunkt():
    offene = [anforderung("A1", "RASS1", 900.0, bedarf_s=1500.0)]
    assert dringlichkeit().naechste_wartefrist(zustand(offene)) == 1500.0 - VORLAUF


def test_beide_grenzen_die_zuerst_erreichte_gilt():
    verfahren = V3WartezeitDringlichkeit(max_wartezeit_s=FRIST, vorlauf_s=VORLAUF)
    frueh_dringend = [anforderung("A1", "RASS1", 900.0, bedarf_s=1250.0)]
    assert verfahren.naechste_wartefrist(zustand(frueh_dringend)) == 1050.0
    lange_wartend = [anforderung("A2", "RASS1", 900.0, bedarf_s=5000.0)]
    assert verfahren.naechste_wartefrist(zustand(lange_wartend)) == 900.0 + FRIST


# Gemeinsame Regeln


def test_ohne_freie_box_wird_gewartet():
    assert wartezeit().entscheide(zustand(rass1(4), freie_boxen=0), BEDARF) == []


def test_stationen_in_folge_ihres_aeltesten_satzes_bei_knappen_boxen():
    offene = rass1(4, start_s=950.0) + [
        anforderung(f"R3-{nr}", "RASS3", 900.0 + nr) for nr in range(8)
    ]
    z = zustand(offene, freie_boxen=1)
    chargen = wartezeit().entscheide(z, BEDARF)
    assert [c.station for c in chargen] == ["RASS3"]
    pruefe_alle(chargen, z)


def test_stationen_werden_nicht_gemischt():
    offene = rass1(2, start_s=600.0) + [anforderung("R3-0", "RASS3", 600.0)]
    z = zustand(offene)
    chargen = wartezeit().entscheide(z, BEDARF)
    assert ids(chargen) == [("R1-0", "R1-1"), ("R3-0",)]
    pruefe_alle(chargen, z)


def test_fehlteilsatz_wird_uebersprungen_und_blockiert_nicht():
    bestand = {**VOLLER_BESTAND, 814: 0}
    offene = rass1(1, start_s=600.0) + [anforderung("R3-0", "RASS3", 650.0)]
    z = zustand(offene, bestand)
    chargen = wartezeit().entscheide(z, BEDARF)
    assert ids(chargen) == [("R3-0",)]
    pruefe_alle(chargen, z)


def test_bestand_wird_ueber_mehrere_boxen_nicht_doppelt_vergeben():
    bestand = {**VOLLER_BESTAND, 800: 5}
    z = zustand(rass1(8, start_s=600.0), bestand)
    chargen = wartezeit().entscheide(z, BEDARF)
    assert ids(chargen) == [("R1-0", "R1-1", "R1-2", "R1-3"), ("R1-4",)]
    pruefe_alle(chargen, z)


def test_unzulaessiger_satz_wird_nie_gebunden_und_setzt_keine_frist():
    zu_gross = anforderung("A1", "RASS3", 100.0, komponenten=((831, 9),))
    fremdes_teil = anforderung("A2", "RASS1", 100.0, komponenten=((800, 1), (831, 1)))
    offene = [zu_gross, fremdes_teil]
    assert wartezeit().entscheide(zustand(offene), BEDARF) == []
    assert wartezeit().naechste_wartefrist(zustand(offene, zeit_s=0.0)) is None


def test_ohne_offene_saetze_keine_wartefrist():
    assert wartezeit().naechste_wartefrist(zustand([])) is None


def test_alle_anlaesse_gleich_behandelt_und_zustand_unveraendert():
    z = zustand(rass1(2, start_s=600.0))
    vorher = dict(z.freier_bestand)
    verfahren = wartezeit()
    ergebnisse = [ids(verfahren.entscheide(z, Anlass(art, z.zeit_s))) for art in Planungsanlass]
    assert all(ergebnis == [("R1-0", "R1-1")] for ergebnis in ergebnisse)
    assert dict(z.freier_bestand) == vorher


def test_kein_restbedarf_bleibt_dauerhaft_liegen():
    """Ein einzelner Satz wird spätestens zur gemeldeten Frist gebunden."""
    offene = [anforderung("A1", "RASS3", 1000.0)]
    verfahren = wartezeit()
    z = zustand(offene, zeit_s=1000.0)
    assert verfahren.entscheide(z, BEDARF) == []
    frist = verfahren.naechste_wartefrist(z)
    assert frist == 1000.0 + FRIST
    anlass = Anlass(Planungsanlass.WARTEFRIST_ABGELAUFEN, frist)
    assert ids(verfahren.entscheide(zustand(offene, zeit_s=frist), anlass)) == [("A1",)]


def test_parameter_fehlen_oder_sind_ungueltig():
    verfahren = erzeuge("V3")  # erzeugbar ohne Parameter (smoke), aber nicht aufrufbar
    with pytest.raises(ValueError, match="max_wartezeit_s, vorlauf_s"):
        verfahren.entscheide(zustand(rass1(1)), BEDARF)
    with pytest.raises(ValueError, match="max_wartezeit_s, vorlauf_s"):
        verfahren.naechste_wartefrist(zustand(rass1(1)))
    for falsch in (
        {"max_wartezeit_s": 0},
        {"max_wartezeit_s": -1},
        {"max_wartezeit_s": True},
        {"vorlauf_s": -1},
        {"vorlauf_s": "200"},
        {"dringlichkeit": 3},
    ):
        with pytest.raises(ValueError):
            V3WartezeitDringlichkeit(**falsch)
    assert (
        V3WartezeitDringlichkeit(vorlauf_s=0).naechste_wartefrist(
            zustand([anforderung("A1", "RASS1", 900.0, bedarf_s=1500.0)])
        )
        == 1500.0
    )


def test_v3_ist_ueber_kurzname_mit_parametern_erzeugbar():
    verfahren = erzeuge("V3", max_wartezeit_s=FRIST)
    assert isinstance(verfahren, V3WartezeitDringlichkeit)
    z = zustand(rass1(2, start_s=600.0))
    assert ids(verfahren.entscheide(z, BEDARF)) == [("R1-0", "R1-1")]
