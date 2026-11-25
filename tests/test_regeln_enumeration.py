"""Enumeration der Chargenbildungen für kleine Fälle (AP4, Issue #13).

Materialsätze wie in config/anlage.yaml: RASS1 800 + 814, RASS3 831.
"""

from __future__ import annotations

import pytest

from matsim.kennzahlen.pruefung import pruefe_charge
from matsim.modell.typen import Anforderung, Charge, Materialsatz
from matsim.regeln.basis import Chargenentscheidung, Planungszustand
from matsim.regeln.enumeration import (
    Bewertung,
    Zeitansaetze,
    _set_partitionen,
    alternativen,
    aufteilungen,
    bewerte,
    pareto_front,
    plan_des_verfahrens,
)
from matsim.regeln.verfahren import erzeuge

ZULAESSIG = {
    "RASS1": frozenset({800, 814}),
    "RASS2": frozenset({811, 812, 813}),
    "RASS3": frozenset({831, 832, 833, 834}),
}
SATZ = {"RASS1": ((800, 1), (814, 1)), "RASS3": ((831, 1),)}
BESTAND = {800: 10, 814: 10, 831: 10}
ZEITEN = Zeitansaetze(
    vorlauf_s=264, pickzeit_je_teil_s=23, quellboxwechsel_s=62, hintransport_s=130
)


def anforderung(id_: str, station: str, eingang_s: float, komponenten=None) -> Anforderung:
    satz = Materialsatz(id_, station, komponenten or SATZ[station])
    return Anforderung(id_, station, 1, 1, eingang_s, eingang_s + 600.0, satz)


def zustand(anforderungen, bestand=None, freie_boxen: int = 7) -> Planungszustand:
    return Planungszustand(
        zeit_s=0.0,
        offene_anforderungen=tuple(anforderungen),
        freier_bestand=dict(BESTAND if bestand is None else bestand),
        freie_boxen=freie_boxen,
        freie_kommissionierplaetze=1,
        freie_fahrzeuge=2,
        freie_uebergabeplaetze={"RASS1": 2, "RASS2": 2, "RASS3": 2},
        box_positionen=8,
        zulaessige_teile=ZULAESSIG,
    )


def fall_1() -> Planungszustand:
    """Drei Sätze für RASS1, zwei für RASS3 (wie im Notebook 04)."""
    return zustand(
        [
            anforderung("A1", "RASS1", -120),
            anforderung("A2", "RASS1", -60),
            anforderung("A3", "RASS1", 0),
            anforderung("B1", "RASS3", -90),
            anforderung("B2", "RASS3", 0),
        ]
    )


def test_set_partitionen_ergeben_die_bellzahlen():
    for n, bell in [(0, 1), (1, 1), (2, 2), (3, 5), (4, 15), (5, 52)]:
        elemente = [anforderung(f"A{i}", "RASS3", i) for i in range(n)]
        partitionen = list(_set_partitionen(elemente))
        assert len(partitionen) == bell
        assert len({tuple(sorted(tuple(a.id for a in b) for b in p)) for p in partitionen}) == bell


def test_fall_1_zahl_der_alternativen():
    z = fall_1()
    assert len(aufteilungen(z)) == 5 * 2  # Bellzahlen B(3) x B(2)
    assert len(list(alternativen(z))) == 242  # mit allen Kommissionierreihenfolgen


def test_jede_alternative_ist_zulaessig_und_bindet_jeden_satz_genau_einmal():
    z = fall_1()
    nach_id = {a.id: a for a in z.offene_anforderungen}
    for alternative in alternativen(z):
        ids = [i for charge in alternative for i in charge.anforderung_ids]
        assert sorted(ids) == sorted(nach_id)
        for nr, entscheidung in enumerate(alternative):
            saetze = tuple(nach_id[i].satz for i in entscheidung.anforderung_ids)
            charge = Charge(f"C{nr}", entscheidung.station, nr, saetze, 0.0)
            assert pruefe_charge(charge, z.box_positionen, z.zulaessige_teile) == []


def test_boxkapazitaet_schliesst_aufteilungen_aus():
    z = zustand([anforderung(f"A{i}", "RASS1", i) for i in range(5)])  # 10 Positionen
    assert len(aufteilungen(z)) == 52 - 1  # nur die Aufteilung in eine einzige Box fehlt


def test_freie_boxen_begrenzen_die_zahl_der_chargen():
    z = zustand([anforderung(f"B{i}", "RASS3", i) for i in range(3)], freie_boxen=1)
    assert aufteilungen(z) == [(("B0", "B1", "B2"),)]


def test_zu_knapper_bestand_laesst_keine_vollstaendige_bindung_zu():
    z = zustand([anforderung("A1", "RASS1", 0), anforderung("A2", "RASS1", 1)], {800: 1})
    assert aufteilungen(z) == []


def test_unzulaessiger_satz_wird_nicht_aufgeteilt():
    zu_gross = anforderung("X", "RASS3", 0, ((831, 9),))
    z = zustand([zu_gross, anforderung("B1", "RASS3", 1)], {831: 20})
    assert aufteilungen(z) == [(("B1",),)]


def test_bewertung_von_hand_nachgerechnet():
    z = fall_1()
    folge = (
        Chargenentscheidung("RASS3", ("B1",), 0.0),
        Chargenentscheidung("RASS1", ("A1", "A2"), 0.0),
    )
    bewertung = bewerte(folge, z, ZEITEN)
    # B1: 264 + 1 x 23 + 0 x 62 = 287, Lieferung 287 + 130 = 417
    # A1, A2: Start 287, Dauer 264 + 4 x 23 + 1 x 62 = 418, Ende 705, Lieferung 835
    assert bewertung.lieferung_s == {"B1": 417.0, "A1": 835.0, "A2": 835.0}
    assert bewertung.transporte == 2
    assert bewertung.mittlere_bereitstellung_s == pytest.approx((417 + 835 + 835) / 3)
    assert bewertung.max_bereitstellung_s == 835.0


def test_spaeterer_versand_verschiebt_den_beginn():
    z = fall_1()
    bewertung = bewerte((Chargenentscheidung("RASS3", ("B1",), 500.0),), z, ZEITEN)
    assert bewertung.lieferung_s == {"B1": 500.0 + 287.0 + 130.0}


def test_leere_folge_ist_ein_fehler():
    with pytest.raises(ValueError):
        bewerte((), fall_1(), ZEITEN)


def test_plan_des_verfahrens_bindet_alle_saetze():
    z = fall_1()
    for name, parameter in [
        ("V1", {}),
        ("V2", {"fuellschwelle_positionen": 8, "hoechstwartezeit_s": 600}),
        ("V3", {"max_wartezeit_s": 300}),
    ]:
        plan = plan_des_verfahrens(erzeuge(name, **parameter), z)
        ids = sorted(i for charge in plan for i in charge.anforderung_ids)
        assert ids == ["A1", "A2", "A3", "B1", "B2"], name


def test_wartende_verfahren_binden_zu_ihren_fristen():
    z = fall_1()
    plan = plan_des_verfahrens(erzeuge("V3", max_wartezeit_s=300), z)
    assert [(c.anforderung_ids, c.versand_fruehestens_s) for c in plan] == [
        (("A1", "A2", "A3"), 180.0),
        (("B1", "B2"), 210.0),
    ]


def test_fall_1_ergebnis():
    """Im Fall 1 ist je Station eine Box in beiden Zielgrößen optimal; V1 liegt am weitesten weg."""
    z = fall_1()
    alle = list(alternativen(z))
    bewertungen = [bewerte(a, z, ZEITEN) for a in alle]
    front = pareto_front(bewertungen)
    assert {bewertungen[i].transporte for i in front} == {2}
    beste = min(b.mittlere_bereitstellung_s for b in bewertungen)
    v1 = bewerte(plan_des_verfahrens(erzeuge("V1"), z), z, ZEITEN)
    assert v1.transporte == 5 and v1.mittlere_bereitstellung_s > beste


def test_pareto_front():
    def b(transporte: int, zeit: float) -> Bewertung:
        return Bewertung(transporte, zeit, zeit, {})

    bewertungen = [b(2, 900), b(3, 800), b(3, 850), b(4, 800), b(2, 900)]
    assert pareto_front(bewertungen) == [0, 1, 4]


def test_zeitansaetze_aus_anlage():
    anlage = {
        "kommissionierplatz": {
            "vorlauf_s": {"wert": 264},
            "pickzeit_je_teil_s": {"wert": 23},
            "quellboxwechsel_s": {"wert": 62},
        },
        "fahrzeuge": {"hintransport_s": {"wert": 130}},
    }
    assert Zeitansaetze.aus_anlage(anlage) == ZEITEN
