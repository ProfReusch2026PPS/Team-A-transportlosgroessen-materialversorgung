"""Materialpfad und Beladungsregeln aus der Historie (Issue #4)."""

from __future__ import annotations

import pytest

from matsim.daten import materialpfad
from matsim.modell.anlage import lade_anlage, wert


@pytest.mark.dumps
def test_jeder_kommissionierauftrag_fuellt_genau_eine_zielbox_einer_station(snapshots):
    zielboxen: dict[int, set[int]] = {}
    for u in materialpfad.umsetzungen(snapshots["1557"]):
        zielboxen.setdefault(u.ono, set()).add(u.zielbox)
    assert len(zielboxen) == 229
    assert all(len(boxen) == 1 for boxen in zielboxen.values())


@pytest.mark.dumps
def test_nie_gemischte_zielboxen(snapshots):
    nutzungen, paare = materialpfad.gemischte_zielboxen(snapshots["1557"])
    assert (nutzungen, paare) == (229, [])


@pytest.mark.dumps
def test_saetze_liegen_vollstaendig_in_einer_box(snapshots):
    klassen = materialpfad.satzpruefung(snapshots["1557"])
    assert len(klassen["vollstaendig"]) == 262
    assert klassen["geteilt"] == [] and klassen["unvollstaendig"] == []
    assert klassen["ohne_pick"] == [(8926, 1, 1), (9093, 1, 3)]


@pytest.mark.dumps
def test_box_kapazitaet_wird_nie_ueberschritten(snapshots):
    teile: dict[int, int] = {}
    for u in materialpfad.umsetzungen(snapshots["1557"]):
        teile[u.ono] = teile.get(u.ono, 0) + 1
    assert max(teile.values()) == 8 == wert(lade_anlage(), "box.positionen")


def test_beladungsregeln_in_anlage_yaml():
    anlage = lade_anlage()
    assert wert(anlage, "beladung.stationen_je_box") == 1
    assert wert(anlage, "beladung.zielboxen_je_kommissionierauftrag") == 1
    assert wert(anlage, "beladung.satz_vollstaendig_in_einer_box") is True
    for station in ("RASS1", "RASS2", "RASS3"):
        satzgroesse = sum(
            eintrag["wert"] for eintrag in anlage["stationen"][station]["materialsatz"].values()
        )
        assert wert(anlage, f"beladung.max_saetze_je_box.{station}") == (
            wert(anlage, "box.positionen") // satzgroesse
        )
