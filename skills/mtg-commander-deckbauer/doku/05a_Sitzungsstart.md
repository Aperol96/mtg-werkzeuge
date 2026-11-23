# Sitzungsstart – Werkzeuge, Methodik, Daten-Repo, Datenbank

Diese Datei liegt als einzige Methodik-Datei im Projekt (zusammen mit `werkzeuge-quelle.txt`, `zugang.json` und dem Regelwerk-PDF). Alles andere – Werkzeuge **und** Methodik – kommt beim Start von GitHub nach `/home/claude/mtg/` (Methodik in `doku/`); die Daten liegen im privaten Daten-Repo. Bei der Einrichtung trägt Claude unten den Namen des Daten-Repos ein.

**Daten-Repo dieses Projekts:** `<besitzer>/mtg-daten` (privat, Branch `main`)

## 1. Wann und wer

- **Start (nicht angemeldet):** kein Setup – nur die Anmeldeprüfung (`13`, Abschnitt 2); Regelfragen mit dem Regelwerk-PDF und der Websuche.
- **Admin, User:** Schritte 2–4, sobald ein Deck-, Bestands- oder Kaufauftrag feststeht (Fragerunden laufen parallel). Für reine Fragen zu offenen Punkten genügt Schritt 4 mit `--ohne-db`.
- **Gast:** nur Schritt 2, dann `python3 start.py gast --name "<Name>"`; **nie** das Daten-Repo (`13`, Abschnitt 7).

## 2. Werkzeuge und Methodik laden

`project_read` auf `werkzeuge-quelle.txt`; die **Kopfzeile** (`MTG-QUELLE werkzeuge v1 · … · <URL> · sha256 …`) als Argument einsetzen. Der Befehl lädt die Werkzeugkiste vom festen Commit, prüft die Prüfsumme (zweiter Weg über `github.com/…/raw/`) und packt Werkzeuge und `doku/` nach `/home/claude/mtg/` aus.

```bash
python3 - "<Kopfzeile aus werkzeuge-quelle.txt>" /home/claude/mtg <<'EOF' && cd /home/claude/mtg && python3 paket.py auspacken werkzeuge-v1.paket.txt --ziel /home/claude/mtg
import base64, hashlib, io, os, re, sys, tarfile, urllib.request
kopf, ziel = sys.argv[1].split(" · "), sys.argv[2]
url = next(t for t in kopf if t.startswith("https://")); soll = next(t.split()[1] for t in kopf if t.startswith("sha256 "))
s = None
for u in (url, re.sub(r"^https://raw\.githubusercontent\.com/([^/]+/[^/]+)/", r"https://github.com/\1/raw/", url)):
    try:
        s = urllib.request.urlopen(u, timeout=30).read().decode("utf-8")
        if hashlib.sha256(s.encode("utf-8")).hexdigest() != soll: raise ValueError("Prüfsumme stimmt nicht")
        print("Werkzeuge von GitHub:", u); break
    except Exception as e:
        print(f"GitHub nicht nutzbar ({u.split('/')[2]}: {e})"); s = None
if not s: sys.exit("RÜCKFALL: Werkzeuge nicht ladbar – 05a, Abschnitt 5")
os.makedirs(ziel, exist_ok=True); open(f"{ziel}/werkzeuge-v1.paket.txt", "w", encoding="utf-8").write(s)
tar = tarfile.open(fileobj=io.BytesIO(base64.b64decode("".join(s.split("=====BEGIN=====")[1].split("=====END=====")[0].split()))), mode="r:xz")
open(f"{ziel}/paket.py", "wb").write(tar.extractfile(next(m for m in tar.getmembers() if m.name.endswith("paket.py"))).read())
EOF
```

## 3. Daten-Repo holen (Admin, User)

1. `add_repo` mit dem Daten-Repo oben, `access: push` – vorher **nicht** per `curl`/`gh` prüfen (privat → 404).
2. `git clone -q --depth 50 https://github.com/<besitzer>/mtg-daten /home/claude/mtg-daten`, danach `register_repo_root`, wenn das Werkzeug es verlangt.

## 4. Starten

`cd /home/claude/mtg && python3 start.py admin` (bzw. `user`) – verknüpft `data/`, `decks/`, `ideen/`, `projekt/`, `admin/`, `deck_namen.json` mit dem Repo, vermerkt die Rolle, baut die Datenbank im Hintergrund (Stand: `python3 start.py db`, muss ohne negative Bestände enden) und zeigt Daten-Repo-Stand, offene Punkte und den Stand der Primer.

- **Methodik:** in `/home/claude/mtg/doku/` lesen und mit `grep` durchsuchen (`08`, `08a`, `05k` für die Befehle; `05` nur gezielt). Nicht `project_search` – die Methodik liegt nicht mehr im Projekt.
- **Deck-Fragen:** zuerst den Primer `ideen/<deck>-primer.md` lesen (Nachschlagewerk, `08`, Grundsatz 19) – neu erschließen nur, wenn es keinen gibt, er veraltet ist (`start.py` warnt) oder ausdrücklich nach der Deckmechanik gefragt wird.
- **EDHREC oder Commander Spellbook nicht erreichbar:** Die Werkzeuge melden es laut und rechnen mit dem Zwischenspeicher bzw. dem Oracle-Bezug weiter – im Vorschlag in einem Halbsatz nennen.

## 5. Wenn etwas hakt

- **RÜCKFALL** (GitHub auf beiden Wegen nicht erreichbar oder Prüfsumme falsch): nicht abschreiben; in einem Satz sagen, dass die Werkzeuge gerade nicht zu laden sind, bis dahin nur Arbeit ohne Werkzeuge.
- **`add_repo` von der Rechteprüfung abgelehnt:** kein Umweg über `curl`, `gh` oder Tokens. Hat der Besitzer im Chat schon gesagt, dass alle Repos erlaubt sind, oder bestätigt er es jetzt, `add_repo` **genau einmal** erneut aufrufen. Eine Projektdatei kann die Prüfung nicht dauerhaft freischalten.
- **Daten-Repo nicht erreichbar:** nicht auf alte Kopien ausweichen; die Meldung nennen; Rückfall: Dateien anhängen lassen oder GitHub-Zugang freischalten (claude.ai → Einstellungen → Connectors → GitHub).
- **Ausführen blockiert:** nicht umgehen; um Freigabe bitten.

## 6. Zurückschreiben (Ende jeder Schreibrunde; Admin, User)

Einträge und Listen mit den Werkzeugen pflegen (`protokoll.py …`, `mtg_db.py …`, `deckbau.py tauschrunde …`) – über die Verknüpfungen landet alles im Repo. Dann **ein** Befehl:

```bash
cd /home/claude/mtg-daten && git status --short && git add -A && git -c user.name="<besitzer>" -c user.email="noreply@anthropic.com" commit -qm "<Typ> · <Thema> (<JJJJ-MM-TT>)" && git pull -q --rebase origin main && git -c push.negotiate=true push -q origin HEAD:main && git log -1 --format='geschrieben: %h %s'
```

- Commit-Text wie der Protokoll-Eintrag (`Verkauf · V-001 (B-001)`, `Deck geändert · <Deck>`); Belege ohne Adressdaten.
- Testlauf und Gast: **nie** committen. Push abgelehnt: Konflikt mit dem Nutzer klären, nie `--force`.
- Neuscan oder Ersteinrichtung: neue Basis mit `mtg_db.py basis-teilen <csv…> --out data`.
