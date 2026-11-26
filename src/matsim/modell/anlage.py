"""Laden und Prüfen von ``config/anlage.yaml`` (Schnittstelle AP1 → AP3).

Jeder Parameter ist ein Eintrag ``{wert, herkunft, beleg}``. ``herkunft`` unterscheidet
MES-Werte, abgeleitete Werte, Annahmen und offene Punkte, wie es die Aufgabenstellung verlangt.
"""

from __future__ import annotations

import copy
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

from matsim.pfade import ANLAGE

SCHEMA_VERSION = 1
HERKUNFT = {"mes", "abgeleitet", "annahme", "offen"}
PFLICHTABSCHNITTE = (
    "teile",
    "box",
    "beladung",
    "materiallager",
    "kommissionierplatz",
    "fahrzeuge",
    "stationen",
    "werkstueckumlauf",
)
_ANZAHLEN = {
    "box": (
        "anzahl_stammdaten", "anzahl_verortet", "anzahl_ohne_ort",
        "transportboxen_frei", "quellboxen_mit_teilen",
    ),
    "materiallager": ("lagerplaetze", "vollstaendige_produkte_aus_anfangsbestand"),
    "kommissionierplatz": ("gleichzeitige_chargen", "quellboxen_je_auftrag", "baender"),
    "fahrzeuge": ("anzahl_stammdaten", "anzahl", "boxplaetze_je_fahrzeug"),
}


class AnlagenFehler(ValueError):
    """``anlage.yaml`` verletzt das vereinbarte Schema."""


def _pruefe_parameter(knoten: Any, pfad: str, fehler: list[str]) -> None:
    if isinstance(knoten, dict):
        if "herkunft" in knoten:
            herkunft = knoten["herkunft"]
            if not isinstance(herkunft, str) or herkunft not in HERKUNFT:
                fehler.append(f"{pfad}: unbekannte Herkunft {herkunft!r}")
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


def _parameterwert(knoten: object, pfad: str, fehler: list[str]) -> object:
    if not isinstance(knoten, dict) or "herkunft" not in knoten:
        fehler.append(f"{pfad}: Parameter mit 'wert', 'herkunft' und 'beleg' fehlt")
        return None
    # Die Strukturprüfung hat sichergestellt, dass nur dokumentierte Lücken null sind.
    return knoten["wert"]


def _ganzzahl(
    knoten: object, pfad: str, fehler: list[str], *, mindestens: int = 0
) -> int | None:
    zahl = _parameterwert(knoten, pfad, fehler)
    if zahl is None:
        return None
    if type(zahl) is not int or zahl < mindestens:
        bereich = "positive" if mindestens == 1 else "nichtnegative"
        fehler.append(f"{pfad}: erwartet eine {bereich} ganze Zahl, erhalten {zahl!r}")
        return None
    return zahl


def _pruefe_dauer(knoten: object, pfad: str, fehler: list[str]) -> None:
    dauer = _parameterwert(knoten, pfad, fehler)
    if dauer is None:
        return
    if not (
        (type(dauer) is int and dauer >= 0)
        or (type(dauer) is float and isfinite(dauer) and dauer >= 0)
    ):
        fehler.append(f"{pfad}: Dauer muss eine endliche, nichtnegative Zahl sein, erhalten {dauer!r}")


def _pruefe_dauern(knoten: dict[Any, Any], pfad: str, fehler: list[str]) -> None:
    for name, kind in knoten.items():
        kindpfad = f"{pfad}.{name}"
        if name == "montagezeit_s":
            if not isinstance(kind, dict) or "herkunft" in kind:
                fehler.append(f"{kindpfad}: erwartet Dauern je Teilenummer")
            else:
                for pno, dauer in kind.items():
                    _pruefe_dauer(dauer, f"{kindpfad}.{pno}", fehler)
        elif isinstance(name, str) and name.endswith("_s"):
            _pruefe_dauer(kind, kindpfad, fehler)
        elif isinstance(kind, dict) and "herkunft" not in kind:
            _pruefe_dauern(kind, kindpfad, fehler)


def _pruefe_fachwerte(daten: dict[str, Any], fehler: list[str]) -> None:
    boxpositionen = _ganzzahl(daten["box"].get("positionen"), "box.positionen", fehler, mindestens=1)
    for abschnitt, namen in _ANZAHLEN.items():
        for name in namen:
            _ganzzahl(daten[abschnitt].get(name), f"{abschnitt}.{name}", fehler)

    for name in ("anfangsbestand", "bestand_ohne_ort"):
        pfad = f"materiallager.{name}"
        bestand = daten["materiallager"].get(name, {} if name == "bestand_ohne_ort" else None)
        if not isinstance(bestand, dict) or "herkunft" in bestand:
            fehler.append(f"{pfad}: erwartet Bestandsmengen je Teilenummer")
        else:
            for pno, menge in bestand.items():
                _ganzzahl(menge, f"{pfad}.{pno}", fehler)

    max_saetze = daten["beladung"].get("max_saetze_je_box")
    if not isinstance(max_saetze, dict) or "herkunft" in max_saetze:
        fehler.append("beladung.max_saetze_je_box: erwartet eine Höchstzahl je Station")
    else:
        for name in max_saetze.keys() - daten["stationen"].keys():
            fehler.append(f"beladung.max_saetze_je_box.{name}: unbekannte Station")

    for name, station in daten["stationen"].items():
        if not isinstance(station, dict) or "herkunft" in station:
            fehler.append(f"stationen.{name}: erwartet eine Stationsbeschreibung")
            continue
        obergrenze = (
            _ganzzahl(max_saetze.get(name), f"beladung.max_saetze_je_box.{name}", fehler)
            if isinstance(max_saetze, dict) and "herkunft" not in max_saetze
            else None
        )
        _pruefe_station(name, station, daten["teile"], boxpositionen, obergrenze, fehler)

    _pruefe_dauern(daten, "anlage", fehler)


def _pruefe_station(
    name: str,
    station: dict[str, Any],
    bekannte_teile: dict[int, Any],
    boxpositionen: int | None,
    obergrenze: int | None,
    fehler: list[str],
) -> None:
    pfad = f"stationen.{name}"
    _ganzzahl(station.get("uebergabeplaetze"), f"{pfad}.uebergabeplaetze", fehler)
    erlaubt = _parameterwert(station.get("zulaessige_teile"), f"{pfad}.zulaessige_teile", fehler)
    if erlaubt is not None and (
        not isinstance(erlaubt, list) or any(type(pno) is not int or pno <= 0 for pno in erlaubt)
    ):
        fehler.append(f"{pfad}.zulaessige_teile: erwartet eine Liste gültiger Teilenummern")
        erlaubt = None

    satz = station.get("materialsatz")
    if not isinstance(satz, dict) or not satz or "herkunft" in satz:
        fehler.append(f"{pfad}.materialsatz: erwartet mindestens eine Komponentenmenge")
        return
    mengen: list[int] = []
    for pno, knoten in satz.items():
        komponentenpfad = f"{pfad}.materialsatz.{pno}"
        if type(pno) is not int or pno not in bekannte_teile:
            fehler.append(f"{komponentenpfad}: Teil {pno!r} nicht unter 'teile'")
        elif isinstance(erlaubt, list) and pno not in erlaubt:
            fehler.append(f"{komponentenpfad}: Teil {pno} ist für {name} nicht zulässig")
        menge = _ganzzahl(knoten, komponentenpfad, fehler, mindestens=1)
        if menge is not None:
            mengen.append(menge)

    if boxpositionen is None or len(mengen) != len(satz):
        return
    satzgroesse = sum(mengen)
    if satzgroesse > boxpositionen:
        fehler.append(
            f"{pfad}.materialsatz: ein Satz benötigt {satzgroesse} Positionen, "
            f"box.positionen bietet nur {boxpositionen}"
        )
    elif obergrenze is not None and obergrenze * satzgroesse > boxpositionen:
        fehler.append(
            f"beladung.max_saetze_je_box.{name}: {obergrenze} Sätze × {satzgroesse} Positionen "
            f"überschreiten box.positionen ({boxpositionen})"
        )


def lade_anlage(pfad: Path = ANLAGE) -> dict[str, Any]:
    """Lädt S1 und prüft Struktur, Herkunft, Mengen, Dauern und Satz-/Boxregeln."""
    return pruefe_anlage(yaml.safe_load(pfad.read_text(encoding="utf-8")))


def pruefe_anlage(daten: Any) -> dict[str, Any]:
    """Prüft eine eingelesene Anlagenbeschreibung wie :func:`lade_anlage` und gibt sie zurück.

    Getrennt vom Laden, damit auch eine im Speicher geänderte Anlage (Szenario-Abweichungen,
    :func:`mit_abweichungen`) dieselbe Prüfung durchläuft.
    """
    if not isinstance(daten, dict):
        raise AnlagenFehler("anlage: erwartet eine Zuordnung von Konfigurationsabschnitten")
    fehler: list[str] = []
    if daten.get("schema_version") != SCHEMA_VERSION:
        fehler.append(f"schema_version muss {SCHEMA_VERSION} sein")
    for abschnitt in PFLICHTABSCHNITTE:
        if abschnitt not in daten:
            fehler.append(f"Abschnitt '{abschnitt}' fehlt")
        elif not isinstance(daten[abschnitt], dict) or "herkunft" in daten[abschnitt]:
            fehler.append(f"{abschnitt}: erwartet einen Konfigurationsabschnitt")
    _pruefe_parameter(daten, "anlage", fehler)
    if not fehler:
        _pruefe_fachwerte(daten, fehler)
    if fehler:
        raise AnlagenFehler("\n".join(fehler))
    return daten


def mit_abweichungen(
    daten: dict[str, Any], abweichungen: dict[str, Any], quelle: str
) -> dict[str, Any]:
    """Kopie der Anlage mit den Abweichungen eines Szenarios (``anlage_abweichungen``).

    ``abweichungen`` ordnet Punktpfaden neue Werte zu, z. B. ``{"box.transportboxen_frei": 3}``.
    Jeder geänderte Parameter bekommt ``herkunft: annahme`` und das Szenario als Beleg. Die Kopie
    wird vollständig neu geprüft; die übergebene Anlage bleibt unverändert. Ohne Abweichungen
    kommt die Anlage selbst zurück.
    """
    if not abweichungen:
        return daten
    kopie = copy.deepcopy(daten)
    for pfad, neuer_wert in abweichungen.items():
        knoten: Any = kopie
        for teil in pfad.split("."):
            if not isinstance(knoten, dict):
                knoten = None
                break
            # Teilenummern sind in YAML ganzzahlige Schlüssel (wie in ``wert``).
            schluessel = int(teil) if teil.isdigit() and int(teil) in knoten else teil
            knoten = knoten.get(schluessel)
        if not isinstance(knoten, dict) or "herkunft" not in knoten:
            raise AnlagenFehler(f"Szenario {quelle}: {pfad} ist kein Parameter der Anlage")
        knoten.update(wert=neuer_wert, herkunft="annahme", beleg=f"Szenario {quelle}")
    return pruefe_anlage(kopie)


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
