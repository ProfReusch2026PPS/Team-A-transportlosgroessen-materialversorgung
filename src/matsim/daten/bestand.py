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


#: Ressourcen der assistierten Handarbeitsplätze AASS1/AASS2. Eine Box dort steht außerhalb des
#: Kreislaufs Lager -> Kommissionierung -> Montagestation.
HANDARBEITSPLAETZE = frozenset({26, 27})


def boxstandort_aufgeloest(
    verbindung: sqlite3.Connection,
) -> dict[int, tuple[int, int, int]]:
    """Ein Standort ``(ResourceId, BufNo, BufPos)`` je verorteter Box.

    Steht eine Box an mehreren Orten (Befund B-11), gilt der Platz mit dem jüngsten
    ``TimeStamp``: Das ist die zuletzt gebuchte Bewegung. Die Rohdaten bleiben unverändert.
    """
    standort: dict[int, tuple[str, tuple[int, int, int]]] = {}
    for box, resource, bufno, bufpos, zeit in verbindung.execute(
        "SELECT BoxID, ResourceId, BufNo, BufPos, TimeStamp FROM tblbufferpos WHERE BoxID > 0"
    ):
        if box not in standort or (zeit or "") > standort[box][0]:
            standort[box] = (zeit or "", (resource, bufno, bufpos))
    return {box: ort for box, (_, ort) in sorted(standort.items())}


def letzte_kommissionierung_je_box(verbindung: sqlite3.Connection) -> dict[int, str | None]:
    """Letzter Pick-Start, bei dem eine Box Quell- oder Zielbox war (``None`` = nie)."""
    letzte: dict[int, str | None] = {
        box: None for (box,) in verbindung.execute("SELECT BoxID FROM tblbox")
    }
    for box, start in verbindung.execute(
        "SELECT CAST(p.Parameter AS INTEGER), MAX(s.Start) FROM tblfinstepparameter p "
        "JOIN tblfinstep s ON s.ONo = p.ONo AND s.OPos = p.OPos AND s.StepNo = p.StepNo "
        "WHERE s.OpNo = 220 AND p.StepNo = 10 AND p.ParameterNo IN (3, 6) "
        "GROUP BY CAST(p.Parameter AS INTEGER)"
    ):
        letzte[box] = start
    return letzte


@dataclass(frozen=True)
class Startbestand:
    """Startbestand der Simulation aus einem Snapshot nach den Zählregeln (A-02, A-03)."""

    teile_frei: dict[int, int]  # freie Teile in verorteten Boxen außerhalb der Handarbeitsplätze
    teile_ohne_ort: dict[int, int]  # Teile in Boxen ohne Ort, nur für die Sensitivität
    teile_reserviert: dict[int, int]
    boxen_stammdaten: int
    boxen_verortet: list[int]
    boxen_ohne_ort: list[int]
    leere_boxen: list[int]  # leer, verortet, im Kreislauf: Transportboxen
    leere_boxen_ausserhalb: list[int]  # leer, aber an einem Handarbeitsplatz


def startbestand(verbindung: sqlite3.Connection) -> Startbestand:
    """Zählt Teile und Boxen eines Snapshots so, wie sie in die Simulation gehen.

    * Teilebestand nur aus ``tblboxpos``; Reservierungen sind kein zusätzlicher Bestand.
    * Frei ist ein Teil mit ``ONo = 0`` in einer verorteten Box, die nicht an einem
      Handarbeitsplatz steht.
    * Boxen werden nur aus ``tblbufferpos`` gezählt, jede Box einmal (Standort nach
      :func:`boxstandort_aufgeloest`).
    """
    standort = boxstandort_aufgeloest(verbindung)
    im_kreislauf = {b for b, ort in standort.items() if ort[0] not in HANDARBEITSPLAETZE}
    alle = [b for (b,) in verbindung.execute("SELECT BoxID FROM tblbox ORDER BY BoxID")]
    frei: dict[int, int] = {}
    ohne_ort: dict[int, int] = {}
    reserviert: dict[int, int] = {}
    belegt: set[int] = set()
    for box, pno, ono in verbindung.execute(
        "SELECT BoxId, PNo, ONo FROM tblboxpos WHERE PNo > 0 OR ONo <> 0"
    ):
        belegt.add(box)
        if pno == 0:
            continue
        if box not in standort:
            ohne_ort[pno] = ohne_ort.get(pno, 0) + 1
        elif ono != 0:
            reserviert[pno] = reserviert.get(pno, 0) + 1
        elif box in im_kreislauf:
            frei[pno] = frei.get(pno, 0) + 1
    leer = [b for b in standort if b not in belegt]
    return Startbestand(
        teile_frei=dict(sorted(frei.items())),
        teile_ohne_ort=dict(sorted(ohne_ort.items())),
        teile_reserviert=dict(sorted(reserviert.items())),
        boxen_stammdaten=len(alle),
        boxen_verortet=sorted(standort),
        boxen_ohne_ort=[b for b in alle if b not in standort],
        leere_boxen=[b for b in leer if b in im_kreislauf],
        leere_boxen_ausserhalb=[b for b in leer if b not in im_kreislauf],
    )
