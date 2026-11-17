# Aufgabenpaket 2: Rechercheprotokoll und Zugriffslücken

> **Prüfstand der Übernahme (17.11.2026):** Grundlage ist eine vom Nutzer bereitgestellte Deep-Research-Ausarbeitung. Die dort gemeldete Quellenprüfung wurde in dieser Integration nicht unabhängig bestätigt. Der Crossref-Abgleich scheiterte am Netzwerkzugriff (HTTP 403). Bibliografische Angaben und inhaltliche Quellenbelege Q01–Q14 bleiben bis zur Gegenprüfung vorläufig. Die Lehrunterlagen unter `docs/` fehlen im aktuellen Checkout. Projektannahmen sind keine empirischen Nachweise; Regelvorschläge sind keine Teamentscheidungen.

**Stichtag:** 17.11.2026
**Projekt:** Transportlosgrößen und Materialversorgung, IoT Factory
**Zweck:** Nachvollziehbare Recherche aktueller wissenschaftlicher Grundlagen für Transportlosbildung und Materialversorgung, ohne empirische Bewertung der Verfahren V0 bis V4.

## 1. Recherchefrage und Eingrenzung

Gesucht wurden wissenschaftliche Arbeiten zu (a) innerbetrieblicher Versorgung von Montagearbeitsplätzen, (b) Kitting und auftragsbezogener Chargenbildung, (c) Zeit-, Mengen- und Mischregeln für die Bündelung, (d) beschränkten Ressourcen und Wartezeiten sowie (e) Änderungen der Versorgungsleistung unter Unsicherheit. Der Schwerpunkt wurde auf begutachtete Journalbeiträge der Jahre 2021 bis 2026 gelegt. Ältere Quellen wurden nur dort einbezogen, wo sie definitorische Grundlagen zur Kitting- oder Konsolidierungstheorie bereitstellen.

**Nicht recherchiert wurden** als eigenständige Arbeitspakete: eine Optimierung der Montagepriorität, Robotino-Routen- oder Flottensteuerung, Entscheidungsmodelle, Programmierlösungen, Rohdatenauswertung oder eine nachträgliche Verifikation der Repository-Implementierung.

## 2. Tatsächlich genutzte Recherchezugänge

Die aktuelle Recherche erfolgte webbasiert über wissenschaftliche Publisherseiten, DOI-Landingpages und öffentliche Hochschulrepositorien beziehungsweise bibliografische Nachweisseiten. Verwendet wurden insbesondere:

| Zugang | Rolle in der Recherche | Einschränkung |
|---|---|---|
| Springer Nature Link | Publisherangaben und Open-Access-Volltexte zu In-Line-Kitting und Warteschlangen [Q07, Q10] | Zugang zu anderen Springer-Titeln nicht automatisch gegeben |
| Taylor & Francis Online | Publishermetadaten und, wo öffentlich verfügbar, Artikeltext/Abstract [Q02, Q03, Q04, Q08, Q09, Q12, Q14] | Teilweise Zugriffssperren oder nur Abstract |
| ScienceDirect / Elsevier | bibliografischer Abgleich und Abstracts [Q06, Q11, Q13] | Keine pauschale Hochschullizenz angenommen |
| INFORMS PubsOnline | begutachtete Maschinenbau-Fallstudie [Q05] | Publisher-Abstrakt statt gesicherter Volltextlektüre |
| MDPI / DOI-Landingpage | aktuelle offene systematische Review [Q01] | Reviewmethodik ersetzt nicht eine eigene systematische Suche |
| UGent Biblio und UTS-Repositorium | Publikationsstatus, Autoren, institutionelle Volltextfassung [Q02, Q03, Q06, Q09] | Manuskriptfassungen können sich in Satz und Seitenzählung unterscheiden |
| RePEc/IDEAS und Hochschulbibliografien | unabhängiger Abgleich von Heftdaten, Autoren und Abstract [Q06, Q08, Q12, Q13] | Metadaten kein Volltextersatz |

**Reproduzierbarkeitshinweis:** Es wurden keine eigenen institutionellen Abfragen mit exportierbaren Trefferlisten aus Scopus, Web of Science oder IEEE Xplore vorgenommen. Das vorliegende Protokoll beschreibt eine **gezielte, überprüfbare wissenschaftliche Webrecherche**, aber **keine vollständig reproduzierbare systematische Literaturübersicht mit dokumentierter Gesamttrefferzahl und formalem PRISMA-Screening**. Die PRISMA-Zahlen der Quelle [Q01] sind Ergebnisse **dieser fremden Review**, nicht eigene Trefferzahlen.

## 3. Verwendete Suchbegriffe und Suchkombinationen

Die folgenden englischen Suchbegriffe wurden thematisch kombiniert; Pluralvarianten und spezifische Publikationstitel dienten zum Quellenabgleich:

1. `assembly line feeding` AND (`material supply` OR `intralogistics` OR `kitting`)
2. `part feeding` AND (`internal transportation` OR `vehicle capacity`)
3. `kitting` AND (`batch supply` OR `order-dependent parts supply`)
4. `transport batching` OR `shipment consolidation` AND (`quantity-based` OR `time-based` OR `hybrid`)
5. `online order batching` AND `time window` AND `warehouse`
6. `material handling systems` AND (`queueing` OR `limited resources` OR `uncertainty`)
7. `assembly line feeding` AND (`2024` OR `2025` OR `2026` OR `review`)
8. `low-volume high-variety manufacturing` AND `line feeding`
9. `material shortages` AND (`assembly` OR `intralogistics`)
10. `line-side inventory` AND (`kitting` OR `part feeding`)

Die Auswahl wurde zunächst nach Themenrelevanz vorgenommen und dann über Original-Publisherseiten oder institutionelle Nachweise validiert. Recherchebegriffe sind keine Behauptung, dass für jede Kombination ein vollständiger strukturierter Datenbankexport vorliegt.

## 4. Kriterien für Aufnahme und Ausschluss

**Aufnahme:** Wissenschaftlicher Journalbeitrag mit überprüfbarem Titel, Autoren, Jahr und stabilem DOI; klarer Bezug mindestens zu einem Teilproblem; vorzugsweise begutachtet und ab 2021; bei abstrakt geprüften Quellen nur entsprechend enge Verwendung; bei älteren Beiträgen erkennbar grundlegende Relevanz.

**Ausschluss oder Zurückstellung:** Werbetexte, Seminarpräsentationen, nicht validierte Code- oder Projektseiten, Literatur ohne gesicherte Urheberschaft, reine Lieferketten- oder Langstreckentransportfälle ohne nachvollziehbaren Konzeptanschluss sowie Publikationen, deren Ergebnisse mangels Abstract nicht überprüfbar sind. Preprints ohne überprüfbare veröffentlichte Fassung wurden nicht als Kernbelege verwendet. Studien mit Milk-Run- oder Routenzuglogik wurden nicht als direkte Evidenz für gebündelte Direktfahrten eingesetzt.

**Besonderes Auswahlprinzip:** Aktualität ist wichtig, ersetzt aber keine Passung. Darum werden [Q11, Q12] für Konsolidierungsregeln und [Q09] für den betrieblichen Prozessbezug als zentral bewertet, während [Q13, Q14] nur den älteren Begriffs- und Vergleichsrahmen ergänzen.

## 5. Tatsächlich erreichte Quellenabdeckung

Das Quellenregister umfasst **14 laut Recherche geprüfte wissenschaftliche Journalarbeiten (unabhängige Bestätigung offen)**, davon:

- **11 Arbeiten aus 2023 bis 2026** nach den im Register berichteten Publikationsjahren: 3 aus 2026, 2 aus 2025, 3 aus 2024 und 3 aus 2023. Online-Erstveröffentlichung und Heftjahr sind getrennt zu beachten; die Angaben sind noch unabhängig zu bestätigen.
- **3 ältere Grundlagen-/Vergleichsarbeiten** aus 2010, 1992 und 2013.
- **5 öffentlich inhaltlich weiter zugängliche Fassungen**, bei denen über den Abstract hinaus wissenschaftliche Textteile geprüft wurden (Q01, Q04, Q07, Q09, Q10). Q11 wird getrennt als Abstract plus ausgewählte Publishertextteile geführt; eine vollständige Volltextlektüre ist nicht eindeutig dokumentiert. Die übrigen acht Quellen werden als Abstract/Metadaten geführt. Alle Zugriffsangaben stammen aus der ursprünglichen Recherche.

Die Zahlen bezeichnen die hier **ausgewählten Registerquellen**, nicht die Zahl aller Suchtreffer oder aller weltweit existierenden Arbeiten. Auswahl und Prüfung beziehen sich auf den **17.11.2026**. Einzelne Verlagsseiten können sich später ändern.

## 6. Prüfung der bibliografischen Angaben

Für die Kernquellen wurde jeweils wenigstens eine Publisherseite oder eine institutionelle bibliografische Erfassung eingesehen. Das Register dokumentiert Autoren, Originaltitel, Journal, Jahr, Heft-/Artikelnummer soweit verfügbar, DOI und Zugriffsstatus. Besondere Jahrgangsfallen wurden wie folgt behandelt:

- **Q05:** online 18.10.2024, im Journalheft 55(2) von 2025. Beide Daten sind angegeben.
- **Q07:** online 07.09.2023, Journalband 36 von 2024.
- **Q08:** online 03.10.2023, Jahrgang 2024.
- **Q02:** 2026 als Online-Publikation; die spätere endgültige Heftseitenzählung wurde nicht unterstellt.
- **Q03:** 2026 bereits mit Jahrgang 64(21) und Seiten 9539 bis 9561 nachweisbar.
- **Q11:** Artikelnummer 103135, nicht fälschlich als Seitenbereich dargestellt.

Es wurden keine ungeprüften Ausgaben oder Seitenangaben für Schmidt/Nyhuis, Schönsleben, Schuh/Stich, Scheer, Lödding oder Hopp/Spearman ergänzt. Auch wurde kein indirektes Lehrunterlagen-Zitat als direkte Originalquellenlektüre ausgegeben.

## 7. Verbleibende wissenschaftliche und projektspezifische Lücken

### Wissenschaftliche Zugriffslücken

**Z-01:** Einige aktuelle Artikel wurden über Publisher-Abstract und Metadaten eingeordnet, ohne dass der vollständige Haupttext vorlag. Detaillierte methodische Annahmen, konkrete Tabellen oder empirische Effektgrößen werden in diesen Fällen nicht behauptet.

**Z-02:** Die Recherche liefert keine publizierte Studie, die exakt alle Bedingungen der Laborfabrik abbildet: vollständige und anforderungengebundene Materialsätze, unterschiedliche Positionenzahlen, nur stationsreine Acht-Positions-Boxen, Robotino-Direktfahrten, mehrere knappe Ressourcen und die V0-bis-V4-Regeln.

**Z-03:** Die aktuellen Arbeiten zu hybriden Kitting-Systemen [Q04] und hybrider Konsolidierung [Q11] verwenden den Ausdruck „hybrid“ für unterschiedliche Sachverhalte. Eine Übertragung ohne Definition wäre fachlich irreführend.

**Z-04:** Keine belastbare Aussage zum geeigneten Zahlenwert einer Füllschwelle, Frist oder Sicherheitsreserve für RASS1 bis RASS3. Die Originalstudien sind keine Kalibrierungsdatensätze dieses Projekts.

### Verfahrensrelevante Projektdatenlücken

Hier werden die bestehenden Kennungen aus der Projektzusammenfassung beibehalten; vollständig stehen sie in [annahmen-und-datenluecken.md](annahmen-und-datenluecken.md).

| Kennung | Bedeutung für die wissenschaftliche Übertragung |
|---|---|
| L-01 | Dozenten-Referenzpaket fehlt; fachliche Randbedingungen könnten zu präzisieren sein |
| L-02 | Werkstück-/Bandumlaufzeit unbekannt; Dringlichkeit nicht belastbar terminierbar |
| L-03 | Hin- und Rückfahrzeiten nicht belastbar getrennt |
| L-04 | Snapshots ohne Historie; Zeit- und Wartedauern nicht belastbar ableitbar |
| L-05 | Pufferplatz-/Kommissionierkapazitäten ungeklärt |
| L-06 | Maschinenmeldungen als mögliche Quelle für Fahrzeugbelegung ungeklärt; Werkstückankunftsprognosen sind unabhängig davon nicht zugesichert |
| L-07 | Dokumentiert doppelt verortete Box; Risiko fehlerhaften Ressourcenbestands |
| L-08 | Tatsächlich verfügbarer Boxbestand nicht abschließend geklärt |
| L-09 | Ein einzelner beobachteter Ablauf liefert kein repräsentatives Bedarfsmuster |
| L-10 | Live-Datenbankzugriff nicht validiert; keine aktuelle Datenanbindung behaupten |

## 8. Vorgehensweise für die spätere Überprüfung im Team

Die Dateien sind Arbeitsgrundlagen für eine spätere Prüfung am tatsächlichen Repository. Vor einer Übernahme sollte das Team die folgenden **fachlichen Punkte** abgleichen: Welche Schnittstellenwerte sind wirklich verfügbar? Welche Verfahrensereignisse existieren? Welche Restbedarfsregel wird verbindlich? Welche Prioritäts- und Kapazitätsregeln bleiben feste Referenz? Wie sind die A- und L-Kennungen in den bestehenden Originaldokumenten bereits verwendet? Dies ist **keine** Anweisung zu einer sofortigen Code- oder Repositoryänderung.

**Verweise:** [Literaturregister und Matrix](literatur-ergaenzung.md), [Theorie](theoretische-grundlagen.md), [Verfahrenssteckbriefe](planungsverfahren.md), [Annahmen](annahmen-und-datenluecken.md).
