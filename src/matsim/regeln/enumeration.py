"""Vollständige Enumeration der Chargenbildungen für einen kleinen Fall (AP4, Issue #13, R-49).

Für eine Entscheidungssituation (ein Planungszustand) werden alle zulässigen Aufteilungen der
offenen Sätze auf Boxen aufgezählt, mit einem einfachen Bewertungsmodell bewertet und mit den
Entscheidungen der Verfahren verglichen.

Entscheidungshorizont: genau diese eine Entscheidung. Alle offenen, versorgbaren Sätze werden
gebunden; künftige Bedarfe sind unbekannt. Ohne neue Bedarfe bringt Warten nur Verzögerung,
deshalb versenden die aufgezählten Alternativen sofort. Verfahren, die warten (V2, V3), werden
über ihre angemeldeten Wartefristen bis zur vollständigen Bindung weitergeführt
(``plan_des_verfahrens``).

Bewertungsmodell (Modellgrenze, keine Simulation):

* Der Kommissionierplatz bearbeitet eine Charge zur Zeit (A-04), in der Reihenfolge der
  Alternative bzw. der Bindung durch das Verfahren.
* Dauer einer Charge: ``vorlauf_s + Teile x pickzeit_je_teil_s
  + (Quellboxen - 1) x quellboxwechsel_s`` (Formel aus ``config/anlage.yaml``, A-11). Als Zahl
  der Quellboxen gilt die Zahl verschiedener Teilenummern der Charge (Annahme der Enumeration).
* Danach folgt der Hintransport mit ``hintransport_s`` (enthält Warten auf ein Fahrzeug, A-07).
  Fahrzeuge, Übergabeplätze, Montage und Leerboxrückführung sind nicht modelliert.

Zielgrößen: Zahl der Transporte (Boxen) sowie mittlere und größte Bereitstellungszeit der Sätze,
gemessen ab dem Entscheidungszeitpunkt. Eine optimale Einzelentscheidung beweist keinen insgesamt
optimalen Ablauf.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import permutations, product
from typing import Any

from matsim.kennzahlen.pruefung import pruefe_charge
from matsim.modell.typen import Anforderung, Charge
from matsim.regeln.basis import (
    Anlass,
    Chargenentscheidung,
    Planungsanlass,
    Planungsverfahren,
    Planungszustand,
)

#: Eine Alternative: Chargen in der Reihenfolge, in der sie kommissioniert werden.
Alternative = tuple[Chargenentscheidung, ...]


@dataclass(frozen=True)
class Zeitansaetze:
    """Zeitansätze des Bewertungsmodells in Sekunden."""

    vorlauf_s: float
    pickzeit_je_teil_s: float
    quellboxwechsel_s: float
    hintransport_s: float

    @classmethod
    def aus_anlage(cls, anlage: Mapping[str, Any]) -> Zeitansaetze:
        """Liest die Festwerte aus der geladenen ``config/anlage.yaml``."""
        platz = anlage["kommissionierplatz"]
        return cls(
            vorlauf_s=platz["vorlauf_s"]["wert"],
            pickzeit_je_teil_s=platz["pickzeit_je_teil_s"]["wert"],
            quellboxwechsel_s=platz["quellboxwechsel_s"]["wert"],
            hintransport_s=anlage["fahrzeuge"]["hintransport_s"]["wert"],
        )


@dataclass(frozen=True)
class Bewertung:
    """Ergebnis des Bewertungsmodells für eine Folge von Chargen."""

    transporte: int
    mittlere_bereitstellung_s: float
    max_bereitstellung_s: float
    #: Bereitstellungszeitpunkt je Anforderung (Lieferung an der Station).
    lieferung_s: Mapping[str, float]


def _set_partitionen(elemente: Sequence[Anforderung]) -> Iterator[list[list[Anforderung]]]:
    """Alle Mengenpartitionen in kanonischer Form (Reihenfolge der Blöcke nach erstem Element)."""
    if not elemente:
        yield []
        return
    erstes, rest = elemente[0], elemente[1:]
    for partition in _set_partitionen(rest):
        yield [[erstes], *partition]
        for i in range(len(partition)):
            yield [*partition[:i], [erstes, *partition[i]], *partition[i + 1 :]]


def _versorgbare(zustand: Planungszustand) -> list[Anforderung]:
    """Offene Sätze, die für sich allein eine zulässige Charge bilden können (wie V1)."""
    ergebnis = []
    for anforderung in sorted(zustand.offene_anforderungen, key=lambda a: (a.eingang_s, a.id)):
        charge = Charge("pruefung", anforderung.station, 0, (anforderung.satz,), zustand.zeit_s)
        if not pruefe_charge(charge, zustand.box_positionen, zustand.zulaessige_teile):
            ergebnis.append(anforderung)
    return ergebnis


def _bestand_reicht(saetze: Sequence[Anforderung], bestand: Mapping[int, int]) -> bool:
    bedarf: dict[int, int] = {}
    for anforderung in saetze:
        for pno, menge in anforderung.satz.komponenten:
            bedarf[pno] = bedarf.get(pno, 0) + menge
    return all(bestand.get(pno, 0) >= menge for pno, menge in bedarf.items())


def aufteilungen(zustand: Planungszustand) -> list[tuple[tuple[str, ...], ...]]:
    """Alle zulässigen Aufteilungen der versorgbaren Sätze auf Boxen, ohne Reihenfolge.

    Jede Box enthält nur Sätze einer Station und besteht ``pruefe_charge``; zusammen dürfen die
    Boxen den freien Bestand und die freien Boxen nicht überschreiten. Ist der Bestand für alle
    Sätze zu knapp, gibt es keine Alternative, die alle Sätze bindet (leere Liste).
    """
    saetze = _versorgbare(zustand)
    if not _bestand_reicht(saetze, zustand.freier_bestand):
        return []
    je_station: dict[str, list[Anforderung]] = {}
    for anforderung in saetze:
        je_station.setdefault(anforderung.station, []).append(anforderung)

    def zulaessig(station: str, block: list[Anforderung]) -> bool:
        charge = Charge("c", station, 0, tuple(a.satz for a in block), zustand.zeit_s)
        return not pruefe_charge(charge, zustand.box_positionen, zustand.zulaessige_teile)

    stationsweise = []
    for station, liste in sorted(je_station.items()):
        stationsweise.append(
            [
                [(station, tuple(a.id for a in block)) for block in partition]
                for partition in _set_partitionen(liste)
                if all(zulaessig(station, block) for block in partition)
            ]
        )
    ergebnis = []
    for kombination in product(*stationsweise):
        boxen = tuple(ids for teil in kombination for _, ids in teil)
        if len(boxen) <= zustand.freie_boxen:
            ergebnis.append(boxen)
    return ergebnis


def alternativen(zustand: Planungszustand) -> Iterator[Alternative]:
    """Alle zulässigen Aufteilungen in jeder Kommissionierreihenfolge, Versand sofort."""
    station = {a.id: a.station for a in zustand.offene_anforderungen}
    for boxen in aufteilungen(zustand):
        for folge in permutations(boxen):
            yield tuple(Chargenentscheidung(station[ids[0]], ids, zustand.zeit_s) for ids in folge)


def bewerte(
    folge: Sequence[Chargenentscheidung], zustand: Planungszustand, zeiten: Zeitansaetze
) -> Bewertung:
    """Bewertet Chargen in Kommissionierreihenfolge mit dem Modell aus dem Modulkopf.

    Eine Charge beginnt frühestens zu ihrem ``versand_fruehestens_s`` und erst, wenn der
    Kommissionierplatz frei ist.
    """
    if not folge:
        raise ValueError("Eine leere Folge von Chargen lässt sich nicht bewerten")
    nach_id = {a.id: a for a in zustand.offene_anforderungen}
    platz_frei = zustand.zeit_s
    lieferung: dict[str, float] = {}
    for charge in folge:
        saetze = [nach_id[i].satz for i in charge.anforderung_ids]
        teile = sum(satz.positionen for satz in saetze)
        quellboxen = len({pno for satz in saetze for pno, _ in satz.komponenten})
        dauer = (
            zeiten.vorlauf_s
            + teile * zeiten.pickzeit_je_teil_s
            + (quellboxen - 1) * zeiten.quellboxwechsel_s
        )
        beginn = max(platz_frei, charge.versand_fruehestens_s)
        platz_frei = beginn + dauer
        for anforderung_id in charge.anforderung_ids:
            lieferung[anforderung_id] = platz_frei + zeiten.hintransport_s
    zeiten_ab_entscheidung = [t - zustand.zeit_s for t in lieferung.values()]
    return Bewertung(
        transporte=len(folge),
        mittlere_bereitstellung_s=sum(zeiten_ab_entscheidung) / len(zeiten_ab_entscheidung),
        max_bereitstellung_s=max(zeiten_ab_entscheidung),
        lieferung_s=lieferung,
    )


def plan_des_verfahrens(
    verfahren: Planungsverfahren, zustand: Planungszustand, max_aufrufe: int = 100
) -> list[Chargenentscheidung]:
    """Führt ein Verfahren ohne neue Bedarfe weiter, bis alle versorgbaren Sätze gebunden sind.

    Erster Aufruf mit Anlass „Bedarfseingang“, danach jeweils zur angemeldeten Wartefrist.
    Gebundene Sätze, ihr Bestand und ihre Boxen sind danach nicht mehr frei (keine Rückführung
    im Entscheidungshorizont). V0 braucht den Simulationszustand ``chargen_in_versorgung`` und
    ist hier nicht vorgesehen.
    """
    offene = list(zustand.offene_anforderungen)
    bestand = dict(zustand.freier_bestand)
    boxen = zustand.freie_boxen
    zeit = zustand.zeit_s
    art = Planungsanlass.BEDARFSEINGANG
    plan: list[Chargenentscheidung] = []
    for _ in range(max_aufrufe):
        jetzt = _mit(zustand, zeit, offene, bestand, boxen)
        chargen = verfahren.entscheide(jetzt, Anlass(art, zeit))
        plan.extend(chargen)
        gebunden = {i for charge in chargen for i in charge.anforderung_ids}
        for anforderung in offene:
            if anforderung.id in gebunden:
                for pno, menge in anforderung.satz.komponenten:
                    bestand[pno] -= menge
        boxen -= len(chargen)
        offene = [a for a in offene if a.id not in gebunden]
        frist = verfahren.naechste_wartefrist(_mit(zustand, zeit, offene, bestand, boxen))
        if frist is None or not offene:
            return plan
        zeit, art = frist, Planungsanlass.WARTEFRIST_ABGELAUFEN
    raise RuntimeError(f"{verfahren.name} hat nach {max_aufrufe} Aufrufen noch offene Sätze")


def _mit(
    zustand: Planungszustand,
    zeit: float,
    offene: list[Anforderung],
    bestand: Mapping[int, int],
    boxen: int,
) -> Planungszustand:
    return Planungszustand(
        zeit_s=zeit,
        offene_anforderungen=tuple(offene),
        freier_bestand=dict(bestand),
        freie_boxen=boxen,
        freie_kommissionierplaetze=zustand.freie_kommissionierplaetze,
        freie_fahrzeuge=zustand.freie_fahrzeuge,
        freie_uebergabeplaetze=zustand.freie_uebergabeplaetze,
        box_positionen=zustand.box_positionen,
        zulaessige_teile=zustand.zulaessige_teile,
        zusatz=zustand.zusatz,
    )


def pareto_front(bewertungen: Sequence[Bewertung]) -> list[int]:
    """Indizes der nicht dominierten Bewertungen (weniger Transporte, kürzere Ø-Zeit)."""
    front = []
    for i, a in enumerate(bewertungen):
        dominiert = any(
            b.transporte <= a.transporte
            and b.mittlere_bereitstellung_s <= a.mittlere_bereitstellung_s
            and (
                b.transporte < a.transporte
                or b.mittlere_bereitstellung_s < a.mittlere_bereitstellung_s
            )
            for b in bewertungen
        )
        if not dominiert:
            front.append(i)
    return front
