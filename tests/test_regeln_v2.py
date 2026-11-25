"""V2 Füllschwelle auf handgebauten Planungszuständen (AP4).

Materialsätze wie in config/anlage.yaml: RASS1 800 + 814, RASS2 811 + 813, RASS3 831.
Jede gelieferte Charge wird zusätzlich mit der unabhängigen Prüfung ``pruefe_charge`` geprüft.
"""

from __future__ import annotations

import pytest

from matsim.kennzahlen.pruefung import pruefe_charge
from matsim.modell.typen import Anforderung, Charge, Materialsatz
from matsim.regeln.basis import Anlass, Chargenentscheidung, Planungsanlass, Planungszustand
from matsim.regeln.verfahren import V2Fuellschwelle, erzeuge

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
FRIST = 600.0


def anforderung(
    id_: str, station: str, eingang_s: float, komponenten: tuple | None = None
) -> Anforderung:
    satz = Materialsatz(id_, station, komponenten or SATZ[station])
    return Anforderung(id_, station, 1, 1, eingang_s, eingang_s + 600.0, satz)


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


def v2(schwelle=8, frist: float | None = FRIST) -> V2Fuellschwelle:
    parameter = {"fuellschwelle_positionen": schwelle}
    if frist is not None:
        parameter["hoechstwartezeit_s"] = frist
    return V2Fuellschwelle(**parameter)


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


def test_unter_der_schwelle_wird_gewartet():
    z = zustand(rass1(3))  # 6 von 8 Positionen
    assert v2().entscheide(z, BEDARF) == []


def test_schwelle_erreicht_eine_volle_box_mit_sofortigem_versand():
    z = zustand(rass1(4))  # 8 von 8 Positionen
    chargen = v2().entscheide(z, BEDARF)
    assert ids(chargen) == [("R1-0", "R1-1", "R1-2", "R1-3")]
    assert chargen[0].versand_fruehestens_s == z.zeit_s
    pruefe_alle(chargen, z)


def test_ueberschuss_bleibt_offen_bis_zur_naechsten_schwelle():
    z = zustand(rass1(5))  # 10 Positionen: eine volle Box, Rest 2 wartet
    chargen = v2().entscheide(z, BEDARF)
    assert ids(chargen) == [("R1-0", "R1-1", "R1-2", "R1-3")]
    pruefe_alle(chargen, z)


def test_zwei_volle_boxen_derselben_station_in_einem_aufruf():
    z = zustand(rass1(8))
    chargen = v2().entscheide(z, BEDARF)
    assert ids(chargen) == [("R1-0", "R1-1", "R1-2", "R1-3"), ("R1-4", "R1-5", "R1-6", "R1-7")]
    pruefe_alle(chargen, z)


def test_restbedarfsregel_versendet_unvollstaendige_box_nach_hoechstwartezeit():
    offene = rass1(2, start_s=400.0)  # ältester Satz bei 400 s, fällig bei 1000 s
    assert v2().entscheide(zustand(offene, zeit_s=999.0), BEDARF) == []
    anlass = Anlass(Planungsanlass.WARTEFRIST_ABGELAUFEN, 1000.0)
    z = zustand(offene, zeit_s=1000.0)
    chargen = v2().entscheide(z, anlass)
    assert ids(chargen) == [("R1-0", "R1-1")]
    pruefe_alle(chargen, z)


def test_wartefrist_ist_der_frueheste_faelligkeitszeitpunkt():
    offene = [
        anforderung("A1", "RASS1", 700.0),
        anforderung("A2", "RASS2", 500.0),
        anforderung("A3", "RASS3", 300.0),  # bereits fällig: keine Frist mehr
    ]
    assert v2().naechste_wartefrist(zustand(offene, zeit_s=1000.0)) == 500.0 + FRIST


def test_ohne_offene_saetze_keine_wartefrist():
    assert v2().naechste_wartefrist(zustand([])) is None


def test_unzulaessiger_satz_wird_nie_gebunden_und_setzt_keine_frist():
    zu_gross = anforderung("A1", "RASS3", 100.0, ((831, 9),))
    fremdes_teil = anforderung("A2", "RASS1", 100.0, ((800, 1), (831, 1)))
    z = zustand([zu_gross, fremdes_teil], zeit_s=1000.0)
    assert v2().entscheide(z, BEDARF) == []
    assert v2().naechste_wartefrist(zustand([zu_gross, fremdes_teil], zeit_s=0.0)) is None


def test_stationen_werden_nicht_gemischt():
    offene = rass1(2) + [anforderung(f"R2-{nr}", "RASS2", 950 + nr) for nr in range(2)]
    z = zustand(offene)  # je Station 4 Positionen, gemischt wären es 8
    assert v2().entscheide(z, BEDARF) == []


def test_schwelle_je_station():
    offene = rass1(2) + [anforderung(f"R3-{nr}", "RASS3", 950 + nr) for nr in range(3)]
    z = zustand(offene)
    chargen = v2({"RASS1": 4, "RASS2": 4, "RASS3": 4}).entscheide(z, BEDARF)
    assert ids(chargen) == [("R1-0", "R1-1")]
    pruefe_alle(chargen, z)


def test_stationen_in_folge_ihres_aeltesten_satzes_bei_knappen_boxen():
    offene = rass1(4, start_s=950.0) + [
        anforderung(f"R3-{nr}", "RASS3", 900 + nr) for nr in range(8)
    ]
    z = zustand(offene, freie_boxen=1)
    chargen = v2().entscheide(z, BEDARF)
    assert [c.station for c in chargen] == ["RASS3"]
    pruefe_alle(chargen, z)


def test_ohne_freie_box_wird_gewartet():
    assert v2().entscheide(zustand(rass1(4), freie_boxen=0), BEDARF) == []


def test_fehlteilsatz_wird_uebersprungen_und_blockiert_nicht():
    bestand = {**VOLLER_BESTAND, 814: 4}  # reicht für 4 der 5 Sätze
    offene = rass1(5)
    z = zustand(offene, bestand)
    chargen = v2().entscheide(z, BEDARF)
    assert ids(chargen) == [("R1-0", "R1-1", "R1-2", "R1-3")]
    pruefe_alle(chargen, z)


def test_bestand_wird_ueber_mehrere_boxen_nicht_doppelt_vergeben():
    bestand = {**VOLLER_BESTAND, 800: 5}
    z = zustand(rass1(8), bestand)
    chargen = v2().entscheide(z, BEDARF)
    assert ids(chargen) == [("R1-0", "R1-1", "R1-2", "R1-3")]
    pruefe_alle(chargen, z)


def test_satz_der_nicht_mehr_passt_wird_uebersprungen():
    gross = anforderung("G", "RASS3", 905.0, ((831, 6),))
    offene = [anforderung("K1", "RASS3", 900.0, ((831, 3),)), gross] + [
        anforderung(f"K{nr}", "RASS3", 910.0 + nr, ((831, 1),)) for nr in range(2, 7)
    ]
    z = zustand(offene)
    chargen = v2().entscheide(z, BEDARF)
    assert ids(chargen) == [("K1", "K2", "K3", "K4", "K5", "K6")]
    pruefe_alle(chargen, z)


def test_alle_anlaesse_gleich_behandelt_und_zustand_unveraendert():
    z = zustand(rass1(4))
    vorher = dict(z.freier_bestand)
    verfahren = v2()
    ergebnisse = [ids(verfahren.entscheide(z, Anlass(art, z.zeit_s))) for art in Planungsanlass]
    assert all(ergebnis == ergebnisse[0] for ergebnis in ergebnisse)
    assert dict(z.freier_bestand) == vorher


def test_kein_restbedarf_bleibt_dauerhaft_liegen():
    """Ein Satz unter der Schwelle wird spätestens zur gemeldeten Frist gebunden."""
    offene = [anforderung("A1", "RASS3", 1000.0)]
    verfahren = v2()
    z = zustand(offene, zeit_s=1000.0)
    assert verfahren.entscheide(z, BEDARF) == []
    frist = verfahren.naechste_wartefrist(z)
    assert frist == 1000.0 + FRIST
    anlass = Anlass(Planungsanlass.WARTEFRIST_ABGELAUFEN, frist)
    assert ids(verfahren.entscheide(zustand(offene, zeit_s=frist), anlass)) == [("A1",)]


def test_parameter_fehlen_oder_sind_ungueltig():
    verfahren = erzeuge("V2")  # erzeugbar ohne Parameter (smoke), aber nicht aufrufbar
    with pytest.raises(ValueError, match="fuellschwelle_positionen|hoechstwartezeit_s"):
        verfahren.entscheide(zustand(rass1(4)), BEDARF)
    with pytest.raises(ValueError, match="hoechstwartezeit_s"):
        v2(frist=None).naechste_wartefrist(zustand(rass1(1)))
    with pytest.raises(ValueError, match="übersteigt"):
        v2(schwelle=9).entscheide(zustand(rass1(1)), BEDARF)
    with pytest.raises(ValueError, match="nennt Station"):
        v2({"RASS1": 4}).entscheide(zustand([anforderung("A", "RASS3", 900)]), BEDARF)
    for falsch in (
        {"fuellschwelle_positionen": 0},
        {"fuellschwelle_positionen": True},
        {"hoechstwartezeit_s": 0},
        {"hoechstwartezeit_s": -5},
        {"schwelle": 8},
    ):
        with pytest.raises(ValueError):
            V2Fuellschwelle(**falsch)


def test_v2_ist_ueber_kurzname_mit_parametern_erzeugbar():
    verfahren = erzeuge("V2", fuellschwelle_positionen=8, hoechstwartezeit_s=FRIST)
    assert isinstance(verfahren, V2Fuellschwelle)
    assert ids(verfahren.entscheide(zustand(rass1(4)), BEDARF)) == [
        ("R1-0", "R1-1", "R1-2", "R1-3")
    ]
