"""V0 Referenz auf handgebauten Planungszuständen (AP4).

Materialsätze wie in config/anlage.yaml: RASS1 800 + 814, RASS2 811 + 813, RASS3 831.
Jede gelieferte Charge wird zusätzlich mit der unabhängigen Prüfung ``pruefe_charge`` geprüft.
"""

from __future__ import annotations

import pytest

from matsim.kennzahlen.pruefung import pruefe_charge
from matsim.modell.typen import Anforderung, Charge, Materialsatz
from matsim.regeln.basis import Anlass, Chargenentscheidung, Planungsanlass, Planungszustand
from matsim.regeln.verfahren import CHARGEN_IN_VERSORGUNG, V0Referenz, erzeuge

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
VOLLER_BESTAND = {800: 10, 814: 10, 811: 10, 812: 10, 813: 10, 831: 10, 832: 10}
BEDARF = Anlass(Planungsanlass.BEDARFSEINGANG, 1000.0, "A1")
KAPAZITAET = Anlass(Planungsanlass.KAPAZITAET_FREI, 1000.0, "fahrzeug")


def anforderung(
    id_: str, station: str, eingang_s: float, komponenten: tuple | None = None
) -> Anforderung:
    satz = Materialsatz(id_, station, komponenten or SATZ[station])
    return Anforderung(id_, station, 1, 1, eingang_s, eingang_s + 600.0, satz)


def zustand(
    anforderungen: list[Anforderung],
    bestand: dict[int, int] | None = None,
    freie_boxen: int = 10,
    in_versorgung: int | None = 0,
    zeit_s: float = 1000.0,
) -> Planungszustand:
    zusatz = {} if in_versorgung is None else {CHARGEN_IN_VERSORGUNG: in_versorgung}
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
        zusatz=zusatz,
    )


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


def ablauf(
    verfahren: V0Referenz, offene: list[Anforderung], bestand: dict[int, int] | None = None
) -> list[Chargenentscheidung]:
    """Spielt Planungsaufrufe nach, bis nichts mehr gebunden wird.

    Nach jeder Charge wird zuerst ein Aufruf mit noch nicht abgelieferter Box gemacht (muss
    warten), dann gilt die Box als abgeliefert, die Sätze sind nicht mehr offen.
    """
    bestand = dict(VOLLER_BESTAND if bestand is None else bestand)
    gebunden: list[Chargenentscheidung] = []
    while True:
        z = zustand(offene, bestand)
        chargen = verfahren.entscheide(z, KAPAZITAET)
        if not chargen:
            return gebunden
        assert len(chargen) == 1
        pruefe_alle(chargen, z)
        assert verfahren.entscheide(zustand(offene, bestand, in_versorgung=1), KAPAZITAET) == []
        nach_id = {a.id: a for a in offene}
        for i in chargen[0].anforderung_ids:
            for pno, menge in nach_id[i].satz.komponenten:
                bestand[pno] -= menge
        offene = [a for a in offene if a.id not in chargen[0].anforderung_ids]
        gebunden.extend(chargen)


def test_ablauf_09_11_je_station_eine_box_nacheinander():
    """Drei Produkte: je Station drei Sätze, versorgt in der Folge RASS1, RASS2, RASS3 (B-08)."""
    offene = [
        anforderung(f"{station}-{nr}", station, 900 + nr)
        for station in ("RASS3", "RASS2", "RASS1")
        for nr in range(3)
    ]
    chargen = ablauf(V0Referenz(), offene)
    assert [c.station for c in chargen] == ["RASS1", "RASS2", "RASS3"]
    assert ids(chargen) == [
        ("RASS1-0", "RASS1-1", "RASS1-2"),
        ("RASS2-0", "RASS2-1", "RASS2-2"),
        ("RASS3-0", "RASS3-1", "RASS3-2"),
    ]
    assert all(c.versand_fruehestens_s == 1000.0 for c in chargen)


def test_solange_eine_box_nicht_abgeliefert_ist_wird_gewartet():
    z = zustand([anforderung("A1", "RASS1", 900)], in_versorgung=1)
    verfahren = V0Referenz()
    assert all(verfahren.entscheide(z, Anlass(art, z.zeit_s)) == [] for art in Planungsanlass)


def test_ohne_freie_box_wird_gewartet():
    z = zustand([anforderung("A1", "RASS1", 900)], freie_boxen=0)
    assert V0Referenz().entscheide(z, BEDARF) == []


def test_box_wird_bis_acht_positionen_gefuellt_rest_in_naechster_runde():
    rass1 = [anforderung(f"R1-{nr}", "RASS1", 900 + nr) for nr in range(5)]
    rass2 = [anforderung("R2-0", "RASS2", 950)]
    chargen = ablauf(V0Referenz(), rass1 + rass2)
    assert ids(chargen) == [("R1-0", "R1-1", "R1-2", "R1-3"), ("R2-0",), ("R1-4",)]


def test_zyklus_beginnt_nach_rass3_wieder_bei_rass1():
    verfahren = V0Referenz()
    ablauf(verfahren, [anforderung("R3-0", "RASS3", 900)])
    z = zustand([anforderung("R3-1", "RASS3", 910), anforderung("R1-0", "RASS1", 920)])
    assert ids(verfahren.entscheide(z, BEDARF)) == [("R1-0",)]


def test_station_ohne_versorgbaren_satz_wird_uebersprungen():
    bestand = {**VOLLER_BESTAND, 814: 0}
    z = zustand([anforderung("R1-0", "RASS1", 900), anforderung("R2-0", "RASS2", 950)], bestand)
    chargen = V0Referenz().entscheide(z, BEDARF)
    assert ids(chargen) == [("R2-0",)]
    pruefe_alle(chargen, z)


def test_bestand_wird_innerhalb_der_box_nicht_doppelt_vergeben():
    bestand = {**VOLLER_BESTAND, 800: 2}
    z = zustand([anforderung(f"R1-{nr}", "RASS1", 900 + nr) for nr in range(3)], bestand)
    chargen = V0Referenz().entscheide(z, BEDARF)
    assert ids(chargen) == [("R1-0", "R1-1")]
    pruefe_alle(chargen, z)


def test_fehlteilsatz_blockiert_spaetere_saetze_derselben_station_nicht():
    bestand = {**VOLLER_BESTAND, 832: 0}
    z = zustand(
        [
            anforderung("R3-0", "RASS3", 900, ((832, 1),)),
            anforderung("R3-1", "RASS3", 910),
        ],
        bestand,
    )
    chargen = V0Referenz().entscheide(z, BEDARF)
    assert ids(chargen) == [("R3-1",)]
    pruefe_alle(chargen, z)


def test_unzulaessiger_satz_wird_nie_gebunden():
    zu_gross = anforderung("A1", "RASS3", 900, ((831, 9),))
    fremdes_teil = anforderung("A2", "RASS1", 910, ((800, 1), (831, 1)))
    gueltig = anforderung("A3", "RASS1", 920)
    z = zustand([zu_gross, fremdes_teil, gueltig], {**VOLLER_BESTAND, 831: 20})
    chargen = V0Referenz().entscheide(z, BEDARF)
    assert ids(chargen) == [("A3",)]
    pruefe_alle(chargen, z)


def test_gleiche_eingangszeit_kleinere_identitaet_zuerst():
    z = zustand([anforderung(f"R3-{nr}", "RASS3", 900) for nr in (8, 1, 5)])
    assert ids(V0Referenz().entscheide(z, BEDARF)) == [("R3-1", "R3-5", "R3-8")]


def test_stationsfolge_als_parameter():
    offene = [anforderung(f"{s}-0", s, 900) for s in ("RASS1", "RASS2", "RASS3")]
    chargen = ablauf(V0Referenz(stationsfolge=["RASS3", "RASS1", "RASS2"]), offene)
    assert [c.station for c in chargen] == ["RASS3", "RASS1", "RASS2"]


@pytest.mark.parametrize("folge", [[], ["RASS1", "RASS1"]])
def test_ungueltige_stationsfolge_wird_abgelehnt(folge):
    with pytest.raises(ValueError):
        V0Referenz(stationsfolge=folge)


@pytest.mark.parametrize("wert", [None, -1, 0.5, True])
def test_fehlende_oder_ungueltige_versorgungsangabe_ist_ein_fehler(wert):
    z = zustand([anforderung("A1", "RASS1", 900)], in_versorgung=None)
    if wert is not None:
        z = Planungszustand(**{**z.__dict__, "zusatz": {CHARGEN_IN_VERSORGUNG: wert}})
    with pytest.raises(ValueError, match=CHARGEN_IN_VERSORGUNG):
        V0Referenz().entscheide(z, BEDARF)


def test_zustand_bleibt_unveraendert():
    z = zustand([anforderung("A1", "RASS1", 900), anforderung("A2", "RASS1", 910)])
    vorher = dict(z.freier_bestand)
    V0Referenz().entscheide(z, BEDARF)
    assert dict(z.freier_bestand) == vorher
    assert z.freie_boxen == 10


def test_keine_offenen_anforderungen_keine_charge():
    assert V0Referenz().entscheide(zustand([]), BEDARF) == []


def test_v0_meldet_keine_wartefrist_und_erzeuge_liefert_neue_instanz():
    erste, zweite = erzeuge("V0"), erzeuge("V0")
    assert isinstance(erste, V0Referenz) and erste is not zweite
    ablauf(erste, [anforderung("R1-0", "RASS1", 900)])
    z = zustand([anforderung("R1-1", "RASS1", 910), anforderung("R2-0", "RASS2", 920)])
    assert ids(erste.entscheide(z, BEDARF)) == [("R2-0",)]
    assert ids(zweite.entscheide(z, BEDARF)) == [("R1-1",)]
    assert erste.naechste_wartefrist(z) is None
