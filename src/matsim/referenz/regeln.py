"""Feste Referenzregeln (AP3). In allen Vergleichsläufen identisch, nie Teil des Verfahrens.

Die Aufgabenstellung verweist für diese Regeln auf ein Referenzpaket, das im Repo noch fehlt
(projekt/annahmen-und-datenluecken.md, L-01). Die Produktionsregeln sind dokumentierte
Übergangsregeln, keine bestätigten Anlagenregeln.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import isfinite
from typing import Any

from matsim.modell.typen import Anforderung, Produktauftrag


def montageprioritaet(anforderung: Anforderung) -> tuple[float, int, int]:
    """Sortierschlüssel der bereits wartenden Positionen nach A-15 (kleiner zuerst)."""
    return anforderung.bedarfszeitpunkt_s, anforderung.auftrag, anforderung.position


def auftragsfreigabe(auftrag: Produktauftrag) -> float:
    """A-16: Freigabe aus dem gemeinsamen Verlauf übernehmen, nicht neu disponieren."""
    if not (0 <= auftrag.eingang_s <= auftrag.freigabe_s and isfinite(auftrag.freigabe_s)):
        raise ValueError(f"Auftrag {auftrag.nr}: ungültiger Eingang oder Freigabezeitpunkt")
    return auftrag.freigabe_s


def fahrzeugzuordnung(freie_fahrzeuge: Sequence[Any], transportauftrag: Any) -> Any:
    """Ordnet einem Transportauftrag ein freies Fahrzeug zu (feste Regel).

    Übergangsregel bis zum Referenzpaket: A-13, umgesetzt in ``Simulation.hintransport`` über
    das Fahrzeugregal (am längsten freies Fahrzeug, wartende Aufträge in ihrer Reihenfolge).
    """
    raise NotImplementedError("AP3: Fahrzeugzuordnung nach Referenzpaket")


def leerboxrueckfuehrung(station: str, box: Any) -> Any:
    """Legt fest, wann und wohin eine geleerte Box zurückgeführt wird (feste Regel).

    Übergangsregel bis zum Referenzpaket: A-14 (sofort, sobald ein Fahrzeug frei ist, ins
    Kistenlager), umgesetzt in ``Simulation.leerboxrueckfuehrung``.
    """
    raise NotImplementedError("AP3: Leerboxrückführung nach Referenzpaket")


def uebergabe_bei_vollem_zielpuffer(station: str, charge: Any) -> Any:
    """Warte- und Übergaberegel, wenn kein Übergabeplatz der Zielstation frei ist.

    MES-Beleg: OpNo 215 sucht einen freien Pufferplatz der Station (``PNo = 0``); eine
    Ausweichregel ist in den Daten nicht hinterlegt.

    Übergangsregel bis zum Referenzpaket: A-12 (erst Übergabeplatz, dann Fahrzeug), umgesetzt in
    ``Simulation.hintransport``.
    """
    raise NotImplementedError("AP3: Warte- und Übergaberegel nach Referenzpaket")


def weiterfahrt_bei_materialmangel(weiterfahrt: bool, umlaufzeit_s: float) -> float:
    """A-01/A-10: erneute Chance an derselben Station nach einem ganzen Umlauf."""
    if weiterfahrt is not True:
        raise ValueError("Keine Referenzregel ohne Weiterfahrt bei Materialmangel vereinbart")
    if not isfinite(umlaufzeit_s) or umlaufzeit_s <= 0:
        raise ValueError("Die Umlaufzeit bis zur Wiederkehr muss endlich und positiv sein")
    return umlaufzeit_s
