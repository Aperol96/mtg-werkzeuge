# mtg-werkzeuge
Auslagerung von Code für mein Deckbau-Assistenten / Sammlungsverwalter

Werkzeuge für das Claude-Projekt „MTG Deck Builder & Bestandsverwalter“ (Magic: The Gathering, Schwerpunkt Commander).

| Datei | Zweck |
|---|---|
| `werkzeuge/mtg_db.py` | Datenbank aus Scryfall-Daten, Bestand, Decks, Scans, Moxfield-Export |
| `werkzeuge/deckbau.py` | geführter Commander-Deckbau, Upgrades, Passungs-Check, Fazit-Entwurf |
| `werkzeuge/archetypen.py` | Archetypen-Pakete und Sammlungsprofil |
| `werkzeuge/kartenbilder.py` | Fazit-PDF, Tauschübersicht und Deck-PDF mit Kartenbildern |
| `werkzeuge/paket.py` | Arbeitspakete packen und auspacken |
| `werkzeuge/archetypen_daten.json` | Richtwerte je Archetyp (EDHREC, Bracket 3) |
| `werkzeugkiste.txt` | alle sechs als ein Paket (tar.xz in Base64, mit Prüfsummen) |

**So nutzt Claude das Repo:** Das Projekt hält einen festen Commit und die Prüfsumme der `werkzeugkiste.txt` fest. Der Startbefehl lädt genau diesen Stand, prüft die Prüfsumme und packt aus; klappt das nicht, nimmt Claude die Werkzeugkiste aus dem Projekt. Neue Commits wirken erst, wenn das Projekt auf sie zeigt.

**Keine persönlichen Daten:** Bestand, Decks, Ideen und Protokoll bleiben im Projekt.

Daten zur Laufzeit von Scryfall, EDHREC und Commander Spellbook; Schriften der PDFs (Cinzel, EB Garamond, SIL Open Font License) von Google Fonts. Magic: The Gathering ist eine Marke von Wizards of the Coast; dieses Projekt ist inoffiziell.
