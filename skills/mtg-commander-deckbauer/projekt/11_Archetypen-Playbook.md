# Archetypen-Playbook – Commander (Schwerpunkt Bracket 3)

**Stand:** 30.10.2026 (Richtwerte neu erhoben mit den Paket- und Rollenregeln seit V1.7 – Entscheidung des Admins: am aktuellen EDHREC orientieren · V1.6: Rollen mit Qualitätsregeln neu gezählt) · **Daten:** EDHREC (Themenseiten und Durchschnittsdecks mit Bracket-3-Filter „Upgraded“, abgerufen 30.10.2026), Scryfall-Tagger (Funktionstags, Bulk vom 26.10.2026), playgroup.gg (Spieldaten, geprüft 27.10.2026), Commander Spellbook (Combos, geprüft 27.10.2026) · **Werkzeug:** `archetypen.py`, Rohdaten `archetypen_daten.json` · **Auf die Sammlung angewendet:** `12_Sammlungsprofil` · **Pflege:** Abschnitt 7

Zweck: die Ebene zwischen dem allgemeinen Template (`01_Quellen-Framework`, Abschnitt 4) und den commander-spezifischen Live-Daten beim Deckbau (`08_Deckbau-Verfahren`). Hier steht, was ein Archetyp konkret braucht, was die Community spielt und wo die Fallen liegen.

---

## 1. Begriffe

- **Archetyp** = wiederkehrender Bauplan aus Paketen, unabhängig vom Commander. Beispiel Aristokraten: Opfer-Outlets + Futter + Tod-Payoffs.
- **Spielstil** (Aggro, Midrange, Control, Combo) = Tempo und Interaktionsgrad; bestimmt Kurve, Länderzahl und Interaktionsmix.
- **Thema / Kindred** = Kreaturtyp oder Flair (Engel, Elementals); meist mit einem Archetyp kombiniert.
- EDHREC nennt Archetypen „Themes“ (410 Themen). Die Strategie-Frage in `08`, Phase 2, nutzt sie; Combo, Aggro, Control, Ramp und Midrange sind dort Spielstile, keine Archetypen.
- Paket-Rollen wie in `01`, Abschnitt 4.4: Engine · Enabler · Payoff · Schutz.

## 2. So sind die Zahlen entstanden

- **Daten:** Je Archetyp die 6 Commander mit den meisten Decks im EDHREC-Thema (Kindred: je 1 Commander aus 8 Kreaturtyp-Themen; Landfall: je 3 aus „Lands Matter“ und „Landfall“) → deren Durchschnittsdeck mit Bracket- und Themenfilter (`average-decks/<commander>/upgraded/<thema>`) → Rollen und Pakete mit Scryfall-Funktionstags und Oracle-Text-Mustern gezählt (`archetypen.py daten`) – seit V1.6 mit denselben Qualitätsregeln wie `deckbau.py` (`bewertung.py`: kein symmetrischer Ramp, keine Rituale, Landsuche ist Ramp und kein Tutor, Removal nur gegen Spieler zählt nicht).
- **Basis:** 80 Durchschnittsdecks aus 39.674 Decklisten. Angegeben ist **Median (kleinster–größter Wert)** über die Commander.
- **Grenzen:** Durchschnittsdecks zeigen, was gespielt wird, nicht was gewinnt. Die Tag-Zählung ist eine Näherung (Karten mit Doppelrolle zählen mehrfach; Land-Tutoren wie Cultivate zählen seit V1.6 als Ramp, nicht als Tutor). Große Spannen heißen: stark commander-abhängig → beim Deckbau immer die Commander-Seite live prüfen (`deckbau.py commander`).
- **Kennzeichnung:** *Daten* = gemessen · *Einschätzung* = Claude.

## 3. Was für alle Archetypen gilt

### 3.1 Grundrollen: Community gegen unser Template

| Rolle | Median aller 80 Decks | Spanne der Archetyp-Mediane | Template (`01`, nur ohne Archetyp-Richtwert) |
|---|---|---|---|
| Länder | 35 | 34–39 | 38 (35–38) |
| Ramp | 12 | 6,5–23 | 10–12 |
| Kartenvorteil | 12 | 8–22 | 10–12 |
| Gezielte Interaktion | 9 | 6–14 | 10–12 |
| davon Instant-Tempo | 5 | 3–9,5 | ≥ 4 |
| Massen-Interaktion | 2 | 1,5–4 | 3–6 |
| Counterspells | 1 | 0–5 | – |
| Schutz | 4 | 1,5–12 | 2–4 |
| Tutoren (ohne Land-Tutoren) | 1 | 0–5,5 | – |
| Ø Manawert ohne Länder | 2,9 | 2,6–3,5 | ≤ 3,5 |

*Daten, ergänzend (playgroup.gg, 27.10.2026):*
- „Deck Template“ misst 180.283 vollständige Decks getrennt nach 32 Farbidentitäten. Beispiel Fünffarben (13.195 Decks), typisch (25.–75. Perzentil): 37 Länder (35–38), 16 Ramp (12–20), 11 Kartenvorteil (8–14), 9 gezielte Interaktion (6–12), 3 Wipes (1–4), 4 Schutz (2–6). Beim Deckbau die Vorlage der eigenen Farbidentität ansehen.
- „How Many Lands“ empfiehlt 38–42 Länder für typische Casual-Decks. Gewinnrate in 4–6-Spieler-Partien nach Ländern in der Starthand (163.404 Hände, laut Seite „richtungsweisend“, nicht bereinigt): 0 Länder 17 %, 1 Land 25 %, 2–5 Länder 28–29 %, 6 Länder 25 %.

*Einschätzung:*
- Die EDHREC-Durchschnittsdecks sparen Länder (35) und spielen dafür etwas mehr günstigen Ramp (12, mit den Qualitätsregeln seit V1.6); das Mana-Budget liegt knapp unter dem Template (≈ 47 Quellen). Gemessene Decks auf playgroup.gg liegen höher (Fünffarben 37), die Seite empfiehlt 38–42. Für uns bleiben 36–38 Länder richtig; mit 12+ günstigem Ramp und Ø MV ≤ 3 sind 35–36 vertretbar.
- **Richtwerte seit V1.6:** Minimum je Rolle = Median des Ziel-Archetyps (abgerundet), Ziel = Minimum + 2 (Länder + 3); das Template gilt nur, wenn kein Archetyp feststeht (`bewertung.richtwerte`, `08`, Grundsatz 15). Massen-Interaktion mindestens 1; symmetrische Kreaturen-Wipes zählen in Go-wide-Decks (Tokens, Aristokraten, Kindred, Counter, Voltron, Blink) nicht, weil sie den eigenen Plan zerstören.
- Gezielte Interaktion liegt bei vielen Archetypen unter 10. Damit nichts Wichtiges unbeantwortet bleibt, prüft die Bracket-3-Abnahme zusätzlich die **Interaktion nach Ziel** (Kreatur ≥ 5, Artefakt ≥ 2, Verzauberung ≥ 2, Friedhof ≥ 1 – Einschätzung, vorläufig).

### 3.2 Wie Partien gewonnen werden

*Daten (playgroup.gg, 390.731 Mehrspieler-Partien mit erfasstem Siegweg):* Kampfschaden 53,3 % · Nicht-Kampfschaden (Drain, Burn) 20,9 % · Combo 8,1 % · Commander-Schaden 8,0 % · alternative Siegbedingung 6,6 % · Mill 1,8 % · Gift 1,2 %. Median 9 Runden, im 4er-Pod 64 Minuten.

*Einschätzung:* Rund drei Viertel der Siege kommen über Schaden auf dem Brett oder Drain. Jedes Deck braucht einen Kampf- oder Drain-Finisher als Plan A oder B; reines Mill ist eine Nische.

### 3.3 Bracket 3 und Game Changer

*Daten (playgroup.gg „Power Level“, 411.959 Partien, 35.386 Decks):* Gewinnrate gegenüber dem Pod-Schnitt: 0 Game Changer −4,4 %, 1–3 Game Changer +3,2 %, 4 und mehr +10,5 % (Korrelation, keine Ursache). Das angegebene Bracket erklärt nur 2–3 % der Ergebnisse; etwa jedes vierte Deck spielt wie ein anderes Bracket; ab etwa 20 erfassten Partien sagt die eigene Bilanz mehr als das Label.

*Daten (playgroup.gg „Game Changers“, 52.941 Partien auf Playgroup Live mit virtuellen Karten, 27.10.2026):* Gewinnrate, wenn die Karte aufgelöst wurde, gegenüber Partien, in denen sie in der Bibliothek blieb. Größte Effekte: Thassa's Oracle +34,0 %, Consecrated Sphinx +23,5 %, Underworld Breach +22,0 %, Ad Nauseam +21,7 %, Seedborn Muse +16,5 %, Cyclonic Rift +16,3 % (Biorhythm +23,7 %, aber mit breitem Konfidenzintervall). Kleinste: Braids, Cabal Minion und Mishra's Workshop je +4,3 % (Intervall schließt 0 ein), Farewell +5,3 %. Laut Seite steigt der Wert mit dem Manawert – Korrelation, nicht der Beitrag der Karte allein.

*Einschätzung:* Die 3 Game-Changer-Slots zu nutzen ist „maximal stark im Rahmen“ – gewählt nach Wirkung im Deck, nicht nach Preis (`01`, Abschnitt 6). Ob ein Deck wirklich Bracket 3 ist, zeigt erst die Spielgruppe; Rückmeldungen nach Partien sind wertvoller als jede Liste.

### 3.4 Combos im Bracket 3

- Regel: keine 2-Karten-Combos, die früh im Spiel gewinnen (`01a_Format-Stand`). Commander Spellbook stuft jede Combo ein (Ruthless, Spicy, Powerful, Oddball, Core, Exhibition); Ruthless und Spicy sind die schärfsten Stufen.
- *Daten (Commander Spellbook, 27.10.2026)* – bekannte 2-Karten-Combos je Archetyp, jeweils ohne weitere Voraussetzungen:

| Archetyp | Combo | Einstufung |
|---|---|---|
| Lifegain / Aristokraten | Sanguine Bond + Exquisite Blood · Vito, Thorn of the Dusk Rose + Exquisite Blood | Spicy |
| Lifegain / Counter | Heliod, Sun-Crowned + Walking Ballista | Spicy |
| Counter | Devoted Druid + Vizier of Remedies | Spicy |
| Counter / Tokens | Scurry Oak + Ivy Lane Denizen | Ruthless |
| Blink | Saheeli Rai + Felidar Guardian | Spicy |
| Blink | Kiki-Jiki, Mirror Breaker + Restoration Angel | Ruthless |
| Spellslinger | Dualcaster Mage + Twinflame · Niv-Mizzet, Parun + Curiosity | 34 | 10 | 22 | 12 (9,5) | 2 | 3,5 | 2 | 1 | 2,8 |
| Spellslinger / Artefakte | Isochron Scepter + Dramatic Reversal (braucht Manasteine) | Spicy |
| Reanimator | Worldgorger Dragon + Animate Dead | 35 | 14 | 17 | 10 (5) | 2 | 1 | 2,5 | 2,5 | 3,1 |
| Artefakte | Basalt Monolith + Rings of Brighthearth | 34,5 | 14 | 17,5 | 9 (7) | 2 | 2,5 | 4,5 | 2,5 | 3,1 |
| Mill | Painter's Servant + Grindstone | 35,5 | 6,5 | 12 | 9 (6,5) | 2,5 | 5 | 3,5 | 0 | 3 |

- *Einschätzung:* Solche Paare nur nach Absprache mit der Gruppe und ohne Tutor-Paket drumherum; `deckbau.py pruefen` meldet sie automatisch.

### 3.5 Beliebtheit ist nicht Stärke

*Daten (EDHREC-Themen):* Tokens 207.434 Decks · +1/+1 Counters 167.888 · Combo 122.512 · Artifacts 115.610 · Aggro 103.706 · Spellslinger 89.421 · Reanimator 88.216 · Lifegain 82.344 · Control 72.395 · Aristocrats 69.846 · Burn 67.948 · Ramp 65.254 · Lands Matter 64.552 · Voltron 61.117 · Midrange 55.152.

*Daten (playgroup.gg, 27.10.2026):* Die Seite „Commander Archetypes“ beschreibt Archetypen und nennt Top-Commander (z. B. Aristokraten: Teysa Karlov, Savra, Sephiroth), weist aber **keine Gewinnraten je Archetyp** aus. Die Tier-Liste (365 Tage, 355.382 Partien, ab 150 Partien und 10 Spielern, auf 4 Spieler normiert, 25 % = Erwartungswert; S ≥ 35 %, D < 18 %) zeigt nur Einzelwerte, z. B. Endrek Sahr, Master Breeder (auf EDHREC meist als Aristokraten gebaut) 43,1 % im S-Tier bei nur 205 Partien, der Mill-Commander The Mindskinner 17,9 % im D-Tier bei 1.056 Partien.

*Einschätzung:* Für die Stärke eines konkreten Decks zählt der Commander mehr als der Archetyp – deshalb beim Deckbau immer die Commander-Seite auf playgroup.gg prüfen (`01`, Abschnitt 2).

### 3.6 Archetypen als Gegner – Bedrohungsprofil

*Einschätzung* – für die Meta-Analyse (Ablauf D) und den Interaktionsmix in `08`, Phase 2:

| Gegner spielt | woran der Plan hängt | was ihn bremst (in die Interaktion einplanen) |
|---|---|---|
| Tokens | breites Brett, Verdoppler, Anthem oder Drain pro Körper | Wipes (auch −X/−X-Wipes), Verdoppler und Anthems gezielt entfernen, Blocker gegen Overrun |
| Aristokraten | Opfer-Outlets, Tod-Payoffs, Rekursion | Friedhofs-Exil, Exil statt Zerstören, Payoff oder Outlet gezielt entfernen |
| +1/+1-Counter | wenige große Kreaturen, Verstärker (Hardened Scales-Klasse) | Exil-Removal, Edikte, Verstärker früh entfernen |
| Artefakte | Artefakt-Dichte, Steine, Rekursion (Academy Ruins) | Artefakt-Massenentfernung (Vandalblast-Klasse), Friedhofs-Exil |
| Spellslinger | bleibende Payoffs (Guttersnipe-Klasse), viele Zauber pro Zug | Payoffs sofort entfernen, Counterspells; Zauber-Limits (Rule of Law-Klasse) nur nach Absprache |
| Reanimator | Friedhof als zweite Hand | Friedhofs-Exil mit Instant-Tempo, Exil-Removal, Counter auf Reanimationszauber |
| Lifegain | Lebens-Engines, Drain-Combos | Payoffs entfernen, Verzauberungs-Removal gegen Sanguine Bond/Exquisite Blood |
| Landfall | Ländermasse, Land-Rekursion (Crucible of Worlds, Ramunap Excavator) | Payoffs (Lotus Cobra, Avenger of Zendikar) entfernen, Friedhofs-Exil, früher Druck (wenig Interaktion) |
| Voltron | eine Kreatur, Ausrüstung | Edikte, Exil, fliegende/Chump-Blocker, Artefakt-Removal gegen Ausrüstung |
| Enchantress | Verzauberungs-Dichte, Pillow-Fort | Verzauberungs-Wipes (Tranquility-Klasse), Druck vor Sphere of Safety |
| Blink / ETB | ETB-Werte, Flicker mit Instant-Tempo | Exil-Removal, Counter; ETB-Unterdrücker (Torpor Orb-Klasse) nur nach Absprache |
| Kindred | Lords und Typ-Engines | Wipes, Lords gezielt entfernen |
| Mill | langsamer Plan, Mill-Engines | Druck, Engines entfernen, Friedhof-Rückmischer (Elixir of Immortality-Klasse) |

Faustregel: Friedhofs-Exil mit Instant-Tempo und Exil-Removal treffen die meisten Archetypen gleichzeitig (Aristokraten, Reanimator, Landfall-Rekursion, Artefakt-Rekursion) – gute Kandidaten für flexible Slots.

## 4. Übersicht der Archetypen (Daten)

Grundrollen als Median der Durchschnittsdecks. Zum Vergleich der Median aller 80 Decks: Länder 35 · Ramp 12 · Kartenvorteil 12 · gezielt 9 (Instant 5) · Wipes 2 · Counter 1 · Schutz 4 · Ø MV 2,9.

| Archetyp | EDHREC-Decks | Länder | Ramp | Karten-vorteil | Gezielt (Instant) | Wipes | Counter | Schutz | Tutoren | Ø MV |
|---|---|---|---|---|---|---|---|---|---|---|
| Tokens | 207.434 | 35 | 9 | 10 | 8 (5,5) | 2,5 | 0 | 4 | 1 | 3 |
| Aristokraten | 69.846 | 35 | 11 | 11,5 | 11 (5,5) | 3,5 | 0 | 1,5 | 1,5 | 2,8 |
| +1/+1-Counter | 167.888 | 35 | 12,5 | 12 | 7 (5) | 2 | 2 | 7 | 0 | 2,8 |
| Artefakte | 115.610 | 34,5 | 14 | 17,5 | 9 (7) | 2 | 2,5 | 4,5 | 2,5 | 3,1 |
| Spellslinger | 89.421 | 34 | 10 | 22 | 12 (9,5) | 2 | 3,5 | 2 | 1 | 2,8 |
| Reanimator | 88.216 | 35 | 14 | 17 | 10 (5) | 2 | 1 | 2,5 | 2,5 | 3,1 |
| Lifegain | 82.344 | 35 | 7,5 | 12,5 | 8 (6) | 3 | 0 | 2,5 | 1 | 3 |
| Lands Matter / Landfall | 64.552 + 22.972 | 39 | 23 | 11,5 | 6 (4,5) | 1,5 | 0 | 2 | 0 | 3,3 |
| Voltron | 61.117 | 35,5 | 11 | 8 | 7,5 (5) | 2 | 0,5 | 12 | 5,5 | 2,6 |
| Enchantress | 54.221 | 36 | 11,5 | 12,5 | 8 (3) | 2 | 0,5 | 4,5 | 3 | 3,5 |
| Blink / ETB | 38.089 | 35 | 9,5 | 17 | 14 (7) | 2,5 | 3,5 | 11 | 0,5 | 3,2 |
| Kindred | je Typ, z. B. Dragons 21.271, Elves 16.963 | 35,5 | 9 | 11 | 8 (4) | 4 | 0 | 6 | 1,5 | 3,1 |
| Mill | 47.477 | 35,5 | 6,5 | 12 | 9 (6,5) | 2,5 | 5 | 3,5 | 0 | 3 |

## 5. Steckbriefe

Kern-Pakete = *Daten* (Median, Spanne). Schlüsselkarten = EDHREC-Karten mit hoher Synergie im Thema (*Daten:* Anteil der Themen-Decks / Synergie in Prozentpunkten); allgemeine Staples wie Swords to Plowshares sind weggelassen. Fallen und Hinweise = *Einschätzung*. Der Status der Schlüsselkarten in der Sammlung steht im `12_Sammlungsprofil`.

### 5.1 Tokens (Go-wide)
- **Plan:** viele kleine Körper, dann Anthem, Overrun oder Drain pro Körper.
- **Kern-Pakete:** Token-Quellen 19,5 (8–24), davon wiederholbar 10 (7–17) · Anthems für alle eigenen Kreaturen/Tokens 3 (2–3; typbezogene Lords und „nontoken“-Anthems zählen seit V1.6 nicht) · Token-Verdoppler 4 (0–11) · Overrun-Finisher 0 (0–2).
- **Typische Nebenpakete:** im Median 6 Tod-Payoffs und 5,5 Opfer-Outlets – Tokens und Aristokraten überschneiden sich stark.
- **Schlüsselkarten:** Mirkwood Bats 29 %/+20 · Impact Tremors 29/+20 · Skullclamp 30/+19 · Doubling Season 28/+17 · Parallel Lives 24/+18 · Jetmir, Nexus of Revels 22/+17 · Second Harvest 21/+16 · Warleader's Call 22/+15 · Anointed Procession 22/+15.
- **Beispiel-Commander:** Baylen, the Haymaker · Chatterfang, Squirrel General · Krenko, Mob Boss · Edgar Markov.
- **Fallen:** eigene Wipes zerstören den Plan → einseitige Wipes oder Schutzzauber (Heroic Intervention-Klasse). Zu viele einmalige Token-Zauber statt wiederholbarer Quellen. Kein Finisher: Overrun spielt laut Daten kaum jemand, Drain pro Körper (Impact Tremors, Mirkwood Bats) übernimmt diese Rolle.

### 5.2 Aristokraten
- **Plan:** Opfern als Ressource – jedes Sterben drainiert, zieht Karten oder macht Mana. Drei Beine: Outlet, Futter, Payoff. Laut EDHREC-Guide (27.10.2025) ist das Payoff-Bein dasjenige, das die meisten Deckbauer vernachlässigen; zwischen bezahlten und kostenlosen Outlets liege ein großer Unterschied.
- **Kern-Pakete:** Opfer-Outlets 10 (7–16), davon kostenlos 4 (1–8) · Futter 17,5 (5–24) · Tod-/Opfer-Payoffs 15 (7–22) · Kreaturen-Rekursion 2 (0–8).
- **Grundrollen:** mehr gezielte Interaktion (11) und Wipes (3,5, oft Edikte), wenig Schutz (1,5).
- **Schlüsselkarten:** Pitiless Plunderer 43/+34 · Ashnod's Altar 41/+35 · Bastion of Remembrance 36/+30 · Goblin Bombardment 35/+30 · Mayhem Devil 36/+26 · Deadly Dispute 38/+25 · Cauldron of Essence 35/+26 · Phyrexian Tower 34/+25 · Warren Soultrader 31/+25 · Village Rites 32/+23 · Victimize 33/+20; dazu die Top-Karten Blood Artist (50 %), Zulaport Cutthroat (50 %), Viscera Seer (44 %).
- **Beispiel-Commander:** Teysa Karlov · Sephiroth, Fabled SOLDIER · Meren of Clan Nel Toth · Chatterfang · Zurgo Stormrender.
- **Fallen:** zu wenige Payoffs; teure statt kostenloser Outlets; auf gegnerisches Removal hoffen (Gegner meiden das); Friedhofs-Hate trifft die Rekursion.

### 5.3 +1/+1-Counter
- **Plan:** Counter verteilen, verstärken (Hardened Scales-Klasse), mit Proliferate stapeln; Sieg über große Kreaturen mit Evasion.
- **Kern-Pakete:** Counter-Quellen 11,5 (6–24) · Counter-Payoffs 18 (2–41) · Counter-Verstärker 4,5 (0–11) · Proliferate 6 (0–18).
- **Grundrollen:** viel Schutz (7), wenig gezielte Interaktion (7).
- **Schlüsselkarten:** Branching Evolution 30/+23 · Kami of Whispered Hopes 30/+23 · Corpsejack Menace 28/+23 · Forgotten Ancient 27/+20 · Herald of Secret Streams 24/+21 · Kutzil, Malamet Exemplar 31/+16 · Simic Ascendancy 24/+19 · Gavony Township 23/+16 · The Ozolith 20/+17 · Winding Constrictor 20/+16; Top-Karten Hardened Scales (45 %), Inspiring Call (37 %), Rhythm of the Wild (35 %).
- **Beispiel-Commander:** The Wise Mothman · Ms. Bumbleflower · Hakbal of the Surging Soul · Atraxa, Praetors' Voice · Giada, Font of Hope.
- **Fallen:** alles auf wenigen Kreaturen → wipe-anfällig (daher der hohe Schutz-Anteil); Payoffs ohne genug Quellen; zu wenig Interaktion gegen fremde Engines.

### 5.4 Artefakte
- **Plan:** hohe Artefakt-Dichte für Kostensenkung, Kartenvorteil und Tokens; Sieg über Synergie-Burst oder große Konstrukte.
- **Kern-Pakete:** Artefakte 37,5 (23–48) · Artefakt-Payoffs 34,5 (2–44) · Artefakt-Token-Quellen 7 (1–14) · Kostensenker 2,5 (0–6).
- **Grundrollen:** viel Ramp (14) und Kartenvorteil (17,5) durch Steine, Clues und Treasures; Counterspells 2,5.
- **Schlüsselkarten:** Thought Monitor 32/+29 · Sai, Master Thopterist 32/+29 · Padeem, Consul of Innovation 30/+27 · Fabricate 29/+24 · Thoughtcast 27/+24 · Kappa Cannoneer 27/+23 · Urza, Lord High Artificer 26/+23 · Academy Ruins 34/+29 · Inventors' Fair 31/+27; Artefaktländer (Seat of the Synod 57 % u. a.) als Synergie-Länder; Top-Karten Etherium Sculptor (51 %), Foundry Inspector (38 %).
- **Beispiel-Commander:** Breya, Etherium Shaper · Urza, Chief Artificer · Urza, Lord High Artificer · Toph, the First Metalbender.
- **Fallen:** Artefakt-Wipes der Gegner (Vandalblast-Klasse) → Redundanz und Schutz; blaue Artefaktdecks rutschen leicht in Combo-Bereiche → Bracket prüfen.

### 5.5 Spellslinger
- **Plan:** viele billige Spontanzauber und Hexereien; bleibende Payoffs machen aus jedem Zauber Tokens, Schaden oder Karten.
- **Kern-Pakete:** Spontanzauber/Hexereien 36 (28–41) · bleibende Zauber-Payoffs 10 (4–20) · Zauber kopieren 3 (0–8) · Kostensenker 2,5 (0–5).
- **Grundrollen:** höchster Kartenvorteil (22), viel Instant-Interaktion (12, davon 9,5 Instant-Tempo), Counterspells 3,5, niedrige Kurve (2,8).
- **Schlüsselkarten:** Manamorphose 37/+34 · Jeskai Ascendancy 35/+30 · Guttersnipe 35/+29 · Opt, Ponder, Preordain (34–38 %/+25–28) · Goblin Electromancer 34/+26 · Veyran, Voice of Duality 33/+26 · Lightning Bolt 35/+24 · Monastery Mentor 28/+26 · Stormcatch Mentor 30/+23; Top-Karten Storm-Kiln Artist (56 %), Whirlwind of Thought (53 %), Archmage Emeritus (50 %).
- **Beispiel-Commander:** Vivi Ornitier · Fire Lord Azula · Y'shtola, Night's Blessed · Kuja, Genome Sorcerer.
- **Fallen:** zu wenige Payoffs („Zauber ohne Plan“); teure Zauber in einer 2,7er-Kurve; zu wenig Kreaturen gegen Aggro; Finisher einplanen (Burn pro Zauber, Token-Armee).

### 5.6 Reanimator / Friedhof
- **Plan:** Friedhof füllen, große Ziele zurückholen; der Friedhof wird zur zweiten Hand.
- **Kern-Pakete:** Friedhof füllen (Self-Mill, Loot, Entomb) 22 (9–29) · Reanimation 8 (7–15); dazu große Ziele (Kreatur MV ≥ 6) 4,5 (2–13).
- **Grundrollen:** Ramp 14, Kartenvorteil 17, Tutoren 2,5 (Entomb-Klasse).
- **Schlüsselkarten:** Animate Dead 32/+23 · Buried Alive 30/+23 · Entomb 27/+20 · Anger 33/+27 · Life from the Loam 24/+20 · Six 24/+19 · Sidisi, Brood Tyrant 23/+19 · Colossal Grave-Reaver 25/+20 · Kheru Goldkeeper 25/+21; Top-Karten Reanimate (51 %), Faithless Looting (46 %), Eternal Witness (38 %), Victimize (37 %).
- **Beispiel-Commander:** Teval, the Balanced Scale · Terra, Herald of Hope · Meren of Clan Nel Toth · Muldrotha, the Gravetide.
- **Fallen:** Friedhofs-Hate (Bojuka Bog, Rest in Peace-Klasse) → Plan B und Rekursion aus mehreren Winkeln; zu viele Ziele, zu wenig Enabler; Ziele, die auf der Hand verrotten.

### 5.7 Lifegain
- **Plan:** viele kleine Lebensgewinne, die Payoffs in Counter, Tokens oder Drain umwandeln.
- **Kern-Pakete:** wiederholbare Lebens-Quellen 18,5 (17–27) · Lifegain-Payoffs 14 (4–31).
- **Grundrollen:** wenig Ramp (7,5), Wipes 3.
- **Schlüsselkarten:** Exquisite Blood 34/+29 · Authority of the Consuls 34/+27 · Soul's Attendant 30/+27 · Enduring Tenacity 30/+26 · Blood Artist 32/+21 · Marauding Blight-Priest 27/+24 · Prosperous Innkeeper 26/+24 · Lathiel, the Bounteous Dawn 26/+23; Top-Karten Vito, Thorn of the Dusk Rose (45 %), Sanguine Bond (44 %), Soul Warden und Essence Warden (je 40 %).
- **Beispiel-Commander:** Frodo, Adventurous Hobbit // Sam · Giada, Font of Hope · Oloro, Ageless Ascetic · Liesa, Shroud of Dusk.
- **Fallen:** Leben allein gewinnt nicht → Payoff-Dichte und Finisher; viele schwache „Gain 2“-Karten; die bekannten Drain-Combos (Abschnitt 3.4) liegen im Paket nahe.

### 5.8 Lands Matter / Landfall
- **Plan:** Länder als Ressource – zusätzliche Landdrops, Fetches, Land-Rekursion → Landfall-Trigger.
- **Kern-Pakete:** Land-Ramp 19 (6–28) · Landfall-Payoffs 14 (9–25) · zusätzliche Landdrops 10 (1–15) · Opfer-/Fetch-Länder 8 (6–12) · Land-Rekursion 5 (0–12).
- **Grundrollen:** meiste Länder (39), Ramp 23 (Landsuche zählt als Ramp; Spanne 16–33); dafür nur 6 gezielte Interaktion und 1,5 Wipes.
- **Schlüsselkarten:** Azusa, Lost but Seeking 49/+42 · Avenger of Zendikar 45/+37 · Felidar Retreat 43/+38 · Tannuk, Memorial Ensign 43/+38 · Ancient Greenwarden 40/+36 · Ramunap Excavator 40/+34 · Harrow 40/+32 · Oracle of Mul Daya 36/+31 · Rampaging Baloths 36/+29; Top-Karten Tatyova, Benthic Druid (61 %), Scute Swarm (49 %), Lotus Cobra (48 %).
- **Beispiel-Commander:** Hearthhull, the Worldseed · The Necrobloom · Omnath, Locus of Creation · Aesi, Tyrant of Gyre Strait.
- **Fallen:** zu wenig Interaktion – die Daten zeigen den Trend, Grundsatz 8 gleicht ihn aus. Crop Rotation, Field of the Dead und Gaea's Cradle sind Game Changer; Armageddon-Effekte sind Massen-Landzerstörung (im Bracket 3 verboten).

### 5.9 Voltron (Equipment / Auren)
- **Plan:** eine Kreatur (meist der Commander) groß, ausweichend und geschützt machen; Sieg über 21 Commander-Schaden.
- **Kern-Pakete:** Ausrüstung 15 (2–24) – Auren-Decks sind seltener (Median 1, Spanne 0–23) · Evasion/Doppelschlag geben 13 (3–16) · Schutz 12 (10–20) · Equipment-/Auren-Payoffs 16 (1–24).
- **Grundrollen:** Schutz 12, Tutoren 5,5 (Ausrüstungs-Tutoren), nur 8 Kartenvorteil, niedrigste Kurve (2,6).
- **Schlüsselkarten:** Rogue's Passage 52/+32 · Open the Armory 37/+32 · Sigarda's Aid 34/+30 · All That Glitters 30/+26 · Rancor 29/+25 · Steelshaper's Gift 27/+24 · Fighter Class 26/+23 · Stoneforge Mystic 24/+22 · The Reaver Cleaver 25/+20; Top-Karten Swiftfoot Boots (56 %), Sram, Senior Edificer (44 %), Puresteel Paladin (42 %), Boros Charm (42 %).
- **Beispiel-Commander:** Cloud, Ex-SOLDIER · Kotis, the Fangkeeper · Light-Paws, Emperor's Voice · Captain America, First Avenger.
- **Fallen:** alles auf eine Karte → Plan B; Edikte (Opfer-Effekte) umgehen Hexproof; Kartenvorteil fehlt.

### 5.10 Enchantress
- **Plan:** hohe Verzauberungs-Dichte plus Engines, die je Verzauberung eine Karte ziehen → Wert, Pillow-Fort-Schutz, Tokens.
- **Kern-Pakete:** Verzauberungen 41 (26–43) · Enchantress-Engines 6,5 (1–8) · Verzauberungs-Payoffs 23,5 (4–30).
- **Grundrollen:** nur 3 Instant-Interaktion, höchste Kurve (3,5).
- **Schlüsselkarten:** Hall of Heliod's Generosity 49/+43 · Sphere of Safety 40/+36 · Doomwake Giant 36/+34 · Satyr Enchanter 35/+32 · Inquisitive Glimmer 34/+32 · Wild Growth 37/+27 · Herald of the Pantheon 32/+30 · Sanctum of All 33/+28 · Sigil of the Empty Throne 31/+29; Top-Karten Sanctum Weaver (67 %), Sythis, Harvest's Hand (63 %), Eidolon of Blossoms (58 %), Enchantress's Presence (55 %), Setessan Champion (53 %), Sterling Grove (53 %).
- **Beispiel-Commander:** Go-Shintai of Life's Origin · Anikthea, Hand of Erebos · Sythis, Harvest's Hand · Bello, Bard of the Brambles.
- **Fallen:** Sorcery-Tempo – schwach gegen Combo und Stack-Interaktion; Verzauberungs-Wipes (Tranquility-Klasse).

### 5.11 Blink / ETB
- **Plan:** Kreaturen mit Eintritts-Effekt mehrfach auslösen (Flicker) und Trigger verdoppeln.
- **Kern-Pakete:** Flicker-Effekte 20 (8–24) · Kreaturen mit ETB-Wert 16,5 (8–22) · Trigger-Verdoppler 3 (0–5).
- **Grundrollen:** viel gezielte Interaktion (14, oft ETB-Removal), Kartenvorteil 17, Schutz 11 (Flicker schützt), Counterspells 3,5.
- **Schlüsselkarten:** Essence Flux 39/+35 · Eerie Interlude 38/+35 · Displacer Kitten 38/+33 · Momentary Blink 36/+33 · Conjurer's Closet 35/+32 · Restoration Angel 33/+30; Top-Karten Ephemerate (65 %), Soulherder (55 %), Cloudshift (49 %), Ghostly Flicker (48 %), Panharmonicon (39 %).
- **Beispiel-Commander:** Brago, King Eternal · Niko, Light of Hope · Atraxa, Grand Unifier · Pantlaza, Sun-Favored.
- **Fallen:** ETB-Kreaturen ohne Flicker sind nur langsames Midrange; Schleifen um Displacer Kitten und die Combos aus Abschnitt 3.4 heben das Bracket.

### 5.12 Kindred (Tribal)
- **Plan:** Dichte eines Kreaturtyps, Lords und Typ-Payoffs, Kartenvorteil über den Typ.
- **Kern-Pakete:** Typ-Payoffs (Lords, „wähle einen Kreaturtyp“) 10 (8–15); Gestaltwandler 0–1. Dazu im Median 6,5 Anthems.
- **Grundrollen:** die meisten Wipes (4), Schutz 6, wenig Ramp (9).
- **Schlüsselkarten (in mehreren Typ-Themen):** Shared Animosity 26/+22 · Urza's Incubator 25/+21 · Kindred Discovery 24/+17 · Raise the Palisade 22/+18 · Harmonized Crescendo 21/+19 · Herald's Horn 21/+15; dazu typ-spezifische Karten (bei Elfen z. B. Elvish Archdruid 84 %, Priest of Titania 75 %).
- **Beispiel-Commander:** Lathril (Elfen) · Wilhelt (Zombies) · The Ur-Dragon (Drachen) · Giada (Engel) · Krenko (Goblins) · Edgar Markov (Vampire) · Hakbal (Merfolk) · Pantlaza (Dinosaurier).
- **Fallen:** Typ vor Qualität – schwache Typkarten verdrängen Interaktion; Wipe-Anfälligkeit; Payoffs ohne genug Körper.

### 5.13 Mill (Gegner)
- **Plan:** die Bibliotheken der Gegner leeren; Verstärker (Bruvac-Klasse) und Friedhofs-Payoffs.
- **Kern-Pakete:** Mill-Effekte 23,5 (4–32) · Mill-Verstärker/-Payoffs 10 (2–14).
- **Grundrollen:** die meisten Counterspells (5), am wenigsten Ramp (6,5).
- **Schlüsselkarten:** Maddening Cacophony 35/+33 · The Water Crystal 34/+31 · Hedge Shredder 31/+28 · Drown in the Loch 31/+26 · Fractured Sanity 29/+28 · Mindcrank 29/+27 · Psychic Corrosion 27/+25; Top-Karten Consuming Aberration (39 %), Syr Konrad, the Grim (37 %), Ruin Crab (37 %).
- **Beispiel-Commander:** The Wise Mothman · Captain N'ghathrod · Hope Estheim · The Mindskinner · Phenax, God of Deception.
- **Fallen:** drei Gegner mit je 99 Karten machen Mill langsam (Abschnitt 3.2: 1,8 % der Siege); Karten, die den Friedhof zurückmischen; ohne Drain- oder Combo-Plan B schwach.

## 6. Anwendung beim Deckbau

1. Commander-Steckbrief (`deckbau.py commander`) → Archetyp wählen (EDHREC-Thema).
2. Kern-Pakete aus Abschnitt 5 als Ziel in den Steckbrief (`08`, Phase 3) übernehmen; Grundrollen weiter nach `08` (unsere Mindestwerte gelten zusätzlich).
3. Entwurf prüfen: `archetypen.py deck entwurf.txt --archetyp <a>` vergleicht die Pakete mit den Medianen; ⚠ = Kernpaket unter dem kleinsten Wert der Datenbasis.
4. Weg 1: `archetypen.py karten <a> --paket <p> --farben <WUBRG>` listet freie Karten je Paket; den Überblick gibt `12_Sammlungsprofil`.
5. Interaktionsmix: Bedrohungsprofil der Spielgruppe (Ablauf D) mit Abschnitt 3.6 abgleichen.
6. Upgrade eines bestehenden Decks (Ablauf B): Zeile in `12a_Deck-Raster` als Startpunkt, dann `deckbau.py upgrade` (Raus-Sperren schützen Kernpakete und Commander-Bezug) und `abnahme`.

Archetyp-Schlüssel: tokens, aristokraten, counters, artefakte, spellslinger, reanimator, lifegain, landfall, voltron, enchantress, blink, kindred, mill.

## 7. Pflege

- Setup in einer neuen Sitzung: kommt mit der Werkzeugkiste (`05a_Sitzungsstart`). Mit `mtg.sqlite` zählt der aktuelle Bestand; ohne Datenbank `--frei claude/07_Sammlung-Frei.csv --decks claude/decks/*.txt` angeben (Scryfall-Bulk wird bei Bedarf geladen).
- Richtwerte erneuern (nur Admin; sonst Hinweis an den Admin): `archetypen.py daten` (≈ 1 Minute, rund 120 EDHREC-Abrufe) → `archetypen_daten.json` ersetzen, Tabellen in Abschnitt 3.1, 4 und 5 nachziehen.
- Turnus: nach großen Commander-Sets oder alle drei Monate, zusammen mit `01a_Format-Stand`.
- Sammlungsprofil nach größeren Zugängen neu erzeugen (`archetypen.py profil`).

## 8. Quellen

- EDHREC: Themenliste und Themenseiten (edhrec.com/tags), Durchschnittsdecks (json.edhrec.com/pages/average-decks/…), Guide „EDHREC Guide to Aristocrats in Commander“ (Cooper Gottfried, 27.10.2025): edhrec.com/guides/edhrec-guide-to-aristocrats-in-commander
- playgroup.gg: Siegwege playgroup.gg/commander/how-to-play · Power Level playgroup.gg/commander/power-level · Game Changers playgroup.gg/commander/game-changers · How Many Lands playgroup.gg/commander/how-many-lands · Deck Template playgroup.gg/commander/deck-template · Archetypen playgroup.gg/commander/archetypes · Tier-Liste playgroup.gg/commanders/tier-list/365-days
- Commander Spellbook: Combo-Einstufungen über backend.commanderspellbook.com/variants
- Scryfall: Bulk-Daten default_cards und oracle_tags vom 30.10.2026.
