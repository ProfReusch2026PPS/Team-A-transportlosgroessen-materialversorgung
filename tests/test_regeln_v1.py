"""V1 Einzelversorgung auf handgebauten Planungszuständen (AP4).

Materialsätze wie in config/anlage.yaml: RASS1 800 + 814, RASS2 811 + 813, RASS3 831.
Jede gelieferte Charge wird zusätzlich mit der unabhängigen Prüfung ``pruefe_charge`` geprüft.
"""

from __future__ import annotations

from matsim.kennzahlen.pruefung import pruefe_charge
from matsim.modell.typen import Anforderung, Charge, Materialsatz
from matsim.regeln.basis import Anlass, Chargenentscheidung, Planungsanlass, Planungszustand
from matsim.regeln.verfahren import V1Einzelversorgung, erzeuge

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
VOLLER_BESTAND = {800: 10, 814: 10, 811: 10, 812: 10, 813: 10, 831: 10}
BEDARF = Anlass(Planungsanlass.BEDARFSEINGANG, 1000.0, "A1")


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


def test_jeder_satz_sofort_in_eigener_box_in_eingangsfolge():
    z = zustand(
        [
            anforderung("A3", "RASS3", 980),
            anforderung("A1", "RASS1", 900),
            anforderung("A2", "RASS1", 950),
        ]
    )
    chargen = V1Einzelversorgung().entscheide(z, BEDARF)
    assert ids(chargen) == [("A1",), ("A2",), ("A3",)]
    assert [c.station for c in chargen] == ["RASS1", "RASS1", "RASS3"]
    assert all(c.versand_fruehestens_s == z.zeit_s for c in chargen)
    pruefe_alle(chargen, z)


def test_gleiche_eingangszeit_kleinere_identitaet_zuerst():
    z = zustand([anforderung("A2", "RASS2", 900), anforderung("A1", "RASS1", 900)], freie_boxen=1)
    assert ids(V1Einzelversorgung().entscheide(z, BEDARF)) == [("A1",)]


def test_ohne_freie_box_wird_gewartet():
    z = zustand([anforderung("A1", "RASS1", 900)], freie_boxen=0)
    assert V1Einzelversorgung().entscheide(z, BEDARF) == []


def test_boxen_begrenzen_die_zahl_der_chargen():
    z = zustand([anforderung(f"A{i}", "RASS3", 900 + i) for i in range(5)], freie_boxen=2)
    chargen = V1Einzelversorgung().entscheide(z, BEDARF)
    assert ids(chargen) == [("A0",), ("A1",)]
    pruefe_alle(chargen, z)


def test_bestand_wird_innerhalb_eines_aufrufs_nicht_doppelt_vergeben():
    bestand = {**VOLLER_BESTAND, 800: 1}
    z = zustand([anforderung("A1", "RASS1", 900), anforderung("A2", "RASS1", 950)], bestand)
    chargen = V1Einzelversorgung().entscheide(z, BEDARF)
    assert ids(chargen) == [("A1",)]
    pruefe_alle(chargen, z)


def test_fehlteilsatz_blockiert_spaetere_saetze_nicht():
    bestand = {**VOLLER_BESTAND, 814: 0}
    z = zustand([anforderung("A1", "RASS1", 900), anforderung("A2", "RASS3", 950)], bestand)
    chargen = V1Einzelversorgung().entscheide(z, BEDARF)
    assert ids(chargen) == [("A2",)]
    pruefe_alle(chargen, z)


def test_unzulaessiger_satz_wird_nie_gebunden():
    zu_gross = anforderung("A1", "RASS3", 900, ((831, 9),))
    fremdes_teil = anforderung("A2", "RASS1", 910, ((800, 1), (831, 1)))
    gueltig = anforderung("A3", "RASS1", 920)
    z = zustand([zu_gross, fremdes_teil, gueltig], {**VOLLER_BESTAND, 831: 20})
    chargen = V1Einzelversorgung().entscheide(z, BEDARF)
    assert ids(chargen) == [("A3",)]
    pruefe_alle(chargen, z)


def test_alle_anlaesse_gleich_behandelt_und_zustand_unveraendert():
    z = zustand([anforderung("A1", "RASS1", 900)])
    vorher = dict(z.freier_bestand)
    verfahren = V1Einzelversorgung()
    ergebnisse = {
        art: ids(verfahren.entscheide(z, Anlass(art, z.zeit_s))) for art in Planungsanlass
    }
    assert all(ergebnis == [("A1",)] for ergebnis in ergebnisse.values())
    assert dict(z.freier_bestand) == vorher


def test_keine_offenen_anforderungen_keine_charge():
    assert V1Einzelversorgung().entscheide(zustand([]), BEDARF) == []


def test_v1_meldet_keine_wartefrist_und_ist_ueber_kurzname_erzeugbar():
    verfahren = erzeuge("V1")
    assert isinstance(verfahren, V1Einzelversorgung)
    assert verfahren.naechste_wartefrist(zustand([anforderung("A1", "RASS1", 900)])) is None
