"""Fachobjekte des Modells (docs/projekt/logikstruktur.md, Abschnitt 2).

Zeiten sind Sekunden seit Simulationsbeginn. Teile werden über ihre MES-Teilenummer (PNo)
bezeichnet, Stationen über ihren Schlüssel in ``config/anlage.yaml`` (z. B. ``"RASS1"``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BoxZustand(StrEnum):
    FREI = "frei"
    IN_KOMMISSIONIERUNG = "in_kommissionierung"
    UNTERWEGS = "unterwegs"
    AN_STATION = "an_station"
    LEER_ZURUECK = "leer_zurueck"


class ReservierungsArt(StrEnum):
    BESTAND = "bestand"
    BOX = "box"
    KOMMISSIONIERPLATZ = "kommissionierplatz"
    FAHRZEUG = "fahrzeug"
    UEBERGABEPLATZ = "uebergabeplatz"


@dataclass(frozen=True)
class Materialsatz:
    """Gemeinsam bereitzustellende Komponenten eines Montagevorgangs.

    Ein Satz ist nur vollständig lieferbar und bleibt seiner Anforderung zugeordnet.
    ``komponenten`` enthält Paare ``(PNo, Stückzahl)``.
    """

    anforderung_id: str
    station: str
    komponenten: tuple[tuple[int, int], ...]

    @property
    def positionen(self) -> int:
        """Benötigte Boxpositionen (ein Teil je Position)."""
        return sum(menge for _, menge in self.komponenten)


@dataclass(frozen=True)
class Anforderung:
    """Materialbedarf einer Auftragsposition an einer Station; erzeugt genau einen Materialsatz."""

    id: str
    station: str
    auftrag: int
    position: int
    eingang_s: float
    bedarfszeitpunkt_s: float
    satz: Materialsatz


@dataclass(frozen=True)
class Boxplatz:
    """Belegung einer Boxposition. ``pno = 0`` bedeutet leer; reserviert und leer ist möglich."""

    position: int
    pno: int = 0
    anforderung_id: str | None = None


@dataclass
class Box:
    id: int
    positionen: int
    zustand: BoxZustand = BoxZustand.FREI
    plaetze: list[Boxplatz] = field(default_factory=list)


@dataclass(frozen=True)
class Charge:
    """Vollständige Sätze in genau einer Box für genau eine Station.

    Nach der Bindung (``gebunden_s`` gesetzt) wird eine Charge nicht mehr umgeplant.
    """

    id: str
    station: str
    box_id: int
    saetze: tuple[Materialsatz, ...]
    versand_fruehestens_s: float
    gebunden_s: float | None = None

    @property
    def positionen(self) -> int:
        return sum(satz.positionen for satz in self.saetze)


@dataclass(frozen=True)
class Reservierung:
    """Bindet Bestand oder einen Platz an eine Anforderung. Erhöht den Bestand nie."""

    art: ReservierungsArt
    objekt: str
    anforderung_id: str
    menge: int = 1


@dataclass(frozen=True)
class Produktauftrag:
    """Ein Eintrag im vorab erzeugten Bedarfsverlauf (Schnittstelle Runner → Simulation).

    ``eingang_s``: Bedarfseingang, die Anforderungen für RASS1 bis RASS3 entstehen.
    ``freigabe_s``: Auftragsfreigabe, das Werkstück wird ausgelagert. Bis AP5 den Zeitpunkt des
    Bedarfseingangs festlegt (versuchsplan.md, Punkt 2), gilt ``freigabe_s = eingang_s``.
    """

    nr: int
    eingang_s: float
    freigabe_s: float


@dataclass
class Werkstueck:
    """Ein Produkt durchläuft die Montagefolge; nur beendete Montagen zählen als Fortschritt."""

    produktauftrag: Produktauftrag
    abgeschlossene_stationen: int = 0

    @property
    def id(self) -> str:
        return f"W{self.produktauftrag.nr:03d}"
