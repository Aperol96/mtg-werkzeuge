#!/usr/bin/env python3
"""paket.py – Arbeitspakete: Werkzeuge und Daten als je eine Textdatei im Projekt.

Warum: `project_read` liefert Projektdateien als Text in den Chat; einzelne Dateien in den Arbeitsbereich
abzuschreiben kostet viel und ist fehleranfällig. Ein Arbeitspaket ist eine einzige Textdatei
(tar.xz, Base64) mit Prüfsummen. Claude liest sie mit `project_read`; der Startbefehl in
`05a_Sitzungsstart` holt sie aus dem Sitzungsprotokoll und packt sie aus.

Pakete (Projektpfad im Admin-Projekt)
  werkzeuge  claude/pakete/werkzeugkiste.txt – mtg_db.py, deckbau.py, bewertung.py, simulation.py, archetypen.py,
             kartenbilder.py, protokoll.py, paket.py, zugang.py, archetypen_daten.json, projektanweisungen.md
             (Admin zusätzlich weitergabe.py). Programm – ändert sich selten.
  daten      claude/pakete/datenpaket.txt (Teil „haupt“) + claude/pakete/datenpaket-basis.txt (Teil „basis“).
             haupt: buchungen.csv, vormerkungen.csv, Soll-Stände claude/decks/, Entwürfe claude/ideen/, deck_namen.json
             und die Listen 04, 09, 10 (nach projekt/, gelesen und gepflegt mit protokoll.py).
             basis: die Basis claude/sammlung/basis-*.csv (ändert sich nur bei Neuscan oder Ersteinrichtung).
             Seit 08.11.2026 (V1.9.6): Jeder Teil ist höchstens GRENZE Zeichen groß – sonst Folgeteile -2, -3 …
             (gleiche Prüfsumme, Kopf „Teil <gruppe> i/n“). Grund: project_write mit local_path nimmt nur Dateien,
             die Claude in einem Lesevorgang ganz gelesen hat. Unveränderte Teile schreibt packen nicht neu.
             Nach JEDER Schreibrunde neu packen.
  gast       claude/gaeste/<slug>.txt – Archiv eines Gastes (13_Betriebsmodus-und-Weitergabe): seine Bestandsdateien,
             Soll-Stände, Entwürfe, deck_namen.json, gast_profil.json; im Kopf Name und PIN-Hash. Wird nur nach
             richtiger PIN ausgepackt und ist nie Teil des Bestands des Projekts.

Sitzungsrolle: Liegt <ziel>/SITZUNG.json (zugang.py sitzung …), sperrt paket.py, was die Rolle nicht darf:
  gast – kein Datenpaket auspacken oder packen, kein `geaendert` (nichts ins Projekt), keine Werkzeuge packen;
  user – keine Werkzeuge packen (Programm gesperrt).

Befehle
  packen --art werkzeuge|daten (--quelle <projektordner> | --arbeit <arbeitsordner>) --out <datei> [--nutzer]
        --quelle: Ordner mit Projektstruktur (claude/…; Nutzer-Kopie: Programm im Stamm).
        --arbeit: ausgepackter Arbeitsordner – Projektpfade kommen aus dessen paket_manifest.json.
  packen --art gast --arbeit <arbeitsordner> --name <Name> --pin-hash <Hash aus zugang.py pin-hash> --out <datei>
        Gast-Archiv aus dem Arbeitsordner (data/*.csv, decks/*.txt, ideen/*, deck_namen.json, gast_profil.json).
  auspacken <paketdatei …> [--ziel /home/claude/mtg] [--pin <PIN>]
        Setzt Teile („Teil <gruppe> i/n“) zusammen, prüft die Prüfsummen und legt an: Werkzeuge in <ziel>/, Bestand in <ziel>/data/, Soll-Stände in
        <ziel>/decks/, Entwürfe in <ziel>/ideen/, 04/09/10 in <ziel>/projekt/; schreibt <ziel>/paket_manifest.json
        (lokal ↔ Projektpfad).
        Ein Gast-Archiv wird nur mit richtiger --pin ausgepackt (sonst übersprungen).
  holen --art <art> --out <datei>
        Das zuletzt mit project_read gelesene vollständige Paket dieser Art aus dem Sitzungsprotokoll als Datei
        ablegen (z. B. ein Gast-Archiv vor der PIN-Prüfung).
  geaendert [--ziel /home/claude/mtg]
        Welche ausgepackten Dateien seit dem Auspacken geändert oder neu sind → mit Projektpfad, damit Claude
        genau diese mit `project_write` (local_path) zurückschreibt; danach `packen --art daten --arbeit …`.
  liste <paketdatei …>
        Kopf und Inhalt eines Pakets anzeigen (Teile eines Datenpakets zusammen angeben).
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
WERKZEUGE = ["mtg_db.py", "deckbau.py", "bewertung.py", "simulation.py", "archetypen.py", "kartenbilder.py",
             "protokoll.py", "paket.py", "zugang.py", "archetypen_daten.json", "projektanweisungen.md"]
LISTEN = ["04_Deckregister.md", "09_Aenderungsprotokoll.md", "10_Geplante-Kaeufe-und-Ideen.md"]   # im Datenpaket
NUR_ADMIN = ["weitergabe.py"]
ZEILE = 100
GRENZE = 30000                                   # Zeichen je Teil eines Datenpakets (ein Lesevorgang, mit Puffer)
BASIS = re.compile(r"(^|/)(sammlung|data)/(basis[^/]*|moxfield_haves_[^/]*)\.csv$")


def sha(daten):
    return hashlib.sha256(daten).hexdigest()


def rolle(ziel):
    """Rolle der Sitzung aus SITZUNG.json (zugang.py sitzung) – im Zielordner, im aktuellen Ordner oder im
    Standard-Arbeitsbereich; None = nicht vermerkt."""
    for ort in (ziel, os.getcwd(), "/home/claude/mtg"):
        p = os.path.join(ort or ".", "SITZUNG.json")
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8")).get("rolle")
    return None


def sperre(ziel, verboten, was):
    r = rolle(ziel)
    if r in verboten:
        sys.exit(f"Gesperrt in der Rolle „{r}“: {was} (13_Betriebsmodus-und-Weitergabe, Rechte je Zustand).")


def dateien_gast(arbeit):
    """(Projektpfad im Archiv, lokaler Pfad) für ein Gast-Archiv."""
    out = []
    for unter, ziel, muster in (("data", "sammlung", r".*\.csv$"), ("decks", "decks", r".*\.txt$"),
                                ("ideen", "ideen", r".*\.(txt|md)$")):
        d = os.path.join(arbeit, unter)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if re.match(muster, f) and not f.startswith("_"):
                out.append((f"gast/{ziel}/{f}", f"{unter}/{f}"))
    for f in ("deck_namen.json", "gast_profil.json"):
        if os.path.exists(os.path.join(arbeit, f)):
            out.append((f"gast/{f}", f))
    return out


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
    if name in LISTEN:
        return f"projekt/{name}"                  # 04/09/10 – protokoll.py liest und pflegt sie dort
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
    for name in LISTEN:
        for kand in (f"claude/{name}", name):
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
    ort = a.arbeit or a.quelle
    if a.art == "werkzeuge":
        sperre(ort, ("gast", "user", "start"), "Werkzeuge packen – das Programm ändert nur der Admin")
    if a.art == "daten":
        sperre(ort, ("gast", "start"), "Datenpaket packen – Gäste arbeiten nur mit ihren eigenen Dateien")
    if a.art == "gast":
        sperre(ort, ("user", "start"), "Gast-Archiv packen")
        if not a.arbeit or not a.name or not a.pin_hash:
            sys.exit("--art gast braucht --arbeit, --name und --pin-hash")
        if not re.fullmatch(r"pbkdf2_sha256\$\d+\$[0-9a-f]+\$[0-9a-f]{64}", a.pin_hash):
            sys.exit("--pin-hash: Ausgabe von zugang.py pin-hash erwartet")
    eintraege = []                               # (Projektpfad, Dateipfad auf der Platte)
    if a.art == "gast":
        eintraege = [(p, os.path.join(a.arbeit, l)) for p, l in dateien_gast(a.arbeit)]
    elif a.quelle:
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
                        if unter == "data" and f not in (man.get("datendateien") or []) \
                                and not BASIS.search(f"data/{f}"):
                            continue              # in data/ nur die Bestandsdateien des Projekts (und neue Basis-Teile)
                        bekannt[f"{unter}/{f}"] = f"{praefix}{ziel}/{f}"
            for f in LISTEN:                      # 04/09/10 (z. B. nach der Ersteinrichtung in projekt/ abgelegt)
                if os.path.exists(os.path.join(a.arbeit, "projekt", f)) and f"projekt/{f}" not in bekannt:
                    bekannt[f"projekt/{f}"] = f"{praefix}{f}"
        eintraege = [(p, os.path.join(a.arbeit, l)) for l, p in sorted(bekannt.items(), key=lambda x: x[1])
                     if os.path.exists(os.path.join(a.arbeit, l))]
    if not eintraege:
        sys.exit("keine Dateien gefunden")
    if a.art != "daten":
        extra = ""
        if a.art == "gast":                       # Name und PIN-Hash im Kopf (PIN-Prüfung ohne Auspacken)
            extra = f" · gast {slug_von(a.name)} · name {a.name.replace(' · ', ' ')} · pin {a.pin_hash}"
        b64, manifest, roh = baue_tar(a.art, eintraege)
        kopf = (f"{KENNUNG} {a.art} v{VERSION} · Stand {manifest['stand']} · {len(eintraege)} Dateien · "
                f"{sum(d['bytes'] for d in manifest['dateien']) // 1024} KB entpackt{extra} · sha256 {sha(roh)}")
        open(a.out, "w", encoding="utf-8").write(paket_text(kopf, eintraege, b64))
        print(f"{kopf}\n-> {a.out} ({os.path.getsize(a.out) // 1024} KB Text)")
        if a.art == "gast" and os.path.getsize(a.out) > GRENZE:
            print(f"Hinweis: Archiv größer als {GRENZE // 1000} KB – Zurückschreiben nur nach vollständigem Lesen "
                  "(05a, Abschnitt 6).")
        return
    # Datenpaket: Teil „basis“ (Basis-Dateien) und „haupt“ (alles andere), jeder Teil höchstens GRENZE Zeichen
    stamm = a.out[:-4] if a.out.endswith(".txt") else a.out
    ort = os.path.dirname(os.path.abspath(a.out))
    gruppen = {"haupt": [e for e in eintraege if not BASIS.search(e[0])],
               "basis": [e for e in eintraege if BASIS.search(e[0])]}
    print("Datenpaket – zurückschreiben mit project_write(path=<Projektpfad>, local_path=<Datei>):")
    for gruppe, teil in gruppen.items():
        if not teil:
            continue
        name = os.path.basename(stamm) + ("" if gruppe == "haupt" else f"-{gruppe}")
        inhalt = sha(json.dumps(sorted((p, sha(open(f, "rb").read())) for p, f in teil)).encode())[:16]
        alt = vorhandener_teil(a.art, gruppe, [os.path.join(ort, name + ".txt"), (a.arbeit or ".")])
        if alt == inhalt:
            print(f"  unverändert  claude/pakete/{name}.txt – nicht zurückschreiben")
            continue
        b64, manifest, roh = baue_tar(a.art, teil)
        stuecke = teile_text(b64, kopf_laenge=400 + 60 * len(teil))
        for i, stueck in enumerate(stuecke, 1):
            datei = os.path.join(ort, name + ("" if i == 1 else f"-{i}") + ".txt")
            kopf = (f"{KENNUNG} {a.art} v{VERSION} · Teil {gruppe} {i}/{len(stuecke)} · Stand {manifest['stand']} · "
                    f"{len(teil)} Dateien · {sum(d['bytes'] for d in manifest['dateien']) // 1024} KB entpackt · "
                    f"inhalt {inhalt} · sha256 {sha(roh)}")
            open(datei, "w", encoding="utf-8").write(paket_text(kopf, teil if i == 1 else [], stueck))
            print(f"  neu          claude/pakete/{os.path.basename(datei)}  <-  {datei} "
                  f"({os.path.getsize(datei) // 1024} KB)")
        for i in range(len(stuecke) + 1, 10):     # Folgeteile eines früheren, größeren Stands
            if os.path.exists(os.path.join(ort, f"{name}-{i}.txt")):
                os.remove(os.path.join(ort, f"{name}-{i}.txt"))
                print(f"  überzählig   claude/pakete/{name}-{i}.txt – im Projekt löschen (project_delete)")


def baue_tar(art, eintraege):
    """-> (Base64-Text, Manifest, Rohdaten) eines tar.xz mit den Einträgen (Projektpfad, Datei)."""
    manifest = {"kennung": KENNUNG, "version": VERSION, "art": art, "stand": time.strftime("%Y-%m-%d %H:%M"),
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
    return base64.b64encode(roh).decode(), manifest, roh


def paket_text(kopf, eintraege, b64):
    zeilen = [kopf]
    if eintraege:
        zeilen.append("Inhalt: " + ", ".join(e[0] for e in eintraege))
    zeilen.append("Auspacken: Startbefehl in 05a_Sitzungsstart (nicht von Hand abschreiben). Projektdateien bleiben "
                  "maßgeblich; dieses Paket ist ihre Transportkopie.")
    return "\n".join(zeilen + ["=====BEGIN====="] + [b64[i:i + ZEILE] for i in range(0, len(b64), ZEILE)]
                     + ["=====END====="]) + "\n"


def teile_text(b64, kopf_laenge):
    """Base64 in Stücke, deren Paketdatei samt Kopf höchstens GRENZE Zeichen hat (ganze Zeilen)."""
    netto = (GRENZE - kopf_laenge) // (ZEILE + 1) * ZEILE
    return [b64[i:i + netto] for i in range(0, len(b64), netto)] or [""]


def vorhandener_teil(art, gruppe, orte):
    """Inhalts-Kennung („inhalt …“ im Kopf) eines schon vorhandenen Teils – in der Ausgabedatei oder in einem
    ausgepackten <art>-*.paket.txt im Arbeitsordner; None, wenn keiner da ist."""
    import glob
    kandidaten = []
    for o in orte:
        kandidaten += sorted(glob.glob(os.path.join(o, "*.paket.txt"))) if os.path.isdir(o) else [o]
    for k in kandidaten:
        if not os.path.exists(k):
            continue
        kopf = open(k, encoding="utf-8").readline()
        if kopf.startswith(f"{KENNUNG} {art} ") and f" · Teil {gruppe} 1/" in kopf:
            m = re.search(r" · inhalt ([0-9a-f]{16})", kopf)
            return m.group(1) if m else None
    return None


def slug_von(name):
    import unicodedata
    for a_, b_ in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss")):
        name = name.replace(a_, b_)
    t = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "gast"


def pin_stimmt(kopf, pin):
    import hmac
    m = re.search(r" · pin pbkdf2_sha256\$(\d+)\$([0-9a-f]+)\$([0-9a-f]{64})", kopf)
    if not m:
        return False
    h = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(m.group(2)), int(m.group(1))).hex()
    return hmac.compare_digest(h, m.group(3))


def b64_von(text):
    try:
        return "".join(text.split("=====BEGIN=====")[1].split("=====END=====")[0].split())
    except IndexError:
        sys.exit("Paket unvollständig (BEGIN/END fehlt) – Datei neu lesen")


def lies_pakete(dateien):
    """Paketdateien lesen; Teile eines Datenpakets („Teil <gruppe> i/n“) zusammensetzen.
    -> Liste (Kopf, tar, Manifest, Gruppe oder None)."""
    einzeln, teile = [], {}
    for datei in dateien:
        text = open(datei, encoding="utf-8").read()
        kopf = text.strip().splitlines()[0] if text.strip() else ""
        m = re.search(r" · Teil (\S+) (\d+)/(\d+) · Stand ([^·]+) ·.* · sha256 ([0-9a-f]{64})", kopf)
        if not m:
            einzeln.append((kopf, text, None))
            continue
        gruppe, i, n, stand, summe = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).strip(), m.group(5)
        art = kopf.split()[1] if len(kopf.split()) > 1 else "?"
        teile.setdefault((art, gruppe), {}).setdefault((stand, summe, n), {})[i] = (kopf, b64_von(text))
    geteilt = {art for art, _ in teile}           # Paket ohne Teile (vor V1.9.6) neben geteiltem Paket: veraltet
    for kopf, _, _ in [e for e in einzeln if len(e[0].split()) > 1 and e[0].split()[1] in geteilt]:
        print(f"Hinweis: {kopf.split(' · sha256')[0]} übergangen – es gibt das Paket in Teilen (neuer).")
    out = [(*lies_paket(text), g) for kopf, text, g in einzeln
           if not (len(kopf.split()) > 1 and kopf.split()[1] in geteilt)]
    for (art, gruppe), staende in sorted(teile.items()):
        stand, summe, n = max(staende)            # neuester Stand dieser Gruppe
        da = staende[(stand, summe, n)]
        if len(staende) > 1:
            print(f"Hinweis: {art}/{gruppe} – ältere Teile übergangen, genommen wird Stand {stand}.")
        fehlt = [i for i in range(1, n + 1) if i not in da]
        if fehlt:
            sys.exit(f"Datenpaket unvollständig: Teil {gruppe} " + ", ".join(f"{i}/{n}" for i in fehlt)
                     + " fehlt – im Projekt lesen (claude/pakete/…) und erneut auspacken.")
        kopf = da[1][0]
        out.append((*lies_paket(kopf + "\n=====BEGIN=====\n" + "".join(da[i][1] for i in range(1, n + 1))
                                + "\n=====END=====\n"), gruppe))
    return out


def lies_paket(text):
    zeilen = text.strip().splitlines()
    if not zeilen or not zeilen[0].startswith(KENNUNG):
        sys.exit("kein MTG-Paket (erste Zeile muss mit MTG-PAKET beginnen)")
    m = re.search(r"sha256 ([0-9a-f]{64})", zeilen[0])
    roh = base64.b64decode(b64_von(text))
    if m and sha(roh) != m.group(1):
        sys.exit("Prüfsumme des Pakets stimmt nicht – Paket beim Lesen abgeschnitten? Neu lesen.")
    tar = tarfile.open(fileobj=io.BytesIO(roh), mode="r:xz")
    manifest = json.load(tar.extractfile("manifest.json"))
    return zeilen[0], tar, manifest


def cmd_auspacken(a):
    os.makedirs(a.ziel, exist_ok=True)
    mpfad = os.path.join(a.ziel, "paket_manifest.json")
    gesamt = json.load(open(mpfad, encoding="utf-8")) if os.path.exists(mpfad) else {"dateien": []}
    for kopf, tar, man, gruppe in lies_pakete(a.pakete):
        if man["art"] == "gast" and not (a.pin and pin_stimmt(kopf, a.pin)):
            print(f"Gast-Archiv übersprungen ({kopf.split(' · Stand')[0]}): erst die PIN prüfen, dann "
                  "auspacken mit --pin <PIN>.")
            continue
        if man["art"] == "daten" and (rolle(a.ziel) == "gast" or os.path.exists(os.path.join(a.ziel, "gast_profil.json"))):
            print("Datenpaket übersprungen: Gast-Sitzung – der Bestand des Projekts gehört nicht in den Arbeitsbereich.")
            continue
        # gleiche Art und Gruppe ersetzen; ein Paket ohne Gruppe (vor V1.9.6) ersetzt die ganze Art und umgekehrt
        gesamt["dateien"] = [d for d in gesamt["dateien"] if d["art"] != man["art"]
                             or (gruppe and d.get("gruppe") and d["gruppe"] != gruppe)]
        for d in man["dateien"]:
            roh = tar.extractfile(d["projekt"]).read()
            if sha(roh) != d["sha256"]:
                sys.exit(f"Prüfsumme falsch: {d['projekt']}")
            lokal = lokal_fuer(d["projekt"])
            ziel = os.path.join(a.ziel, lokal)
            os.makedirs(os.path.dirname(ziel) or a.ziel, exist_ok=True)
            open(ziel, "wb").write(roh)
            gesamt["dateien"].append({"art": man["art"], "projekt": d["projekt"], "lokal": lokal,
                                      "sha256": d["sha256"], **({"gruppe": gruppe} if gruppe else {})})
        if man["art"] == "daten":
            gesamt["praefix"] = "claude/"
            gesamt["datendateien"] = sorted(os.path.basename(d["projekt"]) for d in gesamt["dateien"]
                                            if d["art"] == "daten" and "/sammlung/" in "/" + d["projekt"])
        if man["art"] == "gast":
            gesamt["gast"] = re.search(r" · gast (\S+)", kopf).group(1)
        gesamt[f"stand_{man['art']}"] = man["stand"]
        print(f"{kopf.split(' · sha256')[0]}\n  -> {len(man['dateien'])} Dateien nach {a.ziel}")
    json.dump(gesamt, open(mpfad, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    basis = sorted(d["lokal"] for d in gesamt["dateien"] if d["art"] != "gast" and BASIS.search(d["lokal"]))
    if not basis:                                 # Gast-Archiv: alle Bestandsdateien außer Journal und Vormerkungen
        basis = [d["lokal"] for d in gesamt["dateien"] if d["art"] == "gast" and d["lokal"].startswith("data/")
                 and d["lokal"].endswith(".csv") and not re.search(r"(buchungen|vormerkungen)\.csv$", d["lokal"])]
    if basis:
        print("\nDatenbank bauen (im Hintergrund):\n  cd " + a.ziel + " && python3 mtg_db.py build --sammlung "
              + " ".join(basis + (["data/buchungen.csv"] if os.path.exists(os.path.join(a.ziel, "data/buchungen.csv"))
                                  else [])) + " --decks decks/*.txt")


def cmd_geaendert(a):
    if rolle(a.ziel) == "gast" or os.path.exists(os.path.join(a.ziel, "gast_profil.json")):
        sys.exit("Gast-Sitzung: nichts ins Projekt zurückschreiben. Am Ende nur das Archiv "
                 "(packen --art gast) – oder alles löschen (13_Betriebsmodus-und-Weitergabe, Gast-Ablauf).")
    man = json.load(open(os.path.join(a.ziel, "paket_manifest.json"), encoding="utf-8"))
    alt = {d["lokal"]: d for d in man["dateien"]}
    geaendert = []
    for lokal, d in sorted(alt.items()):
        p = os.path.join(a.ziel, lokal)
        if not os.path.exists(p):
            geaendert.append(("gelöscht", lokal, d["projekt"]))
        elif sha(open(p, "rb").read()) != d["sha256"]:
            geaendert.append(("geändert", lokal, d["projekt"]))
    for unter, ziel, muster in (("decks", "decks", r".*\.txt$"), ("ideen", "ideen", r".*\.(txt|md)$"),
                                ("data", "sammlung", BASIS.pattern)):
        d = os.path.join(a.ziel, unter)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if re.search(muster, f if unter != "data" else f"data/{f}") and f"{unter}/{f}" not in alt \
                    and not f.startswith("_"):
                geaendert.append(("neu", f"{unter}/{f}", f"{man.get('praefix', 'claude/')}{ziel}/{f}"))
    if not geaendert:
        print("Keine Änderungen gegenüber dem ausgepackten Stand.")
        return
    for art, lokal, projekt in geaendert:
        print(f"{art:9} {os.path.join(a.ziel, lokal)}  ->  {projekt}")
    print("\nZurückschreiben: je Datei project_write(path=<Projektpfad>, local_path=<lokal>) – vorher die lokale Datei "
          "mit Read ganz lesen; „gelöscht“ = project_delete. Danach das Datenpaket neu packen (packen --art daten "
          "--arbeit " + a.ziel + " --out datenpaket.txt) und die als „neu“ gemeldeten Teile ebenso schreiben.")


def cmd_holen(a):
    """Letztes vollständiges Paket der Art aus dem Sitzungsprotokoll (project_read-Ergebnis) als Datei ablegen."""
    import glob
    gefunden = []

    def pruefe(s):
        if isinstance(s, str) and "MTG-PAKET" in s:
            try:
                s = json.loads(s).get("content", s)
            except Exception:
                pass
            if isinstance(s, str) and s.startswith(f"{KENNUNG} {a.art} ") and "=====END=====" in s:
                gefunden.append(s)

    def lauf(o):
        if isinstance(o, dict):
            for v in o.values():
                lauf(v)
        elif isinstance(o, list):
            for v in o:
                lauf(v)
        else:
            pruefe(o)

    for f in sorted(glob.glob(os.path.expanduser("~/.claude/projects/**/*.jsonl"), recursive=True),
                    key=os.path.getmtime):
        for zeile in open(f, encoding="utf-8", errors="replace"):
            if f"{KENNUNG} {a.art}" in zeile:
                try:
                    lauf(json.loads(zeile))
                except Exception:
                    continue
    if not gefunden:
        sys.exit(f"kein Paket der Art „{a.art}“ im Sitzungsprotokoll – erst mit project_read lesen")
    open(a.out, "w", encoding="utf-8").write(gefunden[-1].rstrip("\n") + "\n")
    print(f"{gefunden[-1].splitlines()[0].split(' · sha256')[0]}\n-> {a.out}")


def cmd_liste(a):
    for kopf, tar, man, _ in lies_pakete(a.paket):
        print(kopf)
        for d in man["dateien"]:
            print(f"  {d['projekt']:55} {d['bytes']:>8} B  -> {lokal_fuer(d['projekt'])}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("packen")
    p.add_argument("--art", choices=("werkzeuge", "daten", "gast"), required=True)
    p.add_argument("--quelle")
    p.add_argument("--arbeit")
    p.add_argument("--out", required=True)
    p.add_argument("--nutzer", action="store_true", help="Nutzer-Kopie: ohne weitergabe.py")
    p.add_argument("--name", help="Gast-Archiv: Name des Gastes")
    p.add_argument("--pin-hash", help="Gast-Archiv: Ausgabe von zugang.py pin-hash")
    p = sp.add_parser("auspacken")
    p.add_argument("pakete", nargs="+")
    p.add_argument("--ziel", default="/home/claude/mtg")
    p.add_argument("--pin", help="PIN des Gast-Archivs")
    p = sp.add_parser("holen")
    p.add_argument("--art", required=True)
    p.add_argument("--out", required=True)
    p = sp.add_parser("geaendert")
    p.add_argument("--ziel", default="/home/claude/mtg")
    p = sp.add_parser("liste")
    p.add_argument("paket", nargs="+", help="Paketdatei(en); Teile eines Datenpakets zusammen angeben")
    a = ap.parse_args()
    {"packen": cmd_packen, "auspacken": cmd_auspacken, "geaendert": cmd_geaendert, "holen": cmd_holen,
     "liste": cmd_liste}[a.cmd](a)


if __name__ == "__main__":
    main()
