"""Planungsverfahren V0 bis V4 (AP4).

Stand: V1 umgesetzt; V0, V2, V3 und V4 sind Gerüst.
Steckbriefe und Begründungen: docs/projekt/planungsverfahren.md.
"""

from __future__ import annotations

from collections.abc import Mapping

from matsim.modell.typen import Anforderung
from matsim.regeln.basis import Anlass, Chargenentscheidung, Planungsverfahren, Planungszustand


def _in_eingangsfolge(anforderungen: tuple[Anforderung, ...]) -> list[Anforderung]:
    """Sortiert nach Eingangszeit; bei gleicher Zeit entscheidet die kleinere Identität.

    Die Gleichstandsregel folgt docs/projekt/logikstruktur.md, Abschnitt „Gleichzeitige
    Ereignisse“.
    """
    return sorted(anforderungen, key=lambda anforderung: (anforderung.eingang_s, anforderung.id))


def _satz_zulaessig(anforderung: Anforderung, zustand: Planungszustand) -> bool:
    """Prüft, ob der Satz für sich allein überhaupt eine zulässige Charge bilden kann.

    Dieselben Bedingungen wie ``pruefe_charge``: Satz passt in eine Box, alle Teile sind für
    die Station zulässig, jede Menge ist positiv.
    """
    satz = anforderung.satz
    erlaubt = zustand.zulaessige_teile.get(anforderung.station, frozenset())
    return (
        satz.station == anforderung.station
        and 0 < satz.positionen <= zustand.box_positionen
        and all(menge > 0 and pno in erlaubt for pno, menge in satz.komponenten)
    )


def _bestand_reicht(anforderung: Anforderung, bestand: Mapping[int, int]) -> bool:
    """Reicht der noch freie, nicht reservierte Bestand für den vollständigen Satz?"""
    return all(bestand.get(pno, 0) >= menge for pno, menge in anforderung.satz.komponenten)


def _bestand_abziehen(anforderung: Anforderung, bestand: dict[int, int]) -> None:
    """Zieht den Satz vom lokal mitgeführten Bestand ab (keine Doppelvergabe im selben Aufruf)."""
    for pno, menge in anforderung.satz.komponenten:
        bestand[pno] -= menge


class V0Referenz(Planungsverfahren):
    """Beobachtetes MES-Verhalten zur Validierung gegen den Ablauf vom 09.11.2026.

    Ein Kommissionierauftrag je Station, alle offenen Sätze der Station in einer Box, Stationen
    nacheinander (nächster Auftrag erst nach Ablieferung der vorherigen Box).
    """

    name = "V0"

    def entscheide(self, zustand: Planungszustand, anlass: Anlass) -> list[Chargenentscheidung]:
        raise NotImplementedError("AP4: V0 Referenz")

    def naechste_wartefrist(self, zustand: Planungszustand) -> float | None:
        raise NotImplementedError("AP4: V0 Referenz")


class V1Einzelversorgung(Planungsverfahren):
    """Jeder vollständige Satz frühestmöglich in eigener Box (Lot-for-Lot in Eingangsfolge).

    Regel je Planungsaufruf:

    1. Offene Anforderungen in Eingangsfolge durchgehen (Gleichstand: kleinere Identität).
    2. Je Satz genau eine Charge mit sofortigem Versand (``versand_fruehestens_s = zeit_s``),
       solange eine freie Box vorhanden ist und der freie Bestand den vollständigen Satz deckt.
    3. Reicht der Bestand für einen Satz nicht, wird er übersprungen; spätere Sätze, deren
       Bestand reicht, werden trotzdem versorgt (keine Blockade durch einen Fehlteilsatz).
    4. Sätze, die für sich allein keine zulässige Charge bilden können (zu groß für die Box,
       stationsfremde Teile), werden nie gebunden. Die Simulation weist sie als Restbedarf aus.

    Der Anlass ändert die Regel nicht: V1 bindet bei jedem Aufruf alles, was möglich ist.
    Kommissionierplatz, Fahrzeug und Übergabeplatz begrenzen V1 nicht; das Warten darauf
    bildet die Simulation ab (Warteursachen im Ereignisprotokoll). Parameter: keine.
    """

    name = "V1"

    def entscheide(self, zustand: Planungszustand, anlass: Anlass) -> list[Chargenentscheidung]:
        bestand = dict(zustand.freier_bestand)
        freie_boxen = zustand.freie_boxen
        chargen: list[Chargenentscheidung] = []
        for anforderung in _in_eingangsfolge(zustand.offene_anforderungen):
            if freie_boxen <= 0:
                break
            if not _satz_zulaessig(anforderung, zustand):
                continue
            if not _bestand_reicht(anforderung, bestand):
                continue
            _bestand_abziehen(anforderung, bestand)
            freie_boxen -= 1
            chargen.append(
                Chargenentscheidung(
                    station=anforderung.station,
                    anforderung_ids=(anforderung.id,),
                    versand_fruehestens_s=zustand.zeit_s,
                )
            )
        return chargen

    def naechste_wartefrist(self, zustand: Planungszustand) -> float | None:
        """V1 wartet nie bewusst. Bleibt ein Satz offen, fehlt eine Box oder Bestand.

        Eine frei werdende Box löst den Anlass „Kapazität frei“ aus; eine Frist würde
        nichts ändern.
        """
        return None


class V2Fuellschwelle(Planungsverfahren):
    """Bündelung vollständiger Sätze bis zu einer festgelegten Füllschwelle.

    Parameter: ``fuellschwelle_positionen`` (belegte Boxpositionen, ab denen versendet wird) und
    die Restbedarfsregel für nicht erreichte Schwellen (siehe planungsverfahren.md).
    """

    name = "V2"

    def entscheide(self, zustand: Planungszustand, anlass: Anlass) -> list[Chargenentscheidung]:
        raise NotImplementedError("AP4: V2 Füllschwelle")

    def naechste_wartefrist(self, zustand: Planungszustand) -> float | None:
        raise NotImplementedError("AP4: V2 Restbedarfsregel")


class V3WartezeitDringlichkeit(Planungsverfahren):
    """Bündelung mit maximaler Wartezeit oder produktionsbezogener Dringlichkeitsgrenze.

    Parameter: ``max_wartezeit_s`` oder ``dringlichkeit`` (aus dem Produktionsbedarf abgeleitet,
    keine frei gesetzten Dringlichkeitspunkte).
    """

    name = "V3"

    def entscheide(self, zustand: Planungszustand, anlass: Anlass) -> list[Chargenentscheidung]:
        raise NotImplementedError("AP4: V3 Wartezeit/Dringlichkeit")

    def naechste_wartefrist(self, zustand: Planungszustand) -> float | None:
        raise NotImplementedError("AP4: V3 Wartezeit/Dringlichkeit")


class V4EigeneVerbesserung(Planungsverfahren):
    """Eigene Verbesserung innerhalb von V2 oder V3. Kandidaten: planungsverfahren.md, Abschnitt V4.

    Die Auswahl trifft das Team.
    """

    name = "V4"

    def entscheide(self, zustand: Planungszustand, anlass: Anlass) -> list[Chargenentscheidung]:
        raise NotImplementedError("AP4: V4 nach Teamentscheidung")

    def naechste_wartefrist(self, zustand: Planungszustand) -> float | None:
        raise NotImplementedError("AP4: V4 nach Teamentscheidung")


VERFAHREN: dict[str, type[Planungsverfahren]] = {
    klasse.name: klasse
    for klasse in (
        V0Referenz,
        V1Einzelversorgung,
        V2Fuellschwelle,
        V3WartezeitDringlichkeit,
        V4EigeneVerbesserung,
    )
}


def erzeuge(name: str, **parameter) -> Planungsverfahren:
    """Erzeugt ein Verfahren über seinen Kurznamen aus der Szenario-Datei."""
    if name not in VERFAHREN:
        raise KeyError(f"Unbekanntes Verfahren {name!r}; bekannt: {sorted(VERFAHREN)}")
    return VERFAHREN[name](**parameter)
