"""Vereinbarte Schnittstellen: Anlage, Szenarien, Verfahren, Ereignisprotokoll, Smoke-Test."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

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


def _schreibe_anlage(
    tmp_path: Path, aenderungen: dict[tuple[str | int, ...], object]
) -> Path:
    anlage = lade_anlage()
    for pfad, neuer_wert in aenderungen.items():
        knoten = anlage
        for schluessel in pfad:
            knoten = knoten[schluessel]
        knoten["wert"] = neuer_wert
    datei = tmp_path / "anlage.yaml"
    datei.write_text(yaml.safe_dump(anlage, allow_unicode=True), encoding="utf-8")
    return datei


@pytest.mark.parametrize(
    ("pfad", "neuer_wert", "meldung"),
    [
        (("box", "positionen"), 0, "positive ganze Zahl"),
        (("box", "positionen"), True, "positive ganze Zahl"),
        (("materiallager", "anfangsbestand", 800), -1, "nichtnegative ganze Zahl"),
        (("fahrzeuge", "anzahl"), "2", "nichtnegative ganze Zahl"),
        (("stationen", "RASS1", "uebergabeplaetze"), 1.5, "nichtnegative ganze Zahl"),
        (("stationen", "RASS1", "materialsatz", 800), 0, "positive ganze Zahl"),
        (("kommissionierplatz", "vorlauf_s"), -1, "endliche, nichtnegative Zahl"),
        (("fahrzeuge", "fahrauftrag_s"), float("inf"), "endliche, nichtnegative Zahl"),
        (("stationen", "RASS1", "montagezeit_s", 800), float("nan"), "endliche, nichtnegative Zahl"),
        (("werkstueckumlauf", "bandsegment_s"), False, "endliche, nichtnegative Zahl"),
        (("stationen", "RASS1", "zulaessige_teile"), [814], "nicht zulässig"),
        (("stationen", "RASS1", "materialsatz", 800), 8, "ein Satz benötigt 9 Positionen"),
        (("beladung", "max_saetze_je_box", "RASS1"), 5, "5 Sätze × 2 Positionen"),
    ],
)
def test_anlage_lehnt_fachlich_ungueltige_werte_ab(tmp_path, pfad, neuer_wert, meldung):
    datei = _schreibe_anlage(tmp_path, {pfad: neuer_wert})
    fehlerpfad = {
        ("stationen", "RASS1", "zulaessige_teile"): "stationen.RASS1.materialsatz.800",
        ("stationen", "RASS1", "materialsatz", 800): (
            "stationen.RASS1.materialsatz" if neuer_wert == 8 else "stationen.RASS1.materialsatz.800"
        ),
    }.get(pfad, ".".join(map(str, pfad)))

    with pytest.raises(AnlagenFehler) as fehler:
        lade_anlage(datei)
    assert f"{fehlerpfad}:" in str(fehler.value)
    assert meldung in str(fehler.value)


@pytest.mark.parametrize("obergrenze", [2, 3])
def test_anlage_erlaubt_geaenderte_gueltige_mengen_und_engpaesse(tmp_path, obergrenze):
    datei = _schreibe_anlage(
        tmp_path,
        {
            ("box", "positionen"): 9,
            ("stationen", "RASS1", "materialsatz", 800): 2,
            ("beladung", "max_saetze_je_box", "RASS1"): obergrenze,
            ("materiallager", "anfangsbestand", 800): 0,
            ("fahrzeuge", "anzahl"): 0,
            ("kommissionierplatz", "vorlauf_s"): 0.0,
        },
    )

    anlage = lade_anlage(datei)
    assert wert(anlage, "beladung.max_saetze_je_box.RASS1") == obergrenze
    assert wert(anlage, "materiallager.anfangsbestand.800") == 0
    assert wert(anlage, "fahrzeuge.anzahl") == 0


def test_anlage_meldet_fehlende_satzobergrenze_und_erhaelt_offene_dauer(tmp_path):
    anlage = lade_anlage()
    anlage["kommissionierplatz"]["vorlauf_s"] = {
        "wert": None, "herkunft": "offen", "beleg": "Testdaten: Vorlauf noch nicht bekannt",
    }
    datei = tmp_path / "anlage.yaml"
    datei.write_text(yaml.safe_dump(anlage), encoding="utf-8")
    geladen = lade_anlage(datei)
    assert "kommissionierplatz.vorlauf_s" in offene_parameter(geladen)
    with pytest.raises(AnlagenFehler, match=r"kommissionierplatz\.vorlauf_s ist noch offen"):
        wert(geladen, "kommissionierplatz.vorlauf_s")

    del anlage["beladung"]["max_saetze_je_box"]["RASS1"]
    datei.write_text(yaml.safe_dump(anlage), encoding="utf-8")
    with pytest.raises(AnlagenFehler, match=r"beladung\.max_saetze_je_box\.RASS1: .* fehlt"):
        lade_anlage(datei)


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
