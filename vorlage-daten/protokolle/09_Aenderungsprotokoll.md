# Änderungsprotokoll

Roter Faden über alle Chats: Was hat sich an Bestand und Decks geändert, und warum? **Neueste Einträge oben.**

---

## Regeln (für Claude)

**Datenhoheit:** Das private Daten-Repo ist die Hauptdatenbank. Bestand = Basis (`sammlung/basis-a-d.csv` … `basis-s-z.csv`) + `sammlung/buchungen.csv`; Decks = Soll-Stände in `decks/`. Moxfield wird nur nachgezogen (Repo → Moxfield), ManaBox liefert Scans. Moxfield-Exporte wirken hier nur bei Fehlerkorrektur oder wenn der Nutzer sie ausdrücklich zum Überschreiben nutzt.

**Lesen und schreiben:** `protokoll.py zeigen --deck <D>` (oder `--typ`, `--suche`, `--letzte N`) – nicht die ganze Datei; schreiben mit `protokoll.py neu --typ <Typ> --thema <Deck/Thema> --zeile "…"`, danach `git push` (`05a`, Abschnitt 6).

**Wann ein Eintrag:** am Ende jeder Aufgabe, die Bestand, Decks oder Entscheidungen verändert:

| Typ | Anlass |
|---|---|
| Kauf | Zugang gebucht (`buchungen.csv`, Beleg) bzw. Kaufliste beschlossen |
| Verkauf | Abgang gebucht (`buchungen.csv`, Beleg) |
| Import | ManaBox-Scan als Zugang gebucht; Moxfield-Export als neue Basis (nur auf ausdrücklichen Wunsch) |
| Abgleich | Abweichung zwischen Scan/Export und Soll-Stand bzw. Bestand geklärt |
| Deck neu | Deck nach `08_Deckbau-Verfahren` freigegeben und vom Nutzer physisch gebaut |
| Deck geändert | Upgrade, Tausch, Korrektur – nach Freigabe und physischem Aufbau |
| Idee | Vorschlag ohne Freigabe – Eintrag in `10_Geplante-Kaeufe-und-Ideen` (Details in `ideen/`), Soll-Stand bleibt unverändert |
| Entscheidung | Festlegung mit Folgen (Bracket, Format, Deck zerlegt, Regel zum Bestand, Namen) |
| Hinweis | Hinweis eines Users an den Admin (Problem oder Widerspruch im Programm, `13_Betriebsmodus-und-Weitergabe`, Abschnitt 4) |
| Werkzeug | Änderung an Tools/Verfahren – nur im Admin-Projekt (Programm-Protokoll des Admins) |

**Kein Eintrag** für reine Fragen, Regelfragen, Kartensuchen ohne Folgen, Datenbank-Neubau, reine Analysen – und nie für Gast-Sitzungen (Name, PIN und Daten eines Gastes stehen nicht im Protokoll). Einträge schreiben Admin und User.

**Format** (knapp, eine Zeile je Punkt):

```
### JJJJ-MM-TT · Typ · Deckname/Thema
- raus (n): …  /  rein (n): …            (bei Deckänderungen)
- Buchung: B-nnn …                        (bei Bestandsänderungen)
- Grund: …
- Bracket: vorher → nachher; Abnahme: …   (wenn betroffen)
- Status: umgesetzt | umgesetzt – in Moxfield nachziehen | offen: …
```

**Soll-Stand der Decks:** `decks/<deckname>.txt` = maßgebliche Deckliste (Moxfield-Format, mit `// Commander`-Markierung). Freigabe, „gebaut“ und Neuscan: `08a`, Abschnitte 2 und 4; `05`, Abschnitt 2.

**Bestand:** jede Änderung als Zeile in `buchungen.csv` (ID `B-nnn`, Art, Datum, Beleg); danach Moxfield-Übernahme in `10` vermerken. Ein Moxfield-Rückexport ist nicht nötig; Claude fragt nicht danach.

**Pflege:** Einträge nur mit `protokoll.py neu`. Wird die Datei zu lang (≈ 300 Einträge oder Jahreswechsel): ältere Einträge nach `09_Aenderungsprotokoll_<Jahr>.md` verschieben.

---

---

## Einträge
