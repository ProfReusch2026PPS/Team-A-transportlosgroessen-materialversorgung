"""Lesender Datenbankzugriff: Normalisierung und Vergleich mit dem SQLite-Import.

Der Vergleich gegen eine echte MariaDB läuft nur, wenn eine erreichbar ist (lokal mit den
geladenen Dumps oder im Labornetz, Zugang über .env); sonst wird er übersprungen.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from matsim.daten import live


def test_normalisierung_entspricht_dem_sqlite_import():
    assert live._normalisiere(datetime(2026, 11, 9, 15, 8, 29)) == "2026-11-09 15:08:29"
    assert live._normalisiere(Decimal("1.5")) == 1.5
    assert live._normalisiere(timedelta(hours=1, seconds=5)) == "01:00:05"
    assert live._normalisiere("text") == "text"
    assert live._normalisiere(None) is None


@pytest.fixture(scope="module")
def datenbank():
    try:
        verbindung = live.verbinde("mes4_1557")
    except Exception as fehler:  # keine .env, kein Treiber oder Server nicht erreichbar
        pytest.skip(f"keine MariaDB erreichbar: {fehler}")
    yield verbindung
    verbindung.close()


@pytest.mark.dumps
def test_datenbank_und_import_sind_zeilengleich(datenbank, snapshots):
    ergebnisse = live.vergleiche_inhalt(snapshots["1557"], datenbank)
    assert len(ergebnisse) == 62
    assert [e.tabelle for e in ergebnisse if not e.gleich] == []


def test_zugang_ist_nur_lesend(datenbank):
    with pytest.raises(live.NurLesenFehler):
        live.lies("DELETE FROM tblorder", verbindung=datenbank)
