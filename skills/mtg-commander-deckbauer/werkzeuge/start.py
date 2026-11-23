#!/usr/bin/env python3
"""start.py – Sitzungsstart in einem Befehl (05a): Daten-Repo verknüpfen, Rolle vermerken, Datenbank im Hintergrund
bauen, Stand zeigen (Daten-Repo, offene Punkte, Primer).

Voraussetzung: Werkzeugkiste in /home/claude/mtg ausgepackt (Startbefehl aus 05a); Admin/User: Daten-Repo nach
/home/claude/mtg-daten geklont (add_repo + git clone, 05a). Gast: kein Daten-Repo – Daten aus seinen Uploads (13, G2).

  python3 start.py admin|user [--daten /home/claude/mtg-daten] [--ohne-db]
  python3 start.py gast --name "<Name>"
  python3 start.py db            Stand des Datenbank-Baus (Ende des Protokolls, Prüfung negativer Bestände)
"""
import argparse
import glob
import os
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
LOG = "/tmp/mtg_build.log"
VERKNUEPFUNG = [("data", "sammlung"), ("decks", "decks"), ("ideen", "ideen"), ("projekt", "protokolle"),
                ("admin", "admin"), ("deck_namen.json", "deck_namen.json")]


def lauf(*befehl, still=False):
    r = subprocess.run([sys.executable, *befehl], cwd=HIER, capture_output=True, text=True)
    if not still:
        print((r.stdout + r.stderr).rstrip())
    return r


def verknuepfen(daten):
    for lokal, repo in VERKNUEPFUNG:
        ziel, quelle = os.path.join(HIER, lokal), os.path.join(daten, repo)
        if not os.path.exists(quelle):
            continue
        if os.path.islink(ziel) or os.path.isfile(ziel):
            os.remove(ziel)
        elif os.path.isdir(ziel):
            import shutil
            shutil.rmtree(ziel)
        os.symlink(quelle, ziel)
    r = subprocess.run(["git", "-C", daten, "log", "-1", "--format=%h %cs %s"], capture_output=True, text=True)
    print(f"Daten-Repo: {r.stdout.strip() or '(kein Git-Stand)'}")


def db_bauen():
    basis = sorted(glob.glob(os.path.join(HIER, "data", "basis*.csv")))
    if not basis:
        print("Datenbank: keine Basis-Dateien in data/ – Bau übersprungen")
        return
    befehl = [sys.executable, "mtg_db.py", "build", "--sammlung", *[os.path.relpath(b, HIER) for b in basis]]
    if os.path.exists(os.path.join(HIER, "data", "buchungen.csv")):
        befehl.append("data/buchungen.csv")
    decks = sorted(glob.glob(os.path.join(HIER, "decks", "*.txt")))
    if decks:
        befehl += ["--decks", *[os.path.relpath(d, HIER) for d in decks]]
    with open(LOG, "w") as log:
        subprocess.Popen(befehl, cwd=HIER, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    print(f"Datenbank: Bau läuft im Hintergrund (≈ 15–60 s) – Stand: python3 start.py db · Protokoll {LOG}")


def db_stand():
    if not os.path.exists(LOG):
        sys.exit("kein Bau gestartet")
    text = open(LOG, encoding="utf-8", errors="replace").read().strip().splitlines()
    print("\n".join(text[-8:]))
    if os.path.exists(os.path.join(HIER, "mtg.sqlite")) and any("Exemplare:" in z for z in text):
        r = lauf("mtg_db.py", "sql", "SELECT name, SUM(qty) FROM collection GROUP BY oracle_id HAVING SUM(qty) < 0",
                 still=True)
        neg = [z for z in r.stdout.splitlines() if z.strip() and not z.startswith(("name", "-"))]
        print("Prüfung negativer Bestände: " + ("ok" if not neg else "⚠ " + "; ".join(neg[:5])))
    else:
        print("… Bau läuft noch")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rolle", choices=["admin", "user", "gast", "db"])
    ap.add_argument("--name", help="Gast: Name")
    ap.add_argument("--daten", default="/home/claude/mtg-daten", help="Ordner des geklonten Daten-Repos")
    ap.add_argument("--ohne-db", action="store_true", help="Datenbank nicht bauen (reine Fragen zu offenen Punkten)")
    a = ap.parse_args(argv)
    if a.rolle == "db":
        return db_stand()
    if a.rolle == "gast":
        if not a.name:
            sys.exit("Gast braucht --name")
        lauf("zugang.py", "sitzung", "gast", "--name", a.name)
        print("Gast: kein Daten-Repo; Daten aus seinen Uploads einrichten (13, G2–G4), dann mtg_db.py build")
        return
    if not os.path.isdir(os.path.join(a.daten, ".git")):
        sys.exit(f"Daten-Repo fehlt unter {a.daten} – add_repo und git clone (05a, Abschnitt 3)")
    verknuepfen(a.daten)
    lauf("zugang.py", "sitzung", a.rolle)
    if not a.ohne_db:
        db_bauen()
    print(f"Methodik: {os.path.join(HIER, 'doku')} (lesen und durchsuchen dort, nicht im Projekt)")
    print("\n— Offen —")
    lauf("protokoll.py", "offen")
    print("\n— Primer (Nachschlagewerk je Deck) —")
    lauf("protokoll.py", "primer")


if __name__ == "__main__":
    main()
