# Planungsverfahren

Verantwortlich: AP2 (Theorie und Steckbriefe), AP4 (Umsetzung). Stand: Arbeitsfassung vom 17.11.2026. V1 ist implementiert; V0 und V2–V4 sind Gerüste. Neue Regeln sind Vorschläge, Parameter nicht kalibriert.

> **Prüfstand der Übernahme (17.11.2026):** Grundlage ist eine vom Nutzer bereitgestellte Deep-Research-Ausarbeitung. Die dort gemeldete Quellenprüfung wurde in dieser Integration nicht unabhängig bestätigt. Der Crossref-Abgleich scheiterte am Netzwerkzugriff (HTTP 403). Bibliografische Angaben und inhaltliche Quellenbelege Q01–Q14 bleiben bis zur Gegenprüfung vorläufig. Die Lehrunterlagen unter `docs/` fehlen im aktuellen Checkout. Projektannahmen sind keine empirischen Nachweise; Regelvorschläge sind keine Teamentscheidungen.

## 1. Einordnung

Die Grundlagen zu Materialbereitstellung, Kitting, Transportlosbildung, Mengen-/Zeitregeln und Ressourcenwartezeiten stehen in [theoretische-grundlagen.md](theoretische-grundlagen.md). Quellenkennungen Q01–Q14 verweisen auf [literatur-ergaenzung.md](literatur-ergaenzung.md); Suchweg und Zugriffslücken stehen in [literaturrecherche.md](literaturrecherche.md).

Vollständige Materialsätze bleiben ihren Anforderungen zugeordnet; Reservieren schafft keinen Bestand. Stationsreinheit ist die bestehende Annahme A-06. Transportlose sind von Produktions- und Transferlosen zu unterscheiden. Bündelung einer Direktfahrt ist keine Routenzuglogik. Weder wenige Transporte noch eine frühe Freigabe beweisen eine bessere tatsächliche Versorgung.

Frühere Verweise auf Lehrkapitel und Lehrbuchseiten können mangels `docs/` derzeit nicht bestätigt werden. Sie werden nicht als geprüfte Primärbelege übernommen. Das folgende bestehende Entscheidungsmodell sowie Enumeration und bisherige Parameter bleiben in dieser Bearbeitung unverändert.

## 2. Entscheidungsmodell

| Element | Festlegung |
|---|---|
| Entscheidungsgrößen | je Planungsanlass: welche offenen Sätze bilden jetzt eine Charge, und ab wann darf sie bereitgestellt und versendet werden |
| Ziele | geringer Transportaufwand, kurze Zeit bis zur Materialbereitstellung, geringe materialbedingte Montageverzögerung; Zielhierarchie legt das Team fest |
| Nebenbedingungen | nur vollständige Sätze; höchstens 8 Boxpositionen; nur Sätze einer Station je Charge (A-06); nur freier, nicht reservierter Bestand; freie Box erforderlich; Satz bleibt seiner Anforderung zugeordnet |
| Entscheidungshorizont | der zum Anlass bekannte Zustand; keine Vorschau auf künftige Bedarfe |
| Modellgrenze | Produktionsabschnitt RASS1 bis RASS3; Referenzregeln fest |

## 3. Steckbriefe

### Verfahrensfrist, Messung und Zuständigkeit

**Bestehende Kennzahlendefinition:** Vor der Bindung gilt die Rangfolge **Bestand → Box → Bündelung** ([kennzahlen.md, Abschnitt 2](kennzahlen.md#2-wartezeit-zerlegung)). Gemessene Bündelungswartezeit entsteht nur, wenn freier Bestand und eine freie Box vorhanden sind, die Regel aber bewusst zurückhält. Ein Timer ist daher nicht mit der gemessenen Bündelungswartezeit gleichzusetzen.

**Neuer Vorschlag zur Abstimmung (A-V04/A-V07/A-V11):** Für jede offene Anforderung wird der erste bei einem zulässigen Aufruf festgestellte Zeitpunkt vollständiger Erfüllbarkeit aus freiem Bestand festgehalten. Eine fehlende Box verhindert diesen Friststart nicht. Der einmal gesetzte Termin wird durch zwischenzeitlichen Bestands- oder Boxmangel nicht nach hinten verschoben. Der maßgebliche Gruppentermin ist der früheste Termin der noch offenen, zulässigen Anforderungen. Nach Bindung einer Teilcharge wird er aus den verbleibenden Anforderungen neu bestimmt; für bereits wartende Anforderungen beginnt keine neue Frist. Ist eine fällige Anforderung nicht bindbar, bleibt sie überfällig; ein erneuter Versuch erfolgt beim nächsten zulässigen Planungsanlass. Kein wiederholtes Fristereignis zum selben vergangenen Zeitpunkt und kein beliebiges Polling. Welcher bestehende Anlass eine Bestandsänderung erfasst, bleibt mit AP3 zu klären. Die Warteursache wird unabhängig davon gemäß der genannten Rangfolge gemessen. Eine maximale Verfahrensfrist garantiert keine maximale Lieferzeit.

**Informationsbedarf:** Die Standardschnittstelle enthält keinen Zeitpunkt „erstmals erfüllbar“. AP3/AP4 müssen entscheiden, ob das Verfahren diesen Verlauf intern führt oder die Simulation ihn über `zusatz` liefert. Keine Schnittstellen- oder Codeänderung erfolgt mit dieser Dokumentation.

**Bestehende Schnittstelle:** Das Verfahren liefert Chargenentscheidungen und verändert den übergebenen Zustand nicht. Lokale Bestands- und Boxenzähler verhindern Doppelvorschläge innerhalb eines Aufrufs. Erst die Simulation prüft und bindet die Entscheidungen verbindlich und reserviert Bestand und Boxen. „Aufnehmen“ oder „Auffüllen“ vor der Entscheidung bezeichnet nur eine vorläufige Auswahl; es werden keine gebundenen Chargen wieder geöffnet.

### Offene Teamentscheidung: Abgrenzung V3 und K2

Der bisherige Entwurf lässt für V3 sowohl eine feste Wartefrist als auch Dringlichkeit zu. Damit ist K2 nicht schon durch Rückwärtsterminierung und Auffüllen eine eigenständige Verbesserung.

**Vorschlag, noch nicht beschlossen:** Für den Vergleich wird eine **zeitbasierte V3-Variante** mit fester maximaler Verfahrensfrist verwendet; eine Vollboxfreigabe ist zusätzlich ausdrücklich festzulegen. K2 erweitert genau diese Basis um individuelle bekannte Werkstückbedarfstermine: Der frühere Zeitpunkt aus fester Frist und rückwärts aus Bedarf und begründetem Vorlauf abgeleitetem Freigabetermin ist maßgeblich. K2 verkürzt damit das feste Bündelungsfenster bedarfsabhängig; Auffüllen allein ist kein Unterschied. Für Anforderungen ohne verlässlichen Bedarfstermin gilt die feste Basisfrist.

Wird die Dringlichkeitsvariante bereits als V3 beibehalten, ist K2 in dieser Form **keine hinreichend eigenständige Verbesserung**. Dann müssen Team und AP4 einen zusätzlichen Mechanismus bestimmen oder K1/K3 weiterverfolgen. Weder die V3-Beschränkung noch die K2-Auswahl ist hiermit beschlossen. Bekannte Ankünfte bereits freigegebener Werkstücke sind von unbekanntem zukünftigem Bedarf zu unterscheiden; deren Verfügbarkeit ist nicht zugesichert. Das bestehende Entscheidungsmodell wird nicht verändert.

### Gemeinsame Randbedingungen, Statussprache und Illustrationsfall

**Statusschlüssel:**

- **Bestehende Vorgabe:** Vom Team als verbindlicher Projektrahmen beschrieben; nicht durch eigene Datenprüfung verifiziert.
- **Implementiert:** Im bereitgestellten Projektkontext ausdrücklich als im Codex-Chat geprüfter Implementierungsstand gemeldet. Die ursprüngliche Recherche las den Python-Code nicht; bei der Integration wurde die Beschreibung mit `src/matsim/regeln/verfahren.py` und `basis.py` abgeglichen.
- **Dokumentierter Entwurf:** Vom Team vorgesehen, aber nach Projektstand nicht implementiert oder nicht abschließend festgelegt.
- **Neuer Vorschlag:** Hier fachlich ergänzt. Keine Teamentscheidung und keine Implementierungsbehauptung.

**Für alle Verfahren bestehende Vorgaben:** Ein Materialsatz ist nur vollständig nutzbar; jede Anforderung behält ihre ID und ihre Station; Reservieren erhöht den Bestand nicht; eine Box besitzt in der aktuellen Konfiguration acht Positionen; der Platzverbrauch je Satz kann variieren; je Charge werden gemäß **A-06** nur Sätze derselben Station gebündelt. Boxen, Kommissionierplätze, Fahrzeuge und stationsspezifische Übergabeplätze sind beschränkt. Es werden keine gebundenen Chargen oder beauftragten Transporte umgeplant. Ereignisse für die Neuplanung sind Bedarfseingang, Fristablauf und Freigabe relevanter Kapazität. Die Regeln für Montagepriorität, Auftragsfreigabe, Fahrzeugzuordnung, Übergabe und Rückfahrt gelten als **feste Referenz**. Das Verfahren liefert nur `(Zielstation, Anforderungs-IDs in Charge, frühester Bereitstellungs-/Versandzeitpunkt)`; die physische Abwicklung liegt in der Simulation.

**Informationsbasis laut Schnittstelle:** Aktuelle Zeit; noch offene, nicht gebundene Anforderungen; freier, nicht reservierter Bestand je Teilenummer; freie Boxen; freie Kommissionierplätze; freie Fahrzeuge; freie Übergabeplätze je Station; Boxkapazität; zulässige Teile je Station. Zusätzliche Ankunftsprognosen sind **nicht zugesichert**. Regeln, die diese benötigen, sind daher nur unter zusätzlicher Voraussetzung ausführbar.

**Beispielvorrat (sämtliche Zahlen frei illustrativ, keine gemessenen Werte):** Alle Teile seien vollständig und die dafür benötigten freien Bestände verfügbar. RASS1 hat Anforderungen A (Eingang 0 s, Belegung 3), B (20 s, Belegung 2), C (40 s, Belegung 3). RASS2 hat D (0 s, Belegung 4) und E (30 s, Belegung 4). RASS3 hat F (10 s, Belegung 1). Es gibt zunächst genügend freie Boxen und keine nachgelagerte Ressourcenwartezeit, **nur für das Beispiel**. Jeder Verfahrenssteckbrief erläutert anschließend, was bei knappen Ressourcen anders zu unterscheiden ist.

### V0: Referenzversorgung nach beobachtetem MES-Ablauf

**1. Grundidee und theoretische Einordnung.** [Dokumentierter Entwurf] Stationsweise sequentielle Referenzversorgung, keine allgemeine theoretisch überlegene Bündelungsregel. Die Prozessabfolge von Bedarf und Ausführung passt begrifflich zu [Q09]; die Literatur bestätigt jedoch **nicht**, dass diese konkrete Stationsfolge ein universelles MES-Verhalten ist.

**2. Ausgangslage und Datenbasis.** [Dokumentierter Entwurf] Der beobachtete Ablauf vom **09.11.2026** umfasste drei Produkte und sechs in den Projekttexten genannte MES-Snapshots. Deren Rohdaten liegen hier nicht vor. Der Entwurf nennt RASS1, dann RASS2, dann RASS3, wobei die nächste Stationscharge erst nach Lieferung der vorherigen Box abgewickelt wird.

**3. Informationsbedarf.** [Bestehende Vorgabe] Stationskennung, offene Sätze, Satzvollständigkeit, freier Bestand, Boxbelegung, freie Boxen und ein Rückmeldesignal über abgeschlossene Ablieferung der vorherigen Box. [Ungeklärt] Ob das aktuelle Simulatorinterface die Ablieferung in der erforderlichen Bedeutung bereits bereitstellt, ist nicht verifiziert.

**4. Auslöser.** [Dokumentierter Entwurf] Zu einem zulässigen Neuplanungsereignis wird die nächstberechtigte Station mit offenen, erfüllbaren Sätzen betrachtet. [Neuer Vorschlag] Die Simulatorrückmeldung „vorherige Lieferung abgeschlossen“ ist fachlich als Freigabe einer relevanten Versorgungskapazität oder als bereits vorhandenes Folgeereignis zuzuordnen, nicht durch ein neues beliebiges Polling-Ereignis zu ersetzen.

**5. Entscheidungsablauf.** [Dokumentierter Entwurf] (a) Bearbeite Stationen in Referenzreihenfolge RASS1, RASS2, RASS3. (b) Ermittle deren offene, vollständige und verfügbare Sätze. (c) Forme pro Station die beobachtungsnahe Charge. (d) Schlage genau die zugeordneten Sätze vor; die Simulation reserviert bei verbindlicher Bindung die Teile und eine freie Box. (e) Gib sie zum frühestmöglichen zulässigen Zeitpunkt frei. (f) Wechsle die Station erst nach Ablieferung der vorherigen Box. **Wichtig:** Schritt (c) ist **nicht vollständig spezifiziert**, sobald mehr Positionen verlangt werden, als in eine Box passen.

**6. Parameter.** [Dokumentierter Entwurf] Stationsreihenfolge. [Bestehende Vorgabe] Boxkapazität acht Positionen, A-06. [Ungeklärt] Auswahl-/Restbedarfsregel bei mehr als einer Boxkapazität, Zeitpunkt eines möglichen Neustarts der Stationsreihenfolge.

**7. Kapazitäten und Konkurrenz.** [Dokumentierter Entwurf] Die Stationssequenz begrenzt gleichzeitige Freigaben. [Bestehende Vorgabe] Keine Überbuchung von Bestand oder Boxen; reale Wartezeiten liegen bei der Simulation. [Neuer Vorschlag] Bei fehlender freier Box ist der Zustand „nächste Station freigabeberechtigt, jedoch noch nicht bindbar“ explizit zu protokollieren. Die Referenzreihenfolge darf ohne Teamentscheidung nicht aus Dringlichkeit umsortiert werden.

**8. Restbedarf.** [Ungeklärt] Was mit mehr als acht belegten Positionen derselben Station oder einzelnen späteren Nachforderungen passiert, ist aus dem beobachteten Dreiproduktlauf nicht ableitbar. [Neuer Vorschlag zur Abstimmung] V0 nur für Referenzfälle einsetzen, in denen die beschriebene Regel eindeutig ist; komplexere Fälle erst nach Klärung von L-01 und L-09 spezifizieren. Eine zusätzliche Boxteilung wäre eine **neue** Regel, nicht die beobachtete Referenz.

**9. Theoretisch erwartbare Stärke und Grenze.** [Eigene Übertragung] Gut interpretierbare Referenz mit harter Stationsfolge. Gefahr langer Wartezeiten nachfolgender Stationen, wenn eine frühere Station oder ihre Lieferung blockiert. Wenige beobachtete Vorgänge sind kein generalisierbarer MES-Nachweis.

**10. Beispiel.** **Illustrativ:** Um Sekunde 40 sind A, B, C und D, E, F vollständig offen. V0 sieht zunächst die RASS1-Box mit A+B+C (3+2+3 = 8 Positionen) vor. Erst nach tatsächlicher Ablieferung darf die RASS2-Box D+E (4+4 = 8) folgen; anschließend RASS3 mit F. Aus diesem Schema darf **keine** Dauer bis zum Lieferabschluss abgeleitet werden.

**11. Offene Fragen.** L-01, L-04, L-09; Verhalten bei Überschreitung der Boxkapazität; Ablieferungsereignis; Behandlung fehlteiliger RASS1-Anforderungen bei offenen RASS2-Anforderungen.

---

### V1: Einzelversorgung

**1. Grundidee und theoretische Einordnung.** [Implementiert, gemäß berichteter Codeprüfung] Pro zulässigem, aktuell vollständig erfüllbarem Materialsatz entsteht eine eigene Charge. V1 erzeugt **keine bewusste Bündelungswartezeit**. Es ist die Einzelversorgungs-Referenz innerhalb der Materialregelklassen, aber keine Garantie der schnellsten physischen Bereitstellung [Q07, Q09].

**2. Informationsbedarf.** [Implementiert] Aktuelle Zeit, offene Anforderungen mit Eingangszeit und ID, Komponentenliste, freie Bestände, Stationszulässigkeit, Satzbelegung und freie Boxen. [Bestehende Vorgabe] Die Ressourcen Kommissionierung, Fahrzeug und Übergabe werden nicht als sofort verfügbar angenommen.

**3. Auslöser.** [Bestehende Vorgabe] Aufruf zu einem zulässigen Planungsereignis. [Implementiert] Keine eigene Wartefrist; der früheste Versandzeitpunkt der freizugebenden Charge ist die aktuelle Zeit.

**4. Entscheidungsablauf.** [Implementiert] (a) Alle offenen Anforderungen aufsteigend nach Eingangszeit sortieren, bei Gleichstand nach Anforderungs-ID. (b) Prüfen, ob ein Satz an der Station grundsätzlich zulässig ist und in eine Box passt; falls nein, nicht binden. (c) Prüfen, ob alle Komponenten im **noch freien** Bestand verfügbar sind. (d) Falls nicht, überspringen; spätere verfügbare Anforderungen bleiben prüfbar. (e) Falls verfügbar und eine Box frei ist, für genau diesen Satz eine Charge erzeugen, die lokal verfügbaren Boxen um eins vermindern und den **innerhalb desselben Aufrufs fortgeschriebenen** freien Bestand reduzieren. Die verbindliche Bindung übernimmt die Simulation. (f) Bis zum Ende der Prüfliste fortfahren, ohne bereits gebundene Anforderungen noch einmal zu vergeben.

**5. Parameter.** [Implementiert] Reihenfolge `(Eingangszeit, ID)`; Satz pro Charge = 1; früheste Freigabe = aktuelle Zeit. [Bestehende Vorgabe] Belegung <= acht Positionen, A-06. **Keine** Mindestfüllung, kein Fristwert, kein Dringlichkeitsscore. Die Ordnung ist eine implementierte Regel, kein einstellbarer V1-Parameter.

**6. Kapazitäten.** [Implementiert] Ohne freie Box keine neue Charge. Freier Bestand ist **kein** mehrfach nutzbarer Pool, sondern wird innerhalb des Aufrufs nach jeder Bindung fortgeschrieben. [Bestehende Vorgabe] Kommissionierplatz, Fahrzeug und Übergabeplatz bestimmen gegebenenfalls die spätere Ausführung. **Keine** Aussage „im selben Moment ausgeliefert“.

**7. Konkurrenz zwischen Anforderungen/Stationen.** [Implementiert] Es gilt die globale Ordnung nach Eingang/ID, nicht die Stationenreihenfolge von V0. Eine ältere, fehlteilige Anforderung kann übergangen werden. [Neuer Vorschlag] Zustände und Überspringgründe separat sichtbar halten; daraus entsteht **keine** neue Prioritätsänderung.

**8. Restbedarf.** [Implementiert] Jeder später verfügbaren und erlaubten Anforderung ist auch ohne weitere Bündelung eine Einzelcharge möglich. Fehlteiliger Bedarf bleibt offen bis zu einem zukünftigen zulässigen Planungsaufruf; wenn Bestandserhöhung kein solches Ereignis auslöst, bleibt dieser Zusammenhang **ungeklärt**. Grundsätzlich unzulässige Sätze dürfen nicht gebunden werden.

**9. Theoretisch erwartbare Stärke und Grenze.** [Eigene Übertragung] Minimiert absichtliches Warten auf weitere Sätze. Kann bei vielen Anforderungen viele einzelne Boxen und Transporte erzeugen; dies erhöht möglicherweise Ressourcenlast und Ressourcenwartezeit [Q07, Q08]. Ein möglicher Vorteil oder Nachteil für rechtzeitige Versorgung ist **nicht** belegt.

**10. Beispiel.** **Illustrativ:** A und D treffen bei t=0 ein; Gleichstand wird über die Anforderungs-ID entschieden, nicht automatisch über RASS1. Für A entsteht eine Charge mit drei von acht belegten Positionen, für D eine eigene mit vier. B, C, E, F erhalten bei eigener vollständiger Verfügbarkeit ebenfalls Einzelchargen. Bei nur einer freien Box entsteht zunächst höchstens **eine** Bindung, die übrigen bleiben offen. Fehlendes Display bei A führt zum Überspringen von A; D darf trotzdem bedient werden.

**11. Offene Fragen.** Sind alle grundsätzlich unzulässigen Fälle vollständig dokumentiert? Welches Ereignis startet einen erneuten Versuch bei neu verfügbarem Material? Wie wird mögliche Dauerbenachteiligung älterer fehlteiliger Anforderungen ausgewiesen? Die V1-Beschreibung wurde bei der Integration mit dem vorhandenen Code abgeglichen; ein empirischer Wirksamkeitsnachweis folgt daraus nicht.

---

### V2: Füllschwellenverfahren

**1. Grundidee und theoretische Einordnung.** [Dokumentierter Entwurf] Für dieselbe Station werden vollständige Sätze bis zu einer Mindestzahl belegter Boxpositionen gesammelt. Das ist zunächst eine **mengenabhängige** Bündelung. Fügt man eine maximale Wartezeit als Restregel hinzu, wird V2 **hybrid mengen-/zeitabhängig** [Q11, Q12].

**2. Informationsbedarf.** [Bestehende Vorgabe] Standard-Schnittstelle mit Anforderungen, IDs, Eingang, Komponenten und Satzbelegungen, freiem Bestand, Boxen und Station. [Neuer Vorschlag] Zeit des frühesten bereits vollständig erfüllbaren und noch ungebundenen Satzes pro Station für eine optionale Restfrist; ein bekanntes Bedarfsende nur bei tatsächlich bereitgestelltem Signal.

**3. Auslöser.** [Dokumentierter Entwurf] Erreichen einer Füllschwelle. [Neuer Vorschlag] Bei Abschluss einer tatsächlich bekannten Bedarfsperiode die verbleibenden erfüllbaren Sätze freigeben. **Alternative neuer Vorschlag:** Spätestens nach einer definierten Restwartefrist freigeben. Diese Alternative verändert die Regelklasse zu „Menge oder Zeit“.

**4. Entscheidungsablauf.** [Dokumentierter Entwurf] (a) Je Station offene Sätze auf Zulässigkeit, Vollständigkeit und freien Bestand prüfen. (b) Aus erfüllbaren Sätzen **eine stationsreine** Kombination mit insgesamt maximal acht Positionen bilden. (c) Bei Erreichen der positionsbezogenen Schwelle freigeben. [Neuer Vorschlag für reproduzierbare Auswahl] Nach Eingangszeit und dann ID sukzessive passende Sätze aufnehmen; würde der nächste Satz die acht Positionen überschreiten, wird er vorläufig übersprungen und ein späterer passender Satz darf aufgenommen werden. Keine Änderung bereits gebundener Chargen. (d) Nach jedem Chargenvorschlag die lokalen Bestands- und Boxenzähler fortschreiben; die Simulation übernimmt die verbindliche Bindung. (e) Nicht erreichte Schwelle nach beschlossener Restregel behandeln.

**5. Parameter.** [Dokumentierter Entwurf] `F`, minimale Positionenauslastung, als ganzzahlige Schwelle zwischen 2 und 8 gemäß bisherigem Parameterbereich, **nicht** als Mindestanzahl von Sätzen. [Neuer Vorschlag] `W_rest`, maximale bewusste Wartezeit des ältesten erfüllbaren Satzes, **nur** falls diese Variante beschlossen wird. [Bestehende Vorgabe] Kapazität acht Positionen. Beispielwerte `F=6` und `W_rest=120 s` sind **rein illustrativ**, keine Kalibrierung.

**6. Nicht exakt erreichbare Schwelle.** [Neuer Vorschlag] Die Schwelle bedeutet „**mindestens F und höchstens 8**“, kein Zwang zu exakter Gleichheit. Beispiel: Satzgrößen 4+3 = 7 erfüllen `F=6`. Wenn nur 5er-Sätze vorhanden sind, sind zwei davon nicht gemeinsam transportierbar; ein Satz mit fünf Positionen kann durch reine Mengenschwelle nie die Sechsergrenze erreichen. Dafür ist eine separate Restbedarfsregel notwendig.

**7. Kapazitäten und Konkurrenz.** [Bestehende Vorgabe] Bindung nur bei ausreichend freien Teilen und Box, physische Ressourcenabwicklung durch Simulation. [Neuer Vorschlag] Freigabereife Stationschargen, die gleichzeitig konkurrieren, in aufsteigender Zeit des ersten erfüllbaren Satzes, bei Gleichstand nach Stationskennung behandeln. Das ist nur eine deterministische **Chargenauswahlregel**, keine Änderung der Fahrzeugzuordnung. Die Auswahl kann nicht allein aufgrund eines freien Fahrzeugs „sofortige Lieferung“ garantieren.

**8. Restbedarfsregel.** [Dokumentierter Entwurf] Freigabe am bekannten Ende des Bedarfseingangs **oder** nach Höchstwartezeit. [Neuer Vorschlag] Beide Bedingungen sauber in der Dokumentation trennen: V2a „Menge + nachweisbares Endesignal“; V2b „Menge oder Höchstwartezeit“. Fehlt das Endesignal und wird keine Frist verwendet, ist die Lieferung eines kleinen Rests **nicht gewährleistet**. Eine Frist darf erst ab dem definierten erfüllbaren Satz laufen und ersetzt keine fehlenden Teile oder Boxen.

**9. Theoretisch erwartbare Stärke und Grenze.** [Eigene Übertragung] Bei regelmäßigem Bedarf können höhere Positionsauslastung und weniger Einzelfahrten auftreten. Ein kleiner Rest kann lange warten, und eine hohe Schwelle kann die ersten Sätze verzögern. Eine Höchstwartezeit kann dieses absichtliche Warten begrenzen, nicht die physische Ankunft [Q07, Q11, Q12].

**10. Beispiel.** **Illustrativ:** `F=6`. Bei t=20 sind A(3)+B(2)=5 Positionen an RASS1, also noch keine Mengenauslösung. Bei t=40 kommt C(3) hinzu; die acht Positionen aus A+B+C werden freigegeben. Bei RASS2 werden D(4)+E(4) bei t=30 freigabereif. F(1) an RASS3 bleibt ein Rest und erhält bei vorhandener Frist erst nach deren Ablauf eine mögliche Freigabe. Nach t=40 ist damit nicht bewiesen, dass eine der Boxen bereits am Übergabeplatz steht.

**11. Offene Fragen.** Verbindliche Auswahlregel bei unterschiedlichen Größen, Reihenfolge konkurrierender Stationen, Definition des Friststarts, Verfügbarkeit eines Endesignals, Umgang mit bestandsbedingtem Teilfüllstand, zulässige Bedeutung von „Füllschwelle“ in der späteren Simulation.

---

### V3: Maximale Bündelungswartezeit oder Dringlichkeit

**1. Grundidee und theoretische Einordnung.** [Dokumentierter Entwurf] Stationsreine vollständige Sätze dürfen zur Bündelung warten, sollen jedoch spätestens an einer **maximalen Regelwartefrist** oder einer **aus bekanntem Produktionsbedarf abgeleiteten Dringlichkeitsgrenze** freigegeben werden. Zeitfenster sind aus Online-Batching bekannt [Q08]; verfahrensübergreifende Vorlauf- und Ressourcenunsicherheit ist für Materialflusssysteme relevant [Q07].

**2. Informationsbedarf.** [Bestehende Vorgabe] Standarddaten der Schnittstelle. [Dokumentierter Entwurf] Falls eine bedarfsabhängige Dringlichkeit genutzt wird: erwarteter Ankunfts- beziehungsweise Bedarfszeitpunkt des **bereits bekannten** Werkstücks sowie notwendige Kommissionier-, Fahr- und Übergabevorlaufzeit. [Ungeklärt] Ob diese Daten tatsächlich in `zusatz` oder anderweitig verfügbar sind.

**3. Auslöser.** [Dokumentierter Entwurf] Ablauf der maximalen Wartezeit **oder** Erreichen einer Dringlichkeitsgrenze. [Neuer Vorschlag] Eine volle Box wird vor Fristablauf ebenfalls freigegeben, damit erfüllbare weitere Sätze nicht blockiert werden; das ist eine zusätzliche explizite Regel, keine bereits getroffene Teamentscheidung.

**4. Entscheidungsablauf.** [Dokumentierter Entwurf] (a) Stationsweise nur zulässige, vollständige und noch nicht gebundene Sätze betrachten. (b) Den Zeitpunkt des ersten erfüllbaren Satzes pro Stationsgruppe festhalten. (c) Weitere passende Sätze, maximal acht Positionen, aufnehmen. (d) Ablauf der Wartefrist und gegebenenfalls den aus real verfügbaren Werkstückdaten abgeleiteten spätesten Regelfreigabetermin beobachten. (e) Beim **früheren** Auslöser die aktuelle kompatible Charge freigeben. [Neuer Vorschlag] Die Auswahl innerhalb einer Gruppe folgt Eingangszeit/ID, mit Überspringen nicht passender größerer Sätze; bei konkurrierenden Stationsgruppen ist der zuerst auslösende Termin vorrangig, bei Gleichstand Stationskennung. Bereits gebundene Chargen bleiben unverändert.

**5. Parameter.** [Dokumentierter Entwurf] `W_max` als maximale **bewusste Bündelungswartezeit**; möglicher Bedarfstermin und benötigte Vorlaufzeit für die Dringlichkeitsgrenze. [Neuer Vorschlag] Ein separat dokumentierter Vorlauf-Sicherheitszuschlag, falls Unsicherheit berücksichtigt werden kann. Illustrativ `W_max=90 s`; dies ist kein gemessener Projektwert. **Keine** erfundenen Dringlichkeitspunkte oder frei skalierten Scores.

**6. Dringlichkeit sachgerecht ableiten.** [Neuer Vorschlag zur Abstimmung] Für einen bekannten erwarteten Satzbedarf `t_bedarf` wird der späteste sinnvolle Freigabezeitpunkt aus `t_bedarf` abzüglich erforderlicher Kommissionier-, Transport- und Übergabevorlaufzeit sowie eines begründeten Sicherheitszuschlags abgeleitet. Diese einfache Rückwärtsterminierung ist eine **operative Freigaberegel**, kein mathematisches Optimierungsmodell. Bei fehlendem `t_bedarf` darf der Zeitpunkt nicht aus zukünftigen, zum Entscheidungszeitpunkt unbekannten Anforderungen konstruiert werden.

**7. Kapazitäten und Konkurrenz.** [Bestehende Vorgabe] Ohne freies Material oder Box keine physische Bindung. Kommissionierplatz, Robotino und Übergabeplatz wirken nach der Freigabe. [Neuer Vorschlag] Der einmal gesetzte Termin wird bei zwischenzeitlichem Box- oder Bestandsmangel nicht zurückgesetzt (A-V04). Gemessene Bündelungswartezeit zählt nur bei erfüllbarem Satz und freier Box. Der Fristablauf dokumentiert dann „Regelwartefrist beendet, Ausführung blockiert“. Die spätere Lieferung kann die Frist überschreiten.

**8. Restbedarfsregel.** [Dokumentierter Entwurf] Ein erfüllbarer Rest wird am Fristablauf oder bei Dringlichkeit auch dann freigegeben, wenn die Box nicht voll ist. [Neuer Vorschlag] Bei unbekannten Ankunftsdaten ausschließlich auf `W_max` und ausdrücklich beschlossene Vollboxfreigabe zurückfallen. **Kein** Ersatz einer fehlenden Frist durch perfekte Kenntnis des zukünftigen Bedarfseingangs.

**9. Theoretisch erwartbare Stärke und Grenze.** [Eigene Übertragung] Die Regel adressiert verspätete kleine Restchargen gezielter als eine reine Mengenschwelle. Bei ungenauen Bedarfsterminen oder Vorlaufzeiten kann der Dringlichkeitstermin falsch liegen; eine Frist begrenzt nie Material- oder Ressourcenmangel [Q07, Q08].

**10. Beispiel.** **Illustrativ:** A(3) wird bei t=0 erfüllbar; `W_max=90 s`. B(2) kommt t=20 hinzu, C(3) t=40. Ohne frühere dringliche Bedarfe könnte eine voll belegte Box bei t=40 vorfristig freigegeben werden, **nur wenn** die Vollboxregel beschlossen ist. Bleibt F(1) als einziger Satz an RASS3 ab t=10 offen, löst seine Frist bei t=100 eine Regelfreigabe aus. Wenn bei t=100 keine Box frei ist, findet **keine** garantierte tatsächliche Übergabe bei t=100 statt.

**11. Offene Fragen.** Ist `W_max` am ersten erfüllbaren Satz oder ursprünglichen Bedarfseingang zu verankern? Welche Werkstückdaten sind bekannt? Wie wird Unsicherheit behandelt? Ist die Vollboxfreigabe erwünscht? Welche Auslöser greifen nach einem Vorratsmangel? Wie erhalten konkurrierende Stationen knappe Boxen, ohne den Referenzfahrzeugplan zu verändern?

---

### V4: Eigene Verbesserung, Kandidaten K1 bis K3

**Status des gesamten V4:** [Dokumentierter Entwurf] Drei Kandidaten, **keiner ist ausgewählt oder implementiert**. Ein fachlich begründeter Vorschlag ist erlaubt, keine abschließende Teamentscheidung. Die Kandidaten verändern ausschließlich **stationsreine Chargenbildung und Regelfreigabe**, nicht Fahrzeugsteuerung, Montagepriorität oder Materialnachschub.

#### K1: Bedarfsgekoppelte Füllschwelle

**Grundidee.** [Dokumentierter Entwurf] Die Füllschwelle richtet sich nach bekannten oder mit expliziter Unsicherheit prognostizierten Sätzen, die bis zu einer nächsten möglichen Lieferung benötigt werden. Statt einer stationsübergreifend festen Zahl würde sie je Station und Situation angepasst.

**Literaturanschluss.** [Eigene Übertragung aus Q01, Q03, Q05, Q09] Bedarf, Feeding-Policy und Transporthäufigkeit sind gekoppelt. **Keine** der Quellen beweist eine konkrete K1-Regel für die Festo-Laborfabrik.

**Informationen.** [Bestehende Vorgabe] Standardzustand und Satzbelegungen. [Neue zusätzliche Voraussetzung] Tatsächlich verfügbare Prognose der Werkstückankünfte, bekannte Liefermöglichkeiten und eine Interpretation ihrer Unsicherheit. „Nächste mögliche Lieferung“ darf keine versteckte zukünftige Fahrzeugzuordnung sein.

**Auslöser und Entscheidungsablauf.** [Neuer Vorschlag] Bei Neuplanungsereignis erwartete **bereits bekannte** Bedarfe bis zur nächsten realistisch beschriebenen Liefergelegenheit je Station in Positionen erfassen; daraus eine zulässige Schwelle bis acht Positionen bestimmen; entsprechend V2 passende vollständige Sätze auswählen; bei erreichter Schwelle freigeben. [Neuer Vorschlag] Rest über eine explizite Frist oder tatsächlich bekanntes Bedarfsende behandeln. Ohne diese Zusatzregel verbleibt das V2-Restproblem.

**Parameter und Kapazitäten.** [Neuer Vorschlag] Prognosehorizont und Mindest-/Maximalfüllung, gegebenenfalls `W_rest`. Bei fehlenden Boxen keine Bindung. Lieferzeiten müssen sich aus bekanntem Zustand oder nachvollziehbarer Schätzung ergeben.

**Konkurrenz/Restbedarf.** [Neuer Vorschlag] Gleiche Termin-/ID-Auswahl innerhalb der Station; Stationenkonkurrenz nach dem früheren bekannten Bedarf, bei Gleichstand Stationskennung. Ohne bekannte Bedarfszeit auf eine ausdrücklich beschlossene Restregel zurückfallen, nicht Zukunftswissen annehmen.

**Stärke/Grenze.** [Eigene Übertragung] Kann die Menge näher am bekannten realen Bedarf ausrichten. Hohe Anforderung an Prognose- und Lieferterminverfügbarkeit; Prognosefehler führen zu Fehlbündelung.

**Beispiel.** **Illustrativ:** Für RASS1 sind bis zur nächsten zulässigen Liefergelegenheit nur A(3) und B(2) bekannt, C(3) ist noch **nicht** bekannt. K1 könnte fünf Positionen als situationsbezogene Schwelle behandeln. Es wäre unzulässig, t=40 für C vorzeitig als sichere Information einzusetzen.

**Offen:** Herkunft und Qualität der Prognose, zulässige Lieferdefinition, Restfrist.

#### K2: Rückwärtsterminierte Dringlichkeit mit Auffüllen

**Grundidee.** [Dokumentierter Entwurf] Der dringendste bekannte vollständige Satz einer Station bestimmt den spätesten noch sinnvollen **Regelfreigabezeitpunkt**. Bis zu diesem Zeitpunkt dürfen passende weitere vollständige Sätze derselben Station die Box auffüllen.

**Literaturanschluss.** [Eigene Übertragung aus Q08, Q09, Q11, Q12] Ein befristetes Warten vor Batching und die Verbindung von Zeit- und Mengenauslösern sind wissenschaftlich etablierte Konzepte. **Nicht** bewiesen ist, dass rückwärtsterminierte K2-Regeln in der Festo-Laborfabrik optimal sind.

**Informationen.** [Bestehende Vorgabe] Offene Anforderungen, Identität, Belegung, Bestand, freie Boxen. [Neue Voraussetzung] Verifizierbarer erwarteter Materialbedarfstermin je bereits bekanntem Werkstück und plausibler Vorlauf für Kommissionieren, Fahrt, Übergabe. [Neuer Vorschlag] Unsicherheit als sichtbar dokumentierter Zuschlag oder Bandbreite, kein als Fakt behaupteter 130-Sekunden-Fahrwert.

**Auslöser und Entscheidungsablauf.** [Neuer Vorschlag] (a) Je Station erfüllbare Sätze identifizieren. (b) Für Sätze mit bekanntem Bedarf den spätesten Regelfreigabetermin durch Rückrechnung aus Bedarfstermin und erforderlichem Vorlauf ableiten. (c) Den früheren Zeitpunkt aus dem frühesten Bedarfstermin abzüglich Vorlauf und der festen Basisfrist als Grenze nehmen (Abgrenzungsvorschlag, siehe oben). (d) Bis dahin nach Eingang/ID mit passenden voll erfüllbaren Sätzen auffüllen. (e) Bei Terminablauf oder vorher voller Box, **falls als Regel beschlossen**, freigeben. (f) Für Sätze ohne Bedarfstermin die feste Basisfrist verwenden, sofern der Abgrenzungsvorschlag beschlossen wird. Keine Bindung ohne Material/Box; bereits beauftragte Fahrten bleiben fix.

**Parameter.** [Neuer Vorschlag] Bedarfstermin, Vorlaufbeiträge, nachvollziehbarer Sicherheitszuschlag, die feste Basisfrist `W_max` auch für unbekannte Bedarfstermine. Diese Werte sind **nicht** kalibriert und erfordern Teamabstimmung.

**Konkurrenz/Restbedarf.** [Neuer Vorschlag] Falls mehrere Stationen freigabereif sind, zuerst die mit dem frühesten verifizierten Freigabetermin, bei Gleichstand Stationskennung. Ohne freie Box bleibt die Station offen und als überfällig markiert. Ein Rest wird bei Frist ausgelöst, soweit erfüllbar. Das setzt **keine neue Fahrzeugzuordnung** fest.

**Stärke/Grenze.** [Eigene Übertragung] Fachlich klarer Bezug zur Dringlichkeit eines bekannten Werkstücks und zur Nutzung verbleibender Bündelungszeit. Hauptgrenze ist der nicht gesicherte Ankunftsdatensatz; ungenaue Vorläufe können zu verspäteter oder unnötig früher Regelfreigabe führen [Q07].

**Beispiel.** **Illustrativ:** Für A(3) ist t=300 s als belastbarer Bedarfstermin bekannt, die angenommene gesamte Vorlaufzeit sei 180 s. Bei einer ebenfalls illustrativen Basisfrist von 150 s ab t=0 würde K2 t=120 s als früheren **Regelfreigabezeitpunkt** ansetzen. Bei einer Basisfrist von 90 s bliebe dagegen t=90 s maßgeblich. B(2) und C(3) können zuvor die Box auffüllen, wenn sie rechtzeitig bekannt und erfüllbar sind. Die Zahlen sind **frei illustrativ**. Wenn keine Ankunftszeit existiert, darf der Termin t=120 s nicht erfunden werden.

**Offen:** Vorlaufmessung (L-02, L-03, A-07), Ankunftsfeld, Regeln für unsichere und unbekannte Termine, Zusammenwirken mit V3.

#### K3: Engpassabhängige Bündelung

**Grundidee.** [Dokumentierter Entwurf] Bei reichlich vorhandener Versorgungskapazität kleinere Chargen früher freigeben; bei knappen Boxen, Kommissionierplätzen oder Fahrzeugen stärkere Bündelung anstreben.

**Literaturanschluss.** [Eigene Übertragung aus Q01, Q05, Q07] Ressourcenknappheit kann Antwortzeiten beeinflussen. Die Studien geben **keine** direkt übernehmbare K3-Umschaltschwelle vor.

**Informationen.** [Bestehende Vorgabe] Freie Boxen, freie Kommissionierplätze, freie Fahrzeuge, freie Übergabeplätze je Station. **Keine Zukunftsprognose nötig** für eine rein gegenwartsbezogene Variante. [Offen] Reicht ein momentaner Frei-Zähler als Belastungsindikator oder sind Warteschlangenlängen nötig?

**Auslöser und Entscheidungsablauf.** [Neuer Vorschlag] Bei zulässigem Neuplanungsereignis eine **vorab definierte** Engpassklasse aus verfügbaren Ressourcen ableiten; bei normalem Zustand niedrige Füllschwelle, bei Engpass höhere Füllschwelle; erfüllbare Sätze stationsrein nach deterministischer Ordnung sammeln. [Neuer Vorschlag] Jede Schwelle benötigt eine maximale Wartefrist, sonst kann hohe Kapazitätsknappheit zu unbegrenztem Rückhalt führen. Häufiges Hin- und Herschalten muss vermieden werden; bestehende Chargen werden dabei nicht neu geöffnet.

**Parameter.** [Neuer Vorschlag] Wenige klar erklärte Zustandsgrenzen, `F_niedrig`, `F_hoch` und `W_rest`; alle nur als diskrete Verfahrensparameter, kein lernendes oder mathematisches Optimierungsmodell.

**Konkurrenz/Restbedarf.** [Neuer Vorschlag] Erst die vorher definierte Freigabereife prüfen, dann bei Ressourcenwiederfreigabe neu entscheiden. Rest spätestens nach beschlossener Regelwartefrist freigeben, sofern bindbar. Es bleibt offen, ob Ressourcenknappheit höhere Bündelung bei knapper Boxzahl überhaupt verbessert.

**Stärke/Grenze.** [Eigene Übertragung] Direkt mit einem Teil der schon vorhandenen Schnittstellenwerte realisierbar. Aber eine hohe Füllschwelle bei Engpass kann den dringendsten Satz zusätzlich verzögern, und freie Fahrzeugzahl allein kann bereits anstehende Aufgaben verschleiern.

**Beispiel.** **Illustrativ:** Bei vier freien Boxen gelte versuchsweise `F_niedrig=3`, bei nur einer freien Box `F_hoch=6`. A(3) würde im ersten Zustand unmittelbar freigabereif, im zweiten auf passende weitere Sätze warten. Daraus folgt **keine** automatische Verbesserung, selbst wenn weniger Fahrten entstehen.

**Offen:** Zustandsdefinition, Schwellwerte, Stabilität des Umschaltens, Fristschutz, Gefahr einer Benachteiligung einzelner Stationen.

#### Vergleich der V4-Kandidaten

| Kriterium | K1: bedarfsgekoppelte Füllschwelle | K2: rückwärtsterminierte Dringlichkeit | K3: engpassabhängige Bündelung |
|---|---|---|---|
| Fachlicher Schwerpunkt | Erwartete Bedarfsmenge bis zur Lieferung | Spätester sinnvoller Freigabetermin des dringendsten Satzes | Aktuell knappe Versorgungskapazität |
| Literaturanschluss | Q01, Q03, Q05, Q09 | Q07, Q08, Q11, Q12 | Q01, Q05, Q07 |
| Mit aktueller Standardschnittstelle allein vollständig ausführbar? | **Nein** | **Nein** | **Potenziell ja**, wenn Regeln allein auf vorhandenen Frei-Zählern beruhen |
| Erforderliche Zusatzinformation | Bedarfsprognose und Beschreibung „nächste mögliche Lieferung“ | Verifizierbarer Bedarfstermin und logistische Vorlaufzeit | Ggf. Warteschlangeninformationen für belastbare Engpassdiagnose |
| Restbedarfsrisiko | Ja, wenn Prognose-/Schwellenwert nicht erreicht | Für unbekannte Bedarfstermine zusätzlicher Fristschutz nötig | Ja, wenn hohe Engpassschwelle ohne Frist |
| Verfahrensbezogene Komplexität | Dynamische Prognoseschwelle | Rückwärtsterminierung und Auffüllen | Zustandsklassifikation und Schwellenwechsel |
| Wichtigster Fehlermodus | Unbekannter Zukunftsbedarf wird scheinbar gewusst | Vorlauf oder Bedarfszeitpunkt unzuverlässig | Engpass wird durch Warten verschärft |
| Nicht Teil des Kandidaten | Zukünftige Nachfrage erzeugen oder Fahrzeugrouten planen | Freigabetermine als Liefergarantie darstellen | Fahrzeugdisposition oder Bestandsnachschub optimieren |

**Vorschlag zur Teamabstimmung, keine Entscheidung:** K2 bleibt ein bedingter Kandidat. Nur gegenüber einer zeitbasierten V3-Basis wäre die bedarfsabhängige Verkürzung des Fensters ein klar benannter zusätzlicher Mechanismus. Wird V3 bereits mit derselben Dringlichkeitslogik umgesetzt, ist die Eigenständigkeit nicht gegeben. Ankunfts- und Vorlaufdaten sind nicht gesichert. K3 kann alternativ anhand vorhandener Frei-Zähler vertieft werden, ohne Wirksamkeit zu behaupten. K1 setzt ebenfalls zusätzliche Prognoseinformationen voraus. Die Auswahl bleibt offen.


## 4. Enumeration eines kleinen Falls

Verpflichtend laut gemeinsamer Anforderung: Für einen kleinen Fall werden alle zulässigen Chargenbildungen vollständig aufgezählt und mit dem Ergebnis des Verfahrens verglichen. Vorschlag: vier bis sechs Sätze an zwei Stationen, eine Entscheidungssituation. Zu dokumentieren sind die Zahl der Alternativen, die Zielgröße und der Entscheidungshorizont. Eine optimale Einzelentscheidung beweist keinen insgesamt optimalen Ablauf.

## 5. Parameter

| Verfahren | Parameter | Wertebereich | Festlegung |
|---|---|---|---|
| V2 | `fuellschwelle_positionen` | 2 bis 8, je Station an der Satzgröße auszurichten | auf dem Szenario `kalibrierung` |
| V2 | Höchstwartezeit der Restbedarfsregel | offen | auf dem Szenario `kalibrierung` |
| V3 | `max_wartezeit_s` oder Dringlichkeitsregel | offen | auf dem Szenario `kalibrierung` |
| V4 | je nach Kandidat | offen | auf dem Szenario `kalibrierung` |

Parameterwahl und abschließende Prüfung erfolgen auf getrennten Szenarien.
