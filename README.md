# MTG Deck Builder & Bestandsverwalter

Ein Commander-Assistent für **Magic: The Gathering** auf Basis von Claude: Decks bauen und verbessern, die eigene Sammlung führen, Regelfragen klären – mit Python-Werkzeugen für die Datenarbeit und einer festen Methodik für den Deckbau. Stand **V1.7** (29.10.2026), Sprache Deutsch, Preise in Euro.

> **English summary:** A German-language Claude assistant for Magic: The Gathering Commander. It manages your collection (Moxfield/ManaBox), builds and upgrades decks from cards you own, checks them against Bracket 3 rules with a Definition of Done (roles, archetype packages, consistency simulation, combos), weighs cost vs. benefit in EUR, renders deck PDFs with card images – and can run two independent competitor agents to cross-check its proposals. Use it as a Claude project, as a Claude skill, or as plain Python tools.

## Was es kann

| Bereich | Funktionen |
|---|---|
| **Deckbau** | geführter Neubau und Upgrade in festen Stufen (Gespräch → Recherche → Vorschlag → Freigabe → Aufbau → Buchen); Fragenplan mit Empfehlungen; Passungs-Check Deck ↔ Commander ↔ Ziel |
| **Qualität** | Rollen gegen Archetyp-Richtwerte, Kernpakete, Interaktion nach Ziel, Kurve und Farbquellen, Bracket-Zeile mit Game Changern und Combos, Konsistenz-Simulation, **Bracket-3-Abnahme** mit Stärke-Index |
| **Upgrades** | Tauschpaare „raus → rein“ mit Begründung aus dem Oracle-Text, Raus-Sperren für tragende Karten, Upgrade aus freien Karten zuerst (Kompromiss-Stufen), Käufe mit Preis und Klasse A–D |
| **Sammlung** | Bestand als Datenbank (Moxfield-Export + Buchungsjournal), ManaBox-Scans prüfen und buchen, freie Karten, Vormerkungen für Ideen, Verkaufsliste, Moxfield-Exporte |
| **Gegenlauf** | zwei unabhängige Agenten (Methodik von *Commander Deck Skills* und *MTG Master*) bauen mit denselben Vorgaben; der Vergleich zeigt, welche Tausche mehrere Läufe gewählt haben |
| **Ausgabe** | Deck-PDF, Tauschübersicht und Fazit mit Kartenbildern; Einfügeblöcke für Moxfield |
| **Regeln** | Antworten mit Regelnummern der Comprehensive Rules, Formatstand (Brackets, Game Changer, Banlist) live geprüft |
| **Rollen** (Projekt) | Admin (Passwort), User, Gast mit eigener Sammlung und PIN-Archiv |

## Schnellstart

### A) Als Claude-Projekt (claude.ai, empfohlen)

1. Einstellungen → Funktionen: **Code-Ausführung** und **Netzwerkzugriff** einschalten (Pro reicht).
2. Eigenes Admin-Passwort anlegen (einmal, lokal mit Python):
   `python3 werkzeuge/zugang.py setzen --datei zugang.json --passwort "<dein Passwort>"` und
   `python3 werkzeuge/zugang.py freischalten --datei zugang.json --user ja`
3. Neues Projekt anlegen: Inhalt von `projekt/Projektanweisungen.md` in die Projektanweisungen kopieren; hochladen: alle Dateien aus `projekt/` und `werkzeuge/`, dazu `werkzeugkiste.txt` und deine `zugang.json`.
4. Neuen Chat öffnen – Claude begrüßt dich. Mit „Admin <Passwort>“ richtest du deinen Bestand ein (`projekt/13_…`, Abschnitt 8), danach arbeitest du als User oder lädst Gäste ein.

### B) Als Claude-Skill

Das Repo als ZIP herunterladen und unter Einstellungen → Skills hochladen (Claude Code: in `~/.claude/skills/` klonen). Einstieg ist `SKILL.md`; die Methodik liegt in `projekt/`, die Werkzeuge in `werkzeuge/`. Ohne Rollen – du arbeitest direkt mit deiner Sammlung.

### C) Nur die Python-Werkzeuge

```bash
git clone https://github.com/Aperol96/mtg-werkzeuge && cd mtg-werkzeuge/werkzeuge
python3 mtg_db.py build --sammlung meine_sammlung.csv --decks mein_deck.txt   # Datenbank (≈ 110 MB Scryfall-Daten)
python3 deckbau.py pruefen mein_deck.txt --bracket 3                          # Rollen, Kurve, Farben, Bracket
python3 deckbau.py upgrade mein_deck.txt --stufe 0                            # Upgrade nur aus freien Karten
python3 deckbau.py abnahme mein_deck.txt                                      # Bracket-3-Abnahme mit Simulation
python3 kartenbilder.py deck mein_deck.txt --out out/mein_deck --mobil        # Deck-PDF mit Kartenbildern
```

Jeder Befehl erklärt sich mit `--help`. Für PDFs: `pip install pillow reportlab`.

## Aufbau des Repos

| Ordner/Datei | Inhalt |
|---|---|
| `SKILL.md` | Einstieg als Skill: wann, wie einrichten, Ablauf, Grundregeln |
| `projekt/` | Methodik und Projektanweisungen ohne persönliche Daten: Deckbau-Verfahren (`08`, `08a`), Werkzeuge (`05`, `05a`), Quellen (`01`, `01a`), Regeln (`02`), Formate (`03`), Archetypen (`11`), Rollen (`13`) |
| `werkzeuge/` | `mtg_db.py` (Datenbank, Bestand, Exporte) · `deckbau.py` (Deckbau, Upgrade, Abnahme, Gegenlauf, Vergleich, Verkauf) · `bewertung.py` (Regeln) · `simulation.py` · `archetypen.py` + `archetypen_daten.json` · `kartenbilder.py` (PDFs) · `protokoll.py` (Protokoll, Ideen, Aufwand) · `paket.py` · `zugang.py` · `projektanweisungen.md` |
| `werkzeugkiste.txt` | alle Werkzeuge als ein prüfsummengesichertes Paket – so lädt Claude sie in den Arbeitsbereich |
| `tests/` | automatische Tests ohne Netz und ein monatlicher Rauchtest mit Live-Daten (GitHub Actions) |

Deine Daten (Sammlung, Decks, Ideen, Protokolle, Passwort) liegen nie im Repo, sondern in deinem Projekt bzw. lokal.

## Wie Claude damit arbeitet

Claude bekommt je Gespräch einen frischen Linux-Arbeitsbereich. Ein Startbefehl (`projekt/05a_Sitzungsstart.md`) packt Werkzeuge und Daten aus und baut die Datenbank im Hintergrund; Ergebnisse und Buchungen schreibt Claude ins Projekt zurück. Das Admin-Projekt des Autors lädt die Werkzeuge von einem festen Commit dieses Repos (Prüfsumme in `werkzeuge-quelle.txt`), Kopien nutzen `werkzeugkiste.txt`.

## Tests

```bash
pip install pytest && python -m pytest tests -q   # ohne Netz
python tests/rauchtest.py                          # mit Netz: Quellen erreichbar, Formate unverändert
```

## Datenquellen und Hinweise

- Kartendaten, Preise und Bilder: Scryfall · Deckstatistiken: EDHREC · Combos und Bracket-Einstufung: Commander Spellbook. Die Werkzeuge rufen sie zur Laufzeit ab – bitte deren Nutzungsbedingungen beachten.
- Gegenlauf-Methodik: [Commander Deck Skills](https://github.com/philiptyler/mtg-commander-deck-claude-skills) und [MTG Master](https://github.com/M-Sahin/mtg-master) (beide MIT); deren Code wird nicht mitgeliefert oder ausgeführt.
- Schriften der PDFs: Cinzel, EB Garamond (SIL Open Font License).
- Lizenz: MIT. Magic: The Gathering ist eine Marke von Wizards of the Coast; dies ist ein inoffizielles Fanprojekt ohne Verbindung zu Wizards of the Coast.
