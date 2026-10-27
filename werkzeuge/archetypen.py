#!/usr/bin/env python3
"""archetypen.py – Commander-Archetypen: Pakete erkennen, Sammlung und Decks auswerten, Richtwerte erheben.

Begleitwerkzeug zu den Projektdateien 11_Archetypen-Playbook (Wissen) und 12_Sammlungsprofil (Ergebnis).
Ein Archetyp besteht aus Paketen (z. B. Aristokraten = Opfer-Outlets + Futter + Tod-Payoffs). Die Pakete
werden über Scryfall-Funktionstags (Community-Daten, Tagger) und Oracle-Text-Muster erkannt – das ist eine
Näherung; Claude prüft Einzelfälle am Oracle-Text.

Datenquellen
  - mtg.sqlite (von mtg_db.py build) im aktuellen Ordner: Kartendaten und freie Karten (v_karten.frei).
  - Ohne Datenbank: Scryfall-Bulk oracle_cards (wird geladen) + Liste der freien Karten (--frei, Format 07).
  - Funktionstags immer aus bulk/oracle_tags.jsonl.gz (lädt mtg_db.py build mit; sonst wird sie geladen),
    weil hier zwischen direkten und geerbten Tags unterschieden wird.

Befehle
  profil [--frei 07.csv] [--decks claude/decks/*.txt] [--einschaetzung E.md] [--out 12_Sammlungsprofil.md] [--hinweis T]
        Sammlungsprofil: Welche Archetypen tragen die freien Karten, in welchen Farben, welche Pakete fehlen?
        Mit --decks zusätzlich: Status der Schlüsselkarten je Deck und die Commander-Decks im Archetyp-Raster.
  karten <archetyp> [--paket P] [--farben RWB] [--frei 07.csv] [--alle] [--ohne-deck <deckdatei>]
        Freie Karten (mit --alle: alle Commander-legalen) eines Archetyps bzw. Pakets auflisten; --ohne-deck lässt
        Karten weg, die schon im Deck stecken (Singleton – ein zweites freies Exemplar hilft nicht).
  deck <deckdatei> [--archetyp A] [--daten archetypen_daten.json]
        Paket-Zählung eines Decks; mit Richtwerten aus der Datenerhebung (Median der EDHREC-Durchschnittsdecks).
        Rollen zählen wie in deckbau.py über die 99 ohne Commander; Pakete und Ø MV mit Commander.
  daten [--top 6] [--bracket 3] [--out archetypen_daten.json]
        Datenerhebung: Top-Commander je Archetyp (EDHREC-Themenseite) -> Durchschnittsdecks (Bracket-/Themenfilter)
        -> Rollen und Pakete zählen -> Median und Spanne je Archetyp. Grundlage der Stückzahlen im Playbook.

Archetypen-Schlüssel: tokens, aristokraten, counters, artefakte, spellslinger, reanimator, lifegain, landfall,
voltron, enchantress, blink, kindred, mill
"""
import argparse
import csv
import gzip
import json
import os
import re
import sqlite3
import statistics
import sys
import time
import urllib.request
from collections import Counter, defaultdict

UA = {"User-Agent": "MTG-Projekt/1.0", "Accept": "application/json"}
BULK = "bulk"
WUBRG = "WUBRG"

# ----------------------------------------------------------------- Rollen (wie deckbau.py)
TAGS_RAMP = {"ramp", "mana-rock", "mana-dork", "land-ramp"}
TAGS_KA = {"card-advantage", "draw"}
TAGS_SCHUTZ = {"protects-all", "protects-creature", "gives-indestructible", "gives-hexproof",
               "gives-protection", "protects-permanent"}
ROLLEN = [("land", "Länder"), ("ramp", "Ramp"), ("ka", "Kartenvorteil"), ("gezielt", "Gezielte Interaktion"),
          ("instant_int", "davon Instant-Tempo"), ("massen", "Massen-Interaktion"), ("counter", "Counterspells"),
          ("schutz", "Schutz"), ("tutor", "Tutoren"), ("rekursion", "Rekursion")]

RX_TOKEN = re.compile(r"\bcreates?\b[^.]*?\bcreature tokens?\b", re.I)
RX_LORD = re.compile(r"\b[Oo]ther [A-Z][a-z]+(?: [A-Z][a-z]+)? creatures (?:you control )?get \+")
RX_GENERISCH_TYP = {"Creature", "Legendary", "Artifact", "Enchantment", "Snow", "Basic", "World", "Kindred", "Tribal"}


def front_typ(k):
    return (k["typ"] or "").split(" // ")[0]


def hat(k, *tags):
    return bool(k["t"] & set(tags))


def ist_land(k):
    return "Land" in front_typ(k)


def ist_kreatur(k):
    return "Creature" in front_typ(k)


def ist_permanent(k):
    return any(x in front_typ(k) for x in ("Creature", "Artifact", "Enchantment", "Planeswalker", "Battle", "Land"))


def etb_wert(k):
    """Kreatur mit eigenem Eintritts-Trigger ('When this creature enters' / 'When <Name> enters')."""
    if not ist_kreatur(k):
        return False
    name = re.escape(k["name"].split(" // ")[0])
    kurz = re.escape(k["name"].split(",")[0].split(" // ")[0])
    for zeile in (k["text"] or "").split("\n"):
        if re.match(rf"^when (?:this creature|{name}|{kurz}) enters", zeile, re.I):
            return True
    return False


def rollen(k):
    if ist_land(k):
        return {"land"}
    r = set()
    t = k["t"]
    gegner = bool(t & {"removal", "spot-removal"}) and bool(
        re.search(r"(its controller|that player|their controller)[^.]*search", (k["text"] or "").lower()))
    if t & TAGS_RAMP and not gegner:            # Path to Exile u. Ä. gibt dem Gegner ein Land – kein Ramp
        r.add("ramp")
    if t & TAGS_KA:
        r.add("ka")
    if "spot-removal" in t or "counterspell" in t or ("removal" in t and "sweeper" not in t):
        r.add("gezielt")
        if "Instant" in front_typ(k) or "flash" in k["kw"]:
            r.add("instant_int")
    if "counterspell" in t:
        r.add("counter")
    if "sweeper" in t:
        r.add("massen")
    if t & TAGS_SCHUTZ:
        r.add("schutz")
    if "tutor" in t:
        r.add("tutor")
    if "recursion" in t:
        r.add("rekursion")
    return r


# ----------------------------------------------------------------- Archetypen und Pakete
RX_FREMD_TOKEN = re.compile(r"(its controller|that player|target opponent|an opponent|each opponent|each player|its owner)"
                            r"[^.]*\bcreates?\b", re.I)


def p_token_quelle(k):
    """Erzeugt eigene Kreaturen-Tokens (nicht Tokens für Gegner wie bei Crib Swap)."""
    if ist_land(k):
        return False
    if hat(k, "repeatable-creature-tokens"):
        return True
    for satz in re.split(r"(?<=[.\n])", k["text"] or ""):
        if RX_TOKEN.search(satz) and not RX_FREMD_TOKEN.search(satz):
            return True
    return False


def p_futter(k):
    return p_token_quelle(k) or (not ist_land(k) and hat(k, "multiple-bodies")) or (
        ist_kreatur(k) and (k["td"] & {"death-trigger-self", "reanimate-self", "recursion-self", "cheat-death-self"}))


def p_tod_payoff(k):
    return not ist_land(k) and bool(("death-trigger" in k["td"]) or hat(k, "blood-artist-ability",
                                                                         "your-sacrifice-matters", "morbid"))


def p_flicker(k):
    return bool(k["td"] & {"flicker", "flicker-creature", "flicker-permanent", "flicker-slow", "flicker-nonland",
                           "flicker-artifact", "flicker-enchantment"})


def p_lord(k):
    return ist_permanent(k) and (hat(k, "typal-choose", "typal-share", "warlord") or bool(RX_LORD.search(k["text"] or ""))
                                 or ("typal" in k["t"] and "anthem" in k["t"]))


# Pakete: (Schlüssel, Anzeige, Prüffunktion, Kernpaket?) – Kernpakete bestimmen die Einstufung im Profil
ARCHETYPEN = {
    "tokens": {
        "name": "Tokens (Go-wide)", "edhrec": ["tokens"],
        "pakete": [
            ("quelle", "Token-Quellen (Kreaturen)", p_token_quelle, True),
            ("wiederholt", "davon wiederholbar", lambda k: hat(k, "repeatable-creature-tokens") and not ist_land(k), False),
            ("anthem", "Anthems (dauerhaft)", lambda k: hat(k, "anthem"), True),
            ("overrun", "Overrun-Finisher", lambda k: hat(k, "overrun"), False),
            ("verdoppler", "Token-Verdoppler", lambda k: hat(k, "token-doubler", "token-increaser"), False),
        ]},
    "aristokraten": {
        "name": "Aristokraten", "edhrec": ["aristocrats"],
        "pakete": [
            ("outlet", "Opfer-Outlets (wiederholbar)", lambda k: hat(k, "repeatable-sacrifice-outlet"), True),
            ("outlet_frei", "davon kostenlos", lambda k: hat(k, "free-sacrifice-outlet"), False),
            ("futter", "Futter (Tokens, Mehrfachkörper, Tod-Wert)", p_futter, True),
            ("payoff", "Tod-/Opfer-Payoffs", p_tod_payoff, True),
            ("rekursion", "Kreaturen-Rekursion", lambda k: hat(k, "reanimate-creature", "mass-reanimation"), False),
        ]},
    "counters": {
        "name": "+1/+1-Counter", "edhrec": ["plus-1-plus-1-counters"],
        "pakete": [
            ("geber", "Counter-Quellen", lambda k: hat(k, "gives-pp-counters", "repeatable-pp-counters"), True),
            ("payoff", "Counter-Payoffs", lambda k: hat(k, "pp-counters-matter", "counters-matter"), True),
            ("verdoppler", "Counter-Verstärker", lambda k: hat(k, "counter-increaser", "counter-doubler"), False),
            ("proliferate", "Proliferate", lambda k: "proliferate" in k["kw"] or hat(k, "repeatable-proliferate")
             or "proliferate" in (k["text"] or "").lower(), False),
        ]},
    "artefakte": {
        "name": "Artefakte", "edhrec": ["artifacts"],
        "pakete": [
            ("artefakte", "Artefakte (ohne Länder)", lambda k: "Artifact" in front_typ(k) and not ist_land(k), True),
            ("payoff", "Artefakt-Payoffs", lambda k: hat(k, "synergy-artifact", "artifact-count-matters"), True),
            ("token", "Artefakt-Token-Quellen", lambda k: hat(k, "repeatable-artifact-tokens", "repeatable-treasures"), False),
            ("kostensenker", "Kostensenker", lambda k: hat(k, "cost-reducer-artifact"), False),
        ]},
    "spellslinger": {
        "name": "Spellslinger", "edhrec": ["spellslinger"],
        "pakete": [
            ("zauber", "Spontanzauber/Hexereien", lambda k: any(x in front_typ(k) for x in ("Instant", "Sorcery")), True),
            ("payoff", "Zauber-Payoffs (bleibende)", lambda k: ist_permanent(k) and hat(k, "synergy-instant", "synergy-sorcery"), True),
            ("kostensenker", "Kostensenker", lambda k: hat(k, "cost-reducer-instant-sorcery", "cost-reducer-instant",
                                                            "cost-reducer-sorcery"), False),
            ("kopie", "Zauber kopieren", lambda k: hat(k, "copy-instant", "copy-sorcery", "copy-spell"), False),
        ]},
    "reanimator": {
        "name": "Reanimator / Friedhof", "edhrec": ["reanimator"],
        "pakete": [
            ("reanimation", "Reanimation", lambda k: hat(k, "reanimate-creature", "mass-reanimation", "reanimate-from-any"), True),
            ("fuellen", "Friedhof füllen (Self-Mill, Loot, Entomb)", lambda k: hat(k, "mill-self", "tutor-to-graveyard", "loot",
                                                                                 "rummage", "discard-outlet"), True),
            ("ziele", "große Ziele (Kreatur MV ≥ 6)", lambda k: ist_kreatur(k) and (k["cmc"] or 0) >= 6, False),
        ]},
    "lifegain": {
        "name": "Lifegain", "edhrec": ["lifegain"],
        "pakete": [
            ("quelle", "Lebens-Quellen (wiederholbar)", lambda k: hat(k, "repeatable-lifegain"), True),
            ("payoff", "Lifegain-Payoffs", lambda k: hat(k, "lifegain-matters", "pridemate", "lifegain-to-damage",
                                                          "lifegain-increaser"), True),
        ]},
    "landfall": {
        "name": "Lands Matter / Landfall", "edhrec": ["lands-matter", "landfall"],
        "pakete": [
            ("payoff", "Landfall-Payoffs", lambda k: hat(k, "landfall"), True),
            ("extra_land", "zusätzliche Landdrops", lambda k: hat(k, "extra-land", "play-additional-land"), True),
            ("land_ramp", "Land-Ramp", lambda k: hat(k, "land-ramp") and not ist_land(k), True),
            ("fetch", "Opfer-/Fetch-Länder", lambda k: ist_land(k) and hat(k, "fetchland"), False),
            ("rekursion", "Land-Rekursion", lambda k: hat(k, "reanimate-land", "regrowth-land"), False),
        ]},
    "voltron": {
        "name": "Voltron (Equipment/Auren)", "edhrec": ["voltron"],
        "pakete": [
            ("ausruestung", "Ausrüstung", lambda k: "Equipment" in front_typ(k), True),
            ("auren", "eigene Auren (ohne Removal-Auren)", lambda k: "Aura" in front_typ(k) and not hat(k, "removal", "hate"), False),
            ("evasion", "Evasion/Doppelschlag geben", lambda k: not ist_land(k) and hat(k, "gives-evasion", "gives-double-strike",
                                                                                         "gives-trample", "gives-flying",
                                                                                         "gives-unblockable"), True),
            ("schutz", "Schutz", lambda k: bool(k["t"] & TAGS_SCHUTZ), True),
            ("payoff", "Equipment-/Auren-Payoffs", lambda k: hat(k, "synergy-equipment", "synergy-aura", "cost-reducer-equip-ability",
                                                                  "auto-equip", "quick-equip"), False),
        ]},
    "enchantress": {
        "name": "Enchantress", "edhrec": ["enchantress"],
        "pakete": [
            ("verzauberungen", "Verzauberungen", lambda k: "Enchantment" in front_typ(k), True),
            ("engine", "Enchantress-Engines (Karte je Verzauberung)", lambda k: hat(k, "enchantment-engine"), True),
            ("payoff", "Verzauberungs-Payoffs", lambda k: hat(k, "synergy-enchantment"), True),
        ]},
    "blink": {
        "name": "Blink / ETB", "edhrec": ["blink"],
        "pakete": [
            ("flicker", "Flicker-Effekte", p_flicker, True),
            ("etb", "Kreaturen mit ETB-Wert", etb_wert, True),
            ("verdoppler", "Trigger-Verdoppler", lambda k: hat(k, "trigger-doubler"), False),
        ]},
    "kindred": {
        "name": "Kindred (Tribal)", "edhrec": ["elves", "zombies", "dragons", "angels", "goblins", "vampires", "merfolk",
                                               "dinosaurs"],
        "pakete": [
            ("payoff", "Typ-Payoffs (Lords, Typ wählen)", p_lord, True),
            ("changeling", "Gestaltwandler", lambda k: "changeling" in k["kw"] or hat(k, "changeling"), False),
        ]},
    "mill": {
        "name": "Mill (Gegner)", "edhrec": ["mill"],
        "pakete": [
            ("mill", "Mill-Effekte (Gegner)", lambda k: hat(k, "mill-opponent", "mill-each", "mill-any"), True),
            ("payoff", "Mill-Verstärker/-Payoffs", lambda k: hat(k, "synergy-mill"), False),
        ]},
}


def pakete_von(k):
    """-> {(archetyp, paket)} für eine Karte."""
    out = set()
    for a, d in ARCHETYPEN.items():
        for key, _, fn, _ in d["pakete"]:
            try:
                if fn(k):
                    out.add((a, key))
            except Exception:
                pass
    return out


# ----------------------------------------------------------------- Daten laden
def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def bulk_datei(typ):
    os.makedirs(BULK, exist_ok=True)
    fn = os.path.join(BULK, f"{typ}.jsonl.gz")
    if not os.path.exists(fn) or time.time() - os.path.getmtime(fn) > 7 * 86400:
        liste = {x["type"]: x for x in get_json("https://api.scryfall.com/bulk-data")["data"]}
        url = liste[typ].get("jsonl_download_uri") or liste[typ].get("download_uri")
        print(f"lade Scryfall-Bulk {typ} …", file=sys.stderr)
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=600) as r, open(fn + ".part", "wb") as out:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                out.write(b)
        os.replace(fn + ".part", fn)
    return fn


def iter_jsonl(fn):
    with gzip.open(fn, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip().rstrip(",")
            if line and line not in ("[", "]"):
                yield json.loads(line)


def lade_tags():
    """-> (alle Tags je Oracle-ID inkl. Elterntags, direkte Tags je Oracle-ID)."""
    tags = list(iter_jsonl(bulk_datei("oracle_tags")))
    by_id = {t["id"]: t for t in tags}
    memo = {}

    def ahnen(tid, seen=()):
        if tid in memo:
            return memo[tid]
        out = set()
        for pid in by_id.get(tid, {}).get("parent_ids", []):
            if pid in by_id and pid not in seen:
                out.add(by_id[pid]["slug"])
                out |= ahnen(pid, seen + (tid,))
        memo[tid] = out
        return out

    alle, direkt = defaultdict(set), defaultdict(set)
    for t in tags:
        s = {t["slug"]} | ahnen(t["id"])
        for tg in t.get("taggings", []):
            alle[tg["oracle_id"]] |= s
            direkt[tg["oracle_id"]].add(t["slug"])
    return alle, direkt


def lade_karten():
    """-> (Karten {oid: dict}, Namensindex {name_lower: oid}, Quelle)."""
    alle, direkt = lade_tags()
    karten, namen = {}, {}
    if os.path.exists("mtg.sqlite"):
        con = sqlite3.connect("mtg.sqlite")
        for oid, name, typ, text, cmc, ci, kw, legal, gc, eur, rank in con.execute(
                "SELECT oracle_id, name, type_line, oracle_text, cmc, color_identity, keywords, legal_commander,"
                " game_changer, eur_min, edhrec_rank FROM cards"):
            karten[oid] = {"oid": oid, "name": name, "typ": typ or "", "text": text or "", "cmc": cmc, "ci": ci or "",
                           "kw": {x.lower() for x in (kw or "").split(",") if x}, "legal": legal, "gc": bool(gc),
                           "eur": eur, "rank": rank}
        quelle = "mtg.sqlite"
    else:
        for c in iter_jsonl(bulk_datei("oracle_cards")):
            if c.get("layout") in ("token", "double_faced_token", "emblem", "art_series", "vanguard", "scheme", "planar"):
                continue
            faces = c.get("card_faces") or []
            oid = c.get("oracle_id") or (faces[0].get("oracle_id") if faces else None)
            if not oid:
                continue
            text = c.get("oracle_text") or "\n// \n".join(f.get("oracle_text", "") for f in faces)
            eur = (c.get("prices") or {}).get("eur") or (c.get("prices") or {}).get("eur_foil")
            karten[oid] = {"oid": oid, "name": c["name"], "typ": c.get("type_line", ""), "text": text, "cmc": c.get("cmc"),
                           "ci": "".join(x for x in WUBRG if x in c.get("color_identity", [])),
                           "kw": {x.lower() for x in c.get("keywords", [])},
                           "legal": c.get("legalities", {}).get("commander"), "gc": bool(c.get("game_changer")),
                           "eur": float(eur) if eur else None, "rank": c.get("edhrec_rank")}
        quelle = "Scryfall oracle_cards"
    for oid, k in karten.items():
        k["t"] = alle.get(oid, set())
        k["td"] = direkt.get(oid, set())
        n = k["name"].lower()
        namen.setdefault(n, oid)
        namen.setdefault(n.split(" // ")[0], oid)
    return karten, namen, quelle


def freie_karten(karten, namen, frei_csv):
    """-> {oid: Anzahl frei}. Aus mtg.sqlite (v_karten) oder aus der Liste 07 (Name, frei, …)."""
    if os.path.exists("mtg.sqlite") and not frei_csv:
        con = sqlite3.connect("mtg.sqlite")
        return dict(con.execute("SELECT oracle_id, frei FROM v_karten WHERE frei > 0")), "mtg.sqlite (v_karten)"
    if not frei_csv or not os.path.exists(frei_csv):
        sys.exit("Keine Datenbank und keine Liste der freien Karten (--frei claude/07_Sammlung-Frei.csv)")
    out, fehlt = {}, []
    with open(frei_csv, encoding="utf-8-sig", newline="") as fh:
        kopf = fh.readline()
        if not kopf.lstrip('"').startswith("#"):
            fh.seek(0)
        for r in csv.DictReader(fh):
            oid = namen.get(r["Name"].lower()) or namen.get(r["Name"].split(" // ")[0].lower())
            if oid:
                out[oid] = out.get(oid, 0) + int(r.get("frei") or 0)
            else:
                fehlt.append(r["Name"])
    if fehlt:
        print("nicht erkannt:", ", ".join(fehlt), file=sys.stderr)
    return out, os.path.basename(frei_csv)


# ----------------------------------------------------------------- Auswertungen
FARBPAARE = ["WU", "UB", "BR", "RG", "WG", "WB", "UR", "BG", "WR", "UG"]
FARBNAME = {"WU": "Azorius", "UB": "Dimir", "BR": "Rakdos", "RG": "Gruul", "WG": "Selesnya", "WB": "Orzhov", "UR": "Izzet",
            "BG": "Golgari", "WR": "Boros", "UG": "Simic", "WUB": "Esper", "UBR": "Grixis", "BRG": "Jund", "WRG": "Naya",
            "WUG": "Bant", "WBG": "Abzan", "WUR": "Jeskai", "UBG": "Sultai", "WBR": "Mardu", "URG": "Temur"}


def passt(k, farben):
    return set(k["ci"]) <= set(farben)


def zaehle(liste, karten, archetyp, farben=None):
    """liste: {oid: n} -> {paket: (Karten-Unikate, Beispiele)}."""
    d = ARCHETYPEN[archetyp]
    out = {}
    for key, label, fn, kern in d["pakete"]:
        treffer = []
        for oid in liste:
            k = karten.get(oid)
            if not k or k["legal"] != "legal" or (farben and not passt(k, farben)):
                continue
            try:
                if fn(k):
                    treffer.append(k)
            except Exception:
                pass
        treffer.sort(key=lambda k: (k["rank"] or 999999))
        out[key] = treffer
    return out


def lade_richtwerte(pfad):
    if pfad and os.path.exists(pfad):
        return json.load(open(pfad, encoding="utf-8"))
    return None


def einstufung(zahlen, richt, archetyp):
    """Abdeckung der Kernpakete: Anteil frei/Richtwert (Median), gedeckelt bei 100 %."""
    d = ARCHETYPEN[archetyp]
    teile = []
    for key, _, _, kern in d["pakete"]:
        if not kern:
            continue
        soll = None
        if richt:
            soll = richt.get("archetypen", {}).get(archetyp, {}).get("pakete", {}).get(f"{archetyp}.{key}", {}).get("median")
        soll = max(soll or 0, 1)
        teile.append(min(len(zahlen.get(key, [])) / soll, 1.0))
    return sum(teile) / len(teile) if teile else 0


def ampel(q):
    return "GRÜN" if q >= 0.8 else "GELB" if q >= 0.5 else "ROT"


def de(x):
    """Zahl im deutschen Format (4,5 statt 4.5)."""
    return f"{x:g}".replace(".", ",")


def deckung(z, richt, a_key):
    """Abdeckung der Kernpakete eines Archetyps durch eine Deck-Zählung (Anteil am Median, gedeckelt bei 100 %)."""
    teile = []
    for key, _, _, kern in ARCHETYPEN[a_key]["pakete"]:
        if kern:
            m = ((richt or {}).get("archetypen", {}).get(a_key, {}).get("pakete", {})
                 .get(f"{a_key}.{key}", {}).get("median")) or 1
            teile.append(min(z[f"{a_key}.{key}"] / max(m, 1), 1.0))
    return sum(teile) / len(teile) if teile else 0


# Strategie-Stichwort (deck_namen.json, Deckregister) -> Archetyp im Playbook
STRATEGIE_ZU_ARCHETYP = {"token": "tokens", "aristo": "aristokraten", "sacrifice": "aristokraten",
                         "counter": "counters", "artefakt": "artefakte", "artifact": "artefakte",
                         "spellslinger": "spellslinger", "reanimat": "reanimator", "friedhof": "reanimator",
                         "lifegain": "lifegain", "landfall": "landfall", "lands": "landfall", "voltron": "voltron",
                         "enchant": "enchantress", "blink": "blink", "mill": "mill", "elemental": "kindred",
                         "tribal": "kindred", "kindred": "kindred", "angel": "kindred"}


STARK_RANG = 5000    # EDHREC-Rang ≤ 5.000 = Karte wird in Commander nennenswert gespielt (Qualitäts-Näherung)


def stark(k):
    return (k["rank"] or 999999) <= STARK_RANG


def qualitaet(zahlen, archetyp):
    """Anteil 'spielstarker' Karten (EDHREC-Rang ≤ 5.000) unter den Kernpaket-Karten."""
    kart = {k["oid"]: k for key, _, _, kern in ARCHETYPEN[archetyp]["pakete"] if kern for k in zahlen.get(key, [])}
    return (sum(1 for k in kart.values() if stark(k)) / len(kart)) if kart else 0


def besitz_daten(deckdateien, namen):
    """{oid: (Besitz, Decknamen)} – aus mtg.sqlite (v_karten) oder aus Soll-Stand-Dateien (--decks); sonst leer."""
    if os.path.exists("mtg.sqlite") and not deckdateien:
        con = sqlite3.connect("mtg.sqlite")
        return {o: (b, ids or "") for o, b, ids in
                con.execute("SELECT oracle_id, besitz, deck_ids FROM v_karten WHERE besitz > 0")}
    out = {}
    for pfad in deckdateien or []:
        deckname = os.path.splitext(os.path.basename(pfad))[0].replace("-", " ").title()
        _, deck, _ = lies_deck(pfad, namen)
        for oid in deck:
            b, ids = out.get(oid, (1, ""))
            out[oid] = (b, ", ".join(filter(None, [ids, deckname])))
    return out


def status(oid, frei, besitz):
    if oid in frei:
        return "**frei**"
    if besitz:
        b, ids = besitz.get(oid, (0, ""))
        return f"im Deck {ids}" if b and ids else "fehlt"
    return "nicht frei"


THEMA_ZU_ARCHETYP = {"tokens": "tokens", "aristocrats": "aristokraten", "sacrifice": "aristokraten",
                     "plus-1-plus-1-counters": "counters", "artifacts": "artefakte", "spellslinger": "spellslinger",
                     "reanimator": "reanimator", "graveyard": "reanimator", "self-mill": "reanimator",
                     "lifegain": "lifegain", "lands-matter": "landfall", "landfall": "landfall", "voltron": "voltron",
                     "equipment": "voltron", "auras": "voltron", "enchantress": "enchantress", "blink": "blink",
                     "mill": "mill"}


KINDRED_THEMEN = {"elves", "zombies", "dragons", "angels", "goblins", "vampires", "merfolk", "dinosaurs", "elementals",
                  "humans", "kithkin", "spirits", "faeries", "knights", "soldiers", "wizards", "rats", "treefolk",
                  "cats", "dogs", "birds", "slivers", "demons", "eldrazi", "pirates", "squirrels", "warriors", "clerics"}


def edh_slug(name):
    n = re.sub(r"[^a-z0-9\s-]", "", name.split(" // ")[0].lower().replace("é", "e").replace("û", "u").replace("ó", "o"))
    return re.sub(r"[\s-]+", "-", n).strip("-")


def commander_abschnitt(frei, karten):
    """Freie Karten, die Commander sein können, mit ihren häufigsten EDHREC-Themen."""
    zeilen = ["## Freie Commander und ihre EDHREC-Themen\n",
              "Legendäre Kreaturen (bzw. „can be your commander“) aus der Sammlung; Themen = häufigste EDHREC-Themen "
              "der Decks mit diesem Commander (Deckzahl in Klammern), Stand des Abrufs.\n",
              "| Commander | Farben | Decks auf EDHREC | häufigste Themen | Archetyp im Playbook |", "|---|---|---|---|---|"]
    kand = []
    for oid in frei:
        k = karten.get(oid)
        if not k or k["legal"] != "legal":
            continue
        ft = front_typ(k)
        if ("Legendary" in ft and "Creature" in ft) or "can be your commander" in (k["text"] or ""):
            kand.append(k)
    reihen = []
    for k in kand:
        d = edhrec(f"commanders/{edh_slug(k['name'])}")
        if not d:
            reihen.append((0, f"| {k['name']} | {k['ci'] or 'C'} | – | keine EDHREC-Seite | – |"))
            continue
        n = d["container"]["json_dict"].get("card", {}).get("num_decks") or 0
        themen = (d.get("panels") or {}).get("taglinks", [])[:3]
        arche = sorted({THEMA_ZU_ARCHETYP.get(t["slug"], "") for t in themen} - {""})
        if any(t["slug"] in KINDRED_THEMEN for t in themen):
            arche.append("kindred")
        reihen.append((n, f"| {k['name']} | {k['ci'] or 'C'} | {n} | " +
                       ", ".join(f"{t['value']} ({t['count']})" for t in themen) + f" | {', '.join(arche) or '–'} |"))
    reihen.sort(key=lambda r: -r[0])
    zeilen += [r for _, r in reihen]
    zeilen.append("")
    return zeilen


def deck_abschnitt(deckdateien, karten, namen, richt, config_pfad):
    """Commander-Decks (Soll-Stände) im Archetyp-Raster: Ziel-Archetyp aus der Strategie, Kernpakete gegen Median."""
    config = json.load(open(config_pfad, encoding="utf-8")) if config_pfad and os.path.exists(config_pfad) else {}
    zeilen = ["## Bestehende Commander-Decks im Archetyp-Raster\n",
              "Paket-Zählung der Soll-Stände (`claude/decks/`) gegen die Richtwerte. Ziel-Archetyp = Strategie aus "
              "`deck_namen.json`; ⚠ = Kernpaket unter dem kleinsten Wert der Datenbasis. Grundlage für Upgrades nach "
              "Ablauf B (Masterprompt) – ersetzt nicht `deckbau.py pruefen`.\n",
              "| Deck | Commander | Strategie | Ziel-Archetyp: Kernpakete (ist / Median) | am besten abgedeckt |",
              "|---|---|---|---|---|"]
    n = 0
    for pfad in deckdateien:
        cmdr, deck, _ = lies_deck(pfad, namen)
        if sum(deck.values()) < 90 or not cmdr:
            continue                      # nur Commander-Decks
        n += 1
        z = zaehle_deck(deck, karten)
        cfg = config.get(f"commander:{cmdr[0]}", {})
        strategie = cfg.get("strategie", "")
        deckname = cfg.get("name") or cfg.get("precon") or os.path.splitext(os.path.basename(pfad))[0].replace("-", " ").title()
        ziel = next((v for k, v in STRATEGIE_ZU_ARCHETYP.items() if k in strategie.lower()), None)
        if ziel:
            teile = []
            for key, label, _, kern in ARCHETYPEN[ziel]["pakete"]:
                if not kern:
                    continue
                m = (richt or {}).get("archetypen", {}).get(ziel, {}).get("pakete", {}).get(f"{ziel}.{key}")
                ist = z[f"{ziel}.{key}"]
                teile.append(f"{label.split(' (')[0]} {ist}" + (f" / {de(m['median'])}" + (" ⚠" if ist < m["min"] else "")
                                                                if m else ""))
            ziel_txt = f"{ARCHETYPEN[ziel]['name']}: " + " · ".join(teile)
        else:
            ziel_txt = "– (Strategie keinem Archetyp zugeordnet)"
        top = sorted(ARCHETYPEN, key=lambda k: -deckung(z, richt, k))[:3]
        top_txt = ", ".join(f"{ARCHETYPEN[k]['name'].split(' (')[0]} {deckung(z, richt, k) * 100:.0f} %" for k in top)
        zeilen.append(f"| {deckname} | {cmdr[0]} | {strategie or '–'} | {ziel_txt} | {top_txt} |")
    if not n:
        return []
    zeilen.append("")
    return zeilen


def cmd_profil(a):
    karten, namen, quelle = lade_karten()
    frei, fquelle = freie_karten(karten, namen, a.frei)
    besitz = besitz_daten(a.decks, namen)
    richt = lade_richtwerte(a.daten)
    n_unikate, n_ex = len(frei), sum(frei.values())
    zeilen = []
    zeilen.append("# Sammlungsprofil – Archetypen in den freien Karten\n")
    zeilen.append(f"**Stand:** {time.strftime('%d.%m.%Y')} · erzeugt mit `claude/tools/archetypen.py profil` · freie Karten: "
                  f"{fquelle} ({n_unikate} Karten / {n_ex} Exemplare) · Kartendaten und Funktionstags: {quelle}, "
                  f"Scryfall-Tagger" + (f" · {a.hinweis}" if a.hinweis else ""))
    zeilen.append("Richtwerte = Median der EDHREC-Durchschnittsdecks je Archetyp (`archetypen_daten.json`, siehe "
                  "`11_Archetypen-Playbook`). **Daten:** Zählungen über Tags/Oracle-Text (Näherung). **Einschätzung:** "
                  "Ampel und Kommentare.\n")
    zeilen.append("**Lesart:** „frei“ zählt Karten-Unikate in der Sammlung (nicht in Decks, nicht vorgemerkt), unabhängig "
                  "von der Farbe, sofern nicht anders angegeben. Ampel je Archetyp = Abdeckung der Kernpakete gegen den "
                  "Richtwert (GRÜN ≥ 80 %, GELB ≥ 50 %, ROT darunter) in der besten Zwei- bzw. Dreifarben-Kombination. "
                  "Das ist ein Startsignal für Weg 1, kein fertiges Deck – Commander, Ramp, Interaktion und Länder "
                  "kommen dazu.\n")
    if a.einschaetzung and os.path.exists(a.einschaetzung):
        zeilen.append(open(a.einschaetzung, encoding="utf-8").read().strip() + "\n")
    # Übersicht
    zeilen.append("## Übersicht\n")
    zeilen.append("| Archetyp | Kernpakete frei (alle Farben) | beste 2 Farben | beste 3 Farben | Ampel (3 Farben) | "
                  "spielstark* |")
    zeilen.append("|---|---|---|---|---|---|")
    detail = []
    dreier = [p for p in FARBNAME if len(p) == 3]
    for a_key, d in ARCHETYPEN.items():
        z_alle = zaehle(frei, karten, a_key)
        kern = [(key, label) for key, label, _, k in d["pakete"] if k]
        txt_alle = ", ".join(f"{label.split(' (')[0]} {len(z_alle[key])}" for key, label in kern)
        def wertung(f):
            z = zaehle(frei, karten, a_key, f)
            kern_k = {k["oid"]: k for key, _, _, kern in d["pakete"] if kern for k in z[key]}
            # Abdeckung zuerst; bei Gleichstand mehr spielstarke, dann mehr Kernkarten
            return (round(einstufung(z, richt, a_key), 3), sum(1 for k in kern_k.values() if stark(k)), len(kern_k))
        best2 = max(FARBPAARE, key=wertung)
        q2 = einstufung(zaehle(frei, karten, a_key, best2), richt, a_key)
        best3 = max(dreier, key=wertung)
        z3 = zaehle(frei, karten, a_key, best3)
        q3 = einstufung(z3, richt, a_key)
        zeilen.append(f"| {d['name']} | {txt_alle} | {FARBNAME[best2]} ({q2 * 100:.0f} %) | {FARBNAME[best3]} "
                      f"({q3 * 100:.0f} %) | {ampel(q3)} | {qualitaet(z3, a_key) * 100:.0f} % |")
        detail.append((a_key, d, z_alle, best3, z3, q3))
    zeilen.append("")
    zeilen.append(f"\\* spielstark = Anteil der Kernpaket-Karten (beste 3 Farben) mit EDHREC-Rang ≤ {STARK_RANG:,}".replace(",", ".")
                  + " – Näherung für Kartenqualität. Die Ampel misst Menge, nicht Qualität: viele freie Karten stammen "
                    "aus Draft-/Play-Boostern.\n")
    # Kindred: Kreaturtypen
    typen = Counter()
    for oid, n in frei.items():
        k = karten.get(oid)
        if not k or not ist_kreatur(k):
            continue
        tl = front_typ(k)
        if "—" in tl:
            for t in tl.split("—", 1)[1].split():
                typen[t] += 1
    changelings = [karten[o]["name"] for o in frei if o in karten and karten[o]["legal"] == "legal" and
                   ("changeling" in karten[o]["kw"] or "changeling" in karten[o]["t"])]
    zeilen.append("## Kreaturtypen (Kindred-Kandidaten)\n")
    zeilen.append("Häufigste Kreaturtypen unter den freien Kreaturen (Karten-Unikate): " +
                  ", ".join(f"{t} {n}" for t, n in typen.most_common(15)) + ".")
    zeilen.append(f"Gestaltwandler (zählen für jeden Typ): {len(changelings)} – " + ", ".join(sorted(changelings)) + ".\n")
    # Rollen
    zeilen.append("## Grundrollen in der Sammlung (für jeden Archetyp nötig)\n")
    rz = Counter()
    for oid in frei:
        k = karten.get(oid)
        if k and k["legal"] == "legal":
            for r in rollen(k):
                rz[r] += 1
    zeilen.append("| Rolle | freie Karten (alle Farben) |")
    zeilen.append("|---|---|")
    for key, label in ROLLEN:
        zeilen.append(f"| {label} | {rz[key]} |")
    zeilen.append("")
    # Details
    zeilen.append("## Details je Archetyp\n")
    for a_key, d, z_alle, best3, z3, q3 in detail:
        zeilen.append(f"### {d['name']} – beste Farben: {FARBNAME[best3]} ({best3}), Ampel {ampel(q3)}\n")
        zeilen.append("| Paket | Richtwert (Median) | frei, alle Farben | frei in " + FARBNAME[best3] +
                      " (davon spielstark) | Beispiele (frei, EDHREC-beliebteste zuerst) |")
        zeilen.append("|---|---|---|---|---|")
        for key, label, _, kern in d["pakete"]:
            soll = "–"
            if richt:
                m = richt.get("archetypen", {}).get(a_key, {}).get("pakete", {}).get(f"{a_key}.{key}")
                if m:
                    soll = f"{de(m['median'])} ({de(m['min'])}–{de(m['max'])})"
            bsp = ", ".join(k["name"] for k in z3[key][:6]) or "–"
            n_stark = sum(1 for k in z3[key] if stark(k))
            zeilen.append(f"| {label}{' *' if kern else ''} | {soll} | {len(z_alle[key])} | {len(z3[key])} ({n_stark}) | {bsp} |")
        zeilen.append("")
        schl = (richt or {}).get("archetypen", {}).get(a_key, {}).get("schluesselkarten", [])
        if schl:
            teile = []
            for s in schl:
                oid = namen.get(s["name"].lower()) or namen.get(s["name"].split(" // ")[0].lower())
                teile.append(f"{s['name']} ({status(oid, frei, besitz)})")
            zeilen.append("Schlüsselkarten laut EDHREC (hohe Synergie im Thema) – Status: " + "; ".join(teile) + ".\n")
    zeilen.append("\\* Kernpaket (zählt für die Ampel). Status der Schlüsselkarten: **frei** · im Deck (Deckname) · fehlt = nicht im Besitz oder vorgemerkt.\n")
    if a.decks:
        zeilen += deck_abschnitt(a.decks, karten, namen, richt, a.config)
    if not a.ohne_commander:
        zeilen += commander_abschnitt(frei, karten)
    text = "\n".join(zeilen)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text + "\n")
        print(f"Profil -> {a.out}")
    else:
        print(text)


def cmd_karten(a):
    karten, namen, _ = lade_karten()
    if a.archetyp not in ARCHETYPEN:
        sys.exit("Archetyp unbekannt: " + ", ".join(ARCHETYPEN))
    if a.alle:
        liste = {oid: 0 for oid, k in karten.items() if k["legal"] == "legal"}
    else:
        liste, _ = freie_karten(karten, namen, a.frei)
    if a.ohne_deck:
        _, im_deck, _ = lies_deck(a.ohne_deck, namen)
        liste = {oid: n for oid, n in liste.items() if oid not in im_deck}
    z = zaehle(liste, karten, a.archetyp, a.farben.upper() if a.farben else None)
    for key, label, _, kern in ARCHETYPEN[a.archetyp]["pakete"]:
        if a.paket and key != a.paket:
            continue
        print(f"\n{label} ({len(z[key])}):")
        for k in z[key][:a.limit]:
            print(f"  {k['name']} | {k['ci'] or 'C'} | MV {k['cmc']:g} | {front_typ(k)}"
                  + (f" | frei {liste[k['oid']]}" if not a.alle else f" | ab {k['eur']} €"))


def lies_deck(pfad, namen):
    """Moxfield-/Text-Deckliste -> (Commander-Namen, {oid: Anzahl}, unbekannt)."""
    rx = re.compile(r"^\s*(\d+)x?\s+(.+?)(?:\s+[\(\[][A-Za-z0-9_]+[\)\]](?:\s+\S+)?)?(?:\s+\*[A-Za-z]+\*)*\s*$")
    bloecke, cur = [], []
    for raw in open(pfad, encoding="utf-8-sig"):
        s = raw.strip()
        if s.startswith("//") or s.lower().rstrip(":") in ("commander", "deck", "mainboard", "sideboard"):
            if s.lower().startswith("// commander"):
                if cur:
                    bloecke.append(cur)
                cur = []
            continue
        if not s:
            if cur:
                bloecke.append(cur)
                cur = []
            continue
        m = rx.match(s)
        if m:
            cur.append((int(m.group(1)), m.group(2).strip()))
    if cur:
        bloecke.append(cur)
    cmdr = bloecke[-1] if len(bloecke) > 1 and sum(q for q, _ in bloecke[-1]) <= 2 else []
    deck, unbekannt = Counter(), []
    for b in bloecke:
        for q, n in b:
            oid = namen.get(n.lower()) or namen.get(n.split(" // ")[0].lower())
            if oid:
                deck[oid] += q
            else:
                unbekannt.append(n)
    return [n for _, n in cmdr], deck, unbekannt


def zaehle_deck(deck, karten, ohne_rollen=()):
    """deck: {oid: Anzahl} -> Kennzahlen (Rollen, Pakete aller Archetypen, Länder, Ø MV).
    ohne_rollen: Oracle-IDs (Commander), die bei den Rollen nicht zählen (wie deckbau.py)."""
    z = Counter()
    mv, n_sp = 0.0, 0
    for oid, q in deck.items():
        k = karten.get(oid)
        if not k:
            continue
        for r in (rollen(k) if oid not in ohne_rollen else ()):
            z[f"rolle.{r}"] += q
        for a_key, p in pakete_von(k):
            z[f"{a_key}.{p}"] += q
        if not ist_land(k):
            mv += (k["cmc"] or 0) * q
            n_sp += q
    z["mv"] = round(mv / n_sp, 2) if n_sp else 0
    return z


def cmd_deck(a):
    karten, namen, _ = lade_karten()
    cmdr, deck, unbekannt = lies_deck(a.deck, namen)
    richt = lade_richtwerte(a.daten)
    c_oids = {namen.get(n.lower()) or namen.get(n.split(" // ")[0].lower()) for n in cmdr}
    z = zaehle_deck(deck, karten, c_oids)
    print(f"Deck {a.deck}: {sum(deck.values())} Karten | Commander: {', '.join(cmdr) or '?'} | "
          f"Ø MV {de(z['mv'])} (Nichtländer inkl. Commander)")
    if unbekannt:
        print("nicht erkannt:", ", ".join(unbekannt))
    print("\nRollen (99 ohne Commander, wie deckbau.py pruefen):")
    for key, label in ROLLEN:
        soll = ""
        if richt:
            m = richt.get("alle", {}).get(f"rolle.{key}")
            if m:
                soll = f" (Median aller erhobenen Decks {de(m['median'])})"
        print(f"  {label}: {z['rolle.' + key]}{soll}")
    if a.archetyp:
        ziele = [a.archetyp]
    else:
        # ohne Vorgabe: die 3 Archetypen, deren Kernpakete das Deck am besten abdeckt
        ziele = sorted(ARCHETYPEN, key=lambda k: -deckung(z, richt, k))[:3]
        print("\nAm besten abgedeckte Archetypen: " + ", ".join(f"{ARCHETYPEN[k]['name']} ({deckung(z, richt, k) * 100:.0f} %)"
                                                             for k in ziele) + " – Einzelprüfung mit --archetyp")
    print("\nPakete" + (" (Richtwert = Median der Durchschnittsdecks des Archetyps):" if richt else ":"))
    for a_key in ziele:
        d = ARCHETYPEN[a_key]
        werte = []
        for key, label, _, kern in d["pakete"]:
            ist = z[f"{a_key}.{key}"]
            soll = None
            if richt:
                soll = richt.get("archetypen", {}).get(a_key, {}).get("pakete", {}).get(f"{a_key}.{key}")
            s = f"{label}: {ist}"
            if soll:
                s += f" / {de(soll['median'])}" + (" ⚠" if kern and ist < soll["min"] else "")
            werte.append(s)
        if a.archetyp or any(z[f"{a_key}.{key}"] for key, _, _, k in d["pakete"] if k):
            print(f"  {d['name']}: " + " | ".join(werte))
    if richt:
        print("\n⚠ = Kernpaket unter der kleinsten Anzahl der erhobenen Durchschnittsdecks.")


# ----------------------------------------------------------------- Datenerhebung (EDHREC)
BRACKET_PFAD = {1: "exhibition", 2: "core", 3: "upgraded", 4: "optimized", 5: "cedh"}


def edhrec(pfad, cache="cache/edhrec"):
    os.makedirs(cache, exist_ok=True)
    fn = os.path.join(cache, pfad.replace("/", "__") + ".json")
    if os.path.exists(fn) and time.time() - os.path.getmtime(fn) < 72 * 3600:
        d = json.load(open(fn, encoding="utf-8"))
        return d or None
    time.sleep(0.25)
    try:
        d = get_json(f"https://json.edhrec.com/pages/{pfad}.json")
        if not isinstance(d, dict) or "redirect" in d or "container" not in d:
            d = {}
    except Exception:
        d = {}
    json.dump(d, open(fn, "w", encoding="utf-8"))
    return d or None


def median_spanne(werte):
    return {"median": round(statistics.median(werte), 1), "min": min(werte), "max": max(werte)}


def cmd_daten(a):
    karten, namen, _ = lade_karten()
    b = BRACKET_PFAD.get(a.bracket)
    ergebnis = {"stand": time.strftime("%Y-%m-%d"), "bracket": a.bracket, "top": a.top,
                "methode": "EDHREC: Top-Commander der Themenseite (nach Deckzahl im Thema) -> Durchschnittsdeck "
                           "average-decks/<commander>/<bracket>/<thema> (Fallback ohne Bracket) -> Rollen und Pakete "
                           "über Scryfall-Tags gezählt; Median/Spanne über die Commander",
                "archetypen": {}, "alle": {}}
    alle_decks = []
    for a_key, d in ARCHETYPEN.items():
        decks = []
        top_karten = []
        themen = d["edhrec"]
        pro_thema = max(1, a.top // len(themen))      # mehrere Themen (Landfall, Kindred) teilen sich die Plätze
        gesehen = set()
        for thema in themen:
            seite = edhrec(f"tags/{thema}")
            if not seite:
                print(f"  Thema {thema}: keine Daten", file=sys.stderr)
                continue
            listen = {cl.get("header"): cl.get("cardviews", []) for cl in seite["container"]["json_dict"]["cardlists"]}
            # Schlüsselkarten: Kategorielisten der Themenseite (ohne Commander-/Neu-/Top-Listen) mit Synergie
            for kat in ("Creatures", "Instants", "Sorceries", "Utility Artifacts", "Enchantments", "Planeswalkers",
                        "Utility Lands", "Mana Artifacts"):
                for cv in listen.get(kat, []):
                    pot = cv.get("potential_decks") or 0
                    if pot and cv.get("synergy") is not None:
                        top_karten.append((cv["name"], cv["num_decks"] / pot, cv["synergy"], thema))
            cmds = sorted(listen.get("Top Commanders", []), key=lambda c: -(c.get("num_decks") or 0))
            genommen = 0
            for cv in cmds:
                if genommen >= pro_thema:
                    break
                slug = cv.get("sanitized")
                if slug in gesehen:
                    continue
                dd, pfad = None, None
                for p in ([f"average-decks/{slug}/{b}/{thema}"] if b else []) + [f"average-decks/{slug}/{thema}"]:
                    dd = edhrec(p)
                    n = (dd or {}).get("container", {}).get("json_dict", {}).get("card", {}).get("num_decks") or 0
                    if dd and n >= a.min_decks:
                        pfad = p
                        break
                    dd = None
                if not dd:
                    continue
                deck = Counter()
                for typ, eintraege in dd["deck"]["cards"].items():
                    for name, q in eintraege:
                        oid = namen.get(name.lower()) or namen.get(name.split(" // ")[0].lower())
                        if oid:
                            deck[oid] += q
                for name in dd["deck"].get("commander", []):
                    oid = namen.get(name.lower())
                    if oid:
                        deck[oid] += 1
                z = zaehle_deck(deck, karten)
                z["karten"] = sum(deck.values())
                n = dd["container"]["json_dict"]["card"]["num_decks"]
                decks.append({"commander": cv["name"], "thema": thema, "pfad": pfad, "decks": n, "werte": dict(z)})
                gesehen.add(slug)
                genommen += 1
        if not decks:
            continue
        # Schlüsselkarten über alle Themen des Archetyps: in genügend Themenseiten vorhanden, hohe Synergie
        je_karte = defaultdict(list)
        for name, inc, syn, thema in top_karten:
            je_karte[name].append((inc, syn))
        n_th = len({t for *_, t in top_karten}) or 1
        min_seiten = max(1, round(n_th * 0.4))
        min_syn = 0.05 if n_th > 2 else 0.12
        schl = []
        for name, werte in je_karte.items():
            if len(werte) < min_seiten:
                continue
            inc = statistics.mean(w[0] for w in werte)
            syn = statistics.mean(w[1] for w in werte)
            if syn >= min_syn and inc >= 0.12:
                schl.append({"name": name, "inclusion": round(inc, 3), "synergy": round(syn, 3), "seiten": len(werte)})
        schl.sort(key=lambda s: -(s["inclusion"] * s["synergy"]))
        top_karten = schl[:15]
        schluessel = sorted({k for dk in decks for k in dk["werte"]})
        stat = {}
        for k in schluessel:
            stat[k] = median_spanne([dk["werte"].get(k, 0) for dk in decks])
        ergebnis["archetypen"][a_key] = {
            "name": d["name"], "commander": [{k: dk[k] for k in ("commander", "thema", "pfad", "decks")} for dk in decks],
            "rollen": {k: v for k, v in stat.items() if k.startswith("rolle.")},
            "pakete": {k: v for k, v in stat.items() if k.startswith(f"{a_key}.")},
            "fremdpakete": {k: v for k, v in stat.items() if "." in k and not k.startswith(("rolle.", f"{a_key}."))
                            and v["median"] > 0},
            "mv": stat.get("mv"), "schluesselkarten": top_karten}
        alle_decks += decks
        print(f"{d['name']}: {len(decks)} Durchschnittsdecks ({sum(dk['decks'] for dk in decks)} Decklisten)")
    for k in sorted({k for dk in alle_decks for k in dk["werte"]}):
        ergebnis["alle"][k] = median_spanne([dk["werte"].get(k, 0) for dk in alle_decks])
    json.dump(ergebnis, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"-> {a.out}")


def main():
    import signal
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("profil")
    p.add_argument("--frei", help="Liste der freien Karten (Format 07), wenn keine mtg.sqlite da ist")
    p.add_argument("--daten", default="archetypen_daten.json")
    p.add_argument("--out")
    p.add_argument("--hinweis")
    p.add_argument("--ohne-commander", action="store_true", help="Abschnitt freie Commander (EDHREC-Abruf) weglassen")
    p.add_argument("--decks", nargs="*", help="Soll-Stände (claude/decks/*.txt): Status der Schlüsselkarten (statt mtg.sqlite) "
                                               "und Abschnitt „Commander-Decks im Archetyp-Raster“")
    p.add_argument("--einschaetzung", help="Markdown-Datei mit Claudes Einschätzung, wird nach dem Kopf eingefügt")
    p.add_argument("--config", default="deck_namen.json", help="deck_namen.json (Strategie je Commander) für den Deck-Abschnitt")
    p = sp.add_parser("karten")
    p.add_argument("archetyp")
    p.add_argument("--paket")
    p.add_argument("--farben")
    p.add_argument("--frei")
    p.add_argument("--alle", action="store_true", help="alle Commander-legalen Karten statt nur freier")
    p.add_argument("--ohne-deck", help="Deckdatei: Karten, die schon im Deck stecken, weglassen")
    p.add_argument("--limit", type=int, default=40)
    p = sp.add_parser("deck")
    p.add_argument("deck")
    p.add_argument("--archetyp", choices=list(ARCHETYPEN))
    p.add_argument("--daten", default="archetypen_daten.json")
    p = sp.add_parser("daten")
    p.add_argument("--top", type=int, default=6)
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--min-decks", type=int, default=40)
    p.add_argument("--out", default="archetypen_daten.json")
    a = ap.parse_args()
    {"profil": cmd_profil, "karten": cmd_karten, "deck": cmd_deck, "daten": cmd_daten}[a.cmd](a)


if __name__ == "__main__":
    main()
