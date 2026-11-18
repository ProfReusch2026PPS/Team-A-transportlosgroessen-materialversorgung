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
    start: datetime  # erster Start OpNo 215: Box an der Station
    erstes_ende: datetime  # erstes Ende OpNo 215
    ende: datetime  # letztes Ende OpNo 215
    letzter_pick: datetime | None


def ablieferungen(verbindung: sqlite3.Connection) -> list[Ablieferung]:
    """Je Kommissionierauftrag der erste Start und das letzte Ende von OpNo 215."""
    zeilen = verbindung.execute(
        "SELECT s.ONo, s.ResourceID, MIN(s.Start), MIN(s.End), MAX(s.End), "
        "(SELECT MAX(k.End) FROM tblfinstep k WHERE k.ONo = s.ONo AND k.OpNo = ? "
        " AND k.End IS NOT NULL AND k.End <> '') "
        "FROM tblfinstep s WHERE s.OpNo = ? AND s.Start IS NOT NULL AND s.Start <> '' "
        "AND s.End IS NOT NULL AND s.End <> '' GROUP BY s.ONo ORDER BY MIN(s.Start)",
        (KOMMISSIONIER_OPNO, ABLIEFERUNG_OPNO),
    )
    return [
        Ablieferung(ono, station, _zeit(start), _zeit(erstes), _zeit(ende), _zeit(letzter))
        for ono, station, start, erstes, ende, letzter in zeilen
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


def exportzeit(verbindung: sqlite3.Connection) -> datetime:
    """Schätzt den Exportzeitpunkt eines Snapshots als jüngsten Zeitstempel darin.

    Herangezogen werden Maschinenmeldungen, Pufferbelegung und laufende sowie abgeschlossene
    Schritte. Der echte Export liegt kurz danach.
    """
    abfragen = (
        "SELECT MAX(TimeStamp) FROM tblmachinereport",
        "SELECT MAX(TimeStamp) FROM tblbufferpos",
        "SELECT MAX(End) FROM tblfinstep WHERE End <> ''",
        "SELECT MAX(Start) FROM tblstep WHERE Start <> ''",
        "SELECT MAX(End) FROM tblstep WHERE End <> ''",
    )
    werte = [verbindung.execute(sql).fetchone()[0] for sql in abfragen]
    return max(_zeit(w) for w in werte if w)


def boxinhalt(verbindung: sqlite3.Connection) -> dict[tuple[int, int], int]:
    """Physischer Inhalt ``(BoxId, BoxPos) -> PNo`` aller Boxplätze (0 = leer)."""
    return {
        (box, platz): pno
        for box, platz, pno in verbindung.execute("SELECT BoxId, BoxPos, PNo FROM tblboxpos")
    }


def fortschreiben(
    inhalt: dict[tuple[int, int], int],
    historie: sqlite3.Connection,
    von: datetime,
    bis: datetime,
) -> dict[tuple[int, int], int]:
    """Schreibt einen Boxinhalt mit den Picks und Montagen aus ``(von, bis]`` fort.

    Ein Pick leert den Quellplatz und belegt den Zielplatz mit dem Teil. Eine Montage leert den
    Zielplatz des Picks, der für genau diesen Auftrag, diese Position und diesen Schritt
    umgesetzt hat. ``historie`` muss die Schritte des Zeitraums in ``tblfinstep`` enthalten
    (also ein späterer Snapshot sein).
    """
    ergebnis = dict(inhalt)
    picks = umsetzungen(historie)
    ziel_je_schritt = {(u.prod_ono, u.prod_opos, u.prod_stepno): u for u in picks}
    ereignisse: list[tuple[datetime, int, Umsetzung]] = [
        (u.ende, 0, u) for u in picks if u.ende is not None and von < u.ende <= bis
    ]
    for ono, opos, stepno, ende in historie.execute(
        "SELECT ONo, OPos, StepNo, End FROM tblfinstep WHERE OpNo IN (323, 324, 325) "
        "AND End IS NOT NULL AND End <> ''"
    ):
        zeitpunkt = _zeit(ende)
        pick = ziel_je_schritt.get((ono, opos, stepno))
        if pick is not None and von < zeitpunkt <= bis:
            ereignisse.append((zeitpunkt, 1, pick))
    for _, art, u in sorted(ereignisse, key=lambda e: (e[0], e[1])):
        if art == 0:
            ergebnis[(u.quellbox, u.quellplatz)] = 0
            ergebnis[(u.zielbox, u.zielplatz)] = u.pno
        else:
            ergebnis[(u.zielbox, u.zielplatz)] = 0
    return ergebnis


def abgleich(
    a: sqlite3.Connection, b: sqlite3.Connection, historie: sqlite3.Connection
) -> list[tuple[int, int, int, int]]:
    """Vergleicht den fortgeschriebenen Boxinhalt von Snapshot ``a`` mit Snapshot ``b``.

    Liefert die abweichenden Plätze als ``(BoxId, BoxPos, PNo erwartet, PNo in b)``. Eine leere
    Liste heißt: Jede Inhaltsänderung zwischen den beiden Snapshots ist durch einen Pick oder
    eine Montage der Historie erklärt.
    """
    erwartet = fortschreiben(boxinhalt(a), historie, exportzeit(a), exportzeit(b))
    tatsaechlich = boxinhalt(b)
    return sorted(
        (box, platz, erwartet.get((box, platz), 0), pno)
        for (box, platz), pno in tatsaechlich.items()
        if erwartet.get((box, platz), 0) != pno
    )


def quellboxen_je_auftrag(verbindung: sqlite3.Connection) -> dict[int, int]:
    """Anzahl verschiedener Quellboxen je Kommissionierauftrag.

    Jede Quellbox muss vom Boxlager zur Kommissionierstation und zurück gefahren werden. Diese
    Fahrten belegen dieselben Robotinos wie die Ablieferung der Zielbox.
    """
    quellen: dict[int, set[int]] = defaultdict(set)
    for u in umsetzungen(verbindung):
        quellen[u.ono].add(u.quellbox)
    return {ono: len(boxen) for ono, boxen in sorted(quellen.items())}


@dataclass(frozen=True)
class Zielboxnutzung:
    """Zeitraum, in dem eine Zielbox Teile eines Kommissionierauftrags trägt."""

    zielbox: int
    ono: int
    wpno: int
    beginn: datetime  # erster Pick in die Box
    ende: datetime  # letzte Montage eines dieser Teile, ersatzweise Ende der Ablieferung


def zielboxnutzungen(verbindung: sqlite3.Connection) -> list[Zielboxnutzung]:
    """Je Kommissionierauftrag und Zielbox der Zeitraum vom ersten Pick bis zum letzten Verbrauch."""
    montageende = {
        (ono, opos, stepno): _zeit(ende)
        for ono, opos, stepno, ende in verbindung.execute(
            "SELECT ONo, OPos, StepNo, End FROM tblfinstep WHERE OpNo IN (323, 324, 325) "
            "AND End IS NOT NULL AND End <> ''"
        )
    }
    lieferende = {a.ono: a.ende for a in ablieferungen(verbindung)}
    gruppen: dict[tuple[int, int], list[Umsetzung]] = defaultdict(list)
    for u in umsetzungen(verbindung):
        if u.start is not None:
            gruppen[(u.zielbox, u.ono)].append(u)
    nutzungen = []
    for (box, ono), teile in gruppen.items():
        enden = [
            montageende.get((u.prod_ono, u.prod_opos, u.prod_stepno)) or lieferende.get(ono)
            for u in teile
        ]
        enden = [e for e in enden if e is not None] or [max(u.ende or u.start for u in teile)]
        nutzungen.append(
            Zielboxnutzung(box, ono, teile[0].wpno, min(u.start for u in teile), max(enden))
        )
    return sorted(nutzungen, key=lambda n: (n.zielbox, n.beginn))


def gemischte_zielboxen(
    verbindung: sqlite3.Connection,
) -> tuple[int, list[tuple[Zielboxnutzung, Zielboxnutzung]]]:
    """Paare von Kommissionieraufträgen, deren Teile zur selben Zeit in derselben Zielbox lagen.

    Liefert ``(Anzahl Nutzungen, überlappende Paare)``. Ein Paar mit verschiedenem ``wpno`` wäre
    eine nach Station gemischte Box.
    """
    nutzungen = zielboxnutzungen(verbindung)
    paare = []
    for i, a in enumerate(nutzungen):
        for b in nutzungen[i + 1 :]:
            if b.zielbox != a.zielbox:
                break
            if b.beginn < a.ende:
                paare.append((a, b))
    return len(nutzungen), paare


def satzpruefung(verbindung: sqlite3.Connection) -> dict[str, list[tuple[int, int, int]]]:
    """Ordnet jeden Satz (Produktionsposition WPNo 1000 x Station) einer von vier Klassen zu.

    * ``vollstaendig``: alle Teile des Satzes im selben Kommissionierauftrag, also derselben Box
    * ``geteilt``: alle Teile kommissioniert, aber über mehrere Aufträge bzw. Boxen verteilt
    * ``unvollstaendig``: nur ein Teil des Satzes kommissioniert
    * ``ohne_pick``: kein Teil des Satzes kommissioniert

    Liefert je Klasse ``(ONo, OPos, Zielstation-WPNo)``. Grundlage sind die Montageschritte von
    WPNo 1000 (30/60 RASS1, 100/110 RASS2, 160 RASS3).
    """
    satzschritte = {1: (30, 60), 2: (100, 110), 3: (160,)}
    positionen = verbindung.execute(
        "SELECT ONo, OPos FROM tblfinorderpos WHERE WPNo = 1000 ORDER BY ONo, OPos"
    ).fetchall()
    pick = {(u.prod_ono, u.prod_opos, u.prod_stepno): u.ono for u in umsetzungen(verbindung)}
    klassen: dict[str, list[tuple[int, int, int]]] = {
        "vollstaendig": [],
        "geteilt": [],
        "unvollstaendig": [],
        "ohne_pick": [],
    }
    for ono, opos in positionen:
        for wpno, schritte in satzschritte.items():
            auftraege = [pick.get((ono, opos, s)) for s in schritte]
            gefunden = [a for a in auftraege if a is not None]
            if not gefunden:
                klasse = "ohne_pick"
            elif len(gefunden) < len(schritte):
                klasse = "unvollstaendig"
            elif len(set(gefunden)) > 1:
                klasse = "geteilt"
            else:
                klasse = "vollstaendig"
            klassen[klasse].append((ono, opos, wpno))
    return klassen
