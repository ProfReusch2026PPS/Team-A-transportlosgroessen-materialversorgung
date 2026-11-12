"""Gemeinsame Fixtures. Tests mit dem Marker ``dumps`` brauchen die lokalen MES-Dumps."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from matsim.daten.dump_import import dump_nach_sqlite, snapshot_kurzname
from matsim.pfade import ROH_SNAPSHOTS

ERWARTETE_SNAPSHOTS = ["1516", "1522", "1525", "1536", "1541", "1557"]


@pytest.fixture(scope="session")
def snapshot_pfade(tmp_path_factory) -> dict[str, Path]:
    """Importiert alle lokalen Dumps in ein temporäres Verzeichnis; Schlüssel ist die Uhrzeit."""
    dumps = sorted(ROH_SNAPSHOTS.glob("*.sql"))
    if len(dumps) != len(ERWARTETE_SNAPSHOTS):
        pytest.skip(f"{len(dumps)} von 6 Dumps in {ROH_SNAPSHOTS} gefunden")
    ordner = tmp_path_factory.mktemp("snapshots")
    pfade = {}
    for dump in dumps:
        kurzname = snapshot_kurzname(dump)
        pfade[kurzname[-4:]] = ordner / f"{kurzname}.sqlite"
        dump_nach_sqlite(dump, pfade[kurzname[-4:]])
    return pfade


@pytest.fixture(scope="session")
def snapshots(snapshot_pfade) -> dict[str, sqlite3.Connection]:
    verbindungen = {name: sqlite3.connect(pfad) for name, pfad in snapshot_pfade.items()}
    yield verbindungen
    for verbindung in verbindungen.values():
        verbindung.close()
