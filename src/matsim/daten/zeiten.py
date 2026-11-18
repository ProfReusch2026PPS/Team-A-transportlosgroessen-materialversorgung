"""Zeitansätze aus der Schritthistorie ``tblfinstep``.

Eine Zeitstempeldifferenz ist nicht automatisch reine Bearbeitungs- oder Fahrzeit. Jede hier
berechnete Dauer ist ein abgeleiteter Wert; Filter und Bedeutung stehen in
docs/projekt/datenmodell-mes.md.
"""

from __future__ import annotations

import sqlite3
import statistics
from dataclasses import dataclass
from datetime import datetime

_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class Dauerstatistik:
    n_gesamt: int  # alle Schritte der Auswahl, vor dem Filter
    n: int  # Schritte nach dem Filter
    median: float
    mittel: float
    minimum: float
    maximum: float
    q10: float
    q90: float


def _sekunden(start: str, ende: str) -> float:
    return (datetime.strptime(ende, _FORMAT) - datetime.strptime(start, _FORMAT)).total_seconds()


def schrittdauern(verbindung: sqlite3.Connection, opno: int, resource_id: int) -> list[float]:
    """Dauern (Ende minus Start, in Sekunden) aller Schritte einer Operation an einer Ressource.

    Filter: Start und Ende vorhanden, ``ErrorRetVal = 0``.
    """
    zeilen = verbindung.execute(
        "SELECT Start, End FROM tblfinstep WHERE OpNo = ? AND ResourceID = ? "
        "AND Start IS NOT NULL AND End IS NOT NULL AND Start <> '' AND End <> '' "
        "AND ErrorRetVal = 0",
        (opno, resource_id),
    )
    return [_sekunden(start, ende) for start, ende in zeilen]


def statistik(verbindung: sqlite3.Connection, opno: int, resource_id: int) -> Dauerstatistik:
    """Lage- und Streuungsmaße der Schrittdauern (Median und Quantile statt nur Mittelwert)."""
    dauern = sorted(schrittdauern(verbindung, opno, resource_id))
    if not dauern:
        raise ValueError(f"Keine auswertbaren Schritte für OpNo {opno} an Ressource {resource_id}")
    gesamt = verbindung.execute(
        "SELECT COUNT(*) FROM tblfinstep WHERE OpNo = ? AND ResourceID = ?", (opno, resource_id)
    ).fetchone()[0]

    def quantil(p: float) -> float:
        return dauern[min(len(dauern) - 1, int(p * len(dauern)))]

    return Dauerstatistik(
        n_gesamt=gesamt,
        n=len(dauern),
        median=statistics.median(dauern),
        mittel=statistics.fmean(dauern),
        minimum=dauern[0],
        maximum=dauern[-1],
        q10=quantil(0.10),
        q90=quantil(0.90),
    )


def quartile(werte: list[float]) -> tuple[float, float]:
    """Unteres und oberes Quartil (Methode ``inclusive`` der Standardbibliothek)."""
    q1, _, q3 = statistics.quantiles(werte, n=4, method="inclusive")
    return q1, q3


def tukey_grenzen(werte: list[float], faktor: float = 3.0) -> tuple[float, float]:
    """Äußere Tukey-Grenzen ``Q1 - faktor * IQR`` und ``Q3 + faktor * IQR``.

    Mit ``faktor = 3`` („far out“) gelten nur deutlich abgesetzte Werte als Ausreißer. Sie werden
    als Störung gewertet (z. B. ein Pick mit 1051 s), nicht als normale Streuung.
    """
    q1, q3 = quartile(werte)
    iqr = q3 - q1
    return q1 - faktor * iqr, q3 + faktor * iqr


def zeitverteilung(verbindung: sqlite3.Connection, opno: int, resource_id: int):
    """Leitet eine belegte Verteilung für das Unsicherheitsszenario ab (AP1).

    Offen: Ausreißerbehandlung (Maximum 1051 s bei OpNo 220), Verteilungsfamilie oder empirische
    Verteilung, Trennung von Bearbeitungs- und Wartezeitanteilen.
    """
    raise NotImplementedError("AP1: Verteilung für das Unsicherheitsszenario ableiten")
