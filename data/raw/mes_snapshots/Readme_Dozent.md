\# Inhalte und Bedeutung des Ordners



\## Datenbank-Exporte: Überblick



Die vorliegenden Datenbank-Exporte sind Momentaufnahmen (Snapshots) der MES-Datenbank. Zu Beginn wurden zwei Aufträge angelegt: Auftrag 1 umfasst ein Standardprodukt (WPNo 1000), Auftrag 2 umfasst zwei Standardprodukte.



\### Was sich daraus ableiten lässt



Anhand der Snapshots lassen sich insbesondere Kommissionieraufträge und Belegungen der Tabellen `Order`, `OrderPos`, `BufferPos` etc. nachvollziehen. Deren Änderungen werden aktuell nicht persistiert. Zudem zeigt sich, inwieweit Aufträge automatisch zusammengefasst werden. Der letzte Export enthält insbesondere in den `tblfin\*`-Tabellen die vollständige Produktionsabfolge aller drei Produkte inklusive der Zeiten je Arbeitsschritt (Operation).



\### Laden der Datei



Die einfache Option ist, die Anleitung zum Laden eines Datenbank-Dumps zu verwenden. Dabei können entweder mehrere Datenbanken mit verschiedenen Zuständen geöffnet oder die Dumps nacheinander geladen werden. Bei Bedarf lassen sich einzelne Tabellen mit Python nach SQLite exportieren.

