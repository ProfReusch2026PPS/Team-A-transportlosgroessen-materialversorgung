"""Zentrale Pfade des Repos (relativ zur Repo-Wurzel)."""

from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
ROH_SNAPSHOTS = WURZEL / "data" / "raw" / "mes_snapshots"
INTERIM = WURZEL / "data" / "interim"
PROCESSED = WURZEL / "data" / "processed"
ANLAGE = WURZEL / "config" / "anlage.yaml"
SZENARIEN = WURZEL / "config" / "szenarien"
ERGEBNISSE = WURZEL / "results"
