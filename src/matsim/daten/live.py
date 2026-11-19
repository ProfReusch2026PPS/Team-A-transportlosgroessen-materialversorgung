"""Lesender Zugriff auf eine MariaDB mit dem MES4-Schema.

Das ist entweder die Labordatenbank (nur im Labornetz erreichbar) oder eine lokale MariaDB, in
die die Dumps des Dozenten geladen sind (Anleitung: docs/projekt/datenmodell-mes.md, Abschnitt
4.3). Zugangsdaten kommen ausschließlich aus Umgebungsvariablen (``DB_HOST``, ``DB_USER``,
``DB_PASSWORD``, ``DB_NAME``, optional ``DB_PORT``), z. B. aus einer lokalen, nicht versionierten
``.env``. Es werden nur ``SELECT``-Abfragen ausgeführt.
"""

from __future__ import annotations

import os
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from matsim.daten.dump_import import PERSONENBEZOGENE_TABELLEN
from matsim.pfade import WURZEL

_VARIABLEN = ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME")
_VERBOTEN = re.compile(
    r"\b(insert|update|delete|replace|drop|alter|create|truncate|grant|revoke|call|set|load|"
    r"lock|rename|into\s+outfile)\b",
    re.IGNORECASE,
)


class NurLesenFehler(PermissionError):
    """Die Abfrage ist kein reines SELECT oder berührt eine gesperrte Tabelle."""


def lade_env(pfad: Path = WURZEL / ".env") -> None:
    """Liest ``SCHLUESSEL=wert``-Zeilen aus einer ``.env`` in die Umgebung (ohne zu überschreiben)."""
    if not pfad.exists():
        return
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        schluessel, wert = zeile.split("=", 1)
        os.environ.setdefault(schluessel.strip(), wert.strip())


def pruefe_nur_lesend(sql: str) -> None:
    """Wirft ``NurLesenFehler``, wenn ``sql`` kein einzelnes SELECT ist.

    >>> pruefe_nur_lesend("SELECT * FROM tblfinstep WHERE ONo = ?")
    """
    bereinigt = sql.strip().rstrip(";")
    if not bereinigt.lower().startswith("select"):
        raise NurLesenFehler("Nur SELECT-Abfragen sind erlaubt")
    if ";" in bereinigt:
        raise NurLesenFehler("Nur eine Anweisung je Aufruf")
    if _VERBOTEN.search(bereinigt):
        raise NurLesenFehler("Abfrage enthält ein schreibendes Schlüsselwort")
    for tabelle in PERSONENBEZOGENE_TABELLEN:
        if re.search(rf"\b{tabelle}\b", bereinigt, re.IGNORECASE):
            raise NurLesenFehler(f"{tabelle} enthält personenbezogene Daten und ist gesperrt")


def verbinde(datenbank: str | None = None):
    """Öffnet eine Verbindung mit den Werten aus der Umgebung. Benötigt das Extra ``live``.

    ``datenbank`` ersetzt ``DB_NAME``, etwa um lokal zwischen den sechs Snapshots zu wechseln.
    """
    lade_env()
    fehlend = [name for name in _VARIABLEN if not os.environ.get(name)]
    if fehlend:
        raise RuntimeError(f"Umgebungsvariablen fehlen: {', '.join(fehlend)} (siehe .env.example)")
    try:
        import mariadb
    except ImportError as fehler:
        raise RuntimeError('Paket "mariadb" fehlt: pip install -e ".[live]"') from fehler
    return mariadb.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT") or 3306),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=datenbank or os.environ["DB_NAME"],
    )


def lies(sql: str, parameter: tuple = (), verbindung=None) -> list[tuple]:
    """Führt ein geprüftes SELECT aus und liefert alle Zeilen.

    Ohne ``verbindung`` wird eine eigene Verbindung geöffnet und wieder geschlossen.
    """
    pruefe_nur_lesend(sql)
    eigene = verbindung is None
    verbindung = verbinde() if eigene else verbindung
    try:
        cursor = verbindung.cursor()
        cursor.execute(sql, parameter)
        return cursor.fetchall()
    finally:
        if eigene:
            verbindung.close()


#: Tabellen für den Abgleich Live gegen Snapshot: Stammdaten (sollten gleich sein) und
#: Zustands- bzw. Historientabellen (dürfen sich seit dem Export bewegt haben).
VERGLEICHSTABELLEN = (
    "tblresource",
    "tblbuffer",
    "tbltopology",
    "tblboxdef",
    "tblbox",
    "tblparts",
    "tblstepdef",
    "tblstepparameterdef",
    "tbloperation",
    "tblsqlquery",
    "tblboxpos",
    "tblbufferpos",
    "tblorder",
    "tblfinorder",
    "tblfinorderpos",
    "tblfinstep",
    "tblmachinereport",
)


def vergleiche_mit_snapshot(snapshot, verbindung=None) -> list[tuple[str, int, int]]:
    """Zeilenzahl je Tabelle in der Live-Datenbank und in einem importierten Snapshot.

    ``snapshot`` ist eine ``sqlite3.Connection``. Liefert ``(Tabelle, live, snapshot)``. Es
    werden nur ``SELECT COUNT(*)`` ausgeführt.
    """
    eigene = verbindung is None
    verbindung = verbinde() if eigene else verbindung
    try:
        ergebnis = []
        for tabelle in VERGLEICHSTABELLEN:
            live = lies(f"SELECT COUNT(*) FROM {tabelle}", verbindung=verbindung)[0][0]
            lokal = snapshot.execute(f"SELECT COUNT(*) FROM {tabelle}").fetchone()[0]
            ergebnis.append((tabelle, live, lokal))
        return ergebnis
    finally:
        if eigene:
            verbindung.close()


def _normalisiere(wert: object) -> object:
    """Bringt einen MariaDB-Wert in die Darstellung des SQLite-Imports."""
    if isinstance(wert, datetime):
        return wert.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(wert, date):
        return wert.isoformat()
    if isinstance(wert, timedelta):
        sekunden = int(wert.total_seconds())
        return f"{sekunden // 3600:02d}:{sekunden % 3600 // 60:02d}:{sekunden % 60:02d}"
    if isinstance(wert, time):
        return wert.strftime("%H:%M:%S")
    if isinstance(wert, Decimal):
        return float(wert)
    if isinstance(wert, (bytes, bytearray)):
        return bytes(wert).decode("utf-8", errors="replace")
    if isinstance(wert, float) and wert.is_integer():
        return wert
    return wert


@dataclass(frozen=True)
class Inhaltsvergleich:
    tabelle: str
    zeilen_db: int
    zeilen_snapshot: int
    nur_db: int
    nur_snapshot: int
    beispiel: tuple | None  # eine abweichende Zeile aus der Datenbank, falls vorhanden

    @property
    def gleich(self) -> bool:
        return self.nur_db == 0 and self.nur_snapshot == 0


def vergleiche_inhalt(
    snapshot: sqlite3.Connection, verbindung, tabellen: tuple[str, ...] | None = None
) -> list[Inhaltsvergleich]:
    """Vergleicht je Tabelle alle Zeilen der Datenbank mit dem SQLite-Import als Multimenge.

    Damit wird der eigene Dump-Import (``matsim.daten.dump_import``) unabhängig geprüft: Die
    Datenbank hat den Dump mit dem MariaDB-Parser gelesen, der Import mit unserem eigenen.
    Werte werden vorher normalisiert (Zeitpunkte als Text, Dezimalzahlen als Gleitkomma).
    Ohne ``tabellen`` werden alle Tabellen des Snapshots verglichen.
    """
    if tabellen is None:
        tabellen = tuple(
            name
            for (name,) in snapshot.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'tbl%' "
                "ORDER BY name"
            )
        )
    ergebnis = []
    for tabelle in tabellen:
        db = Counter(
            tuple(_normalisiere(w) for w in zeile)
            for zeile in lies(f"SELECT * FROM {tabelle}", verbindung=verbindung)
        )
        lokal = Counter(snapshot.execute(f"SELECT * FROM {tabelle}").fetchall())
        nur_db, nur_snapshot = db - lokal, lokal - db
        ergebnis.append(
            Inhaltsvergleich(
                tabelle,
                sum(db.values()),
                sum(lokal.values()),
                sum(nur_db.values()),
                sum(nur_snapshot.values()),
                next(iter(nur_db), None),
            )
        )
    return ergebnis
