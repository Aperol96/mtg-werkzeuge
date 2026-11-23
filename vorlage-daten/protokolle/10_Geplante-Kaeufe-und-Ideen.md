# Geplante Käufe / Ideen

Zentrale Liste über alle Chats: Ideen ohne Freigabe, freigegebene Decks bis zum Aufbau, geplante Verkäufe, offene Übernahmen nach Moxfield. **Kaufliste** und **Vormerkungen** stehen nicht hier, sondern nur in `sammlung/kaufliste.csv` und `sammlung/vormerkungen.csv` (eine Quelle, gepflegt mit `protokoll.py`). Ablauf: `08` (Stufen A–F), `08a` (Freigabe, Buchen).

## Regeln (für Claude)

- **Lesen:** `protokoll.py offen [--deck D]` – nie die ganze Datei. **Schreiben:** nur mit `protokoll.py` (`idee-neu`, `idee-status`, `idee-entfernen`, `kauf-neu`, `kauf-status`, `kauf-entfernen`, `vormerken`, `vormerkung-entfernen`, `nachziehen`, `nachziehen-erledigt`), danach `git push` (`05a`, Abschnitt 6).
- **Wann eine Idee entsteht:** endet ein Chat ohne Freigabe → „wartet auf Freigabe“; mit der Freigabe → „freigegeben – Aufbau offen“. Je Idee eine ID `I-nnn`; Details in `ideen/<deck>-<thema>.md`, ab Freigabe der Entwurf als `ideen/<deck>-<thema>.txt`. Gibt es zum Deck schon eine offene Idee, diese aktualisieren.
- **Status (feste Werte, Zusatz nach „ · “):** Ideen `wartet auf Freigabe` · `freigegeben – Aufbau offen` · `teilweise gebaut` · `bestellt – Ankunft offen` · `gebaut – Buchen offen` · `zurückgestellt`; Verkäufe `geplant` · `eingestellt` · `teilweise verkauft`; Kaufzeilen `geplant` · `bestellt` · `angekommen`.
- **Vormerkungen** sperren freie Karten bis zum Buchen (`mtg_db.py` zieht sie ab und meldet Konflikte). Geplante Verkäufe (`V-nnn`) sind weiche Vormerkungen: Karten bleiben frei, die Werkzeuge zeigen „Verkauf geplant“.
- **Sammelbestellung:** `kartenbilder.py einkauf --kaufliste data/kaufliste.csv --ideen projekt/10_Geplante-Kaeufe-und-Ideen.md` (nur „geplant“); Preise vor der Bestellung neu prüfen. Nach der Bestellung `kauf-status … bestellt`, bei Ankunft Zugang buchen und `kauf-entfernen`.
- **Gebaut / verkauft / verworfen:** buchen nach `08a`, Abschnitt 4; dann `idee-entfernen` (entfernt auch Kaufzeilen und Vormerkungen). Ohne Hinweis des Nutzers wird nichts entfernt. Erledigtes steht nur noch in `09`.
- **In Moxfield nachziehen:** jede Buchung erzeugt eine Zeile, bis der Nutzer das Nachziehen meldet.

## Offene Ideen

| ID | Datum | Deck / Vorhaben | Inhalt | Status | Details |
|---|---|---|---|---|---|

## Geplante Verkäufe (weich vorgemerkt – Karten bleiben frei)

| ID | Datum | Inhalt | Summe (Stand) | Status | Details |
|---|---|---|---|---|---|

## In Moxfield nachziehen / Wartung

| Seit | Was | Aufgabe |
|---|---|---|
| – | derzeit nichts offen | – |
