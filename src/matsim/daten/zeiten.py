"""Zeitansätze aus der Schritthistorie ``tblfinstep``.

Eine Zeitstempeldifferenz ist nicht automatisch reine Bearbeitungs- oder Fahrzeit. Jede hier
berechnete Dauer ist ein abgeleiteter Wert; Filter und Bedeutung stehen in
docs/projekt/datenmodell-mes.md.
"""

from __future__ import annotations

import json
import random
import sqlite3
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class Dauerstatistik:
    n_gesamt: int  # alle Schritte der Auswahl, vor dem Filter
    n: int  # Schritte nach dem Filter
    median: float
    mittel: float
    minimum: float
    maximum: float
    q10: float
    q90: float


def _sekunden(start: str, ende: str) -> float:
    return (datetime.strptime(ende, _FORMAT) - datetime.strptime(start, _FORMAT)).total_seconds()


def schrittdauern(verbindung: sqlite3.Connection, opno: int, resource_id: int) -> list[float]:
    """Dauern (Ende minus Start, in Sekunden) aller Schritte einer Operation an einer Ressource.

    Filter: Start und Ende vorhanden, ``ErrorRetVal = 0``.
    """
    zeilen = verbindung.execute(
        "SELECT Start, End FROM tblfinstep WHERE OpNo = ? AND ResourceID = ? "
        "AND Start IS NOT NULL AND End IS NOT NULL AND Start <> '' AND End <> '' "
        "AND ErrorRetVal = 0",
        (opno, resource_id),
    )
    return [_sekunden(start, ende) for start, ende in zeilen]


def statistik(verbindung: sqlite3.Connection, opno: int, resource_id: int) -> Dauerstatistik:
    """Lage- und Streuungsmaße der Schrittdauern (Median und Quantile statt nur Mittelwert)."""
    dauern = sorted(schrittdauern(verbindung, opno, resource_id))
    if not dauern:
        raise ValueError(f"Keine auswertbaren Schritte für OpNo {opno} an Ressource {resource_id}")
    gesamt = verbindung.execute(
        "SELECT COUNT(*) FROM tblfinstep WHERE OpNo = ? AND ResourceID = ?", (opno, resource_id)
    ).fetchone()[0]

    def quantil(p: float) -> float:
        return dauern[min(len(dauern) - 1, int(p * len(dauern)))]

    return Dauerstatistik(
        n_gesamt=gesamt,
        n=len(dauern),
        median=statistics.median(dauern),
        mittel=statistics.fmean(dauern),
        minimum=dauern[0],
        maximum=dauern[-1],
        q10=quantil(0.10),
        q90=quantil(0.90),
    )


def quartile(werte: list[float]) -> tuple[float, float]:
    """Unteres und oberes Quartil (Methode ``inclusive`` der Standardbibliothek)."""
    q1, _, q3 = statistics.quantiles(werte, n=4, method="inclusive")
    return q1, q3


def tukey_grenzen(werte: list[float], faktor: float = 3.0) -> tuple[float, float]:
    """Äußere Tukey-Grenzen ``Q1 - faktor * IQR`` und ``Q3 + faktor * IQR``.

    Mit ``faktor = 3`` („far out“) gelten nur deutlich abgesetzte Werte als Ausreißer. Sie werden
    als Störung gewertet (z. B. ein Pick mit 1051 s), nicht als normale Streuung.
    """
    q1, q3 = quartile(werte)
    iqr = q3 - q1
    return q1 - faktor * iqr, q3 + faktor * iqr


def _quantil(sortiert: list[float] | tuple[float, ...], p: float) -> float:
    return sortiert[min(len(sortiert) - 1, int(p * len(sortiert)))]


def _statistik(dauern: list[float], n_gesamt: int) -> Dauerstatistik:
    werte = sorted(dauern)
    return Dauerstatistik(
        n_gesamt=n_gesamt,
        n=len(werte),
        median=statistics.median(werte),
        mittel=statistics.fmean(werte),
        minimum=werte[0],
        maximum=werte[-1],
        q10=_quantil(werte, 0.10),
        q90=_quantil(werte, 0.90),
    )


# ---------------------------------------------------------------------------------------------
# Montagezeit je Teil
# ---------------------------------------------------------------------------------------------

#: Montagestation -> (OpNo, Nummer des Parameters mit der Teilenummer) laut tblstepparameterdef.
MONTAGE = {"RASS1": (323, 2, 3), "RASS2": (324, 4, 4), "RASS3": (325, 6, 3)}
#: Teile der Materialsätze des Standardprodukts WPNo 1000 je Station (B-04).
MATERIALSATZ_WPNO_1000 = {"RASS1": (800, 814), "RASS2": (813, 811), "RASS3": (831,)}


def montagedauern_je_teil(verbindung: sqlite3.Connection, station: str) -> dict[int, list[float]]:
    """Montagedauern einer Station getrennt nach Teil (gleicher Filter wie ``schrittdauern``).

    Die Montagezeit ist zweigipflig, weil das erste Teil eines Satzes (Mainboard, Analog-Platine)
    länger dauert als das zweite (Display, Gyroskop). Deshalb wird je Teil ausgewertet.
    """
    opno, resource_id, parameter_nr = MONTAGE[station]
    dauern: dict[int, list[float]] = {}
    for pno, start, ende in verbindung.execute(
        "SELECT CAST(p.Parameter AS INTEGER), s.Start, s.End FROM tblfinstep s "
        "JOIN tblfinstepparameter p ON p.ONo = s.ONo AND p.OPos = s.OPos AND p.StepNo = s.StepNo "
        "AND p.ParameterNo = ? WHERE s.OpNo = ? AND s.ResourceID = ? "
        "AND s.Start IS NOT NULL AND s.End IS NOT NULL AND s.Start <> '' AND s.End <> '' "
        "AND s.ErrorRetVal = 0",
        (parameter_nr, opno, resource_id),
    ):
        dauern.setdefault(pno, []).append(_sekunden(start, ende))
    return dauern


def montagestatistik_je_teil(
    verbindung: sqlite3.Connection, station: str
) -> dict[int, Dauerstatistik]:
    return {
        pno: _statistik(werte, len(werte))
        for pno, werte in sorted(montagedauern_je_teil(verbindung, station).items())
    }


def stationsbelegung(verbindung: sqlite3.Connection, station: str) -> list[float]:
    """Belegung einer Montagestation je Werkstück (WPNo 1000): erster Start bis letztes Ende.

    Enthält neben der Montage auch Abdeckung auflegen (OpNo 320), Einschalten und QR lesen
    (RASS1) und Ablegen auf das Band (OpNo 321). Werkstücke mit einem Fehlerschritt an der
    Station fließen nicht ein.
    """
    resource_id = MONTAGE[station][1]
    return [
        _sekunden(start, ende)
        for start, ende in verbindung.execute(
            "SELECT MIN(Start), MAX(End) FROM tblfinstep WHERE WPNo = 1000 AND ResourceID = ? "
            "AND Start IS NOT NULL AND End IS NOT NULL AND Start <> '' AND End <> '' "
            "GROUP BY ONo, OPos HAVING SUM(ErrorRetVal <> 0) = 0",
            (resource_id,),
        )
    ]


# ---------------------------------------------------------------------------------------------
# Kommissionierstation: laufen zwei Aufträge gleichzeitig?
# ---------------------------------------------------------------------------------------------


def kommissionier_ueberlappungen(verbindung: sqlite3.Connection) -> tuple[int, list[tuple]]:
    """Prüft, ob sich die Pick-Zeiträume zweier Kommissionieraufträge je überlappt haben.

    Zeitraum eines Auftrags = erster Pick-Start bis letztes Pick-Ende an Ressource 19. Liefert
    ``(Anzahl Aufträge, Liste überlappender Paare (ONo A, ONo B))``.
    """
    spannen = sorted(
        verbindung.execute(
            "SELECT MIN(Start), MAX(End), ONo FROM tblfinstep WHERE OpNo = 220 "
            "AND ResourceID = 19 AND Start <> '' AND End <> '' GROUP BY ONo"
        ).fetchall()
    )
    paare = []
    spaetestes_ende, auftrag = "", None
    for start, ende, ono in spannen:
        if start < spaetestes_ende:
            paare.append((auftrag, ono))
        if ende > spaetestes_ende:
            spaetestes_ende, auftrag = ende, ono
    return len(spannen), paare


# ---------------------------------------------------------------------------------------------
# Fahrzeuge: Statusmeldungen der Robotinos (tblmachinereport)
# ---------------------------------------------------------------------------------------------

#: Robotinos für Boxen (tblresource 20 bis 25, LOG-MR-B).
ROBOTINOS = tuple(range(20, 26))


def fahrzeugabschnitte(
    verbindung: sqlite3.Connection, resource_id: int
) -> list[tuple[datetime, datetime]]:
    """Zeiträume mit ``Busy = 1`` eines Robotinos aus ``tblmachinereport``.

    Jeder Abschnitt ist ein Fahr- oder Übergabekommando. Zwischen zwei Kommandos desselben
    Fahrauftrags meldet das Fahrzeug etwa 3 s ``Busy = 0``. Ort und Box stehen nicht in der
    Meldung.
    """
    abschnitte = []
    beginn = None
    for zeit, busy in verbindung.execute(
        "SELECT TimeStamp, Busy FROM tblmachinereport WHERE ResourceID = ? ORDER BY TimeStamp, ID",
        (resource_id,),
    ):
        zeitpunkt = datetime.strptime(zeit, _FORMAT)
        if busy == 1 and beginn is None:
            beginn = zeitpunkt
        elif busy == 0 and beginn is not None:
            abschnitte.append((beginn, zeitpunkt))
            beginn = None
    return abschnitte


def aktive_fahrzeuge_je_tag(verbindung: sqlite3.Connection) -> dict[str, list[int]]:
    """Robotinos mit mindestens einem ``Busy``-Abschnitt je Tag, an dem Boxen abgeliefert wurden."""
    tage = {
        tag
        for (tag,) in verbindung.execute(
            "SELECT DISTINCT substr(Start, 1, 10) FROM tblfinstep WHERE OpNo = 215 AND Start <> ''"
        )
    }
    aktiv: dict[str, set[int]] = {tag: set() for tag in tage}
    for robotino in ROBOTINOS:
        for beginn, _ in fahrzeugabschnitte(verbindung, robotino):
            tag = beginn.strftime("%Y-%m-%d")
            if tag in aktiv:
                aktiv[tag].add(robotino)
    return {tag: sorted(fahrzeuge) for tag, fahrzeuge in sorted(aktiv.items())}


def max_gleichzeitig_aktiv(verbindung: sqlite3.Connection, tag: str) -> int:
    """Größte Zahl gleichzeitig beschäftigter Robotinos an einem Tag."""
    wechsel = []
    for robotino in ROBOTINOS:
        for beginn, ende in fahrzeugabschnitte(verbindung, robotino):
            if beginn.strftime("%Y-%m-%d") == tag:
                wechsel += [(beginn, 1), (ende, -1)]
    aktuell = hoechstens = 0
    for _, delta in sorted(wechsel, key=lambda w: (w[0], w[1])):
        aktuell += delta
        hoechstens = max(hoechstens, aktuell)
    return hoechstens


@dataclass(frozen=True)
class Transportzerlegung:
    """Zerlegung „Ende letzter Pick bis Ablieferung“ einer Zielbox (B-14)."""

    ono: int
    station: int
    fahrzeug: int
    warten_s: float  # Ende letzter Pick bis Beginn des Fahrauftrags
    fahrauftrag_s: float  # Aufnahme an der Kommissionierung, Fahrt, Übergabe bis OpNo-215-Start
    gesamt_s: float


def transportzerlegung(
    verbindung: sqlite3.Connection,
) -> tuple[list[Transportzerlegung], int]:
    """Ordnet jeder Ablieferung (OpNo 215) einen Fahrauftrag eines Robotinos zu.

    Regel: Unter den ``Busy``-Abschnitten, die vor dem Ablieferstart beginnen und höchstens 5 s
    davor bis 40 s danach enden, wird einer gewählt, der den Ablieferstart enthält;
    gibt es keinen, der mit dem nächstgelegenen Ende. Von dort werden direkt vorausgehende
    Abschnitte desselben Fahrzeugs (Lücke höchstens 6 s, Beginn nicht vor dem letzten Pick)
    zum Fahrauftrag zusammengefasst. Die Zuordnung ist eine Heuristik: Die Meldungen enthalten
    weder Ort noch Box. Liefert ``(Zerlegungen, Anzahl nicht zuordenbarer Ablieferungen)``.
    """
    from matsim.daten.materialpfad import ablieferungen

    abschnitte = {r: fahrzeugabschnitte(verbindung, r) for r in ROBOTINOS}
    ergebnis = []
    ohne = 0
    for a in ablieferungen(verbindung):
        if a.letzter_pick is None:
            continue
        t = a.start
        kandidaten = []
        for robotino, liste in abschnitte.items():
            for i, (beginn, ende) in enumerate(liste):
                versatz = (ende - t).total_seconds()
                if beginn < t and -5 <= versatz <= 40:
                    enthaelt = beginn <= t <= ende
                    kandidaten.append((not enthaelt, abs(versatz), robotino, i))
        if not kandidaten:
            ohne += 1
            continue
        _, _, robotino, i = min(kandidaten)
        liste = abschnitte[robotino]
        beginn = liste[i][0]
        while (
            i > 0
            and (beginn - liste[i - 1][1]).total_seconds() <= 6
            and (liste[i - 1][0] - a.letzter_pick).total_seconds() >= -5
        ):
            i -= 1
            beginn = liste[i][0]
        warten = (beginn - a.letzter_pick).total_seconds()
        if warten < 0:
            ohne += 1
            continue
        ergebnis.append(
            Transportzerlegung(
                ono=a.ono,
                station=a.station,
                fahrzeug=robotino,
                warten_s=warten,
                fahrauftrag_s=(t - beginn).total_seconds(),
                gesamt_s=(t - a.letzter_pick).total_seconds(),
            )
        )
    return ergebnis, ohne


def vollstaendige_fahrauftraege(verbindung: sqlite3.Connection) -> list[float]:
    """Fahrauftragsdauern ohne unvollständig erkannte Ketten.

    Pausiert ein Fahrzeug länger als 6 s, bricht die Verkettung in :func:`transportzerlegung` ab
    und der Fahrauftrag erscheint zu kurz (bis hinunter zu 2 s). Werte unter dem halben Median
    werden deshalb nicht als Fahrzeit gewertet. Zum Vergleich: Am 09.11.2026 dauerten Fahrt und
    Übergabe allein 78 s (Robotino 25, Auftrag 9177).
    """
    dauern = [z.fahrauftrag_s for z in transportzerlegung(verbindung)[0]]
    grenze = statistics.median(dauern) / 2
    return [d for d in dauern if d >= grenze]


def hintransportdauern(verbindung: sqlite3.Connection) -> list[float]:
    """Ende letzter Pick bis Ende des ersten Ablieferschritts (OpNo 215) je Auftrag (B-14)."""
    from matsim.daten.materialpfad import ablieferungen

    return [
        (a.erstes_ende - a.letzter_pick).total_seconds()
        for a in ablieferungen(verbindung)
        if a.letzter_pick is not None
    ]


# ---------------------------------------------------------------------------------------------
# Werkstückumlauf: Bandsegmente zwischen benachbarten Stationen
# ---------------------------------------------------------------------------------------------

#: Benachbarte Stationen der inneren Schleife ohne Materialabhängigkeit an der Folgestation.
FREIE_BANDSEGMENTE = ((2, 3), (4, 5), (6, 7))


def bandsegmentdauern(verbindung: sqlite3.Connection) -> list[float]:
    """Ende eines Schritts bis Start des nächsten Schritts desselben Werkstücks an der Folgestation.

    Nur für Segmente, deren Folgestation kein Material braucht (RASS1 → Messen, RASS2 → Kamera,
    RASS3 → Funktionstest). Dort enthält die Zeitspanne kein Warten auf Material.
    """
    zeilen = verbindung.execute(
        "SELECT ONo, OPos, ResourceID, Start, End FROM tblfinstep WHERE WPNo >= 1000 "
        "AND Start <> '' AND End <> '' AND Start IS NOT NULL AND End IS NOT NULL "
        "AND ErrorRetVal = 0 ORDER BY ONo, OPos, Start"
    ).fetchall()
    dauern = []
    for vorher, nachher in zip(zeilen, zeilen[1:], strict=False):
        if vorher[:2] == nachher[:2] and (vorher[2], nachher[2]) in FREIE_BANDSEGMENTE:
            dauern.append(_sekunden(vorher[4], nachher[3]))
    return dauern


# ---------------------------------------------------------------------------------------------
# Verteilungen für das Unsicherheitsszenario
# ---------------------------------------------------------------------------------------------

VERTEILUNGSDATEI = "zeitverteilungen.json"


@dataclass(frozen=True)
class Zeitverteilung:
    """Empirische Verteilung einer Dauer nach Entfernen der Störungen.

    Gezogen wird mit Zurücklegen aus der bereinigten Stichprobe (empirische Verteilung). So muss
    keine Verteilungsfamilie unterstellt werden, und die Zweigipfligkeit oder Schiefe der Daten
    bleibt erhalten. Störungen (Stillstand, Eingriff; Regel in :func:`stoerungsgrenzen`) werden
    entfernt, weil Störungen nicht Teil des Modells sind.
    """

    name: str
    quelle: str
    werte: tuple[float, ...]  # bereinigt, aufsteigend sortiert
    n_roh: int
    untere_grenze: float
    obere_grenze: float

    @property
    def entfernt(self) -> int:
        return self.n_roh - len(self.werte)

    @property
    def median(self) -> float:
        return statistics.median(self.werte)

    @property
    def q10(self) -> float:
        return _quantil(self.werte, 0.10)

    @property
    def q90(self) -> float:
        return _quantil(self.werte, 0.90)

    def ziehe(self, rng: random.Random) -> float:
        """Eine Dauer in Sekunden; ``rng`` ist der Zufallsgenerator der Replikation."""
        return rng.choice(self.werte)

    def als_dict(self) -> dict:
        return {
            "quelle": self.quelle,
            "n_roh": self.n_roh,
            "untere_grenze": self.untere_grenze,
            "obere_grenze": self.obere_grenze,
            "werte": list(self.werte),
        }


def stoerungsgrenzen(dauern: list[float]) -> tuple[float, float]:
    """Grenzen, außerhalb derer eine Dauer als Störung gilt.

    Eine Dauer ist eine Störung, wenn sie außerhalb der äußeren Tukey-Grenzen liegt **und** mehr
    als doppelt so lang bzw. weniger als halb so lang wie der Median ist. Die zweite Bedingung
    verhindert, dass bei sehr engen Verteilungen (z. B. Gyroskop: Q1 = Q3 = 25 s) schon eine
    Sekunde Abweichung als Störung zählt.
    """
    unten, oben = tukey_grenzen(dauern)
    median = statistics.median(dauern)
    return min(unten, median / 2), max(oben, 2 * median)


def bereinige(name: str, quelle: str, dauern: list[float]) -> Zeitverteilung:
    """Entfernt Störungen (:func:`stoerungsgrenzen`) und legt die Verteilung an."""
    unten, oben = stoerungsgrenzen(dauern)
    behalten = tuple(sorted(d for d in dauern if unten <= d <= oben))
    return Zeitverteilung(name, quelle, behalten, len(dauern), unten, oben)


def zeitverteilung(
    verbindung: sqlite3.Connection, opno: int, resource_id: int, name: str | None = None
) -> Zeitverteilung:
    """Verteilung der Schrittdauern einer Operation an einer Ressource (Filter wie B-13)."""
    return bereinige(
        name or f"OpNo {opno} an Ressource {resource_id}",
        f"tblfinstep OpNo {opno}, ResourceID {resource_id}; Start und Ende vorhanden, "
        "ErrorRetVal = 0",
        schrittdauern(verbindung, opno, resource_id),
    )


def leite_verteilungen_ab(verbindung: sqlite3.Connection) -> dict[str, Zeitverteilung]:
    """Alle Verteilungen, benannt nach dem Parameterpfad in ``config/anlage.yaml``."""
    verteilungen = {
        "kommissionierplatz.pickzeit_je_teil_s": zeitverteilung(
            verbindung, 220, 19, "kommissionierplatz.pickzeit_je_teil_s"
        ),
        "werkstueckumlauf.auslagern_s": zeitverteilung(
            verbindung, 212, 1, "werkstueckumlauf.auslagern_s"
        ),
        "werkstueckumlauf.einlagern_s": zeitverteilung(
            verbindung, 211, 1, "werkstueckumlauf.einlagern_s"
        ),
        "fahrzeuge.hintransport_s": bereinige(
            "fahrzeuge.hintransport_s",
            "Ende letzter Pick bis Ende OpNo 215 je Kommissionierauftrag (B-14)",
            hintransportdauern(verbindung),
        ),
        "fahrzeuge.fahrauftrag_s": bereinige(
            "fahrzeuge.fahrauftrag_s",
            "tblmachinereport: Busy-Abschnitte des zugeordneten Robotinos bis Ablieferstart "
            "(B-22, Heuristik transportzerlegung); ohne unvollständig erkannte Ketten",
            vollstaendige_fahrauftraege(verbindung),
        ),
        "werkstueckumlauf.bandsegment_s": bereinige(
            "werkstueckumlauf.bandsegment_s",
            "tblfinstep: Ende Schritt an 2/4/6 bis Start Schritt an 3/5/7 desselben Werkstücks",
            bandsegmentdauern(verbindung),
        ),
    }
    for station, teile in MATERIALSATZ_WPNO_1000.items():
        name = f"stationen.{station}.belegung_je_werkstueck_s"
        verteilungen[name] = bereinige(
            name,
            f"tblfinstep WPNo 1000 an Ressource {MONTAGE[station][1]}: erster Start bis letztes "
            "Ende je Werkstück, ohne Fehlerschritte",
            stationsbelegung(verbindung, station),
        )
        dauern_je_teil = montagedauern_je_teil(verbindung, station)
        for pno in teile:
            dauern = dauern_je_teil[pno]
            name = f"stationen.{station}.montagezeit_s.{pno}"
            opno = MONTAGE[station][0]
            verteilungen[name] = bereinige(
                name, f"tblfinstep OpNo {opno}, Teil {pno}; Filter wie B-13", dauern
            )
    return verteilungen


def speichere_verteilungen(verteilungen: dict[str, Zeitverteilung], pfad: Path) -> None:
    daten = {name: v.als_dict() for name, v in sorted(verteilungen.items())}
    text = json.dumps(daten, ensure_ascii=False, indent=1) + "\n"
    pfad.write_text(text, encoding="utf-8", newline="\n")


def lade_verteilungen(pfad: Path | None = None) -> dict[str, Zeitverteilung]:
    """Lädt die versionierten Verteilungen aus ``data/processed/`` (ohne Dumps nutzbar).

    Beispiel für die Simulation::

        rng = random.Random(seed)
        pick = lade_verteilungen()["kommissionierplatz.pickzeit_je_teil_s"].ziehe(rng)
    """
    if pfad is None:
        from matsim.pfade import PROCESSED

        pfad = PROCESSED / VERTEILUNGSDATEI
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    return {
        name: Zeitverteilung(
            name,
            eintrag["quelle"],
            tuple(eintrag["werte"]),
            eintrag["n_roh"],
            eintrag["untere_grenze"],
            eintrag["obere_grenze"],
        )
        for name, eintrag in daten.items()
    }


def verteilung(name: str) -> Zeitverteilung:
    """Eine Verteilung nach Parameterpfad, z. B. ``"fahrzeuge.fahrauftrag_s"``."""
    verteilungen = lade_verteilungen()
    if name not in verteilungen:
        raise KeyError(f"Keine Verteilung für {name}; vorhanden: {', '.join(sorted(verteilungen))}")
    return verteilungen[name]
