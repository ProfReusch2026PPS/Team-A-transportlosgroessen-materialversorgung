"""Vergleich zweier importierter Snapshots (SQLite-Dateien) je Tabelle.

Verglichen werden vollständige Zeilen als Multimenge. Eine geänderte Zeile erscheint deshalb
einmal unter ``nur_a`` und einmal unter ``nur_b``. Das genügt, um zu sehen, welche Tabellen sich
zwischen zwei Momentaufnahmen bewegen; eine Bewegungshistorie entsteht daraus nicht.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TabellenDifferenz:
    tabelle: str
    zeilen_a: int
    zeilen_b: int
    nur_a: int
    nur_b: int

    @property
    def veraendert(self) -> bool:
        return self.nur_a > 0 or self.nur_b > 0


def _tabellen(verbindung: sqlite3.Connection) -> set[str]:
    zeilen = verbindung.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE '\\_%' ESCAPE '\\'"
    )
    return {name for (name,) in zeilen}


def _zeilen(verbindung: sqlite3.Connection, tabelle: str) -> Counter:
    return Counter(verbindung.execute(f'SELECT * FROM "{tabelle}"').fetchall())


def vergleiche(sqlite_a: Path, sqlite_b: Path) -> list[TabellenDifferenz]:
    """Liefert je Tabelle Zeilenzahlen und die Anzahl der nur in A bzw. nur in B vorhandenen Zeilen.

    Tabellen, die nur in einer der beiden Dateien existieren, werden mit Zeilenzahl 0 auf der
    anderen Seite ausgewiesen.
    """
    a = sqlite3.connect(sqlite_a)
    b = sqlite3.connect(sqlite_b)
    try:
        tabellen_a, tabellen_b = _tabellen(a), _tabellen(b)
        ergebnis = []
        for tabelle in sorted(tabellen_a | tabellen_b):
            zeilen_a = _zeilen(a, tabelle) if tabelle in tabellen_a else Counter()
            zeilen_b = _zeilen(b, tabelle) if tabelle in tabellen_b else Counter()
            ergebnis.append(
                TabellenDifferenz(
                    tabelle=tabelle,
                    zeilen_a=sum(zeilen_a.values()),
                    zeilen_b=sum(zeilen_b.values()),
                    nur_a=sum((zeilen_a - zeilen_b).values()),
                    nur_b=sum((zeilen_b - zeilen_a).values()),
                )
            )
        return ergebnis
    finally:
        a.close()
        b.close()
