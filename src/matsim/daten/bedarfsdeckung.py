"""Mengenprüfung der Versuchseingänge vor dem Simulationslauf (Issue #25).

Der Bericht zeigt, ob die freien Teile am Anfang für die geplanten Anforderungen reichen.
Er enthält weder eine Lieferprognose noch eine Annahme über späteren Nachschub.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field

from matsim.modell.typen import Anforderung

_BESTANDSPFAD = "materiallager.anfangsbestand"


@dataclass(frozen=True)
class Bedarfsbeitrag:
    anforderung_id: str
    station: str
    menge: int


@dataclass(frozen=True)
class Teiledeckung:
    pno: int
    bedarf: int
    freier_bestand: int
    fehlmenge: int
    anforderungen: tuple[Bedarfsbeitrag, ...]


@dataclass(frozen=True)
class Bestandsannahme:
    pno: int
    basiswert: int
    szenariowert: int


@dataclass(frozen=True)
class Deckungsbericht:
    """Bedarf und Fehlmengen je benötigtem Teil, mit Datenstand und Szenarioannahmen."""

    datenstand: str
    teile: tuple[Teiledeckung, ...]
    bestandsannahmen: tuple[Bestandsannahme, ...]
    hinweis: str = field(
        init=False,
        default="Nur Mengenprüfung des Anfangsbestands. Nachschub bleibt unberücksichtigt; "
        "keine Aussage über Lieferzeitpunkte oder Fertigstellung.",
    )

    @property
    def gedeckt(self) -> bool:
        return all(teil.fehlmenge == 0 for teil in self.teile)

    def als_json(self) -> str:
        return json.dumps({**asdict(self), "gedeckt": self.gedeckt}, ensure_ascii=False, indent=2)


def _bestandsannahmen(
    bestand: Mapping[int, int], abweichungen: Mapping[str, object]
) -> tuple[Bestandsannahme, ...]:
    annahmen = []
    for pfad, menge in abweichungen.items():
        if pfad != _BESTANDSPFAD and not pfad.startswith(f"{_BESTANDSPFAD}."):
            continue
        teilenummer = pfad.removeprefix(f"{_BESTANDSPFAD}.")
        if re.fullmatch(r"[1-9][0-9]*", teilenummer) is None:
            raise ValueError(f"{pfad}: Bestandsabweichung braucht eine gültige Teilenummer")
        if type(menge) is not int or menge < 0:
            raise ValueError(f"{pfad}: Bestandsmenge muss eine nichtnegative ganze Zahl sein")
        pno = int(teilenummer)
        annahmen.append(Bestandsannahme(pno, bestand.get(pno, 0), menge))
    return tuple(sorted(annahmen, key=lambda annahme: annahme.pno))


def pruefe_bedarfsdeckung(
    anforderungen: Iterable[Anforderung],
    freier_anfangsbestand: Mapping[int, int],
    *,
    datenstand: str,
    anlage_abweichungen: Mapping[str, object] | None = None,
) -> Deckungsbericht:
    """Vergleicht konkrete Anforderungen mit dem bereinigten freien Anfangsbestand.

    Der Bestand stammt z. B. aus ``Startbestand.teile_frei``. Reservierte und nicht verortete
    Teile sind darin bereits ausgeschlossen. Fehlt ein benötigtes Teil im effektiven
    Anfangsbestand, zählt sein Bestand als null.

    Punktpfade ``materiallager.anfangsbestand.<PNo>`` setzen absolute Szenariomengen, keine
    Zu- oder Abschläge. Der Basisbestand bleibt unverändert; andere Anlagenparameter wirken
    sich nicht auf die Mengenprüfung aus.
    """
    if not datenstand.strip():
        raise ValueError("Datenstand des Anfangsbestands fehlt")
    for pno, menge in freier_anfangsbestand.items():
        if type(pno) is not int or pno <= 0 or type(menge) is not int or menge < 0:
            raise ValueError(f"{_BESTANDSPFAD}.{pno}: ungültige Teilenummer oder Bestandsmenge")

    annahmen = _bestandsannahmen(freier_anfangsbestand, anlage_abweichungen or {})
    bestand = dict(freier_anfangsbestand)
    bestand.update((annahme.pno, annahme.szenariowert) for annahme in annahmen)

    beitraege: dict[int, list[Bedarfsbeitrag]] = defaultdict(list)
    gesehen: set[str] = set()
    for anforderung in anforderungen:
        if anforderung.id in gesehen:
            raise ValueError(f"Anforderung {anforderung.id!r} mehrfach übergeben")
        gesehen.add(anforderung.id)
        # Je Anforderung soll im Bericht nur ein Beitrag pro Teilenummer stehen.
        bedarf_je_satz: Counter[int] = Counter()
        for pno, menge in anforderung.satz.komponenten:
            if type(pno) is not int or pno <= 0 or type(menge) is not int or menge <= 0:
                raise ValueError(f"Anforderung {anforderung.id!r}: ungültige Komponente {pno!r}")
            bedarf_je_satz[pno] += menge
        for pno, menge in bedarf_je_satz.items():
            beitraege[pno].append(Bedarfsbeitrag(anforderung.id, anforderung.station, menge))

    teile = []
    for pno, beitraege_je_teil in sorted(beitraege.items()):
        bedarf = sum(beitrag.menge for beitrag in beitraege_je_teil)
        frei = bestand.get(pno, 0)
        teile.append(Teiledeckung(pno, bedarf, frei, max(0, bedarf - frei), tuple(beitraege_je_teil)))
    return Deckungsbericht(datenstand, tuple(teile), annahmen)
