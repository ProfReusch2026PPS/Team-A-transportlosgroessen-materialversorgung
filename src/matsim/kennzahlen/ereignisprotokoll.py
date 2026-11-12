"""Schema des Ereignisprotokolls (Schnittstelle AP3 → AP5).

Jede Zeile enthält Zeit, Ereignis, Identität, Ressource und Zustandsänderung. Alle Kennzahlen
und die unabhängigen Prüfregeln werden ausschließlich aus diesem Protokoll berechnet.
Zeiten sind Sekunden. Gleichzeitige Ereignisse werden über ``lfd_nr`` eindeutig geordnet.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, fields
from enum import StrEnum
from pathlib import Path


class Ereignistyp(StrEnum):
    BEDARF_EINGANG = "bedarf_eingang"
    SATZ_GEBILDET = "satz_gebildet"
    PLANUNG_AUFRUF = "planung_aufruf"
    CHARGE_GEBUNDEN = "charge_gebunden"
    RESERVIERT = "reserviert"
    RESERVIERUNG_AUFGELOEST = "reservierung_aufgeloest"
    WARTEN_BEGINN = "warten_beginn"
    WARTEN_ENDE = "warten_ende"
    KOMMISSIONIERUNG_BEGINN = "kommissionierung_beginn"
    TEIL_GEPICKT = "teil_gepickt"
    KOMMISSIONIERUNG_ENDE = "kommissionierung_ende"
    TRANSPORT_BEGINN = "transport_beginn"
    TRANSPORT_ENDE = "transport_ende"
    LIEFERUNG = "lieferung"
    WERKSTUECK_ANKUNFT = "werkstueck_ankunft"
    WEITERFAHRT_MATERIALMANGEL = "weiterfahrt_materialmangel"
    MONTAGE_BEGINN = "montage_beginn"
    KOMPONENTE_VERBRAUCHT = "komponente_verbraucht"
    MONTAGE_ENDE = "montage_ende"
    LEERBOX_RUECK_BEGINN = "leerbox_rueck_beginn"
    LEERBOX_RUECK_ENDE = "leerbox_rueck_ende"
    LAUF_ENDE = "lauf_ende"


class Warteursache(StrEnum):
    """Jede Wartezeit eines Satzes hat genau eine Ursache (Zuordnungsregel: kennzahlen.md)."""

    BUENDELUNG = "buendelung"
    BESTAND = "bestand"
    BOX = "box"
    KOMMISSIONIERUNG = "kommissionierung"
    TRANSPORT = "transport"
    STATIONSKAPAZITAET = "stationskapazitaet"


@dataclass(frozen=True)
class Ereignis:
    lfd_nr: int
    zeit_s: float
    ereignis: Ereignistyp
    #: Identitäten; leer, wenn für das Ereignis nicht zutreffend.
    anforderung_id: str = ""
    charge_id: str = ""
    box_id: str = ""
    werkstueck_id: str = ""
    #: Station oder Ressource, an der das Ereignis stattfindet (z. B. "RASS1", "fahrzeug_1").
    ressource: str = ""
    #: Zustandsänderung des betroffenen Objekts.
    zustand_alt: str = ""
    zustand_neu: str = ""
    #: Nur bei WARTEN_BEGINN/WARTEN_ENDE: Wert aus ``Warteursache``.
    ursache: str = ""
    #: Teilenummer und Menge bei Bestandsbewegungen (Pick, Verbrauch, Reservierung).
    pno: int = 0
    menge: int = 0
    bemerkung: str = ""


SPALTEN: tuple[str, ...] = tuple(feld.name for feld in fields(Ereignis))


class Ereignisprotokoll:
    """Sammelt Ereignisse eines Laufs und schreibt sie als CSV."""

    def __init__(self) -> None:
        self.ereignisse: list[Ereignis] = []

    def schreibe(self, zeit_s: float, ereignis: Ereignistyp, **felder) -> Ereignis:
        if self.ereignisse and zeit_s < self.ereignisse[-1].zeit_s:
            raise ValueError("Ereignisse müssen in nicht fallender Zeitfolge protokolliert werden")
        ursache = felder.get("ursache", "")
        wartend = ereignis in (Ereignistyp.WARTEN_BEGINN, Ereignistyp.WARTEN_ENDE)
        if wartend and ursache not in set(Warteursache):
            raise ValueError("Warteereignisse brauchen genau eine Ursache aus Warteursache")
        if not wartend and ursache:
            raise ValueError("Eine Ursache ist nur bei Warteereignissen zulässig")
        eintrag = Ereignis(len(self.ereignisse) + 1, float(zeit_s), Ereignistyp(ereignis), **felder)
        self.ereignisse.append(eintrag)
        return eintrag

    def speichere_csv(self, pfad: Path) -> None:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        with pfad.open("w", encoding="utf-8", newline="") as datei:
            schreiber = csv.DictWriter(datei, fieldnames=SPALTEN, lineterminator="\n")
            schreiber.writeheader()
            for eintrag in self.ereignisse:
                schreiber.writerow(asdict(eintrag))


def lade_csv(pfad: Path) -> list[Ereignis]:
    """Liest ein gespeichertes Protokoll (für Kennzahlen und Prüfung, getrennt von der Simulation)."""
    with pfad.open(encoding="utf-8", newline="") as datei:
        return [
            Ereignis(
                **{
                    **zeile,
                    "lfd_nr": int(zeile["lfd_nr"]),
                    "zeit_s": float(zeile["zeit_s"]),
                    "ereignis": Ereignistyp(zeile["ereignis"]),
                    "pno": int(zeile["pno"]),
                    "menge": int(zeile["menge"]),
                }
            )
            for zeile in csv.DictReader(datei)
        ]
