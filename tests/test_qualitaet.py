"""Datenqualitätsprüfungen (Befundregister) und Stichprobe Auftrag 9178 an den echten Dumps."""

from __future__ import annotations

import pytest

from matsim.daten import live, materialpfad, qualitaet, zeiten


def test_tukey_grenzen():
    unten, oben = zeiten.tukey_grenzen([1, 2, 3, 4, 5, 6, 7, 8, 9])
    assert (unten, oben) == (-9.0, 19.0)


def test_live_vergleich_fragt_nur_lesend():
    for tabelle in live.VERGLEICHSTABELLEN:
        live.pruefe_nur_lesend(f"SELECT COUNT(*) FROM {tabelle}")
    with pytest.raises(live.NurLesenFehler):
        live.pruefe_nur_lesend("DELETE FROM tblboxpos")


@pytest.mark.dumps
def test_alle_pruefungen_laufen_und_sind_vollstaendig(snapshots):
    ergebnisse = qualitaet.pruefe_alle(snapshots["1557"])
    assert [e.nr for e in ergebnisse] == [f"B-{i:02d}" for i in range(1, 25)]
    for e in ergebnisse:
        assert 0 <= e.auffaellig <= e.geprueft, e.nr
        assert e.pruefung and e.beispiel, e.nr


@pytest.mark.dumps
def test_befundzahlen_snapshot_1557(snapshots):
    e = {x.nr: (x.geprueft, x.auffaellig) for x in qualitaet.pruefe_alle(snapshots["1557"])}
    assert e["B-01"] == (14723, 0)
    assert e["B-03"] == (40, 0)
    assert e["B-05"] == (6, 6)
    assert e["B-06"] == (1498, 0)
    assert e["B-07"] == (572, 9)
    assert e["B-08"] == (18, 0)
    assert e["B-09"] == (40, 19)
    assert e["B-10"] == (71, 15)
    assert e["B-11"] == (21, 1)
    assert e["B-13"] == (1701, 104)
    assert e["B-14"] == (229, 21)
    assert e["B-16"] == (14723, 2645)
    assert e["B-20"] == (749, 176)


@pytest.mark.dumps
def test_doppelte_box_nur_im_letzten_snapshot(snapshots):
    for name, verbindung in snapshots.items():
        erwartet = 1 if name == "1557" else 0
        assert qualitaet.b11_doppelt_verortet(verbindung).auffaellig == erwartet


@pytest.mark.dumps
def test_stichprobe_9178_materialpfad(snapshots):
    letzter = snapshots["1557"]
    teile = [u for u in materialpfad.umsetzungen(letzter) if u.prod_ono == 9178]
    # Zwei Werkstücke mit je 2 + 2 + 1 Teilen aus den Kommissionieraufträgen 9177, 9179, 9180.
    assert len(teile) == 10
    assert {u.ono for u in teile} == {9177, 9179, 9180}
    assert {(u.prod_opos, u.prod_stepno, u.pno) for u in teile} == {
        (opos, schritt, pno)
        for opos in (1, 2)
        for schritt, pno in ((30, 800), (60, 814), (100, 813), (110, 811), (160, 831))
    }
    # Jedes Teil landet in der Zielbox seines Kommissionierauftrags: 11 (RASS1, RASS3), 18 (RASS2).
    assert {(u.ono, u.zielbox) for u in teile} == {(9177, 11), (9179, 18), (9180, 11)}
    ereignisse = materialpfad.verfolge_auftrag(letzter, 9178)
    assert ereignisse == sorted(ereignisse, key=lambda e: e[0])
    assert ereignisse[0][1].startswith("9178/1 Schritt 10 OpNo 212")
    assert ereignisse[-1][1].startswith("9178/1 Schritt 250 OpNo 211")


@pytest.mark.dumps
def test_stichprobe_9178_passt_zu_den_snapshots(snapshots):
    def box(snapshot, box_id):
        return (
            snapshots[snapshot]
            .execute(
                "SELECT BoxPos, PNo, ONo, OPos FROM tblboxpos WHERE BoxId = ? AND PNo > 0 "
                "ORDER BY BoxPos",
                (box_id,),
            )
            .fetchall()
        )

    # 15:22: RASS1-Box an der Station, Plätze 3/4 auf den Produktionsauftrag umgebucht (OpNo 215).
    assert box("1522", 11) == [(3, 800, 9178, 1), (4, 814, 9178, 1)]
    # 15:36: RASS2-Box an der Station, Teile für 9178/1 und 9178/2 auf den Plätzen 3 bis 6.
    assert (3, 813, 9178, 1) in box("1536", 18) and (6, 811, 9178, 2) in box("1536", 18)
