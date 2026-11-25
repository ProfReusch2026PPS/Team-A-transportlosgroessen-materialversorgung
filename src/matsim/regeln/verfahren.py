"""Planungsverfahren V0 bis V4 (AP4).

Stand: V0, V1 und V2 umgesetzt; V3 und V4 sind Gerüst.
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
    """Bündelung vollständiger Sätze einer Station bis zu einer festen Füllschwelle.

    Regel je Planungsaufruf:

    1. Ohne freie Box wird gewartet.
    2. Die Stationen werden in der Folge ihres ältesten offenen Satzes betrachtet
       (Eingangsfolge, Gleichstand: kleinere Identität).
    3. Je Station wird eine Box mit den offenen Sätzen in Eingangsfolge gefüllt, solange
       Boxpositionen und freier Bestand den jeweils vollständigen Satz decken. Ein Satz ohne
       ausreichenden Bestand oder ohne Platz in der Box wird übersprungen.
    4. Die Box wird als Charge mit sofortigem Versand gebunden, wenn
       a) die belegten Positionen die Füllschwelle der Station erreichen oder
       b) der älteste Satz der Box seit mindestens ``hoechstwartezeit_s`` offen ist
          (Restbedarfsregel).
       Sonst wartet die Station.
    5. Nach einer gebundenen Box wird dieselbe Station erneut geprüft, solange Boxen frei
       sind (bei mehr als einer Box Bedarf entstehen mehrere Chargen).

    Die Restbedarfsregel ist ein Sicherheitsnetz: Ohne sie bliebe ein Rest unterhalb der
    Schwelle liegen, sobald kein weiterer Bedarf der Station eingeht. Damit sie greift, meldet
    V2 über ``naechste_wartefrist`` den frühesten Zeitpunkt an, zu dem ein offener Satz die
    Höchstwartezeit erreicht. Die Höchstwartezeit soll deutlich über der üblichen
    Bündelungswartezeit liegen; sonst wird V2 faktisch zu V3.

    Sätze, die für sich allein keine zulässige Charge bilden können, werden wie bei V0 und V1
    nie gebunden und lösen keine Wartefrist aus. Der Anlass ändert die Regel nicht.

    Parameter (beide Pflicht, keine Ersatzwerte):

    * ``fuellschwelle_positionen``: belegte Boxpositionen, ab denen versendet wird. Eine Zahl
      für alle Stationen oder ein Mapping Station → Zahl. Ganzzahl von 1 bis
      ``box_positionen``. Die Schwelle ist an der Satzgröße auszurichten: Bei Sätzen mit zwei
      Positionen ist 7 nie erreichbar und wirkt wie 8.
    * ``hoechstwartezeit_s``: Höchstwartezeit des ältesten Satzes in Sekunden, größer 0.
    """

    name = "V2"

    def __init__(self, **parameter) -> None:
        super().__init__(**parameter)
        unbekannt = set(parameter) - {"fuellschwelle_positionen", "hoechstwartezeit_s"}
        if unbekannt:
            raise ValueError(f"V2 kennt diese Parameter nicht: {sorted(unbekannt)}")
        schwelle = parameter.get("fuellschwelle_positionen")
        if schwelle is not None:
            werte = schwelle.values() if isinstance(schwelle, Mapping) else (schwelle,)
            if not werte or not all(
                isinstance(w, int) and not isinstance(w, bool) and w >= 1 for w in werte
            ):
                raise ValueError(
                    f"fuellschwelle_positionen muss ganzzahlig >= 1 sein: {schwelle!r}"
                )
        frist = parameter.get("hoechstwartezeit_s")
        if frist is not None and (
            isinstance(frist, bool) or not isinstance(frist, int | float) or not frist > 0
        ):
            raise ValueError(f"hoechstwartezeit_s muss eine Zahl > 0 sein: {frist!r}")
        self._schwelle = schwelle
        self._hoechstwartezeit_s = None if frist is None else float(frist)

    def _schwelle_fuer(self, station: str, zustand: Planungszustand) -> int:
        """Füllschwelle der Station; fehlt sie oder ist sie zu groß, ist das ein Fehler."""
        if self._schwelle is None:
            raise ValueError("V2 braucht den Parameter fuellschwelle_positionen")
        if isinstance(self._schwelle, Mapping):
            if station not in self._schwelle:
                raise ValueError(f"fuellschwelle_positionen nennt Station {station!r} nicht")
            schwelle = self._schwelle[station]
        else:
            schwelle = self._schwelle
        if schwelle > zustand.box_positionen:
            raise ValueError(
                f"Füllschwelle {schwelle} für {station} übersteigt die Boxpositionen "
                f"({zustand.box_positionen}) und wäre nie erreichbar"
            )
        return schwelle

    def _frist(self) -> float:
        if self._hoechstwartezeit_s is None:
            raise ValueError(
                "V2 braucht den Parameter hoechstwartezeit_s (Restbedarfsregel, "
                "siehe docs/projekt/planungsverfahren.md, Abschnitt V2)"
            )
        return self._hoechstwartezeit_s

    def _fuelle_box(
        self, station_saetze: list[Anforderung], bestand: Mapping[int, int], positionen: int
    ) -> list[Anforderung]:
        """Sätze in Eingangsfolge, solange Positionen und Bestand reichen (wie V0)."""
        lokal = dict(bestand)
        frei = positionen
        gewaehlt: list[Anforderung] = []
        for anforderung in station_saetze:
            if anforderung.satz.positionen > frei or not _bestand_reicht(anforderung, lokal):
                continue
            _bestand_abziehen(anforderung, lokal)
            frei -= anforderung.satz.positionen
            gewaehlt.append(anforderung)
        return gewaehlt

    def _nach_station(self, zustand: Planungszustand) -> dict[str, list[Anforderung]]:
        """Zulässige offene Sätze je Station, Stationen nach ihrem ältesten Satz geordnet."""
        je_station: dict[str, list[Anforderung]] = {}
        for anforderung in _in_eingangsfolge(zustand.offene_anforderungen):
            if _satz_zulaessig(anforderung, zustand):
                je_station.setdefault(anforderung.station, []).append(anforderung)
        return je_station

    def entscheide(self, zustand: Planungszustand, anlass: Anlass) -> list[Chargenentscheidung]:
        frist = self._frist()
        bestand = dict(zustand.freier_bestand)
        freie_boxen = zustand.freie_boxen
        chargen: list[Chargenentscheidung] = []
        for station, saetze in self._nach_station(zustand).items():
            schwelle = self._schwelle_fuer(station, zustand)
            while freie_boxen > 0 and saetze:
                box = self._fuelle_box(saetze, bestand, zustand.box_positionen)
                if not box:
                    break
                belegt = sum(anforderung.satz.positionen for anforderung in box)
                faellig = zustand.zeit_s >= box[0].eingang_s + frist
                if belegt < schwelle and not faellig:
                    break
                for anforderung in box:
                    _bestand_abziehen(anforderung, bestand)
                freie_boxen -= 1
                chargen.append(
                    Chargenentscheidung(
                        station=station,
                        anforderung_ids=tuple(anforderung.id for anforderung in box),
                        versand_fruehestens_s=zustand.zeit_s,
                    )
                )
                gebunden = {anforderung.id for anforderung in box}
                saetze = [anforderung for anforderung in saetze if anforderung.id not in gebunden]
        return chargen

    def naechste_wartefrist(self, zustand: Planungszustand) -> float | None:
        """Frühester künftiger Zeitpunkt, zu dem ein zulässiger offener Satz fällig wird.

        Bereits fällige Sätze liefern keine Frist mehr: Werden sie trotzdem nicht gebunden,
        fehlt eine Box oder Bestand. Eine frei werdende Box löst den Anlass „Kapazität frei“
        aus. Ohne zulässige offene Sätze gibt es keine Frist.
        """
        frist = self._frist()
        termine = [
            anforderung.eingang_s + frist
            for saetze in self._nach_station(zustand).values()
            for anforderung in saetze
            if anforderung.eingang_s + frist > zustand.zeit_s
        ]
        return min(termine, default=None)


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
