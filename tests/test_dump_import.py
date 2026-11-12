"""Dump-Import: Parser an einem synthetischen Dump, danach an allen sechs echten Dumps."""

from __future__ import annotations

import sqlite3

import pytest

from matsim.daten import bestand, zeiten
from matsim.daten.dump_import import (
    PERSONENBEZOGENE_TABELLEN,
    dump_nach_sqlite,
    parse_values,
    snapshot_kurzname,
)
from matsim.daten.snapshot_vergleich import vergleiche

MINI_DUMP = r"""-- MySQL dump
CREATE TABLE `tblDemo` (
  `Id` int(11) NOT NULL DEFAULT 0,
  `Text` varchar(50) DEFAULT NULL,
  `Wert` double DEFAULT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB;
INSERT INTO `tblDemo` VALUES (1,'a,b (c)',1.5),(2,'it\'s; ok',NULL),(3,'',-7);
CREATE TABLE `tblcustomer` (
  `CNo` int(11) NOT NULL,
  `Name` varchar(50) DEFAULT NULL
) ENGINE=InnoDB;
INSERT INTO `tblcustomer` VALUES (1,'Geheim');
"""


def test_parse_values_behandelt_quotes_kommas_und_null():
    assert list(parse_values(r"(1,'a,b (c)',NULL),(2,'it\'s',3.5);")) == [
        (1, "a,b (c)", None),
        (2, "it's", 3.5),
    ]


def test_import_synthetischer_dump(tmp_path):
    dump = tmp_path / "DB_Export_2026.11.09_1516_demo.sql"
    dump.write_text(MINI_DUMP, encoding="utf-8-sig")
    ziel = tmp_path / "demo.sqlite"
    assert dump_nach_sqlite(dump, ziel) == {"tbldemo": 3}
    verbindung = sqlite3.connect(ziel)
    assert verbindung.execute("SELECT * FROM tbldemo ORDER BY Id").fetchall() == [
        (1, "a,b (c)", 1.5),
        (2, "it's; ok", None),
        (3, "", -7.0),
    ]
    tabellen = {n for (n,) in verbindung.execute("SELECT name FROM sqlite_master")}
    verbindung.close()
    assert "tblcustomer" not in tabellen  # personenbezogen, wird nie exportiert
    assert snapshot_kurzname(dump) == "2026-11-09_1516"


@pytest.mark.dumps
def test_alle_sechs_dumps_importierbar(snapshots):
    assert sorted(snapshots) == ["1516", "1522", "1525", "1536", "1541", "1557"]
    for verbindung in snapshots.values():
        tabellen = {
            n for (n,) in verbindung.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert len(tabellen - {"_snapshot_meta"}) == 62  # 64 Tabellen minus 2 personenbezogene
        assert not (tabellen & PERSONENBEZOGENE_TABELLEN)
        assert verbindung.execute("SELECT COUNT(*) FROM tblboxpos").fetchone()[0] == 320


@pytest.mark.dumps
def test_mengenbilanz_der_snapshots(snapshots):
    """Verbrauch von je 3 Stück passt zu 3 gefertigten Produkten; Reservierung ist kein Bestand."""
    anfang = bestand.teilebestand(snapshots["1516"])
    ende = bestand.teilebestand(snapshots["1557"])
    assert (anfang[800].frei, anfang[800].reserviert) == (9, 3)
    assert (anfang[814].frei, anfang[814].reserviert) == (13, 3)
    for pno in (800, 814, 811, 813, 831):
        assert anfang[pno].physisch - ende[pno].physisch == 3
        assert ende[pno].reserviert == 0
    for pno in (812, 832, 833, 834):
        assert anfang[pno].physisch == ende[pno].physisch


@pytest.mark.dumps
def test_reservierter_zielplatz_ist_kein_bestand(snapshots):
    plaetze = bestand.reservierte_zielplaetze(snapshots["1522"])
    assert len(plaetze) == 6
    assert {ono for _, _, ono, _ in plaetze} == {9179}
    assert bestand.reservierte_zielplaetze(snapshots["1557"]) == []


@pytest.mark.dumps
def test_boxbestand_und_ungeklaerte_bindungen(snapshots):
    for verbindung in snapshots.values():
        assert len(bestand.boxstandorte(verbindung)) == 21  # tblboxdef nennt 40
    doppelt = {b: o for b, o in bestand.boxstandorte(snapshots["1557"]).items() if len(o) > 1}
    assert list(doppelt) == [11]  # Datenbefund B-11, wird nicht bereinigt
    assert bestand.reservierungen_ohne_auftrag(snapshots["1516"])["tblstepparameter"] == 26


@pytest.mark.dumps
def test_zeitansaetze_und_snapshot_vergleich(snapshots, snapshot_pfade):
    letzter = snapshots["1557"]
    assert zeiten.statistik(letzter, 220, 19).median == 23
    assert zeiten.statistik(letzter, 323, 2).median == 37
    assert zeiten.statistik(letzter, 325, 6).median == 24
    differenzen = vergleiche(snapshot_pfade["1516"], snapshot_pfade["1557"])
    veraendert = {d.tabelle for d in differenzen if d.veraendert}
    assert {"tblboxpos", "tblbufferpos", "tblorder", "tblfinstep"} <= veraendert
    assert "tblstepdef" not in veraendert
