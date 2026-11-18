"""Zeitansätze und Verteilungen für das Unsicherheitsszenario (Issue #3)."""

from __future__ import annotations

import random

import pytest

from matsim.daten import zeiten
from matsim.modell.anlage import lade_anlage, wert


def test_verteilungen_ohne_dumps_abrufbar_und_in_anlage_yaml_belegt():
    anlage = lade_anlage()
    verteilungen = zeiten.lade_verteilungen()
    assert "kommissionierplatz.pickzeit_je_teil_s" in verteilungen
    assert "fahrzeuge.hintransport_s" in verteilungen
    for name, v in verteilungen.items():
        wert(anlage, name)  # jeder Name ist ein belegter Parameter in config/anlage.yaml
        assert v.werte == tuple(sorted(v.werte))
        assert v.untere_grenze <= v.werte[0] and v.werte[-1] <= v.obere_grenze
        assert v.entfernt >= 0


def test_ziehen_ist_mit_seed_reproduzierbar():
    v = zeiten.verteilung("kommissionierplatz.pickzeit_je_teil_s")
    a = [v.ziehe(random.Random(11)) for _ in range(3)]
    b = [v.ziehe(random.Random(11)) for _ in range(3)]
    assert a == b
    rng = random.Random(1)
    stichprobe = [v.ziehe(rng) for _ in range(2000)]
    assert min(stichprobe) >= v.werte[0] and max(stichprobe) <= v.werte[-1]
    with pytest.raises(KeyError):
        zeiten.verteilung("gibt.es.nicht")


def test_stoerungsgrenzen_schuetzen_enge_verteilungen():
    eng = [25.0] * 20 + [24.0, 26.0, 40.0, 900.0]
    unten, oben = zeiten.stoerungsgrenzen(eng)
    assert oben == 50.0  # 2 x Median, nicht Q3 + 3 IQR = 25
    v = zeiten.bereinige("test", "synthetisch", eng)
    assert v.entfernt == 1 and v.werte[-1] == 40.0


@pytest.mark.dumps
def test_verteilungsdatei_entspricht_den_dumps(snapshots):
    abgeleitet = zeiten.leite_verteilungen_ab(snapshots["1557"])
    gespeichert = zeiten.lade_verteilungen()
    assert set(abgeleitet) == set(gespeichert)
    for name, v in abgeleitet.items():
        assert v.werte == gespeichert[name].werte, name


@pytest.mark.dumps
def test_kommissionierung_nie_parallel(snapshots):
    assert zeiten.kommissionier_ueberlappungen(snapshots["1557"]) == (229, [])


@pytest.mark.dumps
def test_montagezeit_haengt_am_teil(snapshots):
    """Zweigipflige Montagezeit: erstes Teil eines Satzes lang, zweites kurz."""
    rass1 = zeiten.montagestatistik_je_teil(snapshots["1557"], "RASS1")
    rass2 = zeiten.montagestatistik_je_teil(snapshots["1557"], "RASS2")
    assert (rass1[800].median, rass1[814].median) == (39, 28)
    assert (rass2[813].median, rass2[811].median) == (40, 25)


@pytest.mark.dumps
def test_fahrzeuge_aus_tblmachinereport(snapshots):
    letzter = snapshots["1557"]
    assert zeiten.aktive_fahrzeuge_je_tag(letzter)["2026-11-09"] == [24, 25]
    assert zeiten.max_gleichzeitig_aktiv(letzter, "2026-11-09") == 2
    zerlegt, ohne = zeiten.transportzerlegung(letzter)
    assert (len(zerlegt), ohne) == (189, 40)
    # 09.11.2026: laut Snapshots fuhr Robotino 25 die Boxen für RASS1 und RASS2, 24 für RASS3.
    am_0911 = {z.ono: z.fahrzeug for z in zerlegt if z.ono in (9177, 9179, 9180)}
    assert am_0911 == {9177: 25, 9179: 25, 9180: 24}


@pytest.mark.dumps
def test_festwerte_in_anlage_yaml_passen_zu_den_daten(snapshots):
    anlage = lade_anlage()
    letzter = snapshots["1557"]
    for station, (opno, resource_id, _) in zeiten.MONTAGE.items():
        for pno, s in zeiten.montagestatistik_je_teil(letzter, station).items():
            if pno in zeiten.MATERIALSATZ_WPNO_1000[station]:
                assert wert(anlage, f"stationen.{station}.montagezeit_s.{pno}") == s.median
        assert wert(anlage, f"stationen.{station}.montagezeit_je_teil_s") == (
            zeiten.statistik(letzter, opno, resource_id).median
        )
    assert wert(anlage, "fahrzeuge.hintransport_s") == 130
    assert (
        wert(anlage, "fahrzeuge.fahrauftrag_s")
        == zeiten.verteilung("fahrzeuge.fahrauftrag_s").median
    )
