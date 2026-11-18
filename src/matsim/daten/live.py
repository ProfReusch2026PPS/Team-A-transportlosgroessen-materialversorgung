"""Lesender Live-Zugriff auf die MES-Datenbank im Labornetz.

Zugangsdaten kommen ausschließlich aus Umgebungsvariablen (``DB_HOST``, ``DB_USER``,
``DB_PASSWORD``, ``DB_NAME``), z. B. aus einer lokalen, nicht versionierten ``.env``.
Es werden nur ``SELECT``-Abfragen ausgeführt.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from matsim.daten.dump_import import PERSONENBEZOGENE_TABELLEN

_VARIABLEN = ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME")
_VERBOTEN = re.compile(
    r"\b(insert|update|delete|replace|drop|alter|create|truncate|grant|revoke|call|set|load|"
    r"lock|rename|into\s+outfile)\b",
    re.IGNORECASE,
)


class NurLesenFehler(PermissionError):
    """Die Abfrage ist kein reines SELECT oder berührt eine gesperrte Tabelle."""


def lade_env(pfad: Path = Path(".env")) -> None:
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


def verbinde():
    """Öffnet eine Verbindung mit den Werten aus der Umgebung. Benötigt das Extra ``live``."""
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
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
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
