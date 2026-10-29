# Import-Formate & Bestandsmodell

**Stand:** 29.10.2026 (Basis heißt `basis.csv`) · Projekt = Hauptdatenbank; Moxfield = externe Datenbank (Ziel der Exporte); ManaBox = Zulieferer der Scans · Verarbeitung mit `mtg_db.py` (siehe `05_Datenbank-und-Tools`)

---

## 0. Wichtig zum Bestand des Nutzers

- **Das Projekt ist die Hauptdatenbank** (Festlegung des Nutzers, 26.10.2026). Alle Änderungen an Bestand und Decks werden hier beschlossen und gebucht; Richtung immer **Projekt → Moxfield**. Änderungen in Moxfield wirken hier nicht – außer bei Fehlerkorrektur oder wenn der Nutzer einen Moxfield-Export ausdrücklich zum Überschreiben der Daten hier nutzt.
- **Begriffe:** Bestand = Deckkarten + Sammlung; Sammlung = freie Karten. Bestand = Basis (`claude/sammlung/basis.csv`, eine Moxfield-CSV) + Buchungsjournal (`claude/sammlung/buchungen.csv`).
- **ManaBox** liefert nur Scans:
  - **Neue Karten:** `mtg_db.py manabox-zu-moxfield` → Zeilen als Zugang in `buchungen.csv` buchen; die erzeugte Moxfield-CSV (und ggf. Deck-TXT) bekommt der Nutzer zum Nachziehen in Moxfield.
  - **Neuscan eines vorhandenen Decks:** nicht buchen – nur mit dem Soll-Stand vergleichen und den Soll-Stand nach Klärung korrigieren.
- **Frei** ist nur, was in keinem Deck steckt und nicht in `10_Geplante-Kaeufe-und-Ideen` vorgemerkt ist; für Upgrade-Stufe 0, Weg 1 und Tauschkandidaten nur freie Karten (Liste `07_Sammlung-Frei.csv` bzw. `suche --nur-frei`).
- **Standardländer** sind wahrscheinlich nicht vollständig eingescannt → beim Deckbau Bestand prüfen und Nachkauf separat vorschlagen (`laender --plan`).

---

## 1. Dateien bereitstellen

- **Zur Analyse:** Datei in den Chat hochladen.
- **ManaBox-Scans:** ein Binder bzw. eine Liste je Deck oder Zugang, Name = Deckname bzw. Commander; als CSV exportieren und hochladen.
- **Belege** (z. B. Cardmarket-Verkäufe/-Käufe): Screenshot oder Text genügt; gebucht wird mit Belegnummer, Datum und Preis, ohne Adressdaten.
- **Moxfield-Exporte** nur noch als Ausnahme (Fehlerkorrektur oder ausdrückliche Überschreibung). Dateinamen dann unverändert lassen – bei Moxfield enthalten sie den Decknamen (als Slug) und das Exportdatum, z. B. `mardu-surge-…-precon-20261025-163721.txt`.

---

## 2. ManaBox – Scan-Export als CSV (mit echter Datei geprüft 26.10.2026)

**Export:** Collection → ⋯ (oben rechts) → Export → CSV. Ganze Sammlung (mit Binder-Name) oder nur ein Binder/eine Liste (dann vorher den Binder öffnen).

Kopfzeile des Nutzers (Export einer Liste): `Name, Set code, Set name, Collector number, Foil, Rarity, Quantity, ManaBox ID, Scryfall ID, Purchase price, Misprint, Altered, Signed, Condition, Language, Proxy, Purchase price currency, Added`

| Spalte | Inhalt / Werte |
|---|---|
| Name | Kartenname (Englisch) |
| Set code / Set name | Set-Kürzel (Großbuchstaben) / Set-Name |
| Collector number | Sammlernummer |
| Foil | normal · foil · etched |
| Rarity | Seltenheit |
| Quantity | Anzahl |
| ManaBox ID | interne ID |
| Scryfall ID | **eindeutige Druckversion** – wichtigster Schlüssel (100 % Zuordnung im Test) |
| Purchase price / Purchase price currency | von ManaBox eingetragener Preis beim Scannen / Währung (EUR) |
| Misprint · Altered · Signed · Proxy | true/false |
| Condition | near_mint · excellent · good · light_played · played · poor (Cardmarket-Skala) |
| Language | Sprachcode (z. B. de) |
| Added | Zeitpunkt des Scans (UTC) |
| Binder Name / Binder Type | nur beim Gesamtexport der Sammlung; fehlen beim Export einer einzelnen Liste |

- ManaBox wählt beim Scannen eine Druckversion mit passendem Bild – Set/Nummer, teils auch die Sprache, können vom tatsächlichen Druck abweichen. Name und Oracle-ID stimmen immer; für Besitz und Deckbau ist das egal, für Preise der genauen Druckversion nicht.
- **Umrechnung ins Moxfield-Format** (`manabox-zu-moxfield`): Zustand Cardmarket → Moxfield (near_mint → Near Mint, excellent → Good (Lightly Played), good/light_played → Played, played → Heavily Played, poor → Damaged), Sprache ausgeschrieben (de → German), Set-Code klein. `Tradelist Count` wird von Moxfield beim Import nicht übernommen (Test 26.10.).

**ManaBox-Decks als Text:** Format nicht dokumentiert. Unterstützt werden `1 Name`, `1x Name`, `(SET) 123`, `[SET] 123`, `*F*`, `SB:`-Zeilen und Überschriften wie `Commander (1)`, `Mainboard`, `Sideboard`, `Maybeboard` (`Tokens` werden ignoriert). Ohne Commander-Markierung erkennt das Tool den Commander (Farbidentität + Deckname) und meldet das zur Bestätigung.

---

## 3. Bestand im Moxfield-CSV-Format (Basis, Buchungen, Moxfield-Import/-Export; geprüft 25./26.10.2026)

Kopfzeile: `"Count","Tradelist Count","Name","Edition","Condition","Language","Foil","Tags","Last Modified","Collector Number","Alter","Proxy","Purchase Price"` – alle Felder in Anführungszeichen.

| Spalte | Inhalt / Werte |
|---|---|
| Count | Anzahl (in `buchungen.csv`: negativ = Abgang) |
| Tradelist Count | davon zum Tausch (in den Exporten des Nutzers überall = Count; Importwert wird von Moxfield ignoriert) |
| Name | Kartenname (Englisch, bei doppelseitigen Karten `A // B`) |
| Edition | Set-Kürzel in Kleinbuchstaben = Scryfall-Code |
| Collector Number | Sammlernummer (auch Formen wie `157p`, `NPH-123`) |
| Condition | Mint · Near Mint · Good (Lightly Played) · Played · Heavily Played · Damaged |
| Language | voller Sprachname (English, German …) |
| Foil | leer · foil · etched |
| Tags | eigene Tags |
| Last Modified | Änderungsdatum |
| Alter · Proxy | True/False |
| Purchase Price | Kaufpreis (oft leer) |

- **Nur in `buchungen.csv`:** `Buchung` (ID `B-nnn` + Art), `Datum`, `Beleg` – Moxfield und `mtg_db.py` ignorieren unbekannte Spalten.
- Keine Scryfall-ID → Abgleich über **Edition + Collector Number** (beim Nutzer 100 % Treffer).
- Gleiche Druckversion kann in mehreren Zeilen stehen → Mengen addieren.
- Moxfield erkennt Spalten am **Namen**, die Reihenfolge ist egal.
- **Import in Moxfield nur als CSV, fügt nur hinzu** (getestet 26.10.: +35 Karten, Rest unverändert) → Zugänge per CSV, Abgänge löscht der Nutzer in Moxfield von Hand.

---

## 4. Deckliste als Text (Moxfield-Format; mit echten Dateien geprüft 25.10.2026)

Der Textexport von Moxfield sieht so aus – dasselbe Format geben wir für den Import in Moxfield aus:

```
1 Abrade
3 Mountain
2 Mountain

1 Zurgo Stormrender
```

- `Anzahl Name`, **ohne** Set und Nummer, alphabetisch.
- Gleiche Karte in verschiedenen Druckversionen erscheint mehrfach (z. B. `3 Mountain` + `2 Mountain`) → Mengen addieren.
- **Commander** steht nach einer Leerzeile am Ende. Bei 60-Karten-Decks wäre ein Block nach der Leerzeile das Sideboard (`mtg_db.py` unterscheidet das automatisch).
- Moxfield akzeptiert beim Import zusätzlich `(SET) Nummer`, `*F*` (Foil), `*E*` (Etched).
- **Deckimport in Moxfield als `.txt`.**
- Soll-Stände in `claude/decks/` haben zusätzlich Kommentarzeilen (`//`) und `// Commander`; `mtg_db.py` liest sie direkt.

---

## 5. Gemeinsames Datenmodell (intern)

| Feld | ManaBox | Moxfield-Format |
|---|---|---|
| name | Name | Name |
| set | Set code | Edition |
| cn | Collector number | Collector Number |
| finish (nonfoil/foil/etched) | Foil | Foil |
| qty | Quantity | Count |
| trade_qty | – | Tradelist Count |
| condition (NM/EX/GD/LP/PL/HP/DMG) | Condition | Condition |
| lang (Code) | Language | Language |
| price_paid | Purchase price | Purchase Price |
| binder / binder_type | Binder Name / Binder Type | – |
| tags | – | Tags |
| scryfall_id | Scryfall ID | über Set + Nummer ermittelt |
| oracle_id | über Scryfall | über Scryfall |
| source | „manabox“ | „moxfield“ |

**Zusammenführen**
- Schlüssel: Druckversion (scryfall_id); Besitz je Karte über oracle_id.
- **Bestand = Basis + `buchungen.csv`** (Abgänge als negative Zeilen). ManaBox-CSVs werden nie direkt geladen → keine Doppelzählung.
- Decks = Soll-Stände in `claude/decks/`; Abgleich Deck ↔ Bestand über oracle_id (Druckversion egal).
- „frei“ = Besitz minus Bedarf aller Decks (inkl. Standardländer und Sideboards), zusätzlich ohne in `10` vorgemerkte Karten → nur freie Karten sind echte Stufe-0-Upgrades.

---

## 6. Was ich mit den Dateien mache

- **Bestandsübersicht:** Anzahl Karten/Unikate, Verteilung nach Farbe und Typ, Wert (Scryfall-EUR).
- **Zwei Listen (abgeleitet, nach jeder Buchung neu):** `06_Sammlung-Bestand.csv` (Bestand inkl. Deckkarten) und `07_Sammlung-Frei.csv` (Sammlung = freie Karten).
- **Deck ↔ Bestand:** Was besitze ich, was fehlt (mit Preisen und Summe), welche Karten werden in mehreren Decks gleichzeitig gebraucht, Standardländer mit Nachkauf.
- **Buchen:** Käufe, Verkäufe, Scans und Tausch als Zeilen in `buchungen.csv` mit Beleg.
- **Ausgabe für Moxfield:** Einfügeblock bzw. Deck-TXT, Zugänge als Bestands-CSV, Abgänge als Löschliste.
- **Tausch/Verkauf:** Kandidaten (doppelte, ungenutzte, wertvolle freie Karten), auf Wunsch mit Händler-Ankaufspreis.

---

## 7. Ausgabe für Moxfield (verbindlich)

- **Einfügeblöcke** im Format von Abschnitt 4: eine Karte pro Zeile, `Anzahl Name` (optional ` (SET) Nummer`), alphabetisch, Commander nach einer Leerzeile am Ende, **keine** Überschriften, Kommentare oder Rollen-Gruppen im Block. Kaufliste und Standardländer-Nachkauf als eigene Blöcke. Rollen und Begründungen stehen in der Tabelle daneben. Details: `05_Datenbank-und-Tools`, Abschnitt 7.
- **Dateien:** Decks als `.txt`; Bestand **nur als `.csv`** mit Kopfzeile
  `Count,Tradelist Count,Name,Edition,Condition,Language,Foil,Tags,Last Modified,Collector Number,Alter,Proxy,Purchase Price`
