"""Gemeinsame Schnittstelle aller Planungsverfahren (Schnittstelle AP3 ↔ AP4).

Ein Verfahren entscheidet ausschließlich über

* Anzahl und Kombination vollständiger Materialsätze je Box und
* den frühesten Bereitstellungs- bzw. Versandzeitpunkt der Charge.

Alles andere (Montagepriorität, Auftragsfreigabe, Fahrzeugzuordnung, Leerboxrückführung,
Übergaberegel) liegt in ``matsim.referenz`` und ist in allen Vergleichsläufen identisch.
Ein Verfahren verändert den Zustand nicht und sieht nur den zum Anlass bekannten Zustand.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from matsim.modell.typen import Anforderung


class Planungsanlass(StrEnum):
    """Die einzigen zulässigen Auslöser einer Neuplanung."""

    BEDARFSEINGANG = "bedarfseingang"
    WARTEFRIST_ABGELAUFEN = "wartefrist_abgelaufen"
    KAPAZITAET_FREI = "kapazitaet_frei"


@dataclass(frozen=True)
class Anlass:
    art: Planungsanlass
    zeit_s: float
    #: z. B. Anforderungs-ID, oder freigewordene Kapazität ("box", "kommissionierplatz", ...)
    detail: str = ""


@dataclass(frozen=True)
class Planungszustand:
    """Zum Planungsanlass bekannter Zustand. Enthält keine gebundenen Chargen zum Umplanen."""

    zeit_s: float
    #: Anforderungen, deren Satz noch keiner gebundenen Charge zugeordnet ist.
    offene_anforderungen: tuple[Anforderung, ...]
    #: Freier, nicht reservierter Lagerbestand je Teilenummer.
    freier_bestand: Mapping[int, int]
    freie_boxen: int
    freie_kommissionierplaetze: int
    freie_fahrzeuge: int
    #: Freie Übergabeplätze je Station.
    freie_uebergabeplaetze: Mapping[str, int]
    box_positionen: int
    #: Zulässige Teilenummern je Station (Gruppenregel des Materialpfads).
    zulaessige_teile: Mapping[str, frozenset[int]]
    #: Weitere, vom Verfahren lesbare Größen (z. B. erwartete Werkstückankünfte), dokumentiert
    #: in docs/projekt/logikstruktur.md, sobald AP3 und AP4 sie vereinbaren.
    zusatz: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chargenentscheidung:
    """Eine zu bildende Charge: vollständige Sätze einer Station für eine Box."""

    station: str
    anforderung_ids: tuple[str, ...]
    #: Frühester Bereitstellungs-/Versandzeitpunkt; ``zustand.zeit_s`` bedeutet sofort.
    versand_fruehestens_s: float


class Planungsverfahren(ABC):
    """Basisklasse der Verfahren V0 bis V4."""

    #: Kurzname, z. B. "V1"; wird in Szenario-Dateien und im Ergebnis verwendet.
    name: str

    def __init__(self, **parameter: Any) -> None:
        self.parameter = parameter

    @abstractmethod
    def entscheide(self, zustand: Planungszustand, anlass: Anlass) -> list[Chargenentscheidung]:
        """Liefert die jetzt zu bindenden Chargen. Eine leere Liste bedeutet: weiter warten.

        Jede zurückgegebene Charge muss mit ``zustand`` zulässig sein (Bestand, Boxkapazität,
        zulässige Inhalte, vollständige Sätze). Die Simulation prüft das unabhängig.
        """

    @abstractmethod
    def naechste_wartefrist(self, zustand: Planungszustand) -> float | None:
        """Zeitpunkt, zu dem das Verfahren spätestens erneut aufgerufen werden will.

        ``None`` bedeutet: keine Frist. Damit wird sichergestellt, dass Restbedarf auch dann
        bearbeitet wird, wenn eine Füllschwelle nicht erreicht wird.
        """
