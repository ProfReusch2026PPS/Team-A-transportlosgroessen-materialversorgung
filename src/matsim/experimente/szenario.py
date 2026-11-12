"""Laden und Prüfen der Szenario-Dateien (Schnittstelle AP5 → AP3).

Schema: docs/projekt/versuchsplan.md. Alle Szenariowerte sind Szenarioannahmen, keine MES-Werte.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from matsim.pfade import SZENARIEN
from matsim.regeln.verfahren import VERFAHREN

SCHEMA_VERSION = 1
BEDARFSMUSTER = {"gleichmaessig", "spitze"}
ZEITMODI = {"fest", "verteilung"}
ZWECKE = {"parameterwahl", "abschlusspruefung"}


class SzenarioFehler(ValueError):
    """Eine Szenario-Datei verletzt das vereinbarte Schema."""


def pruefe_szenario(daten: dict[str, Any], quelle: str = "") -> None:
    fehler: list[str] = []

    def verlange(bedingung: bool, meldung: str) -> None:
        if not bedingung:
            fehler.append(meldung)

    verlange(daten.get("schema_version") == SCHEMA_VERSION, "schema_version falsch")
    for schluessel in ("name", "beschreibung", "zweck", "laufzeit", "replikationen", "bedarf",
                       "zeiten", "verfahren"):
        verlange(schluessel in daten, f"'{schluessel}' fehlt")
    if not fehler:
        verlange(daten["zweck"] in ZWECKE, f"zweck muss eines von {sorted(ZWECKE)} sein")
        laufzeit = daten["laufzeit"]
        for schluessel in ("max_laufzeit_s", "einschwingphase_s", "endkriterium"):
            verlange(schluessel in laufzeit, f"laufzeit.{schluessel} fehlt")
        replikationen = daten["replikationen"]
        seeds = replikationen.get("seeds", [])
        verlange(len(seeds) == replikationen.get("anzahl"), "Anzahl der Seeds ≠ replikationen.anzahl")
        verlange(len(set(seeds)) == len(seeds), "Seeds müssen verschieden sein")
        verlange(daten["bedarf"].get("muster") in BEDARFSMUSTER, "bedarf.muster unbekannt")
        verlange(daten["zeiten"].get("modus") in ZEITMODI, "zeiten.modus unbekannt")
        if daten["zeiten"].get("modus") == "verteilung":
            verlange(len(seeds) > 1, "zufällige Dauern erfordern mehrere Replikationen")
        unbekannt = [name for name in daten["verfahren"] if name not in VERFAHREN]
        verlange(not unbekannt, f"unbekannte Verfahren: {unbekannt}")
    if fehler:
        raise SzenarioFehler(f"{quelle}: " + "; ".join(fehler))


def lade_szenario(pfad: Path) -> dict[str, Any]:
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    pruefe_szenario(daten, pfad.name)
    return daten


def lade_alle(ordner: Path = SZENARIEN) -> dict[str, dict[str, Any]]:
    """Lädt alle ``*.yaml`` des Szenario-Ordners, Schlüssel ist ``name``."""
    szenarien = {}
    for pfad in sorted(ordner.glob("*.yaml")):
        daten = lade_szenario(pfad)
        if daten["name"] in szenarien:
            raise SzenarioFehler(f"Szenarioname doppelt: {daten['name']}")
        szenarien[daten["name"]] = daten
    return szenarien
