"""Materialpfad eines Teils aus der Schritthistorie: Kommissionieren, Ablieferung, Montage.

Grundlage sind die Parameter der Kommissionieroperation (OpNo 220, Schritt 10 der Arbeitspläne
WPNo 1, 2 und 3) in ``tblfinstepparameter``. Ihre Bedeutung folgt aus dem hinterlegten SQL
(``tbloperation.SqlWrite`` für OpNo 220 und ``tblstepdef.SqlWrite`` für WPNo 1, Schritt 20):

=====  ==========================================================
Nr.    Bedeutung
=====  ==========================================================
2      Puffernummer der Quellbox an der Kommissionierstation
3      Quellbox (``BoxId``)
4      Platz in der Quellbox
5      Puffernummer der Zielbox an der Kommissionierstation
6      Zielbox (``BoxId``)
7      Platz in der Zielbox
8, 9   Produktionsauftrag und -position, für die das Teil bestimmt ist
10     Montageschritt (``StepNo``) des Produktionsauftrags
11     Teilenummer
=====  ==========================================================

Die Rohdaten werden nur gelesen. Details und Belege: docs/projekt/datenmodell-mes.md, Abschnitt 5.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

_FORMAT = "%Y-%m-%d %H:%M:%S"
#: Kommissionier-Arbeitsplan -> Ressource der Zielstation (tblstepdef WPNo 1/2/3, Schritt 20).
ZIELSTATION = {1: 2, 2: 4, 3: 6}
#: Montageoperationen je Station.
MONTAGE_OPNO = {2: 323, 4: 324, 6: 325}
ABLIEFERUNG_OPNO = 215
KOMMISSIONIER_OPNO = 220


def _zeit(text: str | None) -> datetime | None:
    if not text:
        return None
    return datetime.strptime(text, _FORMAT)


@dataclass(frozen=True)
class Umsetzung:
    """Ein Teil, das an der Kommissionierstation von einer Quell- in eine Zielbox gesetzt wurde."""

    ono: int  # Kommissionierauftrag
    opos: int
    wpno: int  # 1, 2 oder 3 = Zielstation RASS1, RASS2, RASS3
    start: datetime | None
    ende: datetime | None
    pno: int
    quellbox: int
    quellplatz: int
    zielbox: int
    zielplatz: int
    prod_ono: int
    prod_opos: int
    prod_stepno: int

    @property
    def zielstation(self) -> int:
        return ZIELSTATION[self.wpno]


def umsetzungen(verbindung: sqlite3.Connection) -> list[Umsetzung]:
    """Alle Kommissionierschritte (OpNo 220) der Historie mit ihren Parametern, zeitlich sortiert."""
    parameter: dict[tuple[int, int], dict[int, str]] = defaultdict(dict)
    for ono, opos, nr, wert in verbindung.execute(
        "SELECT ONo, OPos, ParameterNo, Parameter FROM tblfinstepparameter "
        "WHERE WPNo IN (1, 2, 3) AND StepNo = 10"
    ):
        parameter[(ono, opos)][nr] = wert
    ergebnis = []
    for ono, opos, wpno, start, ende in verbindung.execute(
        "SELECT ONo, OPos, WPNo, Start, End FROM tblfinstep WHERE OpNo = ? AND StepNo = 10",
        (KOMMISSIONIER_OPNO,),
    ):
        p = parameter.get((ono, opos))
        if p is None:
            continue
        ergebnis.append(
            Umsetzung(
                ono=ono,
                opos=opos,
                wpno=wpno,
                start=_zeit(start),
                ende=_zeit(ende),
                pno=int(p[11]),
                quellbox=int(p[3]),
                quellplatz=int(p[4]),
                zielbox=int(p[6]),
                zielplatz=int(p[7]),
                prod_ono=int(p[8]),
                prod_opos=int(p[9]),
                prod_stepno=int(p[10]),
            )
        )
    return sorted(ergebnis, key=lambda u: (u.start or datetime.min, u.ono, u.opos))


@dataclass(frozen=True)
class Ablieferung:
    """Ablieferung der Zielbox eines Kommissionierauftrags an der Station (OpNo 215)."""

    ono: int
    station: int
    start: datetime
    ende: datetime
    letzter_pick: datetime | None


def ablieferungen(verbindung: sqlite3.Connection) -> list[Ablieferung]:
    """Je Kommissionierauftrag der erste Start und das letzte Ende von OpNo 215."""
    zeilen = verbindung.execute(
        "SELECT s.ONo, s.ResourceID, MIN(s.Start), MAX(s.End), "
        "(SELECT MAX(k.End) FROM tblfinstep k WHERE k.ONo = s.ONo AND k.OpNo = ? "
        " AND k.End IS NOT NULL AND k.End <> '') "
        "FROM tblfinstep s WHERE s.OpNo = ? AND s.Start IS NOT NULL AND s.Start <> '' "
        "AND s.End IS NOT NULL AND s.End <> '' GROUP BY s.ONo ORDER BY MIN(s.Start)",
        (KOMMISSIONIER_OPNO, ABLIEFERUNG_OPNO),
    )
    return [
        Ablieferung(ono, station, _zeit(start), _zeit(ende), _zeit(letzter))
        for ono, station, start, ende, letzter in zeilen
    ]


def verfolge_auftrag(verbindung: sqlite3.Connection, ono: int) -> list[tuple[datetime, str]]:
    """Zeitlich sortierte Ereignisse eines Produktionsauftrags samt Materialpfad seiner Teile.

    Enthält die Schritte des Auftrags selbst (Auslagern, Montage, Prüfung, Einlagern), die
    Kommissionierschritte, die Teile für ihn umgesetzt haben, und die Ablieferung der Zielboxen.
    """
    ereignisse: list[tuple[datetime, str]] = []
    for opos, stepno, beschreibung, opno, resource, start, ende, fehler in verbindung.execute(
        "SELECT OPos, StepNo, Description, OpNo, ResourceID, Start, End, ErrorRetVal "
        "FROM tblfinstep WHERE ONo = ? ORDER BY Start, OPos, StepNo",
        (ono,),
    ):
        if not start:
            continue
        ereignisse.append(
            (
                _zeit(start),
                f"{ono}/{opos} Schritt {stepno} OpNo {opno} an Ressource {resource}: "
                f"{beschreibung} ({start[11:]} bis {(ende or '')[11:]}, Fehler {fehler})",
            )
        )
    teile = [u for u in umsetzungen(verbindung) if u.prod_ono == ono]
    for u in teile:
        if u.ende is None:
            continue
        ereignisse.append(
            (
                u.ende,
                f"Kommissionierung {u.ono}/{u.opos} (WPNo {u.wpno}): Teil {u.pno} aus Box "
                f"{u.quellbox}/{u.quellplatz} in Box {u.zielbox}/{u.zielplatz}, bestimmt für "
                f"{u.prod_ono}/{u.prod_opos} Schritt {u.prod_stepno}",
            )
        )
    for a in ablieferungen(verbindung):
        if a.ono in {u.ono for u in teile}:
            ereignisse.append(
                (
                    a.start,
                    f"Ablieferung {a.ono}: Zielbox an Ressource {a.station} "
                    f"(OpNo 215 {a.start:%H:%M:%S} bis {a.ende:%H:%M:%S})",
                )
            )
    return sorted(ereignisse, key=lambda e: e[0])


def montage_ohne_umsetzung(verbindung: sqlite3.Connection) -> tuple[int, list[tuple]]:
    """Montageschritte (OpNo 323 bis 325, mit Start, Ende, ohne Fehler) ohne verknüpften Pick.

    Liefert ``(geprüft, Liste der Schritte ohne Pick als (ONo, OPos, StepNo, OpNo, Start))``.
    """
    verknuepft = {(u.prod_ono, u.prod_opos, u.prod_stepno) for u in umsetzungen(verbindung)}
    schritte = verbindung.execute(
        "SELECT ONo, OPos, StepNo, OpNo, Start FROM tblfinstep WHERE OpNo IN (323, 324, 325) "
        "AND Start IS NOT NULL AND Start <> '' AND End IS NOT NULL AND End <> '' "
        "AND ErrorRetVal = 0 ORDER BY Start"
    ).fetchall()
    return len(schritte), [s for s in schritte if (s[0], s[1], s[2]) not in verknuepft]


def umsetzungen_ohne_produktionsposition(verbindung: sqlite3.Connection) -> list[Umsetzung]:
    """Picks, deren Produktionsbezug (Parameter 8/9) in ``tblfinorderpos`` fehlt."""
    positionen = set(verbindung.execute("SELECT ONo, OPos FROM tblfinorderpos").fetchall())
    return [u for u in umsetzungen(verbindung) if (u.prod_ono, u.prod_opos) not in positionen]
