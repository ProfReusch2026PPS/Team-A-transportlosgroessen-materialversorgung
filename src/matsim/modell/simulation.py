"""SimPy-Modell der Materialversorgung (AP3).

Stand: Bauplan, Schritt 2. Fertig sind das Grundgerüst (Ressourcen, Zustand, Zeiten,
Reihenfolge gleichzeitiger Ereignisse, Protokollhilfe) und die Kommissionierung. Die übrigen
Prozesse folgen in den Schritten 3 bis 8 und lösen bis dahin ``NotImplementedError`` aus.

Die Simulation verarbeitet die Entscheidungen eines Planungsverfahrens mit begrenzten
Ressourcen. Sie übernimmt keine geplanten Fertigstellungen als Ergebnis und ruft das
Verfahren nur zu den drei festgelegten Planungsanlässen auf.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from typing import Any

import simpy
from simpy.events import Event

from matsim.daten.zeiten import Zeitverteilung, lade_verteilungen
from matsim.kennzahlen.ereignisprotokoll import Ereignis, Ereignisprotokoll, Ereignistyp
from matsim.modell.anlage import AnlagenFehler, mit_abweichungen, wert
from matsim.modell.typen import Box, Boxplatz, BoxZustand, Charge, Produktauftrag
from matsim.regeln.basis import Anlass, Planungsanlass, Planungsverfahren, Planungszustand

# --- Reihenfolge gleichzeitiger Ereignisse (docs/projekt/logikstruktur.md, Abschnitt 3) ---------
# SimPy arbeitet Ereignisse derselben Zeit nach Priorität ab, kleinere zuerst. Es selbst nutzt
# 0 (Prozessstart, Unterbrechung) und 1 (alles Übrige, auch die Zuteilung einer Ressource).
# Die eigenen Ränge liegen dahinter und legen die Reihenfolge fest, die das Team vereinbart hat.
FREIGABE = 2  # eine Ressource wird frei (Kommissionierung, Montage, Leerbox zurück)
LIEFERUNG = 3  # eine Box kommt am Übergabeplatz an
ANKUNFT = 4  # ein Werkstück kommt an einer Station an
BEDARF = 5  # ein Produktauftrag kommt an
FRIST = 6  # eine Wartefrist des Verfahrens läuft ab
PLANUNG = 9  # der Planungsaufruf, immer zuletzt

#: Name des Kommissionierplatzes im Protokoll (es gibt nur einen).
KOMMISSIONIERPLATZ = "kommissionierplatz"

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
        self.warteursache: dict = {}  # laufende Wartezeit je Satz (Schritt 5 und 6)
        #: Gemeldete Planungsanlässe; ab Schritt 6 löst der erste je Zeitpunkt die Planung aus.
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

    # --- Planung (Bauplan, Abschnitt 6; Issue #27) ---------------------------------------------

    def melde_anlass(self, art: Planungsanlass, detail: str = "") -> None:
        """Merkt einen Planungsanlass vor; geplant wird je Zeitpunkt einmal, zuletzt.

        Stand Schritt 2: Die Anlässe werden nur gesammelt. Den Planungsaufruf dazu ergänzt
        Schritt 6 (#27).
        """
        self.anlaesse.append(Anlass(art, self.env.now, detail))

    def planungszustand(self) -> Planungszustand:
        """Momentaufnahme für das Planungsverfahren (nur der jetzt bekannte Zustand)."""
        raise NotImplementedError("AP3 Schritt 6 (#27): Planungszustand bilden")

    def plane(self):
        """Prozess: ruft das Verfahren auf, prüft die Entscheidungen und bindet die Chargen."""
        raise NotImplementedError("AP3 Schritt 6 (#27): Planungsaufruf und Bindung")

    # --- Prozesse (Bauplan, Abschnitte 5, 7 und 8) ---------------------------------------------

    def bedarfseingang(self):
        """Prozess: legt je Produktauftrag die Anforderungen an und startet das Werkstück."""
        raise NotImplementedError("AP3 Schritt 8: Bedarfseingang")

    def versorgung(self, charge, box):
        """Prozess je Charge: Kommissionierung, dann Hintransport bis zur Lieferung."""
        raise NotImplementedError("AP3 Schritte 2 und 3: Versorgungskette")

    def kommissionierung(self, charge: Charge, box: Box):
        """Belegt den Kommissionierplatz, pickt die Sätze der Charge und legt die Teile in die Box.

        Bauplan, Abschnitt 7, Schritte 0 bis 5. Die Charge ist schon gebunden: Box reserviert,
        Bestand vom freien Bestand abgezogen (Planung, Schritt 6). Dauer am Platz:
        Vorlauf + Teile × Pickzeit + (min(Quellboxen, Teile) − 1) × Quellboxwechsel (A-11).
        """
        teile = [
            (satz.anforderung_id, pno)
            for satz in charge.saetze
            for pno, menge in satz.komponenten
            for _ in range(menge)
        ]
        if box.id != charge.box_id or box.zustand != BoxZustand.IN_KOMMISSIONIERUNG or box.plaetze:
            raise SimulationsFehler(
                f"Charge {charge.id}: Box {box.id} ist nicht die leere, reservierte Box "
                f"{charge.box_id} (Zustand {box.zustand}, {len(box.plaetze)} Teile)"
            )
        if len(teile) > box.positionen:
            raise SimulationsFehler(
                f"Charge {charge.id}: {len(teile)} Teile passen nicht in die Box"
            )
        ids = {"charge_id": charge.id, "box_id": str(box.id)}

        # 0  Will das Verfahren erst später versenden, beginnt die Kommissionierung erst dann.
        if charge.versand_fruehestens_s > self.env.now:
            yield self.env.timeout(charge.versand_fruehestens_s - self.env.now)

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
            #    Anforderung zugeordnet.
            for anforderung_id, pno in teile:
                yield self.env.timeout(self.dauer("kommissionierplatz.pickzeit_je_teil_s"))
                box.plaetze.append(Boxplatz(len(box.plaetze) + 1, pno, anforderung_id))
                self.protokolliere(
                    Ereignistyp.TEIL_GEPICKT,
                    anforderung_id=anforderung_id,
                    ressource=KOMMISSIONIERPLATZ,
                    pno=pno,
                    menge=1,
                    **ids,
                )

            # 4  Quellboxwechsel; eine Charge mit nur einem Teil braucht keinen.
            quellboxen = wert(self.anlage, "kommissionierplatz.quellboxen_je_auftrag")
            for _ in range(min(quellboxen, len(teile)) - 1):
                yield self.env.timeout(self.dauer("kommissionierplatz.quellboxwechsel_s"))

            # 5  Freigabe des Platzes im Rang FREIGABE, damit gleichzeitige Lieferungen,
            #    Ankünfte und die Planung den Platz schon frei sehen (Abschnitt 9).
            yield Termin(self.env, 0, FREIGABE)
        self.protokolliere(Ereignistyp.KOMMISSIONIERUNG_ENDE, ressource=KOMMISSIONIERPLATZ, **ids)
        self.protokolliere(Ereignistyp.RESERVIERUNG_AUFGELOEST, ressource=KOMMISSIONIERPLATZ, **ids)
        self.melde_anlass(Planungsanlass.KAPAZITAET_FREI, KOMMISSIONIERPLATZ)

    def hintransport(self, charge, box):
        """Reserviert den Übergabeplatz, holt ein Fahrzeug, fährt und liefert ab."""
        raise NotImplementedError("AP3 Schritt 3: Hintransport und Lieferung")

    def leerboxrueckfuehrung(self, box, platz):
        """Prozess: holt die leere Box ab, gibt den Platz frei und bringt sie ins Lager."""
        raise NotImplementedError("AP3 Schritt 4: Leerboxrückführung")

    def werkstueckumlauf(self, werkstueck):
        """Prozess je Werkstück: Ankunft, Montage bei vollständigem Satz, sonst Weiterfahrt."""
        raise NotImplementedError("AP3 Schritt 7 (#28): Werkstückumlauf")

    def montage(self, station, werkstueck, box, platz):
        """Montage mit Komponentenverbrauch aus der Box am Übergabeplatz der Station."""
        raise NotImplementedError("AP3 Schritt 7 (#28): Montage")

    def laufe(self) -> Ereignisprotokoll:
        """Startet die Prozesse und läuft bis zum Endkriterium oder zur maximalen Laufzeit."""
        raise NotImplementedError("AP3 Schritt 8: Simulationslauf")
