#!/usr/bin/env python3
"""mtg_db.py – Sammlungs-Datenbank und Deck-Werkzeuge für das MTG-Projekt.

Baut aus dem Moxfield-/ManaBox-Sammlungsexport, den Moxfield-Deckexporten und den
Scryfall-Bulk-Daten eine SQLite-Datenbank (Standard: mtg.sqlite im aktuellen Ordner).

Befehle
  build  --sammlung <csv...> [--decks <txt|csv...>] [--binder-decks [MUSTER]] [--bulk DIR]
         [--config deck_namen.json]
         DB neu bauen; Scryfall-Bulk wird geladen, wenn älter als 20 h. Sammlung: Moxfield- oder
         ManaBox-CSV (enthält beim Nutzer auch alle Deckkarten). Decks: Moxfield-/ManaBox-Text oder
         CSV (Soll-Stände claude/decks/*.txt); --vormerkungen <csv> (Standard data/vormerkungen.csv) zieht
         reservierte Karten von „frei“ ab; --scan-decks <csv…> liest ManaBox-Scans als Decklisten (nicht Teil
         des Bestands); --binder-decks legt Decks aus Bindern der Sammlungsdatei an.
         Bestand = Basis + Journal (claude/sammlung/buchungen.csv); das Projekt ist die Hauptdatenbank.
  laender [<deck>] [--plan "Plains=12, Swamp=10"]
                                Standardländer: Bedarf vs. Besitz (abzüglich anderer Decks), Nachkauf
  sammlung                      Bestandsübersicht (Menge, Wert, Farben, Typen, teuerste Karten)
  decks                         alle Decks mit Format, Farben, Kartenzahl, Herkunft
  namen                         Namensvorschläge alt -> neu (einheitliches Schema)
  besitz <deck>                 Besitz-Abgleich eines Decks (fehlt / Konflikte mit anderen Decks)
  mehrfach                      Karten, die mehr Decks brauchen, als Exemplare da sind
  bracket <deck>                Bracket-Check: lokal + Commander Spellbook (estimate-bracket)
  export <deck> [--sets]        Liste zum Einfügen in Moxfield (wie Moxfield-Export)
  suche [--tag T] [--farben RWB] [--max-mv N] [--text TXT] [--typ TYP]
        [--nur-besitz | --nur-frei] [--limit N]       Funktionssuche über alle Karten
  bestand-export <alle.csv> [--frei <frei.csv>] [--hinweis TEXT]
                                Gesamtbestand je Karte + Liste der freien Karten (nicht in Decks)
  sql "<SELECT …>"              freie Abfrage
  exemplare <Karte|Deck>        jedes physische Exemplar (Druck, Sprache, Foil) mit Ort: Deck, Vormerkung oder frei
  drucke <entwurf.txt> [--deck D] [--idee I-nnn] --out <entwurf_drucke.txt>
                                Entwurf mit eigenen Drucken: Karten aus dem Deck D behalten dessen Exemplare, neue Karten
                                bekommen freie Exemplare; ohne Exemplar = Kauf (Grundlage für Deck-PDF und Tausch)
  snapshot <ordner> [--deck D] [--hinweis T] [--drucke]
                                Soll-Stand aller Decks als Moxfield-Text (Projektordner claude/decks/); Drucke stehen
                                drin, wenn sie bekannt sind (aus der Deckliste/dem Scan) – mit --drucke auch die
                                über die Exemplar-Zuordnung ermittelten
  scan <manabox.csv> [--buchen] [--verdacht-buchen] [--moxfield zugang.csv] [--beleg T]
                                ManaBox-Scan prüfen (Datei-Hash, schon gebuchte Scan-Zeilen, Druck schon im
                                Bestand, Sprache) und als Zugang ins Journal buchen
  moxfield-export <out.csv> [--basis B] [--journal J]
                                Gesamtbestand (Basis + Journal) als Moxfield-Sammlungs-CSV
  manabox-zu-moxfield <manabox.csv> [--sammlung out.csv] [--deck out.txt] [--sets] [--tausch 0] [--tags T]
                                ManaBox-Scan -> Moxfield-Sammlungsimport (CSV) und Moxfield-Deckimport (TXT)
  vergleich <alt> <neu> [--titel T] [--art deck|sammlung] [--csv diff.csv]
                                Deck- oder Sammlungsdateien vergleichen -> Eintrag fürs Änderungsprotokoll
  vergleich --snapshots <ordner>
                                alle Decks der Datenbank gegen den Soll-Stand -> Abweichungen als Protokolleinträge
<deck> = Deck-ID oder Teil des alten/neuen Namens bzw. des Commanders.

Namensschema (Stand 26.10.2026, max. 100 Zeichen):
  <Format> | <Deckname> | <Farbname (Kürzel)> | <Strategie> | <Herkunft>[ | In Arbeit]
"""
import argparse
import csv
import gzip
import json
import os
import re
import sqlite3
import sys
import time
import unicodedata
import urllib.request
from collections import Counter, defaultdict

UA = {"User-Agent": "MTG-Projekt/1.0", "Accept": "application/json"}
BULK_TYPES = ["default_cards", "oracle_tags", "rulings"]
FORMATE = ["standard", "pioneer", "modern", "legacy", "vintage"]
FORMAT_ANZEIGE = {"standard": "Standard", "pioneer": "Pioneer", "modern": "Modern",
                  "legacy": "Legacy", "vintage": "Vintage", "commander": "Commander"}
WUBRG = "WUBRG"
FARBE_DE = {"W": "Weiß", "U": "Blau", "B": "Schwarz", "R": "Rot", "G": "Grün"}
# Farbkombination -> (Name, Reihenfolge wie in Manakosten)
FARBNAMEN = {
    "WU": ("Azorius", "WU"), "UB": ("Dimir", "UB"), "BR": ("Rakdos", "BR"),
    "RG": ("Gruul", "RG"), "GW": ("Selesnya", "GW"), "WB": ("Orzhov", "WB"),
    "UR": ("Izzet", "UR"), "BG": ("Golgari", "BG"), "RW": ("Boros", "RW"),
    "GU": ("Simic", "GU"),
    "GWU": ("Bant", "GWU"), "WUB": ("Esper", "WUB"), "UBR": ("Grixis", "UBR"),
    "BRG": ("Jund", "BRG"), "RGW": ("Naya", "RGW"), "WBG": ("Abzan", "WBG"),
    "URW": ("Jeskai", "URW"), "BGU": ("Sultai", "BGU"), "RWB": ("Mardu", "RWB"),
    "GUR": ("Temur", "GUR"),
}
FARBNAMEN = {frozenset(k): v for k, v in FARBNAMEN.items()}
PRECON_SETTYPEN = {"commander", "starter", "duel_deck", "box", "planechase",
                   "archenemy", "premium_deck", "arsenal", "spellbook"}
ARCHETYPEN = ["aggro", "midrange", "control", "combo", "tempo", "ramp", "stompy", "burn"]
THEMEN = ["landfall", "tokens", "token", "aristocrats", "voltron", "spellslinger",
          "reanimator", "mill", "lifegain", "blink", "counters", "elementals",
          "superfriends", "artifacts", "enchantress", "wheels", "storm", "sacrifice"]
COND = {"mint": "NM", "near_mint": "NM", "near mint": "NM", "nm": "NM",
        "excellent": "EX", "good (lightly played)": "LP", "lightly played": "LP",
        "good": "GD", "light_played": "LP", "played": "PL", "heavily played": "HP",
        "poor": "DMG", "damaged": "DMG"}
LANG = {"english": "en", "german": "de", "french": "fr", "italian": "it", "spanish": "es",
        "portuguese": "pt", "japanese": "ja", "korean": "ko", "russian": "ru",
        "chinese simplified": "zhs", "chinese traditional": "zht"}


# ----------------------------------------------------------------- Hilfsfunktionen
def fold(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower().strip()


def front(name):
    return str(name).split(" // ")[0].strip()


def ci_str(cols):
    return "".join(c for c in WUBRG if c in set(cols))


def farbname(ci):
    s = frozenset(ci)
    if not s:
        return "Farblos"
    if len(s) == 1:
        c = next(iter(s))
        return f"Mono-{FARBE_DE[c]}"
    if len(s) == 5:
        return "5-Farben"
    if len(s) == 4:
        fehlt = next(c for c in WUBRG if c not in s)
        return f"4-Farben ohne {FARBE_DE[fehlt]}"
    name, order = FARBNAMEN[s]
    return f"{name} ({'/'.join(FARBE_DE[c] for c in order)})"


def farbname_kurz(ci):
    """Kompakte Farbangabe für Decknamen (Moxfield erlaubt max. 100 Zeichen):
    Gilde/Shard/Wedge + WUBRG-Kürzel in Manakosten-Reihenfolge, z. B. 'Mardu (RWB)'."""
    s = frozenset(ci)
    if not s:
        return "Farblos"
    if len(s) == 1:
        return f"Mono-{FARBE_DE[next(iter(s))]}"
    if len(s) == 5:
        return "5-Farben"
    if len(s) == 4:
        return f"4-Farben ({ci_str(s)})"
    name, order = FARBNAMEN[s]
    return f"{name} ({order})"


MAX_NAME = 100   # Moxfield-Grenze für Decknamen


def get_json(url, data=None):
    headers = dict(UA)
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def ensure_bulk(bulk_dir, max_age_h=20):
    os.makedirs(bulk_dir, exist_ok=True)
    meta = {}
    liste = None
    for t in BULK_TYPES:
        fn = os.path.join(bulk_dir, f"{t}.jsonl.gz")
        if os.path.exists(fn) and time.time() - os.path.getmtime(fn) < max_age_h * 3600:
            meta[t] = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(fn)))
            continue
        if liste is None:
            liste = {x["type"]: x for x in get_json("https://api.scryfall.com/bulk-data")["data"]}
        x = liste[t]
        url = x.get("jsonl_download_uri") or x.get("download_uri")
        print(f"lade {t} …", file=sys.stderr)
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=600) as r, open(fn + ".part", "wb") as out:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
        os.replace(fn + ".part", fn)
        meta[t] = x["updated_at"][:16].replace("T", " ")
    return meta


def iter_jsonl(fn):
    op = gzip.open if open(fn, "rb").read(2) == b"\x1f\x8b" else open
    with op(fn, "rt", encoding="utf-8") as f:
        first = f.read(1)
        f.seek(0)
        if first == "[":                      # altes JSON-Array-Format
            for obj in json.load(f):
                yield obj
        else:
            for line in f:
                line = line.strip().rstrip(",")
                if line and line not in ("[", "]"):
                    yield json.loads(line)


# ----------------------------------------------------------------- Schema
SCHEMA = """
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE cards(oracle_id TEXT PRIMARY KEY, name TEXT, front TEXT, mana_cost TEXT,
  cmc REAL, type_line TEXT, oracle_text TEXT, colors TEXT, color_identity TEXT,
  keywords TEXT, produced_mana TEXT, layout TEXT, legal_commander TEXT,
  legal_standard TEXT, legal_pioneer TEXT, legal_modern TEXT, legal_legacy TEXT,
  legal_vintage TEXT, legal_pauper TEXT, game_changer INTEGER, reserved INTEGER,
  edhrec_rank INTEGER, eur_min REAL, eur_min_print TEXT, pt TEXT);
CREATE TABLE prints(scryfall_id TEXT PRIMARY KEY, oracle_id TEXT, name TEXT, set_code TEXT,
  set_name TEXT, set_type TEXT, cn TEXT, rarity TEXT, lang TEXT, released_at TEXT,
  eur REAL, eur_foil REAL, eur_etched REAL, finishes TEXT, promo INTEGER);
CREATE INDEX prints_setcn ON prints(set_code, cn);
CREATE INDEX prints_oid ON prints(oracle_id);
CREATE TABLE names(key TEXT, oracle_id TEXT, prio INTEGER);
CREATE INDEX names_key ON names(key);
CREATE TABLE tags(oracle_id TEXT, tag TEXT, PRIMARY KEY(oracle_id, tag)) WITHOUT ROWID;
CREATE INDEX tags_tag ON tags(tag);
CREATE TABLE tag_info(tag TEXT PRIMARY KEY, description TEXT);
CREATE TABLE rulings(oracle_id TEXT, published_at TEXT, comment TEXT);
CREATE INDEX rulings_oid ON rulings(oracle_id);
CREATE TABLE collection(id INTEGER PRIMARY KEY, source TEXT, datei TEXT, name TEXT,
  set_code TEXT, cn TEXT, finish TEXT, qty INTEGER, trade_qty INTEGER, condition TEXT,
  lang TEXT, tags TEXT, modified TEXT, altered TEXT, proxy TEXT, price_paid TEXT,
  binder TEXT, binder_type TEXT, scryfall_id TEXT, oracle_id TEXT, match TEXT);
CREATE TABLE decks(deck_id INTEGER PRIMARY KEY, datei TEXT, export_datum TEXT,
  alter_name TEXT, format TEXT, format_label TEXT, format_legal TEXT, commander TEXT,
  farben TEXT, karten INTEGER, precon_set TEXT, precon_set_name TEXT, precon_anteil REAL,
  herkunft TEXT, strategie TEXT, status TEXT, neuer_name TEXT, kurz TEXT, hinweise TEXT);
CREATE TABLE deck_cards(deck_id INTEGER, board TEXT, name TEXT, qty INTEGER,
  set_code TEXT, cn TEXT, oracle_id TEXT);
CREATE VIEW v_besitz AS
  SELECT oracle_id, SUM(qty) AS besitz FROM collection
  WHERE oracle_id IS NOT NULL AND lower(proxy) <> 'true' GROUP BY oracle_id;
-- Die Sammlung enthält auch alle Deckkarten. Bedarf = alles, was physisch in Decks steckt
-- (Haupt-, Commander-, Sideboard; ohne Maybeboard), inkl. Standardländer -> frei = Besitz - Bedarf - Vormerkungen.
CREATE VIEW v_bedarf AS
  SELECT d.oracle_id, SUM(d.qty) AS bedarf, COUNT(DISTINCT d.deck_id) AS decks,
         GROUP_CONCAT(DISTINCT k.kurz) AS deck_ids
  FROM deck_cards d JOIN decks k USING(deck_id)
  WHERE d.board IN ('main','commander','sideboard','companion') AND d.oracle_id IS NOT NULL
  GROUP BY d.oracle_id;
CREATE VIEW v_basics AS
  SELECT oracle_id, name FROM cards WHERE type_line LIKE 'Basic%Land%';
-- Vormerkungen: Karten, die eine nicht freigegebene Idee (10_Geplante-Kaeufe-und-Ideen) reserviert hat.
-- weich = 1 (Idee-ID „V-nnn“, geplanter Verkauf): zieht NICHT von frei ab, die Werkzeuge warnen nur.
CREATE TABLE vormerkungen(idee TEXT, name TEXT, oracle_id TEXT, qty INTEGER, datum TEXT, hinweis TEXT,
  weich INTEGER DEFAULT 0);
CREATE VIEW v_vorgemerkt AS
  SELECT oracle_id, SUM(qty) AS vorgemerkt, GROUP_CONCAT(DISTINCT idee) AS ideen
  FROM vormerkungen WHERE oracle_id IS NOT NULL AND weich = 0 GROUP BY oracle_id;
CREATE VIEW v_verkauf_geplant AS
  SELECT oracle_id, SUM(qty) AS verkauf_geplant, GROUP_CONCAT(DISTINCT idee) AS verkauf_ideen
  FROM vormerkungen WHERE oracle_id IS NOT NULL AND weich = 1 GROUP BY oracle_id;
-- Exemplare: jedes physische Exemplar (Basis + Journal netto) mit Ort. zuordnung: druck (Set + Nummer aus der
-- Deckliste/dem Scan), zeitstempel (gemeinsamer Erfassungszeitpunkt der Deckkarten), set (Precon-Set), geschätzt
CREATE TABLE exemplare(nr INTEGER PRIMARY KEY, oracle_id TEXT, name TEXT, set_code TEXT, cn TEXT, finish TEXT,
  lang TEXT, modified TEXT, deck_id INTEGER, zuordnung TEXT, idee TEXT, verkauf TEXT);
CREATE INDEX exemplare_oid ON exemplare(oracle_id);
-- frei (Sammlung) = Besitz - Deckkarten - Vormerkungen
CREATE VIEW v_karten AS
  SELECT c.oracle_id, c.name, c.cmc, c.type_line, c.color_identity, c.game_changer,
         c.eur_min, COALESCE(b.besitz,0) AS besitz, COALESCE(v.bedarf,0) AS in_decks,
         MAX(COALESCE(b.besitz,0) - COALESCE(v.bedarf,0) - COALESCE(r.vorgemerkt,0), 0) AS frei, v.deck_ids,
         COALESCE(r.vorgemerkt,0) AS vorgemerkt, r.ideen,
         COALESCE(g.verkauf_geplant,0) AS verkauf_geplant, g.verkauf_ideen
  FROM cards c LEFT JOIN v_besitz b USING(oracle_id) LEFT JOIN v_bedarf v USING(oracle_id)
  LEFT JOIN v_vorgemerkt r USING(oracle_id) LEFT JOIN v_verkauf_geplant g USING(oracle_id);
"""


# ----------------------------------------------------------------- Build
def load_cards(con, bulk_dir):
    cards, prints, names = {}, [], []
    eur_best = {}
    for c in iter_jsonl(os.path.join(bulk_dir, "default_cards.jsonl.gz")):
        if "paper" not in c.get("games", []) or c.get("layout") in (
                "token", "double_faced_token", "emblem", "art_series", "vanguard", "scheme",
                "planar"):
            continue
        faces = c.get("card_faces") or []
        oid = c.get("oracle_id") or (faces[0].get("oracle_id") if faces else None)
        if not oid:
            continue
        p = c.get("prices") or {}
        f = lambda k: float(p[k]) if p.get(k) else None
        prints.append((c["id"], oid, c["name"], c["set"], c.get("set_name"), c.get("set_type"),
                       c.get("collector_number"), c.get("rarity"), c.get("lang"),
                       c.get("released_at"), f("eur"), f("eur_foil"), f("eur_etched"),
                       ",".join(c.get("finishes", [])), int(bool(c.get("promo")))))
        if c.get("set_type") not in ("memorabilia", "token", "minigame", "funny") and not c.get("oversized"):
            e = f("eur") or f("eur_foil") or f("eur_etched")
            if e is not None and (oid not in eur_best or e < eur_best[oid][0]):
                eur_best[oid] = (e, f"{c['set'].upper()} {c.get('collector_number')}")
        if oid in cards:
            continue
        txt = c.get("oracle_text")
        if txt is None and faces:
            txt = "\n// \n".join(fc.get("oracle_text", "") for fc in faces)
        mc = c.get("mana_cost")
        if mc is None and faces:
            mc = " // ".join(fc.get("mana_cost", "") for fc in faces)
        cols = c.get("colors")
        if cols is None and faces:
            cols = sorted({x for fc in faces for x in fc.get("colors", [])})
        lg = c.get("legalities", {})
        pt_teile = []
        for q in ([c] if not faces or c.get("power") is not None or c.get("loyalty") else faces):
            if q.get("power") is not None:
                pt_teile.append(f"{q['power']}/{q.get('toughness')}")
            elif q.get("loyalty"):
                pt_teile.append(f"Loyalität {q['loyalty']}")
            elif q.get("defense"):
                pt_teile.append(f"Verteidigung {q['defense']}")
        cards[oid] = [oid, c["name"], front(c["name"]), mc, c.get("cmc"), c.get("type_line"),
                      txt, ci_str(cols or []), ci_str(c.get("color_identity", [])),
                      ",".join(c.get("keywords", [])), ci_str(c.get("produced_mana", []) or []),
                      c.get("layout"), lg.get("commander"), lg.get("standard"),
                      lg.get("pioneer"), lg.get("modern"), lg.get("legacy"), lg.get("vintage"),
                      lg.get("pauper"), int(bool(c.get("game_changer"))),
                      int(bool(c.get("reserved"))), c.get("edhrec_rank"), None, None,
                      " // ".join(pt_teile) or None]
        names.append((c["name"].lower(), oid, 0))
        names.append((front(c["name"]).lower(), oid, 1))
        for fc in faces:
            names.append((fc["name"].lower(), oid, 2))
        names.append((fold(c["name"]), oid, 3))
        names.append((fold(front(c["name"])), oid, 3))
    for oid, (e, pr) in eur_best.items():
        if oid in cards:
            cards[oid][22], cards[oid][23] = e, pr
    con.executemany(f"INSERT INTO cards VALUES ({','.join('?' * 25)})", cards.values())
    con.executemany(f"INSERT OR IGNORE INTO prints VALUES ({','.join('?' * 15)})", prints)
    con.executemany("INSERT INTO names VALUES (?,?,?)", names)
    return len(cards), len(prints)


def load_tags(con, bulk_dir):
    tags = list(iter_jsonl(os.path.join(bulk_dir, "oracle_tags.jsonl.gz")))
    by_id = {t["id"]: t for t in tags}
    memo = {}

    def ancestors(tid, seen=()):
        if tid in memo:
            return memo[tid]
        out = set()
        for pid in by_id.get(tid, {}).get("parent_ids", []):
            if pid in by_id and pid not in seen:
                out.add(by_id[pid]["slug"])
                out |= ancestors(pid, seen + (tid,))
        memo[tid] = out
        return out

    rows = set()
    for t in tags:
        slugs = {t["slug"]} | ancestors(t["id"])
        for tg in t.get("taggings", []):
            for s in slugs:
                rows.add((tg["oracle_id"], s))
    con.executemany("INSERT OR IGNORE INTO tags VALUES (?,?)", rows)
    con.executemany("INSERT OR IGNORE INTO tag_info VALUES (?,?)",
                    [(t["slug"], t.get("description")) for t in tags])
    return len(rows)


def load_rulings(con, bulk_dir):
    rows = [(r["oracle_id"], r["published_at"], r["comment"])
            for r in iter_jsonl(os.path.join(bulk_dir, "rulings.jsonl.gz"))]
    con.executemany("INSERT INTO rulings VALUES (?,?,?)", rows)
    return len(rows)


def resolve_name(con, name):
    for key in (name.lower(), front(name).lower(), fold(name), fold(front(name))):
        r = con.execute("SELECT oracle_id FROM names WHERE key=? ORDER BY prio LIMIT 1",
                        (key,)).fetchone()
        if r:
            return r[0]
    return None


COLMAP = {
    # ManaBox (Export- und Import-Spaltennamen, Groß-/Kleinschreibung egal)
    "name": "name", "card name": "name", "set code": "set", "set name": "set_name",
    "collector number": "cn", "card number": "cn", "foil": "finish", "rarity": "rarity",
    "quantity": "qty", "manabox id": "manabox_id", "scryfall id": "scryfall_id",
    "purchase price": "price_paid", "misprint": "misprint", "altered": "altered",
    "condition": "condition", "language": "lang", "binder name": "binder",
    "binder type": "binder_type", "binder": "binder", "list name": "binder",
    # Moxfield
    "count": "qty", "tradelist count": "trade_qty", "edition": "set", "tags": "tags",
    "last modified": "modified", "alter": "altered", "proxy": "proxy",
    # ManaBox: Zeitpunkt des Scans; Journal: Buchungsspalten
    "added": "added", "buchung": "buchung", "datum": "datum", "beleg": "beleg",
}


def read_csv_rows(path):
    """CSV (ManaBox oder Moxfield, Trennzeichen egal) -> (Quelle, vereinheitlichte Zeilen)."""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rd = csv.DictReader(fh, dialect=dialect)
        cols = {c: COLMAP.get(c.strip().lower()) for c in rd.fieldnames}
        lower = {c.strip().lower() for c in rd.fieldnames}
        source = "manabox" if lower & {"scryfall id", "set code", "manabox id", "binder name"} else "moxfield"
        rows = [{v: (row.get(k) or "").strip() for k, v in cols.items() if v} for row in rd]
    return source, rows


def match_print(con, r):
    """Druckversion finden: Scryfall-ID > Set + Nummer > Name."""
    setc, cn = r.get("set", "").lower(), r.get("cn", "")
    sid = r.get("scryfall_id") or None
    if sid:
        x = con.execute("SELECT oracle_id FROM prints WHERE scryfall_id=?", (sid,)).fetchone()
        if x:
            return sid, x[0], "id"
    if setc and cn:
        x = con.execute("SELECT scryfall_id, oracle_id FROM prints WHERE set_code=? AND cn=?",
                        (setc, cn)).fetchone()
        if x:
            return x[0], x[1], "set+cn"
    oid = resolve_name(con, r.get("name", ""))
    return sid, oid, ("name" if oid else "none")


def load_collection(con, path):
    source, rows = read_csv_rows(path)
    for r in rows:
        fin = r.get("finish", "").lower()
        fin = "foil" if fin == "foil" else "etched" if fin == "etched" else "nonfoil"
        sid, oid, match = match_print(con, r)
        tq = r.get("trade_qty")
        con.execute("INSERT INTO collection(source,datei,name,set_code,cn,finish,qty,trade_qty,"
                    "condition,lang,tags,modified,altered,proxy,price_paid,binder,binder_type,"
                    "scryfall_id,oracle_id,match) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (source, os.path.basename(path), r.get("name"), r.get("set", "").lower(),
                     r.get("cn", ""), fin, int(float(r.get("qty") or 1)),
                     int(float(tq)) if tq else None,
                     COND.get(r.get("condition", "").lower(), r.get("condition", "")),
                     LANG.get(r.get("lang", "").lower(), r.get("lang", "").lower()),
                     r.get("tags"), r.get("modified"), r.get("altered"),
                     r.get("proxy") or "False", r.get("price_paid"),
                     r.get("binder") or None, (r.get("binder_type") or "").lower() or None,
                     sid, oid, match))
    return len(rows), source


# Decktext: Moxfield ("1 Name", "1 Name (SET) 123 *F*"), ManaBox/MTGO/Arena-Varianten
# ("1x Name", "1 Name [SET] 123", "SB: 1 Name", Überschriften wie "Commander (1)").
LINE = re.compile(r"^\s*(SB:\s*)?(\d+)x?\s+(.+?)"
                  r"(?:\s+[\(\[]([A-Za-z0-9_]+)[\)\]](?:\s+([^\s#*]+))?)?"
                  r"((?:\s+\*[A-Za-z]+\*)*)((?:\s+#\S+)*)\s*$")
HEADERS = {"commander": "commander", "commanders": "commander", "deck": "main",
           "main": "main", "mainboard": "main", "main deck": "main", "maindeck": "main",
           "sideboard": "sideboard", "maybeboard": "maybeboard", "maybe": "maybeboard",
           "considering": "maybeboard", "companion": "companion", "tokens": "skip",
           "token": "skip", "about": "skip"}


def header_key(s):
    k = s.lstrip("/ #").strip()
    k = re.sub(r"\s*\(\d+\)\s*$", "", k)
    return k.rstrip(":").strip().lower()


def parse_deck(path):
    """-> Liste von Blöcken (Board oder None, [(Anzahl, Name, Set, Nummer), …])."""
    if path.lower().endswith(".csv"):
        _, rows = read_csv_rows(path)
        cards = [(int(float(r.get("qty") or 1)), r.get("name", ""), r.get("set", "").lower(),
                  r.get("cn", "")) for r in rows if r.get("name")]
        return [(None, cards)]
    blocks, cur, header, sb = [], [], None, []
    with open(path, encoding="utf-8-sig") as fh:
        for raw in fh:
            s = raw.strip()
            if not s:
                if cur:
                    blocks.append((header, cur))
                    cur, header = [], None
                continue
            key = header_key(s)
            if key in HEADERS and not LINE.match(s):
                if cur:
                    blocks.append((header, cur))
                    cur = []
                header = HEADERS[key]
                continue
            if s.startswith("//"):
                continue
            m = LINE.match(s)
            if m:
                ziel = sb if m.group(1) else cur
                ziel.append((int(m.group(2)), m.group(3).strip(), (m.group(4) or "").lower(),
                             m.group(5) or ""))
            else:
                cur.append((0, s, "", ""))
    if cur:
        blocks.append((header, cur))
    if sb:
        blocks.append(("sideboard", sb))
    return [(h, c) for h, c in blocks if h != "skip"]


def slug_name(datei):
    base = os.path.basename(datei)
    base = re.sub(r"-(\d{8})-(\d{6})\.(txt|csv)$", "", base)
    base = re.sub(r"\.(txt|csv)$", "", base)
    return base.replace("--", " - ").replace("-", " ").replace("_", " ").strip()


def export_datum(datei):
    m = re.search(r"-(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})\d{2}\.(txt|csv)$", datei)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}" if m else None


def is_commander_eligible(con, oid):
    r = con.execute("SELECT type_line, oracle_text FROM cards WHERE oracle_id=?", (oid,)).fetchone()
    if not r:
        return False
    tl, tx = r[0] or "", r[1] or ""
    return ("Legendary" in tl and any(t in tl for t in ("Creature", "Vehicle", "Spacecraft"))) \
        or "can be your commander" in tx or "Background" in tl


def config_for(config, name):
    """Eintrag aus deck_namen.json über einen Teil des Dateinamens/Decknamens.
    Mehrere Alternativen mit '|' trennen (z. B. alter und neuer Moxfield-Name)."""
    n = re.sub(r"\s+", " ", fold(name))
    for k, v in config.items():
        art, _, muster = k.partition(":")
        if art in ("slug", "deck", "binder") and any(
                m.strip() and re.sub(r"\s+", " ", fold(m)) in n for m in muster.split("|")):
            return v
    return {}


def assign_commander(con, rows, name, config):
    """Commander setzen, wenn die Liste keinen markiert: deck_namen.json > Erkennung.
    rows: Listen [deck_id, board, name, qty, set, cn, oid]. Gibt Hinweis oder None zurück."""
    if any(r[1] == "commander" for r in rows):
        return None
    cfg = config_for(config, name)
    main = [r for r in rows if r[1] == "main"]
    total = sum(r[3] for r in main)
    wunsch = cfg.get("commander")
    if wunsch:
        wunsch = [wunsch] if isinstance(wunsch, str) else wunsch
        for w in wunsch:
            hit = next((r for r in main if front(r[2]).lower() == front(w).lower()), None)
            if hit:
                hit[1] = "commander"
            else:
                rows.append([rows[0][0] if rows else 0, "commander", w, 1, "", "", resolve_name(con, w)])
        return None
    if total < 90:
        return None
    ci_all = set()
    for r in main:
        if r[6]:
            x = con.execute("SELECT color_identity FROM cards WHERE oracle_id=?", (r[6],)).fetchone()
            ci_all |= set(x[0] or "")
    kand = []
    for r in main:
        if r[6] and is_commander_eligible(con, r[6]):
            x = con.execute("SELECT color_identity FROM cards WHERE oracle_id=?", (r[6],)).fetchone()
            if set(x[0] or "") == ci_all:
                kand.append(r)
    if len(kand) > 1:
        # Decks heißen oft nach dem Commander: Kandidat, dessen Vorname im Decknamen steht
        imnamen = [r for r in kand if re.split(r"[ ,]", front(r[2]))[0].lower() in name.lower()]
        if len(imnamen) == 1:
            kand = imnamen
    if len(kand) == 1:
        kand[0][1] = "commander"
        return f"Commander erkannt (nicht markiert): {kand[0][2]} – bitte bestätigen"
    if kand:
        return ("Commander nicht eindeutig (" + ", ".join(r[2] for r in kand)
                + ") – in deck_namen.json festlegen")
    return "kein Commander erkennbar – in deck_namen.json festlegen"


def insert_deck(con, deck_id, datei, alter_name, datum, rows, config):
    hinweis = assign_commander(con, rows, alter_name, config)
    con.executemany("INSERT INTO deck_cards VALUES (?,?,?,?,?,?,?)", [tuple(r) for r in rows])
    con.execute("INSERT INTO decks(deck_id, datei, export_datum, alter_name) VALUES (?,?,?,?)",
                (deck_id, datei, datum, alter_name))
    analyse_deck(con, deck_id, config)
    if hinweis:
        alt = con.execute("SELECT hinweise FROM decks WHERE deck_id=?", (deck_id,)).fetchone()[0]
        con.execute("UPDATE decks SET hinweise=? WHERE deck_id=?",
                    ("; ".join(filter(None, [hinweis, alt])), deck_id))


def deck_rows(con, path, deck_id=0):
    """Deckdatei -> Zeilen [deck_id, board, name, qty, set, cn, oracle_id] (Board-Erkennung wie Moxfield-Export)."""
    blocks = parse_deck(path)
    rows = []
    main_qty = 0
    letzter = len(blocks) - 1
    for j, (header, cards) in enumerate(blocks):
        board = header
        if board is None:
            if j == 0 or j < letzter:
                # Moxfield setzt Commander/Sideboard nur in den LETZTEN Block;
                # unbeschriftete Blöcke davor (z. B. verirrte Leerzeile) gehören zum Hauptdeck
                board = "main"
            else:
                qty = sum(q for q, *_ in cards)
                oids = [resolve_name(con, n) for _, n, _, _ in cards]
                # Moxfield-Textexport: Commander steht nach einer Leerzeile am Ende.
                # Auch unfertige Decks (z. B. 91 Karten) erkennen.
                if qty <= 2 and main_qty >= 80 and all(
                        o and is_commander_eligible(con, o) for o in oids):
                    board = "commander"
                else:
                    board = "sideboard"
        for q, n, st, cn in cards:
            rows.append([deck_id, board, n, q, st, cn, resolve_name(con, n)])
            if board == "main":
                main_qty += q
    return rows


def load_decks(con, paths, config, start=1):
    for i, path in enumerate(paths, start):
        rows = deck_rows(con, path, i)
        insert_deck(con, i, os.path.basename(path), slug_name(path),
                    export_datum(os.path.basename(path)), rows, config)
    return start + len(paths)


def load_scan_decks(con, paths, config, start):
    """ManaBox-Scans als Decklisten: je Binder ein Deck (ohne Binder-Spalte: ganze Datei = ein Deck).
    Die Karten werden NICHT zum Bestand gezählt (neue Karten nur über `scan` buchen)."""
    i = start
    for path in paths:
        _, zeilen = read_csv_rows(path)
        gruppen = {}
        for r in zeilen:
            gruppen.setdefault(r.get("binder") or slug_name(path), []).append(r)
        for name, rs in sorted(gruppen.items()):
            menge = sum(int(float(r.get("qty") or 1)) for r in rs)
            if menge > 250:
                print(f"  Binder '{name}' übersprungen ({menge} Karten – kein Deck)")
                continue
            rows = []
            for r in rs:
                sid, oid, _ = match_print(con, r)
                rows.append([i, "main", r.get("name", ""), int(float(r.get("qty") or 1)),
                             r.get("set", "").lower(), r.get("cn", ""), oid])
            insert_deck(con, i, f"Scan: {os.path.basename(path)}", name, None, rows, config)
            i += 1
    return i


def load_binder_decks(con, muster, config, start):
    """Decks aus Bindern/Listen der Sammlung (ManaBox): Binder-Typ 'deck' oder Name passt zu muster."""
    binder = con.execute("SELECT DISTINCT binder, binder_type FROM collection WHERE binder IS NOT NULL").fetchall()
    gewaehlt = [b for b, t in binder if (t or "") == "deck" or (muster and re.search(muster, b, re.I))]
    i = start
    for b in sorted(gewaehlt):
        rows = [[i, "main", n, q, s, c, o] for n, q, s, c, o in con.execute(
            "SELECT name, SUM(qty), set_code, cn, oracle_id FROM collection WHERE binder=?"
            " GROUP BY oracle_id, name", (b,))]
        insert_deck(con, i, f"Binder: {b}", b, None, rows, config)
        i += 1
    return i


def analyse_deck(con, deck_id, config):
    alt = con.execute("SELECT alter_name FROM decks WHERE deck_id=?", (deck_id,)).fetchone()[0]
    toks = re.findall(r"[a-zäöüß]+", alt.lower())
    dc = con.execute("SELECT d.board, d.name, d.qty, d.oracle_id, c.type_line, c.color_identity,"
                     " c.legal_commander, c.legal_standard, c.legal_pioneer, c.legal_modern,"
                     " c.legal_legacy, c.legal_vintage FROM deck_cards d LEFT JOIN cards c"
                     " USING(oracle_id) WHERE deck_id=?", (deck_id,)).fetchall()
    hinweise = []
    unbekannt = [r[1] for r in dc if r[3] is None]
    if unbekannt:
        hinweise.append("nicht erkannt: " + ", ".join(unbekannt))
    main = [r for r in dc if r[0] in ("main", "commander")]
    cmdr = [r for r in dc if r[0] == "commander"]
    karten = sum(r[2] for r in main)
    basics = lambda r: (r[4] or "").startswith("Basic")
    # Format
    label = next((t for t in toks if t in FORMATE or t == "commander"), None)
    singleton = all(r[2] <= 1 or basics(r) for r in main)
    if not cmdr and (karten >= 90 and singleton or label == "commander"):
        # Commander-Deck ohne erkannten Commander: trotzdem als Commander behandeln
        fmt, legal = "commander", None
        ci = set("".join(r[5] or "" for r in main))
        if karten != 100:
            hinweise.append(f"{karten} statt 100 Karten")
    elif cmdr:
        fmt = "commander"
        ci = set("".join(r[5] or "" for r in cmdr))
        fehl = [r[1] for r in main if r[5] and not set(r[5]) <= ci]
        if fehl:
            hinweise.append("außerhalb der Farbidentität: " + ", ".join(fehl))
        gebannt = [r[1] for r in main if r[6] == "banned"]
        if gebannt:
            hinweise.append("in Commander gebannt: " + ", ".join(gebannt))
        if karten != 100:
            hinweise.append(f"{karten} statt 100 Karten")
        legal = "commander" if not (fehl or gebannt) else None
    else:
        ci = set("".join(r[5] or "" for r in main if "Land" not in (r[4] or "")))
        legal = None
        idx = {"standard": 7, "pioneer": 8, "modern": 9, "legacy": 10, "vintage": 11}
        for f in FORMATE:
            if all(basics(r) or r[idx[f]] in ("legal", "restricted") for r in main if r[3]):
                legal = f
                break
        fmt = label if label in FORMATE and legal and FORMATE.index(legal) <= FORMATE.index(label) else (legal or label or "casual")
        if label in FORMATE and fmt != label:
            nicht = [r[1] for r in main if r[3] and not basics(r) and r[idx[label]] != "legal"]
            hinweise.append(f"nicht {FORMAT_ANZEIGE[label]}-legal ({len(set(nicht))} Karten: "
                            + ", ".join(sorted(set(nicht))[:8]) + (" …" if len(set(nicht)) > 8 else "") + ")")
        if karten < 60:
            hinweise.append(f"nur {karten} Karten")
    # Herkunft über Kartenstruktur: Anteil der Nicht-Standardländer, die im Set eines vorkonstruierten
    # Produkts gedruckt sind. Commander-Precons haben eigene Set-Codes (z. B. TDC) -> zuverlässig.
    # Konstruierte Precons nutzen oft normale Set-Drucke -> dort entscheidet im Zweifel der alte Name.
    nb = {r[3] for r in main if r[3] and not basics(r)}
    best = (None, None, 0.0)
    settypen = {"commander"} if fmt == "commander" else PRECON_SETTYPEN - {"commander", "box"}
    if len(nb) >= 20:          # kleine Listen sagen nichts über die Herkunft
        q = ",".join("?" * len(nb))
        cov = con.execute(f"SELECT set_code, set_name, set_type, MAX(released_at), COUNT(DISTINCT oracle_id)"
                          f" FROM prints WHERE oracle_id IN ({q}) GROUP BY set_code", list(nb)).fetchall()
        cov = [c for c in cov if c[2] in settypen]
        if cov:
            c = max(cov, key=lambda x: (x[4], x[3] or ""))
            best = (c[0], c[1], c[4] / len(nb))
    anteil = best[2]
    herkunft = "Precon" if anteil >= 0.97 else "Precon-Edit" if anteil >= 0.5 else "Selfbuild"
    if herkunft == "Selfbuild":
        if "ai" in toks and "build" in toks:
            herkunft = "AI Build"
        elif not cmdr and ("precon" in toks or "preconedit" in toks):
            # Kartenstruktur nicht eindeutig -> Angabe im Namen
            herkunft = "Precon-Edit" if ("edit" in toks or "preconedit" in toks) else "Precon"
            hinweise.append("Herkunft aus dem alten Namen übernommen (Precon-Set nicht erkennbar)")
            best = (None, None, anteil)
    set_anzeige = re.sub(r"\s*Commander$|^Commander\s*", "", best[1] or "").strip() if herkunft.startswith("Precon") else None
    cname = cmdr[0][1] if cmdr else None
    cfg = {**config_for(config, alt), **(config.get(f"commander:{cname}", {}) if cname else {})}
    # Deckname: eigener Name aus deck_namen.json ("name") > Wizards-Precon-Name ("precon")
    deckname = cfg.get("name") or cfg.get("precon")
    if not deckname:
        deckname = "?"
        hinweise.append("Deckname fehlt – in deck_namen.json eintragen (Precon: Wizards-Name, sonst eigener Name)")
    # Strategie: Konfiguration > Archetyp/Thema aus dem bisherigen Namen
    arche = [t.capitalize() for t in toks if t in ARCHETYPEN]
    them = [t.capitalize() for t in toks if t in THEMEN]
    strategie = cfg.get("strategie") or " ".join(filter(None, ["-".join(dict.fromkeys(arche)),
                                                                " ".join(dict.fromkeys(them))])) or None
    if not strategie:
        strategie = "?"
        hinweise.append("Strategie unbekannt – in deck_namen.json eintragen")
    herkunft = cfg.get("herkunft", herkunft)
    if herkunft.startswith("Precon") and set_anzeige and best[0] and "(" not in herkunft:
        herkunft = f"{herkunft} ({best[0].upper()})"      # Set-Code statt Set-Name (Platz)
    # Status nur aus den Prüfungen (nicht aus dem Namen – sonst bliebe „In Arbeit“ ewig stehen)
    in_arbeit = any(h.startswith(("nur ", "außerhalb", "in Commander gebannt")) or "statt 100" in h
                    for h in hinweise)
    status = cfg["status"] if "status" in cfg else ("In Arbeit" if in_arbeit else "")
    fmt_anz = FORMAT_ANZEIGE.get(fmt, fmt.capitalize())
    teile = [fmt_anz, deckname, farbname_kurz(ci), strategie, herkunft] + ([status] if status else [])
    neuer = " | ".join(teile)
    if len(neuer) > MAX_NAME:
        hinweise.append(f"Name hat {len(neuer)} Zeichen (Moxfield max. {MAX_NAME}) – "
                        f"Strategie oder Deckname in deck_namen.json kürzen")
    kurz = deckname if deckname != "?" else (
        cname.split(",")[0].split(" // ")[0] if cname else f"{farbname(ci).split(' (')[0]} {fmt_anz}")
    con.execute("UPDATE decks SET format=?, format_label=?, format_legal=?, commander=?, farben=?,"
                " karten=?, precon_set=?, precon_set_name=?, precon_anteil=?, herkunft=?,"
                " strategie=?, status=?, neuer_name=?, kurz=?, hinweise=? WHERE deck_id=?",
                (fmt, label, legal, " + ".join(r[1] for r in cmdr) or None, ci_str(ci), karten,
                 best[0], best[1], round(anteil, 3), herkunft, strategie, status, neuer, kurz,
                 "; ".join(hinweise) or None, deck_id))


def ist_weich(idee):
    """Weiche Vormerkung = geplanter Verkauf (Idee-ID „V-nnn“): sperrt nicht, die Werkzeuge warnen nur."""
    return str(idee or "").strip().upper().startswith("V-")


def load_vormerkungen(con, path):
    """claude/sammlung/vormerkungen.csv (Idee, Name, Anzahl, Datum, Hinweis) laden; Konflikte melden.
    Ideen „V-nnn“ (geplanter Verkauf) sind weich: frei bleibt gleich, Exemplare bekommen nur den Vermerk."""
    if not path or not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        oid = resolve_name(con, r["Name"])
        if not oid:
            print(f"  Vormerkung nicht erkannt: {r['Name']} ({r.get('Idee')})")
        con.execute("INSERT INTO vormerkungen VALUES (?,?,?,?,?,?,?)",
                    (r.get("Idee"), r["Name"], oid, int(r.get("Anzahl") or 1), r.get("Datum"), r.get("Hinweis"),
                     1 if ist_weich(r.get("Idee")) else 0))
    return len(rows)


def baue_exemplare(con):
    """Jedes physische Exemplar (Basis + Journal, Abgänge abgezogen) einem Deck, einer Vormerkung oder der
    Sammlung zuordnen – damit Tauschübersicht, Export und Soll-Stand den eigenen Druck und die Sprache kennen.
    Reihenfolge je Deckkarte: (1) Druck steht in der Deckliste (Set + Nummer) → 'druck'; (2) Erfassungszeitpunkt
    des Decks (Moxfield 'Last Modified': die Karten eines Decks wurden gemeinsam erfasst) → 'zeitstempel';
    (3) Precon-Set des Decks → 'set'; (4) sonst → 'geschätzt' (Exemplare anderer Decks-Zeitstempel zuletzt).
    Vormerkungen bekommen danach freie Exemplare. Zählung je Karte = v_karten (Besitz − Decks − Vormerkungen)."""
    pos, neg = [], []
    for rid, oid, name, st, cn, fin, lang, mod, q in con.execute(
            "SELECT id, oracle_id, name, set_code, cn, finish, lang, COALESCE(modified,''), qty FROM collection"
            " WHERE oracle_id IS NOT NULL AND lower(COALESCE(proxy,'false'))<>'true' ORDER BY id"):
        (pos if q > 0 else neg).append([rid, oid, name, st, cn, fin, lang, mod, q])
    for n in neg:
        rest = -n[8]
        kand = [p for p in pos if p[1] == n[1] and p[3] == n[3] and p[4] == n[4] and p[5] == n[5]
                and p[6] == n[6] and p[8] > 0]
        kand.sort(key=lambda p: (not n[7] or p[7] != n[7]))
        for p in kand:
            ab = min(rest, p[8])
            p[8] -= ab
            rest -= ab
            if not rest:
                break
    ex = []
    for p in pos:
        ex += [[p[1], p[2], p[3], p[4], p[5], p[6], p[7], None, None, None, None] for _ in range(p[8])]
    je_oid = defaultdict(list)
    for e in ex:
        je_oid[e[0]].append(e)
    bedarf = con.execute("SELECT d.deck_id, d.oracle_id, d.qty, d.set_code, d.cn, k.precon_set FROM deck_cards d"
                         " JOIN decks k USING(deck_id) WHERE d.board IN ('main','commander','sideboard','companion')"
                         " AND d.oracle_id IS NOT NULL ORDER BY d.deck_id").fetchall()
    ts = {}
    for did in sorted({b[0] for b in bedarf}):
        oids = {b[1] for b in bedarf if b[0] == did}
        c = Counter(m for oid in oids for m in {e[6] for e in je_oid.get(oid, []) if e[6]})
        if c:
            m, n = c.most_common(1)[0]
            if n >= max(5, 0.3 * len(oids)):
                ts[did] = m
    offen = []
    for did, oid, q, st, cn, pset in bedarf:
        rest = q
        if st and cn:
            for e in je_oid.get(oid, []):
                if rest and e[7] is None and e[2] == st.lower() and str(e[3]).lower() == str(cn).lower():
                    e[7], e[8] = did, "druck"
                    rest -= 1
        if rest:
            offen.append((did, oid, rest, (pset or "").lower()))
    for did, oid, rest, pset in offen:
        fremd = {m for d, m in ts.items() if d != did}

        def rang(e):
            if ts.get(did) and e[6] == ts[did]:
                return 0
            if pset and e[2] == pset:
                return 1
            return 2 if e[6] not in fremd else 3
        frei = sorted((e for e in je_oid.get(oid, []) if e[7] is None), key=rang)
        for e in frei[:rest]:
            e[7], e[8] = did, ("zeitstempel", "set", "geschätzt", "geschätzt")[rang(e)]
    for idee, oid, q in con.execute("SELECT idee, oracle_id, qty FROM vormerkungen WHERE oracle_id IS NOT NULL"
                                    " AND weich = 0"):
        for e in [e for e in je_oid.get(oid, []) if e[7] is None and e[9] is None][:q]:
            e[9] = idee
    # geplante Verkäufe (weich): freie Exemplare markieren; „Druck: SET Nr [de|en] [foil]“ im Hinweis hat Vorrang
    for idee, oid, q, hinweis in con.execute("SELECT idee, oracle_id, qty, COALESCE(hinweis,'') FROM vormerkungen"
                                             " WHERE oracle_id IS NOT NULL AND weich = 1"):
        m = re.search(r"Druck:\s*([A-Za-z0-9]+)\s+([^\s;,]+)(?:\s+([a-z]{2})\b)?(?:\s+(foil|etched|nonfoil))?",
                      hinweis, re.I)

        def passt(e, m=m):
            if not m:
                return 1
            ok = e[2] == m.group(1).lower() and str(e[3]).lower() == m.group(2).lower()
            ok = ok and (not m.group(3) or e[5] == m.group(3).lower())
            ok = ok and (not m.group(4) or e[4] == m.group(4).lower())
            return 0 if ok else 1
        frei = sorted((e for e in je_oid.get(oid, []) if e[7] is None and e[9] is None and e[10] is None), key=passt)
        for e in frei[:q]:
            e[10] = idee
    con.executemany("INSERT INTO exemplare(oracle_id, name, set_code, cn, finish, lang, modified, deck_id, zuordnung,"
                    " idee, verkauf) VALUES (?,?,?,?,?,?,?,?,?,?,?)", ex)
    zuo = Counter(e[8] or ("vorgemerkt" if e[9] else "frei") for e in ex)
    abw = con.execute("SELECT COUNT(*) FROM v_karten k LEFT JOIN (SELECT oracle_id, COUNT(*) AS n FROM exemplare"
                      " WHERE deck_id IS NULL AND idee IS NULL GROUP BY oracle_id) x USING(oracle_id)"
                      " WHERE k.frei <> COALESCE(x.n, 0)").fetchone()[0]
    return zuo, abw


def build(args):
    config = json.load(open(args.config, encoding="utf-8")) if args.config and os.path.exists(args.config) else {}
    meta = ensure_bulk(args.bulk)
    if os.path.exists(args.db):
        os.remove(args.db)
    con = sqlite3.connect(args.db)
    con.executescript(SCHEMA)
    t0 = time.time()
    nc, np_ = load_cards(con, args.bulk)
    nt = load_tags(con, args.bulk)
    nr = load_rulings(con, args.bulk)
    print(f"Scryfall: {nc} Karten, {np_} Drucke, {nt} Tag-Zuordnungen, {nr} Rulings ({time.time()-t0:.0f} s)")
    for s in args.sammlung:
        n, src = load_collection(con, s)
        print(f"Sammlung: {n} Zeilen aus {os.path.basename(s)} ({src})")
    nxt = load_decks(con, args.decks, config)
    if args.binder_decks is not None:
        nxt = load_binder_decks(con, args.binder_decks or None, config, nxt)
    if args.scan_decks:
        nxt = load_scan_decks(con, args.scan_decks, config, nxt)
    print(f"Decks: {nxt - 1} ({len(args.decks)} aus Deckdateien, {nxt - 1 - len(args.decks)} aus Bindern/Scans)")
    nv = load_vormerkungen(con, args.vormerkungen)
    if nv:
        print(f"Vormerkungen: {nv} Zeilen aus {os.path.basename(args.vormerkungen)}")
        for n, b, d, v, ideen in con.execute(
                "SELECT k.name, k.besitz, k.in_decks, k.vorgemerkt, k.ideen FROM v_karten k"
                " WHERE k.vorgemerkt > 0 AND k.besitz - k.in_decks < k.vorgemerkt"):
            print(f"  Konflikt Vormerkung: {n} – {v} vorgemerkt ({ideen}), aber nur {max(b - d, 0)} frei vor Vormerkung")
        for n, f, g, ideen in con.execute("SELECT name, frei, verkauf_geplant, verkauf_ideen FROM v_karten"
                                          " WHERE verkauf_geplant > frei"):
            print(f"  Verkauf geplant: {n} – {g} zum Verkauf vorgesehen ({ideen}), aber nur {f} frei")
    zuo, abw = baue_exemplare(con)
    print("Exemplare: " + ", ".join(f"{k} {v}" for k, v in zuo.most_common())
          + (f" | {abw} Karten mit abweichender Frei-Zählung (Deck braucht mehr, als da ist)" if abw else ""))
    for r in con.execute("SELECT kurz, hinweise FROM decks WHERE hinweise LIKE '%Commander%'"):
        print(f"  Hinweis {r[0]}: {r[1]}")
    for k, v in {**{f"bulk_{k}": v for k, v in meta.items()},
                 "gebaut": time.strftime("%Y-%m-%d %H:%M"),
                 "sammlung": ", ".join(os.path.basename(s) for s in args.sammlung)}.items():
        con.execute("INSERT INTO meta VALUES (?,?)", (k, v))
    con.commit()
    m = dict(con.execute("SELECT match, SUM(qty) FROM collection GROUP BY match").fetchall())
    print("Zuordnung Sammlung (Karten):", m)


# ----------------------------------------------------------------- Abfragen
def table(rows, headers):
    rows = [["" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v)) for v in r] for r in rows]
    w = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    print(" | ".join(h.ljust(w[i]) for i, h in enumerate(headers)))
    print("-+-".join("-" * x for x in w))
    for r in rows:
        print(" | ".join(r[i].ljust(w[i]) for i in range(len(headers))))


def find_deck(con, ref):
    if str(ref).isdigit():
        return int(ref)
    r = con.execute("SELECT deck_id FROM decks WHERE lower(alter_name) LIKE ? OR lower(neuer_name)"
                    " LIKE ? OR lower(commander) LIKE ?", (f"%{ref.lower()}%",) * 3).fetchall()
    if len(r) != 1:
        sys.exit(f"Deck '{ref}' nicht eindeutig: {len(r)} Treffer")
    return r[0][0]


def cmd_sammlung(con, args):
    tot = con.execute("""SELECT SUM(c.qty), (SELECT COUNT(*) FROM v_besitz WHERE besitz > 0),
        SUM(c.qty * COALESCE(CASE c.finish WHEN 'foil' THEN COALESCE(p.eur_foil,p.eur)
             WHEN 'etched' THEN COALESCE(p.eur_etched,p.eur_foil,p.eur)
             ELSE COALESCE(p.eur,p.eur_foil) END, 0)),
        SUM(CASE WHEN p.eur IS NULL AND p.eur_foil IS NULL AND p.eur_etched IS NULL THEN c.qty ELSE 0 END)
        FROM collection c LEFT JOIN prints p USING(scryfall_id)""").fetchone()
    print(f"Karten: {tot[0]} | Unikate: {tot[1]} | Wert (Scryfall-EUR, Druckversion): {tot[2]:.2f} € "
          f"| ohne Preis: {tot[3]}")
    print("\nNach Farbidentität:")
    table(con.execute("""SELECT CASE WHEN k.color_identity='' THEN 'C' ELSE k.color_identity END,
        SUM(c.qty) FROM collection c JOIN cards k USING(oracle_id) GROUP BY 1 ORDER BY 2 DESC LIMIT 15""").fetchall(),
          ["Farben", "Karten"])
    print("\nNach Typ:")
    typen = Counter()
    for tl, q in con.execute("SELECT k.type_line, c.qty FROM collection c JOIN cards k USING(oracle_id)"):
        t = (tl or "").split(" // ")[0]
        for x in ("Land", "Creature", "Planeswalker", "Battle", "Instant", "Sorcery", "Artifact", "Enchantment"):
            if x in t:
                typen[x] += q
                break
    table(typen.most_common(), ["Typ", "Karten"])
    print("\nTeuerste Karten (Einzelpreis der eigenen Druckversion):")
    table(con.execute("""SELECT c.name, UPPER(c.set_code)||' '||c.cn, c.finish, SUM(c.qty) AS n,
        CASE c.finish WHEN 'foil' THEN COALESCE(p.eur_foil,p.eur) WHEN 'etched' THEN COALESCE(p.eur_etched,p.eur_foil)
        ELSE COALESCE(p.eur,p.eur_foil) END AS e FROM collection c LEFT JOIN prints p USING(scryfall_id)
        GROUP BY c.oracle_id, c.set_code, c.cn, c.finish HAVING n > 0
        ORDER BY e DESC LIMIT 20""").fetchall(), ["Karte", "Druck", "Finish", "Anz", "€"])


def cmd_decks(con, args):
    table(con.execute("SELECT deck_id, kurz, format, farben, commander, karten, herkunft, precon_set,"
                      " precon_anteil, status FROM decks").fetchall(),
          ["ID", "Kurzname", "Format", "Farben", "Commander", "Karten", "Herkunft", "Precon-Set", "Anteil", "Status"])


def cmd_namen(con, args):
    for d in con.execute("SELECT deck_id, alter_name, neuer_name, hinweise FROM decks"):
        print(f"[{d[0]}] alt: {d[1]}\n    neu: {d[2]}  ({len(d[2])}/{MAX_NAME} Zeichen)"
              + (f"\n    Hinweis: {d[3]}" if d[3] else ""))


def cmd_besitz(con, args):
    did = find_deck(con, args.deck)
    rows = con.execute("""SELECT d.name, SUM(d.qty), COALESCE(b.besitz,0), COALESCE(v.bedarf,0), v.decks,
        k.eur_min, k.type_line FROM deck_cards d LEFT JOIN v_besitz b USING(oracle_id)
        LEFT JOIN v_bedarf v USING(oracle_id) LEFT JOIN cards k USING(oracle_id)
        WHERE d.deck_id=? AND d.board IN ('main','commander') GROUP BY d.oracle_id, d.name""", (did,)).fetchall()
    fehlt, konflikt = [], []
    for n, need, have, bedarf, ndecks, eur, tl in rows:
        if (tl or "").startswith("Basic"):
            continue
        if have < need:
            fehlt.append((n, need, have, need - have, eur))
        elif have < bedarf:
            konflikt.append((n, have, bedarf, ndecks))
    gesamt = sum(r[1] for r in rows)
    print(f"Deck {did}: {gesamt} Karten | fehlen: {sum(f[3] for f in fehlt)} | "
          f"Konflikte mit anderen Decks: {len(konflikt)}")
    if fehlt:
        print("\nFehlt in der Sammlung:")
        table(fehlt, ["Karte", "braucht", "besitzt", "fehlt", "ab € (Scryfall)"])
        print(f"Summe (günstigster Druck): {sum((f[4] or 0) * f[3] for f in fehlt):.2f} €")
    if konflikt:
        print("\nVorhanden, aber nicht genug Exemplare für alle Decks:")
        table(konflikt, ["Karte", "besitzt", "Bedarf alle Decks", "Decks"])
    print()
    laender_tabelle(con, did, None)


def parse_plan(text):
    """'Plains=12, Mountain=8' -> {oracle-Name: Anzahl}."""
    plan = {}
    for teil in re.split(r"[,;]\s*|\s+(?=[A-Z][a-z-]+=)", text.strip()):
        if "=" in teil:
            n, q = teil.split("=", 1)
            plan[n.strip()] = int(q)
    return plan


def laender_tabelle(con, did, plan):
    """Standardländer: Bedarf eines Decks (oder Plan) gegen Sammlung, abzüglich anderer Decks.
    Die Sammlung enthält alle Deckkarten; Standardländer sind oft nicht vollständig eingescannt."""
    basics = dict(con.execute("SELECT name, oracle_id FROM v_basics"))
    need_deck = {}
    if plan:
        for n, q in plan.items():
            key = next((b for b in basics if b.lower() == n.lower()), None)
            if not key:
                sys.exit(f"'{n}' ist kein Standardland (englischer Name, z. B. Plains, Island, Swamp, Mountain, Forest, Wastes)")
            need_deck[key] = q
    elif did:
        for n, q in con.execute("SELECT b.name, SUM(d.qty) FROM deck_cards d JOIN v_basics b USING(oracle_id)"
                                " WHERE d.deck_id=? AND d.board IN ('main','commander','sideboard')"
                                " GROUP BY b.name", (did,)):
            need_deck[n] = q
    zeilen, kauf = [], {}
    namen = need_deck.keys() if (did or plan) else basics.keys()
    for n in sorted(namen):
        oid = basics[n]
        besitz = con.execute("SELECT COALESCE(SUM(qty),0) FROM collection WHERE oracle_id=?", (oid,)).fetchone()[0]
        andere = con.execute("SELECT COALESCE(SUM(qty),0) FROM deck_cards WHERE oracle_id=? AND deck_id IS NOT ?"
                             " AND board IN ('main','commander','sideboard')", (oid, did)).fetchone()[0]
        if did or plan:
            frei = max(besitz - andere, 0)
            fehlt = max(need_deck[n] - frei, 0)
            zeilen.append((n, need_deck[n], besitz, andere, frei, fehlt))
        else:
            if besitz == 0 and andere == 0:
                continue
            fehlt = max(andere - besitz, 0)
            zeilen.append((n, andere, besitz, max(besitz - andere, 0), fehlt))
        if fehlt:
            kauf[n] = fehlt
    if did or plan:
        print("Standardländer (Sammlung enthält alle Decks; Bestand ggf. unvollständig eingescannt):")
        table(zeilen, ["Land", "braucht", "Besitz", "in anderen Decks", "verfügbar", "nachkaufen"])
    else:
        print("Standardländer über alle Decks:")
        table(zeilen, ["Land", "Bedarf alle Decks", "Besitz", "frei", "nachkaufen"])
    if kauf:
        print("\nNachkauf Standardländer (zum Einfügen in Moxfield):")
        print("\n".join(f"{q} {n}" for n, q in sorted(kauf.items())))
    else:
        print("Kein Nachkauf nötig.")


def cmd_laender(con, args):
    did = find_deck(con, args.deck) if args.deck else None
    laender_tabelle(con, did, parse_plan(args.plan) if args.plan else None)


def cmd_mehrfach(con, args):
    table(con.execute("""SELECT k.name, v.decks, v.bedarf, COALESCE(b.besitz,0), v.deck_ids, k.eur_min
        FROM v_bedarf v JOIN cards k USING(oracle_id) LEFT JOIN v_besitz b USING(oracle_id)
        WHERE v.decks > 1 AND k.type_line NOT LIKE 'Basic%'
        ORDER BY (COALESCE(b.besitz,0) >= v.bedarf), v.decks DESC, k.name""").fetchall(),
          ["Karte", "Decks", "Bedarf", "Besitz", "in Decks", "ab €"])


def cmd_bracket(con, args):
    did = find_deck(con, args.deck)
    d = con.execute("SELECT format, commander FROM decks WHERE deck_id=?", (did,)).fetchone()
    rows = con.execute("SELECT d.board, d.name, d.qty, d.oracle_id FROM deck_cards d WHERE deck_id=?"
                       " AND board IN ('main','commander')", (did,)).fetchall()
    oids = [r[3] for r in rows if r[3]]
    q = ",".join("?" * len(oids))
    gc = [r[0] for r in con.execute(f"SELECT name FROM cards WHERE game_changer=1 AND oracle_id IN ({q})", oids)]
    mld = [r[0] for r in con.execute(f"SELECT DISTINCT c.name FROM tags t JOIN cards c USING(oracle_id)"
                                     f" WHERE t.tag='mass-land-denial' AND t.oracle_id IN ({q})", oids)]
    xt = [r[0] for r in con.execute(f"SELECT DISTINCT c.name FROM tags t JOIN cards c USING(oracle_id)"
                                    f" WHERE t.tag='extra-turn' AND t.oracle_id IN ({q})", oids)]
    print(f"Lokal (Scryfall-Daten): Game Changer {len(gc)}: {', '.join(gc) or '–'} | "
          f"MLD: {', '.join(mld) or '–'} | Extra Turns: {', '.join(xt) or '–'}")
    try:
        body = {"main": [{"card": front(r[1]), "quantity": r[2]} for r in rows if r[0] == "main"],
                "commanders": [{"card": front(r[1]), "quantity": r[2]} for r in rows if r[0] == "commander"]}
        res = get_json("https://backend.commanderspellbook.com/estimate-bracket", body)
    except Exception as e:
        print("Commander Spellbook nicht erreichbar:", e)
        return
    tagname = {"R": "Ruthless", "S": "Spicy", "P": "Powerful", "O": "Oddball", "C": "Core",
               "E": "Exhibition", "B": "Banned"}
    print(f"Commander Spellbook: Einstufung {res.get('bracketTag')} ({tagname.get(res.get('bracketTag'), '?')})")
    flagged = [c for c in res.get("cards", []) if c.get("gameChanger") or c.get("massLandDenial")
               or c.get("extraTurn") or c.get("banned")]
    for c in flagged:
        art = [k for k in ("gameChanger", "massLandDenial", "extraTurn", "banned") if c.get(k)]
        print(f"  Karte: {c['card']['name']} -> {', '.join(art)}")
    combos = res.get("combos", [])
    print(f"  Combos im Deck: {len(combos)}")
    for v in combos:
        cb = v["combo"]
        karten = [u["card"]["name"] for u in cb.get("uses", [])]
        art = "2-Karten (sicher)" if v.get("definitelyTwoCard") else "2-Karten (strittig)" if v.get("arguablyTwoCard") else f"{len(karten)} Karten"
        prod = ", ".join(p["feature"]["name"] for p in cb.get("produces", [])[:3])
        print(f"   - {art} | Tag {cb.get('bracketTag')} | speed {v.get('speed')} | relevant {v.get('relevant')}"
              f" | {' + '.join(karten)} => {prod} | https://commanderspellbook.com/combo/{cb.get('id')}/")


def drucke_im_deck(con, did, oid, nur_sicher=False):
    """[(set, nummer, finish, anzahl)] der Exemplare dieses Decks (aus der Tabelle exemplare)."""
    try:
        return con.execute("SELECT set_code, cn, finish, COUNT(*) FROM exemplare WHERE deck_id=? AND oracle_id=?"
                           + (" AND zuordnung='druck'" if nur_sicher else "")
                           + " GROUP BY set_code, cn, finish ORDER BY COUNT(*) DESC, set_code", (did, oid)).fetchall()
    except sqlite3.OperationalError:              # ältere Datenbank ohne Exemplare
        return []


def druck_zeilen(con, did, n, qn, oid, nur_sicher):
    """Eine Karte als Moxfield-Zeilen mit Druck – je Druck eine Zeile, Foil als *F*, Etched als *E*."""
    zeilen, rest = [], qn
    for st, cn, fin, k in drucke_im_deck(con, did, oid, nur_sicher):
        k = min(k, rest)
        if k <= 0 or not st:
            continue
        zeilen.append(f"{k} {n} ({st.upper()}) {cn}" + {"foil": " *F*", "etched": " *E*"}.get(fin, ""))
        rest -= k
    if rest > 0:
        zeilen.append(f"{rest} {n}")
    return zeilen


def deck_text(con, did, sets=False, marker=False, nur_sicher=False):
    """Deck als Moxfield-Text: Hauptdeck alphabetisch, Commander nach Leerzeile am Ende.
    marker=True (Snapshots): Abschnitte mit '// Commander' / '// Sideboard' kennzeichnen.
    sets=True: Druck je Exemplar aus der Exemplar-Zuordnung (nur_sicher: nur Drucke aus Deckliste/Scan)."""
    out = []
    for board in ("main", "commander", "sideboard"):
        rows = con.execute("SELECT name, SUM(qty), oracle_id FROM deck_cards WHERE deck_id=? AND board=?"
                           " GROUP BY oracle_id, name ORDER BY name", (did, board)).fetchall()
        if not rows or (board == "sideboard" and not marker):
            continue
        lines = [f"// {board.capitalize()}"] if marker and board != "main" else []
        for n, qn, oid in rows:
            if sets:
                lines += druck_zeilen(con, did, n, qn, oid, nur_sicher)
            else:
                lines.append(f"{qn} {n}")
        out.append("\n".join(lines))
    return "\n\n".join(out)


def cmd_export(con, args):
    print(deck_text(con, find_deck(con, args.deck), args.sets))


# ----------------------------------------------------------------- ManaBox -> Moxfield
# ManaBox nutzt die Cardmarket-Skala, Moxfield die TCGplayer-Skala
MB_ZU_MOX_ZUSTAND = {"mint": "Mint", "near_mint": "Near Mint", "excellent": "Good (Lightly Played)",
                     "good": "Played", "light_played": "Played", "played": "Heavily Played",
                     "poor": "Damaged"}
LANG_NAME = {v: k.title() for k, v in LANG.items()}


def cmd_manabox_zu_moxfield(con, args):
    """ManaBox-Scan (CSV) -> Moxfield-Sammlungs-CSV und/oder Moxfield-Deck-TXT."""
    _, zeilen = read_csv_rows(args.datei)
    if args.sammlung:
        with open(args.sammlung, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, quoting=csv.QUOTE_ALL)
            w.writerow(["Count", "Tradelist Count", "Name", "Edition", "Condition", "Language", "Foil", "Tags",
                        "Last Modified", "Collector Number", "Alter", "Proxy", "Purchase Price"])
            for r in zeilen:
                fin = (r.get("finish") or "").lower()
                lang = (r.get("lang") or "").lower()
                w.writerow([int(float(r.get("qty") or 1)), args.tausch, r.get("name"), (r.get("set") or "").lower(),
                            MB_ZU_MOX_ZUSTAND.get((r.get("condition") or "").lower(), "Near Mint"),
                            LANG_NAME.get(lang, "English" if not lang else lang),
                            fin if fin in ("foil", "etched") else "", args.tags or "", "", r.get("cn"),
                            "True" if (r.get("altered") or "").lower() == "true" else "False",
                            "True" if (r.get("proxy") or "").lower() == "true" else "False",
                            r.get("price_paid") or ""])
        print(f"Moxfield-Sammlung: {len(zeilen)} Zeilen, {sum(int(float(r.get('qty') or 1)) for r in zeilen)} Karten"
              f" -> {args.sammlung}")
    if args.deck:
        rows = []
        for r in zeilen:
            sid, oid, _ = match_print(con, r)
            name = con.execute("SELECT name FROM cards WHERE oracle_id=?", (oid,)).fetchone()[0] if oid else r.get("name")
            rows.append([0, "main", name, int(float(r.get("qty") or 1)), (r.get("set") or "").upper(), r.get("cn"), oid])
        config = json.load(open(args.config, encoding="utf-8")) if os.path.exists(args.config) else {}
        hinweis = assign_commander(con, rows, os.path.basename(args.datei), config)
        teile = []
        for board in ("main", "commander"):
            sel = sorted((r for r in rows if r[1] == board), key=lambda r: (fold(r[2]), r[4], r[5]))
            if sel:
                teile.append("\n".join(f"{r[3]} {r[2]}" + (f" ({r[4]}) {r[5]}" if args.sets and r[4] else "")
                                       for r in sel))
        with open(args.deck, "w", encoding="utf-8") as fh:
            fh.write("\n\n".join(teile) + "\n")
        print(f"Moxfield-Deck: {sum(r[3] for r in rows)} Karten -> {args.deck}" + (f" | {hinweis}" if hinweis else ""))


# ----------------------------------------------------------------- Scans buchen (mit Doppelscan-Schutz)
MOX_COLS = ["Count", "Tradelist Count", "Name", "Edition", "Condition", "Language", "Foil", "Tags",
            "Last Modified", "Collector Number", "Alter", "Proxy", "Purchase Price"]
JOURNAL_COLS = MOX_COLS + ["Buchung", "Datum", "Beleg"]


def datei_hash(path):
    import hashlib
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:12]


def lies_journal(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def naechste_buchung(journal):
    nums = [int(m.group(1)) for r in journal for m in [re.match(r"B-(\d+)", r.get("Buchung") or "")] if m]
    return f"B-{max(nums, default=0) + 1:03d}"


def scan_zeile_moxfield(con, r):
    """ManaBox-Zeile -> Moxfield-Zeile (Druck über Scryfall-ID aufgelöst) + Oracle-ID."""
    sid, oid, _ = match_print(con, r)
    p = con.execute("SELECT set_code, cn, name FROM prints WHERE scryfall_id=?", (sid,)).fetchone() if sid else None
    setc, cn = (p[0], p[1]) if p else ((r.get("set") or "").lower(), r.get("cn") or "")
    name = (con.execute("SELECT name FROM cards WHERE oracle_id=?", (oid,)).fetchone() or [r.get("name")])[0] if oid else r.get("name")
    fin = (r.get("finish") or "").lower()
    lang = (r.get("lang") or "").lower()
    qty = int(float(r.get("qty") or 1))
    return {"Count": str(qty), "Tradelist Count": "0", "Name": name, "Edition": setc,
            "Condition": MB_ZU_MOX_ZUSTAND.get((r.get("condition") or "").lower(), "Near Mint"),
            "Language": LANG_NAME.get(lang, "English" if not lang else lang.title()),
            "Foil": fin if fin in ("foil", "etched") else "", "Tags": "",
            "Last Modified": r.get("added") or "", "Collector Number": cn,
            "Alter": "True" if (r.get("altered") or "").lower() == "true" else "False",
            "Proxy": "True" if (r.get("proxy") or "").lower() == "true" else "False",
            "Purchase Price": r.get("price_paid") or ""}, oid


def cmd_scan(con, args):
    """ManaBox-Scan prüfen und (mit --buchen) als Zugang ins Journal schreiben.
    Schutz gegen Doppelscans: (1) dieselbe Datei (Hash) schon gebucht, (2) dieselbe Scan-Zeile
    (Druck + Foil + Sprache + ManaBox-Zeitstempel 'Added') schon gebucht – z. B. bei einem Gesamtexport,
    der ältere Scans erneut enthält, (3) Verdacht: gleicher Druck + Foil schon im Bestand (zweites Exemplar
    oder Doppelscan?) – wird nur mit --verdacht-buchen gebucht, (4) Sprachkontrolle."""
    _, zeilen = read_csv_rows(args.datei)
    journal = lies_journal(args.journal)
    h = datei_hash(args.datei)
    hash_treffer = sorted({r["Buchung"] for r in journal if f"sha:{h}" in (r.get("Beleg") or "")})
    gebucht = {(r["Edition"], r["Collector Number"], r["Foil"], r["Language"], r["Last Modified"])
               for r in journal if int(float(r.get("Count") or 0)) > 0 and r.get("Last Modified")}
    neu, schon, verdacht, unbekannt = [], [], [], []
    for r in zeilen:
        m, oid = scan_zeile_moxfield(con, r)
        if not oid:
            unbekannt.append(m)
            continue
        k = (m["Edition"], m["Collector Number"], m["Foil"], m["Language"], m["Last Modified"])
        if m["Last Modified"] and k in gebucht:
            schon.append(m)
            continue
        fin = m["Foil"] or "nonfoil"
        im_bestand = con.execute("SELECT COALESCE(SUM(qty),0) FROM collection WHERE set_code=? AND cn=? AND finish=?",
                                 (m["Edition"], m["Collector Number"], fin)).fetchone()[0]
        (verdacht if im_bestand > 0 else neu).append((m, im_bestand))
    menge = lambda xs: sum(int((x[0] if isinstance(x, tuple) else x)["Count"]) for x in xs)
    sprachen = Counter()
    for x in neu + verdacht:
        sprachen[x[0]["Language"]] += int(x[0]["Count"])
    print(f"Scan {os.path.basename(args.datei)} (sha:{h}): {len(zeilen)} Zeilen, "
          f"{sum(int(float(r.get('qty') or 1)) for r in zeilen)} Karten")
    if hash_treffer:
        print(f"  !! Diese Datei wurde schon gebucht ({', '.join(hash_treffer)}) – nichts erneut buchen.")
    print(f"  bereits gebucht (gleiche Scan-Zeile): {len(schon)} Zeilen / {menge(schon)} Karten")
    print(f"  neu, Druck noch nicht im Bestand:     {len(neu)} Zeilen / {menge(neu)} Karten")
    print(f"  Verdacht (Druck schon im Bestand):    {len(verdacht)} Zeilen / {menge(verdacht)} Karten")
    print(f"  nicht erkannt:                        {len(unbekannt)} Zeilen")
    print(f"  Sprachen der zu buchenden Karten: {dict(sprachen)}")
    if verdacht:
        print("\nVerdacht – zweites Exemplar oder Doppelscan? (im Bestand = Exemplare dieses Drucks vorher)")
        table([(m["Name"], m["Edition"].upper(), m["Collector Number"], m["Foil"], m["Language"], m["Count"], b)
               for m, b in sorted(verdacht, key=lambda x: x[0]["Name"])],
              ["Karte", "Set", "Nr", "Foil", "Sprache", "Scan", "im Bestand"])
    for m in unbekannt:
        print("  nicht erkannt:", m["Name"], m["Edition"], m["Collector Number"])
    if not args.buchen:
        print("\nNur geprüft. Buchen mit --buchen (Verdachtsfälle zusätzlich mit --verdacht-buchen).")
        return
    if hash_treffer and not args.erzwingen:
        sys.exit("Abbruch: Datei schon gebucht (mit --erzwingen trotzdem buchen).")
    if unbekannt and not args.erzwingen:
        sys.exit("Abbruch: nicht erkannte Zeilen klären (mit --erzwingen ohne diese buchen).")
    buchen = [m for m, _ in neu] + ([m for m, _ in verdacht] if args.verdacht_buchen else [])
    if not buchen:
        print("Nichts zu buchen.")
        return
    bid = args.id or naechste_buchung(journal)
    datum = args.datum or time.strftime("%Y-%m-%d")
    beleg = f"Scan {os.path.basename(args.datei)} sha:{h}" + (f" – {args.beleg}" if args.beleg else "")
    neu_datei = not os.path.exists(args.journal)
    with open(args.journal, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        if neu_datei:
            w.writerow(JOURNAL_COLS)
        for m in buchen:
            w.writerow([m[c] for c in MOX_COLS] + [f"{bid} Scan", datum, beleg])
    print(f"\nGebucht: {bid} – {len(buchen)} Zeilen / {sum(int(m['Count']) for m in buchen)} Karten -> {args.journal}")
    if verdacht and not args.verdacht_buchen:
        print(f"Nicht gebucht (Verdacht): {len(verdacht)} Zeilen – nach Klärung erneut mit --verdacht-buchen.")
    if args.moxfield:
        with open(args.moxfield, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, quoting=csv.QUOTE_ALL)
            w.writerow(MOX_COLS)
            for m in buchen:
                w.writerow([m[c] for c in MOX_COLS])
        print(f"Moxfield-Import (nur Zugänge) -> {args.moxfield}")
    print("Danach: Datenbank neu bauen, 06/07 neu erzeugen, Protokoll „Import“.")


def netto_bestand(basis, journal_pfad):
    """Basis + Journal -> Zeilen im Moxfield-Format (Abgänge von passenden Basiszeilen abgezogen)."""
    with open(basis, encoding="utf-8-sig", newline="") as fh:
        rows = [dict(r) for r in csv.DictReader(fh)]
    offen = []
    schluessel = ("Name", "Edition", "Collector Number", "Foil", "Language")
    for j in lies_journal(journal_pfad):
        q = int(float(j.get("Count") or 0))
        if q > 0:
            rows.append({c: j.get(c, "") for c in MOX_COLS})
            continue
        rest = -q
        kand = [r for r in rows if all(r[c] == j[c] for c in schluessel) and int(r["Count"]) > 0]
        # genaueste Zeile zuerst: gleicher Zeitstempel, dann gleicher Zustand
        kand.sort(key=lambda r: (r["Last Modified"] != j.get("Last Modified") or not j.get("Last Modified"),
                                 r["Condition"] != j.get("Condition")))
        for r in kand:
            if rest == 0:
                break
            ab = min(rest, int(r["Count"]))
            r["Count"] = str(int(r["Count"]) - ab)
            rest -= ab
        if rest:
            offen.append((j.get("Buchung"), j.get("Name"), rest))
    out = []
    for r in rows:
        n = int(r["Count"])
        if n > 0:
            r["Tradelist Count"] = str(min(n, int(float(r.get("Tradelist Count") or 0))))
            out.append(r)
    return out, offen


def cmd_moxfield_export(con, args):
    """Gesamtbestand (Basis + Journal) als Moxfield-Sammlungs-CSV zum Ersetzen der Moxfield-Sammlung."""
    out, offen = netto_bestand(args.basis, args.journal)
    if offen:
        for b, n, q in offen:
            print(f"  !! Abgang ohne passende Zeile: {b} {n} ({q})")
        sys.exit("Abbruch: Abgänge passen nicht zur Basis.")
    out.sort(key=lambda r: (fold(r["Name"]), r["Edition"], r["Collector Number"], r["Language"], r["Foil"]))
    with open(args.datei, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(MOX_COLS)
        for r in out:
            w.writerow([r.get(c, "") for c in MOX_COLS])
    # Kontrolle gegen die Datenbank (Summe je Oracle-ID)
    soll = dict(con.execute("SELECT oracle_id, SUM(qty) FROM collection GROUP BY oracle_id HAVING SUM(qty)<>0"))
    ist = Counter()
    for r in out:
        _, oid, _ = match_print(con, {"set": r["Edition"], "cn": r["Collector Number"], "name": r["Name"]})
        ist[oid] += int(r["Count"])
    abw = {k for k in set(soll) | set(ist) if soll.get(k, 0) != ist.get(k, 0)}
    print(f"Moxfield-Export: {len(out)} Zeilen, {sum(int(r['Count']) for r in out)} Karten, "
          f"{len([k for k in ist if ist[k]])} Unikate -> {args.datei}")
    print("Kontrolle gegen Datenbank: " + ("identisch" if not abw else f"{len(abw)} Abweichungen!"))


# ----------------------------------------------------------------- Snapshots & Vergleich
def datei_slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", fold(text)).strip("-")
    return s or "deck"


def cmd_snapshot(con, args):
    """Soll-Stand aller Decks als Moxfield-Text in einen Ordner (für claude/decks/ im Projekt)."""
    os.makedirs(args.ordner, exist_ok=True)
    stand = time.strftime("%Y-%m-%d")
    for did, kurz, neu, datei, karten in con.execute(
            "SELECT deck_id, kurz, neuer_name, datei, karten FROM decks ORDER BY kurz").fetchall():
        if args.deck and did != find_deck(con, args.deck):
            continue
        fn = os.path.join(args.ordner, datei_slug(kurz) + ".txt")
        kopf = (f"// Soll-Stand: {neu}\n// Kurzname: {kurz} | {karten} Karten | Quelle: {datei} | Stand: {stand}"
                + (f" | {args.hinweis}" if args.hinweis else ""))
        with open(fn, "w", encoding="utf-8") as fh:
            fh.write(kopf + "\n" + deck_text(con, did, sets=True, marker=True, nur_sicher=not args.drucke) + "\n")
        print(f"{kurz} -> {fn}")


def zaehlen(con, rows, boards):
    c, namen = Counter(), {}
    for _, board, n, q, *_rest, oid in rows:
        if board in boards:
            key = oid or f"?{n}"
            c[key] += q
            namen.setdefault(key, front(n) if oid is None else
                             con.execute("SELECT name FROM cards WHERE oracle_id=?", (oid,)).fetchone()[0])
    return c, namen


def lies_vergleichsdatei(con, path, art=None):
    """-> ('deck', {board: (Counter, Namen)}) oder ('sammlung', (Counter, Namen))."""
    if path.lower().endswith(".csv"):
        with open(path, encoding="utf-8-sig") as fh:
            erste = fh.readline()
        if erste.lstrip('"').startswith("#"):                     # Bestandsliste 06 (Name, Besitz, …)
            with open(path, encoding="utf-8-sig", newline="") as fh:
                fh.readline()
                rd = csv.DictReader(fh)
                c, namen = Counter(), {}
                for r in rd:
                    oid = resolve_name(con, r["Name"]) or f"?{r['Name']}"
                    c[oid] += int(r.get("Besitz") or 0)
                    namen[oid] = r["Name"]
            return "sammlung", (c, namen)
        _, zeilen = read_csv_rows(path)
        menge = sum(int(float(r.get("qty") or 1)) for r in zeilen)
        if (art or ("sammlung" if menge > 250 else "deck")) == "sammlung":
            c, namen = Counter(), {}
            for r in zeilen:
                _, oid, _ = match_print(con, r)
                key = oid or f"?{r.get('name')}"
                c[key] += int(float(r.get("qty") or 1))
                namen.setdefault(key, r.get("name"))
            return "sammlung", (c, namen)
    rows = deck_rows(con, path)
    assign_commander(con, rows, os.path.basename(path), {})
    return "deck", {"haupt": zaehlen(con, rows, ("main",)), "commander": zaehlen(con, rows, ("commander",)),
                    "sideboard": zaehlen(con, rows, ("sideboard", "companion"))}


def diff(alt, neu):
    (ca, na), (cn, nn) = alt, neu
    namen = {**na, **nn}
    raus = sorted(((ca[k] - cn.get(k, 0), namen[k]) for k in ca if ca[k] > cn.get(k, 0)), key=lambda x: x[1])
    rein = sorted(((cn[k] - ca.get(k, 0), namen[k]) for k in cn if cn[k] > ca.get(k, 0)), key=lambda x: x[1])
    return raus, rein


def liste_txt(eintraege, limit=40):
    if not eintraege:
        return "–"
    s = ", ".join(f"{q} {n}" for q, n in eintraege[:limit])
    return s + (f" … (+{len(eintraege) - limit} weitere)" if len(eintraege) > limit else "")


def deck_vergleich(alt, neu, titel, quelle):
    """Zwei gelesene Decks vergleichen -> (geändert?, Markdown-Eintrag)."""
    zeilen = [f"### {time.strftime('%Y-%m-%d')} · Abgleich · {titel}", f"- Vergleich: {quelle}"]
    ka = sum(alt["haupt"][0].values()) + sum(alt["commander"][0].values())
    kn = sum(neu["haupt"][0].values()) + sum(neu["commander"][0].values())
    zeilen.append(f"- Karten: {ka} → {kn}")
    geaendert = False
    cmd_a, cmd_n = sorted(alt["commander"][1].values()), sorted(neu["commander"][1].values())
    if cmd_a != cmd_n:
        geaendert = True
        zeilen.append(f"- Commander: {' + '.join(cmd_a) or '–'} → {' + '.join(cmd_n) or '–'}")
    for board, label in (("haupt", ""), ("sideboard", " (Sideboard)")):
        raus, rein = diff(alt[board], neu[board])
        if raus or rein:
            geaendert = True
            zeilen.append(f"- raus{label} ({sum(q for q, _ in raus)}): {liste_txt(raus)}")
            zeilen.append(f"- rein{label} ({sum(q for q, _ in rein)}): {liste_txt(rein)}")
    if not geaendert:
        zeilen.append("- keine Unterschiede")
    else:
        zeilen.append("- Grund: _offen – mit Nutzer klären (Absicht oder Fehler in Moxfield?)_")
    return geaendert, "\n".join(zeilen)


def cmd_vergleich(con, args):
    if args.snapshots:
        return vergleich_snapshots(con, args)
    if not (args.alt and args.neu):
        sys.exit("vergleich <alt> <neu>  oder  vergleich --snapshots <ordner>")
    ta, a = lies_vergleichsdatei(con, args.alt, args.art)
    tn, n = lies_vergleichsdatei(con, args.neu, args.art)
    if ta != tn:
        sys.exit(f"Unterschiedliche Dateiarten: {ta} vs. {tn} (mit --art deck|sammlung festlegen)")
    quelle = f"`{os.path.basename(args.alt)}` → `{os.path.basename(args.neu)}`"
    if ta == "deck":
        _, eintrag = deck_vergleich(a, n, args.titel or os.path.basename(args.neu), quelle)
        print(eintrag)
        return
    raus, rein = diff(a, n)
    ka, kn = sum(a[0].values()), sum(n[0].values())
    ua, un = sum(1 for v in a[0].values() if v), sum(1 for v in n[0].values() if v)
    eintrag = [f"### {time.strftime('%Y-%m-%d')} · Import · {args.titel or 'Sammlung'}",
               f"- Vergleich: {quelle}",
               f"- Karten: {ka} → {kn} ({kn - ka:+d}) · Unikate: {ua} → {un} ({un - ua:+d})",
               f"- neu/mehr ({sum(q for q, _ in rein)}): {liste_txt(rein, 30)}",
               f"- weg/weniger ({sum(q for q, _ in raus)}): {liste_txt(raus, 30)}"]
    if raus:
        eintrag.append("- Grund für Abgänge: _offen – verkauft/getauscht/Scanfehler?_")
    print("\n".join(eintrag))
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Karte", "alt", "neu", "Differenz"])
            for k in sorted(set(a[0]) | set(n[0]), key=lambda k: {**a[1], **n[1]}[k]):
                d = n[0].get(k, 0) - a[0].get(k, 0)
                if d:
                    w.writerow([{**a[1], **n[1]}[k], a[0].get(k, 0), n[0].get(k, 0), d])
        print(f"\nVollständige Differenz -> {args.csv}")


def vergleich_snapshots(con, args):
    """Alle Decks der Datenbank gegen den Soll-Stand (Snapshot-Ordner) prüfen."""
    snaps = {}
    for fn in sorted(os.listdir(args.snapshots)):
        if fn.endswith(".txt"):
            p = os.path.join(args.snapshots, fn)
            _, d = lies_vergleichsdatei(con, p)
            snaps[fn[:-4]] = (p, d)
    benutzt = set()
    eintraege, gleich, neu_ohne = [], [], []
    for did, kurz, datei in con.execute("SELECT deck_id, kurz, datei FROM decks ORDER BY kurz").fetchall():
        rows = [list(r) for r in con.execute("SELECT deck_id, board, name, qty, set_code, cn, oracle_id"
                                             " FROM deck_cards WHERE deck_id=?", (did,))]
        ist = {"haupt": zaehlen(con, rows, ("main",)), "commander": zaehlen(con, rows, ("commander",)),
               "sideboard": zaehlen(con, rows, ("sideboard", "companion"))}
        key = datei_slug(kurz)
        if key not in snaps:      # Fallback: gleicher Commander
            cmd = set(ist["commander"][0])
            key = next((k for k, (_, d) in snaps.items() if cmd and set(d["commander"][0]) == cmd), None)
        if not key:
            neu_ohne.append(f"{kurz} ({datei})")
            continue
        benutzt.add(key)
        geaendert, eintrag = deck_vergleich(snaps[key][1], ist, kurz,
                                            f"Soll-Stand `decks/{key}.txt` → Export `{datei}`")
        (eintraege.append(eintrag) if geaendert else gleich.append(kurz))
    print(f"Unverändert gegenüber Soll-Stand: {', '.join(gleich) or '–'}")
    if neu_ohne:
        print(f"Neue Decks ohne Soll-Stand: {', '.join(neu_ohne)}")
    fehlend = [k for k in snaps if k not in benutzt]
    if fehlend:
        print(f"Soll-Stand ohne Deck im Import (zerlegt oder nicht exportiert?): {', '.join(fehlend)}")
    print()
    print("\n\n".join(eintraege) if eintraege else "Keine Abweichungen.")


def cmd_suche(con, args):
    where, par = ["1=1"], []
    if args.tag:
        where.append("k.oracle_id IN (SELECT oracle_id FROM tags WHERE tag=?)")
        par.append(args.tag)
    if args.farben is not None:
        erlaubt = set(args.farben.upper())
        nicht = [c for c in WUBRG if c not in erlaubt]
        for c in nicht:
            where.append("instr(k.color_identity, ?) = 0")
            par.append(c)
    if args.max_mv is not None:
        where.append("k.cmc <= ?")
        par.append(args.max_mv)
    if args.text:
        where.append("lower(c.oracle_text) LIKE ?")
        par.append(f"%{args.text.lower()}%")
    if args.typ:
        where.append("lower(k.type_line) LIKE ?")
        par.append(f"%{args.typ.lower()}%")
    if args.nur_besitz:
        where.append("k.besitz > 0")
    if args.nur_frei:
        where.append("k.frei > 0")
    if not args.alle_formate:
        where.append("c.legal_commander = 'legal'")
    sql = (f"SELECT k.name, k.cmc, k.type_line, k.color_identity, k.game_changer, k.eur_min, k.besitz,"
           f" k.frei, k.deck_ids FROM v_karten k JOIN cards c USING(oracle_id) WHERE {' AND '.join(where)}"
           f" ORDER BY (k.frei>0) DESC, (k.besitz>0) DESC, COALESCE(c.edhrec_rank, 999999) LIMIT ?")
    table(con.execute(sql, par + [args.limit]).fetchall(),
          ["Karte", "MV", "Typ", "Farben", "GC", "ab €", "Besitz", "frei", "in Decks"])


def cmd_bestand_export(con, args):
    rows = con.execute("""SELECT k.name, k.besitz, k.in_decks, k.frei, k.color_identity, c.type_line,
        k.cmc, k.game_changer, k.eur_min, k.deck_ids,
        (SELECT GROUP_CONCAT(DISTINCT UPPER(set_code)) FROM collection x WHERE x.oracle_id=k.oracle_id),
        k.vorgemerkt, k.ideen, k.verkauf_geplant, k.verkauf_ideen
        FROM v_karten k JOIN cards c USING(oracle_id) WHERE k.besitz > 0 ORDER BY k.name""").fetchall()
    stand = dict(con.execute("SELECT key, value FROM meta").fetchall())
    decks = ", ".join(r[0] for r in con.execute("SELECT kurz FROM decks ORDER BY kurz"))
    zusatz = f" – {args.hinweis}" if args.hinweis else ""
    with open(args.datei, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"# GESAMTBESTAND je Karte (inkl. Karten in Decks) – Sammlung: {stand.get('sammlung')} – "
                    f"Preise Scryfall-EUR (günstigster Druck) Stand {stand.get('bulk_default_cards')}{zusatz}"])
        w.writerow(["Name", "Besitz", "davon in Decks", "frei", "Farbidentität", "Typ", "MV", "Game Changer",
                    "ab EUR", "Decks", "Sets", "vorgemerkt", "Ideen", "Verkauf geplant", "Verkaufsideen"])
        for r in rows:
            w.writerow(["" if v is None else v for v in r])
    print(f"{len(rows)} Karten -> {args.datei}")
    if args.frei:
        frei = [r for r in rows if r[3] > 0]
        with open(args.frei, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([f"# FREIE KARTEN = Besitz minus alle Decks ({decks}) minus Vormerkungen – Kandidaten für Upgrade-Stufe 0 – "
                        f"Sammlung: {stand.get('sammlung')} – Preise Stand {stand.get('bulk_default_cards')}{zusatz}"])
            w.writerow(["Name", "frei", "Besitz", "Farbidentität", "Typ", "MV", "Game Changer", "ab EUR", "Sets",
                        "Verkauf geplant"])
            for r in frei:
                w.writerow(["" if v is None else v for v in (r[0], r[3], r[1], r[4], r[5], r[6], r[7], r[8], r[10],
                                                               f"{r[13]} ({r[14]})" if r[13] else "")])
        print(f"{len(frei)} freie Karten ({sum(r[3] for r in frei)} Exemplare) -> {args.frei}")


def deck_zeitstempel(con, did):
    """Erfassungszeitpunkt eines Decks und freie Exemplare mit demselben Zeitpunkt.
    -> (zeitpunkt, freie Exemplare) – freie Liste nur, wenn der Zeitpunkt für dieses Deck typisch ist
    (≥ 50 % aller so erfassten Exemplare stecken im Deck); sonst (zeitpunkt, None)."""
    try:
        r = con.execute("SELECT modified, COUNT(*) FROM exemplare WHERE deck_id=? AND zuordnung='zeitstempel'"
                        " GROUP BY modified ORDER BY 2 DESC LIMIT 1", (did,)).fetchone()
    except sqlite3.OperationalError:
        return None, None
    if not r:
        return None, None
    ges = con.execute("SELECT COUNT(*) FROM exemplare WHERE modified=?", (r[0],)).fetchone()[0]
    if r[1] / ges < 0.5:
        return r[0], None
    return r[0], con.execute("SELECT name, UPPER(set_code)||' '||cn, lang, oracle_id FROM exemplare WHERE modified=?"
                             " AND deck_id IS NULL ORDER BY name", (r[0],)).fetchall()


def cmd_exemplare(con, args):
    """Exemplare einer Karte oder eines Decks: Druck, Sprache, Finish, Ort (Deck/vorgemerkt/frei), Zuordnung."""
    oid = None if str(args.ref).isdigit() else resolve_name(con, args.ref)
    sql = ("SELECT e.name, UPPER(e.set_code)||' '||e.cn, e.lang, e.finish, COALESCE(k.kurz, CASE WHEN e.idee IS NOT NULL"
           " THEN 'vorgemerkt ('||e.idee||')' WHEN e.verkauf IS NOT NULL THEN 'frei · Verkauf geplant ('||e.verkauf||')'"
           " ELSE 'frei' END), COALESCE(e.zuordnung,''), e.modified FROM exemplare e"
           " LEFT JOIN decks k USING(deck_id) WHERE ")
    if oid:
        rows = con.execute(sql + "e.oracle_id=? ORDER BY k.kurz IS NULL, k.kurz, e.set_code", (oid,)).fetchall()
    else:
        rows = con.execute(sql + "e.deck_id=? ORDER BY e.name, e.set_code", (find_deck(con, args.ref),)).fetchall()
    table(rows, ["Karte", "Druck", "Sprache", "Finish", "Ort", "Zuordnung", "erfasst"])
    if rows and not oid:
        z = Counter(r[5] for r in rows)
        print(f"\n{len(rows)} Exemplare – Zuordnung: " + ", ".join(f"{k or '–'} {v}" for k, v in z.most_common())
              + " (druck = aus Deckliste/Scan sicher; zeitstempel/set = sehr wahrscheinlich; geschätzt = unsicher)")
        zp, frei = deck_zeitstempel(con, find_deck(con, args.ref))
        if frei:
            print(f"\nNicht im Deck, aber zusammen mit dem Deck erfasst ({zp[:16]}) – liegen sie physisch beim Deck"
                  f" (Maybeboard, fehlende Karten)? Beim Neuscan klären: " + ", ".join(f"{n} ({d} {l})" for n, d, l, _ in frei))


def cmd_drucke(con, args):
    """Entwurf → Moxfield-Text mit (SET) Nummer je eigenem Exemplar (Deck-PDF zeigt dann die eigenen Drucke)."""
    did = find_deck(con, args.deck) if args.deck else None
    rows = deck_rows(con, args.entwurf)
    assign_commander(con, rows, os.path.basename(args.entwurf), {})
    menge = defaultdict(Counter)
    namen = {}
    for _, board, n, q, st, cn, oid in rows:
        if oid and board in ("main", "commander"):
            menge[board][oid] += q
            namen[oid] = con.execute("SELECT name FROM cards WHERE oracle_id=?", (oid,)).fetchone()[0]
    rang = "CASE zuordnung WHEN 'druck' THEN 0 WHEN 'zeitstempel' THEN 1 WHEN 'set' THEN 2 ELSE 3 END"
    teile, stat = [], Counter()
    for board in ("main", "commander"):
        zeilen = []
        for oid in sorted(menge[board], key=lambda o: fold(namen[o])):
            q = menge[board][oid]
            kopien = (con.execute(f"SELECT set_code, cn, finish FROM exemplare WHERE deck_id=? AND oracle_id=?"
                                  f" ORDER BY {rang}", (did, oid)).fetchall() if did else [])[:q]
            stat["aus dem Deck"] += len(kopien)
            if len(kopien) < q:
                frei = con.execute("SELECT set_code, cn, finish FROM exemplare WHERE oracle_id=? AND deck_id IS NULL"
                                   " AND (idee IS NULL OR idee=?) ORDER BY lang<>'en', set_code",
                                   (oid, args.idee or "")).fetchall()[:q - len(kopien)]
                stat["frei"] += len(frei)
                kopien += frei
            for (st, cn, fin), k in sorted(Counter(kopien).items(), key=lambda x: -x[1]):
                zeilen.append(f"{k} {namen[oid]} ({st.upper()}) {cn}" + {"foil": " *F*", "etched": " *E*"}.get(fin, ""))
            if len(kopien) < q:
                zeilen.append(f"{q - len(kopien)} {namen[oid]}")
                stat["ohne Exemplar (Kauf)"] += q - len(kopien)
        if zeilen:
            teile.append(("// Commander\n" if board == "commander" else "") + "\n".join(zeilen))
    open(args.out, "w", encoding="utf-8").write("\n\n".join(teile) + "\n")
    print(f"{args.out}: " + ", ".join(f"{k} {v}" for k, v in stat.items()))


def cmd_sql(con, args):
    cur = con.execute(args.query)
    table(cur.fetchall(), [d[0] for d in cur.description])


def main():
    import signal
    if hasattr(signal, "SIGPIPE"):          # Ausgabe in `head` o. Ä. ohne Traceback beenden
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="mtg.sqlite")
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("build")
    b.add_argument("--sammlung", nargs="+", required=True)
    b.add_argument("--decks", nargs="*", default=[])
    b.add_argument("--bulk", default="bulk")
    b.add_argument("--config", default="deck_namen.json")
    b.add_argument("--vormerkungen", default="data/vormerkungen.csv",
                   help="Vormerkungen aus Ideen (Standard: data/vormerkungen.csv, falls vorhanden)")
    b.add_argument("--scan-decks", nargs="*", default=[], metavar="CSV",
                   help="ManaBox-Scan-Exporte als Decklisten (je Binder ein Deck), nicht Teil der Sammlung")
    b.add_argument("--binder-decks", nargs="?", const="", default=None, metavar="MUSTER",
                   help="Decks aus Bindern der Sammlung (ManaBox): Binder-Typ 'deck' oder Name passt zu MUSTER")
    for n in ("sammlung", "decks", "namen", "mehrfach"):
        sp.add_parser(n)
    la = sp.add_parser("laender")
    la.add_argument("deck", nargs="?")
    la.add_argument("--plan", help="z. B. 'Plains=12, Swamp=10, Mountain=8'")
    for n in ("besitz", "bracket"):
        sp.add_parser(n).add_argument("deck")
    e = sp.add_parser("export")
    e.add_argument("deck")
    e.add_argument("--sets", action="store_true")
    s = sp.add_parser("suche")
    s.add_argument("--tag")
    s.add_argument("--farben")
    s.add_argument("--max-mv", type=float)
    s.add_argument("--text")
    s.add_argument("--typ")
    s.add_argument("--nur-besitz", action="store_true")
    s.add_argument("--nur-frei", action="store_true")
    s.add_argument("--alle-formate", action="store_true")
    s.add_argument("--limit", type=int, default=30)
    be = sp.add_parser("bestand-export")
    be.add_argument("datei")
    be.add_argument("--frei", help="zweite Datei nur mit freien Karten (nicht in Decks)")
    be.add_argument("--hinweis", help="Zusatz für die Kopfzeile, z. B. 'vorläufig'")
    sp.add_parser("sql").add_argument("query")
    sn = sp.add_parser("snapshot")
    sn.add_argument("ordner")
    sn.add_argument("--deck", help="nur dieses Deck")
    sn.add_argument("--hinweis", help="Zusatz im Kopf, z. B. 'vorläufig'")
    sn.add_argument("--drucke", action="store_true", help="auch ermittelte (nicht nur sichere) Drucke schreiben")
    sp.add_parser("exemplare").add_argument("ref", help="Karte (Oracle-Name) oder Deck")
    dr = sp.add_parser("drucke")
    dr.add_argument("entwurf")
    dr.add_argument("--deck", help="Deck, dessen Exemplare der Entwurf behält")
    dr.add_argument("--idee", help="Vormerkungen dieser Idee zählen als frei")
    dr.add_argument("--out", required=True)
    v = sp.add_parser("vergleich")
    v.add_argument("alt", nargs="?")
    v.add_argument("neu", nargs="?")
    v.add_argument("--snapshots", metavar="ORDNER", help="alle Decks der DB gegen den Soll-Stand prüfen")
    v.add_argument("--titel")
    v.add_argument("--art", choices=("deck", "sammlung"))
    v.add_argument("--csv", help="vollständige Sammlungsdifferenz als CSV")
    mb = sp.add_parser("manabox-zu-moxfield")
    mb.add_argument("datei", help="ManaBox-CSV (Scan eines Decks/Binders)")
    mb.add_argument("--sammlung", help="Ausgabe: Moxfield-Sammlungs-CSV")
    mb.add_argument("--deck", help="Ausgabe: Moxfield-Deck-TXT")
    mb.add_argument("--sets", action="store_true", help="Set und Sammlernummer in die Deckliste schreiben")
    mb.add_argument("--tausch", type=int, default=0, help="Tradelist Count je Zeile (Standard 0)")
    mb.add_argument("--tags", help="Moxfield-Tag für alle Zeilen")
    mb.add_argument("--config", default="deck_namen.json")
    sc = sp.add_parser("scan", help="ManaBox-Scan prüfen und als Zugang buchen (Doppelscan-Schutz)")
    sc.add_argument("datei", help="ManaBox-CSV")
    sc.add_argument("--journal", default="data/buchungen.csv")
    sc.add_argument("--buchen", action="store_true", help="neue Zeilen ins Journal schreiben")
    sc.add_argument("--verdacht-buchen", action="store_true", help="auch Verdachtsfälle buchen (nach Klärung)")
    sc.add_argument("--erzwingen", action="store_true", help="trotz Datei-Treffer/unbekannter Zeilen buchen")
    sc.add_argument("--id", help="Buchungs-ID (Standard: nächste freie B-nnn)")
    sc.add_argument("--datum", help="Buchungsdatum JJJJ-MM-TT (Standard: heute)")
    sc.add_argument("--beleg", help="Zusatz zum Beleg, z. B. 'Booster Display FDN'")
    sc.add_argument("--moxfield", help="Ausgabe: Moxfield-CSV nur mit den gebuchten Zugängen")
    mx = sp.add_parser("moxfield-export", help="Gesamtbestand als Moxfield-Sammlungs-CSV")
    mx.add_argument("datei")
    mx.add_argument("--basis", default="data/moxfield_haves_2026-10-26-0709Z.csv")
    mx.add_argument("--journal", default="data/buchungen.csv")
    args = ap.parse_args()
    if args.cmd == "build":
        return build(args)
    con = sqlite3.connect(args.db)
    {"sammlung": cmd_sammlung, "decks": cmd_decks, "namen": cmd_namen, "besitz": cmd_besitz,
     "mehrfach": cmd_mehrfach, "bracket": cmd_bracket, "export": cmd_export, "suche": cmd_suche,
     "laender": cmd_laender, "bestand-export": cmd_bestand_export, "sql": cmd_sql, "exemplare": cmd_exemplare, "drucke": cmd_drucke,
     "snapshot": cmd_snapshot, "vergleich": cmd_vergleich,
     "manabox-zu-moxfield": cmd_manabox_zu_moxfield, "scan": cmd_scan,
     "moxfield-export": cmd_moxfield_export}[args.cmd](con, args)


if __name__ == "__main__":
    main()
