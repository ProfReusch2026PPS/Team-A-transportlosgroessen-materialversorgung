"""Vereinbarte Schnittstellen: Anlage, Szenarien, Verfahren, Ereignisprotokoll, Smoke-Test."""

from __future__ import annotations

import pytest

from matsim import smoke
from matsim.daten.live import NurLesenFehler, pruefe_nur_lesend
from matsim.experimente.szenario import SzenarioFehler, lade_alle, pruefe_szenario
from matsim.kennzahlen.ereignisprotokoll import (
    Ereignisprotokoll,
    Ereignistyp,
    Warteursache,
    lade_csv,
)
from matsim.modell.anlage import AnlagenFehler, lade_anlage, offene_parameter, wert
from matsim.regeln.verfahren import VERFAHREN


def test_anlage_laedt_und_kennzeichnet_offene_parameter():
    anlage = lade_anlage()
    assert wert(anlage, "box.positionen") == 8
    assert wert(anlage, "stationen.RASS1.materialsatz.800") == 1
    assert "werkstueckumlauf.wiederkehrregel" in offene_parameter(anlage)
    with pytest.raises(AnlagenFehler):
        wert(anlage, "werkstueckumlauf.wiederkehrregel")


def test_szenarien_decken_versuchsplan_ab():
    szenarien = lade_alle()
    assert {"basis", "bedarfsspitze", "knappe_boxen", "unsicherheit"} <= set(szenarien)
    for szenario in szenarien.values():
        assert set(szenario["verfahren"]) == set(VERFAHREN)
    kaputt = dict(szenarien["basis"], replikationen={"anzahl": 2, "seeds": [1]})
    with pytest.raises(SzenarioFehler):
        pruefe_szenario(kaputt)


def test_ereignisprotokoll_roundtrip_und_ursachenpflicht(tmp_path):
    protokoll = Ereignisprotokoll()
    protokoll.schreibe(0, Ereignistyp.BEDARF_EINGANG, anforderung_id="A1")
    protokoll.schreibe(
        5, Ereignistyp.WARTEN_BEGINN, anforderung_id="A1", ursache=Warteursache.BUENDELUNG
    )
    with pytest.raises(ValueError):
        protokoll.schreibe(6, Ereignistyp.WARTEN_BEGINN, anforderung_id="A1")
    with pytest.raises(ValueError):
        protokoll.schreibe(1, Ereignistyp.LIEFERUNG, anforderung_id="A1")  # Zeit läuft rückwärts
    datei = tmp_path / "ereignisse.csv"
    protokoll.speichere_csv(datei)
    assert lade_csv(datei) == protokoll.ereignisse


def test_live_zugriff_ist_nur_lesend():
    pruefe_nur_lesend("SELECT * FROM mes4.tblfinstep WHERE ONo = ?")
    for sql in (
        "UPDATE tblboxpos SET PNo = 0",
        "SELECT 1; DROP TABLE tblorder",
        "SELECT * FROM tblcustomer",
        "DELETE FROM tblorder",
    ):
        with pytest.raises(NurLesenFehler):
            pruefe_nur_lesend(sql)


def test_smoke(capsys):
    smoke.main()
    assert "Smoke-Test bestanden" in capsys.readouterr().out
