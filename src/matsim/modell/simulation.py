"""SimPy-Modell der Materialversorgung (AP3).

Stand: Bauplan, Schritt 5. Fertig sind das Grundgerüst (Ressourcen, Zustand, Zeiten,
Reihenfolge gleichzeitiger Ereignisse, Protokollhilfe) und die Versorgungskette: Kommissionierung,
Hintransport bis zur Lieferung, Leerboxrückführung und die Warteursachen der Sätze auf diesem Weg.
Die übrigen Prozesse folgen in den Schritten 6 bis 8 und lösen bis dahin ``NotImplementedError``
aus.

Die Simulation verarbeitet die Entscheidungen eines Planungsverfahrens mit begrenzten
Ressourcen. Sie übernimmt keine geplanten Fertigstellungen als Ergebnis und ruft das
Verfahren nur zu den drei festgelegten Planungsanlässen auf.

Ergänzung zu Schritt 6: Planung, Fristen und Chargenbindung sind implementiert.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from typing import Any

import simpy
from simpy.events import Event

from matsim.daten.zeiten import Zeitverteilung, lade_verteilungen
from matsim.kennzahlen.ereignisprotokoll import (
    Ereignis,
    Ereignisprotokoll,
    Ereignistyp,
    Warteursache,
)
from matsim.modell.anlage import AnlagenFehler, mit_abweichungen, wert
from matsim.modell.typen import Box, Boxplatz, BoxZustand, Charge, Produktauftrag
from matsim.regeln.basis import Anlass, Planungsanlass, Planungsverfahren, Planungszustand
from matsim.regeln.verfahren import CHARGEN_IN_VERSORGUNG

from . import typen
from .planung import Planungsfehler, bereite_chargen_vor, endliche_zeit, lesekopie

# --- Reihenfolge gleichzeitiger Ereignisse (docs/projekt/logikstruktur.md, Abschnitt 3) ---------
# SimPy arbeitet Ereignisse derselben Zeit nach Priorität ab, kleinere zuerst. Es selbst nutzt
# 0 (Prozessstart, Unterbrechung) und 1 (alles Übrige, auch die Zuteilung einer Ressource).
# Die eigenen Ränge liegen dahinter und legen die Reihenfolge fest, die das Team vereinbart hat.
FREIGABE = 2  # eine Ressource wird frei (Kommissionierung, Montage, Leerbox zurück)
LIEFERUNG = 3  # eine Box kommt am Übergabeplatz an
ANKUNFT = 4  # ein Werkstück kommt an einer Station an
BEDARF = 5  # ein Produktauftrag kommt an
FRIST = 6  # eine Wartefrist des Verfahrens läuft ab
PLANUNG = 9  # der Planungsaufruf, nach allen fachlichen Ereignissen
ABGLEICH = 10  # Warteursachen ins Protokoll, nach allem anderen (Bauplan, Abschnitt 10)

#: Name des Kommissionierplatzes im Protokoll (es gibt nur einen).
KOMMISSIONIERPLATZ = "kommissionierplatz"
#: Ressource einer Transportbox im Protokoll; welche Box es ist, steht im Feld ``box_id``.
BOX = "box"

_NR_ZUSCHLAG = 1e-6  # je laufender Nummer; bei gleichem Rang kommt die kleinere Nummer zuerst
_NR_GRENZE = 100_000  # darüber würde der Zuschlag in den nächsten Rang reichen


class Termin(Event):
    """Wie ``env.timeout(verzoegerung)``, aber mit Rang für gleichzeitige Ereignisse.

    ``nr`` ist die laufende Nummer des betroffenen Objekts, etwa 1 für das Werkstück W001.
    Beispiel: ``yield Termin(self.env, 96, LIEFERUNG, nr=3)``.
    """

    def __init__(self, env: simpy.Environment, verzoegerung: float, rang: int, nr: int = 0) -> None:
        if verzoegerung < 0:
            raise ValueError(f"Termin in der Vergangenheit: Verzögerung {verzoegerung} s")
        if not 0 <= nr < _NR_GRENZE:
            raise ValueError(f"Laufende Nummer außerhalb von 0 bis {_NR_GRENZE - 1}: {nr}")
        super().__init__(env)
        # Wie bei simpy.Timeout steht das Ergebnis schon fest; SimPy meldet es zur Zielzeit.
        self._ok = True
        self._value = None
        env.schedule(self, rang + nr * _NR_ZUSCHLAG, verzoegerung)


class SimulationsFehler(RuntimeError):
    """Widerspruch im eigenen Zustand der Simulation. Wird gemeldet, nie stillschweigend repariert."""


class Simulation:
    """Ein Simulationslauf: eine Anlage, ein Szenario, ein Verfahren, eine Replikation.

    Aufbau und Begründungen: Bauplan zum Simulationskern (AP3), Abschnitte 2 bis 4.
    """

    def __init__(
        self,
        anlage: dict[str, Any],
        szenario: dict[str, Any],
        verfahren: Planungsverfahren,
        seed: int,
        verlauf: Sequence[Produktauftrag] | None = None,
    ) -> None:
        name = szenario.get("name", "ohne Namen")
        self.anlage = mit_abweichungen(anlage, szenario.get("anlage_abweichungen") or {}, name)
        self.szenario = szenario
        self.verfahren = verfahren
        self.seed = seed
        #: Vorab erzeugter Bedarfsverlauf; ohne Angabe erzeugt ihn der Runner (Schritt 8).
        self.verlauf = verlauf
        self.env = simpy.Environment()
        self.protokoll = Ereignisprotokoll()

        # --- Zeiten (Bauplan, Abschnitt 4) ----------------------------------------------------
        zeiten = szenario.get("zeiten") or {}
        verteilt = zeiten.get("verteilt", []) if zeiten.get("modus") == "verteilung" else []
        self._verteilungen: dict[str, Zeitverteilung] = {}
        if verteilt:
            alle = lade_verteilungen()
            fehlend = [pfad for pfad in verteilt if pfad not in alle]
            if fehlend:
                raise AnlagenFehler(f"Szenario {name}: keine Verteilung für {fehlend}")
            self._verteilungen = {pfad: alle[pfad] for pfad in verteilt}
        self._stroeme: dict[str, random.Random] = {}

        # --- Begrenzte Ressourcen (Bauplan, Abschnitt 3) --------------------------------------
        self.stationen: tuple[str, ...] = tuple(self.anlage["stationen"])
        self.kommissionierplatz = simpy.Resource(
            self.env, capacity=wert(self.anlage, "kommissionierplatz.gleichzeitige_chargen")
        )
        anzahl_fahrzeuge = wert(self.anlage, "fahrzeuge.anzahl")
        self.fahrzeuge = self._regal(f"fahrzeug_{i}" for i in range(1, anzahl_fahrzeuge + 1))
        self.box_positionen: int = wert(self.anlage, "box.positionen")
        anzahl_boxen = wert(self.anlage, "box.transportboxen_frei")
        self.boxen = self._regal(Box(i, self.box_positionen) for i in range(1, anzahl_boxen + 1))
        self.uebergabeplaetze: dict[str, simpy.Store] = {}
        self.montagestationen: dict[str, simpy.PriorityResource] = {}
        for station in self.stationen:
            plaetze = wert(self.anlage, f"stationen.{station}.uebergabeplaetze")
            self.uebergabeplaetze[station] = self._regal(
                f"{station}.platz_{i}" for i in range(1, plaetze + 1)
            )
            self.montagestationen[station] = simpy.PriorityResource(self.env, capacity=1)

        # --- Fachlicher Zustand (Bauplan, Abschnitt 3) ----------------------------------------
        #: Komponenten je Station als Paare (PNo, Stückzahl), in Montagereihenfolge.
        self.materialsatz: dict[str, tuple[tuple[int, int], ...]] = {
            station: tuple(
                (pno, wert(self.anlage, f"stationen.{station}.materialsatz.{pno}"))
                for pno in self.anlage["stationen"][station]["materialsatz"]
            )
            for station in self.stationen
        }
        self.zulaessige_teile: dict[str, frozenset[int]] = {
            station: frozenset(wert(self.anlage, f"stationen.{station}.zulaessige_teile"))
            for station in self.stationen
        }
        #: Freie, nicht reservierte Teile je Teilenummer.
        self.freier_bestand: dict[int, int] = {
            pno: wert(self.anlage, f"materiallager.anfangsbestand.{pno}")
            for pno in self.anlage["materiallager"]["anfangsbestand"]
        }
        self.anforderungen: dict = {}  # alle Anforderungen des Laufs, Schlüssel ist die Kennung
        self.offene: dict = {}  # noch keiner Charge zugeordnet; nur diese sieht das Verfahren
        self.chargen: dict = {}  # gebundene Chargen, unveränderlich
        self.box_an_platz: dict[str, Box] = {}  # welche Box auf welchem Übergabeplatz steht
        self.chargen_in_versorgung = 0  # gebunden, aber noch nicht abgeliefert (für V0)
        #: Worauf ein Satz gerade wartet, je Anforderung; fehlt sie, wartet der Satz nicht.
        self.warteursache: dict[str, Warteursache] = {}
        self._warten_im_protokoll: dict[str, Warteursache] = {}  # Stand laut Protokoll
        self._abzugleichen: dict[str, None] = {}  # in diesem Zeitpunkt geändert, in Reihenfolge
        self._bedarf_je_zeit: dict[float, list[typen.Anforderung]] = {}
        self._verarbeitete_anlaesse = 0
        self._letzte_planung_s: float | None = None
        self._frist: Termin | None = None
        #: Historie; alle noch nicht verarbeiteten Meldungen bilden den nächsten Sammelaufruf.
        self.anlaesse: list[Anlass] = []
        self.werkstuecke: dict = {}  # Werkstücke mit Fortschritt (Schritt 7)

    def _regal(self, dinge: Iterable[Any]) -> simpy.Store:
        """Ein ``simpy.Store`` mit benannten Einheiten; ``get()`` liefert die vorderste."""
        regal = simpy.Store(self.env)
        regal.items.extend(dinge)
        return regal

    # --- Hilfen (Bauplan, Abschnitte 4 und 10) -------------------------------------------------

    def dauer(self, pfad: str) -> float:
        """Dauer in Sekunden zum Parameterpfad aus ``anlage.yaml``.

        Festwert, außer der Pfad steht im Szenario unter ``zeiten.verteilt``: dann ein Messwert
        aus der empirischen Verteilung, gezogen aus einem eigenen Zufallsstrom je Parameter.
        """
        if pfad in self._verteilungen:
            return float(self._verteilungen[pfad].ziehe(self._strom(pfad)))
        return float(wert(self.anlage, pfad))

    def _strom(self, pfad: str) -> random.Random:
        """Eigener Zufallsstrom je Parameter, damit V0 bis V4 dieselben Dauerfolgen sehen."""
        if pfad not in self._stroeme:
            self._stroeme[pfad] = random.Random(f"{self.seed}/{pfad}")
        return self._stroeme[pfad]

    def protokolliere(self, ereignis: Ereignistyp, **felder: Any) -> Ereignis:
        """Schreibt eine Zeile mit der aktuellen Simulationszeit ins Ereignisprotokoll."""
        return self.protokoll.schreibe(self.env.now, ereignis, **felder)

    def setze_warteursache(
        self, anforderung_ids: Iterable[str], ursache: Warteursache | None
    ) -> None:
        """Legt fest, worauf die Sätze ab jetzt warten; ``None`` heißt, sie warten nicht.

        Ins Protokoll kommt nur, was am Ende des Zeitpunkts gilt: Der Abgleich läuft nach allen
        anderen Ereignissen derselben Zeit (Rang ABGLEICH). So entstehen keine Wartezeiten der
        Länge null, und mehrere Wechsel im selben Moment ergeben höchstens ein Ende und einen
        Beginn (Bauplan, Abschnitt 10).
        """
        if not self._abzugleichen:
            Termin(self.env, 0, ABGLEICH).callbacks.append(self._gleiche_wartezeiten_ab)
        for anforderung_id in anforderung_ids:
            if ursache is None:
                self.warteursache.pop(anforderung_id, None)
            else:
                self.warteursache[anforderung_id] = ursache
            self._abzugleichen[anforderung_id] = None

    def _gleiche_wartezeiten_ab(self, _ereignis: Event) -> None:
        """Schreibt die Änderungen der Warteursachen dieses Zeitpunkts ins Protokoll."""
        for anforderung_id in self._abzugleichen:
            jetzt = self.warteursache.get(anforderung_id)
            bisher = self._warten_im_protokoll.get(anforderung_id)
            if jetzt == bisher:
                continue
            if bisher is not None:
                self.protokolliere(
                    Ereignistyp.WARTEN_ENDE, anforderung_id=anforderung_id, ursache=bisher
                )
                del self._warten_im_protokoll[anforderung_id]
            if jetzt is not None:
                self.protokolliere(
                    Ereignistyp.WARTEN_BEGINN, anforderung_id=anforderung_id, ursache=jetzt
                )
                self._warten_im_protokoll[anforderung_id] = jetzt
        self._abzugleichen.clear()

    # --- Planung (Bauplan, Abschnitt 6; Issue #27) ---------------------------------------------

    def melde_bedarf(self, anforderung: typen.Anforderung) -> None:
        """Plant den Eingang einer Anforderung ein. Vor ihrem Eingang bleibt sie unsichtbar."""
        if not endliche_zeit(anforderung.eingang_s) or anforderung.eingang_s < self.env.now:
            raise SimulationsFehler(f"{anforderung.id}: ungültiger Bedarfseingang")

        zeit = anforderung.eingang_s
        if zeit not in self._bedarf_je_zeit:
            self._bedarf_je_zeit[zeit] = []
            Termin(self.env, zeit - self.env.now, BEDARF).callbacks.append(self._erfasse_bedarf)
        self._bedarf_je_zeit[zeit].append(anforderung)

    def _erfasse_bedarf(self, _ereignis: Event) -> None:
        for anforderung in sorted(self._bedarf_je_zeit.pop(self.env.now), key=lambda a: a.id):
            if anforderung.id in self.anforderungen:
                raise SimulationsFehler(f"Anforderung {anforderung.id} bereits erfasst")
            satz = anforderung.satz
            if (
                satz.anforderung_id != anforderung.id or satz.station != anforderung.station
                or satz.komponenten != self.materialsatz.get(anforderung.station)
            ):
                raise SimulationsFehler(f"{anforderung.id}: unpassender Materialsatz")
            self.anforderungen[anforderung.id] = self.offene[anforderung.id] = anforderung
            ids = {"anforderung_id": anforderung.id, "ressource": anforderung.station}
            self.protokolliere(Ereignistyp.BEDARF_EINGANG, **ids)
            self.protokolliere(Ereignistyp.SATZ_GEBILDET, **ids)
            self.melde_anlass(Planungsanlass.BEDARFSEINGANG, anforderung.id)

    def melde_anlass(self, art: Planungsanlass, detail: str = "") -> None:
        """Plant beim ersten Anlass einen Aufruf nach allen fachlichen Ereignissen dieser Zeit."""
        self.anlaesse.append(Anlass(Planungsanlass(art), self.env.now, detail))
        if self._letzte_planung_s == self.env.now and not self.offene and art == Planungsanlass.KAPAZITAET_FREI:
            # Eine nachgelagerte Nullzeit-Freigabe ohne Restbedarf ändert keine Entscheidung.
            self._verarbeitete_anlaesse = len(self.anlaesse)
        elif len(self.anlaesse) == self._verarbeitete_anlaesse + 1:
            self.env.process(self.plane())

    def planungszustand(self) -> Planungszustand:
        """Momentaufnahme für das Planungsverfahren (nur der jetzt bekannte Zustand)."""
        return Planungszustand(
            zeit_s=self.env.now,
            offene_anforderungen=tuple(sorted(self.offene.values(), key=lambda a: (a.eingang_s, a.id))),
            freier_bestand=lesekopie(self.freier_bestand),
            freie_boxen=len(self.boxen.items),
            freie_kommissionierplaetze=int(self.kommissionierplatz.capacity) - self.kommissionierplatz.count,
            freie_fahrzeuge=len(self.fahrzeuge.items),
            freie_uebergabeplaetze=lesekopie({s: len(p.items) for s, p in self.uebergabeplaetze.items()}),
            box_positionen=self.box_positionen,
            zulaessige_teile=lesekopie(self.zulaessige_teile),
            zusatz=lesekopie({CHARGEN_IN_VERSORGUNG: self.chargen_in_versorgung}),
        )

    def plane(self):
        """Prozess: ruft das Verfahren auf, prüft die Entscheidungen und bindet die Chargen."""
        yield Termin(self.env, 0, PLANUNG)
        meldungen = self.anlaesse[self._verarbeitete_anlaesse:]
        if not meldungen:
            raise SimulationsFehler("Planungsaufruf ohne neuen Planungsanlass")
        self._verarbeitete_anlaesse = len(self.anlaesse)
        self._letzte_planung_s = self.env.now
        rang = {Planungsanlass.BEDARFSEINGANG: BEDARF, Planungsanlass.WARTEFRIST_ABGELAUFEN: FRIST,
                Planungsanlass.KAPAZITAET_FREI: PLANUNG}
        fuehrend = min(meldungen, key=lambda a: rang[a.art])
        detail = "; ".join(f"{a.art}: {a.detail}" for a in meldungen)
        anlass = Anlass(fuehrend.art, self.env.now, detail)
        zustand = self.planungszustand()
        entscheidungen = self.verfahren.entscheide(zustand, anlass)
        try:
            chargen = bereite_chargen_vor(
                entscheidungen, zustand, self.boxen.items, self.anlage, len(self.chargen) + 1
            )
        except Planungsfehler as fehler:
            self.protokolliere(Ereignistyp.PLANUNG_AUFRUF, bemerkung=f"{detail}; abgelehnt: {fehler}")
            raise

        self.protokolliere(Ereignistyp.PLANUNG_AUFRUF, bemerkung=detail, menge=len(chargen))
        # Kein yield zwischen Prüfung und letzter Bindung: Die Versorgung sieht nur den Endstand.
        for charge in chargen:
            self._binde_charge(charge)
        for a in self.offene.values():
            if any(self.freier_bestand.get(p, 0) < m for p, m in a.satz.komponenten):
                ursache = Warteursache.BESTAND
            elif not self.boxen.items:
                ursache = Warteursache.BOX
            else:
                ursache = Warteursache.BUENDELUNG
            self.setze_warteursache([a.id], ursache)
        self._merke_frist(self.verfahren.naechste_wartefrist(self.planungszustand()))

    def _binde_charge(self, charge: Charge) -> None:
        box = self.boxen.items.pop(0)
        box.zustand = BoxZustand.IN_KOMMISSIONIERUNG
        self.chargen[charge.id] = charge
        self.chargen_in_versorgung += 1
        ids = {"charge_id": charge.id, "box_id": str(box.id)}
        self.protokolliere(Ereignistyp.RESERVIERT, ressource=BOX, zustand_alt=BoxZustand.FREI,
                           zustand_neu=box.zustand, **ids)
        for satz in charge.saetze:
            del self.offene[satz.anforderung_id]
            self.protokolliere(Ereignistyp.CHARGE_GEBUNDEN, anforderung_id=satz.anforderung_id,
                               ressource=charge.station, **ids)
            for pno, menge in satz.komponenten:
                self.freier_bestand[pno] -= menge
                self.protokolliere(Ereignistyp.RESERVIERT, anforderung_id=satz.anforderung_id,
                                   ressource="lager", pno=pno, menge=menge, **ids)
        self.setze_warteursache((s.anforderung_id for s in charge.saetze), None)
        self.env.process(self.versorgung(charge, box))

    def _merke_frist(self, zeit_s: float | None) -> None:
        if zeit_s is None:
            self._frist = None
            return
        if not endliche_zeit(zeit_s) or zeit_s <= self.env.now:
            raise Planungsfehler(f"Wartefrist {zeit_s!r} muss endlich und nach {self.env.now} s liegen")
        self._frist = Termin(self.env, zeit_s - self.env.now, FRIST)
        self._frist.callbacks.append(self._frist_abgelaufen)

    def _frist_abgelaufen(self, ereignis: Event) -> None:
        # Eine inzwischen ersetzte oder gestrichene Frist löst keinen Planungsaufruf aus.
        if ereignis is self._frist:
            self._frist = None
            self.melde_anlass(Planungsanlass.WARTEFRIST_ABGELAUFEN, str(self.env.now))

    # --- Prozesse (Bauplan, Abschnitte 5, 7 und 8) ---------------------------------------------

    def bedarfseingang(self):
        """Prozess: legt je Produktauftrag die Anforderungen an und startet das Werkstück."""
        raise NotImplementedError("AP3 Schritt 8: Bedarfseingang")

    def versorgung(self, charge: Charge, box: Box):
        """Prozess je Charge: Kommissionierung, dann Hintransport bis zur Lieferung.

        Die Bindung startet ihn (Anschlusspunkt 1). ``yield from`` reicht die Wartepunkte der
        beiden Teilprozesse durch; so bleiben sie einzeln testbar.
        """
        yield from self.kommissionierung(charge, box)
        yield from self.hintransport(charge, box)

    def kommissionierung(self, charge: Charge, box: Box):
        """Belegt den Kommissionierplatz, pickt die Sätze der Charge und legt die Teile in die Box.

        Bauplan, Abschnitt 7, Schritte 0 bis 5. Die Charge ist schon gebunden: Box reserviert,
        Bestand vom freien Bestand abgezogen (Planung, Schritt 6). Dauer am Platz:
        Vorlauf + Teile × Pickzeit + (min(Quellboxen, Teile) − 1) × Quellboxwechsel (A-11).
        Jeder Satz wartet auf die Kommissionierung, außer während seiner eigenen Picks
        (Abschnitt 10).
        """
        saetze = [satz.anforderung_id for satz in charge.saetze]
        if box.id != charge.box_id or box.zustand != BoxZustand.IN_KOMMISSIONIERUNG or box.plaetze:
            raise SimulationsFehler(
                f"Charge {charge.id}: Box {box.id} ist nicht die leere, reservierte Box "
                f"{charge.box_id} (Zustand {box.zustand}, {len(box.plaetze)} Teile)"
            )
        if charge.positionen > box.positionen:
            raise SimulationsFehler(
                f"Charge {charge.id}: {charge.positionen} Teile passen nicht in die Box"
            )
        ids = {"charge_id": charge.id, "box_id": str(box.id)}

        # 0  Will das Verfahren erst später versenden, beginnt die Kommissionierung erst dann.
        #    Bis dahin warten die Sätze auf die Bündelung.
        if charge.versand_fruehestens_s > self.env.now:
            self.setze_warteursache(saetze, Warteursache.BUENDELUNG)
            yield self.env.timeout(charge.versand_fruehestens_s - self.env.now)

        # Ab jetzt wartet jeder Satz auf die Kommissionierung: auf den Platz, den Vorlauf und die
        # Picks der Sätze vor ihm.
        self.setze_warteursache(saetze, Warteursache.KOMMISSIONIERUNG)

        # 1  Kommissionierplatz anfordern; ist er belegt, stellt sich die Charge an.
        with self.kommissionierplatz.request() as anfrage:
            yield anfrage
            self.protokolliere(Ereignistyp.RESERVIERT, ressource=KOMMISSIONIERPLATZ, **ids)
            self.protokolliere(
                Ereignistyp.KOMMISSIONIERUNG_BEGINN, ressource=KOMMISSIONIERPLATZ, **ids
            )

            # 2  Vorlauf: Ziel- und Quellboxen werden an den Platz gebracht.
            yield self.env.timeout(self.dauer("kommissionierplatz.vorlauf_s"))

            # 3  Picks, Satz für Satz in der Reihenfolge der Charge; jedes Teil bleibt seiner
            #    Anforderung zugeordnet. Während seiner eigenen Picks wartet ein Satz nicht.
            for satz in charge.saetze:
                self.setze_warteursache([satz.anforderung_id], None)
                for pno, menge in satz.komponenten:
                    for _ in range(menge):
                        yield self.env.timeout(self.dauer("kommissionierplatz.pickzeit_je_teil_s"))
                        box.plaetze.append(Boxplatz(len(box.plaetze) + 1, pno, satz.anforderung_id))
                        self.protokolliere(
                            Ereignistyp.TEIL_GEPICKT,
                            anforderung_id=satz.anforderung_id,
                            ressource=KOMMISSIONIERPLATZ,
                            pno=pno,
                            menge=1,
                            **ids,
                        )
                self.setze_warteursache([satz.anforderung_id], Warteursache.KOMMISSIONIERUNG)

            # 4  Quellboxwechsel; eine Charge mit nur einem Teil braucht keinen.
            quellboxen = wert(self.anlage, "kommissionierplatz.quellboxen_je_auftrag")
            for _ in range(min(quellboxen, charge.positionen) - 1):
                yield self.env.timeout(self.dauer("kommissionierplatz.quellboxwechsel_s"))

            # 5  Freigabe des Platzes im Rang FREIGABE, damit gleichzeitige Lieferungen,
            #    Ankünfte und die Planung den Platz schon frei sehen (Abschnitt 9).
            yield Termin(self.env, 0, FREIGABE)
        self.protokolliere(Ereignistyp.KOMMISSIONIERUNG_ENDE, ressource=KOMMISSIONIERPLATZ, **ids)
        self.protokolliere(Ereignistyp.RESERVIERUNG_AUFGELOEST, ressource=KOMMISSIONIERPLATZ, **ids)
        self.melde_anlass(Planungsanlass.KAPAZITAET_FREI, KOMMISSIONIERPLATZ)
        # Das Warten auf die Kommissionierung ist vorbei; worauf die Box jetzt wartet, legt der
        # Hintransport fest.
        self.setze_warteursache(saetze, None)

    def hintransport(self, charge: Charge, box: Box):
        """Reserviert einen Übergabeplatz der Zielstation, holt ein Fahrzeug, fährt und liefert ab.

        Bauplan, Abschnitt 7, Schritte 6 bis 9. Übergangsregeln bis zum Referenzpaket (#18):
        erst Übergabeplatz, dann Fahrzeug (A-12); Fahrzeuge und Plätze nach dem Regalprinzip,
        das am längsten freie zuerst, wartende Aufträge in ihrer Reihenfolge (A-13).
        """
        if (
            box.id != charge.box_id
            or box.zustand != BoxZustand.IN_KOMMISSIONIERUNG
            or len(box.plaetze) != charge.positionen
        ):
            raise SimulationsFehler(
                f"Charge {charge.id}: Box {box.id} ist nicht fertig kommissioniert "
                f"(Zustand {box.zustand}, {len(box.plaetze)} von {charge.positionen} Teilen)"
            )
        ids = {"charge_id": charge.id, "box_id": str(box.id)}
        saetze = [satz.anforderung_id for satz in charge.saetze]

        # 6  Übergabeplatz der Zielstation reservieren. Sind alle belegt, wartet die fertige Box
        #    an der Kommissionierung und bindet kein Fahrzeug (A-12). Warteursache:
        #    Stationskapazität; wird der Platz sofort frei, kommt sie nicht ins Protokoll.
        self.setze_warteursache(saetze, Warteursache.STATIONSKAPAZITAET)
        platz = yield self.uebergabeplaetze[charge.station].get()
        self.protokolliere(Ereignistyp.RESERVIERT, ressource=platz, **ids)

        # 7  Fahrzeug holen; Hintransporte und Leerboxen stellen sich gemeinsam an (A-13).
        #    Warteursache: Transport. Ab dem Fahrzeug wartet der Satz nicht mehr, er fährt.
        self.setze_warteursache(saetze, Warteursache.TRANSPORT)
        fahrzeug = yield self.fahrzeuge.get()
        self.protokolliere(Ereignistyp.RESERVIERT, ressource=fahrzeug, **ids)
        self.setze_warteursache(saetze, None)

        # 8  Aufnahme, Fahrt und Übergabe als ein Fahrauftrag (A-07: ohne Warten auf ein Fahrzeug).
        box.zustand = BoxZustand.UNTERWEGS
        self.protokolliere(
            Ereignistyp.TRANSPORT_BEGINN,
            ressource=fahrzeug,
            zustand_alt=BoxZustand.IN_KOMMISSIONIERUNG,
            zustand_neu=BoxZustand.UNTERWEGS,
            menge=len(box.plaetze),  # belegte Positionen, für K3
            **ids,
        )
        yield Termin(self.env, self.dauer("fahrzeuge.fahrauftrag_s"), LIEFERUNG, nr=box.id)
        self.protokolliere(Ereignistyp.TRANSPORT_ENDE, ressource=fahrzeug, **ids)

        # 9  Lieferung: Die Box steht auf dem Platz, die Montage findet sie über box_an_platz
        #    (Anschlusspunkt 2). Der Platz bleibt belegt, bis die leere Box abgeholt ist.
        if platz in self.box_an_platz:
            raise SimulationsFehler(f"Charge {charge.id}: Übergabeplatz {platz} ist schon belegt")
        self.chargen_in_versorgung -= 1
        if self.chargen_in_versorgung < 0:
            raise SimulationsFehler(f"Charge {charge.id}: mehr Lieferungen als gebundene Chargen")
        box.zustand = BoxZustand.AN_STATION
        self.box_an_platz[platz] = box
        self.protokolliere(
            Ereignistyp.LIEFERUNG,
            ressource=platz,
            zustand_alt=BoxZustand.UNTERWEGS,
            zustand_neu=BoxZustand.AN_STATION,
            **ids,
        )

        # Das Fahrzeug ist sofort wieder frei und stellt sich hinten ins Regal.
        self.fahrzeuge.put(fahrzeug)
        self.protokolliere(Ereignistyp.RESERVIERUNG_AUFGELOEST, ressource=fahrzeug, **ids)
        self.melde_anlass(Planungsanlass.KAPAZITAET_FREI, fahrzeug)

    def leerboxrueckfuehrung(self, box: Box, platz: str):
        """Prozess: holt die leere Box ab, gibt den Platz frei und bringt sie ins Kistenlager.

        Bauplan, Abschnitt 7. Die Montage startet ihn, sobald das letzte Teil entnommen ist
        (Anschlusspunkt 3). Übergangsregel bis zum Referenzpaket (#18): Rückfahrt sofort, sobald
        ein Fahrzeug frei ist, ins Kistenlager, dort ist die Box gleich wieder frei (A-14);
        Fahrzeit wie der Hintransport (A-09).
        """
        if self.box_an_platz.get(platz) is not box or box.zustand != BoxZustand.AN_STATION:
            raise SimulationsFehler(f"Box {box.id} steht nicht auf Übergabeplatz {platz}")
        if box.plaetze:
            raise SimulationsFehler(f"Box {box.id} ist nicht leer ({len(box.plaetze)} Teile)")
        station = platz.split(".")[0]  # Platznamen haben die Form "RASS1.platz_1"
        ids = {"box_id": str(box.id)}

        # 1  Fahrzeug holen; die Rückfahrt stellt sich mit den Hintransporten an (A-13).
        #    Bis ein Fahrzeug kommt, bleibt die leere Box auf dem Platz. Hier wartet kein Satz,
        #    deshalb gibt es keine Warteursache.
        fahrzeug = yield self.fahrzeuge.get()
        self.protokolliere(Ereignistyp.RESERVIERT, ressource=fahrzeug, **ids)

        # 2  Abholung: Box aufs Fahrzeug, der Übergabeplatz ist ab jetzt frei.
        box.zustand = BoxZustand.LEER_ZURUECK
        del self.box_an_platz[platz]
        self.protokolliere(
            Ereignistyp.LEERBOX_RUECK_BEGINN,
            ressource=fahrzeug,
            zustand_alt=BoxZustand.AN_STATION,
            zustand_neu=BoxZustand.LEER_ZURUECK,
            **ids,
        )
        self.uebergabeplaetze[station].put(platz)
        self.protokolliere(Ereignistyp.RESERVIERUNG_AUFGELOEST, ressource=platz, **ids)
        self.melde_anlass(Planungsanlass.KAPAZITAET_FREI, platz)

        # 3  Fahrt ins Kistenlager; die Ankunft gibt Box und Fahrzeug frei, also Rang FREIGABE.
        yield Termin(self.env, self.dauer("fahrzeuge.leerboxruecktransport_s"), FREIGABE, nr=box.id)

        # 4  Box und Fahrzeug sind wieder frei und stellen sich hinten in ihr Regal.
        box.zustand = BoxZustand.FREI
        self.protokolliere(
            Ereignistyp.LEERBOX_RUECK_ENDE,
            ressource=fahrzeug,
            zustand_alt=BoxZustand.LEER_ZURUECK,
            zustand_neu=BoxZustand.FREI,
            **ids,
        )
        self.boxen.put(box)
        self.protokolliere(Ereignistyp.RESERVIERUNG_AUFGELOEST, ressource=BOX, **ids)
        self.fahrzeuge.put(fahrzeug)
        self.protokolliere(Ereignistyp.RESERVIERUNG_AUFGELOEST, ressource=fahrzeug, **ids)
        self.melde_anlass(Planungsanlass.KAPAZITAET_FREI, BOX)
        self.melde_anlass(Planungsanlass.KAPAZITAET_FREI, fahrzeug)

    def werkstueckumlauf(self, werkstueck):
        """Prozess je Werkstück: Ankunft, Montage bei vollständigem Satz, sonst Weiterfahrt."""
        raise NotImplementedError("AP3 Schritt 7 (#28): Werkstückumlauf")

    def montage(self, station, werkstueck, box, platz):
        """Montage mit Komponentenverbrauch aus der Box am Übergabeplatz der Station."""
        raise NotImplementedError("AP3 Schritt 7 (#28): Montage")

    def laufe(self) -> Ereignisprotokoll:
        """Startet die Prozesse und läuft bis zum Endkriterium oder zur maximalen Laufzeit."""
        raise NotImplementedError("AP3 Schritt 8: Simulationslauf")
