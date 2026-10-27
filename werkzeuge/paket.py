#!/usr/bin/env python3
"""paket.py – Arbeitspakete: Werkzeuge und Daten als je eine Textdatei im Projekt.

Warum: `project_read` liefert Projektdateien als Text in den Chat; einzelne Dateien in den Arbeitsbereich
abzuschreiben kostet viel und ist fehleranfällig. Ein Arbeitspaket ist eine einzige Textdatei
(tar.xz, Base64) mit Prüfsummen. Claude liest sie mit `project_read`; der Startbefehl in
`05_Datenbank-und-Tools`, Abschnitt 2 holt sie aus dem Sitzungsprotokoll und packt sie aus.

Pakete (Projektpfad im Admin-Projekt)
  werkzeuge  claude/pakete/werkzeugkiste.txt – mtg_db.py, deckbau.py, archetypen.py, kartenbilder.py, paket.py,
             archetypen_daten.json (Admin zusätzlich weitergabe.py). Programm – ändert sich selten.
  daten      claude/pakete/datenpaket.txt – Basis + buchungen.csv + vormerkungen.csv, Soll-Stände claude/decks/,
             Entwürfe claude/ideen/*.txt, deck_namen.json. Nach JEDER Schreibrunde in diese Dateien neu packen.

Befehle
  packen --art werkzeuge|daten (--quelle <projektordner> | --arbeit <arbeitsordner>) --out <datei> [--nutzer]
        --quelle: Ordner mit Projektstruktur (claude/…; Nutzer-Kopie: Programm im Stamm).
        --arbeit: ausgepackter Arbeitsordner – Projektpfade kommen aus dessen paket_manifest.json.
  auspacken <paketdatei …> [--ziel /home/claude/mtg]
        Prüft die Prüfsummen und legt an: Werkzeuge in <ziel>/, Bestand in <ziel>/data/, Soll-Stände in
        <ziel>/decks/, Entwürfe in <ziel>/ideen/; schreibt <ziel>/paket_manifest.json (lokal ↔ Projektpfad).
  geaendert [--ziel /home/claude/mtg]
        Welche ausgepackten Dateien seit dem Auspacken geändert oder neu sind → mit Projektpfad, damit Claude
        genau diese mit `project_write` (local_path) zurückschreibt; danach `packen --art daten --arbeit …`.
  liste <paketdatei>
        Kopf und Inhalt eines Pakets anzeigen.
"""
import argparse
import base64
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import time

KENNUNG = "MTG-PAKET"
VERSION = 1
WERKZEUGE = ["mtg_db.py", "deckbau.py", "archetypen.py", "kartenbilder.py", "paket.py", "archetypen_daten.json"]
NUR_ADMIN = ["weitergabe.py"]
ZEILE = 100


def sha(daten):
    return hashlib.sha256(daten).hexdigest()


def lokal_fuer(projektpfad):
    """Projektpfad → Pfad im Arbeitsordner."""
    teile = projektpfad.split("/")
    name = teile[-1]
    if "sammlung" in teile[:-1]:
        return f"data/{name}"
    if "decks" in teile[:-1]:
        return f"decks/{name}"
    if "ideen" in teile[:-1]:
        return f"ideen/{name}"
    return name                                   # Werkzeuge und deck_namen.json in den Stamm


def dateien_daten(quelle):
    """Projektpfade der Daten in einem Ordner mit Projektstruktur."""
    out = []
    for unter, muster in (("claude/sammlung", r".*\.csv$"), ("claude/decks", r".*\.txt$"),
                          ("claude/ideen", r".*\.(txt|md)$")):
        d = os.path.join(quelle, unter)
        if os.path.isdir(d):
            out += [f"{unter}/{f}" for f in sorted(os.listdir(d)) if re.match(muster, f)]
    for kand in ("claude/tools/deck_namen.json", "deck_namen.json"):
        if os.path.exists(os.path.join(quelle, kand)):
            out.append(kand)
            break
    return out


def dateien_werkzeuge(quelle, nutzer):
    out = []
    for name in WERKZEUGE + ([] if nutzer else NUR_ADMIN):
        for kand in (f"claude/tools/{name}", name):
            if os.path.exists(os.path.join(quelle, kand)):
                out.append(kand)
                break
        else:
            if name not in NUR_ADMIN:
                sys.exit(f"fehlt in der Quelle: {name}")
    return out


def cmd_packen(a):
    if bool(a.quelle) == bool(a.arbeit):
        sys.exit("genau eines von --quelle oder --arbeit angeben")
    eintraege = []                               # (Projektpfad, Dateipfad auf der Platte)
    if a.quelle:
        pfade = dateien_daten(a.quelle) if a.art == "daten" else dateien_werkzeuge(a.quelle, a.nutzer)
        eintraege = [(p, os.path.join(a.quelle, p)) for p in pfade]
    else:
        mp = os.path.join(a.arbeit, "paket_manifest.json")
        man = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {"dateien": []}
        bekannt = {m["lokal"]: m["projekt"] for m in man["dateien"] if m["art"] == a.art}
        if a.art == "daten" and not bekannt:      # noch kein Datenpaket (Ersteinrichtung): alles aus data/ nehmen
            man["datendateien"] = [f for f in sorted(os.listdir(os.path.join(a.arbeit, "data")))
                                   if f.endswith(".csv") and not f.startswith("_")] \
                if os.path.isdir(os.path.join(a.arbeit, "data")) else []
            if os.path.exists(os.path.join(a.arbeit, "deck_namen.json")):
                bekannt["deck_namen.json"] = "claude/tools/deck_namen.json"
        if a.art == "daten":                      # neue Dateien (z. B. neuer Soll-Stand, neuer Entwurf) mitnehmen
            praefix = man.get("praefix", "claude/")
            for unter, ziel, muster in (("decks", "decks", r".*\.txt$"), ("data", "sammlung", r".*\.csv$"),
                                        ("ideen", "ideen", r".*\.(txt|md)$")):
                d = os.path.join(a.arbeit, unter)
                for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                    if re.match(muster, f) and f"{unter}/{f}" not in bekannt and not f.startswith("_"):
                        if unter == "data" and f not in (man.get("datendateien") or []):
                            continue              # in data/ nur die Bestandsdateien des Projekts
                        bekannt[f"{unter}/{f}"] = f"{praefix}{ziel}/{f}"
        eintraege = [(p, os.path.join(a.arbeit, l)) for l, p in sorted(bekannt.items(), key=lambda x: x[1])
                     if os.path.exists(os.path.join(a.arbeit, l))]
    if not eintraege:
        sys.exit("keine Dateien gefunden")
    manifest = {"kennung": KENNUNG, "version": VERSION, "art": a.art, "stand": time.strftime("%Y-%m-%d %H:%M"),
                "dateien": []}
    puffer = io.BytesIO()
    with tarfile.open(fileobj=puffer, mode="w:xz", preset=9) as tar:
        for projekt, pfad in eintraege:
            roh = open(pfad, "rb").read()
            manifest["dateien"].append({"projekt": projekt, "bytes": len(roh), "sha256": sha(roh)})
            info = tarfile.TarInfo(projekt)
            info.size, info.mtime = len(roh), int(time.time())
            tar.addfile(info, io.BytesIO(roh))
        m = json.dumps(manifest, ensure_ascii=False, indent=1).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(m)
        tar.addfile(info, io.BytesIO(m))
    roh = puffer.getvalue()
    b64 = base64.b64encode(roh).decode()
    kopf = (f"{KENNUNG} {a.art} v{VERSION} · Stand {manifest['stand']} · {len(eintraege)} Dateien · "
            f"{sum(d['bytes'] for d in manifest['dateien']) // 1024} KB entpackt · sha256 {sha(roh)}")
    inhalt = "Inhalt: " + ", ".join(e[0] for e in eintraege)
    text = "\n".join([kopf, inhalt, "Auspacken: Startbefehl in 05_Datenbank-und-Tools, Abschnitt 2 (nicht von Hand "
                      "abschreiben). Projektdateien bleiben maßgeblich; dieses Paket ist ihre Transportkopie.",
                      "=====BEGIN====="] + [b64[i:i + ZEILE] for i in range(0, len(b64), ZEILE)] + ["=====END====="])
    open(a.out, "w", encoding="utf-8").write(text + "\n")
    print(f"{kopf}\n-> {a.out} ({os.path.getsize(a.out) // 1024} KB Text)")


def lies_paket(text):
    zeilen = text.strip().splitlines()
    if not zeilen or not zeilen[0].startswith(KENNUNG):
        sys.exit("kein MTG-Paket (erste Zeile muss mit MTG-PAKET beginnen)")
    m = re.search(r"sha256 ([0-9a-f]{64})", zeilen[0])
    try:
        b64 = "".join(text.split("=====BEGIN=====")[1].split("=====END=====")[0].split())
    except IndexError:
        sys.exit("Paket unvollständig (BEGIN/END fehlt) – Datei neu lesen")
    roh = base64.b64decode(b64)
    if m and sha(roh) != m.group(1):
        sys.exit("Prüfsumme des Pakets stimmt nicht – Paket beim Lesen abgeschnitten? Neu lesen.")
    tar = tarfile.open(fileobj=io.BytesIO(roh), mode="r:xz")
    manifest = json.load(tar.extractfile("manifest.json"))
    return zeilen[0], tar, manifest


def cmd_auspacken(a):
    os.makedirs(a.ziel, exist_ok=True)
    mpfad = os.path.join(a.ziel, "paket_manifest.json")
    gesamt = json.load(open(mpfad, encoding="utf-8")) if os.path.exists(mpfad) else {"dateien": []}
    for datei in a.pakete:
        kopf, tar, man = lies_paket(open(datei, encoding="utf-8").read())
        gesamt["dateien"] = [d for d in gesamt["dateien"] if d["art"] != man["art"]]
        for d in man["dateien"]:
            roh = tar.extractfile(d["projekt"]).read()
            if sha(roh) != d["sha256"]:
                sys.exit(f"Prüfsumme falsch: {d['projekt']}")
            lokal = lokal_fuer(d["projekt"])
            ziel = os.path.join(a.ziel, lokal)
            os.makedirs(os.path.dirname(ziel) or a.ziel, exist_ok=True)
            open(ziel, "wb").write(roh)
            gesamt["dateien"].append({"art": man["art"], "projekt": d["projekt"], "lokal": lokal,
                                      "sha256": d["sha256"]})
        if man["art"] == "daten":
            gesamt["praefix"] = "claude/"
            gesamt["datendateien"] = [os.path.basename(d["projekt"]) for d in man["dateien"]
                                      if "/sammlung/" in "/" + d["projekt"]]
        gesamt[f"stand_{man['art']}"] = man["stand"]
        print(f"{kopf.split(' · sha256')[0]}\n  -> {len(man['dateien'])} Dateien nach {a.ziel}")
    json.dump(gesamt, open(mpfad, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    basis = [d["lokal"] for d in gesamt["dateien"] if re.search(r"data/moxfield_haves_.*\.csv$", d["lokal"])]
    if basis:
        print("\nDatenbank bauen (im Hintergrund):\n  cd " + a.ziel + " && python3 mtg_db.py build --sammlung "
              + " ".join(basis + (["data/buchungen.csv"] if os.path.exists(os.path.join(a.ziel, "data/buchungen.csv"))
                                  else [])) + " --decks decks/*.txt")


def cmd_geaendert(a):
    man = json.load(open(os.path.join(a.ziel, "paket_manifest.json"), encoding="utf-8"))
    alt = {d["lokal"]: d for d in man["dateien"]}
    geaendert = []
    for lokal, d in sorted(alt.items()):
        p = os.path.join(a.ziel, lokal)
        if not os.path.exists(p):
            geaendert.append(("gelöscht", lokal, d["projekt"]))
        elif sha(open(p, "rb").read()) != d["sha256"]:
            geaendert.append(("geändert", lokal, d["projekt"]))
    for unter, ziel, muster in (("decks", "decks", r".*\.txt$"), ("ideen", "ideen", r".*\.(txt|md)$")):
        d = os.path.join(a.ziel, unter)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if re.match(muster, f) and f"{unter}/{f}" not in alt and not f.startswith("_"):
                geaendert.append(("neu", f"{unter}/{f}", f"{man.get('praefix', 'claude/')}{ziel}/{f}"))
    if not geaendert:
        print("Keine Änderungen gegenüber dem ausgepackten Stand.")
        return
    for art, lokal, projekt in geaendert:
        print(f"{art:9} {os.path.join(a.ziel, lokal)}  ->  {projekt}")
    print("\nZurückschreiben: je Datei project_write(path=<Projektpfad>, local_path=<lokal>); danach das Paket neu "
          "packen (packen --art daten|werkzeuge --arbeit " + a.ziel + " --out …) und ebenfalls schreiben.")


def cmd_liste(a):
    kopf, tar, man = lies_paket(open(a.paket, encoding="utf-8").read())
    print(kopf)
    for d in man["dateien"]:
        print(f"  {d['projekt']:55} {d['bytes']:>8} B  -> {lokal_fuer(d['projekt'])}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("packen")
    p.add_argument("--art", choices=("werkzeuge", "daten"), required=True)
    p.add_argument("--quelle")
    p.add_argument("--arbeit")
    p.add_argument("--out", required=True)
    p.add_argument("--nutzer", action="store_true", help="Nutzer-Kopie: ohne weitergabe.py")
    p = sp.add_parser("auspacken")
    p.add_argument("pakete", nargs="+")
    p.add_argument("--ziel", default="/home/claude/mtg")
    p = sp.add_parser("geaendert")
    p.add_argument("--ziel", default="/home/claude/mtg")
    p = sp.add_parser("liste")
    p.add_argument("paket")
    a = ap.parse_args()
    {"packen": cmd_packen, "auspacken": cmd_auspacken, "geaendert": cmd_geaendert, "liste": cmd_liste}[a.cmd](a)


if __name__ == "__main__":
    main()
