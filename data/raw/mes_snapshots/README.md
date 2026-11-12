# MES-Snapshots (lokal, nicht versioniert)

In diesem Ordner liegen die sechs SQL-Dumps der MES-Datenbank `MES4` vom 09.11.2026. Die Dumps werden **nicht** versioniert (`.gitignore`) und kommen nicht per `git pull`. Versioniert sind nur diese Datei und die Beschreibung des Dozenten ([Readme_Dozent.md](Readme_Dozent.md), ursprünglich `Readme.md`).

## So kommen die Dumps hierher

1. Archiv `MES_database_snapschots.zip` aus dem Kursmaterial herunterladen.
2. Entpacken und die sechs `.sql`-Dateien unverändert in diesen Ordner kopieren (Dateinamen nicht ändern).
3. Prüfsummen vergleichen, dann importieren:

```text
.venv\Scripts\python -m matsim.daten importiere
```

Der Import schreibt je Dump eine SQLite-Datei nach `data/interim/` und trägt Quelle und Prüfsumme in die Tabelle `_snapshot_meta` ein. Die Dumps selbst werden nie verändert.

## Dateien

| Datei | Größe (Bytes) | SHA-256 |
|---|---:|---|
| `DB_Export_2026.11.09_1516_production started and comissioning Rass1 ongoing.sql` | 9609492 | `49fe5c5c51a241a63a0f189b7cb8ce5756b8c86286950cd9ec0ff0a7310d08e2` |
| `DB_Export_2026.11.09_1522_comissioning Rass2 ongoing.sql` | 9616710 | `1ecd63f2ebd234cbbfd59e04a566e8ef4a2f6933b866336037520e465287e690` |
| `DB_Export_2026.11.09_1525_comissioning Rass2 still ongoing.sql` | 9618803 | `2def4b0de19eea3656808e5f4ed403f700cb94ac8cae08ea9d35e453d4a49712` |
| `DB_Export_2026.11.09_1536_comissioning Rass3 ongoing.sql` | 9625273 | `88f6ecf11034fdaf71f8aa1f28a94e2f217ae6c35442865ec506f4894878eb2d` |
| `DB_Export_2026.11.09_1541_comissioning Rass3 still ongoing.sql` | 9629040 | `3fbdf345517225911e66b82ef15b59e9e1f98b70a98f9e6e97b8ba38bb83496b` |
| `DB_Export_2026.11.09_1557_production_finished.sql` | 9637775 | `9e3a46c7cafbb03844540354fd1e0d357ac001b1552c0b39ac9a6a82a071ec46` |

Prüfsumme unter Windows: `certutil -hashfile "<Datei>" SHA256`, unter macOS und Linux: `sha256sum "<Datei>"`.

## Zeitstempel und Kurznamen

| Kurzname nach Import | Zeitpunkt | Zustand laut Dateiname |
|---|---|---|
| `2026-11-09_1516` | 09.11.2026, 15:16 | Produktion gestartet, Kommissionierung RASS1 läuft |
| `2026-11-09_1522` | 15:22 | Kommissionierung RASS2 läuft |
| `2026-11-09_1525` | 15:25 | Kommissionierung RASS2 läuft weiter |
| `2026-11-09_1536` | 15:36 | Kommissionierung RASS3 läuft |
| `2026-11-09_1541` | 15:41 | Kommissionierung RASS3 läuft weiter |
| `2026-11-09_1557` | 15:57 | Produktion beendet |

Format: mysqldump 10.16 (MariaDB 10.4.32), UTF-8 mit BOM, 64 Tabellen. Der Import übernimmt 62 Tabellen; `tblcustomer` und `tblusercontrol` enthalten Namen und E-Mail-Adressen und werden nie exportiert.
