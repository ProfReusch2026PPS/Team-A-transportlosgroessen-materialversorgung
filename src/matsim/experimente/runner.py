"""Szenario-Runner (AP5). Gerüst.

Jedes Verfahren läuft in jedem Szenario mit denselben Seeds und denselben vorab erzeugten
Eingangs- und Dauerverläufen. Zwischen den Läufen eines Vergleichs ändern sich nur das
Verfahren und die ausgewiesenen Parameter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from matsim.pfade import ERGEBNISSE


def erzeuge_verlaeufe(szenario: dict[str, Any], seed: int) -> dict[str, Any]:
    """Erzeugt Bedarfseingänge und Dauern eines Laufs vorab, unabhängig vom Verfahren."""
    raise NotImplementedError("AP5: gemeinsame Eingangs- und Dauerverläufe je Seed")


def ergebnisordner(szenario: str, verfahren: str, seed: int, wurzel: Path = ERGEBNISSE) -> Path:
    """Ablageort eines Laufs: ``results/<szenario>/<verfahren>/seed_<seed>/``."""
    return wurzel / szenario / verfahren / f"seed_{seed}"


def laufe_szenario(szenario: dict[str, Any], anlage: dict[str, Any]) -> None:
    """Führt alle Verfahren und Replikationen eines Szenarios aus und legt Protokolle ab."""
    raise NotImplementedError("AP5: Läufe ausführen, Protokolle und Kennzahlen ablegen")
