"""Planungsverfahren V0 bis V4 (AP4). Gerüst: Schnittstelle und Parameter, keine Logik.

Steckbriefe und Begründungen: docs/projekt/planungsverfahren.md.
"""

from __future__ import annotations

from matsim.regeln.basis import Anlass, Chargenentscheidung, Planungsverfahren, Planungszustand


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
    """Jeder vollständige Satz frühestmöglich in eigener Box."""

    name = "V1"

    def entscheide(self, zustand: Planungszustand, anlass: Anlass) -> list[Chargenentscheidung]:
        raise NotImplementedError("AP4: V1 Einzelversorgung")

    def naechste_wartefrist(self, zustand: Planungszustand) -> float | None:
        raise NotImplementedError("AP4: V1 Einzelversorgung")


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
