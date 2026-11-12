"""Unabhängige Prüfregeln (getrennt von Planung und Simulation aufrufbar).

Die Prüfung liest nur Fachobjekte bzw. das Ereignisprotokoll und kennt weder das
Planungsverfahren noch den Simulationscode. Verstöße werden gemeldet, nie repariert.

Bereits umgesetzt sind die beiden zustandslosen Regeln zu Satzvollständigkeit und
Chargenzulässigkeit. Die protokollbasierten Regeln sind Gerüst (AP5, Invarianten mit AP3).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from matsim.kennzahlen.ereignisprotokoll import Ereignis
from matsim.modell.typen import Boxplatz, Charge, Materialsatz


@dataclass(frozen=True)
class Verstoss:
    regel: str
    beschreibung: str


def satz_vollstaendig_in_box(satz: Materialsatz, plaetze: Iterable[Boxplatz]) -> bool:
    """Prüft, ob alle Komponenten des Satzes in derselben Box liegen und ihm zugeordnet sind.

    Teile ohne Zuordnung zur Anforderung des Satzes zählen nicht; getrennte Teillieferungen
    erfüllen den Bedarf nicht.
    """
    vorhanden = Counter(
        platz.pno
        for platz in plaetze
        if platz.pno != 0 and platz.anforderung_id == satz.anforderung_id
    )
    return all(vorhanden[pno] >= menge for pno, menge in satz.komponenten)


def pruefe_charge(
    charge: Charge, box_positionen: int, zulaessige_teile: Mapping[str, frozenset[int]]
) -> list[Verstoss]:
    """Prüft Boxkapazität, Stationsreinheit, zulässige Inhalte und eindeutige Zuordnung."""
    verstoesse: list[Verstoss] = []
    if not charge.saetze:
        verstoesse.append(Verstoss("charge_leer", f"{charge.id} enthält keinen Satz"))
    if charge.positionen > box_positionen:
        verstoesse.append(
            Verstoss(
                "boxkapazitaet",
                f"{charge.id}: {charge.positionen} Positionen bei {box_positionen} Boxpositionen",
            )
        )
    erlaubt = zulaessige_teile.get(charge.station, frozenset())
    for satz in charge.saetze:
        if satz.station != charge.station:
            verstoesse.append(
                Verstoss(
                    "stationsreinheit",
                    f"{charge.id}: Satz {satz.anforderung_id} gehört zu {satz.station}",
                )
            )
        for pno, menge in satz.komponenten:
            if menge <= 0:
                verstoesse.append(
                    Verstoss("stueckzahl", f"{satz.anforderung_id}: Menge {menge} für Teil {pno}")
                )
            if pno not in erlaubt:
                verstoesse.append(
                    Verstoss(
                        "zulaessiger_inhalt",
                        f"{charge.id}: Teil {pno} ist für {charge.station} nicht zulässig",
                    )
                )
    doppelt = [a for a, n in Counter(s.anforderung_id for s in charge.saetze).items() if n > 1]
    for anforderung_id in doppelt:
        verstoesse.append(
            Verstoss("zuordnung", f"{charge.id}: Anforderung {anforderung_id} mehrfach enthalten")
        )
    return verstoesse


def pruefe_mengenbilanz(
    protokoll: Sequence[Ereignis], anfangsbestand: Mapping[int, int]
) -> list[Verstoss]:
    """Je Teil und Zeitpunkt: frei + reserviert + in Boxen unterwegs + verbaut = Anfangsbestand."""
    raise NotImplementedError("AP5 mit AP3: Mengenbilanz aus dem Ereignisprotokoll")


def pruefe_doppelbindungen(protokoll: Sequence[Ereignis]) -> list[Verstoss]:
    """Fahrzeug, Box und Platz sind zu keinem Zeitpunkt doppelt belegt."""
    raise NotImplementedError("AP5 mit AP3: Doppelbindungen aus dem Ereignisprotokoll")


def pruefe_kapazitaeten(protokoll: Sequence[Ereignis], anlage: Mapping) -> list[Verstoss]:
    """Kommissionierplatz, Boxbestand, Fahrzeuge und Übergabeplätze werden nie überschritten."""
    raise NotImplementedError("AP5 mit AP3: Kapazitätsprüfung aus dem Ereignisprotokoll")


def pruefe_vorgaenger(protokoll: Sequence[Ereignis]) -> list[Verstoss]:
    """Reihenfolge je Satz: Reservierung vor Pick, Pick vor Transport, Lieferung vor Montage."""
    raise NotImplementedError("AP5 mit AP3: Vorgängerbeziehungen aus dem Ereignisprotokoll")


def pruefe_abschluss(protokoll: Sequence[Ereignis]) -> list[Verstoss]:
    """Jede Anforderung ist am Laufende geliefert oder als offener Restbedarf ausgewiesen."""
    raise NotImplementedError("AP5 mit AP3: Abschlussprüfung aus dem Ereignisprotokoll")
