# Deckregister

**Zuletzt aktualisiert:** – (angelegt bei der Ersteinrichtung) · **Spielgruppe:** laut `nutzerprofil.md` · **Ziel-Bracket der Commander-Decks:** laut Nutzerprofil (Standard 3) · **Bestand:** Basis in `sammlung/` + `sammlung/buchungen.csv` · **Hauptdatenbank ist das Daten-Repo**, Moxfield wird nachgezogen

Übersicht aller Decks. Wird aktualisiert, sobald ein Deck nach der Freigabe physisch gebaut bzw. geändert (Meldung „gebaut“) oder per Scan abgeglichen wird. Namen nach dem Schema in `05_Datenbank-und-Tools`, Abschnitt 6: `Format | Deckname | Farbname (Kürzel) | Strategie | Herkunft[ | In Arbeit]`, höchstens 100 Zeichen (Moxfield). Der Deckname ist die Kennung des Decks.

## Commander

| Deckname | Name (einheitlich) | Commander | Bracket-Check | Bracket nach Kriterien / Einschätzung | Karten | Status | Quelle/Stand | Abnahme | Notizen |
|---|---|---|---|---|---|---|---|---|---|

## Konstruiert (60 Karten)

Brackets gelten nur für Commander – hier zählt die Format-Legalität.

| Deckname | Name (einheitlich) | Legalität (Scryfall) | Karten | Status | Quelle/Stand | Notizen |
|---|---|---|---|---|---|---|

## Moxfield-Themen und Deckwert

| Deckname | Moxfield-Themen | Deckwert |
|---|---|---|

## Karten in mehreren Decks

–

## Standardländer

–

---

## Pflege-Regeln
- **Deckname:** Wizards-Name bei Precons/Precon-Umbauten, Produktname bei Händler-Decks, eigener Name bei eigenen Decks; in `deck_namen.json` pflegen; voller Name höchstens 100 Zeichen (Moxfield), Länge mit `mtg_db.py namen` prüfen
- **Status:** Idee · im Bau · spielbereit · Upgrade geplant · zerlegt (gleiche Regeln für alle Decks; Vorhaben stehen als Idee in `10`)
- **Ideen zu bestehenden Decks:** zentral in `protokolle/10_Geplante-Kaeufe-und-Ideen.md` (ID, Status; Kaufliste und Vormerkungen in `sammlung/kaufliste.csv` bzw. `vormerkungen.csv`); Details in `ideen/<deckname>-<thema>.md`; Soll-Stand und Register bleiben unverändert, bis der Nutzer meldet, dass das Deck nach der Freigabe physisch gebaut ist; dann Register aktualisieren und Einfügeblock für Moxfield ausgeben (Ablauf: `08_Deckbau-Verfahren`, Abschnitt 2)
- **Begriffe:** Bestand = Deckkarten + Sammlung; Sammlung = freie Karten (`05_Datenbank-und-Tools`, Abschnitt 0)
- **Bracket-Check:** Anzahl und Namen der Game Changer (in Bracket 3 max. 3), MLD, Extra Turns, 2-Karten-Combos – mit `mtg_db.py bracket` bzw. `deckbau.py pruefen`; dazu Einstufung nach Kriterien und Einschätzung mit Datum
- **Abnahme:** Ergebnis der Bracket-3-Abnahme (`deckbau.py abnahme`) mit Datum und offenen Punkten – nach jedem gebuchten Deckumbau neu
- **Quelle/Stand:** Datum der Liste, aus der der Soll-Stand stammt (Moxfield-Erstübernahme, Scan oder gebuchte Änderung im Daten-Repo)
- **Notizen:** Spielplan in einem Satz, offene Baustellen, Budget für nächste Stufe
- **Moxfield-Themen und Beschreibung:** bei neuem oder stark geändertem Deck mitliefern – Themen nur aus der Liste in `profil/Moxfield-Beschreibungen.md` (Farbe/Gilde + Strategie, 4–6 Häkchen), Beschreibung höchstens 140 Zeichen mit Wert und Datum; Deckwert hier nachtragen
- Bei Karten, die mehrere Decks gleichzeitig brauchen, hier vermerken, welches Deck sie gerade hat.
