"""Wiederholbare Datenqualitätsprüfungen zum Befundregister (docs/projekt/datenmodell-mes.md).

Jede Prüfung liest einen importierten Snapshot und liefert ein :class:`Pruefergebnis` mit
Prüfumfang (``geprueft``), Anzahl auffälliger Datensätze (``auffaellig``) und einem Beispiel.
Was „auffällig“ bedeutet, steht im Text der Prüfung. Die Rohdaten werden nicht verändert.

Aufruf: ``python -m matsim.daten qualitaet [SNAPSHOT]`` (Standard: 2026-11-09_1557).
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass

from matsim.daten import bestand, materialpfad, zeiten

#: Teilegruppen je Station laut tblpnogroup (5 = RASS1, 6 = RASS2, 12 = RASS3).
STATIONSGRUPPE = {2: 5, 4: 6, 6: 12}
#: Zeitansätze, die in config/anlage.yaml stehen: (OpNo, ResourceID).
ZEITVORGAENGE = ((220, 19), (323, 2), (324, 4), (325, 6), (212, 1), (211, 1))
_MIT_ZEITEN = "Start IS NOT NULL AND Start <> '' AND End IS NOT NULL AND End <> ''"


@dataclass(frozen=True)
class Pruefergebnis:
    nr: str
    titel: str
    pruefung: str  # was als auffällig gilt
    geprueft: int
    auffaellig: int
    beispiel: str

    @property
    def anteil(self) -> float:
        return self.auffaellig / self.geprueft if self.geprueft else 0.0


Pruefung = Callable[[sqlite3.Connection], Pruefergebnis]
PRUEFUNGEN: dict[str, Pruefung] = {}


def _pruefung(nr: str) -> Callable[[Pruefung], Pruefung]:
    def registriere(funktion: Pruefung) -> Pruefung:
        PRUEFUNGEN[nr] = funktion
        return funktion

    return registriere


def _eins(v: sqlite3.Connection, sql: str, parameter: tuple = ()) -> int:
    return v.execute(sql, parameter).fetchone()[0]


@_pruefung("B-01")
def b01_ressourcen(v: sqlite3.Connection) -> Pruefergebnis:
    geprueft = _eins(v, "SELECT COUNT(*) FROM tblfinstep")
    fehlend = v.execute(
        "SELECT ONo, OPos, StepNo, ResourceID FROM tblfinstep "
        "WHERE ResourceID NOT IN (SELECT ResourceID FROM tblresource)"
    ).fetchall()
    zusatz = v.execute(
        "SELECT ResourceID FROM tblresource WHERE ResourceID IN (8, 9, 10, 12, 13, 16, 18)"
    ).fetchall()
    return Pruefergebnis(
        "B-01",
        "Ressourcen der Schritthistorie in tblresource",
        "Schritt verweist auf eine ResourceID, die tblresource nicht kennt",
        geprueft,
        len(fehlend),
        str(fehlend[0]) if fehlend else f"keiner; zusätzliche Ressourcen {[r for (r,) in zusatz]}",
    )


@_pruefung("B-02")
def b02_topologie(v: sqlite3.Connection) -> Pruefergebnis:
    kanten = v.execute(
        "SELECT SourceId, TargetId FROM tbltopology WHERE SourceId > 0 OR TargetId > 0"
    ).fetchall()
    ausgang = Counter(quelle for quelle, _ in kanten)
    verzweigt = sorted((q, n) for q, n in ausgang.items() if n > 1)
    return Pruefergebnis(
        "B-02",
        "Bandtopologie",
        "Kante beginnt an einem Knoten mit mehr als einem Ausgang (Weiche)",
        len(kanten),
        sum(n for _, n in verzweigt),
        "Ausgänge je Weiche: " + ", ".join(f"{q}: {n}" for q, n in verzweigt),
    )


@_pruefung("B-03")
def b03_boxplaetze(v: sqlite3.Connection) -> Pruefergebnis:
    soll = _eins(v, "SELECT PosCount FROM tblboxdef")
    abweichend = v.execute(
        "SELECT BoxID, (SELECT COUNT(*) FROM tblboxpos p WHERE p.BoxId = b.BoxID) AS n "
        "FROM tblbox b WHERE n <> ?",
        (soll,),
    ).fetchall()
    return Pruefergebnis(
        "B-03",
        "Plätze je Box",
        f"Box hat in tblboxpos nicht genau {soll} Plätze (tblboxdef.PosCount)",
        _eins(v, "SELECT COUNT(*) FROM tblbox"),
        len(abweichend),
        str(abweichend[0])
        if abweichend
        else f"keine; tblboxpos hat {_eins(v, 'SELECT COUNT(*) FROM tblboxpos')} Zeilen",
    )


@_pruefung("B-04")
def b04_stueckliste(v: sqlite3.Connection) -> Pruefergebnis:
    schritte = v.execute(
        "SELECT d.StepNo, d.OpNo, d.ResourceID, p.Parameter FROM tblstepdef d "
        "JOIN tblstepparameterdef p ON p.WPNo = d.WPNo AND p.StepNo = d.StepNo "
        "AND p.ParameterNo = CASE d.OpNo WHEN 324 THEN 4 ELSE 3 END "
        "WHERE d.WPNo = 1000 AND d.OpNo IN (323, 324, 325) ORDER BY d.StepNo"
    ).fetchall()
    gruppen = {(gid, pno) for gid, pno in v.execute("SELECT Id, PNo FROM tblpnogroup").fetchall()}
    falsch = [s for s in schritte if (STATIONSGRUPPE[s[2]], int(s[3])) not in gruppen]
    return Pruefergebnis(
        "B-04",
        "Stückliste WPNo 1000",
        "Montageschritt verlangt ein Teil außerhalb der Materialgruppe seiner Station",
        len(schritte),
        len(falsch),
        "; ".join(f"Schritt {s} an {r}: {p}" for s, _, r, p in schritte),
    )


@_pruefung("B-05")
def b05_zonen(v: sqlite3.Connection) -> Pruefergebnis:
    plaetze = v.execute(
        "SELECT ResourceId, BufPos, Zone FROM tblbufferpos "
        "WHERE ResourceId IN (2, 4, 6) AND BufNo = 1 ORDER BY ResourceId, BufPos"
    ).fetchall()
    abweichend = [p for p in plaetze if p[2] != STATIONSGRUPPE[p[0]]]
    boxgruppen = Counter(g for (g,) in v.execute("SELECT PNoGroup FROM tblboxpos"))
    return Pruefergebnis(
        "B-05",
        "Zonen der Box-Pufferplätze an RASS1 bis RASS3",
        "Zone des Pufferplatzes ist nicht die Materialgruppe der Station",
        len(plaetze),
        len(abweichend),
        f"Zonen {sorted({p[2] for p in plaetze})}; PNoGroup der Boxplätze {dict(boxgruppen)}",
    )


@_pruefung("B-06")
def b06_kommissionierplaene(v: sqlite3.Connection) -> Pruefergebnis:
    picks = v.execute(
        "SELECT ONo, OPos, ResourceID FROM tblfinstep WHERE WPNo IN (1, 2, 3) AND StepNo = 10"
    ).fetchall()
    lieferungen = v.execute(
        "SELECT ONo, OPos, WPNo, ResourceID FROM tblfinstep WHERE WPNo IN (1, 2, 3) AND StepNo = 20"
    ).fetchall()
    falsch = [p for p in picks if p[2] != 19] + [
        lf for lf in lieferungen if lf[3] != materialpfad.ZIELSTATION[lf[2]]
    ]
    return Pruefergebnis(
        "B-06",
        "Kommissionier-Arbeitspläne",
        "Pick nicht an Ressource 19 oder Ablieferung nicht an der Station des Arbeitsplans",
        len(picks) + len(lieferungen),
        len(falsch),
        str(falsch[0])
        if falsch
        else f"keiner; {len(picks)} Picks, {len(lieferungen)} Ablieferungen",
    )


@_pruefung("B-07")
def b07_montage_ohne_pick(v: sqlite3.Connection) -> Pruefergebnis:
    geprueft, ohne = materialpfad.montage_ohne_umsetzung(v)
    return Pruefergebnis(
        "B-07",
        "Montage mit nachweisbarem Materialpfad",
        "Montageschritt ohne Pick, der für genau diesen Auftrag und Schritt umgesetzt hat",
        geprueft,
        len(ohne),
        str(ohne[0]) if ohne else "keiner",
    )


@_pruefung("B-08")
def b08_ablauf_0911(v: sqlite3.Connection) -> Pruefergebnis:
    positionen = v.execute(
        "SELECT ONo, OPos, Start, End, State FROM tblfinorderpos "
        "WHERE ONo BETWEEN 9176 AND 9180 ORDER BY ONo, OPos"
    ).fetchall()
    auffaellig = [p for p in positionen if not p[2] or not p[3] or p[4] != 100]
    reihenfolge = v.execute(
        "SELECT ONo || '/' || OPos FROM tblfinstep WHERE ONo BETWEEN 9176 AND 9180 "
        "AND OpNo = 320 AND ResourceID = 2 ORDER BY Start"
    ).fetchall()
    return Pruefergebnis(
        "B-08",
        "Ablauf vom 09.11.2026 (ONo 9176 bis 9180)",
        "Position ohne Start, ohne Ende oder nicht im Zustand 100",
        len(positionen),
        len(auffaellig),
        "Reihenfolge an RASS1: " + ", ".join(r for (r,) in reihenfolge),
    )


@_pruefung("B-09")
def b09_verortete_boxen(v: sqlite3.Connection) -> Pruefergebnis:
    alle = [b for (b,) in v.execute("SELECT BoxID FROM tblbox ORDER BY BoxID")]
    verortet = set(bestand.boxstandorte(v))
    ohne = [b for b in alle if b not in verortet]
    return Pruefergebnis(
        "B-09",
        "Boxen mit bekanntem Ort",
        "Box aus tblbox steht auf keinem Pufferplatz (tblbufferpos)",
        len(alle),
        len(ohne),
        f"ohne Ort: {ohne}",
    )


@_pruefung("B-10")
def b10_teile_ohne_ort(v: sqlite3.Connection) -> Pruefergebnis:
    verortet = set(bestand.boxstandorte(v))
    teile = v.execute("SELECT BoxId, PNo FROM tblboxpos WHERE PNo > 0").fetchall()
    ohne = Counter(pno for box, pno in teile if box not in verortet)
    boxen = sorted({box for box, _ in teile if box not in verortet})
    return Pruefergebnis(
        "B-10",
        "Teile in Boxen ohne Ort",
        "Teil liegt in einer Box, die auf keinem Pufferplatz steht",
        len(teile),
        sum(ohne.values()),
        f"Boxen {boxen}; je Teil {dict(sorted(ohne.items()))}",
    )


@_pruefung("B-11")
def b11_doppelt_verortet(v: sqlite3.Connection) -> Pruefergebnis:
    doppelt = {}
    for box, orte in bestand.boxstandorte(v).items():
        if len(orte) > 1:
            doppelt[box] = v.execute(
                "SELECT ResourceId, BufNo, BufPos, TimeStamp FROM tblbufferpos WHERE BoxID = ? "
                "ORDER BY TimeStamp",
                (box,),
            ).fetchall()
    return Pruefergebnis(
        "B-11",
        "Boxen an mehr als einem Ort",
        "verortete Box steht auf mehr als einem Pufferplatz",
        len(bestand.boxstandorte(v)),
        len(doppelt),
        str(doppelt) if doppelt else "keine",
    )


@_pruefung("B-12")
def b12_bindungen_ohne_auftrag(v: sqlite3.Connection) -> Pruefergebnis:
    zeilen = (
        _eins(v, "SELECT COUNT(*) FROM tblstepparameter")
        + _eins(v, "SELECT COUNT(*) FROM tblboxpos WHERE ONo <> 0")
        + _eins(v, "SELECT COUNT(*) FROM tblbufferpos WHERE ONo <> 0 OR Booked = 1")
        + _eins(v, "SELECT COUNT(*) FROM tblcarrier WHERE ONo <> 0")
    )
    ohne = bestand.reservierungen_ohne_auftrag(v)
    gebucht = v.execute(
        "SELECT ResourceId, BufNo, BufPos, TimeStamp FROM tblbufferpos "
        "WHERE Booked = 1 AND ONo = 0 ORDER BY TimeStamp"
    ).fetchall()
    return Pruefergebnis(
        "B-12",
        "Bindungen ohne laufenden Auftrag",
        "Reservierung oder Buchung ohne zugehörigen Auftrag in tblorder",
        zeilen,
        sum(ohne.values()) + len(gebucht),
        f"{ohne}; gebucht ohne Auftrag: {gebucht}",
    )


@_pruefung("B-13")
def b13_zeitfilter(v: sqlite3.Connection) -> Pruefergebnis:
    gesamt = verworfen = 0
    teile = []
    for opno, resource in ZEITVORGAENGE:
        s = zeiten.statistik(v, opno, resource)
        gesamt += s.n_gesamt
        verworfen += s.n_gesamt - s.n
        teile.append(f"{opno}: {s.n_gesamt - s.n}")
    return Pruefergebnis(
        "B-13",
        "Filter der Zeitansätze",
        "Schritt ohne Start oder Ende oder mit ErrorRetVal <> 0 (fließt nicht in die Zeit ein)",
        gesamt,
        verworfen,
        "verworfen je OpNo: " + ", ".join(teile),
    )


@_pruefung("B-14")
def b14_transportzeit(v: sqlite3.Connection) -> Pruefergebnis:
    dauern = zeiten.hintransportdauern(v)
    _, oben = zeiten.tukey_grenzen(dauern)
    ausreisser = sorted(d for d in dauern if d > oben)
    return Pruefergebnis(
        "B-14",
        "Ende letzter Pick bis Ende Ablieferung",
        f"Dauer über der äußeren Tukey-Grenze Q3 + 3 IQR = {oben:.0f} s",
        len(dauern),
        len(ausreisser),
        f"größte Werte {ausreisser[-3:]} s" if ausreisser else "keiner",
    )


@_pruefung("B-15")
def b15_buendelung(v: sqlite3.Connection) -> Pruefergebnis:
    auftraege = v.execute(
        "SELECT ONo, WPNo, COUNT(*) FROM tblfinorderpos WHERE WPNo IN (1, 2, 3) GROUP BY ONo"
    ).fetchall()
    ungerade = [a for a in auftraege if a[1] in (1, 2) and a[2] % 2]
    zu_gross = [a for a in auftraege if a[2] > 8]
    return Pruefergebnis(
        "B-15",
        "Positionen je Kommissionierauftrag",
        "Auftrag für RASS1/RASS2 mit ungerader Teilezahl oder mehr als 8 Teile je Box",
        len(auftraege),
        len(ungerade) + len(zu_gross),
        f"ungerade: {len(ungerade)}, z. B. {ungerade[:2]}; über 8: {len(zu_gross)}",
    )


@_pruefung("B-16")
def b16_fehlende_zeiten(v: sqlite3.Connection) -> Pruefergebnis:
    schritte = _eins(v, "SELECT COUNT(*) FROM tblfinstep")
    ohne = _eins(
        v,
        "SELECT COUNT(*) FROM tblfinstep WHERE (Start IS NULL OR Start = '') "
        "AND (End IS NULL OR End = '')",
    )
    fehler = _eins(v, "SELECT COUNT(*) FROM tblfinstep WHERE ErrorRetVal <> 0")
    pos_ohne = _eins(v, "SELECT COUNT(*) FROM tblfinorderpos WHERE Start IS NULL OR Start = ''")
    pos = _eins(v, "SELECT COUNT(*) FROM tblfinorderpos")
    return Pruefergebnis(
        "B-16",
        "Fehlende Zeitstempel und Fehlercodes",
        "Schritt ohne Start und Ende",
        schritte,
        ohne,
        f"zusätzlich {fehler} Schritte mit ErrorRetVal <> 0; {pos_ohne} von {pos} Positionen "
        "ohne Start",
    )


@_pruefung("B-17")
def b17_ungepflegt(v: sqlite3.Connection) -> Pruefergebnis:
    boxen = _eins(v, "SELECT COUNT(*) FROM tblbox")
    leer = _eins(v, "SELECT COUNT(*) FROM tblbox WHERE ONo = 0 AND Full = 0")
    teile = _eins(v, "SELECT COUNT(*) FROM tblparts WHERE SafetyStock = 0 AND LotSize = 0")
    return Pruefergebnis(
        "B-17",
        "Nicht gepflegte Felder",
        "tblbox.ONo und tblbox.Full sind 0, obwohl Boxen belegt und reserviert sind",
        boxen,
        leer,
        f"tblparts ohne SafetyStock und LotSize: {teile}; tblautomaticorder: "
        f"{_eins(v, 'SELECT COUNT(*) FROM tblautomaticorder')} Zeilen",
    )


@_pruefung("B-18")
def b18_plan_ist(v: sqlite3.Connection) -> Pruefergebnis:
    vergleich = []
    for opno, resource in ZEITVORGAENGE[:4]:
        plan = _eins(
            v,
            "SELECT WorkingTime FROM tblresourceoperation WHERE OpNo = ? AND ResourceID = ?",
            (opno, resource),
        )
        vergleich.append((opno, plan, zeiten.statistik(v, opno, resource).median))
    abweichend = [x for x in vergleich if abs(x[2] - x[1]) > 0.2 * x[1]]
    return Pruefergebnis(
        "B-18",
        "Planzeit gegen Istzeit",
        "Median der Istzeit weicht mehr als 20 % von tblresourceoperation.WorkingTime ab",
        len(vergleich),
        len(abweichend),
        "; ".join(f"OpNo {o}: Plan {p} s, Ist {i:g} s" for o, p, i in vergleich),
    )


@_pruefung("B-19")
def b19_montageprioritaet(v: sqlite3.Connection) -> Pruefergebnis:
    sql = v.execute("SELECT SqlString FROM tblsqlquery WHERE MClass = 100 AND MNo = 1").fetchone()
    text = (sql[0] if sql else "") or ""
    reihenfolge = text[text.upper().rfind("ORDER BY") :].split(";")[0].strip()
    return Pruefergebnis(
        "B-19",
        "Montagepriorität im MES (tblsqlquery 100/1)",
        "Auswahlabfrage ohne feste Sortierung",
        1,
        0 if "ORDER BY" in text.upper() else 1,
        " ".join(reihenfolge.split()),
    )


@_pruefung("B-20")
def b20_pick_ohne_produktionsposition(v: sqlite3.Connection) -> Pruefergebnis:
    alle = materialpfad.umsetzungen(v)
    ohne = materialpfad.umsetzungen_ohne_produktionsposition(v)
    auftraege = sorted({u.prod_ono for u in ohne})
    return Pruefergebnis(
        "B-20",
        "Picks mit Produktionsbezug in der Historie",
        "Pick für einen Produktionsauftrag, dessen Position in tblfinorderpos fehlt",
        len(alle),
        len(ohne),
        f"{len(auftraege)} Produktionsaufträge, z. B. {auftraege[:5]}",
    )


@_pruefung("B-21")
def b21_boxen_ohne_ort_genutzt(v: sqlite3.Connection) -> Pruefergebnis:
    ohne_ort = bestand.startbestand(v).boxen_ohne_ort
    letzte = bestand.letzte_kommissionierung_je_box(v)
    tag = materialpfad.exportzeit(v).strftime("%Y-%m-%d")
    am_tag = [b for b in ohne_ort if (letzte[b] or "") >= tag]
    nie = [b for b in ohne_ort if letzte[b] is None]
    juengste = max((letzte[b] for b in ohne_ort if letzte[b]), default=None)
    return Pruefergebnis(
        "B-21",
        "Nutzung der Boxen ohne Ort",
        "Box ohne Ort war am Tag des Snapshots Quell- oder Zielbox eines Picks",
        len(ohne_ort),
        len(am_tag),
        f"nie kommissioniert: {nie}; jüngste Nutzung: {juengste}",
    )


@_pruefung("B-22")
def b22_fahrzeugzuordnung(v: sqlite3.Connection) -> Pruefergebnis:
    zerlegt, ohne = zeiten.transportzerlegung(v)
    tag = materialpfad.exportzeit(v).strftime("%Y-%m-%d")
    aktiv = zeiten.aktive_fahrzeuge_je_tag(v).get(tag, [])
    return Pruefergebnis(
        "B-22",
        "Zuordnung der Ablieferungen zu Robotino-Fahraufträgen (tblmachinereport)",
        "Ablieferung ohne eindeutig zuordenbaren Busy-Abschnitt eines Robotinos",
        len(zerlegt) + ohne,
        ohne,
        f"am {tag} aktiv: Robotinos {aktiv}, höchstens "
        f"{zeiten.max_gleichzeitig_aktiv(v, tag)} gleichzeitig beschäftigt",
    )


@_pruefung("B-23")
def b23_gemischte_zielboxen(v: sqlite3.Connection) -> Pruefergebnis:
    nutzungen, paare = materialpfad.gemischte_zielboxen(v)
    stationen = [(a, b) for a, b in paare if a.wpno != b.wpno]
    return Pruefergebnis(
        "B-23",
        "Gemischte Zielboxen",
        "Zielbox trägt zur selben Zeit Teile zweier Kommissionieraufträge",
        nutzungen,
        len(paare),
        f"davon für verschiedene Stationen: {len(stationen)}; "
        f"Zielboxen je Kommissionierauftrag: genau 1",
    )


@_pruefung("B-24")
def b24_satzvollstaendigkeit(v: sqlite3.Connection) -> Pruefergebnis:
    klassen = materialpfad.satzpruefung(v)
    geprueft = sum(len(liste) for liste in klassen.values())
    return Pruefergebnis(
        "B-24",
        "Vollständige Sätze in einer Box (WPNo 1000)",
        "Satz geteilt auf mehrere Boxen, unvollständig kommissioniert oder ohne Pick",
        geprueft,
        geprueft - len(klassen["vollstaendig"]),
        ", ".join(f"{k}: {len(liste)}" for k, liste in klassen.items())
        + f"; ohne Pick: {klassen['ohne_pick']}",
    )


def pruefe_alle(verbindung: sqlite3.Connection) -> list[Pruefergebnis]:
    """Führt alle registrierten Prüfungen in der Reihenfolge der Befundnummern aus."""
    return [PRUEFUNGEN[nr](verbindung) for nr in sorted(PRUEFUNGEN)]
