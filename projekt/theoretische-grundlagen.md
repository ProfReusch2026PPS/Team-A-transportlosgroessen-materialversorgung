# Aufgabenpaket 2: Theoretische Grundlagen

**Projekt:** Transportlosgrößen und Materialversorgung, IoT Factory, RASS1 bis RASS3
**Stand:** 17.11.2026
**Wissenschaftliche Quellen:** Die Kennungen `[Q01]` bis `[Q14]` werden in [literatur-ergaenzung.md](literatur-ergaenzung.md) bibliografisch aufgelöst. Die nachstehenden Übertragungen sind ausdrücklich keine Versuchsergebnisse.

## 1. Untersuchungsgegenstand und fachliche Abgrenzung

**Projektvorgabe:** Untersucht werden alternative Regeln, nach denen offene Anforderungen an vollständige Materialsätze zu Chargen zusammengefasst und frühestens für die Versorgung von RASS1, RASS2 oder RASS3 freigegeben werden. Der definierte Materialfluss lautet: Bedarfseingang, Satzvollständigkeit, Chargenbildung, Reservierung, Kommissionierung, Robotino-Direktfahrt, Übergabe, Komponentenverbrauch und Leerboxrückführung. **Nicht** Gegenstand des Verfahrensvergleichs sind eine Änderung der Montagepriorität, der Auftragsfreigabe, der Fahrzeugzuordnung, der Übergabe und der Leerboxrückführung.

**Allgemeine Theorie:** *Assembly Line Feeding* bedeutet die innerbetriebliche Zuführung von Bauteilen und Komponenten an Montageplätze. Wissenschaftliche Arbeiten unterscheiden Bedarfsauslösung, Lagerentnahme, innerbetrieblichen Transport und Bereitstellung am Montageplatz. Diese Schritte können auf unterschiedliche Weise kombiniert werden [Q09, Q10]. Die jüngere Forschung betont, dass Feeding, Flächen- und Ressourcenentscheidungen miteinander verflochten sind [Q01, Q03, Q05, Q06].

**Eigene Übertragung auf die Laborfabrik:** Das zu untersuchende Regelwerk ist die **Chargenbildung und früheste Freigabe** innerhalb einer ansonsten festgelegten Versorgungskette. Es ist kein allumfassendes Materialversorgungskonzept. Eine frühere Chargenfreigabe kann später an einer Kommissionier-, Fahrzeug- oder Übergaberessource warten. Ein geringeres Transportaufkommen kann hingegen die Belastung solcher Ressourcen reduzieren. Beides ist zunächst theoretisch möglich, nicht empirisch nachgewiesen.

## 2. Materialien, Anforderungen, Sätze und Chargen

| Begriff | Präzise Verwendung im Projekt | Typischer Fehler |
|---|---|---|
| Einzelbauteil | Physisches Teil einer Teilenummer, beispielsweise ein Display | Mit einem vollständigen Satz gleichsetzen |
| Materialsatz | Gesamtheit aller benötigten Komponenten für **eine** anforderungsbezogene Montage | Mehrere identische Teile als mehrere Sätze zählen |
| Anforderung | Konkreter Bedarf eines Werkstücks an einer Station, mit Identität und Eingang | Satz ohne ursprüngliche Zuordnung behandeln |
| Charge | Auswahl vollständiger Materialsätze, die gemeinsam in **einer** Transportbox bereitgestellt werden | Mit Produktionslos oder Kommissionierauftrag gleichsetzen |
| Boxposition | Kapazitätseinheit der aktuellen Acht-Positions-Konfiguration | Automatisch von acht vollständigen Sätzen ausgehen |
| Transportlos | Im untersuchten Fall gemeinsam beförderte Charge | Mit Produktionsmenge oder Transferlos vermengen |
| Produktionslos | Gemeinsam geplanter oder hergestellter Fertigungsumfang | Aus Transportboxbelegung ableiten |
| Transferlos | Teilmenge, die zwischen zwei Fertigungsoperationen übergeben wird | Mit der internen Versorgungsbox gleichsetzen |

Ein vollständiger RASS1-Satz kann beispielsweise Mainboard und Display enthalten. Liegt nur das Mainboard vor, ist die Anforderung **nicht erfüllbar**, obwohl ein Teil vorhanden ist. Die Menge des verfügbaren Bestands ist für jede Teilenummer separat zu prüfen. Eine Reservierung bedeutet ausschließlich eine Zuordnung bereits existierenden Bestands und darf dessen physische Menge nicht erhöhen.

**A-06** begrenzt Chargen gegenwärtig auf Sätze derselben RASS-Station. Diese Stationsreinheit wird für die Verfahrensbeschreibung übernommen, ist aber eine abgeleitete Projektannahme und keine nachgewiesene technische Restriktion des MES. Unterschiedliche Satzgrößen sind zulässig, solange die Summe ihrer belegten Positionen die Boxkapazität nicht übersteigt. Eine Box mit acht Positionen kann daher beispielsweise mit Satzgrößen `3 + 3 + 2` voll sein, während `3 + 3 + 3` unzulässig ist.

## 3. Kitting und vollständige Materialsätze

**Allgemeine Theorie:** *Kitting* ist die bedarfsbezogene Zusammenstellung unterschiedlicher Komponenten zu einer abgestimmten Einheit für die Montage. Beim *Line Stocking* werden einzelne Komponenten typenrein an oder nahe der Linie bevorratet. Bozer und McGinnis vergleichen diese Prinzipien hinsichtlich Materialhandhabung, Fläche und Umlaufbestand [Q13]. Hanson und Brolin untersuchen Kitting gegenüber kontinuierlicher Versorgung in zwei Automobilfallstudien und betrachten nicht allein den Transport, sondern auch Personalaufwand, Qualität, Flexibilität, Flächen und Bestand [Q14]. Aktuelle Arbeiten differenzieren weitere Kit-Ausprägungen und die Prozesse der Vorbereitung [Q04, Q10].

**Übertragung:** Die vollständige Satzregel der Laborfabrik entspricht dem grundlegenden Gedanken anforderungsbezogener Kits. Es wäre dennoch unpräzise, den gesamten Materialfluss ohne Weiteres mit dem Kitting-System einer der Studien gleichzusetzen. Im Projekt ist die Satzvollständigkeit eine **harte Verwendbarkeitsbedingung**. Davon zu trennen ist die Frage, ob mehrere bereits vollständige Sätze gemeinsam transportiert werden.

**Drei prüfbare Bedarfszustände:**

1. **Grundsätzlich unzulässig:** Ein Satz enthält Komponenten, die an der Zielstation nicht zugelassen sind, oder belegt selbst mehr als acht Boxpositionen. Er darf durch die Verfahrensregel nicht gebunden werden.
2. **Prinzipiell zulässig, momentan nicht erfüllbar:** Mindestens eine erforderliche Komponente fehlt im aktuell freien, unreservierten Bestand. Die Anforderung bleibt offen; sie ist keine absichtlich verzögerte Freigabe.
3. **Vollständig und erfüllbar, bewusst zurückgehalten:** Alle notwendigen Teile sind frei, aber die Bündelungsregel wartet auf weitere Sätze, ein Mengenereignis oder eine Frist. Nur wenn zusätzlich eine freie Box vorhanden ist, ist dieser Zustand echte **Bündelungswartezeit**. Fehlt die Box, gilt Boxwarten; bei Fehlteilen gilt vorrangig Bestandswarten.

Diese Unterscheidung ist für die spätere Interpretation von Zeitpunkten wesentlich. Die Zeit bis zur Vollständigkeit eines Satzes darf nicht als durch V2 oder V3 verursachte Bündelungswartezeit bezeichnet werden.

## 4. Transportlosbildung und Bündelung

**Allgemeine Theorie:** *Transport Batching* bedeutet die Bildung gemeinsamer Beförderungseinheiten aus mehreren Aufträgen, Sendungen oder Bedarfen. Das Einsparpotenzial ergibt sich aus gemeinsam genutzten Transportvorgängen. Eine zusätzliche Konsolidierungswartezeit kann allerdings anfallen, wenn Aufträge erst gesammelt werden. Die Literatur zur Sendungskonsolidierung trennt mengenbasierte, zeitbasierte und kombinierte Zeit-Mengen-Regeln [Q11, Q12]. Die neuere Forschung zu Online-Kommissionierung untersucht die Bedeutung des Wartefensters vor einem Batchstart [Q08].

**Übertragung:** In der Festo-Laborfabrik sind nicht beliebige Teile zusammenzuführen, sondern nur vollständige Sätze. Eine Charge ist zusätzlich nach A-06 auf **eine** Station beschränkt. Anders als bei vielen Distributionsproblemen steht nicht allein die Transportkostensenkung im Fokus, sondern auch die rechtzeitige Verfügbarkeit für einen bestimmten Montagebedarf. Deshalb ist es unzulässig, aus einem allgemeinen Vorteil von Konsolidierung unmittelbar auf eine geringere Versorgungsverzögerung zu schließen.

Eine **gebündelte Direktfahrt** befördert eine Box zu einer Zielstation. Ein *Milk-Run* oder Routenzug dagegen folgt einem geplanten Weg mit mehreren Stopps oder einer Tourenstruktur. Transportbündelung innerhalb einer Box ist nicht dasselbe wie das Zusammenlegen mehrerer Stationen auf eine Route. Für V0 bis V4 bleibt die Fahrzeugzuordnung unverändert; eine Routenneuplanung ist ausgeschlossen.

## 5. Klassen von Freigaberegeln

### 5.1 Einzelbedarfsbezogene unmittelbare Freigabe

Eine sofortige Regel gibt jede zulässige, vollständig bestandsverfügbare Anforderung einzeln zum frühestmöglichen Zeitpunkt frei, ohne weitere Sätze abzuwarten. Das ist das Prinzip von **V1**. „Sofort“ bedeutet hier **Regelfreigabe**, nicht „Robotino fährt sofort“ und nicht „Satz liegt sofort am Montageplatz“.

Theoretische Stärke: kein gezieltes Sammeln voll erfüllbarer Sätze. Theoretisches Risiko: viele kleine Aufträge belasten Boxen, Kommissionierung und Fahrzeuge. Je nach Ressourcenauslastung kann dadurch die physische Antwortzeit anderer Anforderungen steigen [Q07]. Ob das im konkreten Projekt auftritt, ist offen.

### 5.2 Mengenbasierte Freigabe

Bei einer **Mengenschwelle** wird gewartet, bis genügend transportierbarer Bedarf vorliegt. Für das Projekt ist die Menge sinnvollerweise die **Zahl belegter Boxpositionen**, nicht automatisch die Zahl der Sätze. Eine Bedingung „mindestens sechs von acht Positionen“ ist auch dann erfüllt, wenn eine kompatible Kombination sieben Positionen belegt. Bei Satzgrößen `3, 3, 2` kann die Schwelle sechs beispielsweise durch die beiden Dreier-Sätze erreicht werden.

Die zentrale Schwierigkeit besteht im **nicht exakt erreichbaren Schwellenwert** und in dauerhaft unvollständigen Restchargen. Eine reine Mengenregel ohne bekanntes Bedarfsende kann bei geringem Aufkommen unbegrenzt warten. Eine Höchstwartezeit ist eine mögliche Absicherung, verändert das Verfahren fachlich aber zu einer hybriden Regel [Q11, Q12]. Genau dies ist bei **V2** offenzulegen.

### 5.3 Zeitbasierte Freigabe

Eine zeitbasierte Regel misst eine definierte Frist ab einem bestimmten Ereignis, beispielsweise seit der ersten **vollständig erfüllbaren und noch ungebundenen Anforderung** einer Stationsgruppe. Nach Ablauf dieser Frist wird die mögliche Charge freigegeben, auch wenn sie nicht voll ist. Der Ankerzeitpunkt muss verbindlich festgelegt sein. Andernfalls lassen sich zwei Simulationen derselben Regel nicht vergleichen.

Ein Fristablauf ist nur eine Entscheidung über die **Beendigung absichtlichen Wartens**. Er garantiert weder Material, noch eine Box, noch einen freien Kommissionierplatz, noch eine Fahrzeugfahrt, noch einen freien Übergabeplatz. Die reale Lieferzeit kann deutlich länger sein [Q07].

### 5.4 Bedarfs- und dringlichkeitsabhängige Freigabe

Eine bedarfsabhängige Freigabe berücksichtigt den Zeitpunkt, zu dem ein Werkstück seinen vollständigen Satz benötigt. Für die fachliche Logik relevant ist der **bekannte erwartete Zeitpunkt des ersten Materialbedarfs** und die erforderliche Vorlaufzeit für die logistische Abwicklung. Eine Regel kann eine frühere Freigabe verlangen, wenn der Bedarf bevorsteht. Das gehört zum bisherigen Dringlichkeitsentwurf von **V3** und zum Kandidaten **K2**. Die eigenständige Verbesserung ist noch abzugrenzen; der [Vorschlag zur Teamabstimmung](planungsverfahren.md#offene-teamentscheidung-abgrenzung-v3-und-k2) verwendet eine zeitbasierte V3-Basis.

**Informationsgrenze:** Bekanntes oder zuverlässig vorhergesagtes Eintreffen eines **bereits freigegebenen Werkstücks** unterscheidet sich fundamental von künftigem, noch unbekanntem Auftragseingang. Weder die Standardschnittstelle noch die dokumentierten Snapshots garantieren Zugriff auf solche Zeitinformationen. Ohne sie darf keine perfekte Prognose simuliert werden. Ein denkbares Zusatzfeld ist erst nach verifizierter Verfügbarkeit verwendbar.

### 5.5 Hybride Freigabe

Eine Regel ist hybrid, wenn **mindestens zwei eigenständige Auslöser** die Freigabe erlauben, beispielsweise „mindestens sechs Positionen **oder** höchstens 120 Sekunden bewusstes Warten“. Zeit-Mengen-Kombinationen sind in der Konsolidierungsforschung eigenständige Regelklassen [Q11, Q12]. **Nicht** jede Kombination mit einer Kapazitätsgrenze ist schon hybrid: „Die Box darf nie über acht Positionen enthalten“ ist zunächst eine Zulässigkeitsbedingung. Ein Vollbox-Ereignis kann als zusätzlicher Auslöser definiert werden, muss dann aber explizit genannt werden.

Abgrenzung V2/V3: Eine V2-Regel mit Frist ist eine mengengetriebene **hybride** Regel, deren Normalfall die Füllschwelle bleibt. V3 ist primär frist- oder dringlichkeitsgetrieben, die Box darf vor der Frist aufgefüllt werden. Diese Unterscheidung ist fachlich sinnvoll, darf aber nicht über eine verheimlichte Zusatzregel künstlich erzeugt werden.

## 6. Warum Transportzahl, Bestand und Versorgungszeit nicht monoton zusammenhängen

**Begriffliche Trennung:**

- **Transporthäufigkeit:** Wie viele Fahrten beziehungsweise Lieferchargen entstehen?
- **Boxauslastung:** Welcher Anteil der verfügbaren acht Positionen wird in einer transportierten Box genutzt?
- **Gebundener Bestand:** Welche physischen Komponenten sind schon reserviert und deshalb für andere offene Anforderungen nicht mehr frei?
- **Bündelungswartezeit:** Wie lange bleibt ein aus freiem Bestand erfüllbarer Satz bei freier Box allein aufgrund der Chargenregel zurückgehalten?
- **Ressourcenwartezeit:** Wie lange wartet ein freigegebener Auftrag auf Kommissionierung, Fahrzeug oder Übergabe?
- **Physische Versorgungszeit:** Zeitspanne vom relevanten Startpunkt bis zur tatsächlichen Bereitstellung am Übergabeplatz.
- **Versorgungsverzögerung:** Überschreitung des Zeitpunktes, zu dem das Werkstück die Komponenten tatsächlich benötigt. Deren Bestimmung setzt eine belastbare Bedarfszeit voraus.

**Gedankenbeispiel, kein Simulationsergebnis:** Drei vollständige Ein-Positions-Sätze derselben Station werden zu Sekunden 0, 20 und 40 verfügbar. V1 kann drei Einzelfreigaben auslösen. Eine Schwellenregel bei drei Positionen kann eine Box mit drei Sätzen erst ab Sekunde 40 freigeben. Die Schwellenregel spart potenziell Fahrten, verzögert aber die **erste Freigabe**. Bei einem einzigen Engpassfahrzeug ist umgekehrt möglich, dass drei getrennte Freigaben aufeinanderfolgend lange warten, während eine gemeinsame Box die Ressource nur einmal beansprucht. Ohne Kenntnis der realen Folgestufen ist kein allgemeiner Zeitvergleich zulässig.

**Weiteres Gedankenbeispiel:** Wird ein großer Satz früh reserviert, sind seine Komponenten für andere Anforderungen nicht mehr frei. Die Summe physischer Teile bleibt unverändert. Mehr Bündelung kann gleichzeitig die Fahrtenzahl senken und mehr Material in der Warteschlange oder an Übergabeplätzen binden. Studien zu Assembly Line Feeding berücksichtigen deshalb unterschiedliche Ziel- und Einflussgrößen statt einer isolierten Transporthäufigkeit [Q05, Q06, Q14].

## 7. Begrenzte Ressourcen und Konkurrenz zwischen Stationen

In der Projektkonfiguration sind leere Boxen, Kommissionierplätze, Robotino-Fahrzeuge und Übergabeplätze je Station knapp. Ihre Verfügbarkeit kann mit dem vorherigen Materialfluss zusammenhängen, insbesondere mit Entladung und Leerboxrückführung. Die Regeln V0 bis V4 dürfen die festen Zuweisungs-, Übergabe- und Rückführungsregeln nicht heimlich verändern.

Ein freier Materialbestand reicht nicht aus, wenn keine freie Box vorhanden ist. Ein freigegebener Auftrag kann wiederum bei fehlendem Kommissionierplatz oder Robotino warten. Wenn zwei Stationschargen gleichzeitig freigabebereit sind, muss eine **deterministische Reihenfolge für konkurrierende Entscheidungen** festgelegt sein, etwa nach frühestem Fristablauf und bei Gleichstand nach Stationskennung. Dieser Vorschlag darf nicht mit einer neuen Fahrzeugdisposition gleichgesetzt werden. Die konkrete physische Zuteilung verbleibt in der Simulation.

Ein zusätzlicher Zielkonflikt ist **Fairness**: V1 überspringt Anforderungen mit fehlenden Teilen und bedient spätere vollständige Anforderungen. Das verhindert unnötigen Leerlauf, kann aber bei dauerhaft fehlendem Material zu längerem Rückstand älterer Anforderungen führen. Fairness heißt hier zunächst, lange unbehandelte Anforderungen sichtbar zu halten und deren Zustand nachvollziehbar zu machen; eine neue Priorisierungsoptimierung ist nicht Teil von AP2.

## 8. Variabilität und ungesicherte Vorlaufzeiten

Wesentliche Streuungsquellen sind unregelmäßiger Bedarfseingang, unterschiedliche Satzgrößen, Materialfehlmengen, schwankende Kommissionierdauer, Fahrzeugkonkurrenz, Übergabeplatzbelegung und Leerboxrücklauf [Q07]. Die im Projekt gesetzten **130 Sekunden für den Hintransport (A-07)** sind lediglich ein Modellwert. Der indirekt ermittelte Ausgangswert kann bereits Warteanteile enthalten. Er ist **nicht** als empirisch nachgewiesene reine Robotino-Fahrzeit zu interpretieren.

Eine dringlichkeitsabhängige Regel muss unterscheiden zwischen einem nominalen Vorlauf, einem Sicherheitszuschlag und unbekannten Wartezeiten. Wird ein Zuschlag eingesetzt, ist er ein **neuer Modellannahmenvorschlag**, kein gemessener Wert. Außerdem kann ein Zuschlag nicht garantieren, dass ein tatsächlich unvorhersehbarer Engpass ausbleibt. Der 130-Sekunden-Wert darf deshalb nicht ohne Prüfung zu einer exakten Lieferzeit aufgewertet werden.

## 9. Ereignisorientierung und unbeendete Restbedarfe

**Bestehende Vorgabe:** Neuplanung ist nur nach einem Bedarfseingang, dem Ablauf einer Wartefrist oder der Freigabe relevanter Kapazität vorgesehen. Gebundene Chargen und beauftragte Fahrten werden nicht erneut umgeplant.

Für zeitbasierte Verfahren muss eine Wartefrist als tatsächlich auslösbares Ereignis vorliegen. Ohne Frist könnte ein Rest aus weniger als einer Füllschwelle belegten Positionen liegen bleiben, wenn kein weiterer Bedarf eintrifft. Ein ausdrücklich bekanntes **Ende des Bedarfseingangs** kann den Rest freigeben, darf aber nicht aus späteren Simulationsdaten rückwirkend als zu diesem Zeitpunkt bekannt unterstellt werden.

Die Verfahrensfrist ist nicht identisch mit dieser Messgröße. Friststart und Verlaufsspeicherung sind Vorschläge nach A-V04/A-V11 im [Annahmenkatalog](annahmen-und-datenluecken.md).

Die Simulation sollte fachlich den Unterschied zwischen „fertig, aber von der Regel noch zurückgehalten“, „freigegeben, aber wartend auf Ressourcen“ und „noch nicht vollständig aus freiem Bestand bedienbar“ abbilden. Eine Freigabe nach Fristablauf ist bei fehlendem Material nicht automatisch möglich; die Frist begrenzt nur das **bewusste Bündelungswarten nach Erfüllbarkeit**.

## 10. Fachlich gesicherte Aussagen und offene Übertragungen

| Aussage | Status | Grundlage |
|---|---|---|
| Assembly Line Feeding ist mehrstufig und mit Logistikressourcen gekoppelt | **Belegt, allgemein** | Q01, Q05, Q09, Q10 |
| Bündelungswartefenster beeinflussen Online-Auftragsabwicklung | **Belegt, für die untersuchten Systeme** | Q08, Q11 |
| Mengen-, Zeit- und Hybridregeln sind unterscheidbar | **Belegt, allgemeine Fachtypologie** | Q11, Q12 |
| V1 kann im Projekt viele kleine Fahrten auslösen | **Theoretisch abgeleitet** | V1-Regel, Q07 |
| V2 kann bei schwacher Nachfrage Restbedarf unbegrenzt zurückhalten | **Logische Folge einer reinen Schwelle** | V2-Entwurf; keine weitere Nachricht vorausgesetzt |
| Höchstwartezeit garantiert rechtzeitige physische Ankunft | **Nicht belegt und sachlich falsch als allgemeiner Satz** | Q07; begrenzte Ressourcen |
| K2 ist im Projekt besser als K1 oder K3 | **Ungeklärt** | Kein Simulationsvergleich, keine Prognosedaten validiert |
| V0 bildet das allgemeine MES-Verhalten nach | **Ungeklärt** | Nur eng begrenzte Beobachtung vom 09.11.2026 |

## 11. Bezug auf die Arbeitsvorlagen

Die Theorie erklärt Verfahrensklassen, nicht ihre Parametrierung. Konkrete Regeln, Statuskennzeichnungen und kleine Beispiele stehen in [planungsverfahren.md](planungsverfahren.md). Verfahrensbezogene Annahmen und Datenlücken stehen in [annahmen-und-datenluecken.md](annahmen-und-datenluecken.md); der Suchweg und die wissenschaftlichen Zugriffslücken in [literaturrecherche.md](literaturrecherche.md).
