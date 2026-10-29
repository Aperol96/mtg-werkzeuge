# Sitzungsstart – Werkzeuge, Daten, Datenbank

**Stand:** 29.10.2026 (V1.6, ausgelagert aus `05`, Abschnitt 2) · Diese Datei liest Claude zu Beginn jeder Arbeitssitzung; alle Befehle im Detail: `05_Datenbank-und-Tools`.

## 1. Rolle zuerst (`13_Betriebsmodus-und-Weitergabe`)

- **Start:** kein Setup – nur die Anmeldeprüfung (`13`, Abschnitt 2).
- **Admin / User:** Schritte 2–5, danach `python3 zugang.py sitzung admin` bzw. `… sitzung user`.
- **Gast:** in Schritt 2 nur die Werkzeuge – **nie das Datenpaket**; danach `python3 zugang.py sitzung gast --name "<Name>"`, Daten nach `13`, Abschnitt 7 (G2–G4). Kein Zurückschreiben (Schritt 6), am Ende nur das Archiv.
- **Wann:** nicht vor der ersten Frage. Sobald ein Deck- oder Bestandsauftrag feststeht, starten; die Fragerunden laufen parallel (`08`, Abschnitt 2).

## 2. Lesen – nicht abschreiben

`project_read` auf `werkzeugkiste.txt` (in dieser Kopie gibt es keine Werkzeuge-Quelle) und – Admin/User – `claude/pakete/datenpaket.txt` (Basis, Buchungen, Vormerkungen, Soll-Stände, Ideen, `deck_namen.json`, 04/09/10). Arbeit am Programm (nur Admin) oder Rückfall: `werkzeugkiste.txt` statt der Quelle.

| Paket | Inhalt | neu packen, wenn … |
|---|---|---|
| `werkzeugkiste.txt` | `mtg_db.py`, `deckbau.py`, `bewertung.py`, `simulation.py`, `archetypen.py`, `kartenbilder.py`, `protokoll.py`, `paket.py`, `zugang.py`, `archetypen_daten.json`, `projektanweisungen.md` (Admin: + `weitergabe.py`) | ein Werkzeug geändert wurde (nur Admin) |
| `datenpaket.txt` | `claude/sammlung/` (Basis `basis.csv`, `buchungen.csv`, `vormerkungen.csv`), `claude/decks/`, `claude/ideen/`, `deck_namen.json`, `04_Deckregister`, `09_Aenderungsprotokoll`, `10_Geplante-Kaeufe-und-Ideen` | nach **jeder** Schreibrunde (Admin, User) |

Die Projektdateien bleiben maßgeblich; die Pakete sind ihre Transportkopie und werden in derselben Schreibrunde nachgezogen.

## 3. Startbefehl (genau so ausführen)

Holt die gelesenen Pakete aus dem Sitzungsprotokoll (ohne gelesene Werkzeugkiste die Werkzeuge von GitHub), prüft die Prüfsummen und packt nach `/home/claude/mtg/` aus: Werkzeuge in den Stamm, Bestand nach `data/`, Soll-Stände nach `decks/`, Ideen nach `ideen/`, 04/09/10 nach `projekt/`.

```bash
python3 - <<'EOF' && cd /home/claude/mtg && python3 paket.py auspacken *.paket.txt
import base64, glob, hashlib, io, json, os, sys, tarfile, urllib.request
ziel, pakete, quelle = "/home/claude/mtg", {}, []
def merke(s):                               # nur vollständige Pakete/Quellen – keine Bildschirmausgaben wie von auspacken
    if s.startswith("MTG-PAKET") and "=====BEGIN=====" in s and "=====END=====" in s: pakete[s.split()[1]] = s
    elif s.startswith("MTG-QUELLE") and " · sha256 " in s.split("\n")[0]: quelle[:] = [s]
for f in sys.argv[1:]:                      # Fallback: project_read hat Paket oder Quelle als Datei abgelegt
    merke(open(f, encoding="utf-8").read())
for f in sorted(glob.glob(os.path.expanduser("~/.claude/projects/**/*.jsonl"), recursive=True), key=os.path.getmtime):
    for zeile in open(f, encoding="utf-8", errors="replace"):
        if "MTG-PAKET" not in zeile and "MTG-QUELLE" not in zeile:
            continue
        try:
            teile = json.loads(zeile)["message"]["content"]
        except Exception:
            continue
        for t in teile if isinstance(teile, list) else []:
            inh = t.get("content") if isinstance(t, dict) else None
            for s in [inh] if isinstance(inh, str) else [x.get("text", "") for x in inh or [] if isinstance(x, dict)]:
                try:
                    s = json.loads(s).get("content", "")
                except Exception:
                    pass
                if isinstance(s, str):
                    merke(s)
if "werkzeuge" not in pakete and quelle:   # Werkzeuge von GitHub: fester Stand (Commit) + Prüfsumme
    kopf = quelle[0].split("\n")[0].split(" · ")
    url = next(t for t in kopf if t.startswith(("https://", "http://")))
    soll = next(t.split()[1] for t in kopf if t.startswith("sha256 "))
    try:
        s = urllib.request.urlopen(url, timeout=30).read().decode("utf-8")
        if hashlib.sha256(s.encode("utf-8")).hexdigest() != soll or not s.startswith("MTG-PAKET werkzeuge"):
            raise ValueError("Prüfsumme stimmt nicht")
        pakete["werkzeuge"] = s
        print("Werkzeuge von GitHub:", url)
    except Exception as e:
        print(f"GitHub nicht nutzbar ({e})")
if "werkzeuge" not in pakete:
    sys.exit("RÜCKFALL: werkzeugkiste.txt mit project_read lesen, dann den Startbefehl erneut ausführen.")
os.makedirs(ziel, exist_ok=True)
for art, s in pakete.items():
    open(f"{ziel}/{art}.paket.txt", "w", encoding="utf-8").write(s)
w = pakete["werkzeuge"]
tar = tarfile.open(fileobj=io.BytesIO(base64.b64decode("".join(w.split("=====BEGIN=====")[1].split("=====END=====")[0].split()))), mode="r:xz")
open(f"{ziel}/paket.py", "wb").write(tar.extractfile(next(m for m in tar.getmembers() if m.name.endswith("paket.py"))).read())
print("Pakete:", ", ".join(pakete))
EOF
```

- **Ohne Sitzungsprotokoll** (anderer Arbeitsbereich) oder wenn `project_read` den Inhalt als lokale Datei ablegt (großer Text): die Pfade hinten an `python3 -` anhängen (`python3 - /pfad/zur/datei … <<'EOF'`) – der Befehl liest dann diese Dateien. Erst wenn auch das nicht geht: Dateien einzeln lesen (nur die nötigen) und im Protokoll vermerken.
- **„RÜCKFALL“** (GitHub nicht erreichbar oder Prüfsumme falsch): Werkzeugkiste lesen, Befehl erneut ausführen.
- **Falsche Prüfsumme beim Auspacken:** die Leseausgabe war abgeschnitten → Paket erneut lesen.

## 4. Datenbank bauen (im Hintergrund)

`cd /home/claude/mtg && python3 mtg_db.py build --sammlung data/basis.csv data/buchungen.csv --decks decks/*.txt` (≈ 20–60 s inkl. Scryfall-Download ≈ 110 MB; `auspacken` gibt den Befehl aus).

- Hinweise des Baus prüfen (z. B. „Commander erkannt – bitte bestätigen“, „Deckname fehlt“). Die Zuordnung der Soll-Stände läuft über `deck_namen.json`.
- Kontrolle: `python3 mtg_db.py sql "SELECT name, SUM(qty) FROM collection GROUP BY oracle_id HAVING SUM(qty) < 0"` muss leer sein; die Zeile „Exemplare: …“ kommt ohne „abweichende Frei-Zählung“ aus (Ausnahme: ein Deck braucht mehr Exemplare, als da sind).
- **EDHREC oder Commander Spellbook nicht erreichbar:** Die Werkzeuge melden das laut („!! EDHREC nicht erreichbar …“) und rechnen mit dem Zwischenspeicher (mit Datum) bzw. nur mit dem Oracle-Bezug weiter. Im Vorschlag in einem Halbsatz nennen.

## 5. Was gerade offen ist – ohne 04/09/10 ganz zu lesen

- `python3 protokoll.py offen [--deck <Deck>]` – Ideen, geplante Verkäufe, Kaufliste, Vormerkungen, „In Moxfield nachziehen“
- `python3 protokoll.py zeigen --deck <Deck>` – die Einträge zu diesem Deck (neueste zuerst); `--typ`, `--suche`, `--letzte N`
- `python3 protokoll.py register --deck <Deck>` – Zeile im Deckregister · Soll-Stand: `decks/<deckname>.txt`
- Schnellabfrage „Habe ich X frei?“: `python3 mtg_db.py frei "<Karte>" …` (Besitz, Decks, vorgemerkt, Verkauf geplant, frei)

## 6. Zurückschreiben (Ende jeder Schreibrunde; Admin, User)

1. Einträge und Listen mit dem Werkzeug pflegen: `protokoll.py neu …` (09), `idee-neu`, `idee-status`, `idee-entfernen`, `nachziehen`, `nachziehen-erledigt` (10). Das Deckregister (04) nach einem Bau bzw. Abgleich direkt in `projekt/04_Deckregister.md` ändern.
2. `python3 paket.py geaendert` → je Datei `project_write(path=<Projektpfad>, local_path=<lokal>)` – der Inhalt läuft nicht durch den Chat.
3. `python3 paket.py packen --art daten --arbeit /home/claude/mtg --out datenpaket.txt` → `project_write(path="claude/pakete/datenpaket.txt", local_path=…)`.
4. Werkzeuge geändert (nur Admin): `05`, Abschnitt 9.
