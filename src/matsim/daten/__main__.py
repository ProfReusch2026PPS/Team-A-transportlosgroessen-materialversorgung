"""Kommandozeile der Datenschicht.

Beispiele::

    python -m matsim.daten importiere
    python -m matsim.daten vergleiche 2026-11-09_1516 2026-11-09_1557
    python -m matsim.daten bestand 2026-11-09_1516
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from matsim.daten import bestand, dump_import, snapshot_vergleich
from matsim.pfade import INTERIM, ROH_SNAPSHOTS


def _sqlite_pfad(kurzname: str) -> Path:
    pfad = INTERIM / f"{kurzname}.sqlite"
    if not pfad.exists():
        sys.exit(f"{pfad} fehlt. Zuerst: python -m matsim.daten importiere")
    return pfad


def _importiere(_: argparse.Namespace) -> None:
    dumps = sorted(ROH_SNAPSHOTS.glob("*.sql"))
    if not dumps:
        sys.exit(f"Keine Dumps in {ROH_SNAPSHOTS} (siehe data/raw/mes_snapshots/README.md)")
    for dump in dumps:
        ziel = INTERIM / f"{dump_import.snapshot_kurzname(dump)}.sqlite"
        zeilen = dump_import.dump_nach_sqlite(dump, ziel)
        print(f"{ziel.name}: {len(zeilen)} Tabellen, {sum(zeilen.values())} Zeilen")


def _vergleiche(argumente: argparse.Namespace) -> None:
    differenzen = snapshot_vergleich.vergleiche(_sqlite_pfad(argumente.a), _sqlite_pfad(argumente.b))
    print(f"{'Tabelle':<26}{'Zeilen A':>10}{'Zeilen B':>10}{'nur A':>8}{'nur B':>8}")
    for d in differenzen:
        if d.veraendert or argumente.alle:
            print(f"{d.tabelle:<26}{d.zeilen_a:>10}{d.zeilen_b:>10}{d.nur_a:>8}{d.nur_b:>8}")


def _bestand(argumente: argparse.Namespace) -> None:
    verbindung = sqlite3.connect(_sqlite_pfad(argumente.snapshot))
    try:
        print(f"{'PNo':>5}{'frei':>6}{'reserviert':>12}")
        for pno, eintrag in sorted(bestand.teilebestand(verbindung).items()):
            print(f"{pno:>5}{eintrag.frei:>6}{eintrag.reserviert:>12}")
        print("Reservierte Zielplätze ohne Teil:", bestand.reservierte_zielplaetze(verbindung))
        standorte = bestand.boxstandorte(verbindung)
        doppelt = {box: orte for box, orte in standorte.items() if len(orte) > 1}
        print(f"Verortete Boxen: {len(standorte)}; doppelt verortet: {doppelt}")
        print("Bindungen ohne Auftrag:", bestand.reservierungen_ohne_auftrag(verbindung))
    finally:
        verbindung.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m matsim.daten", description=__doc__)
    befehle = parser.add_subparsers(required=True)
    befehle.add_parser("importiere", help="alle Dumps nach data/interim/*.sqlite").set_defaults(
        funktion=_importiere
    )
    vergleich = befehle.add_parser("vergleiche", help="zwei Snapshots je Tabelle vergleichen")
    vergleich.add_argument("a")
    vergleich.add_argument("b")
    vergleich.add_argument("--alle", action="store_true", help="auch unveränderte Tabellen zeigen")
    vergleich.set_defaults(funktion=_vergleiche)
    bestandsbefehl = befehle.add_parser("bestand", help="Teile-, Box- und Reservierungsbestand")
    bestandsbefehl.add_argument("snapshot")
    bestandsbefehl.set_defaults(funktion=_bestand)
    argumente = parser.parse_args()
    argumente.funktion(argumente)


if __name__ == "__main__":
    main()
