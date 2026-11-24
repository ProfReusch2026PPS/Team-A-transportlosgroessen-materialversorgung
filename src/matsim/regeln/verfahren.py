"""Planungsverfahren V0 bis V4 (AP4).

Stand: V0 und V1 umgesetzt; V2, V3 und V4 sind Gerüst.
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


#: Schlüssel in ``Planungszustand.zusatz``: Anzahl gebundener Chargen, deren Box noch nicht am
#: Übergabeplatz abgeliefert ist (vom Ereignis ``charge_gebunden`` bis ``lieferung``).
#: Dokumentiert in docs/projekt/logikstruktur.md, Abschnitt 4. Wird nur von V0 gelesen.
CHARGEN_IN_VERSORGUNG = "chargen_in_versorgung"


def _chargen_in_versorgung(zustand: Planungszustand) -> int:
    """Liest die Zahl der noch nicht abgelieferten Chargen; fehlt der Wert, ist das ein Fehler.

    Ohne diese Angabe kann V0 das beobachtete Nacheinander nicht einhalten. Ein stiller
    Ersatzwert würde einen anderen Ablauf als den beobachteten vortäuschen.
    """
    if CHARGEN_IN_VERSORGUNG not in zustand.zusatz:
        raise ValueError(
            f"V0 braucht zusatz[{CHARGEN_IN_VERSORGUNG!r}] im Planungszustand "
            "(siehe docs/projekt/logikstruktur.md, Abschnitt 4)"
        )
    wert = zustand.zusatz[CHARGEN_IN_VERSORGUNG]
    if isinstance(wert, bool) or not isinstance(wert, int) or wert < 0:
        raise ValueError(f"zusatz[{CHARGEN_IN_VERSORGUNG!r}] muss eine Zahl >= 0 sein: {wert!r}")
    return wert


class V0Referenz(Planungsverfahren):
    """Beobachtetes MES-Verhalten zur Validierung gegen den Ablauf vom 09.11.2026 (B-08).

    Ein Kommissionierauftrag je Station, alle offenen Sätze der Station in einer Box, Stationen
    nacheinander (nächster Auftrag erst nach Ablieferung der vorherigen Box).

    Regel je Planungsaufruf:

    1. Ist noch eine gebundene Charge nicht abgeliefert
       (``zusatz["chargen_in_versorgung"] > 0``) oder ist keine Box frei, wird gewartet.
    2. Sonst werden die Stationen in fester Folge zyklisch durchsucht, beginnend bei der
       Station nach der zuletzt bedienten (Start: erste Station der Folge). Bedient wird die
       erste Station mit mindestens einem versorgbaren Satz; Stationen ohne versorgbaren Satz
       werden übersprungen.
    3. Die Box dieser Station wird mit ihren offenen Sätzen in Eingangsfolge gefüllt
       (Gleichstand: kleinere Identität), solange Boxpositionen und freier Bestand den jeweils
       vollständigen Satz decken. Ein Satz ohne ausreichenden Bestand wird übersprungen.
    4. Passen nicht alle Sätze in die Box, bleibt der Rest offen und wird in der nächsten Runde
       des Zyklus versorgt (Annahme A-09; der beobachtete Ablauf zeigt keine Aufträge mit mehr
       als 8 Positionen, B-15).
    5. Je Aufruf entsteht höchstens eine Charge, mit sofortigem Versand.

    Sätze, die für sich allein keine zulässige Charge bilden können, werden wie bei V1 nie
    gebunden. Der Anlass ändert die Regel nicht.

    Parameter: ``stationsfolge`` (optional, Folge der Stationsschlüssel). Ohne Angabe gilt die
    alphabetische Folge der Stationen in ``zulaessige_teile``, also RASS1, RASS2, RASS3 wie
    am 09.11.2026.

    V0 merkt sich die zuletzt bediente Station. Deshalb gilt: eine Instanz je Simulationslauf
    (``erzeuge`` liefert jeweils eine neue).
    """

    name = "V0"

    def __init__(self, **parameter) -> None:
        super().__init__(**parameter)
        folge = parameter.get("stationsfolge")
        if folge is not None:
            folge = tuple(folge)
            if not folge or len(set(folge)) != len(folge):
                raise ValueError(f"stationsfolge muss Stationen ohne Wiederholung nennen: {folge}")
        self._stationsfolge: tuple[str, ...] | None = folge
        self._zuletzt_bedient: str | None = None

    def _folge(self, zustand: Planungszustand) -> tuple[str, ...]:
        if self._stationsfolge is not None:
            return self._stationsfolge
        return tuple(sorted(zustand.zulaessige_teile))

    def _reihum(self, zustand: Planungszustand) -> list[str]:
        """Stationsfolge, beginnend bei der Station nach der zuletzt bedienten."""
        folge = list(self._folge(zustand))
        if self._zuletzt_bedient in folge:
            start = folge.index(self._zuletzt_bedient) + 1
            folge = folge[start:] + folge[:start]
        return folge

    def _fuelle_box(
        self, station: str, offene: list[Anforderung], zustand: Planungszustand
    ) -> tuple[str, ...]:
        """Sätze der Station in Eingangsfolge, solange Positionen und Bestand reichen."""
        bestand = dict(zustand.freier_bestand)
        frei = zustand.box_positionen
        gewaehlt: list[str] = []
        for anforderung in offene:
            if anforderung.station != station or not _satz_zulaessig(anforderung, zustand):
                continue
            if anforderung.satz.positionen > frei or not _bestand_reicht(anforderung, bestand):
                continue
            _bestand_abziehen(anforderung, bestand)
            frei -= anforderung.satz.positionen
            gewaehlt.append(anforderung.id)
        return tuple(gewaehlt)

    def entscheide(self, zustand: Planungszustand, anlass: Anlass) -> list[Chargenentscheidung]:
        if _chargen_in_versorgung(zustand) > 0 or zustand.freie_boxen <= 0:
            return []
        offene = _in_eingangsfolge(zustand.offene_anforderungen)
        for station in self._reihum(zustand):
            saetze = self._fuelle_box(station, offene, zustand)
            if saetze:
                self._zuletzt_bedient = station
                return [Chargenentscheidung(station, saetze, zustand.zeit_s)]
        return []

    def naechste_wartefrist(self, zustand: Planungszustand) -> float | None:
        """V0 wartet nie bewusst auf eine Frist.

        Bleibt ein Satz offen, wartet V0 auf die Ablieferung der laufenden Charge, auf eine Box
        oder auf Bestand. Die Ablieferung gibt das Fahrzeug frei und löst damit den Anlass
        „Kapazität frei“ aus; eine frei werdende Box ebenso. Eine Frist würde nichts ändern.
        """
        return None


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
