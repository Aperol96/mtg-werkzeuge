# Deckbau-Verfahren – geführter Commander-Deckbau

**Stand:** 31.10.2026 (V1.9: Ziel-Bracket immer im Fragenplan, Erklärung aller Brackets auf Wunsch, Ausgangsbracket messen, Bracket-Wächter `deckbau.py bracket` – Grundsatz 17, Abschnitt 2c · V1.7: Frage nach dem Gegenlauf am Ende von Stufe A · V1.6: Archetyp-Richtwert vor Template, Raus-Sperren, Kompromiss-Stufen, Oracle-Bezug (`synergie`), Bracket-3-Abnahme als Definition of Done, Konsistenz-Simulation; Lieferung, Buchen und Gegentest ausgelagert nach `08a`) · Werkzeuge: `deckbau.py`, `bewertung.py`, `simulation.py`, `mtg_db.py`, `archetypen.py`, `kartenbilder.py` (Anleitung `05_Datenbank-und-Tools`, Sitzungsstart `05a`) · Richtwerte: `11_Archetypen-Playbook`, Template in `01_Quellen-Framework` Abschnitt 4, Kosten-Nutzen Abschnitt 6 · Sammlung nach Archetypen: `12_Sammlungsprofil`, Decks: `12a_Deck-Raster` · Nach der Freigabe: `08a_Lieferung-Buchen-Gegentest`

Dieses Verfahren gilt für **jedes neue Commander-Deck** und für Neuaufbauten – für Admin, User und Gast (der Gast mit seinen eigenen Daten, Besonderheiten in `13_Betriebsmodus-und-Weitergabe`, Abschnitt 7); für **Upgrades** bestehender Decks gelten dieselben Stufen mit den Besonderheiten aus Abschnitt 2a. Es führt den Nutzer per Frage-Antwort-Spiel zum Deck und sichert dabei alles ab, was Spieler beim Deckbau gern übersehen.

---

## 1. Grundsätze

1. **Führen mit Fragenplan – ohne Höchstzahl.** Vor der ersten Frage legt Claude fest, was geklärt werden muss (Pflicht), was nur je nach Ausgangslage oder Antwort (bedingt) und was helfen würde (optional) – Abschnitt 2b. Gefragt wird, bis der Plan erledigt ist oder der Nutzer „reicht – entscheide den Rest“ sagt; es gibt keine feste Zahl an Fragen oder Runden (Wunsch des Nutzers, 27.10.2026). Jede Frage wenn möglich als Auswahl (AskUserQuestion, höchstens 4 je Block) mit markierter Empfehlung und kurzer Datenbasis (z. B. „Tokens – 688 Decks auf EDHREC“), immer mit „Weiß nicht – entscheide du“; eigene Angaben und Ergänzungen per Freitext gehen jederzeit. Bereits Bekanntes nicht erneut fragen (Projektdateien, Deckregister, Notizen).
2. **Der Nutzer kann Fehler machen.** Er wird Ramp, Kartenvorteil, Interaktion (vor allem Instants), Wipes, Schutz oder die Manabasis nicht immer bedenken. Das Verfahren füllt diese Rollen **immer** bis zu den Mindestwerten auf, auch wenn er sie nicht erwähnt. Widerspricht ein Wunsch den Mindestwerten (z. B. „keine Removal“), ehrlich kommentieren; nur auf ausdrücklichen Wunsch abweichen, und dann die Warnung in der Ausgabe stehen lassen.
3. **Daten vor Meinung.** EDHREC (Themen, Inclusion, Synergie, Lift), Commander Spellbook (Combos), Scryfall (Rollen, Legalität, Game Changer), playgroup.gg (Siegquote). Daten und Einschätzung getrennt kennzeichnen. **EDHREC ist ein Anhaltspunkt, nicht die Hauptquelle** (Wunsch des Nutzers, 29.10.2026): Was beim Commander selten gespielt wird, kann im eigenen Deck trotzdem die richtige Karte sein – entscheidend sind Oracle-Text, Rolle, Scryfall-Funktionstags, Combos und der Spielplan. Seit V1.6 rechnen die Werkzeuge das mit: `deckbau.py synergie` liest aus dem Commander-Text, welche Ressourcen er erzeugt und nutzt, und findet freie Karten mit Bezug – auch ohne EDHREC-Eintrag. Eine Karte, die nicht auf der EDHREC-Seite steht, ist **unbekannt, nicht schwach**.
4. **Bestand richtig lesen.** Das Projekt ist die Hauptdatenbank; Bestand = Deckkarten + Sammlung (Basis + `buchungen.csv`). „Vorhanden“ heißt **frei**: nicht in einem Deck und nicht in `10_Geplante-Kaeufe-und-Ideen` vorgemerkt. Deckkarten nur als Tausch im Rahmen einer Deckänderung – das abgebende Deck bekommt einen Ersatz und behält seine Zielgröße.
5. **Bracket-Treue.** Das Ziel-Bracket wird in jedem Gespräch gefragt (Abschnitt 2c); Empfehlung: bei bestehenden Decks das Ausgangsbracket, sonst Bracket 3 (Spielgruppe 3–5 Spieler). Im Bracket maximal stark, nicht heimlich darüber. Jedes Deck – neu oder Upgrade – gilt erst als fertig, wenn es die **Bracket-3-Abnahme** besteht (Abschnitt 8a). Alle Decks werden gleich behandelt; kein Deck hat Vorrang.
6. **Kosten-Nutzen.** Käufe nur mit Rolle, Wirkung, Preis (günstigster Druck, Datum), günstigerer Alternative und Klasse A–D.
7. **Freigabe, Aufbau, Buchung** (`08a`). Bis zur Freigabe ist das Deck ein Vorschlag im Chat – das Projekt bleibt unberührt. Mit der Freigabe fragt Claude kurz nach PDFs und Dateien (Ja/Nein, `13`, Abschnitt 9); die Idee steht dann mit Status „freigegeben – Aufbau offen“ in `10` (Karten vorgemerkt, Entwurf gesichert; Gast: im Arbeitsbereich). **Gebucht wird erst, wenn der Nutzer meldet, dass das Deck physisch gebaut ist** (Soll-Stand, Bestand, Register, Protokoll).
8. **Jeder Schritt an seiner Stelle – die Recherche ohne Beschränkung.** Die Recherche zu Deck und Sammlung (Stufe B) bekommt die Ressourcen, die sie braucht: alle Quellen aus `01` (EDHREC mit allen passenden Themen-, Bracket- und Budgetfiltern, Commander Spellbook, Scryfall-Funktionstags, playgroup.gg/EDHTop16, Live-Prüfungen), so viele Abrufe und Prüfläufe wie nötig – sie beginnt erst, wenn das Gespräch die Richtung geklärt hat, und steht vollständig vor dem Vorschlag. **Nur einmal und erst am Ende** laufen die Schritte, die nichts zur Entscheidung beitragen: Kartenerklärungen, Bilder/PDFs und Schreibvorgänge im Projekt. Den Datenbank-Bau im Hintergrund starten, sobald Deck oder Commander feststeht, damit er während der Fragerunden läuft.
9. **Oracle-Pflicht.** Jede Karte, die Claude im Vorschlag oder in einer Erklärung beschreibt, wird aus ihrem Oracle-Text beschrieben – nie aus dem Gedächtnis. Vor jedem Vorschlag läuft `deckbau.py oracle --alt <Soll-Stand> --neu <Entwurf>` (neues Deck: `oracle <Karten>` bzw. die Spalte Oracle-Text aus `kandidaten`/`erklaerung`); `upgrade` gibt den Text der vorgeschlagenen Karten schon mit aus. Stärke/Widerstand, Kosten und Bedingungen werden aus dieser Ausgabe übernommen. (Anlass: Testlauf 27.10.2026 – vier Karten waren aus dem Gedächtnis falsch beschrieben.)
10. **Fragen ohne Widerspruch.** Hängt eine Frage von einer anderen ab (Game-Changer-Kauf vom Budget), nacheinander fragen oder nur Optionen anbieten, die zu jeder Antwort der anderen Frage passen (z. B. „Game Changer nach Wirkung – bei Stufe 0 nur freie“). Widersprechen sich Antworten trotzdem, gilt die engere Vorgabe (Budget vor Wunsch); Claude sagt das in einem Satz.
11. **Einheitliche Zahlen.** Rollen über die 99 ohne Commander, Ø MV über alle Nichtländer inkl. Commander, EDHREC-Werte von der Commander-Seite mit Bracket-Filter ohne Thema (Themenwerte nur zusätzlich und gekennzeichnet). So stehen im Chat, im Fazit-PDF und im Deck-PDF dieselben Zahlen (`05`, Abschnitt 4).
12. **Passung vor Ausbau.** Die Ausgangslage gilt nicht als gesichert: Erst prüfen, ob Deck, Commander und Ziel zusammenpassen (`deckbau.py passung`), dann upgraden. Ein Commander-Wechsel – aus dem Deck, der Sammlung oder als günstiger Kauf – oder ein an das Deck angepasstes Thema kann besser sein als ein Umbau um den alten Commander. Auch bei neuen Decks prüfen, ob ein eigener Commander das gewünschte Thema besser trägt. Claude legt die Optionen mit Daten vor und empfiehlt; **der Nutzer entscheidet** (Abschnitt 2b).
13. **Jede Änderung begründen – raus wie rein.** Zu jeder herausgenommenen Karte steht ein Satz „warum raus“, zu jeder neuen ein Satz „warum rein“ – beide aus dem Oracle-Text, dazu die Datenbasis (EDHREC-Wert beim Commander, Rolle über bzw. unter Richtwert). Im Vorschlag und im Fazit-PDF.
14. **Rückfall vor Kauf mit Kompromiss-Stufen** (Wunsch des Nutzers 29.10.2026, Stufen seit V1.6). Ist eine Rolle unter dem Minimum und gibt es keine bessere freie Karte, kommt eine schwächere freie Karte mit passender Rolle ins Deck, bevor ein Kauf vorgeschlagen wird – auch Karten wie Terramorphic Expanse, Prophetic Prism oder Embermouth Sentinel. In Stufe 0 und Weg 1 ist das der Normalfall. Jede solche Karte bekommt eine **Kompromiss-Stufe** (aus Funktionsgrad und Wert gegenüber der besten Kauf-Alternative, `05`, Abschnitt 4g): **gleichwertig** · **funktional, aber langsamer** · **nur Platzhalter** – daneben die Kauf-Alternative mit Preis und einem Satz, was der Aufpreis bringt (z. B. „Pitiless Plunderer für 2,92 € bringt: Wert 0,62 → 1,05“). Der Nutzer entscheidet. Ehrlich bleiben: Ist eine Karte für den Plan wirklich schlecht, steht das im Vorschlag.
15. **Archetyp-Richtwert vor Template** (Review 29.10.2026). Die Rollen-Minima kommen vom Ziel-Archetyp (Median der EDHREC-Durchschnittsdecks, `11`), das Template aus `01` gilt nur ohne Archetyp. Karten, die den eigenen Plan zerstören – symmetrische Kreaturen-Wipes im Go-wide-Deck (Tokens, Aristokraten, Kindred, Counter, Voltron, Blink) –, zählen nicht für ihre Rolle und werden nicht vorgeschlagen; Massen-Interaktion kommt dort aus einseitigen Wipes, Edikten oder Schutz.
16. **Nichts Tragendes herausnehmen** (Raus-Sperren, V1.6). Eine Karte verlässt das Deck nicht, wenn dadurch ein Kernpaket unter den Median fällt, wenn sie starken Commander-Bezug hat (≥ 0,5; außer für eine Karte mit gleichem Bezug und Grund), wenn ihre Rolle unter das Minimum fällt oder schlechter ersetzt wird oder wenn die Interaktion gegen ein Ziel unter die Untergrenze fällt. `upgrade` zeigt die gesperrten Karten mit Grund; Claude hebt eine Sperre nur mit Begründung im Vorschlag auf.
17. **Bracket-Wächter** (Wunsch des Admins, 31.10.2026). Das Ziel-Bracket wird bei jedem Bau und Upgrade gefragt, die Erklärung aller Brackets angeboten; bei bestehenden Decks misst Claude vorher das Ausgangsbracket. Ist das Ziel das Ausgangsbracket, warnt Claude bei jeder Änderung, die das Bracket verschieben würde, und schlägt eine Karte vor, die im Bracket bleibt – der Nutzer entscheidet (Abschnitt 2c).

---

## 2. Der Ablauf im Überblick (Stufen A–F, gestrafft 27.10.2026 auf Wunsch des Nutzers)

| Stufe | Wer | Was passiert | Phasen | Werkzeug | Aufwand |
|---|---|---|---|---|---|
| **A Gespräch** | Nutzer ↔ Claude | Auftrag und Ausgangslage erfassen → **Fragenplan** (Abschnitt 2b) → bei bestehenden Decks **Passungs-Check** (Deck ↔ Commander ↔ Ziel, bessere Commander in Deck, Sammlung, Kauf) → Deckphilosophie: Commander, Weg, **Ziel-Bracket** (vorher Ausgangsbracket messen, 2c), Budget, Strategie, Siegwege, Stil, Wünsche, Spielgruppe – Fragen ohne Höchstzahl → Steckbrief bzw. Upgrade-Richtung bestätigen → **Frage Gegenlauf** (Ja/Nein mit Ressourcenhinweis, `08a`, Abschnitt 5) | 0–3 (Steckbrief) | Projektdateien (`09`, `10`, `04`, Soll-Stand, `11`, `12`), `deckbau.py bracket`, `deckbau.py passung`, `commander`, `commander-suche --nur-besitz` | leicht bis mittel; Datenbank-Bau startet sofort, wenn ein bestehendes Deck betroffen ist, sonst sobald der Commander feststeht |
| **B Recherche und Vorschlag** | Claude | Kartenpool, Bauen, Qualitätskontrolle, **Abnahme** → **Vorschlag**: neues Deck = Liste nach Rollen mit Kurzbegründung der tragenden und ungewöhnlichen Karten, Ampel, Bracket-Zeile, Abnahme-Ergebnis, Kaufliste mit Preisen · Bearbeitung = Tauschpaare „raus → rein“ mit Grund, Kompromiss-Stufe bzw. Klasse und Preisdifferenz, Auswirkung aufs Bracket (Bracket-Wächter, 2c), Abnahme vorher → nachher | 3–5, 8a | EDHREC, Spellbook, Scryfall, playgroup.gg; `synergie`, `kandidaten` bzw. `upgrade`, `alternativen`, `suche`, `pruefen`, `bracket --neu`, `abnahme`, `simulation.py`, `oracle`, `archetypen.py deck` | hoch – volle Recherche, keine Beschränkung |
| **C Anpassung** | Nutzer ↔ Claude | Änderungswünsche; Claude recherchiert so tief, wie die Änderung es verlangt (Einzelkarte → Alternativen und `pruefen`; neue Richtung wie Strategie, Commander, Budget, Bracket → Recherche in vollem Umfang neu) und zeigt nur die Änderungen, nicht die ganze Liste; jede Änderung läuft durch den Bracket-Wächter (2c); Schleife bis „passt“ = Freigabe | 3–5 | wie B, nach Bedarf | nach Bedarf |
| **D Abschluss** (`08a`) | Claude | erst nach Freigabe und auf Nachfrage – „PDF-Dokumentation? (Ja/Nein)“, dann „Import-Datei für <Quelle>? (Ja/Nein)“: **Fazit-PDF** (Fazit, Änderungen mit „warum raus“ und „warum rein“, Kennzahlen, Spielplan, Einschätzung, Kartenerklärungen, Vorgehen, Moxfield-Anhang), Einfügeblock **immer auch als TXT**, Kaufliste, Standardländer-Nachkauf, Deckname, Moxfield-Beschreibung/Themen, **PDFs** (bearbeitetes Deck: Tauschübersicht mit PNG + Deck-PDF; neues Deck: Deck-PDF) – alles aus einem vorbefüllten Fazit-Entwurf in einem Lauf (`08a`, Abschnitt 3); Idee in `10` „freigegeben – Aufbau offen“ | 6–7 | `mtg_db.py drucke`/`laender`, `deckbau.py fazit`, `kartenbilder.py lieferung` (Einzelbefehle `bericht`/`tausch`/`deck` nur für Sonderfälle) | mittel, einmal |
| **E Aufbau** | Nutzer | baut das Deck physisch nach den PDFs; meldet „gebaut“ und Abweichungen (Karte nicht gefunden, Ersatz genommen, Kauf noch unterwegs) | – | – | – |
| **F Buchen** (`08a`, Abschnitt 4) | Claude | erst nach der Meldung (Gast: stattdessen Quittung, `13`, G6): Abweichungen einarbeiten, Käufe als Zugang, Soll-Stand(e), Vormerkungen und `10` bereinigen, 06/07, Deckregister, Protokoll, Moxfield-Dateien | 8 | `mtg_db.py` (`snapshot`, `bestand-export`, `export`), Projektdateien | schwer, einmal |

**Ins Projekt geschrieben wird nur in D und F** (im Testlauf und im Zustand Gast nie, `13`, Abschnitte 5.1 und 7; der Gast archiviert am Ende höchstens sein eigenes Archiv). Jede Schreibrunde endet mit dem Nachziehen des Datenpakets (`05a`, Abschnitt 6). D: eine Schreibrunde (Idee mit Status „freigegeben – Aufbau offen“, Vormerkungen, Entwurf als `claude/ideen/<deckname>-<thema>.txt`, damit der Aufbau auch in einem späteren Chat gebucht werden kann). F: alle Buchungen. Endet ein Chat ohne Freigabe, sichert Claude den Stand einmal als Idee in `10` (Status „wartet auf Freigabe“, Vormerkungen), damit kein anderer Chat dieselben Karten verplant.

**Was wann Ressourcen kostet** (die Reihenfolge entscheidet, nicht Sparsamkeit – die Recherche läuft in vollem Umfang):

| Vorgang | Kosten | Stufe |
|---|---|---|
| `protokoll.py offen/zeigen`, Soll-Stand, `deckbau.py commander` (Scryfall/EDHREC, wenige Abrufe) | gering | A |
| Datenbank-Bau (Scryfall-Bulk ≈ 110 MB, ≈ 20–60 s) | hoch | im Hintergrund ab A, gebraucht ab B (bei bestehenden Decks schon in A für `passung`) |
| `deckbau.py passung` (je Commander-Kandidat eine EDHREC-Seite, ≈ 5–30 s) | mittel | A, bei bestehenden Decks |
| Recherche: EDHREC (alle passenden Filter und Themen), Spellbook, Scryfall-Tags, playgroup.gg/EDHTop16, Live-Prüfungen, `synergie`, `kandidaten`, `suche`, `pruefen`, `abnahme` (inkl. Simulation, ≈ 2–5 s), `archetypen.py deck` | hoch – **keine Beschränkung** | B; in C erneut, soweit die Änderung es verlangt |
| Kartenerklärungen für alle Karten | mittel (Text) | D, einmal |
| Fazit-Entwurf + alle PDFs (`fazit` + `lieferung`: ≈ 10 s, Bilder parallel, Handy-Größe ≈ 0,1–2,5 MB je PDF); Claude schreibt nur die Texte | mittel | D, einmal |
| Buchungen, 06/07, Register, Protokoll, Moxfield-Dateien | hoch (viele Schreibvorgänge) | F, einmal |
| `12_Sammlungsprofil` neu (Scryfall-Bulk + Tags) | hoch | F, nur nach größeren Änderungen (ab ≈ 10 freien Karten) oder vor der nächsten Commander-Suche |

## 2a. Upgrade eines bestehenden Decks (Ablauf B, seit 27.10.2026)

Gleiche Stufen A–F. Unterschiede:

**Stufe A – Fragenplan und Passung** (Abschnitt 2b; vorher `protokoll.py zeigen --deck <D>` und `offen --deck <D>`, Soll-Stand und `12a_Deck-Raster` lesen, Datenbank-Bau sofort starten, dann `deckbau.py passung` und das **Ausgangsbracket** messen, Abschnitt 2c). Fragenkatalog für Upgrades – keine Höchstzahl, jede Frage mit „Weiß nicht – entscheide du“:

| Frage | Art | Optionen | Hinweis |
|---|---|---|---|
| Ziel – was soll besser werden, was stört? | Pflicht (darf schon laufen, während die Datenbank baut) | Auswahl aus dem Deckprofil (z. B. „Landfall verdichten“, „mehr Interaktion“, „schneller gewinnen“) · eigene Angabe | liefert das Ziel-Thema für `passung --thema` |
| Richtung / Commander | Pflicht, sobald `passung` es verlangt (Tabelle in 2b) | A Commander behalten, Deck umbauen · B Commander wechseln (Kandidat mit Daten) · C Thema an das Deck anpassen · D Neubau | Empfehlung nach Passung, Aufwand, Kosten und Spielgefühl |
| Richtung im Thema | Pflicht, wenn A gilt | Strategie beibehalten und verdichten · auf ein EDHREC-Thema schärfen (Themen mit Deckzahl, Kurzplan aus `11`) · eigene Idee | Empfehlung nach Commander-Text und Paketlücken (`archetypen.py deck`) |
| Budget | Pflicht | Stufe 0 (nur freie Karten, 0 €) · Stufe 1 bis 25 € · bis 50 € · offen, Stufen zeigen | legt fest, welche Optionen die übrigen Fragen haben dürfen (Grundsatz 10) |
| Ziel-Bracket | Pflicht | „Bracket X behalten (Empfehlung)“ = Ausgangsbracket · ein Bracket höher · ein Bracket niedriger · „Erst alle Brackets erklären“ | vorher das Ausgangsbracket in einer Zeile nennen; gleich → Bracket-Wächter, anders → Umbau aufs Ziel (2c) |
| Game Changer | bedingt (freie Game Changer vorhanden oder Slots frei) | nach Wirkung füllen (bei Stufe 0 nur freie) · Slots frei lassen · Anzahl festlegen | freie Game Changer aus `upgrade` nennen |
| ⚑-Karten | bedingt (wenn `upgrade` welche zeigt) | liegt beim Deck · liegt in der Sammlung | `mtg_db.py exemplare <deck>` |
| Siegwege, Spielstil, Deckname | bedingt (bei neuer Richtung oder neuem Commander) | wie Abschnitt 5 und 6 | |
| Lieblings-/Tabukarten, Spielgruppe | optional | | Bedrohungsprofil `11`, Abschnitt 3.6 |

**Stufe B – Recherche und Vorschlag:**
0. Ausgangslage messen: `deckbau.py abnahme <deck>` (welche Prüfpunkte offen sind, Stärke-Index als Basis) und `deckbau.py synergie <deck>` (freie Karten mit Bezug zum Commander-Text, auch ohne EDHREC).
1. `deckbau.py upgrade <deck> --stufe <0|1> [--max-preis X] [--thema <archetyp|slug>] [--idee I-nnn]` → Rollen gegen den Archetyp-Richtwert, Kernpakete gegen den Median, Raus-Sperren, Tauschpaare mit Oracle-Text, Kompromiss-Stufen und Klassen (kurz; `--voll` für alle Listen). Die Paare sind ein Startpunkt; Claude entscheidet nach Spielplan, Kurve und Synergie. Rollen unter dem Minimum füllt `upgrade` zuerst aus freien Karten mit Kompromiss-Stufe und Kauf-Alternative (Grundsatz 14); `--voll` zeigt den Rückfall-Pool (Länder wie Terramorphic Expanse dort prüfen und bei Bedarf gegen ein Standardland tauschen).
2. **⚑-Karten** (frei, aber zusammen mit dem Deck erfasst): vor dem Vorschlag fragen, ob sie physisch beim Deck liegen (Maybeboard, fehlende Deckkarte) – bedingte Frage im Fragenplan; `mtg_db.py exemplare <deck>` zeigt die Liste.
3. Paketlücken: `archetypen.py deck <Soll-Stand> --archetyp <a>` und `archetypen.py karten <a> --farben <WUBRG> --ohne-deck <Soll-Stand>`.
4. Entwurf schreiben → `pruefen <entwurf> --ersetzt <deck>` → `abnahme <entwurf> --basis <deck>` (Abschnitt 8a; nicht bestanden → nachbessern oder offen benennen) → `oracle --alt <Soll-Stand> --neu <entwurf>` (Pflicht) → Bracket-Wächter `bracket <Soll-Stand> --neu <entwurf> --ziel <Ziel>` (2c) → Bracket-Zeile vorher → nachher.
5. **Vorschlag:** Tauschpaare „raus → rein“ mit **warum raus** und **warum rein** – je ein Satz aus dem Oracle-Text plus Datenbasis aus `upgrade` (EDHREC-Wert oder „unbekannt“, Commander-Bezug mit Grund, Rolle über Richtwert bzw. füllt eine Rolle) –, Status frei mit Kompromiss-Stufe bzw. €, bei Käufen Klasse A–D und günstigere Alternative; Rollenbilanz und Kernpakete vorher → nachher, Abnahme vorher → nachher (Stärke-Index), Bracket-Zeile mit Ausgangs- und Ziel-Bracket und den Warnungen des Bracket-Wächters, offene ⚑-Fragen. `upgrade` gibt den Oracle-Text der Raus- und der Rein-Karten aus.

**Keine Machbarkeitsampel:** Die Ampel aus Abschnitt 6 gilt nur für neue Decks (Weg 1). Bei Upgrades zeigen Rollenbilanz und Kandidaten von `upgrade`, was Stufe 0 leisten kann; reicht das nicht, Stufe 1 anbieten.

**Stufe D:** Fazit-PDF + Tauschübersicht + Deck-PDF in einem Lauf (`08a`, Abschnitt 3): `deckbau.py fazit --alt <deck> --neu <entwurf_drucke> [--paare <datei>] [--thema <archetyp>]` → Texte füllen → `kartenbilder.py lieferung`.

## 2b. Fragenplan und Passungs-Check (Stufe A – für jeden Auftrag, seit 27.10.2026)

Wunsch des Nutzers: keine feste Fragenzahl; vorher festlegen, was gefragt werden muss; die Ausgangslage nicht als gesichert annehmen – Deck und Commander passen vielleicht gar nicht zusammen. Kann der Nutzer etwas nicht beantworten oder will er etwas ergänzen, muss das jederzeit gehen.

**Schritt 1 – Auftrag und Ausgangslage erfassen** (vor der ersten Frage, ohne Rückfrage):
- Auftrag: neues Deck (Commander vorgegeben oder nicht) · Upgrade · Umbau/Neuausrichtung · Analyse.
- Daten: `protokoll.py zeigen --deck` und `offen`, Soll-Stand, `protokoll.py register --deck` (Ziel-Bracket, Strategie), `12a_Deck-Raster`, freie Commander in `12`.
- **Bestehendes Deck:** Datenbank-Bau sofort im Hintergrund starten, danach `deckbau.py passung <deck> [--thema <ziel>] [--kauf 3]`. Bis der Bau fertig ist, darf die erste, datenunabhängige Frage laufen („Was soll das Deck können, was stört dich?“) – ihre Antwort liefert das Ziel-Thema für `--thema` (sonst nimmt `passung` die Strategie aus dem Deckregister). Ebenfalls gleich nach dem Bau: **Ausgangsbracket** messen (Abschnitt 2c).
- **Neues Deck mit Commander:** `deckbau.py commander` (Themen); sobald das Thema feststeht, `deckbau.py commander-suche --thema <slug> --farben <Farbidentität> --nur-besitz` – gibt es einen eigenen Commander, der das Thema besser trägt? Wenn ja: bedingte Frage „Commander bestätigen oder Alternative?“ mit Deckzahl, Besitz und Machbarkeitsampel beider.

**Schritt 2 – Fragenplan festlegen und kurz zeigen** (in der ersten Antwort, eine Zeile je Art, z. B. „Klären muss ich: … · je nach Antwort: … · hilfreich wäre: …“):

| Art | Wann | Beispiele |
|---|---|---|
| Pflicht | ohne Antwort kein sinnvoller Vorschlag | Ziel/Richtung, Weg bzw. Budget, **Ziel-Bracket** (immer, mit Angebot „alle Brackets erklären“, Abschnitt 2c), Commander-Frage bei auffälliger Passung |
| bedingt | nur wenn Ausgangslage oder eine Antwort sie auslöst | Commander-Wechsel, Thema anpassen, ⚑-Karten, Game-Changer-Plan, Siegwege und Deckname bei neuer Richtung, Spielgruppe bei geändertem Interaktionsmix |
| optional | verbessert den Vorschlag; sonst entscheidet Claude mit der Empfehlung | Lieblings-/Tabukarten, Spielstil-Feinheiten, Kurve, Spieldauer |

Regeln:
- **Keine Höchstzahl.** Gefragt wird, bis alle Pflichtfragen und die ausgelösten bedingten Fragen beantwortet sind. Technisch höchstens 4 Fragen je Auswahl-Block, dann der nächste Block; abhängige Fragen kommen in einen späteren Block (Grundsatz 10).
- **Jede Frage** als Auswahl mit markierter Empfehlung und kurzer Datenbasis, plus **„Weiß nicht – entscheide du (Empfehlung: …)“**. Freitext für eigene Ideen und Ergänzungen geht immer; löst eine Ergänzung neue Fragen aus, passt Claude den Plan an und sagt es in einem Satz.
- **„Reicht – entscheide den Rest“** beendet die Fragen: Für offene Punkte gilt die Empfehlung; sie steht im Steckbrief bzw. in der Upgrade-Richtung.
- Der Plan endet mit dem **Steckbrief** (neues Deck) bzw. der **Upgrade-Richtung** zum Bestätigen – Auswahl „passt · ändern · ergänzen“; hier kann der Nutzer alles nachtragen, was nicht gefragt wurde.
- Danach **eine** Ja/Nein-Frage zum **Gegenlauf** (`08a`, Abschnitt 5): zwei Konkurrenz-Agenten bauen unabhängig mit denselben Vorgaben, Claude wägt drei Vorschläge ab – mit Hinweis auf den Aufwand (je Agent ≈ 0,2–0,3 Mio. Token, 5–15 Minuten parallel, ≈ 4–6 € API-Gegenwert). Bei Ja sofort `deckbau.py gegenlauf` und die Agenten starten, dann die eigene Recherche.

**Schritt 3 – Passung abwägen** (bestehende Decks; `passung` liefert die Daten):

`passung` zeigt: was das Deck trägt (Kernpakete je Archetyp gegen die EDHREC-Mediane), was der Commander laut EDHREC spielt (Themen mit Deckzahl, Rang des Ziel-Themas), wie viele Spielkarten Bezug zum Commander haben, welche Commander aus dem Deck, der Sammlung (frei) und optional als Kauf (`--kauf N`, Top-Commander der EDHREC-Themenseite in den Deckfarben) besser zu den vorhandenen Karten passen (Ø Wert je Spielkarte, Faktor gegenüber dem jetzigen Commander, Karten außerhalb der Farbidentität) und welche auf das Ziel-Thema spezialisiert sind. Daraus folgen die Fragen:

| Befund | Frage im Plan | Optionen |
|---|---|---|
| Ziel-Thema ≥ 80 % abgedeckt, Commander passt | keine Passungsfrage – weiter mit dem Upgrade-Katalog (2a) | – |
| Ziel-Thema 50–80 % | Richtung im Thema (Pflicht) | schärfen · Mischung behalten |
| Ziel-Thema < 50 %, ein anderes Thema stark | **Richtung / Commander (Pflicht)** | A Commander behalten, Deck umbauen · B Commander wechseln · C Thema an das Deck anpassen · D Neubau |
| ≥ 40 % der Spielkarten ohne Bezug zum Commander | **Richtung / Commander (Pflicht)** | wie oben |
| ein Kandidat passt ≥ 10 % besser | **Richtung / Commander (Pflicht)** | wie oben; B mit Passung, Herkunft (im Deck · frei · Kauf €) und Karten außerhalb der Farbidentität |
| Spezialist fürs Ziel-Thema vorhanden (EDHREC-Thema unter den Top 3) | Ist das Thema wichtiger als der Commander? (bedingt) | Commander behalten · Spezialisten nehmen |

- **Claude empfiehlt, der Nutzer entscheidet.** Kein Commander- oder Themenwechsel ohne ausdrückliche Antwort. Abwägen: Passung (Daten), Aufwand (Karten ohne Bezug, Karten außerhalb der Farbidentität), Kosten, Spielgefühl des Commanders (Oracle-Text) und was der Nutzer will (Einschätzung, gekennzeichnet).
- **Beispiel** (künstliches Testdeck, 27.10.2026): Karametra, Ziel Landfall, im Deck nur +1/+1-Counter-Karten → Ziel-Thema 8 %, Counter 100 %, 51 von 59 Spielkarten ohne Bezug zu Karametra; Hamza, Guardian of Arashin (im Deck) passt 9,4-mal besser, Black Panther, Wakandan King (Kauf 2,89 €) verbindet Counter und Lands Matter → Pflichtfrage „Richtung / Commander“ mit B als Empfehlung statt eines Umbaus um Karametra.
- Nach einem Wechsel (B, C, D) gilt der neue Commander bzw. das neue Thema: `passung` bzw. `upgrade`/`kandidaten` damit neu laufen lassen; Deckname, Moxfield-Name und Register-Eintrag ändern sich (Stufe F), der alte Commander wird frei bzw. bleibt im Deck, wenn er dort eine Rolle hat.

## 2c. Ziel-Bracket, Ausgangsbracket und Bracket-Wächter (seit V1.9, Wunsch des Admins 31.10.2026)

Wunsch: Bei jedem Bau und jedem Upgrade wird im Gespräch gefragt, welches Bracket das Deck erreichen soll; Claude bietet an, alle Brackets zu erklären. Bei bestehenden Decks prüft Claude vorher, in welchem Bracket das Deck heute steht. Sind Wunsch und Ausgangsbracket gleich, warnt Claude, sobald eine Änderung das Bracket verschieben würde.

**1. Ausgangsbracket messen** (nur bestehende Decks; in Stufe A, sobald die Datenbank steht, vor der Frage nach dem Ziel-Bracket)
- Werkzeug: `deckbau.py bracket <deck>` – liest Game Changer, MLD, Extra Turns und 2-Karten-Combos (Commander Spellbook) und stuft nach den harten Grenzen aus `01a` ein (Stand live prüfen, Datum nennen); dazu die Spalte „Bracket nach Kriterien / Einschätzung“ im Deckregister (`protokoll.py register --deck`). Weicht die Einschätzung im Register von den harten Grenzen ab, gilt sie mit `--ausgang <B>`.
- Einstufung (so rechnet das Werkzeug) – das niedrigste Bracket, dessen Grenzen das Deck einhält:

| Befund (Daten) | Ausgangsbracket |
|---|---|
| keine Game Changer, keine MLD, keine Extra-Turn-Ketten, keine gezielten 2-Karten-Combos | 2 – oder 1, wenn das Deck erkennbar Thema vor Stärke spielt (Einschätzung) |
| 1–3 Game Changer oder eine 2-Karten-Combo, die nicht früh zusammenkommt; keine MLD, keine Extra-Turn-Ketten | 3 |
| mehr als 3 Game Changer, MLD oder zwei und mehr Extra-Turn-Karten (Kette möglich) – eine früh mögliche 2-Karten-Combo nach Einschätzung | 4 – 5 nur, wenn das Deck erkennbar auf cEDH-Niveau gebaut ist (Einschätzung) |

- Die harten Grenzen sind Daten; 1 gegen 2, 4 gegen 5 und „früh“ bei Combos sind Einschätzung und werden so gekennzeichnet. Brackets beschreiben die Absicht: Wirkt ein Deck ohne Game Changer deutlich stärker als Bracket 2 (Spellbook-Einstufung, Tutoren, Kurve, Stärke-Index), sagt Claude das ehrlich.
- Weicht die Messung vom Register ab, nennt Claude beides in einem Satz („Register: Bracket 3 · gemessen: 2 – keine Game Changer“).
- Ausgabe vor der Frage, eine Zeile: „Dein Deck steht heute in Bracket X – <Grund aus der Bracket-Zeile>.“

**2. Frage nach dem Ziel-Bracket** (Pflicht im Fragenplan – neues Deck und Upgrade, auch wenn das Register ein Bracket nennt)
- Auswahl (AskUserQuestion): **Empfehlung** – Upgrade: „Bracket X behalten (Empfehlung)“ = Ausgangsbracket; neues Deck: Bracket 3 (Spielgruppe) – mit dem Zusatz „gilt auch bei ‚Weiß nicht – entscheide du‘“ · ein Bracket höher · ein Bracket niedriger · **„Erst alle Brackets erklären“**. Andere Brackets per Freitext.
- **Erklärung** auf Wunsch (Auswahl oder Freitext wie „Was heißt Bracket 4?“): kurze Tabelle aus `01a` – je Bracket Name, Game Changer, erwartete Spieldauer, Einschränkungen –, ein Satz „Brackets beschreiben die Absicht, nicht nur die Kartenliste“ und bei Upgrades, wo das Deck heute steht. Stand live prüfen (Brackets „Beta“, Game-Changer-Liste) und mit Datum nennen; danach die Frage erneut stellen. Ungefragt erklärt Claude nichts (Admin und erfahrene Spieler).
- Das Ziel-Bracket gilt für `kandidaten`, `upgrade`, `pruefen`, `abnahme` (`--bracket <Ziel>`) und steht im Steckbrief bzw. in der Upgrade-Richtung.

**3. Bracket-Wächter** (Stufen B und C, jede Änderung)
- **Werkzeug:** `deckbau.py bracket <Soll-Stand> --neu <Entwurf> [--ziel <B>] [--ausgang <B>]` – vergleicht beide Stände gegen das Ziel-Bracket, nennt die auslösenden Karten und je Karte bis zu vier Karten gleicher Rolle ohne Game Changer, MLD und Extra Turns (freie zuerst). Läuft nach jedem Entwurf in Stufe B und nach jeder Anpassung in Stufe C; die Warnungen übernimmt Claude wörtlich in den Vorschlag.
- **Ziel = Ausgangsbracket:** Jedes Tauschpaar und jede Anpassung wird darauf geprüft, ob sie das Bracket verschiebt:
  - **nach oben:** erster bzw. zusätzlicher Game Changer über die Grenze des Brackets (in Bracket 1–2 schon der erste), MLD, Extra-Turn-Karte, eine neue 2-Karten-Combo (auch eine Beinahe-Combo, die die neue Karte vervollständigt) oder eine Combo, die dadurch früher zusammenkommt;
  - **nach unten:** eine Änderung, nach der das Deck die Merkmale seines Brackets verliert und spürbar schwächer wird (z. B. der letzte Game Changer geht in Bracket 3) – Bracket-Treue heißt auch „im Bracket maximal stark“.
  - Warnung direkt am Paar und gesammelt bei der Bracket-Zeile: „⚠ Bracket-Wechsel: <Karte> macht aus Bracket X → Y (<Grund>).“ Dazu eine Alternative mit gleicher Rolle, die im Bracket bleibt (`alternativen`), wenn es eine gibt.
  - Claude setzt eine solche Änderung **nicht stillschweigend** um: Im Vorschlag steht die Alternative; der Nutzer entscheidet „Alternative nehmen (Empfehlung) · Karte trotzdem, Ziel-Bracket ändern“. Ändert er das Ziel, gilt der nächste Punkt und die Recherche läuft für die neue Richtung neu (Stufe C).
- **Ziel ≠ Ausgangsbracket:** Der Umbau zielt bewusst auf das neue Bracket – Verschiebungen dorthin sind gewollt und keine Warnung. Die Bracket-Zeile zeigt „Bracket X → Y (Ziel Y)“; gewarnt wird nur, wenn der Entwurf das Ziel überschreitet oder nicht erreicht (z. B. Ziel 3, aber 4 Game Changer; Ziel 2, aber noch ein Game Changer im Deck – er geht raus und wird ersetzt).
- **Neues Deck:** kein Ausgangsbracket; der Wächter prüft jeden Entwurf gegen das Ziel-Bracket (Grundsatz 5).
- Die Abnahme (8a) läuft mit dem Ziel-Bracket.

## 3. Phase 0 – Start

- `protokoll.py zeigen --deck <D>` und `protokoll.py offen` (statt `09`/`10` ganz zu lesen), Soll-Stand bei Bearbeitung (vorgemerkte Karten sind nicht frei).
- Datenbank-Bau (`05a_Sitzungsstart`) **im Hintergrund** starten, sobald Commander bzw. Deck feststeht; die Fragerunden laufen parallel weiter.
- **Bestehendes Deck** → Fragenplan und `passung` (Abschnitt 2b), Upgrade-Katalog (Abschnitt 2a).
- **Commander vorgegeben** → Fragenplan (Abschnitt 2b, inkl. „eigener Commander, der das Thema besser trägt?“), weiter mit Phase 1.
- **Kein Commander** → Idee erfragen (so viele Fragen wie nötig, jede mit „Weiß nicht“): Thema/Mechanik, Farben (oder „egal“), Spielgefühl. Dann:
  - `12_Sammlungsprofil` lesen: welche Archetypen die freien Karten in welchen Farben tragen, welche freien Commander dazu passen
  - `deckbau.py commander-suche --thema <slug> [--farben RWB]` (EDHREC-Top-Commander zum Thema, eigene zuerst)
  - `deckbau.py commander-suche --farben <XY> --nur-besitz` (Commander, die der Nutzer schon besitzt)
  - 3–5 Vorschläge mit Deckzahl, Besitz/frei, Preis und einem Satz zum Spielplan → Nutzer wählt.

## 4. Phase 1 – Rahmen (Pflichtfragen des Fragenplans)

| Frage | Optionen | Standard |
|---|---|---|
| Welcher Weg? | **Weg 1:** nur freie Karten aus der Sammlung · **Weg 2:** Sammlung zuerst, dazu gezielte Kaufvorschläge | fragen; Empfehlung nach Ampel (kann nach Phase 3 wechseln) |
| Ziel-Bracket? (Abschnitt 2c) | Empfehlung · ein Bracket höher · ein Bracket niedriger · „Erst alle Brackets erklären“ (andere per Freitext) | Empfehlung 3 – immer fragen, nie stillschweigend annehmen |
| Budget (nur Weg 2)? | bis 25 € · bis 50 € · bis 100 € · offen, Stufen zeigen | Stufen anbieten |

## 5. Phase 2 – Strategie

Zuerst `deckbau.py commander "<Name>" --bracket <B>` ausführen: Oracle-Text, Profil aus dem Oracle-Text (Ressourcen, Typen), Farbidentität, EDHREC-Themen mit Deckzahlen, Top- und High-Lift-Karten, häufige Combos. Dann `deckbau.py synergie "<Name>"`: freie Karten mit Bezug zum Commander-Text.

**Pflichtfragen**

| Frage | Optionen | Hinweis |
|---|---|---|
| Strategie/Thema? | 2–4 EDHREC-Themen mit Deckzahl + „eigene Idee“ | Empfehlung = Thema, das am besten zum Commander-Text passt, nicht nur das häufigste; je Option den Kurzplan aus `11`, Abschnitt 5 nennen |
| Wie soll das Deck gewinnen? | Kampf/Commander-Schaden · Drain/Aristokraten · Combo (nur bracket-tauglich) · gemischt | mindestens 2 Siegwege einplanen (Siegweg-Daten: `11`, Abschnitt 3.2) |
| Spielstil? | aggressiv · Midrange · kontrollierend | bestimmt Kurve, Länderzahl, Interaktionsmix |

**Bedingte und optionale Fragen** (nur was relevant ist; Abschnitt 2b)
- Pflichtkarten / Lieblingskarten? Karten oder Mechaniken, die er nicht will (Stax, Diebstahl, Infect, Gruppen-Hug …)?
- Game Changer: Sollen die 3 Bracket-3-Slots genutzt werden? (freie Game Changer aus der Sammlung zeigen)
- Spielgruppe: Was spielen die anderen, was nervt? → Bedrohungsprofil (Artefakte, Verzauberungen, Friedhof, große Kreaturen, Combos; Archetypen als Gegner: `11`, Abschnitt 3.6) bestimmt den Interaktionsmix.

## 6. Phase 3 – Steckbrief und Machbarkeit

**Steckbrief** (kurz, zum Bestätigen): Commander · **Deckname** · Bracket · Weg/Budget · Strategie in 2 Sätzen · Siegwege · Kern-Pakete (Engine, Enabler, Payoff, Schutz; Stückzahlen als Ziel aus `11`, Abschnitt 5 – an den Commander anpassen) · Schlüsselfunktionen mit Redundanz (3–4×) · Interaktionsmix · geplante Länderzahl · Game-Changer-Plan · „Plan B“, falls der Commander entfernt wird · typische Fallen des Archetyps (`11`) und wie das Deck sie vermeidet.

**Deckname** (Feld 2 im Namensschema, `05_Datenbank-und-Tools` Abschnitt 6): Precon bzw. Precon-Umbau → Wizards-Name; eigenes Deck → eigener Name. Für eigene Decks 3 Vorschläge passend zu Commander und Strategie als Auswahl anbieten (vorher prüfen, dass kein Vorschlag ein Kartenname ist). Der volle Name darf höchstens **100 Zeichen** haben (Moxfield) → Deckname kurz halten (≈ 25 Zeichen), Strategie als ein Archetyp + ein Thema.

Dann `deckbau.py kandidaten "<Commander>" --weg <1|2> --bracket <B> [--thema <slug>] [--budget]`. Für Weg 1 zusätzlich `archetypen.py karten <archetyp> --farben <WUBRG>`: freie Karten je Paket des Archetyps, auch solche ohne EDHREC-Wert beim Commander.

**Machbarkeitsampel Weg 1** (Einschätzung des Tools aus freien Karten):

| Ampel | Regel | Vorgehen |
|---|---|---|
| GRÜN | Länder, Ramp, Kartenvorteil, gezielte und Massen-Interaktion erreichen das Minimum, ≥ 25 freie Plan-Karten (Oracle-Bezug ≥ 0,33 oder EDHREC-Synergie ≥ 10 %) | bauen |
| GELB | alle Kernrollen ≥ 50 % des Minimums, ≥ 12 Plan-Karten | bauen; Abstriche offen benennen (was fehlt, welche Spielidee leidet) |
| ROT | eine Kernrolle < 50 % oder < 12 Plan-Karten | **nicht bauen.** Lücken konkret nennen und fragen: „Soll ich gezielt nach ergänzenden Karten zum Kauf suchen?“ (→ Weg 2 mit Minimalkäufen) – oder anderen Commander/andere Strategie vorschlagen |

Die Ampel ist ein Startsignal und gilt nur für neue Decks (Upgrades: Abschnitt 2a). Prüfe zusätzlich selbst: Trägt der Pool die gewählte Strategie wirklich? Plan-Karten außerhalb der EDHREC-Liste zeigt `synergie` mit Bezug und Grund – am Oracle-Text bestätigen. Vormerkungen anderer Ideen sind in „frei“ schon abgezogen (`--idee I-nnn` gibt die der eigenen Idee frei).

## 7. Phase 4 – Bauen

Slots in dieser Reihenfolge füllen; Karten mit Doppelrolle bevorzugen. **Richtwert = Archetyp-Richtwert** (`pruefen` zeigt ihn mit Quelle); die Spalte unten ist das Template für Decks ohne Archetyp:

| # | Slot | Richtwert | Worauf achten |
|---|---|---|---|
| 1 | Länder | 38 (35–38) | weniger bei Kurve ≤ 3 und viel Ramp, mehr bei Landfall; ungetappte Länder vor getappten |
| 2 | Ramp | 10–12 | früh (MV ≤ 2) bevorzugen, Fixing in Mehrfarb-Decks |
| 3 | Kartenvorteil | 10–12 | wiederholbare Quellen bevorzugen; Commander als Engine nur mit Augenmaß mitzählen |
| 4 | Gezielte Interaktion | 10–12, davon ≥ 4 Instant-Tempo | Kreatur, Artefakt, Verzauberung abdecken; Friedhof/Counter je nach Spielgruppe |
| 5 | Massen-Interaktion | 3–6 | zur Strategie passend: im Go-wide-Deck zählen symmetrische Kreaturen-Wipes nicht (Grundsatz 15) → einseitige Wipes, Edikte, Resets; Bracket-3-Decks spielen laut Daten meist 2–4 (`11`, Abschnitt 3.1) |
| 6 | Schutz | 2–4 | mehr, wenn der Plan am Commander hängt |
| 7 | Plan/Synergie | Rest | Kern-Pakete des Archetyps mit Redundanz (Stückzahlen: `11`, Abschnitt 5), Karten mit Commander-Bezug (`synergie`), ≥ 2 Siegwege, Antisynergien vermeiden |
| 8 | Manabasis | ≈ 20 Quellen je Hauptfarbe, ≈ 14 Splash | Doppel-Pips früh → mehr Quellen; Standardländer zuletzt |

- **Weg 1:** nur Karten mit `frei ≥ 1` (Kandidaten-CSV, `mtg_db.py suche --nur-frei`, `archetypen.py karten`), ohne in `10` vorgemerkte.
- **Weg 2:** freie Karten zuerst. Kaufen nur, wo es Strategie, Combos, Game-Changer-Slots oder Lücken deutlich verbessert. Je Kauf: Rolle, Wirkung, Preis, günstigere Alternative (`deckbau.py alternativen "<Karte>" --farben <XY>`), Klasse A–D. Combos über `pruefen --combos-fehlend` finden; in Bracket 3 keine 2-Karten-Combos, die früh im Spiel gewinnen (bekannte Paare je Archetyp: `11`, Abschnitt 3.4).
- Entwurf als `entwurf_<commander>.txt` im Moxfield-Format speichern (Commander nach Leerzeile am Ende).

## 8. Phase 5 – Qualitätskontrolle (Pflicht)

`deckbau.py pruefen entwurf_<commander>.txt --bracket <B> [--ersetzt <Deck>] [--combos-fehlend]`

Prüft: 100 Karten, Singleton, Farbidentität, Banlist · Rollen gegen den Richtwert (Archetyp vor Template, mit Quelle) · Instant-Interaktion · Interaktion nach Ziel · nicht mitgezählte Karten mit Grund · Kurve · Farbquellen gegen Pips · Game Changer, MLD, Extra Turns, Combos (Spellbook) → Bracket-Zeile · Besitz (frei/kaufen) mit Kaufliste · Standardländer mit Nachkauf.

Zusätzlich `archetypen.py deck entwurf_<commander>.txt --archetyp <archetyp>`: Kern-Pakete gegen die Mediane der EDHREC-Durchschnittsdecks; ⚠ = Paket unter dem kleinsten Wert der Datenbasis → auffüllen oder begründen (Tag-Zählung ist eine Näherung, Einzelfälle am Oracle-Text prüfen).

Jede Warnung beheben oder mit Grund stehen lassen (Nutzerwunsch, Strategie). Wiederholen, bis das Ergebnis sauber ist. Danach die **Abnahme** (Abschnitt 8a).

**Oracle-Pflicht (Grundsatz 9):** vor dem Vorschlag `deckbau.py oracle --alt <Soll-Stand> --neu <entwurf>` (neues Deck: `oracle` mit den tragenden Karten) und jede Beschreibung im Vorschlag gegen diese Ausgabe prüfen – Kosten, Stärke/Widerstand, Bedingungen, Modi.

---

## 8a. Bracket-3-Abnahme – Definition of Done (V1.6, Review 29.10.2026)

Ein Deck ist erst fertig, wenn es die Abnahme besteht – neu gebaut oder nach einem Upgrade, für jedes Deck gleich. `deckbau.py abnahme <deck|entwurf> [--basis <Soll-Stand>] [--bracket <Ziel>]` prüft acht Punkte (bei einem anderen Ziel-Bracket mit `--bracket <Ziel>`; in Bracket 4–5 sind MLD und Extra Turns erlaubt – ein ✗ in Punkt 2 ist dort nur Hinweis); `fazit` übernimmt die Tabelle ins Fazit-PDF.

| # | Prüfpunkt | bestanden, wenn … |
|---|---|---|
| 1 | Deck legal | 100 Karten, Singleton, Farbidentität, Banlist |
| 2 | Harte Grenzen | ≤ 3 Game Changer, keine Massen-Landzerstörung, keine Extra-Turn-Ketten; 2-Karten-Combos → „offen“ (Claude prüft, ob sie früh gewinnen; dann nicht bestanden) |
| 3 | Rollen auf Richtwert | jede Kernrolle (Länder, Ramp, Kartenvorteil, gezielte und Massen-Interaktion, Schutz) ≥ Minimum des Ziel-Archetyps |
| 4 | Interaktion nach Ziel | Kreatur ≥ 5, Artefakt ≥ 2, Verzauberung ≥ 2, Friedhof ≥ 1 (Einschätzung, vorläufig) |
| 5 | Siegwege | ≥ 2 Siegwege mit konkreten Karten (Kampf/Go-wide, Drain/Aristokraten, Voltron, große Kreaturen, Direktschaden, alternativer Sieg, Mill, Combo) |
| 6 | Kernpakete | jedes Kernpaket ≥ 80 % des Medians |
| 7 | Konsistenz-Simulation | Schwellen aus `05`, Abschnitt 4e (vorläufig) |
| 8 | Messbar stärker | Stärke-Index über dem Ausgangsstand (nur mit `--basis`; neues Deck: „–“) |

- **Urteil:** BESTANDEN · BEDINGT (offene Punkte, Einschätzung nötig) · NICHT BESTANDEN (Punkte mit ✗).
- **Nicht bestanden** heißt nicht „nicht liefern“: Claude bessert nach, wo es mit dem Budget geht, und nennt die offenen Punkte im Vorschlag und im Fazit – mit dem, was sie lösen würde (Kauf mit Klasse, Kompromiss aus der Sammlung). Der Nutzer entscheidet.
- **Stärke-Index:** Mittel aus Rollen-Erfüllung, Kernpaket-Deckung, Ø Wert der Spielkarten (w/(w+0,5)), Ø Commander-Bezug und Simulation – eine Vergleichsgröße zwischen zwei Ständen desselben Decks, kein absolutes Urteil.
- Die Schwellen für Interaktion und Simulation sind vorläufig (aus den Decks des Projekts gemessen) und werden nach weiteren Abnahmen nachgeschärft (Eintrag in `09a`).

## 9. Checkliste: was Spieler oft übersehen (in Phase 4/5 aktiv abhaken)

- zu wenig Ramp oder Ramp erst ab MV 3+
- zu wenig Kartenvorteil, nur einmalige Effekte
- keine Antwort auf Artefakte/Verzauberungen; alles nur mit Sorcery-Tempo
- keine oder zu viele Wipes; Wipes, die den eigenen Plan zerstören (zählen seit V1.6 nicht)
- kein Schutz für einen Commander, von dem alles abhängt; kein Plan B
- nur ein Siegweg; kein Finisher
- Kern-Paket des Archetyps unterbesetzt (z. B. Aristokraten ohne genug Payoffs) – `archetypen.py deck`
- Kurve zu hoch (Ø MV > 3,5) ohne Ausgleich
- zu wenige Farbquellen, zu viele getappte Länder, Doppel-Pips ohne Quellen
- Friedhofs-Hate fehlt, obwohl die Spielgruppe Friedhof spielt
- Bracket-Verstöße: 4. Game Changer, frühe 2-Karten-Combos, MLD, Extra-Turn-Ketten – die Abnahme (8a) prüft sie
- Bracket ungewollt verschoben (Ziel = Ausgangsbracket), z. B. erster Game Changer in Bracket 2, vervollständigte Beinahe-Combo, letzter Game Changer raus – Bracket-Wächter (2c)
- Singleton- oder Farbidentitätsfehler; Karten, die schon in anderen Decks stecken oder in `10` vorgemerkt sind
- Standardländer nicht im Bestand → Nachkauf

---

---

Nach der Freigabe geht es weiter in `08a_Lieferung-Buchen-Gegentest`: Kartenerklärungen, Abschluss, PDFs, Buchen, Gegentest.
