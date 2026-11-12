"""Laden und Prüfen von ``config/anlage.yaml`` (Schnittstelle AP1 → AP3).

Jeder Parameter ist ein Eintrag ``{wert, herkunft, beleg}``. ``herkunft`` unterscheidet
MES-Werte, abgeleitete Werte, Annahmen und offene Punkte, wie es die Aufgabenstellung verlangt.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from matsim.pfade import ANLAGE

SCHEMA_VERSION = 1
HERKUNFT = {"mes", "abgeleitet", "annahme", "offen"}
PFLICHTABSCHNITTE = (
    "teile",
    "box",
    "materiallager",
    "kommissionierplatz",
    "fahrzeuge",
    "stationen",
    "werkstueckumlauf",
)


class AnlagenFehler(ValueError):
    """``anlage.yaml`` verletzt das vereinbarte Schema."""


def _pruefe_parameter(knoten: Any, pfad: str, fehler: list[str]) -> None:
    if isinstance(knoten, dict):
        if "herkunft" in knoten:
            if knoten["herkunft"] not in HERKUNFT:
                fehler.append(f"{pfad}: unbekannte Herkunft {knoten['herkunft']!r}")
            if "wert" not in knoten:
                fehler.append(f"{pfad}: Parameter ohne 'wert'")
            elif knoten["herkunft"] == "offen" and knoten["wert"] is not None:
                fehler.append(f"{pfad}: offener Parameter muss wert: null haben")
            elif knoten["herkunft"] != "offen" and knoten["wert"] is None:
                fehler.append(f"{pfad}: wert fehlt (oder herkunft: offen setzen)")
            if not knoten.get("beleg"):
                fehler.append(f"{pfad}: 'beleg' fehlt")
            return
        for schluessel, kind in knoten.items():
            _pruefe_parameter(kind, f"{pfad}.{schluessel}", fehler)
    elif isinstance(knoten, list):
        for index, kind in enumerate(knoten):
            _pruefe_parameter(kind, f"{pfad}[{index}]", fehler)


def lade_anlage(pfad: Path = ANLAGE) -> dict[str, Any]:
    """Lädt die Anlagenbeschreibung und prüft Schema, Herkunftsangaben und Materialsätze."""
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    fehler: list[str] = []
    if daten.get("schema_version") != SCHEMA_VERSION:
        fehler.append(f"schema_version muss {SCHEMA_VERSION} sein")
    for abschnitt in PFLICHTABSCHNITTE:
        if abschnitt not in daten:
            fehler.append(f"Abschnitt '{abschnitt}' fehlt")
    _pruefe_parameter(daten, "anlage", fehler)
    teile = set(daten.get("teile", {}))
    for name, station in daten.get("stationen", {}).items():
        for pno in station.get("materialsatz", {}):
            if pno not in teile:
                fehler.append(f"stationen.{name}.materialsatz: Teil {pno} nicht unter 'teile'")
    if fehler:
        raise AnlagenFehler("\n".join(fehler))
    return daten


def wert(daten: dict[str, Any], pfad: str) -> Any:
    """Liest den ``wert`` eines Parameters über einen Punktpfad, z. B. ``"box.positionen"``.

    Offene Parameter (``herkunft: offen``) führen zu einem Fehler statt zu einem stillen ``None``.
    """
    knoten: Any = daten
    for teil in pfad.split("."):
        # Teilenummern sind in YAML ganzzahlige Schlüssel.
        knoten = knoten[int(teil)] if teil.isdigit() and int(teil) in knoten else knoten[teil]
    if knoten["herkunft"] == "offen":
        raise AnlagenFehler(f"{pfad} ist noch offen: {knoten['beleg']}")
    return knoten["wert"]


def offene_parameter(daten: dict[str, Any]) -> list[str]:
    """Punktpfade aller Parameter mit ``herkunft: offen``."""
    offen: list[str] = []

    def suche(knoten: Any, pfad: str) -> None:
        if isinstance(knoten, dict):
            if knoten.get("herkunft") == "offen":
                offen.append(pfad)
                return
            for schluessel, kind in knoten.items():
                suche(kind, f"{pfad}.{schluessel}" if pfad else str(schluessel))

    suche(daten, "")
    return offen
