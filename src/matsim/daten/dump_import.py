"""Import eines MES4-Dumps (mysqldump-Format) nach SQLite, ohne Datenbankserver.

Der Parser liest ``CREATE TABLE``-Blöcke (Spaltennamen und -typen) und
``INSERT INTO `t` VALUES (...),(...);``-Zeilen. Die Rohdatei wird nicht verändert.

Tabellen mit personenbezogenen Daten (``PERSONENBEZOGENE_TABELLEN``) werden nie exportiert.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

#: Enthalten Namen und E-Mail-Adressen und werden grundsätzlich nicht importiert.
PERSONENBEZOGENE_TABELLEN: frozenset[str] = frozenset({"tblcustomer", "tblusercontrol"})

_CREATE_RE = re.compile(r"^CREATE TABLE `(?P<name>[^`]+)` \($")
_SPALTE_RE = re.compile(r"^\s+`(?P<name>[^`]+)` (?P<typ>[a-zA-Z]+)")
_INSERT_RE = re.compile(r"^INSERT INTO `(?P<name>[^`]+)` VALUES ")
# Ein Wert: quotierter String (mit Backslash-Escapes oder verdoppeltem '), sonst bis , oder ).
_WERT_RE = re.compile(r"'(?:[^'\\]|\\.|'')*'|[^,()']+")
_ESCAPES = {
    "0": "\0",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "Z": "\x1a",
    "b": "\b",
}
_GANZZAHL_TYPEN = {"int", "tinyint", "smallint", "mediumint", "bigint", "bit", "year"}
_GLEITKOMMA_TYPEN = {"float", "double", "decimal", "real", "numeric"}


class DumpFormatFehler(ValueError):
    """Der Dump entspricht nicht dem erwarteten mysqldump-Format."""


@dataclass
class Tabelle:
    """Struktur und Zeilen einer Tabelle aus dem Dump."""

    name: str
    spalten: list[str] = field(default_factory=list)
    typen: list[str] = field(default_factory=list)
    zeilen: list[tuple] = field(default_factory=list)


def _entquote(roh: str) -> str:
    """Wandelt einen quotierten mysqldump-String (ohne äußere Quotes) in Text um."""
    if "\\" not in roh and "''" not in roh:
        return roh
    teile: list[str] = []
    i = 0
    while i < len(roh):
        zeichen = roh[i]
        if zeichen == "\\" and i + 1 < len(roh):
            folge = roh[i + 1]
            teile.append(_ESCAPES.get(folge, folge))
            i += 2
        elif zeichen == "'" and roh[i + 1 : i + 2] == "'":
            teile.append("'")
            i += 2
        else:
            teile.append(zeichen)
            i += 1
    return "".join(teile)


def _wert(token: str) -> object:
    if token.startswith("'"):
        return _entquote(token[1:-1])
    token = token.strip()
    if token == "NULL":
        return None
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        return token  # z. B. Hex-Literal 0x..., bleibt Text


def parse_values(text: str) -> Iterator[tuple]:
    """Zerlegt den Teil hinter ``VALUES`` in Zeilentupel.

    >>> list(parse_values("(1,'a,b',NULL),(2,'it\\\\'s',3.5);"))
    [(1, 'a,b', None), (2, "it's", 3.5)]
    """
    pos = 0
    laenge = len(text)
    while pos < laenge:
        if text[pos] != "(":
            if text[pos] in ",; \r\n":
                pos += 1
                continue
            raise DumpFormatFehler(f"Unerwartetes Zeichen {text[pos]!r} an Position {pos}")
        pos += 1
        zeile: list[object] = []
        while True:
            if text[pos] == ")":  # leerer Wert bzw. leeres Tupel
                pos += 1
                break
            treffer = _WERT_RE.match(text, pos)
            if treffer is None:
                raise DumpFormatFehler(f"Wert nicht lesbar an Position {pos}")
            zeile.append(_wert(treffer.group()))
            pos = treffer.end()
            if text[pos] == ",":
                pos += 1
            elif text[pos] == ")":
                pos += 1
                break
            else:
                raise DumpFormatFehler(f"Unerwartetes Zeichen {text[pos]!r} an Position {pos}")
        yield tuple(zeile)


def lies_dump(pfad: Path, ohne: frozenset[str] = PERSONENBEZOGENE_TABELLEN) -> dict[str, Tabelle]:
    """Liest einen Dump vollständig ein und liefert ``{tabellenname: Tabelle}``.

    Tabellen aus ``ohne`` werden übersprungen (weder Struktur noch Zeilen).
    """
    tabellen: dict[str, Tabelle] = {}
    aktuelle: Tabelle | None = None
    with pfad.open(encoding="utf-8-sig", newline="") as datei:
        for zeile in datei:
            if aktuelle is not None:
                spalte = _SPALTE_RE.match(zeile)
                if spalte:
                    aktuelle.spalten.append(spalte["name"])
                    aktuelle.typen.append(spalte["typ"].lower())
                elif zeile.startswith(")"):
                    aktuelle = None
                continue
            if zeile.startswith("CREATE TABLE"):
                kopf = _CREATE_RE.match(zeile.rstrip("\r\n"))
                if kopf is None:
                    raise DumpFormatFehler(f"CREATE TABLE nicht lesbar: {zeile[:80]!r}")
                name = kopf["name"].lower()
                aktuelle = Tabelle(name)
                if name not in ohne:
                    tabellen[name] = aktuelle
            elif zeile.startswith("INSERT INTO"):
                kopf = _INSERT_RE.match(zeile)
                if kopf is None:
                    raise DumpFormatFehler(f"INSERT nicht lesbar: {zeile[:80]!r}")
                name = kopf["name"].lower()
                if name in ohne:
                    continue
                if name not in tabellen:
                    raise DumpFormatFehler(f"INSERT vor CREATE TABLE für {name}")
                tabelle = tabellen[name]
                for werte in parse_values(zeile[kopf.end() :]):
                    if len(werte) != len(tabelle.spalten):
                        raise DumpFormatFehler(
                            f"{name}: {len(werte)} Werte bei {len(tabelle.spalten)} Spalten"
                        )
                    tabelle.zeilen.append(werte)
    return tabellen


def _sqlite_typ(mysql_typ: str) -> str:
    if mysql_typ in _GANZZAHL_TYPEN:
        return "INTEGER"
    if mysql_typ in _GLEITKOMMA_TYPEN:
        return "REAL"
    return "TEXT"


def sha256(pfad: Path) -> str:
    """SHA-256-Prüfsumme einer Datei (hexadezimal)."""
    summe = hashlib.sha256()
    with pfad.open("rb") as datei:
        for block in iter(lambda: datei.read(1 << 20), b""):
            summe.update(block)
    return summe.hexdigest()


def dump_nach_sqlite(
    dump: Path, ziel: Path, ohne: frozenset[str] = PERSONENBEZOGENE_TABELLEN
) -> dict[str, int]:
    """Überführt einen Dump in eine SQLite-Datei und liefert ``{tabelle: zeilenzahl}``.

    Eine vorhandene Zieldatei wird ersetzt (sie ist abgeleitet und reproduzierbar).
    Zusätzlich entsteht die Tabelle ``_snapshot_meta`` mit Quelldatei und Prüfsumme.
    """
    tabellen = lies_dump(dump, ohne)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    if ziel.exists():
        ziel.unlink()
    verbindung = sqlite3.connect(ziel)
    try:
        for tabelle in tabellen.values():
            spalten = ", ".join(
                f'"{name}" {_sqlite_typ(typ)}'
                for name, typ in zip(tabelle.spalten, tabelle.typen, strict=True)
            )
            verbindung.execute(f'CREATE TABLE "{tabelle.name}" ({spalten})')
            platzhalter = ", ".join("?" * len(tabelle.spalten))
            verbindung.executemany(
                f'INSERT INTO "{tabelle.name}" VALUES ({platzhalter})', tabelle.zeilen
            )
        verbindung.execute("CREATE TABLE _snapshot_meta (schluessel TEXT PRIMARY KEY, wert TEXT)")
        verbindung.executemany(
            "INSERT INTO _snapshot_meta VALUES (?, ?)",
            [("quelle", dump.name), ("sha256", sha256(dump))],
        )
        verbindung.commit()
    finally:
        verbindung.close()
    return {name: len(tabelle.zeilen) for name, tabelle in tabellen.items()}


def snapshot_kurzname(dump: Path) -> str:
    """Leitet aus ``DB_Export_2026.11.09_1516_... .sql`` den Kurznamen ``2026-11-09_1516`` ab."""
    treffer = re.match(r"DB_Export_(\d{4})\.(\d{2})\.(\d{2})_(\d{4})", dump.name)
    if treffer is None:
        return dump.stem.replace(" ", "_")
    jahr, monat, tag, uhrzeit = treffer.groups()
    return f"{jahr}-{monat}-{tag}_{uhrzeit}"
