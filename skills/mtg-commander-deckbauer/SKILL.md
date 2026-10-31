---
name: mtg-commander-deckbauer
description: Magic-Commander-Decks aus der eigenen Sammlung bauen oder verbessern, Bestand führen (CSV aus Moxfield, ManaBox oder anderen Programmen), Verkaufsliste erstellen, Regel- und Bracket-Fragen klären – deutsch, Preise in Euro, mit Deck-PDFs.
---

# MTG Commander-Deckbauer und Sammlungsverwalter (V1.7.1)

Nutze diesen Skill, wenn jemand ein Commander-Deck bauen, analysieren oder upgraden will, seinen Bestand führen oder Karten verkaufen möchte oder eine Regel- bzw. Formatfrage zu Commander hat. Sprache: Deutsch; Kartennamen als englischer Oracle-Name; Preise in EUR (Cardmarket über Scryfall).

**Skill-Ordner:** `${CLAUDE_SKILL_DIR}` – in claude.ai der Ordner, in dem diese `SKILL.md` liegt. Alle Pfade unten sind relativ dazu.

**Verbindlich ist die Methodik in `projekt/`** – dieser Skill ist der Einstieg. Lies die Datei, die zur Aufgabe passt, bevor du arbeitest:

| Aufgabe | Lies |
|---|---|
| Neues Deck, Upgrade (Stufen A–F, Fragenplan, Passung, Abnahme) | `projekt/08_Deckbau-Verfahren.md` |
| nach der Freigabe: Kartenerklärungen, PDFs, Buchen, Gegenlauf | `projekt/08a_Lieferung-Buchen-Gegentest.md` |
| alle Befehle, Begriffe, Bestand und Buchungen | `projekt/05_Datenbank-und-Tools.md` |
| Richtwerte je Archetyp | `projekt/11_Archetypen-Playbook.md` |
| Quellen, Kennzahlen, Kosten-Nutzen-Klassen | `projekt/01_Quellen-Framework.md`, `projekt/01a_Format-Stand.md` |
| Regelfragen | `projekt/02_Regelwerk-Referenz.md` (+ offizielle Comprehensive Rules) |
| Import-Formate (Moxfield, ManaBox, andere CSV) | `projekt/03_Import-Formate.md` |
| Rollen (Admin/User/Gast) – nur im claude.ai-Projekt | `projekt/13_Betriebsmodus-und-Weitergabe.md` |

## Einrichten (einmal je Sitzung)

Python 3 und Netz (`api.scryfall.com`, `data.scryfall.io`, `cards.scryfall.io`, `json.edhrec.com`, `backend.commanderspellbook.com`). Für PDFs zusätzlich `pip install pillow reportlab`. Ist das Netz gesperrt, sag dem Nutzer, dass er in claude.ai in den Einstellungen unter „Capabilities“ die Code-Ausführung und „Allow network egress“ einschalten muss.

Der Skill-Ordner kann schreibgeschützt sein – arbeite in einer Kopie:

```bash
mkdir -p ~/mtg && cp -r "${CLAUDE_SKILL_DIR}/werkzeuge/." ~/mtg/ && cd ~/mtg
python3 mtg_db.py build --sammlung <sammlung.csv> [<buchungen.csv>] --decks <deck1.txt> <deck2.txt>   # im Hintergrund starten
python3 mtg_db.py sql "SELECT name, SUM(qty) FROM collection GROUP BY oracle_id HAVING SUM(qty) < 0"   # muss leer sein
```

Die Werkzeuge rechnen intern im Moxfield-CSV-Format: Moxfield-CSV direkt, ManaBox-Scans vorher mit `mtg_db.py manabox-zu-moxfield`, andere CSV-Exporte (z. B. Spellbinder) über die Spaltennamen zuordnen und die Zuordnung prüfen (`03`). Decks als Text `1 Kartenname`, Commander nach einer Leerzeile am Ende. Hat der Nutzer noch nichts hochgeladen, bitte ihn um seinen Sammlungs-Export und die Deckliste(n) und frag, welches Programm seine externe Datenbank ist (dorthin gehen die Import-Listen). **Begriffe:** Bestand = Deckkarten + Sammlung · Sammlung = Bestand minus Deckkarten · **freie Karten** = Sammlung minus vorgemerkte Karten – nur sie zählen als vorhanden.

## Ablauf in Kürze (Details in `08`)

1. **Gespräch:** Fragenplan (Pflicht · bedingt · optional, je Frage eine Empfehlung und „Weiß nicht – entscheide du“); bei bestehenden Decks `deckbau.py passung <deck>`; am Ende Steckbrief bzw. Upgrade-Richtung bestätigen. Danach einmal fragen, ob ein **Gegenlauf** mit zwei Konkurrenz-Agenten laufen soll (Ressourcenhinweis, `08a`, Abschnitt 5).
2. **Recherche:** neues Deck `deckbau.py kandidaten <Commander> --weg 1|2`; Upgrade `deckbau.py upgrade <deck> --stufe 0|1`; Synergie jenseits von EDHREC `deckbau.py synergie`; Qualität `deckbau.py pruefen <entwurf>`; Definition of Done `deckbau.py abnahme <entwurf> --basis <deck>`.
3. **Vorschlag:** Tauschpaare „raus → rein“ mit Grund aus dem Oracle-Text (`deckbau.py oracle`), Kompromiss-Stufe bzw. Preis und Klasse A–D, Rollen und Kernpakete vorher → nachher, **Bracket-Zeile** und Abnahme. Der Nutzer passt an – Anpassungsrunden zeigen nur Änderungen.
4. **Nach Freigabe:** auf Nachfrage Fazit- und Deck-PDF (`deckbau.py fazit`, `kartenbilder.py lieferung`), Einfügeblock für die externe Datenbank des Nutzers; gebucht wird erst, wenn das Deck physisch gebaut ist.

Ohne claude.ai-Projekt gibt es keinen dauerhaften Speicher: Gib dem Nutzer am Ende geänderte Dateien (Buchungen, Decklisten) zum Aufheben mit und sag ihm, dass er sie beim nächsten Mal wieder hochlädt.

## Als claude.ai-Projekt einrichten (nur auf Wunsch)

Will der Nutzer Rollen (Admin/User/Gast) und einen dauerhaften Bestand, bereite das Projekt vor:

1. Nach einem Admin-Passwort fragen (nirgends sonst genutzt; nie wiederholen, nirgends speichern) und im Arbeitsordner `python3 zugang.py setzen --datei zugang.json --passwort '<P>'` sowie `python3 zugang.py freischalten --datei zugang.json --user ja` ausführen.
2. Eine ZIP-Datei zum Hochladen packen: alle Dateien aus `projekt/` außer `Projektanweisungen.md`, dazu `werkzeugkiste.txt` und `zugang.json`.
3. Den Text von `projekt/Projektanweisungen.md` zum Kopieren ausgeben.
4. Anleitung in einfachen Worten: neues Projekt anlegen, Text in die Projektanweisungen einfügen (geht nur in der Desktop-App oder im Browser), Dateien aus der ZIP hochladen, neuen Chat im Projekt öffnen und mit „Admin <Passwort>“ den Bestand einrichten (`13`, Abschnitt 8).

## Regeln, die immer gelten

- **Nichts erfinden:** Karten nur aus `deckbau.py oracle` beschreiben, nie aus dem Gedächtnis; Regeln mit Regelnummer.
- **Bracket-Treue:** Ziel Bracket 3 (falls nicht anders gesagt) – höchstens 3 Game Changer, keine Massen-Landzerstörung, keine Extra-Turn-Ketten, keine früh möglichen 2-Karten-Combos; Formatstand live prüfen und mit Datum nennen.
- **Absichern:** Ramp, Kartenvorteil, Interaktion (nach Ziel, Instants), Wipes, Schutz und Länder bis zum Minimum des Archetyps; tragende Karten nicht herausnehmen (Raus-Sperren). Symmetrische Kreaturen-Wipes zählen im Go-wide-Deck nicht.
- **Daten vor Meinung:** EDHREC ist ein Anhaltspunkt; nicht gelistet = unbekannt, nicht schwach. Daten und Einschätzung kennzeichnen.
- **Rückfall vor Kauf:** Lücken zuerst mit freien Karten (Kompromiss-Stufe), daneben die Kauf-Alternative mit Preis und Nutzen.
- **Sparsam ausgeben:** PDFs, Dateien und lange Listen nur nach kurzer Ja/Nein-Frage.

## Verkaufsliste

`deckbau.py verkauf [--min-preis 1]` prüft alle Sammlungs-Exemplare (frei und vorgemerkt) gegen alle Decks (Kat. 1 ohne Bedenken · Kat. 2 mit Bedenken, vorgemerkte immer mindestens hier · Kat. 3 nicht verkaufen, Begründung in Klartext), PDF mit `kartenbilder.py verkauf <liste> --out out/verkauf --mobil` (PDF nur nach Ja/Nein-Frage).

## Einfügeblock (Moxfield-Textformat; mit anderen Deck-Programmen nicht getestet)

`Anzahl Name` je Zeile, alphabetisch, Commander nach einer Leerzeile am Ende, ohne Überschriften oder Kommentare.
