#!/usr/bin/env python3
"""zugang.py – Zugang zum MTG-Projekt: Admin-Passwort, Gast-PIN, Freischaltung, Sitzungsrolle.

Regeln und Ablauf: Projektdatei 13_Betriebsmodus-und-Weitergabe (Zustände, Anmeldung, Gast-Archiv).
Ehrlich: Das ist eine Kindersicherung, kein Schloss. Claude hält sich an die Rollen; wer Zugriff auf das
Projekt hat, kann Dateien und Anweisungen selbst ändern. Gespeichert werden nur Hashes (PBKDF2-SHA256 mit
Salz), nie ein Klartext – auch nicht im öffentlichen GitHub-Repo.

Zugangsdatei: claude/zugang.json (Weitergabe-Kopie: zugang.json im Projektstamm)
  {"admin": {"verfahren", "runden", "salz", "hash", "gesetzt"}, "user_freigeschaltet": bool, "kopie": bool}

Befehle
  setzen --datei <zugang.json> --passwort <P>        Admin-Passwort setzen oder ändern (legt die Datei an)
  pruefen --datei <zugang.json> --passwort <P>       Anmeldung prüfen → OK / FALSCH (Exit 0 / 1);
                                                     nach 3 Fehlversuchen in dieser Sitzung gesperrt
  freischalten --datei <zugang.json> --user ja|nein  User-Zustand freigeben (Weitergabe-Kopie, Admin vor Ort)
  status --datei <zugang.json>                       Stand ohne Geheimnisse
  pin-hash <PIN>                                     Hash einer 4-stelligen Gast-PIN (für paket.py packen --art gast)
  pin-pruefen <gast-archiv.txt> --pin <PIN>          PIN gegen den Kopf eines Gast-Archivs → OK / FALSCH
  sitzung <start|admin|user|gast> [--name N]         Rolle dieser Sitzung im Arbeitsbereich vermerken
                                                     (paket.py sperrt danach, was die Rolle nicht darf)
  slug <Name>                                        Dateiname des Gast-Archivs (claude/gaeste/<slug>.txt)
  gast-profil --name N [--quelle Q] [--quittiert DECK] [--notiz T]
                                                     gast_profil.json im Arbeitsbereich anlegen bzw. ergänzen
                                                     (geht mit ins Archiv: Name, Quelle, quittierte Decks)
"""
import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
import unicodedata

VERFAHREN = "pbkdf2_sha256"
RUNDEN = 200_000
ARBEIT = "/home/claude/mtg"
MAX_FEHLER = 3


def hashe(geheimnis, salz=None, runden=RUNDEN):
    salz = salz or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", geheimnis.encode("utf-8"), bytes.fromhex(salz), runden).hex()
    return {"verfahren": VERFAHREN, "runden": runden, "salz": salz, "hash": h}


def stimmt(geheimnis, eintrag):
    if not eintrag or eintrag.get("verfahren") != VERFAHREN:
        return False
    h = hashe(geheimnis, eintrag["salz"], int(eintrag["runden"]))["hash"]
    return hmac.compare_digest(h, eintrag["hash"])


def als_text(e):
    """Hash-Eintrag als eine Zeile: pbkdf2_sha256$runden$salz$hash (für Paketköpfe)."""
    return f"{e['verfahren']}${e['runden']}${e['salz']}${e['hash']}"


def aus_text(t):
    v, r, s, h = t.strip().split("$")
    return {"verfahren": v, "runden": int(r), "salz": s, "hash": h}


def lade(datei):
    if not os.path.exists(datei):
        return {}
    return json.load(open(datei, encoding="utf-8"))


def speichere(datei, d):
    d = {"_hinweis": "Zugang zum MTG-Projekt (13_Betriebsmodus-und-Weitergabe). Nur Hashes, nie Klartext. "
                     "Ändern nur im Admin-Zustand mit zugang.py.", **{k: v for k, v in d.items() if k != "_hinweis"}}
    os.makedirs(os.path.dirname(os.path.abspath(datei)), exist_ok=True)
    json.dump(d, open(datei, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(datei, "a", encoding="utf-8").write("\n")


def fehlerdatei(ziel):
    return os.path.join(ziel, ".zugang_fehlversuche")


def cmd_setzen(a):
    if len(a.passwort) < 4:
        sys.exit("Passwort zu kurz (mindestens 4 Zeichen)")
    d = lade(a.datei)
    d["admin"] = {**hashe(a.passwort), "gesetzt": time.strftime("%Y-%m-%d")}
    d.setdefault("user_freigeschaltet", True)
    d.setdefault("kopie", False)
    speichere(a.datei, d)
    print(f"Admin-Passwort gesetzt → {a.datei} (nur Hash gespeichert)")


def cmd_pruefen(a):
    os.makedirs(a.ziel, exist_ok=True)
    fd = fehlerdatei(a.ziel)
    fehler = int(open(fd).read() or 0) if os.path.exists(fd) else 0
    if fehler >= MAX_FEHLER:
        print(f"GESPERRT – {MAX_FEHLER} Fehlversuche in dieser Sitzung. Neuen Chat starten.")
        sys.exit(2)
    d = lade(a.datei)
    if "admin" not in d:
        print("KEIN PASSWORT – Admin-Zugang ist nicht eingerichtet.")
        sys.exit(3)
    if stimmt(a.passwort, d["admin"]):
        if os.path.exists(fd):
            os.remove(fd)
        print("OK")
        return
    open(fd, "w").write(str(fehler + 1))
    print(f"FALSCH – noch {MAX_FEHLER - fehler - 1} Versuch(e)")
    sys.exit(1)


def cmd_freischalten(a):
    d = lade(a.datei)
    if not d:
        sys.exit(f"{a.datei} fehlt")
    d["user_freigeschaltet"] = a.user == "ja"
    speichere(a.datei, d)
    print(f"User-Zustand {'freigeschaltet' if d['user_freigeschaltet'] else 'gesperrt'} → {a.datei}")


def cmd_status(a):
    d = lade(a.datei)
    print(f"Datei: {a.datei}")
    print(f"Admin-Passwort: {'gesetzt am ' + d['admin'].get('gesetzt', '?') if 'admin' in d else 'nicht gesetzt'}")
    print(f"User-Zustand: {'freigeschaltet' if d.get('user_freigeschaltet') else 'nicht freigeschaltet'}")
    print(f"Weitergabe-Kopie: {'ja' if d.get('kopie') else 'nein'}")


def cmd_pin_hash(a):
    if not re.fullmatch(r"\d{4}", a.pin):
        sys.exit("PIN muss genau 4 Ziffern haben")
    print(als_text(hashe(a.pin)))


def pin_aus_archiv(pfad):
    kopf = open(pfad, encoding="utf-8").readline()
    m = re.search(r" · pin (\S+)", kopf)
    if not kopf.startswith("MTG-PAKET gast") or not m:
        sys.exit("kein Gast-Archiv (Kopf ohne „MTG-PAKET gast … · pin …“)")
    return aus_text(m.group(1))


def cmd_pin_pruefen(a):
    os.makedirs(a.ziel, exist_ok=True)
    fd = fehlerdatei(a.ziel) + "_pin"
    fehler = int(open(fd).read() or 0) if os.path.exists(fd) else 0
    if fehler >= MAX_FEHLER:
        print(f"GESPERRT – {MAX_FEHLER} falsche PINs in dieser Sitzung. Neuen Chat starten oder als neuer Gast "
              "unter anderem Namen weiterarbeiten.")
        sys.exit(2)
    if stimmt(a.pin, pin_aus_archiv(a.archiv)):
        if os.path.exists(fd):
            os.remove(fd)
        print("OK")
        return
    open(fd, "w").write(str(fehler + 1))
    print(f"FALSCH – noch {MAX_FEHLER - fehler - 1} Versuch(e)")
    sys.exit(1)


def cmd_sitzung(a):
    os.makedirs(a.ziel, exist_ok=True)
    pfad = os.path.join(a.ziel, "SITZUNG.json")
    if os.path.exists(pfad):
        alt = json.load(open(pfad, encoding="utf-8"))
        if alt.get("rolle") not in (None, "start", a.rolle):
            sys.exit(f"Diese Sitzung läuft schon als „{alt['rolle']}“ – eine Rolle je Chat. Neuen Chat starten.")
    d = {"rolle": a.rolle, "seit": time.strftime("%Y-%m-%d %H:%M")}
    if a.name:
        d["name"], d["slug"] = a.name, slug(a.name)
    json.dump(d, open(pfad, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Sitzung: {a.rolle}" + (f" ({a.name}, Archiv claude/gaeste/{d['slug']}.txt)" if a.name else ""))


def slug(name):
    for a_, b_ in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss")):
        name = name.replace(a_, b_)
    t = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    if not t:
        sys.exit("Name ergibt keinen Dateinamen – bitte mit Buchstaben")
    return t[:40]


def cmd_slug(a):
    print(slug(a.name))


def cmd_gast_profil(a):
    pfad = os.path.join(a.ziel, "gast_profil.json")
    d = json.load(open(pfad, encoding="utf-8")) if os.path.exists(pfad) else {}
    jetzt = time.strftime("%Y-%m-%d %H:%M")
    d.setdefault("angelegt", jetzt)
    d.update({"name": a.name, "slug": slug(a.name), "stand": jetzt})
    if a.quelle:
        d["quelle"] = a.quelle
    if a.quittiert:
        d.setdefault("quittiert", []).append({"deck": a.quittiert, "datum": jetzt})
    if a.notiz:
        d.setdefault("notizen", []).append({"text": a.notiz, "datum": jetzt})
    os.makedirs(a.ziel, exist_ok=True)
    json.dump(d, open(pfad, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Gast-Profil: {d['name']} · Quelle {d.get('quelle', '–')} · quittiert {len(d.get('quittiert', []))} · "
          f"angelegt {d['angelegt']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("setzen")
    p.add_argument("--datei", required=True)
    p.add_argument("--passwort", required=True)
    p = sp.add_parser("pruefen")
    p.add_argument("--datei", required=True)
    p.add_argument("--passwort", required=True)
    p.add_argument("--ziel", default=ARBEIT)
    p = sp.add_parser("freischalten")
    p.add_argument("--datei", required=True)
    p.add_argument("--user", choices=("ja", "nein"), required=True)
    p = sp.add_parser("status")
    p.add_argument("--datei", required=True)
    p = sp.add_parser("pin-hash")
    p.add_argument("pin")
    p = sp.add_parser("pin-pruefen")
    p.add_argument("archiv")
    p.add_argument("--pin", required=True)
    p.add_argument("--ziel", default=ARBEIT)
    p = sp.add_parser("sitzung")
    p.add_argument("rolle", choices=("start", "admin", "user", "gast"))
    p.add_argument("--name")
    p.add_argument("--ziel", default=ARBEIT)
    p = sp.add_parser("slug")
    p.add_argument("name")
    p = sp.add_parser("gast-profil")
    p.add_argument("--name", required=True)
    p.add_argument("--quelle")
    p.add_argument("--quittiert")
    p.add_argument("--notiz")
    p.add_argument("--ziel", default=ARBEIT)
    a = ap.parse_args()
    {"setzen": cmd_setzen, "pruefen": cmd_pruefen, "freischalten": cmd_freischalten, "status": cmd_status,
     "pin-hash": cmd_pin_hash, "pin-pruefen": cmd_pin_pruefen, "sitzung": cmd_sitzung, "slug": cmd_slug,
     "gast-profil": cmd_gast_profil}[a.cmd](a)


if __name__ == "__main__":
    main()
