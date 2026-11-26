"""Feste Referenzregeln (AP3). In allen Vergleichsläufen identisch, nie Teil des Verfahrens.

Die Aufgabenstellung verweist für diese Regeln auf ein Referenzpaket, das im Repo noch fehlt
(docs/projekt/annahmen-und-datenluecken.md, L-01). Bis dahin stehen hier nur die Signaturen
und die Belege, die aus den MES-Daten ableitbar sind.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def montageprioritaet(wartende_positionen: Sequence[Any]) -> Any:
    """Wählt die nächste Auftragsposition einer Station.

    MES-Beleg: ``tblsqlquery`` 100/1 ``GetOpForRsc`` sortiert nach
    ``PlannedStart, ONo, OPos``; bearbeitet wird nur, wenn das Werkstück an der Station ist.
    """
    raise NotImplementedError("AP3: Montagepriorität nach Referenzpaket")


def auftragsfreigabe(zeit_s: float, wartende_auftraege: Sequence[Any]) -> Sequence[Any]:
    """Gibt Produktionsaufträge frei (feste Regel, nicht Gegenstand von Team A)."""
    raise NotImplementedError("AP3: Auftragsfreigabe nach Referenzpaket")


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


def weiterfahrt_bei_materialmangel(station: str, werkstueck: Any) -> Any:
    """Anlagenlogik für ein Werkstück, das ohne vollständigen Satz an der Station ankommt.

    Beleg Aufgabenstellung (Team C): "Fehlt Material, fährt das Werkstück weiter". Die
    Wiederkehrregel (wann eine erneute Bearbeitung möglich wird) legt das Referenzpaket fest.
    """
    raise NotImplementedError("AP3: Weiterfahr- und Wiederkehrregel nach Referenzpaket")
