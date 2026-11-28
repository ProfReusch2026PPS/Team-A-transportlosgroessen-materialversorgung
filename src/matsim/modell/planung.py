"""Prüfung der Planerantwort vor der Bindung (AP3). Hier wird kein Simulationszustand geändert."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from math import isfinite
from types import MappingProxyType
from typing import Any, TypeVar

from matsim.kennzahlen.pruefung import pruefe_charge
from matsim.modell.anlage import wert
from matsim.modell.typen import Box, BoxZustand, Charge
from matsim.regeln.basis import Chargenentscheidung, Planungszustand


class Planungsfehler(ValueError):
    """Das Verfahren hat eine unzulässige Bindung oder Wartefrist geliefert."""


K = TypeVar("K")
V = TypeVar("V")


def lesekopie(daten: Mapping[K, V]) -> Mapping[K, V]:
    """Ein Planer darf weder den Laufzustand noch die Prüfgrundlage seiner Antwort ändern."""
    return MappingProxyType(dict(daten))


def endliche_zeit(zeit: object) -> bool:
    return isinstance(zeit, int | float) and not isinstance(zeit, bool) and isfinite(zeit)


def bereite_chargen_vor(
    entscheidungen: list[Chargenentscheidung],
    zustand: Planungszustand,
    boxen: Sequence[Box],
    anlage: dict[str, Any],
    erste_nr: int,
) -> list[Charge]:
    """Ordnet Boxen nur probeweise zu. Erst wenn die ganze Liste passt, erhält AP3 die Chargen."""
    if not isinstance(entscheidungen, list):
        raise Planungsfehler("Das Verfahren muss eine Liste von Chargenentscheidungen liefern")
    if len(entscheidungen) > len(boxen):
        raise Planungsfehler(f"{len(entscheidungen)} Chargen, aber nur {len(boxen)} freie Boxen")

    offen = {a.id: a for a in zustand.offene_anforderungen}
    vergeben: set[str] = set()
    gesamt: Counter[int] = Counter()
    chargen: list[Charge] = []
    fehler: list[str] = []
    for i, entscheidung in enumerate(entscheidungen):
        kennung = f"C{erste_nr + i:03d}"
        if not isinstance(entscheidung, Chargenentscheidung):
            raise Planungsfehler(f"{kennung}: keine Chargenentscheidung")
        if (
            not isinstance(entscheidung.station, str)
            or not isinstance(entscheidung.anforderung_ids, tuple)
            or not all(isinstance(a, str) for a in entscheidung.anforderung_ids)
        ):
            raise Planungsfehler(
                f"{kennung}: Stationsschlüssel oder Anforderungskennungen ungültig"
            )
        station = entscheidung.station
        versand = entscheidung.versand_fruehestens_s
        if not endliche_zeit(versand) or versand < zustand.zeit_s:
            fehler.append(f"{kennung}: ungültiger Versandzeitpunkt {versand!r}")
        if station not in zustand.zulaessige_teile:
            fehler.append(f"{kennung}: unbekannte Station {station!r}")
        elif len(entscheidung.anforderung_ids) > wert(
            anlage, f"beladung.max_saetze_je_box.{station}"
        ):
            fehler.append(f"{kennung}: zu viele Sätze in einer Box für {station}")

        saetze = []
        auftraege = set()
        for anforderung_id in entscheidung.anforderung_ids:
            if anforderung_id in vergeben:
                fehler.append(f"{kennung}: Anforderung {anforderung_id} mehrfach vergeben")
            vergeben.add(anforderung_id)
            a = offen.get(anforderung_id)
            if a is None:
                fehler.append(f"{kennung}: Anforderung {anforderung_id} unbekannt oder nicht offen")
                continue
            if a.station != station or a.satz.anforderung_id != a.id or not a.satz.komponenten:
                fehler.append(
                    f"{kennung}: Satz von {a.id} passt nicht zur Anforderung oder Station"
                )
            saetze.append(a.satz)
            auftraege.add(a.auftrag)
            for pno, menge in a.satz.komponenten:
                gesamt[pno] += menge
        if len(auftraege) > 1 and not wert(
            anlage, "beladung.saetze_verschiedener_auftraege_in_einer_box"
        ):
            fehler.append(f"{kennung}: Sätze verschiedener Aufträge in derselben Box")

        box = boxen[i]
        if (
            box.zustand != BoxZustand.FREI
            or box.plaetze
            or box.positionen != zustand.box_positionen
        ):
            fehler.append(f"{kennung}: Box {box.id} im freien Regal ist nicht einsatzbereit")
        charge = Charge(kennung, station, box.id, tuple(saetze), versand, zustand.zeit_s)
        fehler.extend(
            v.beschreibung for v in pruefe_charge(charge, box.positionen, zustand.zulaessige_teile)
        )
        chargen.append(charge)

    # Zwei einzeln zulässige Boxen dürfen zusammen nicht dasselbe letzte Teil beanspruchen.
    for pno, menge in gesamt.items():
        frei = zustand.freier_bestand.get(pno, 0)
        if menge > frei:
            fehler.append(f"Teil {pno}: {menge} benötigt, nur {frei} frei")
    if fehler:
        raise Planungsfehler("; ".join(fehler))
    return chargen
