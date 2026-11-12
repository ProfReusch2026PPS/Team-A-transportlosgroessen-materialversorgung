"""Bestands- und Reservierungsauswertung eines Snapshots.

Zählregeln (siehe docs/projekt/datenmodell-mes.md):

* Teilebestand wird ausschließlich aus ``tblboxpos`` gezählt (ein Boxplatz = höchstens ein Teil).
* Boxbestand wird ausschließlich aus ``tblbufferpos`` gezählt (Zeilen mit ``BoxID > 0``).
* Eine Reservierung (``ONo <> 0``) ist kein zusätzlicher Bestand. Ein reservierter Boxplatz ohne
  Teil (``PNo = 0``) ist ein reservierter Zielplatz, kein Bestand.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Teilebestand:
    pno: int
    frei: int
    reserviert: int

    @property
    def physisch(self) -> int:
        return self.frei + self.reserviert


def teilebestand(verbindung: sqlite3.Connection) -> dict[int, Teilebestand]:
    """Physischer Teilebestand in Boxen je Teilenummer, getrennt nach frei und reserviert."""
    zeilen = verbindung.execute(
        "SELECT PNo, SUM(ONo = 0), SUM(ONo <> 0) FROM tblboxpos WHERE PNo > 0 GROUP BY PNo"
    )
    return {pno: Teilebestand(pno, frei, reserviert) for pno, frei, reserviert in zeilen}


def reservierte_zielplaetze(verbindung: sqlite3.Connection) -> list[tuple[int, int, int, int]]:
    """Boxplätze, die für eine Auftragsposition reserviert, aber noch leer sind.

    Liefert ``(BoxId, BoxPos, ONo, OPos)``. Diese Plätze sind kein Bestand.
    """
    return verbindung.execute(
        "SELECT BoxId, BoxPos, ONo, OPos FROM tblboxpos WHERE PNo = 0 AND ONo <> 0 "
        "ORDER BY BoxId, BoxPos"
    ).fetchall()


def boxstandorte(verbindung: sqlite3.Connection) -> dict[int, list[tuple[int, int, int]]]:
    """Standorte je Box-ID als Liste ``(ResourceId, BufNo, BufPos)`` aus ``tblbufferpos``.

    Eine Box mit mehr als einem Standort ist ein Datenbefund (Doppelverortung) und wird nicht
    stillschweigend bereinigt.
    """
    standorte: dict[int, list[tuple[int, int, int]]] = {}
    for box_id, resource, bufno, bufpos in verbindung.execute(
        "SELECT BoxID, ResourceId, BufNo, BufPos FROM tblbufferpos WHERE BoxID > 0 "
        "ORDER BY BoxID, ResourceId, BufNo, BufPos"
    ):
        standorte.setdefault(box_id, []).append((resource, bufno, bufpos))
    return standorte


def reservierungen_ohne_auftrag(verbindung: sqlite3.Connection) -> dict[str, int]:
    """Zählt Bindungen an Auftragsnummern, die in ``tblorder`` nicht (mehr) existieren.

    Solche Reservierungen bleiben ungeklärt und gelten nicht als freier Bestand.
    """
    abfragen = {
        "tblboxpos": "SELECT COUNT(*) FROM tblboxpos WHERE ONo <> 0 "
        "AND ONo NOT IN (SELECT ONo FROM tblorder)",
        "tblbufferpos": "SELECT COUNT(*) FROM tblbufferpos WHERE ONo <> 0 "
        "AND ONo NOT IN (SELECT ONo FROM tblorder)",
        "tblcarrier": "SELECT COUNT(*) FROM tblcarrier WHERE ONo <> 0 "
        "AND ONo NOT IN (SELECT ONo FROM tblorder)",
        "tblstepparameter": "SELECT COUNT(*) FROM tblstepparameter "
        "WHERE ONo NOT IN (SELECT ONo FROM tblorder)",
    }
    return {tabelle: verbindung.execute(sql).fetchone()[0] for tabelle, sql in abfragen.items()}
