# Quellen-Framework: Commander-Deckbau, Meta & Synergien

**Stand:** 29.10.2026 (Rolle von Moxfield/ManaBox 26.10.2026; V1.6: Format-Stand in `01a`, Rechenregel der Klassen) · **Pflege:** nach jeder Banned-&-Restricted-Ankündigung (nächste: 30.11.2026) und jedem Brackets-Update `01a_Format-Stand` aktualisieren.

Zweck: Damit ich (Claude) sofort weiß, wo ich welche Information finde, welche Kennzahl was bedeutet und wie ich Empfehlungen bewerte.

---

## 1. Schnellnavigator – welche Frage, welche Quelle

| Frage | Erste Anlaufstelle | Zweitquelle |
|---|---|---|
| Was spielen andere mit Commander X? | EDHREC-Commander-Seite (Filter Bracket/Budget) | Öffentliche Decks auf Moxfield/Archidekt |
| Welche Karte ist *speziell* für X stark (nicht nur generisch gut)? | EDHREC Synergy-Score | Scryfall `otag:synergy-…` |
| Welche Combos stecken im Deck / welche fehlen nur 1 Karte? | Commander Spellbook „Find My Combos" | EDHREC Combos-Tab |
| Was gewinnt wirklich (Casual)? | playgroup.gg (Siegquoten, Staples nach Winrate-Lift) | TopDeck.gg Bracket-3-Events |
| cEDH-Meta | EDHTop16 (Meta-Anteil, Conversion) | cEDH Decklist Database, TopDeck.gg |
| Karte mit Funktion X in Farben Y finden | Scryfall (`otag:`, `id<=`, `f:commander`) | Scryfall Tagger (tagger.scryfall.com) |
| Legal? Game Changer? | Scryfall `banned:commander` / `is:gamechanger` | WotC-Seite Banned & Restricted |
| Regelfrage | Comprehensive Rules (Projektdatei / magic.wizards.com/rules) | Rulings der Karte auf Scryfall/Gatherer |
| Kaufpreis (DE) | Cardmarket Trendpreis (für Claude: Scryfall EUR, siehe Abschnitt 8) | Scryfall EUR (kommt von Cardmarket) |
| Was zahlt ein Händler für meine Karte? | karten-ankauf.de (Connector, falls im Konto verbunden) | Verkauf über Cardmarket |
| Ist ein Produkt (z. B. Precon) im Shop vorrätig? | games-island.eu (Connector, ohne Preise) | – |
| Manabasis | Karsten-Mathematik (Abschnitt 4) | Statistik in Moxfield/Archidekt |
| Bracket einschätzen | Offizielle Kriterien (`01a_Format-Stand`) + `deckbau.py abnahme` + Moxfield-Anzeige | Bracket-Rechner (playgroup.gg, nerdleagues.com) |

---

## 2. Quellen im Detail

### EDHREC – edhrec.com (Daten: Was wird gespielt?)
- **Was:** Aggregiert Decklisten von Archidekt, Moxfield und Scryfall. Seiten für Commander, Themen, Karten, Combos, „Average Deck", Salt.
- **Kennzahlen:**
  - *Inclusion* – Anteil der Decks mit dieser Karte.
  - *Synergy* – Anteil bei diesem Commander minus Anteil in allen Decks derselben Farbidentität. Hoch = commander-spezifisch, niedrig/negativ = generischer Staple.
  - *Salt* – Durchschnitt einer jährlichen Community-Umfrage (wie unangenehm ist die Karte zu spielen gegen). Misst Spielgefühl, nicht Stärke.
- **Filter:** Bracket (1–5), Budget (günstig/teuer), Themen/Tags; Gruppieren und Sortieren nach Synergy, Preis, Salt, Manawert; Decks mit/ohne bestimmte Karten.
- **URL-Muster:** `edhrec.com/commanders/<commander-slug>[/<bracket>][/budget|/expensive]` – Bracket-Segmente `/exhibition`, `/core`, `/upgraded`, `/optimized`, `/cedh`; Budget als `/budget` oder kombiniert `/upgraded/budget`; Precon-Seiten `edhrec.com/precon/<deck-slug>/<commander-slug>` (alle getestet 25.10.2026).
- **Fallen:** Popularität ≠ Stärke; Precon-Listen verzerren; neue Commander = kleine Stichprobe.
- **Zugriff für Claude:** Seiten per WebFetch, Rohdaten per Skript über json.edhrec.com (siehe Abschnitt 8).

### Commander Spellbook – commanderspellbook.com (Combos)
- Datenbank für unendliche Combos, Locks und Siegbedingungen mit Voraussetzungen, Schritten, Ergebnis und Preis. Speist die Combo-Seiten von EDHREC.
- **Find My Combos:** Deckliste einfügen → Combos im Deck + Combos, denen nur eine Karte fehlt.
- **Combo-Einstufung** (pro Combo, nicht pro Deck): Ruthless, Spicy, Powerful, Core, Oddball, Exhibition. Wichtig für Bracket 3 (keine frühen 2-Karten-Combos).
- **Zugriff für Claude:** API per Skript, inkl. Find My Combos (siehe Abschnitt 8).

### Scryfall – scryfall.com (Kartendatenbank & Funktionssuche)
- Oracle-Text, Rulings, Legalität, alle Drucke, Preise (USD über TCGplayer, EUR über Cardmarket – Partnerschaft seit 2025).
- **Tagger-Tags** (`otag:` / `function:`) = Community-Funktionstags → beste Suche nach Rollen und Synergien. Spickzettel in Abschnitt 3.
- **Zugriff für Claude:** API und Bulk-Daten per Skript; WebFetch weiterhin blockiert (siehe Abschnitt 8).

### Moxfield – moxfield.com (externe Datenbank des Nutzers)
- Decks, Bestand, Tags, Playtester, Bracket-Hinweis, Preise – für die Nutzung außerhalb des Projekts.
- **Rolle seit 26.10.2026:** Hauptdatenbank ist das Projekt; Daten fließen nur **Projekt → Moxfield**. Moxfield-Exporte werden nur zur Fehlerkorrektur oder auf ausdrücklichen Wunsch zum Überschreiben genutzt (`05_Datenbank-und-Tools`, Abschnitt 0).
- Import: Deck als Text (`1 Sol Ring (C21) 263`), Bestand als CSV (fügt nur hinzu) → Details in `03_Import-Formate`. Deckbeschreibung max. 140 Zeichen, Themen aus fester Liste (`Moxfield-Beschreibungen`).

### Archidekt – archidekt.com
- Alternativer Deckbauer mit Sammlung und Bracket-Markierung; erlaubt Scryfall-Syntax als Filter innerhalb des Decks. Datenquelle für EDHREC.

### ManaBox (App)
- Nur Scanner des Nutzers – Zulieferer der gescannten Daten, keine Bestandsquelle. CSV-Export enthält die Scryfall-ID → eindeutige Druckversion; Scans werden im Projekt gebucht.

### playgroup.gg (Siegquoten aus echten Casual-Partien)
- Partien aus der Playgroup-App und Online-Spielen. Siegquoten je Commander, auf 4-Spieler-Basis normalisiert (25 % = Erwartungswert).
- Tier-Listen für 30/90/180/365 Tage (Mindestanzahl Spiele und verschiedener Spieler), Staples nach Winrate-Lift, Einfluss der Game Changer auf die Siegquote, Precon-Ranking, Land-/Mulligan-Daten, Bracket-Rechner, Deck-Template-Vergleich.
- Commander-Seite (`playgroup.gg/commanders/<id>-<slug>`): Siegquote, Partien, Decks, bis zu 15 Staples mit Winrate-Lift (gegen Decks desselben Commanders ohne die Karte, gerankt nach unterer 95-%-Grenze). Keine Bracket-Aufschlüsselung je Commander.
- Einordnung: einzige große Quelle für echte Siegquoten im Casual-Bereich – aber selbst gemeldet, Stichprobe beachten.
- **Zugriff für Claude:** Commander-Seiten per WebFetch (Startseite enthält keine Daten); Seiten-ID per Websuche finden.

### EDHTop16 – edhtop16.com + TopDeck.gg (Turnierdaten)
- cEDH-Turnierdaten (u. a. von TopDeck.gg): Meta-Anteil, Conversion-Rate (Top-Cut-Quote), Decklisten der Top-Spieler, öffentliche GraphQL-API.
- Sinnvolle Filter: letzte 3 Monate, Turniere ab ca. 60 Spielern.
- TopDeck.gg ist die Turnierplattform dahinter; Auswertungen nennen dort inzwischen auch Bracket-3-Events.

### cEDH Decklist Database – cedh-decklist-database.com
- Kuratierte cEDH-Listen nach Archetyp.

### Cardmarket – cardmarket.com (Preise & Einkauf in Europa)
- De-facto-Preisreferenz in Europa: Trendpreis, Ab-Preis, 7-/30-Tage-Durchschnitt.
- Wants-Liste + Shopping Wizard bündeln Verkäufer → Porto sparen.
- Käufe und Verkäufe des Nutzers werden als Belege im Projekt gebucht (`buchungen.csv`).
- **Zugriff für Claude:** gesperrt (WebFetch und Skript) → Preise über Scryfall EUR, mit Datum; Feinabgleich macht der Nutzer im Shopping Wizard.

### karten-ankauf.de (Connector, falls im Konto verbunden)
- Ankaufspreise eines deutschen Händlers – für Verkauf/Tausch-Entscheidungen. Händlerpreis ≠ Marktwert.
- Ablauf: `search_cards` (Druckversion) → `get_buy_price` (Zustand nach Cardmarket-Skala MT/NM/EX/GD/LP/PL/PO, Sprache en/de/jp, Foil). Preise täglich gegen 02:00 neu.

### games-island.eu (Connector, falls im Konto verbunden)
- Sortiment und Lagerstatus eines deutschen Shops (z. B. Precons, Displays). Keine Preise über den Connector.

### Strategie-Content (Wissen, keine Daten)
- The Command Zone (Deckbau-Template), EDHRECast, Play to Win, Lemora's Cards, ComedianMTG (cEDH).

### Offiziell – Wizards of the Coast
- Comprehensive Rules: magic.wizards.com/en/rules
- Commander-Format: magic.wizards.com/en/formats/commander
- Banned & Restricted: magic.wizards.com/en/game-info/gameplay/rules-and-formats/banned-restricted
- Ankündigungen (Brackets-Updates, Bans): magic.wizards.com/en/news/announcements

---

## 3. Scryfall-Spickzettel für Commander

| Syntax | Bedeutung |
|---|---|
| `f:commander` | Commander-legal |
| `id<=wbr` bzw. `id<=mardu` | passt in Farbidentität (hier Mardu) |
| `is:commander` | kann Commander sein |
| `is:gamechanger` | steht auf der Game-Changer-Liste |
| `banned:commander` | gebannt |
| `otag:ramp` · `otag:removal` · `otag:card-advantage` | Funktionstags (Rollen) |
| `otag:synergy-<thema>` | Synergie-Tags, z. B. `otag:synergy-mill` |
| `o:"…"` / `fo:"…"` | Oracle-Text / voller Oracle-Text |
| `kw:` · `t:` · `mv<=3` | Schlüsselwort · Typ · Manawert |
| `eur<2` / `usd<5` | Preisgrenze |
| `order:edhrec` · `order:eur` | nach EDHREC-Beliebtheit / Preis sortieren |

Beispiel: `id<=wbr f:commander otag:removal mv<=2 eur<3 order:edhrec` → billige, effiziente Removal für Mardu, beliebteste zuerst.
Genaue Tag-Namen auf tagger.scryfall.com nachschlagen.

---

## 4. Deckbau-Framework

### 4.1 Gerüst (The Command Zone, Template „New Era") – gilt nur ohne Archetyp-Richtwert (seit V1.6: Archetyp vor Template, `08`, Grundsatz 15)

| Kategorie | Richtwert | Hinweis |
|---|---|---|
| Länder | 38 | 35–38 je nach Kurve und Ramp |
| Kartenvorteil | 12 | echter Mehrwert (+Karten), keine reine Selektion |
| Ramp | 10 | Minimum; viele gehen auf 12–14 |
| Gezielte Interaktion | 12 | 1 Karte gegen 1 Bedrohung |
| Massen-Interaktion | 6 | Wipes, Massen-Effekte (im Go-wide-Deck keine symmetrischen Kreaturen-Wipes) |
| Plan/Synergie | Rest | Karten mit Doppelrolle zählen doppelt → mehr Platz |

Ramp-Wahrscheinlichkeit: Mit 10 Ramp-Karten ca. 54 % mindestens eine in der Starthand, ca. 63 % bis Zug 2; mit 12 ca. 61 % / 70 %.

**Anpassen:** niedrige Kurve/Aggro → 35–36 Länder; Landfall → mehr Länder; Commander zieht selbst Karten → weniger Draw; Bracket 4 → mehr effiziente Interaktion (≤ 2 MV), Tutoren, schnelles Mana.

### 4.2 Rollen-Zählung (bei jeder Analyse)
Jede Karte bekommt eine Primärrolle (+ optional Nebenrolle): Land · Ramp · Kartenvorteil · Gezielte Interaktion · Wipe · Schutz · Engine · Enabler · Payoff · Wincon · Utility. Dazu: Kurve (Durchschnitts-MV ohne Länder), Farbpips vs. Farbquellen, Anteil getappter Länder.

### 4.3 Manabasis (Frank Karsten)
- Startwert 37–38 Länder für ein typisches Deck.
- Commander: Karstens Quellenzahlen für 60-Karten-Decks × ca. 1,65. Beispiel: Ein-Pip-Zauber, den man in Zug 3 zuverlässig wirken will → ca. 20 Quellen dieser Farbe.
- 60-Karten-Decks: Länderzahl ≈ 19,59 + 1,90 × Ø MV (ohne Länder), abzüglich ca. 0,28 je günstiger Ramp-/Draw-Karte.
- Splash-Farbe (unter ca. 12 % der farbigen Pips) braucht nur ca. 70 % des Zielwerts.
- Für pünktliches Ausspielen zählen nur ungetappte Quellen.
- Kosten-Nutzen bei Ländern: günstige ungetappte Duals zuerst ersetzen getappte Länder; teure Fetch-/Original-Duals bringen den kleinsten Grenznutzen.

### 4.4 Synergie-Framework
- **Bausteine:** Engine (erzeugt fortlaufend Wert) · Enabler (macht Engine möglich) · Payoff (belohnt den Plan) · Schutz.
- **Pakete denken:** z. B. Aristokraten = Opfer-Outlet + Token-Quelle + Tod-Trigger-Payoff.
- **Redundanz (Faustregel):** Schlüsselfunktion 3–4× im Deck → Konsistenz ohne Tutoren.
- **Synergien finden:** (1) EDHREC High-Synergy, (2) Scryfall `otag:synergy-…`, (3) Spellbook inkl. „1 Karte fehlt", (4) Oracle-Muster, z. B. `o:"whenever" o:"dies"`.
- **Prüffragen:** Funktioniert die Karte auch ohne Commander? Hat sie mehrere Rollen? Antisynergien (eigene Wipes vs. Go-wide, Friedhofs-Hate vs. eigener Friedhofsplan)?

---

## 5. Meta-Analyse-Framework

| Bereich | Meta ist … | Datenquellen |
|---|---|---|
| Bracket 1–3 (Casual) | vor allem die eigene Spielgruppe | Erst Gruppe erfassen (Decks, Tempo, Interaktion), dann EDHREC (üblich?) + playgroup.gg (gewinnt?) + TopDeck.gg B3-Events |
| Bracket 4 | Gruppe + effiziente Standardpakete | EDHREC Bracket-4-Filter, „Optimized"-Listen auf Moxfield |
| Bracket 5 (cEDH) | Turnier-Meta | EDHTop16 (3 Monate, große Turniere), cEDH DDB |

- **Kennzahlen:** Inclusion · Synergy · Siegquote (normalisiert 25 %) · Winrate-Lift einer Karte · Conversion-Rate · Meta-Anteil · Salt.
- **Conversion schlägt Meta-Anteil** als Stärke-Indikator (Beliebtheit ≠ Erfolg).
- **Fallstricke:** kleine Stichprobe (unter ca. 100 Spielen = Rauschen), Selektionseffekt (starke Spieler wählen starke Decks), Datenalter (neue Sets, Bans).
- **Ergebnis:** Bedrohungsprofil der Gruppe → konkreter Interaktionsmix (z. B. mehr Artefakt- oder Friedhofs-Hate, Instant-Speed-Antworten).

---

## 6. Kosten-Nutzen-Framework

**Prinzip:** Jede Karte muss ihren Preis durch Wirkung rechtfertigen. Freie Karten aus der Sammlung kosten 0 €.

**Bewertung je Karte**
- *Wirkung* (1–5): Einfluss auf Siegchance/Konsistenz im Ziel-Bracket.
- *Ersetzbarkeit:* Gibt es eine Karte mit ca. 80 % der Wirkung für einen Bruchteil des Preises?
- *Preis:* günstigste passende Druckversion (Sprache/Edition egal, falls nicht anders gewünscht), Cardmarket-Trend, mit Datum.
- *Mehrfachnutzung:* In wie vielen Decks des Nutzers einsetzbar → Kosten pro Deck sinken.
- *Preisrisiko:* frischer Hype oder Nachdruck wahrscheinlich (Commander-Staples werden oft neu aufgelegt) → eher warten. Reserved List → kein Nachdruck.

**Klassen**

| Klasse | Bedeutung | Empfehlung |
|---|---|---|
| A – Kern | hohe Wirkung, kein gleichwertiger Ersatz | kaufen |
| B – Effizient | gutes Wirkung-pro-Euro-Verhältnis | kaufen |
| C – Luxus | kleine Verbesserung, hoher Preis | nur bei Restbudget oder Mehrfachnutzung |
| D – Falle | teuer, im Ziel-Bracket kaum besser oder bracket-schädlich (z. B. 4. Game Changer in B3) | nicht kaufen |

**Rechenregel der Werkzeuge (V1.6, `bewertung.py`, Einschätzung aus Daten):** Wirkung 1–5 aus dem Wert der Karte für den Commander (max. aus EDHREC-Wert und Oracle-Bezug; < 0,10 → 1, < 0,25 → 2, < 0,45 → 3, < 0,70 → 4, sonst 5; +1, wenn sie eine Rolle unter dem Minimum füllt) · D = bracket-schädlich oder Wirkung ≤ 2 bei ≥ 5 € · A = Wirkung ≥ 4 ohne 80-%-Ersatz · B = ≤ 2 € je Wirkungspunkt über 1 · sonst C. `upgrade` und `kandidaten` zeigen Wirkung, Klasse und € je Wertpunkt; Claude prüft am Oracle-Text und kann begründet abweichen.

**Freie Karten als Kompromiss** (Rückfall vor Kauf, `08`, Grundsatz 14): gleichwertig · funktional, aber langsamer · nur Platzhalter – jeweils mit der besten Kauf-Alternative und dem Satz, was der Aufpreis bringt.

**Upgrade-Stufen:** Stufe 0 = nur freie Karten aus der Sammlung (0 €) → Stufe 1/2/3 mit steigendem Budget (Beträge am Budget des Nutzers ausrichten). Je Stufe: Summe + erwarteter Effekt in einem Satz.

**Faustregeln**
- Grenznutzen sinkt: die ersten ca. 10 Upgrades bringen am meisten.
- Übliche Reihenfolge: Manabasis-Fehler beheben → Interaktion und Kartenvorteil auf Zielwert → Synergie-Payoffs → Luxus.
- Bracket 3: Die max. 3 Game-Changer-Slots mit der höchsten Wirkung belegen, nicht mit den teuersten Karten.
- Einkauf über Cardmarket-Wants + Shopping Wizard, Porto bündeln – Sammelbestellung aus `10_Geplante-Kaeufe-und-Ideen`.

---

## 7. Format-Stand

Steht seit V1.6 in **`01a_Format-Stand`** (Brackets, Game Changer, Banlist, nächste Ankündigung) – kurz, damit Claude nur diese Datei liest, wenn es um den aktuellen Stand geht.

---

## 8. Zugriffshinweise für Claude (im Admin-Projekt getestet 25.10.2026)

In der Nutzer-Kopie hängt der Zugriff von den Netzwerk-Einstellungen des Kontos ab (erlaubte Domains, siehe README des Repos). Schlägt ein Abruf fehl, sagt Claude das und nennt die Domain.

| Quelle | per Skript (Bash) | per WebFetch | Hinweise |
|---|---|---|---|
| api.scryfall.com | ✅ | ❌ Bot-Schutz | Header `User-Agent` und `Accept: application/json` setzen; 50–100 ms Pause zwischen Anfragen. Suche: `/cards/search?q=…` (Seiten über `next_page`) |
| data.scryfall.io (Bulk) | ✅ | – | Liste über `api.scryfall.com/bulk-data`. **Formatänderung:** Download-Link steht jetzt in `jsonl_download_uri` (gzip-komprimiertes JSONL, eine Karte pro Zeile); `download_uri` und `size` gibt es nicht mehr. `oracle_cards` ≈ 25 MB (≈ 39.000 Karten, inkl. `game_changer`, `color_identity`, `legalities`, `prices.eur`) · `default_cards` ≈ 80 MB (alle Drucke → Abgleich über Scryfall-ID bzw. Set + Nummer) · `oracle_tags` ≈ 6 MB (Funktionstags offline) · `rulings` ≈ 5 MB |
| json.edhrec.com | ✅ | edhrec.com ✅ | `/pages/commanders/<slug>[/<bracket>][/budget].json`, `/pages/precon/<deck>/<commander>.json`. Kartenlisten unter `container.json_dict.cardlists[].cardviews[]` mit `num_decks`, `potential_decks` (Inclusion = Quotient) und `synergy` |
| backend.commanderspellbook.com | ✅ | – | `/variants/?q=card="Name"`; `POST /find-my-combos` mit `{"main":[{"card":"…"}],"commanders":[{"card":"…"}]}` → `included`, `almostIncluded` u. a.; je Combo `bracketTag` |
| edhtop16.com | ✅ (HTTP 200) | – | GraphQL-API bei erster cEDH-Nutzung testen |
| playgroup.gg | ❌ | ✅ Commander-Seiten | Startseite ohne Daten; Commander-ID per Websuche |
| cardmarket.com | ❌ | ❌ | Preise über Scryfall EUR (Quelle Cardmarket), Datum nennen |
| moxfield.com | ❌ (Proxy) | ❌ | Themenliste und Daten gibt der Nutzer per Screenshot/Text (Stand 26.10.2026) |
| media.wizards.com | ❌ | – | magic.wizards.com/en/rules per WebFetch ✅ (Versionsname); CR-Volltext muss der Nutzer hochladen oder die Domain freischalten |

- **Connectoren (falls im Konto verbunden):** karten-ankauf.de (Ankaufspreise), games-island.eu (Sortiment/Lager, keine Preise) – im Admin-Projekt getestet 25.10.2026.
- **Arbeitsumgebung:** Python 3; Datenarbeit mit `mtg_db.py` und `deckbau.py` (`05_Datenbank-und-Tools`).
- **Damit möglich:** Bestand automatisch mit Oracle-Text, Farbidentität, Legalität, Game-Changer-Flag und EUR-Preisen anreichern; Funktionstags offline; Deck-Combos per Find My Combos prüfen; EDHREC-Daten je Bracket auswerten.
- **Noch freischaltbar (Einstellungen → Capabilities → erlaubte Domains):** `media.wizards.com` (Regelwerk-Volltext automatisch laden). Cardmarket ist durch Bot-Schutz gesperrt – Freischaltung bringt dort voraussichtlich nichts.

---

## 9. Pflege dieser Datei
- Nach jeder B&R-Ankündigung und jedem Brackets-Update: `01a_Format-Stand`.
- Bei neuen Sets: neue Commander/Karten auf EDHREC und neue Combos auf Commander Spellbook sichten.
- Neue Werkzeuge, die sich bewähren, in Abschnitt 2 aufnehmen; Zugriffstests in Abschnitt 8 mit Datum nachtragen.
