"""Kommandozeile der Datenschicht.

Beispiele::

    python -m matsim.daten importiere
    python -m matsim.daten vergleiche 2026-11-09_1516 2026-11-09_1557
    python -m matsim.daten bestand 2026-11-09_1516
    python -m matsim.daten abgleich 2026-11-09_1516 2026-11-09_1522
    python -m matsim.daten qualitaet
    python -m matsim.daten stichprobe 9178
    python -m matsim.daten zeiten
    python -m matsim.daten live-vergleich 2026-11-09_1557
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from matsim.daten import (
    bestand,
    dump_import,
    materialpfad,
    qualitaet,
    snapshot_vergleich,
    zeiten,
)
from matsim.pfade import INTERIM, PROCESSED, ROH_SNAPSHOTS

LETZTER_SNAPSHOT = "2026-11-09_1557"


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
    differenzen = snapshot_vergleich.vergleiche(
        _sqlite_pfad(argumente.a), _sqlite_pfad(argumente.b)
    )
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
        start = bestand.startbestand(verbindung)
        print("Startbestand frei (verortet, im Kreislauf):", start.teile_frei)
        print("Teile in Boxen ohne Ort:", start.teile_ohne_ort)
        print(
            f"Boxen: {start.boxen_stammdaten} laut Stammdaten, {len(start.boxen_verortet)} "
            f"verortet, leer im Kreislauf {start.leere_boxen}, "
            f"leer am Handarbeitsplatz {start.leere_boxen_ausserhalb}"
        )
    finally:
        verbindung.close()


def _abgleich(argumente: argparse.Namespace) -> None:
    a = sqlite3.connect(_sqlite_pfad(argumente.a))
    b = sqlite3.connect(_sqlite_pfad(argumente.b))
    historie = sqlite3.connect(_sqlite_pfad(argumente.historie))
    try:
        abweichungen = materialpfad.abgleich(a, b, historie)
        print(
            f"Export A ~ {materialpfad.exportzeit(a):%H:%M:%S}, "
            f"Export B ~ {materialpfad.exportzeit(b):%H:%M:%S}"
        )
        print(f"Abweichende Boxplätze (Box, Platz, erwartet, in B): {len(abweichungen)}")
        for zeile in abweichungen:
            print("  ", zeile)
    finally:
        for verbindung in (a, b, historie):
            verbindung.close()


def _qualitaet(argumente: argparse.Namespace) -> None:
    verbindung = sqlite3.connect(_sqlite_pfad(argumente.snapshot))
    try:
        print(f"Snapshot {argumente.snapshot}")
        print(f"{'Nr.':<6}{'geprüft':>9}{'auffällig':>11}{'Anteil':>9}  Prüfung")
        for e in qualitaet.pruefe_alle(verbindung):
            print(f"{e.nr:<6}{e.geprueft:>9}{e.auffaellig:>11}{e.anteil:>9.1%}  {e.titel}")
            print(f"{'':<6}auffällig: {e.pruefung}")
            print(f"{'':<6}Beispiel: {e.beispiel}")
    finally:
        verbindung.close()


def _stichprobe(argumente: argparse.Namespace) -> None:
    verbindung = sqlite3.connect(_sqlite_pfad(argumente.snapshot))
    try:
        for zeitpunkt, text in materialpfad.verfolge_auftrag(verbindung, argumente.ono):
            print(f"{zeitpunkt:%Y-%m-%d %H:%M:%S}  {text}")
    finally:
        verbindung.close()


def _zeiten(argumente: argparse.Namespace) -> None:
    verbindung = sqlite3.connect(_sqlite_pfad(argumente.snapshot))
    try:
        verteilungen = zeiten.leite_verteilungen_ab(verbindung)
        ziel = PROCESSED / zeiten.VERTEILUNGSDATEI
        zeiten.speichere_verteilungen(verteilungen, ziel)
        print(f"{ziel} geschrieben")
        print(f"{'Verteilung':<42}{'n roh':>7}{'entfernt':>9}{'Median':>8}{'q10':>7}{'q90':>7}")
        for name, v in verteilungen.items():
            print(f"{name:<42}{v.n_roh:>7}{v.entfernt:>9}{v.median:>8g}{v.q10:>7g}{v.q90:>7g}")
        anzahl, paare = zeiten.kommissionier_ueberlappungen(verbindung)
        print(f"Kommissionierung: {anzahl} Aufträge, {len(paare)} überlappende Paare")
        zerlegt, ohne = zeiten.transportzerlegung(verbindung)
        print(f"Ablieferungen einem Robotino zugeordnet: {len(zerlegt)}, nicht zuordenbar: {ohne}")
        for tag, fahrzeuge in list(zeiten.aktive_fahrzeuge_je_tag(verbindung).items())[-5:]:
            gleichzeitig = zeiten.max_gleichzeitig_aktiv(verbindung, tag)
            print(f"  {tag}: aktiv {fahrzeuge}, höchstens {gleichzeitig} gleichzeitig")
    finally:
        verbindung.close()


def _live_vergleich(argumente: argparse.Namespace) -> None:
    from matsim.daten import live

    snapshot = sqlite3.connect(_sqlite_pfad(argumente.snapshot))
    try:
        print(f"{'Tabelle':<24}{'live':>10}{'Snapshot':>10}{'Differenz':>11}")
        for tabelle, zeilen_live, zeilen_snapshot in live.vergleiche_mit_snapshot(snapshot):
            differenz = zeilen_live - zeilen_snapshot
            print(f"{tabelle:<24}{zeilen_live:>10}{zeilen_snapshot:>10}{differenz:>+11}")
    finally:
        snapshot.close()


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
    abgleichbefehl = befehle.add_parser(
        "abgleich", help="Boxinhalt von A mit Picks und Montagen fortschreiben, mit B vergleichen"
    )
    abgleichbefehl.add_argument("a")
    abgleichbefehl.add_argument("b")
    abgleichbefehl.add_argument("--historie", default=LETZTER_SNAPSHOT)
    abgleichbefehl.set_defaults(funktion=_abgleich)
    qualitaetsbefehl = befehle.add_parser("qualitaet", help="Prüfungen zum Befundregister")
    qualitaetsbefehl.add_argument("snapshot", nargs="?", default=LETZTER_SNAPSHOT)
    qualitaetsbefehl.set_defaults(funktion=_qualitaet)
    stichprobe = befehle.add_parser("stichprobe", help="Materialpfad eines Produktionsauftrags")
    stichprobe.add_argument("ono", type=int)
    stichprobe.add_argument("--snapshot", default=LETZTER_SNAPSHOT)
    stichprobe.set_defaults(funktion=_stichprobe)
    zeitbefehl = befehle.add_parser(
        "zeiten", help="Zeitverteilungen ableiten und nach data/processed/ schreiben"
    )
    zeitbefehl.add_argument("snapshot", nargs="?", default=LETZTER_SNAPSHOT)
    zeitbefehl.set_defaults(funktion=_zeiten)
    live_befehl = befehle.add_parser(
        "live-vergleich", help="Zeilenzahlen live (nur lesend, Labornetz) gegen einen Snapshot"
    )
    live_befehl.add_argument("snapshot", nargs="?", default=LETZTER_SNAPSHOT)
    live_befehl.set_defaults(funktion=_live_vergleich)
    argumente = parser.parse_args()
    argumente.funktion(argumente)


if __name__ == "__main__":
    main()
