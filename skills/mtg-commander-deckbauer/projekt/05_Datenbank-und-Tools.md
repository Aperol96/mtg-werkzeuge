# Datenbank & Tools (mtg_db.py, deckbau.py, bewertung.py, simulation.py, archetypen.py, kartenbilder.py, protokoll.py, paket.py, zugang.py)

**Stand:** 29.10.2026 (V1.7.1: Begriffe Sammlung und freie Karten geschärft, Abschnitt 0) · Sitzungsstart: `05a_Sitzungsstart` · Tools: `mtg_db.py` (Datenbank, Sammlung, Decks, Vergleich, ManaBox → Moxfield), `deckbau.py` (geführter Deckbau, Upgrade, Abnahme, Gegentest; Verfahren in `08_Deckbau-Verfahren`), `bewertung.py` (Bewertungsregeln), `simulation.py` (Konsistenz-Simulation), `archetypen.py` (Archetypen-Pakete, Sammlungsprofil; Wissen in `11_Archetypen-Playbook`, Ergebnis in `12_Sammlungsprofil`, Richtwerte in `archetypen_daten.json`), `kartenbilder.py` (PDFs mit Kartenbildern, Abschnitt 4b), `protokoll.py` (04/09/10 lesen und pflegen) und `zugang.py` (Anmeldung, Gast-PIN, Freischaltung, Abschnitt 4d) · Zugang: `zugang.json` · Gast-Archive: `claude/gaeste/<name>.txt` · Decknamen und Ergänzungen: `claude/tools/deck_namen.json` · **Bestand = Basis + Buchungen in `claude/sammlung/`:** Basis `basis.csv` = Moxfield-CSV aus der Ersteinrichtung (`13_Betriebsmodus-und-Weitergabe`, Abschnitt 8) + Journal `buchungen.csv` (alle Zu- und Abgänge seitdem) · **Decks:** Soll-Stand `claude/decks/<deckname>.txt` = maßgebliche Deckliste · Listen (abgeleitet): `claude/06_Sammlung-Bestand.csv` (Bestand), `claude/07_Sammlung-Frei.csv` (freie Karten) · Ideen und geplante Käufe: `claude/10_Geplante-Kaeufe-und-Ideen.md` · Protokoll: `claude/09_Aenderungsprotokoll.md` · persönliche Einstellungen: `claude/nutzerprofil.md`

Alles, was die Werkzeuge brauchen, steht in dieser Datei, in `05a` und in `08`; zusätzliche Skills sind nicht nötig.

---

## 0. Grundregeln (25.10.2026; Nomenklatur und Datenhoheit 26.10.2026; Ablage 27.10.2026)

- **Datenhoheit (festgelegt vom Nutzer, 26.10.2026): Das Projekt ist die Hauptdatenbank.** Alle Änderungen an Bestand und Decks werden hier beschlossen und gebucht.
  - **Moxfield** ist nur die externe Datenbank für die Nutzung außerhalb des Projekts. Richtung immer **Projekt → Moxfield** (Einfügeblöcke, Deck-TXT, Bestands-CSV). Änderungen in Moxfield wirken hier nicht.
  - **Ausnahmen:** Fehlerkorrektur, oder der Nutzer nutzt ausdrücklich einen Moxfield-Export, um die Daten hier zu überschreiben (dann wird dieser Export die neue Basis, `buchungen.csv` wird geleert, Eintrag „Import“).
  - **ManaBox** ist nur Zulieferer gescannter Daten: Scans werden hier gebucht (Zugang in `buchungen.csv` bzw. Deckliste) und als Moxfield-Datei für den Nutzer ausgegeben.
- **Nomenklatur (festgelegt vom Nutzer, 26.10.2026; geschärft 29.10.2026): Bestand = Deckkarten + Sammlung; freie Karten = Sammlung − vorgemerkte Karten.**
  - **Bestand** = alles, was der Nutzer besitzt = Basis + `buchungen.csv` (Basis enthält die Deckkarten bereits – nicht noch einmal addieren). Liste `06_Sammlung-Bestand.csv`, Spalte „Besitz“.
  - **Deckkarten** = Karten, die in einem Deck stecken (Haupt-, Commander- und Sideboard, ohne Maybeboard). Spalte „davon in Decks“.
  - **Sammlung** = Bestand minus Deckkarten – Karten, die in keinem Deck stecken.
  - **Vorgemerkt** = Sammlungskarten, die eine nicht umgesetzte Idee reserviert (`vormerkungen.csv`, Tabelle in `10`). Geplante Verkäufe (`V-nnn`) reservieren nicht, sie markieren nur.
  - **Freie Karten** = Sammlung minus vorgemerkte Karten. Liste `07_Sammlung-Frei.csv`. Für Upgrade-Stufe 0, Weg 1 und Tauschkandidaten zählen nur freie Karten → `suche --nur-frei`.
  - Die Tool- und Spaltennamen (`collection`, `v_besitz`, „frei“) bleiben technisch unverändert; in Antworten gelten die Begriffe oben.
- **Buchungsjournal `claude/sammlung/buchungen.csv`:** Moxfield-Spalten + `Buchung` (ID `B-nnn` + Art: Kauf, Verkauf, Scan, Tausch, Korrektur), `Datum`, `Beleg`. Zugang = positive, Abgang = negative `Count`, gleiche Druckversion (Edition + Collector Number) wie in der Basis. Einlesen mit `build --sammlung data/basis.csv data/buchungen.csv` (Zusatzspalten werden ignoriert). Nur ergänzen, nie Zeilen ändern; Konsolidieren (Basis neu schreiben, Journal leeren) nur auf Wunsch, mit Protokoll-Eintrag.
- **Verkäufe:** gemeldete Verkäufe gegen den Bestand prüfen; steckt die Karte in einem Deck → Hinweis (Deckänderung nötig). Dann als Abgang buchen, 06/07 neu erzeugen, Eintrag „Verkauf“ im Protokoll; der Nutzer löscht die Karte in Moxfield (Moxfield-Import fügt nur hinzu).
- **Käufe und Scans:** Zugang buchen, 06/07 neu erzeugen, Eintrag „Kauf“ bzw. „Import“; Moxfield-Bestands-CSV nur mit den Zugängen an den Nutzer (Import fügt hinzu).
- **Abgeleitete Listen 06/07:** nach jeder Buchung neu erzeugen. Sind sie älter als die letzte Buchung (Hinweis in `10`, Abschnitt „In Moxfield nachziehen / Wartung“), gilt der berechnete Bestand aus Basis + Buchungen; beim nächsten Datenbank-Bau neu erzeugen. Nach größeren Zugängen auch `12_Sammlungsprofil` neu erzeugen (Abschnitt 4a).
- **Ideen und geplante Käufe** stehen zentral in `claude/10_Geplante-Kaeufe-und-Ideen.md` (Regeln dort) – Soll-Stände bleiben unverändert, bis der Nutzer nach der Freigabe den physischen Aufbau meldet („gebaut“).
- **Vormerkungen** (Sammlungskarten, die eine nicht freigegebene Idee reserviert): `claude/sammlung/vormerkungen.csv` mit den Spalten `Idee, Name, Anzahl, Datum, Hinweis`. `build` lädt die Datei (`--vormerkungen`, Standard `data/vormerkungen.csv`) und zieht sie von „frei“ ab; Konflikte (mehr vorgemerkt als frei) meldet der Bau. `deckbau.py … --idee I-nnn` behandelt die Vormerkungen dieser einen Idee als frei (für den Entwurf genau dieser Idee). Immer synchron mit der Tabelle in `10` halten. **Geplante Verkäufe (seit V1.5):** Ideen `V-nnn` sind *weiche* Vormerkungen – sie ziehen nicht von „frei“ ab; `build` markiert passende freie Exemplare (Spalte `exemplare.verkauf`; `Druck: SET Nr de|en [foil]` im Hinweis wählt das Exemplar), `v_karten` hat die Spalten `verkauf_geplant` und `verkauf_ideen`, 06/07 die Spalte „Verkauf geplant“; `deckbau.py upgrade`, `kandidaten` und `verkauf` zeigen „Verkauf geplant (V-nnn)“.
- **Standardländer sind wahrscheinlich nicht vollständig eingescannt.** Beim Deckbau erst die Länderzahl festlegen, dann die Aufteilung mit `laender --plan` gegen den Bestand prüfen und den Nachkauf **separat** vorschlagen.
- **Physische Ablage der Sammlung (Standard; eine abweichende Ablage steht im Nutzerprofil):** zuerst nach **Farbe**, darin **eine Box je Kartentyp**; **Länder** und **Standardländer** haben eigene Boxen; innerhalb einer Box keine weitere Sortierung. Mehrfarbige Karten liegen bei der Farbe ihres **ersten farbigen Manasymbols von links** (oben rechts auf der Karte), z. B. Zurgo Stormrender {R}{W}{B} → Rot, Boros Reckoner {R/W} → Rot, Dismember {1}{B/P}{B/P} → Schwarz, Omnath, Locus of the Roil {1}{G}{U}{R} → Grün. Karten ohne farbiges Symbol → Farblos. Doppelseitige, Split- und Abenteuer-Karten nach der Vorderseite. Typ-Box bei mehreren Typen (Annahme, vom Nutzer nicht festgelegt): Kreatur vor Planeswalker, Schlacht, Spontanzauber, Hexerei, Artefakt, Verzauberung – Artefakt- und Verzauberungskreaturen also bei den Kreaturen. Umgesetzt in `kartenbilder.py` (`box()`). Weicht die Ablage des Nutzers ab, gelten die Box-Etiketten nur als Farb- und Typangabe; Claude notiert den Wunsch nach einer anderen Ordnung an den Admin.
- **Decks:** Der Soll-Stand in `claude/decks/` ist die maßgebliche Deckliste. Deckänderungen werden hier beschlossen (Freigabe), nach dem physischen Aufbau gebucht (Meldung „gebaut“) und als Einfügeblock/TXT nach Moxfield ausgegeben. Ein Neuscan wird wie in Abschnitt 2 abgeglichen.

## 1. Was die Datenbank enthält

SQLite-Datei, gebaut aus dem Bestandsexport, allen Decks und den Scryfall-Bulk-Daten:

| Tabelle/Sicht | Inhalt |
|---|---|
| `cards` | alle ≈ 34.000 Papier-Karten: Oracle-Text, MV, Typ, Farbidentität, Legalität, Game-Changer-Flag, Reserved List, EDHREC-Rang, günstigster EUR-Preis + Druck |
| `prints` | alle ≈ 103.000 Drucke mit Set, Nummer, Seltenheit, EUR/EUR-Foil/EUR-Etched |
| `tags` | Scryfall-Funktionstags inkl. Elterntags (z. B. `removal`, `spot-removal`, `ramp`, `sweeper`, `mass-land-denial`, `extra-turn`) |
| `rulings` | offizielle Rulings je Karte |
| `collection` | Bestand (Basis + Buchungen; Abgänge als negative Zeilen), je Zeile der Druckversion zugeordnet (Scryfall-ID > Set + Nummer > Name) |
| `decks`, `deck_cards` | Decks mit Format, Farben, Commander, Kartenzahl, Herkunft, Strategie, Status, vollem Namen und Deckname (`kurz`) |
| `vormerkungen`, `v_vorgemerkt` | von Ideen reservierte Sammlungskarten (aus `vormerkungen.csv`) |
| `v_karten` | je Karte: Besitz (Bestand), davon in Decks (Deckkarten), vorgemerkt (Ideen), frei (freie Karten = Besitz − Decks − Vormerkungen), in welchen Decks, Verkauf geplant |
| `exemplare` | jedes physische Exemplar mit Druck, Sprache, Finish und Ort (Abschnitt 3) |
| `v_basics` | Standardländer (für `laender`) |

Preise: Scryfall-EUR (Quelle Cardmarket) mit Datum des Bulk-Downloads; deutsche Karten zum Preis der englischen Druckversion (Näherung). EDHREC-Antworten werden 3 Tage in `cache/edhrec/` zwischengespeichert.

## 2. Sitzung und Abläufe am Bestand

Sitzungsstart (Pakete lesen, Startbefehl, Datenbank-Bau, Zurückschreiben): **`05a_Sitzungsstart`**. Dort auch die Schnellabfragen (`mtg_db.py frei`, `protokoll.py offen|zeigen`).

1. **Neuer ManaBox-Scan (neue Karten):** erst prüfen `python3 mtg_db.py scan scans/<Scan>.csv` → Verdachtsfälle und Sprache mit dem Nutzer klären → buchen `scan scans/<Scan>.csv --buchen [--verdacht-buchen] --moxfield out/<Name>_Moxfield.csv --beleg "<Kauf/Herkunft>" --journal data/buchungen.csv` → DB neu bauen → 06/07 neu → Protokoll „Import“; die Moxfield-CSV (nur Zugänge) bekommt der Nutzer zum Nachziehen. Nie eine ManaBox- oder Moxfield-Datei direkt an `buchungen.csv` anhängen oder als Basis laden.
   - **Neuscan eines vorhandenen Decks:** nicht buchen (Karten sind schon im Bestand) – nur mit dem Soll-Stand vergleichen (`vergleich decks/<deck>.txt scans/<Scan>.csv --art deck`), Abweichungen mit dem Nutzer klären, Soll-Stand korrigieren. Der Scan liefert die echten Drucke: Soll-Stand mit `snapshot … --deck <D>` aus einer mit dem Scan gebauten Datenbank schreiben, dann stehen `(SET) Nummer` im Soll-Stand; Protokoll „Abgleich“. Dabei die Liste „zusammen mit dem Deck erfasst“ aus `exemplare <deck>` klären.
2. **Deckänderung:** nach der **Freigabe** Entwurf mit eigenen Drucken (`drucke`), PDFs (`kartenbilder.py`, Abschnitt 4b; `08a`, Abschnitt 3) und Idee „freigegeben – Aufbau offen“ in `10`; erst nach der Meldung **„gebaut“** Entwurf als Soll-Stand speichern (`snapshot … --deck <D>`), Protokoll „Deck geändert“, Einfügeblock bzw. TXT für Moxfield an den Nutzer (`export <deck> --sets`).
3. **Moxfield-Export als Ausnahme** (Fehlerkorrektur oder ausdrückliche Überschreibung durch den Nutzer): `vergleich` gegen den berechneten Bestand bzw. `vergleich --snapshots decks` → Abweichungen klären → bei Überschreibung wird der Export die neue Basis, `buchungen.csv` wird geleert, Protokoll „Import“.
4. Nach jeder Buchung oder Deckänderung: `python3 mtg_db.py bestand-export bestand.csv --frei frei.csv --hinweis "<Buchungsstand>"` → `claude/06_…` und `claude/07_…` ersetzen; Deckregister aktualisieren. Vormerkungen sind bereits abgezogen (06: Spalten „vorgemerkt“, „Ideen“).
## 3. Befehle `mtg_db.py`

| Befehl | Zweck |
|---|---|
| `sammlung` | Bestand: Menge, Unikate, Wert, Farben, Typen, teuerste Karten |
| `decks` | alle Decks mit Deckname, Format, Farben, Kartenzahl, Herkunft, Status |
| `namen` | Namen nach Schema (alt → neu) mit Zeichenzahl (Moxfield max. 100) und Hinweisen |
| `besitz <deck>` | was fehlt (mit Preis), Konflikte mit anderen Decks, Standardländer mit Nachkauf |
| `mehrfach` | Karten, die mehrere Decks brauchen, vs. Exemplare (ohne Standardländer) |
| `laender [<deck>] [--plan "Plains=12, Swamp=10"]` | Standardländer: Bedarf vs. Besitz abzüglich anderer Decks → Nachkauf als Einfügeblock |
| `bracket <deck>` | Game Changer, MLD, Extra Turns + Commander Spellbook `estimate-bracket` |
| `export <deck> [--sets]` | Einfügeblock für Moxfield (Abschnitt 7) |
| `frei <Karte …>` | **Schnellabfrage „Habe ich X frei?“ (V1.6):** je Karte Besitz, in welchen Decks, vorgemerkt, Verkauf geplant, frei |
| `suche --tag removal --farben RWB --max-mv 2 --nur-frei` | Funktionssuche; freie Karten zuerst |
| `bestand-export <alle.csv> --frei <frei.csv> [--hinweis TEXT]` | Gesamtbestand + Liste der freien Karten |
| `scan <manabox.csv> [--buchen] [--verdacht-buchen] [--moxfield zugang.csv] [--beleg T] [--id B-nnn] [--datum D]` | **Standardweg für neue Karten.** Prüft einen ManaBox-Scan vor dem Buchen: (1) dieselbe Datei schon gebucht (Hash im Beleg) → Abbruch, (2) dieselbe Scan-Zeile schon gebucht (Druck + Foil + Sprache + ManaBox-Zeitstempel „Added“, steht im Journal unter „Last Modified“) → wird übersprungen, sodass auch ein Gesamtexport aus ManaBox nur das Neue bucht, (3) **Verdacht**: gleicher Druck + Foil schon im Bestand (zweites Exemplar oder Doppelscan?) → Liste, gebucht erst mit `--verdacht-buchen` nach Rückfrage, (4) Sprachverteilung (Kontrolle gegen falsch eingestellte Scan-Sprache). Bucht mit `--buchen` als `B-nnn Scan` ins Journal und schreibt mit `--moxfield` die Zugänge als Moxfield-CSV |
| `moxfield-export <out.csv> [--basis data/basis.csv] [--journal data/buchungen.csv]` | Gesamtbestand (Basis + Journal, Abgänge von der passenden Zeile abgezogen) als Moxfield-Sammlungs-CSV; Kontrolle gegen die Datenbank je Oracle-ID. Zum **Ersetzen** der Moxfield-Sammlung (dort vorher leeren – der Import fügt nur hinzu) |
| `manabox-zu-moxfield <scan.csv> [--sammlung out.csv] [--deck out.txt] [--sets] [--tausch 0] [--tags T]` | ManaBox-Scan → Moxfield-Bestands-CSV (Kopfzeile wie Moxfield-Export, Zustand Cardmarket → Moxfield-Skala, Sprache ausgeschrieben) und Moxfield-Deck-TXT (alphabetisch, `(SET) Nummer`, Commander nach Leerzeile am Ende). Hinweis: Moxfield übernimmt `Tradelist Count` beim Import nicht (Test 26.10.: alles landet auf der Tauschliste) |
| `snapshot <ordner> [--deck D] [--hinweis T] [--drucke]` | Soll-Stand aller (oder eines) Decks als Moxfield-Text mit Kopfzeilen und `// Commander`-Markierung → `claude/decks/<deckname>.txt`. Drucke (`(SET) Nummer`, `*F*`/`*E*`) stehen drin, wenn sie sicher bekannt sind (aus Deckliste oder Scan); `--drucke` schreibt auch die ermittelten |
| `exemplare <Karte\|Deck>` | jedes physische Exemplar mit Druck, Sprache, Finish und Ort (Deck, vorgemerkt, frei) samt Zuordnungsart: `druck` (aus Deckliste/Scan, sicher) · `zeitstempel` (gemeinsamer Erfassungszeitpunkt der Deckkarten, sehr wahrscheinlich) · `set` (Precon-Set) · `geschätzt`. Beim Deck zusätzlich: freie Karten, die **zusammen mit dem Deck erfasst** wurden (liegen vielleicht physisch beim Deck – beim Neuscan klären) |
| `drucke <entwurf.txt> [--deck D] [--idee I-nnn] --out <entwurf_drucke.txt>` | Entwurf mit eigenen Drucken: Karten aus Deck D behalten dessen Exemplare, neue Karten bekommen freie Exemplare (Vormerkungen der Idee zählen als frei), Rest ohne Druck = Kauf. Grundlage für Deck-PDF (eigene Drucke im Bild) und Soll-Stand |
| `vergleich <alt> <neu> [--titel T] [--art deck\|sammlung] [--csv diff.csv]` | zwei Deckdateien oder zwei Bestandsdateien (Moxfield/ManaBox-CSV oder Bestandsliste 06) vergleichen → fertiger Protokolleintrag |
| `vergleich --snapshots <ordner>` | alle Decks der Datenbank gegen den Soll-Stand (Zuordnung über Deckname, sonst Commander): unverändert / abweichend (mit Eintrag) / neue Decks ohne Soll-Stand / Soll-Stand ohne Deck |
| `sql "<SELECT …>"` | freie Abfrage |

`<deck>` = Deck-ID, Deckname, Teil des Namens oder Commander.

**Exemplar-Zuordnung (Tabelle `exemplare`, seit 27.10.2026):** Der Bau löst Basis + Journal in einzelne Exemplare auf (Abgänge von der passenden Zeile abgezogen) und verteilt sie: zuerst die Drucke, die in einer Deckliste stehen, dann je Deck den Erfassungszeitpunkt (Moxfield „Last Modified“ – die Karten eines Decks wurden gemeinsam erfasst), dann das Precon-Set, sonst geschätzt; danach die Vormerkungen; der Rest ist frei. Die Zählung je Karte entspricht immer `v_karten` (Besitz − Decks − Vormerkungen). `export --sets` nimmt die Drucke aus dieser Zuordnung.

## 4. Befehle `deckbau.py` (Verfahren: `08_Deckbau-Verfahren`)

Ausgabe **kurz** als Standard (Bilanz, Paare, Sperren, Oracle-Text); lange Listen mit `--voll`, alles Weitere steht in der CSV daneben. Regeln für Rollen, Wert, Bezug, Kompromiss-Stufen und Klassen: `bewertung.py` (Abschnitt 4g).

| Befehl | Stufe | Zweck |
|---|---|---|
| `commander-suche --thema <slug> [--farben RWB]` / `--farben GW --nur-besitz` | A | Commander finden (EDHREC-Themenseite bzw. eigener Bestand); bei vorgegebenem Commander: trägt ein eigener das Thema besser? |
| `passung <deck> [--thema <archetyp\|slug>] [--bracket 3] [--kandidaten 10] [--kauf N] [--max-illegal 15]` | A | **Passungs-Check** (`08`, Abschnitt 2b): was das Deck trägt (Kernpakete gegen die Mediane), was der Commander laut EDHREC spielt, Bezug der Spielkarten (Ø Wert = EDHREC oder Oracle-Bezug, Liste ohne Bezug), alternative Commander aus Deck, Sammlung und Kauf, Befund und Optionen A–D. Der Nutzer entscheidet |
| `commander "<Name>" [--bracket 3]` | A | Steckbrief: Oracle-Text, Besitz, **Profil aus dem Oracle-Text** (Themen, Kreaturtypen), EDHREC-Themen mit Deckzahlen, Top-/High-Lift-Karten, Combos |
| `synergie <Commander\|Deck> [--thema <archetyp>] [--top 30] [--out datei.csv]` | A, B | **Freie Karten mit Bezug zum Commander-Text (V1.6):** Profil des Commanders (welche Ressourcen er erzeugt und nutzt, welche Typen er nennt) gegen Text, Typen und Tags jeder freien Karte → Rangliste mit Bezug 0–1, „warum“, gefülltem Kernpaket, Rollen, EDHREC als Zusatz; Liste „starker Bezug, aber nicht auf EDHREC“; beim Deck zusätzlich die Deckkarten mit dem geringsten Wert |
| `kandidaten "<Name>" --weg 1\|2 [--bracket 3] [--thema <slug>] [--budget]` | B | Kartenpool (EDHREC + Sammlung) mit Rollen, Bezug, Wert, Besitz, Preis → CSV; Rollenübersicht gegen den Richtwert (mit `--thema` der Archetyp); Weg 1: Machbarkeitsampel (Plan-Karten = Oracle-Bezug ≥ 0,33 oder EDHREC-Synergie ≥ 10 %); Weg 2: Kaufkandidaten mit Wirkung und Klasse |
| `alternativen "<Karte>" [--farben RWB]` | B | günstigere Karten mit gleicher Rolle, Sammlung zuerst |
| `upgrade <deck> [--stufe 0\|1] [--max-preis 10] [--thema <archetyp\|slug>] [--paare 15] [--abstand 0.08] [--voll] [--idee I-nnn]` | B | **Upgrade-Modus (V1.6):** Rollen gegen den Richtwert des Ziel-Archetyps (vor Template), Kernpakete gegen den Median, Tauschpaare in drei Schritten – (1) Rollen unter dem Minimum aus freien Karten füllen (Rückfall vor Kauf, je Karte die **Kompromiss-Stufe** und die beste Kauf-Alternative mit Satz, was der Aufpreis bringt), (2) Kernpakete unter dem Median, (3) Wert verbessern. **Raus-Sperren:** keine Karte, deren Kernpaket dann unter den Median fällt; keine Karte mit Commander-Bezug ≥ 0,5 (außer für eine Karte mit gleichem Bezug und gleichem Grund; bei reiner Wertverbesserung nur für eine laut EDHREC klar stärkere); keine Karte, deren Rolle unter das Minimum (in Schritt 2–3 unter das Ziel) fällt oder schlechter ersetzt wird; keine Interaktion, wenn ein Ziel (Kreatur, Artefakt, Verzauberung, Friedhof) unter die Untergrenze fällt; Länder nur gegen Länder. Symmetrische Wipes im Go-wide-Deck werden nicht vorgeschlagen. Käufe mit Wirkung, Klasse A–D und € je Wertpunkt. Ausgabe: Paare mit „warum raus/rein“, Oracle-Text beider Seiten, `<out>_paare.txt` für `fazit`, CSV mit allen Deckkarten und Kandidaten (Wert, Bezug, Gründe, Sperre). Startpunkt – Claude prüft jedes Paar |
| `pruefen <entwurf.txt> [--bracket 3] [--archetyp A] [--ersetzt <deck>] [--idee I-nnn] [--combos-fehlend]` | B | Qualitätskontrolle: Kartenzahl, Singleton, Farbidentität, Banlist · Rollen gegen den Richtwert (Spalte „Richtwert-Quelle“: Archetyp oder Template) · Instant-Interaktion · Interaktion nach Ziel · nicht mitgezählte Karten mit Grund · Kurve, Farbquellen · Bracket-Zeile, Combos · Kaufliste, Standardländer, Warnungen |
| `abnahme <deck\|entwurf> [--basis <Soll-Stand>] [--archetyp A] [--bracket 3] [--n 5000]` | B, C | **Bracket-3-Abnahme (V1.6, `08`, Abschnitt 8a):** acht Prüfpunkte mit ✓/✗/offen und Urteil; Stärke-Index (Rollen, Kernpakete, Ø Wert, Ø Bezug, Simulation) gegen die Basis |
| `gegenlauf <Deck\|Entwurf> --ziel "…" [--stufe 0\|1 --max-preis X --summe Y] [--game-changer "…"] [--verkauf hinweis\|aus] [--neubau] [--idee I-nnn]` | A→B | **Gegenlauf (V1.7, `08a`, Abschnitt 5):** Ausgangsdeck, Liste freier Karten und je Konkurrent (Commander Deck Skills, MTG Master) einen Auftrag anlegen; Skill-Quellen auf den festen Commit holen und prüfen; Ressourcenhinweis |
| `gegentest <Projekt> <K1> [<K2> …] [--basis <Soll-Stand>] [--namen "Projekt,K1,K2"]` | B | **Vergleich (V1.7):** zwei oder mehr Listen mit denselben Maßstäben (Abnahme je Punkt, Stärke-Index, Rollen, Simulation, Kosten für den eigenen Bestand, Überschneidung, stärkste Karten je Liste); mit `--basis` die Abwägungsgrundlage – welche Tausche mehrere Läufe unabhängig gewählt haben |
| `oracle <Karte …>` / `oracle --alt <Soll-Stand> --neu <Entwurf> [--rulings]` | B, C | Oracle-Text mit Kosten, Typ, Stärke, Game-Changer-Kennzeichen – **Pflicht vor jedem Vorschlag** |
| `erklaerung <entwurf.txt> [--ersetzt <deck>] [--idee I-nnn]` | D | Datenbasis je Karte für die Kartenerklärungen (Rollen, Bezug mit Gründen, EDHREC, Combo-Teil, Status, Oracle-Text) |
| `fazit --neu <entwurf_drucke.txt> [--alt <Deck>] [--paare <datei>] [--thema <archetyp>] [--stufe "Stufe 0"] [--deckname D] [--bracket 3] [--idee I-nnn] --out fazit.md` | D | **Fazit-Entwurf aus Daten** für `kartenbilder.py lieferung` (`08a`, Abschnitt 3): Kopf, Kacheln, Bracket-Zeile, „Die Änderungen“ (Status mit Kompromiss-Stufe), Kennzahlen vorher/nachher mit Kernpaketen, **Bracket-3-Abnahme**, Kartenerklärungen, Vorgehen, Moxfield-Anhang; Platzhalter ‹…› für Claudes Texte |
| `verkauf [--min-preis 1] [--bracket 3] [--out out/verkauf.txt]` | C | **Verkaufsprüfung:** freie Exemplare ab Mindestpreis gegen alle Decks: **Behalten** = Upgrade-Kandidat (EDHREC-Wert ≥ 0,10 oder Oracle-Bezug ≥ 0,5; Karten, die den Plan zerstören, nicht) · **Kat. 2** = Kompromiss für eine Rolle unter Minimum, Game Changer, Playset-Ergänzung, ⚑ · **Kat. 1** = alles andere; Verkaufsliste für `kartenbilder.py verkauf` |

**Kennzahlen (einheitlich in allen Werkzeugen und PDFs):** Rollen zählen über die 99 **ohne** Commander. Ø MV und Kurve über alle Nichtländer **inklusive** Commander. EDHREC-Inclusion und -Synergie kommen von der Commander-Seite **mit Bracket-Filter, ohne Thema** (`commanders/<slug>/<bracket>`); Themenseiten nur für die Kandidatensuche und dann als „Thema“ gekennzeichnet. **Wert** einer Karte für einen Commander = max(EDHREC-Wert, Schätzung aus dem Oracle-Bezug); „≈“ = geschätzt. Eine Karte, die nicht auf der EDHREC-Seite steht, ist **unbekannt, nicht schwach**.

**Rollen** (V1.6, eine Regel für alle Werkzeuge – `bewertung.rollen_detail`): Ramp (`ramp`, `mana-rock`, `mana-dork`, `land-ramp`, zusätzliche Landdrops) **ohne** Removal, das dem Gegner ein Land gibt (Path to Exile), symmetrischen Ramp (Collective Voyage, Gruppen-Hug), Rituale, Einmaleffekte ohne Land aufs Feld und Mana nur für einen Kreaturtyp, den das Deck nicht spielt (Flamebraider) · Kartenvorteil (`card-advantage`, `draw`) · gezielte Interaktion (`spot-removal`, `counterspell`, Removal ohne Wipe – nicht, wenn sie nur Spieler oder Planeswalker trifft) · Massen-Interaktion (`sweeper`; im Go-wide-Deck zählen symmetrische Kreaturen-Wipes nicht) · Schutz (`protects-*`, `gives-indestructible/hexproof/protection`) · Tutor (nicht, wenn nur Länder gesucht werden – das ist Ramp) · Rekursion; ohne Rolle = „Plan/Synergie“. `pruefen` zeigt, welche Karte warum nicht mitzählt. **Richtwerte:** Minimum = Median des Ziel-Archetyps (abgerundet), Ziel = Minimum + 2 (Länder + 3); ohne Archetyp das Template aus `01`. Ziel-Archetyp: Vorgabe (`--thema`/`--archetyp`) → Strategie im Deckregister → am besten abgedeckt.

## 4a. Befehle `archetypen.py` (Wissen: `11_Archetypen-Playbook`, Ergebnis: `12_Sammlungsprofil`, `12a_Deck-Raster`)

13 Archetypen (Schlüssel: `tokens`, `aristokraten`, `counters`, `artefakte`, `spellslinger`, `reanimator`, `lifegain`, `landfall`, `voltron`, `enchantress`, `blink`, `kindred`, `mill`), je aus Paketen (Kernpakete zählen für die Ampel). Pakete werden über Scryfall-Funktionstags (direkte und geerbte Tags aus `bulk/oracle_tags.jsonl.gz`) und Oracle-Text-Muster erkannt – Näherung, Einzelfälle am Oracle-Text prüfen. Mit `mtg.sqlite` im Ordner zählen Bestand und freie Karten aus der Datenbank; ohne Datenbank `--frei claude/07_Sammlung-Frei.csv` und `--decks claude/decks/*.txt` angeben (Scryfall-Bulk `oracle_cards` wird dann geladen).

| Befehl | Zweck |
|---|---|
| `profil [--frei 07.csv] [--decks decks/*.txt] [--einschaetzung E.md] [--out 12_Sammlungsprofil.md] [--raster-out 12a_Deck-Raster.md] [--hinweis T] [--ohne-commander]` | Sammlungsprofil: Kernpakete je Archetyp in den freien Karten, beste Zwei-/Dreifarben-Kombination mit Ampel (GRÜN ≥ 80 %, GELB ≥ 50 % des Medians), Anteil spielstarker Karten (EDHREC-Rang ≤ 5.000), Kreaturtypen, Grundrollen, Status der Schlüsselkarten, Commander-Decks im Archetyp-Raster (mit `--decks`), freie Commander mit EDHREC-Themen. Die Einschätzung schreibt Claude je Lauf neu (`--einschaetzung`) |
| `karten <archetyp> [--paket P] [--farben RWB] [--frei 07.csv] [--alle] [--ohne-deck <deckdatei>]` | freie Karten (mit `--alle`: alle Commander-legalen mit Preis) je Paket – für Weg 1 und Upgrade-Stufe 0; `--ohne-deck` lässt Karten weg, die schon im Deck stecken (Singleton) |
| `deck <deckdatei> [--archetyp A]` | Rollen (99 ohne Commander, gleiche Regeln wie `pruefen`; Hinweis auf Wipes, die den Go-wide-Plan zerstören) und Pakete (mit Commander) eines Decks gegen die Mediane der EDHREC-Durchschnittsdecks; ohne `--archetyp` die 3 am besten abgedeckten Archetypen; ⚠ = Kernpaket unter dem kleinsten Wert der Datenbasis |
| `daten [--top 6] [--bracket 3] [--out archetypen_daten.json]` | Richtwerte neu erheben: Top-Commander je EDHREC-Thema → Durchschnittsdecks mit Bracket- und Themenfilter → Median/Spanne je Paket und Rolle, Schlüsselkarten (≈ 1 Minute, rund 120 EDHREC-Abrufe); danach Tabellen in `11` (Abschnitte 3.1, 4, 5) nachziehen; seit V1.6 mit den Rollenregeln aus `bewertung.py` |

## 4b. Befehle `kartenbilder.py` (Fazit-PDF, Tauschübersicht und Deck-PDF; Ablauf: `08a`, Abschnitt 3)

Bilder von Scryfall (englische Druckversion; Edition + Nummer aus Tauschliste, Entwurf oder Bestand, sonst bevorzugtes Set bzw. Scryfall-Standarddruck). Kartendaten über `api.scryfall.com/cards/collection` (je 75 Karten, Split- und Doppelkarten über den Namen der Vorderseite), Bilder von `cards.scryfall.io` (Cache `cache/kartenbilder/`). Ohne Bildserver zeichnet das Skript Platzhalter mit Name, Typ, Manakosten und Druck. Schriften: Cinzel und EB Garamond (SIL Open Font License) werden beim ersten Lauf von GitHub (`raw.githubusercontent.com/google/fonts`) geholt und als feste Schnitte in `fonts/` abgelegt (braucht `fontTools`); ohne Netz DejaVu Serif. **Netzwerk:** `api.scryfall.com` und `cards.scryfall.io` müssen in den erlaubten Domains stehen (Nutzer, claude.ai → Settings → Capabilities; `cards.scryfall.io` freigegeben am 27.10.2026).

| Befehl | Zweck |
|---|---|
| `lieferung <fazit.md> --neu <entwurf_drucke.txt> [--alt <Soll-Stand>] [--idee I-nnn] --out out/<deckname> [--stempel T] [--druck] [--entwurf]` | **Standard nach der Freigabe (seit V1.2):** alles in einem Lauf – `<name>_fazit.pdf`, `<name>_tausch.pdf` + PNG je Seite (nur mit `--alt`), `<name>_deck.pdf`, `<name>_moxfield.txt` (Einfügeblock aus dem Fazit-Anhang). Kopfdaten für Deck-PDF und Tausch aus dem Kopf des Fazits (`deckname`, `voll`, `bracket_zeile`, `beschreibung`, `themen`, `status`, `wert`, `set`); Kartendaten einmal geholt, Bilder parallel (Test: 102 Bilder, 6 s); Handy-Größe als Standard, `--druck` = volle Auflösung. Bricht ab, solange Platzhalter ‹…› offen sind (`--entwurf` = Vorschau) |
| `verkauf <verkaufsliste.txt> --out out/<name> [--mobil] [--stempel T] [--ohne-png]` | **Verkaufs-PDF (seit V1.5):** aus der Liste von `deckbau.py verkauf` (Zeile `K1 1 Name (SET) Nr \| 4,14 € \| DE \| Hinweis`): Kopf mit Anzahl und Summe je Kategorie, Abschnitte „Kat. 1 – ohne Bedenken verkaufen“ und „Kat. 2 – Verkauf möglich, mit Hinweis“ mit Anzahl und Summe, je Karte Box-Etikett, Druck, Sprache, Preis rechtsbündig und bei Kat. 2 der Hinweis (bis 2 Zeilen); Ordnung je Abschnitt = Box-Ablage; PNG je Seite |
| `tausch <liste.txt> --out out/<name> [--png]` | Tauschübersicht aus einer Tauschliste (`+n Name (SET) Nr \| Quelle \| Hinweis`, `-n …` = geht aus dem Deck; Quellen: `Sammlung`, `Deck: <Name>`, `Kauf`, `Standardland`; Kopfzeilen `# titel:`, `# deck:`, `# datum:`) |
| `tausch --alt <Soll-Stand> --neu <Entwurf> --frei 07.csv --bestand 06.csv [--vormerkungen V --idee I-nnn] [--haves Basis.csv buchungen.csv] --deckname D [--titel T] [--deck "voller Name"] --out out/<name> [--png]` | Vergleichsmodus: erzeugt die Tauschliste selbst (`out/<name>.txt`) – je neuer Karte frei → Sammlung, Standardland → frei/kaufen, in anderem Deck → `Deck: <Name>` (Ersatz nötig), sonst Kauf; entfernte Karten → zurück in die Box. Druck und Sprache des eigenen Exemplars aus `--haves` („besitzt: Deutsch“). Bei neuen Decks keine Tauschübersicht (nur Deck-PDF) |
| `tausch --db mtg.sqlite --alt <Soll-Stand> --neu <Entwurf> [--idee I-nnn] --deckname D [--titel T] [--deck "voller Name"] --out out/<name> [--mobil] [--stempel T]` | **Standard seit 27.10.2026:** Tauschliste aus der Exemplar-Zuordnung – je neuer Karte ein freies Exemplar mit Druck und Sprache (der Druck aus dem Entwurf hat Vorrang; weitere freie Drucke als „auch frei“), sonst Exemplar aus anderem Deck (Ersatz nötig), sonst Kauf; entfernte Karten mit dem Druck des Deck-Exemplars („Druck geschätzt“, wenn die Zuordnung unsicher ist); Standardländer frei/kaufen. PNG kommt immer mit (`--ohne-png` schaltet ab) |
| `deck <Entwurf oder Soll-Stand> [--voll "Format \| Deckname \| Farbname (Kürzel) \| Strategie \| Herkunft"] [--stand] [--set tdc] [--titelkarte K] [--name] [--bracket] [--beschreibung] [--themen] [--status] [--wert] [--hinweis] --out out/<name> [--png]` | Deck-PDF: Deckblatt (Kopfband mit Deckname, Format, Farben, Strategie, Herkunft aus `--voll` bzw. der Soll-Stand-Kopfzeile; Farbsymbole in der Reihenfolge des Kürzels; Commander groß mit Oracle-Text – ohne Commander (Konstruiert) eine Titelkarte: `--titelkarte` oder die häufigste Nichtland-Karte; Kurzdaten mit Bracket-Zeile und Game Changer live laut Scryfall bzw. bei Konstruiert „Format“ (Text aus `--bracket`), Karten/Länder, Ø MV ohne Länder, Deckwert, Themen, Status; Moxfield-Beschreibung; Manakurve; Pips gegen Länderquellen; Kartentypen) + alle Karten nach Kategorien (Kreaturen, Planeswalker, Schlachten, Spontanzauber, Hexereien, Artefakte, Verzauberungen, Länder, Standardländer; je nach MV, mit MV und Preis). `--wert` = Deckwert aus `mtg_db.py` (günstigste Drucke); ohne `--wert` Wert der abgebildeten Drucke |

| `bericht <fazit.md> --out out/<name> [--stempel T]` | **Fazit-PDF** einzeln, im selben Design aus Markdown (Kopf mit Titel/Ober-/Unterzeile/Farben, Kacheln, nummerierte Abschnitte, Tabellen mit Gruppenzeilen, Kästen, Listen, Einfügeblock zwei- bzw. dreispaltig). Vorbefüllter Entwurf: `deckbau.py fazit`; leere Vorlage: `kartenbilder.py vorlage > fazit.md` |

**Vorlagen:** Das Layout aller PDFs ist fest im Werkzeug hinterlegt (Farben, Schriften, Kopf, Kacheln, Tabellen, Kästen, Kartenraster, Box-Etiketten); der Inhalt des Fazits kommt aus `deckbau.py fazit` (Daten) plus Claudes Texte. `tausch`, `deck` und `bericht` einzeln nur für Sonderfälle (Konstruiert-Decks, korrigierte Tauschliste, Deck-PDF aus dem Soll-Stand).

Für `tausch`, `deck`, `bericht`: `--mobil` = kleinere Bilder (Deck-PDF ≈ 2 MB statt ≈ 10 MB, am Bildschirm und im Druck gut lesbar) – Standard für die Lieferung; `--stempel "TESTLAUF – nicht gebucht"` = roter Stempel auf Seite 1 (Testlauf, `13`, Abschnitt 5.1). Lange Titel und Namen werden verkleinert statt abgeschnitten. Zeichen, die Cinzel/EB Garamond nicht haben (①, ⚑, ✓ …), kommen seit V1.5 automatisch aus DejaVu Sans (`laeufe()`, `schreibe()`) – vorher erschienen sie als Kästchen. Deck-PDF: Drucke aus dem Entwurf (`mtg_db.py drucke`) → Bilder der eigenen Exemplare; Ø MV = Nichtländer inkl. Commander.

Ordnung der Tauschübersicht = Ablage des Nutzers (Abschnitt 0): Farbe Weiß → Blau → Schwarz → Rot → Grün → Farblos → Länder → Standardländer, darin Kreaturen → Planeswalker → Schlachten → Spontanzauber → Hexereien → Artefakte → Verzauberungen; jede Karte trägt ein Box-Etikett mit Farbsymbol. Layout: A4, Pergament-Ton mit Goldrahmen; Tauschübersicht 4 Karten je Zeile (12 je Seite), Deck-PDF 5 je Zeile (20 je Seite). `--png` liefert PNG-Seiten fürs Handy (Deck: nur das Deckblatt).

## 4c. Befehle `paket.py` (Arbeitspakete, `05a`)

| Befehl | Zweck |
|---|---|
| `auspacken <paket.txt …> [--ziel /home/claude/mtg] [--pin <PIN>]` | Prüfsummen prüfen; Werkzeuge in den Stamm, Bestand nach `data/`, Soll-Stände nach `decks/`, Ideen nach `ideen/`, 04/09/10 nach `projekt/`; schreibt `paket_manifest.json` (lokal ↔ Projektpfad) und gibt den Bau-Befehl aus. Ein Gast-Archiv nur mit richtiger PIN |
| `geaendert [--ziel …]` | geänderte und neue Dateien seit dem Auspacken mit Projektpfad → genau diese mit `project_write` (`local_path`) zurückschreiben |
| `packen --art werkzeuge\|daten (--arbeit <ordner> \| --quelle <projektordner>) --out <datei> [--nutzer]` | Paket neu bauen (aus dem Arbeitsordner über das Manifest; neue Soll-Stände und Entwürfe kommen automatisch mit); `--nutzer` = ohne `weitergabe.py` |
| `packen --art gast --arbeit <ordner> --name "<Name>" --pin-hash <Hash> --out <slug>.txt` | Gast-Archiv: `data/*.csv`, `decks/*.txt`, `ideen/*`, `deck_namen.json`, `gast_profil.json`; Kopf mit Name und PIN-Hash |
| `holen --art <art> --out <datei>` | das zuletzt mit `project_read` gelesene vollständige Paket dieser Art aus dem Sitzungsprotokoll als Datei (z. B. Gast-Archiv vor der PIN-Prüfung); ohne Sitzungsprotokoll den Pfad nehmen, unter dem `project_read` die Datei abgelegt hat |
| `liste <paket.txt>` | Kopf und Inhalt anzeigen |

**Sperren je Rolle** (aus `SITZUNG.json`, gesetzt mit `zugang.py sitzung`): Gast – kein Datenpaket auspacken oder packen, kein `geaendert`, keine Werkzeuge packen; ein Arbeitsbereich mit `gast_profil.json` gilt ebenfalls als Gast-Sitzung · User – keine Werkzeuge packen. Die Sperren schützen vor Versehen; maßgeblich sind die Regeln in `13`.

Format: erste Zeile `MTG-PAKET <art> v1 · Stand … · sha256 …`, Inhaltsliste, dann Base64 (tar.xz) zwischen `=====BEGIN=====` und `=====END=====`.

## 4d. Befehle `zugang.py` (Rollen und Anmeldung, Regeln: `13_Betriebsmodus-und-Weitergabe`)

Nur Hashes (PBKDF2-SHA256, 200.000 Runden, Salz), nie Klartext – auch nicht im GitHub-Repo. Zugangsdatei `zugang.json` (Kopie: `zugang.json` im Projektstamm): `admin` (Hash), `user_freigeschaltet`, `kopie`.

| Befehl | Zweck |
|---|---|
| `setzen --datei <zugang.json> --passwort '<P>'` | Admin-Passwort setzen oder ändern (nur angemeldeter Admin; danach Datei zurückschreiben) |
| `pruefen --datei <zugang.json> --passwort '<P>'` | Anmeldung prüfen (OK/FALSCH, nach 3 Fehlversuchen gesperrt) – im Zustand Start gilt der feste Befehl aus `13`, Abschnitt 2, der ohne Werkzeuge läuft |
| `freischalten --datei <zugang.json> --user ja\|nein` | User-Zustand in der Weitergabe-Kopie freigeben (Admin vor Ort, `13`, Abschnitt 8, E7) |
| `status --datei <zugang.json>` | Stand ohne Geheimnisse |
| `pin-hash <PIN>` / `pin-pruefen <archiv.txt> --pin <PIN>` | Gast-PIN (4 Ziffern) hashen bzw. gegen den Kopf eines Gast-Archivs prüfen (3 Fehlversuche) |
| `sitzung start\|admin\|user\|gast [--name N]` | Rolle der Sitzung vermerken (`SITZUNG.json`); ein Rollenwechsel im selben Chat wird abgelehnt |
| `slug "<Name>"` | Dateiname des Gast-Archivs (`claude/gaeste/<slug>.txt`; Umlaute als ae/oe/ue) |
| `gast-profil --name N [--quelle Q] [--quittiert DECK] [--notiz T]` | `gast_profil.json` im Arbeitsbereich anlegen bzw. ergänzen (geht mit ins Archiv) |

## 4e. `simulation.py` – Konsistenz-Simulation (V1.6)

`python3 simulation.py <deck|entwurf> [--n 10000] [--seed 1] [--zuege N] [--json]` – spielt die ersten Züge eines Commander-Decks n-mal durch (≈ 1 s je 10.000 Spiele): Mulligan nach London (CR 103.5) mit freiem ersten Mulligan im Mehrspieler-Spiel (103.5c), Kartenziehen im ersten Zug (103.8c), Landdrop je Zug (ungetappte Länder zuerst), Ramp (Steine, Dorks, Landsuche) sobald bezahlbar, Commander sobald bezahlbar – mit Farben. Behalten: 3–5 Länder, 2 Länder mit Ramp bis MV 2; nach zwei Mulligans 2–5, nach drei jede Hand.

| Kennzahl | vorläufige Schwelle (Einschätzung, 29.10.2026) |
|---|---|
| zwei oder mehr Mulligans | ≤ 15 % |
| Landdrops in Zug 1–4 | ≥ 80 % |
| weniger als 3 Länder in Zug 3 | ≤ 8 % |
| Commander spätestens einen Zug nach seinem MV | ≥ 70 % |
| genug Mana, aber falsche Farben für den Commander | ≤ 8 % |

Die Schwellen sind im Admin-Projekt aus drei Commander-Decks gemessen und nach weiteren Abnahmen nachzuschärfen. Grenzen: Kartenziehen, Tutoren und Interaktion der Gegner werden nicht simuliert.

## 4f. `protokoll.py` – 04/09/10 lesen und pflegen (V1.6)

Die Listen kommen mit dem Datenpaket nach `projekt/`. Claude liest nur, was die Aufgabe braucht, und schreibt Einträge mit dem Werkzeug; danach `paket.py geaendert` → `project_write` → Datenpaket neu (`05a`, Abschnitt 6).

| Befehl | Zweck |
|---|---|
| `zeigen [--deck D] [--typ T] [--suche S] [--letzte N]` | Einträge aus `09` (neueste zuerst), gefiltert; ohne Filter die letzten 5 |
| `neu --typ <Typ> --thema <Deck/Thema> --zeile "…" [--zeile …]` | Eintrag oben einfügen (Typen wie in `09`; „Werkzeug“ gehört nach `09a`, nur Admin) |
| `offen [--deck D]` | offene Ideen, geplante Verkäufe, Kaufliste, Vormerkungen, „In Moxfield nachziehen“ aus `10` |
| `idee-neu --deck D --inhalt T --status S [--details P]` · `idee-status <ID> <Status>` · `idee-entfernen <ID>` | Ideen und Verkäufe in `10` (Vormerkungen in `vormerkungen.csv` getrennt pflegen) |
| `nachziehen --was T --aufgabe T` · `nachziehen-erledigt <Teiltext>` | Zeilen „In Moxfield nachziehen / Wartung“ |
| `register [--deck D]` | Zeile(n) des Deckregisters |
| `aufwand [--seit JJJJ-MM-TT] [--eintragen "<Was>"] [--willkommen projektanweisungen.md]` | **V1.7, nur Admin:** Aufwand der Claude-Code-Sitzung aus den Transkripten (Zeitspanne, aktive Zeit, Token, API-Gegenwert in € zu Listenpreisen); `--eintragen` schreibt eine Zeile in `14_Projekt-Aufwand.md` (vorher mit `project_read` nach `projekt/` holen), `--willkommen` setzt den Vermerk 🕒 in der Willkommensnachricht neu – danach Projektanweisungen beim Admin aktualisieren lassen |

## 4g. `bewertung.py` – Bewertungsregeln (V1.6, Bibliothek)

Eine Quelle für `deckbau.py`, `archetypen.py` und `simulation.py`; ohne Datenbank testbar.

- **Rollen mit Qualitätsregeln** – Abschnitt 4 („Rollen“).
- **Wert:** `wert_edhrec` = Inclusion + 1,5 × Synergie (nicht gelistet = unbekannt) · `gesamtwert` = max(EDHREC-Wert, 0,6 × Bezug + Rang-Bonus).
- **Synergie:** `commander_profil` liest aus dem Commander-Text, welche Ressourcen er erzeugt und nutzt (Tokens, Opfern/Tod, Angriff, Kampfschaden, Counter, Leben, Länder, Artefakte, Verzauberungen, Zauber, Friedhof, ETB, Kreaturen, Ausrüstung, Legendäre, Treasure, Fliegen) und welche Kreaturtypen er nennt; EDHREC-Themen nur als Zusatz (Gewicht 0,4). `karte_bezug` → Punkte und Gründe; Bezug 0–1 (1,5 Punkte = 1,0). Ab 0,5 greift die Raus-Sperre.
- **Archetyp-Regeln:** `richtwerte` (Archetyp vor Template), `zerstoert_plan` (symmetrische Kreaturen-Wipes in Tokens, Aristokraten, Kindred, Counter, Voltron, Blink; Wipes, die Tokens verschonen, nicht im Token-Deck).
- **Kompromiss-Stufen** (ersetzen „Notlösung“): `funktionsgrad` je Rolle (z. B. Ramp: MV ≤ 2 = 1,0, einmaliger Effekt − 0,3; gezielte Interaktion: breites Ziel, Instant-Tempo, Bedingungen), Erfüllung q = ½ Funktionsgrad + ½ (Wert frei / Wert der besten Kauf-Alternative): **gleichwertig** (q ≥ 0,8) · **funktional, aber langsamer** (≥ 0,5) · **nur Platzhalter**. Dazu `aufpreis_satz`: was der Kauf bringt (Wert, MV, Instant).
- **Klassen A–D** (`01`, Abschnitt 6): Wirkung 1–5 aus dem Wert (+1, wenn die Karte eine Rolle unter dem Minimum füllt) · D = bracket-schädlich oder Wirkung ≤ 2 bei ≥ 5 € · A = Wirkung ≥ 4 ohne 80-%-Ersatz · B = ≤ 2 € je Wirkungspunkt über 1 · sonst C. Einschätzung aus Daten – Claude prüft am Oracle-Text.

## 5. Unterstützte Importformate

- **Bestand:** Basis im Moxfield-CSV-Format (`basis.csv`, ursprünglich `moxfield_haves_<Datum>.csv`) + `buchungen.csv` (gleiches Format mit Zusatzspalten `Buchung`, `Datum`, `Beleg`; negative `Count` = Abgang). ManaBox-CSV wird technisch gelesen, wird aber nie direkt als Bestand geladen (→ `manabox-zu-moxfield`, dann Zugang buchen).
- **ManaBox-Scan (echte Datei geprüft 26.10.2026):** `Name, Set code, Set name, Collector number, Foil, Rarity, Quantity, ManaBox ID, Scryfall ID, Purchase price, Misprint, Altered, Signed, Condition, Language, Proxy, Purchase price currency, Added`. Export eines einzelnen Binders/einer Liste hat **keine** Binder-Spalten → ganze Datei = ein Deck. Zuordnung per Scryfall-ID: 100 %. Achtung: ManaBox wählt beim Scannen eine Druckversion mit passendem Bild – Set/Nummer können vom tatsächlichen Druck abweichen (Name und Oracle-ID stimmen).
- **Decks als Text:** Moxfield-Export (Commander nach Leerzeile am Ende; Dateiname = Slug des Decknamens + Zeitstempel: klein, Sonderzeichen und Umlaute/ß entfernt, ` | ` → `--`, z. B. `commander--mardu-surge--mardu-rwb--aggro-tokens--precon-tdc-<Zeit>.txt`) und ManaBox/MTGO/Arena-Varianten: `1x Name`, `(SET) 123` oder `[SET] 123`, `*F*`, `SB:`-Zeilen, Überschriften wie `Commander (1)`, `Mainboard (99)`, `Sideboard`, `Maybeboard`, `// Commander`; `Tokens` werden ignoriert. Nur der **letzte** unbeschriftete Block kann Commander oder Sideboard sein.
- **Decks als CSV** (z. B. ManaBox-Scan eines Decks) über `--decks`; mehrere Decks in einer Scan-Datei mit Binder-Spalten über `--scan-decks`.
- **Commander ohne Markierung:** `deck_namen.json` (`"deck:<Name>": {"commander": "…"}`) > Erkennung (legendäre Kreatur mit voller Farbidentität des Decks; bei mehreren entscheidet der Deckname) > Hinweis.

## 6. Einheitliches Namensschema (Stand 26.10.2026)

`<Format> | <Deckname> | <Farbname (Kürzel)> | <Strategie> | <Herkunft>[ | In Arbeit]` – **höchstens 100 Zeichen** (Grenze für Decknamen in Moxfield)

| Feld | Regel |
|---|---|
| Format | Commander, wenn ein Commander erkannt ist oder das Deck ein 100-Karten-Singleton ist. Sonst das Format aus dem bisherigen Namen, falls alle Karten darin legal sind; andernfalls das engste legale Format (Standard → Pioneer → Modern → Legacy → Vintage) + Hinweis |
| **Deckname** | jedes Deck hat einen eigenen Namen: Precon bzw. Precon-Umbau → **Name von Wizards** (z. B. „Jeskai Striker“, „Temur Roar“); vom Händler gekauftes Deck ohne Wizards-Namen → Name des Produkts; **eigene Decks → eigener Name**. Pflege in `deck_namen.json` (`precon` bzw. `name`); fehlt er, meldet das Tool „Deckname fehlt“ |
| Farbname (Kürzel) | Gilde/Shard/Wedge + Farbkürzel (WUBRG) in Manakosten-Reihenfolge, z. B. „Selesnya (GW)“, „Golgari (BG)“, „Mardu (RWB)“; „Mono-Rot“, „4-Farben (WUBR)“, „5-Farben“, „Farblos“. Commander-Decks: Farbidentität des Commanders; sonst Farben der Nicht-Länder |
| Strategie | Archetyp (Aggro, Midrange, Control, Combo, Tempo, Ramp …, mit Bindestrich verbunden) + Thema (Tokens, Landfall, Mentor, Elementals …); aus `deck_namen.json` (`strategie`) oder dem bisherigen Namen. Für Commander-Precons aus den EDHREC-Themen abgeleitet. `archetypen.py profil` ordnet das Thema einem Archetyp aus `11` zu |
| Herkunft | Precon / Precon-Edit / Selfbuild / AI Build; bei Commander-Precons mit **Set-Code** in Klammern, z. B. „Precon (TDC)“, „Precon-Edit (ECC)“. Commander-Decks über die Kartenstruktur (ab 20 Nicht-Standardländern): ≥ 97 % im Commander-Set → Precon, ≥ 50 % → Precon-Edit, sonst Selfbuild; sonst aus dem Namen bzw. `deck_namen.json` |
| Status | „In Arbeit“ nur aus den Prüfungen (falsche Kartenzahl, Farbidentitäts- oder Bann-Verstoß) – nicht aus dem Namen, damit er nach der Korrektur wieder verschwindet; in `deck_namen.json` mit `"status": ""` abschaltbar (z. B. Precon ohne Standardländer) |

**Kennung:** Der Deckname ist zugleich Kurzname in Register, Tabellen und Soll-Stand-Dateien (`claude/decks/<deckname>.txt`). `deck_namen.json`-Schlüssel für Nicht-Commander-Decks enthalten alten und neuen Moxfield-Dateinamen als Alternativen (`|`), damit die Zuordnung vor und nach dem Umbenennen klappt. Rundlauf Name → Moxfield-Dateiname → Name für alle 6 Decks getestet (26.10., auch mit den gekürzten Namen).

**Länge:** Moxfield erlaubt höchstens 100 Zeichen. `namen` zeigt je Deck die Zeichenzahl (z. B. `87/100 Zeichen`); ist ein Name länger, meldet das Tool „Name hat N Zeichen (Moxfield max. 100)“. Kürzen in dieser Reihenfolge: Strategie (ein Archetyp + ein Thema), dann Deckname (in `deck_namen.json`).

## 7. Ausgabeformat zum Einfügen in Moxfield (verbindlich – Wunsch des Nutzers, 25.10.2026)

```
1 Kartenname
1 Kartenname (SET) 123

1 Commander-Name
```

- eine Karte pro Zeile, `Anzahl Name`, optional ` (SET) Nummer`; alphabetisch; Commander nach einer Leerzeile am Ende
- keine Überschriften, Kommentare oder Rollen-Gruppen im Block; Rollen, Begründungen und Preise in die Tabelle daneben
- Kaufliste und Standardländer-Nachkauf als eigene Blöcke; lange Listen zusätzlich als Datei
- **Dateien für Moxfield:** Decks als `.txt`, Bestand **nur als `.csv`** (Kopfzeile `Count,Tradelist Count,Name,Edition,Condition,Language,Foil,Tags,Last Modified,Collector Number,Alter,Proxy,Purchase Price`)
- Soll-Stand-Dateien in `claude/decks/` haben Kommentarzeilen (`//`) – zum Einfügen in Moxfield stattdessen `export` verwenden
- Rundlauf getestet (Export → Einlesen → identisch); Moxfield-Import am 26.10. bestätigt: Bestand (alle Zeilen exakt, hinzugefügt statt ersetzt) und Deck (identisch)
- **Moxfield nachziehen** (Richtung Projekt → Moxfield): Zugänge als Bestands-CSV (Import fügt hinzu); Abgänge als Liste, die der Nutzer in Moxfield von Hand löscht; geänderte Decks als Einfügeblock/TXT. Offene Punkte stehen in `10_Geplante-Kaeufe-und-Ideen`, Abschnitt „In Moxfield nachziehen“.

## 8. Prüfprotokoll

Die Werkzeuge sind im Admin-Projekt geprüft (automatische Tests). Das Paket V1.7 wurde am 29.10.2026 in einer leeren Umgebung mit Beispieldaten getestet (Ersteinrichtung, Datenbank-Bau, Deckprüfung, Deck-PDF). Eigene Prüfungen trägt Claude nicht hier ein (Datei gesperrt), sondern im `09_Aenderungsprotokoll`.
