# Befehle kurz (Alltag)

Auszug aus `05_Datenbank-und-Tools` (Referenz – nur gezielt durchsuchen). Arbeitsordner `/home/claude/mtg`; Hilfe: `python3 <werkzeug>.py <befehl> -h`.

## Start und Schreiben

| Befehl | Zweck |
|---|---|
| `start.py admin\|user [--ohne-db]` · `start.py gast --name N` · `start.py db` | Sitzungsstart in einem Befehl (`05a`) · Gast · Stand des Datenbank-Baus |
| `git -C /home/claude/mtg-daten …` (Befehl in `05a`, Abschnitt 6) | Ende jeder Schreibrunde: `git push` ins Daten-Repo |

## protokoll.py

| Befehl | Zweck |
|---|---|
| `offen [--deck D]` · `zeigen [--deck D] [--typ T] [--suche S] [--letzte N]` · `register [--deck D]` | offene Punkte · Protokoll 09 · Deckregister |
| `neu --typ <Typ> --thema <T> --zeile "…"` | Protokolleintrag |
| `idee-neu --deck D --inhalt T --status S` · `idee-status <ID> <Status>` · `idee-entfernen <ID>` | Ideen (feste Status, `10`) |
| `kauf-neu --idee ID --karte K [--anzahl N --preis 1,23 --art Standardland]` · `kauf-status --idee ID bestellt` · `kauf-entfernen --idee ID [--karte K]` | Kaufliste (`data/kaufliste.csv`) |
| `vormerken --idee ID --karte K` · `vormerkung-entfernen --idee ID [--karte K]` | Vormerkungen (`data/vormerkungen.csv`) |
| `nachziehen --was T --aufgabe T` · `nachziehen-erledigt <Teil>` | „In Moxfield nachziehen“ |
| `primer [--deck D]` | Primer je Deck, Warnung bei veraltetem Primer |

## deckbau.py

| Befehl | Zweck |
|---|---|
| `passung <deck>` · `bracket <deck> [--neu <entwurf>] [--ziel 1–5]` | Passungs-Check · Ausgangsbracket und Bracket-Wächter |
| `commander "<Name>"` · `commander-suche --thema <slug> \| --farben GW --nur-besitz` · `synergie <Commander\|Deck>` | Steckbrief · Commander finden · freie Karten mit Bezug |
| `kandidaten "<Name>" --weg 1\|2` · `upgrade <deck> --stufe 0\|1 --ziel "muster+muster" …` | Kartenpool · Upgrade mit Raus-Sperren und Ziel-Abgleich (`--ziel` Pflicht) |
| `alternativen "<Karte>" [--farben RWB]` · `oracle <Karte …>` · `oracle --alt <Soll-Stand> --neu <Entwurf>` | günstigere Karten gleicher Rolle · Oracle-Text (Pflicht vor jeder Beschreibung) |
| `pruefen <entwurf> --ersetzt <deck> [--idee I-nnn] [--budget 140]` · `abnahme <deck\|entwurf> [--basis <deck>]` | Qualitätskontrolle (mit Budget) · Bracket-3-Abnahme |
| `tauschrunde <deck> --neu <entwurf> --paare <datei>` · `--antwort "1j 2n 3s 4e"` · `--karte N` · `--alle` · `--paar-neu "A -> B"` · `--stand` · `--ergebnis` · `--ohne-bild` | Routine Tauschrunde (`08a`, 5.2) – Bild per `SendUserFile`, Frage im Text |
| `gegenlauf <deck> --ziel "…" --wortlaut "…"` · `gegentest <Projekt> <K1> <K2> <K3> --basis <deck>` | Routine Gegenlauf (`08a`, 5.1) |
| `fazit --neu <entwurf_drucke> --alt <deck> --out fazit.md` · `erklaerung <entwurf>` | Fazit-Entwurf · Datenbasis der Kartenerklärungen |
| `verkauf [--min-preis 1] [--out out/verkauf.txt]` | Verkaufsprüfung Kat. 1–3 |

## mtg_db.py

| Befehl | Zweck |
|---|---|
| `frei <Karte …>` · `suche --tag removal --farben RWB --nur-frei` · `exemplare <Karte\|Deck>` | Habe ich X frei? · Funktionssuche · physische Exemplare |
| `besitz <deck>` · `laender [<deck>] --plan "Plains=12"` · `bracket <deck>` · `export <deck> [--sets]` | Fehlendes · Standardländer · Bracket-Daten · Einfügeblock |
| `drucke <entwurf> --deck D --out <entwurf_drucke>` · `snapshot decks --deck D` | Entwurf mit eigenen Drucken · Soll-Stand schreiben |
| `scan <manabox.csv> [--buchen …]` · `vergleich <alt> <neu>` · `basis-teilen <csv> --out data` · `moxfield-export <out.csv>` | Scan buchen · Abgleich · neue Basis · Bestand für Moxfield |

## kartenbilder.py · archetypen.py · simulation.py

| Befehl | Zweck |
|---|---|
| `kartenbilder.py lieferung fazit.md --neu <entwurf_drucke> --alt decks/<d>.txt --out out/<d>` | Fazit-, Tausch-, Deck-PDF und TXT in einem Lauf |
| `kartenbilder.py einkauf --kaufliste data/kaufliste.csv --ideen projekt/10_Geplante-Kaeufe-und-Ideen.md --out out/einkauf` · `kartenbilder.py verkauf <liste> --out …` | Einkaufs- und Verkaufs-PDF |
| `archetypen.py deck <deckdatei> [--archetyp A]` · `archetypen.py profil --out profil/12_Sammlungsprofil.md --raster-out profil/12a_Deck-Raster.md` | Pakete eines Decks · Sammlungsprofil |
| `simulation.py <deck\|entwurf> [--n 5000]` | Konsistenz-Simulation der ersten Züge |
