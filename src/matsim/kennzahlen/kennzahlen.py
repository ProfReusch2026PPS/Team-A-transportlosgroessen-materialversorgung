"""Kennzahlen aus dem Ereignisprotokoll (AP5). Gerüst; Definitionen: docs/projekt/kennzahlen.md."""

from __future__ import annotations

from collections.abc import Sequence

from matsim.kennzahlen.ereignisprotokoll import Ereignis, Warteursache


def transportzahl(protokoll: Sequence[Ereignis]) -> int:
    """K1: Anzahl der Hintransporte (Leerboxrückführungen werden getrennt gezählt)."""
    raise NotImplementedError("AP5")


def fahrzeugbelegungszeit_s(protokoll: Sequence[Ereignis]) -> float:
    """K2: Summe der Zeiten, in denen Fahrzeuge an einen Transportauftrag gebunden sind."""
    raise NotImplementedError("AP5")


def boxauslastung(protokoll: Sequence[Ereignis], box_positionen: int) -> float:
    """K3: mittlerer Anteil belegter Boxpositionen je Hintransport."""
    raise NotImplementedError("AP5")


def zeit_bis_materialbereitstellung_s(protokoll: Sequence[Ereignis]) -> dict[str, float]:
    """K4: je Anforderung die Zeit vom Bedarfseingang bis zur Lieferung am Übergabeplatz."""
    raise NotImplementedError("AP5")


def materialbedingte_montageverzoegerung_s(protokoll: Sequence[Ereignis]) -> dict[str, float]:
    """K5: je Anforderung die Verzögerung des Montagebeginns, die auf fehlendes Material entfällt."""
    raise NotImplementedError("AP5")


def offener_restbedarf(protokoll: Sequence[Ereignis]) -> dict[str, str]:
    """K6: am Laufende nicht gelieferte Anforderungen mit ihrem letzten Zustand."""
    raise NotImplementedError("AP5")


def wartezeit_zerlegung_s(protokoll: Sequence[Ereignis]) -> dict[str, dict[Warteursache, float]]:
    """K7: je Anforderung die Wartezeit je Ursache; die Summe ergibt die gesamte Wartezeit."""
    raise NotImplementedError("AP5")


def verpasste_bearbeitungsmoeglichkeiten(protokoll: Sequence[Ereignis]) -> dict[str, int]:
    """K8: je Station die Zahl der Werkstückankünfte, bei denen der Satz fehlte."""
    raise NotImplementedError("AP5")


def stationsstillstand_s(protokoll: Sequence[Ereignis]) -> dict[str, float]:
    """K9: je Station die Zeit ohne Arbeit; getrennt von K8 auszuweisen."""
    raise NotImplementedError("AP5")
