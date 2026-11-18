"""Startbestand, Boxstandorte und Abgleich der Schritthistorie mit den Snapshots (Issue #2)."""

from __future__ import annotations

import pytest

from matsim.daten import bestand, materialpfad
from matsim.modell.anlage import lade_anlage, wert

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
