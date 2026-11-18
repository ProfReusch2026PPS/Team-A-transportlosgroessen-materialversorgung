# Stichprobe: Auftrag 9178 vom Auslagern bis zur Montage

Verantwortlich: AP1. Zweck: an einem Auftrag von Hand prüfen, ob Schritthistorie, Materialpfad und Momentaufnahmen zusammenpassen (Issue #1). Ergebnis: **keine Unstimmigkeit**. Jedes Teil lässt sich von der Quellbox über die Zielbox bis zum Verbrauch verfolgen, und jeder der sechs Snapshots zeigt den dazu passenden Zwischenstand.

## Nachvollziehen

```text
.venv\Scripts\python -m matsim.daten importiere
.venv\Scripts\python -m matsim.daten stichprobe 9178
.venv\Scripts\python -m matsim.daten bestand 2026-11-09_1522
```

Der zweite Befehl listet alle Schritte von 9178 und alle Picks und Ablieferungen, die Teile für 9178 bewegt haben, zeitlich sortiert. Die Snapshot-Werte unten stammen aus `tblboxpos` (`BoxId, BoxPos, PNo, ONo, OPos`) und `tblbufferpos` (`ResourceId/BufNo/BufPos`, `BoxID`, `TimeStamp`). Die Prüfungen sind in `tests/test_qualitaet.py` festgeschrieben.

So liest man die Parameter eines Picks (OpNo 220, Schritt 10, `tblfinstepparameter`): 3/4 = Quellbox und -platz, 6/7 = Zielbox und -platz, 8/9/10 = Produktionsauftrag, -position und Montageschritt, 11 = Teil. Die Bedeutung folgt aus dem SQL der Operation, siehe [datenmodell-mes.md](datenmodell-mes.md), Abschnitt 5.

## Auftrag

| Feld | Wert | Quelle |
|---|---|---|
| Auftrag | 9178, zwei Werkstücke (Positionen 1 und 2), Arbeitsplan WPNo 1000 | `tblfinorderpos` |
| Freigabe, Start, Ende | geplant ab 15:07:00; Start 15:08:29; Ende 15:55:34 | `tblfinorder` |
| Zustand | 100 (abgeschlossen), keine Schritte mit Fehlercode | `tblfinorder`, `tblfinstep.ErrorRetVal` |
| Materialbedarf je Werkstück | RASS1: 800 + 814; RASS2: 813 + 811; RASS3: 831 | `tblstepdef` WPNo 1000 |

## Weg von Position 1 Schritt für Schritt

| Zeit | Ereignis | Beleg | Snapshot-Abgleich |
|---|---|---|---|
| 15:08:29–15:08:45 | Werkstück 9178/1 aus dem Hochregal ASRS32 ausgelagert | Schritt 10, OpNo 212, Ressource 1 | |
| 15:13:49–15:14:12 | Pick 9177/3: Teil 800 aus Box 20 Platz 2 in Box 11 Platz 3, bestimmt für 9178/1 Schritt 30 | OpNo 220, Ressource 19, Parameter 3/4/6/7/8/9/10/11 = 20/2/11/3/9178/1/30/800 | 15:16: Box 20 Platz 2 leer; Box 11 Platz 3 = 800, reserviert für 9177/3 |
| 15:14:12–15:14:34 | Pick 9177/4: Teil 814 aus Box 20 Platz 3 in Box 11 Platz 4 für 9178/1 Schritt 60 | wie oben | 15:16: Box 11 Platz 4 = 814 für 9177/4 |
| 15:16:24 | Box 11 auf Robotino 25 | | 15:16: `tblbufferpos` 25/1/1 = Box 11, Zeitstempel 15:16:24 |
| 15:17:44–15:17:47 | Ablieferung 9177 an RASS1; das SQL von OpNo 215 bucht die Plätze vom Kommissionierauftrag auf den Produktionsauftrag um | OpNo 215, Ressource 2 | 15:22: Box 11 auf 2/1/2 (Zeitstempel 15:17:43); Platz 3 = 800 und Platz 4 = 814, beide `ONo/OPos` = 9178/1 |
| 15:22:41–15:23:00 | Werkstück an RASS1 | Schritt 20, OpNo 320 | |
| 15:23:01–15:23:38 | Montage Mainboard (800) aus Box 11 Platz 3, 37 s | Schritt 30, OpNo 323 | 15:25: Box 11 leer |
| 15:23:52–15:24:19 | Montage Display (814) aus Box 11 Platz 4, 27 s | Schritt 60, OpNo 323 | 15:25: Box 11 leer |
| 15:25:11–15:25:34 | Pick 9179/3: Teil 813 aus Box 4 Platz 7 in Box 18 Platz 3 für 9178/1 Schritt 100 | OpNo 220 | 15:22 und 15:25: Box 4 Platz 7 = 813, schon für 9179/3 reserviert; Box 18 Platz 3 leer, für 9179/3 reserviert. 15:36: Box 4 Platz 7 leer |
| 15:32:02–15:32:27 | Pick 9179/4: Teil 811 aus Box 21 Platz 2 in Box 18 Platz 4 für 9178/1 Schritt 110 | OpNo 220 | 15:25: Box 21 Platz 2 = 811 für 9179/4; 15:36: leer |
| 15:34:54–15:34:58 | Ablieferung 9179 an RASS2 | OpNo 215, Ressource 4 | 15:36: Box 18 auf 4/1/2; Platz 3 = 813 und Platz 4 = 811 für 9178/1 |
| 15:39:40–15:39:59 | Werkstück an RASS2 | Schritt 90, OpNo 320 | |
| 15:40:00–15:40:40 | Montage Analog-Platine (813) aus Box 18 Platz 3, 40 s | Schritt 100, OpNo 324 | 15:41: Box 18 Platz 3 leer |
| 15:40:41–15:41:06 | Montage Gyroskop (811) aus Box 18 Platz 4, 25 s | Schritt 110, OpNo 324 | 15:41: Platz 4 = 811 noch vorhanden, der Export lag also vor 15:41:06 |
| 15:40:34–15:40:56 | Pick 9180/2: Teil 831 aus Box 15 Platz 4 in Box 11 Platz 2 für 9178/1 Schritt 160 | OpNo 220 | 15:36: Box 15 Platz 4 = 831 für 9180/2; 15:41: leer, Box 11 Platz 2 = 831 |
| 15:45:07–15:45:09 | Ablieferung 9180 an RASS3 | OpNo 215, Ressource 6 | |
| 15:48:37–15:49:01 | Montage Frontabdeckung (831) aus Box 11 Platz 2, 24 s | Schritt 160, OpNo 325 | 15:57: Box 11 leer |
| 15:49:32–15:55:34 | Funktionstest, Etikett, Ausgabe, Einlagern | Schritte 180 bis 250 | |

Position 2 läuft gleich, mit den Plätzen 11/5 und 11/6 (RASS1), 18/5 und 18/6 (RASS2) und 11/3 (RASS3). Die Quellboxen sind 21 (RASS1), 21 und 26 (RASS2) und 17 (RASS3).

## Beobachtungen

1. **Mengenbilanz:** Für 9178 wurden 10 Teile kommissioniert, je 5 pro Werkstück, und 10 Montageschritte ausgeführt. Jedes Teil wurde genau einmal entnommen, abgeliefert und verbraucht.
2. **Reservierung ist kein Bestand:** Quellteile sind schon ab der Freigabe des Kommissionierauftrags für ihn reserviert (15:22: Box 4 Platz 7 = 813 für 9179/3). Die Zielplätze sind leer reserviert. Physisch zählt jedes Teil nur einmal, die Zählregeln in Abschnitt 3 des Datenmodells sind bestätigt.
3. **Eine Box, eine Station, mehrere Aufträge:** Box 11 trug um 15:17 Sätze für 9176/1, 9178/1 und 9178/2, alle für RASS1. Gemischt nach Station war sie nie. Nach der Leerung um 15:24 wurde dieselbe Box für RASS3 wiederverwendet (9180).
4. **Wartezeit auf Material:** 9178/1 war um 15:08:45 ausgelagert, die Box für RASS1 kam um 15:17:44, montiert wurde ab 15:22:41. An RASS2 wartete das Werkstück von 15:25:10 (Messung) bis 15:39:40, weil die RASS2-Box erst um 15:34:54 kam. An RASS3 wartete es von 15:43:41 bis 15:48:17 (Box seit 15:45:07 da, davor 9178/2).
5. **Reihenfolge:** 9178/2 wurde an RASS1 vor 9176/1 und 9178/1 montiert, obwohl es als letztes ausgelagert wurde (B-08). Das passt zu Werkstücken, die die Schleife umfahren, bis ihr Material da ist (A-01).
6. **Exportzeitpunkte:** Aus dem Abgleich lassen sich die Exporte eingrenzen: 15:25 zwischen 15:25:11 und 15:25:34, 15:41 zwischen 15:40:56 und 15:41:06.
7. **Montagezeiten:** Das erste Teil eines Satzes dauert länger (Mainboard 37 s, Analog-Platine 40 s) als das zweite (Display 27 s, Gyroskop 25 s). Das bestätigt die Erklärung der zweigipfligen Montagezeit (Issue #3).

## Grenzen

- Die Fahrten der Robotinos stehen nicht in der Schritthistorie. Dass Robotino 25 die RASS1-Box gefahren hat, ist nur dem Snapshot 15:16 zu entnehmen.
- Es ist eine Stichprobe von einem Auftrag. Dieselbe Verknüpfung über die Pick-Parameter ist für alle Montageschritte geprüft (B-07: 563 von 572 mit nachweisbarem Pick).
