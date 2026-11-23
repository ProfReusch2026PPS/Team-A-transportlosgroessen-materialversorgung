"""Startbestand, Snapshot-Abgleich und Bedarfsdeckung (Issues #2 und #25)."""

from __future__ import annotations

import json

import pytest

from matsim.daten import bedarfsdeckung, bestand, materialpfad
from matsim.modell.anlage import lade_anlage, wert
from matsim.modell.typen import Anforderung, Materialsatz

REIHENFOLGE = ["1516", "1522", "1525", "1536", "1541", "1557"]


@pytest.mark.dumps
@pytest.mark.parametrize("a, b", list(zip(REIHENFOLGE[:-1], REIHENFOLGE[1:], strict=True)))
def test_jede_inhaltsaenderung_ist_durch_die_historie_erklaert(snapshots, a, b):
    assert materialpfad.abgleich(snapshots[a], snapshots[b], snapshots["1557"]) == []


@pytest.mark.dumps
def test_doppelt_verortete_box_ueber_juengsten_zeitstempel_aufgeloest(snapshots):
    assert bestand.boxstandort_aufgeloest(snapshots["1557"])[11] == (17, 1, 14)
    assert bestand.boxstandort_aufgeloest(snapshots["1516"])[11] == (25, 1, 1)


@pytest.mark.dumps
def test_startbestand_15_57(snapshots):
    start = bestand.startbestand(snapshots["1557"])
    assert start.teile_reserviert == {}
    assert start.teile_ohne_ort == {800: 5, 814: 9, 832: 1}
    assert start.boxen_stammdaten == 40
    assert len(start.boxen_verortet) == 21
    assert start.leere_boxen == [2, 4, 11, 15, 18, 34, 39]
    assert start.leere_boxen_ausserhalb == [38]
    # Box und Inhalt nicht doppelt: jede Box genau einmal, Teile nur aus tblboxpos.
    assert len(start.boxen_verortet) + len(start.boxen_ohne_ort) == start.boxen_stammdaten


@pytest.mark.dumps
def test_reservierung_ist_kein_zusaetzlicher_bestand(snapshots):
    """Über alle Snapshots ist frei + reserviert + ohne Ort = physischer Bestand laut tblboxpos."""
    for verbindung in snapshots.values():
        start = bestand.startbestand(verbindung)
        physisch = {pno: e.physisch for pno, e in bestand.teilebestand(verbindung).items()}
        summe: dict[int, int] = {}
        for teil in (start.teile_frei, start.teile_reserviert, start.teile_ohne_ort):
            for pno, n in teil.items():
                summe[pno] = summe.get(pno, 0) + n
        # Box 38 am Handarbeitsplatz ist leer, deshalb geht die Summe exakt auf.
        assert summe == physisch


@pytest.mark.dumps
def test_anlage_yaml_entspricht_dem_startbestand(snapshots):
    anlage = lade_anlage()
    start = bestand.startbestand(snapshots["1557"])
    for pno, n in start.teile_frei.items():
        assert wert(anlage, f"materiallager.anfangsbestand.{pno}") == n
    assert wert(anlage, "box.transportboxen_frei") == len(start.leere_boxen)
    assert wert(anlage, "box.anzahl_verortet") == len(start.boxen_verortet)


def _anforderung(
    position: int, station: str, komponenten: tuple[tuple[int, int], ...]
) -> Anforderung:
    anforderung_id = f"{position}-{station}"
    satz = Materialsatz(anforderung_id, station, komponenten)
    return Anforderung(anforderung_id, station, 1, position, 0, 0, satz)


@pytest.mark.parametrize(
    ("produkte", "fehlmengen"),
    [(4, {}), (12, {800: 8, 811: 7, 813: 7, 814: 8, 831: 7})],
)
def test_bedarfsdeckung_mit_standardprodukten(produkte, fehlmengen):
    """Vier sind gedeckt, zwölf nicht; die Eingaben stammen aus der Anlagenkonfiguration."""
    anlage = lade_anlage()
    freier_bestand = {
        pno: wert(anlage, f"materiallager.anfangsbestand.{pno}")
        for pno in anlage["materiallager"]["anfangsbestand"]
    }
    anforderungen = (
        _anforderung(
            position,
            station,
            tuple(
                (pno, wert(anlage, f"stationen.{station}.materialsatz.{pno}"))
                for pno in anlage["stationen"][station]["materialsatz"]
            ),
        )
        for position in range(1, produkte + 1)
        for station in anlage["stationen"]
    )

    bericht = bedarfsdeckung.pruefe_bedarfsdeckung(
        anforderungen, freier_bestand, datenstand="Snapshot 2026-11-09 15:57"
    )

    assert bericht.gedeckt == (not fehlmengen)
    assert {teil.pno: teil.bedarf for teil in bericht.teile} == dict.fromkeys(
        (800, 811, 813, 814, 831), produkte
    )
    assert {teil.pno: teil.fehlmenge for teil in bericht.teile if teil.fehlmenge} == fehlmengen


def test_bedarfsdeckung_zaehlt_nur_bereinigten_freien_bestand():
    """Reservierte und nicht verortete Teile zählen nicht; freie Teile bleiben ungekürzt."""
    start = bestand.Startbestand(
        teile_frei={800: 2},
        teile_reserviert={800: 3},
        teile_ohne_ort={800: 4, 831: 7},
        boxen_stammdaten=0,
        boxen_verortet=[],
        boxen_ohne_ort=[],
        leere_boxen=[],
        leere_boxen_ausserhalb=[],
    )
    a = _anforderung(1, "RASS1", ((800, 1),))
    b = _anforderung(2, "RASS1", ((800, 2),))
    c = _anforderung(2, "RASS3", ((831, 1),))

    bericht = bedarfsdeckung.pruefe_bedarfsdeckung(
        (a, b, c), start.teile_frei, datenstand="Handfall"
    )

    assert bericht.teile == (
        bedarfsdeckung.Teiledeckung(
            800, 3, 2, 1, (
                bedarfsdeckung.Bedarfsbeitrag(a.id, "RASS1", 1),
                bedarfsdeckung.Bedarfsbeitrag(b.id, "RASS1", 2),
            )
        ),
        bedarfsdeckung.Teiledeckung(
            831, 1, 0, 1, (bedarfsdeckung.Bedarfsbeitrag(c.id, "RASS3", 1),)
        ),
    )


def test_bedarfsdeckung_beruecksichtigt_szenariobestand_und_exportiert_annahme():
    """Die Szenariomenge ersetzt den Basiswert, der im JSON nachvollziehbar bleibt."""
    freier_bestand = {800: 1}
    anforderungen = [_anforderung(1, "RASS1", ((800, 3),))]

    bericht = bedarfsdeckung.pruefe_bedarfsdeckung(
        anforderungen,
        freier_bestand,
        datenstand="Handfall",
        anlage_abweichungen={
            "materiallager.anfangsbestand.800": 3,
            "box.transportboxen_frei": 0,
        },
    )

    assert freier_bestand == {800: 1}
    export = json.loads(bericht.als_json())
    assert export["gedeckt"]
    assert export["datenstand"] == "Handfall"
    assert export["bestandsannahmen"] == [{"pno": 800, "basiswert": 1, "szenariowert": 3}]
    assert export["teile"] == [
        {
            "pno": 800,
            "bedarf": 3,
            "freier_bestand": 3,
            "fehlmenge": 0,
            "anforderungen": [{"anforderung_id": "1-RASS1", "station": "RASS1", "menge": 3}],
        },
    ]


@pytest.mark.parametrize("menge", [-1, True, 2.5])
def test_bedarfsdeckung_lehnt_ungueltige_bestandsabweichungen_ab(menge):
    with pytest.raises(ValueError, match=r"materiallager\.anfangsbestand\.800"):
        bedarfsdeckung.pruefe_bedarfsdeckung(
            [],
            {800: 1},
            datenstand="Handfall",
            anlage_abweichungen={"materiallager.anfangsbestand.800": menge},
        )
