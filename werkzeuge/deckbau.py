#!/usr/bin/env python3
"""deckbau.py – Werkzeuge für das geführte Commander-Deckbau-Verfahren (Projektdatei 08_Deckbau-Verfahren).

Setzt eine mit mtg_db.py gebaute Datenbank voraus (mtg.sqlite im aktuellen Ordner, mtg_db.py daneben).

Befehle
  commander <Name> [--bracket 3] [--budget]
        Steckbrief: Oracle-Text, Farbidentität, Besitz; EDHREC-Themen mit Deckzahlen, Top- und
        High-Lift-Karten, häufige Combos -> Grundlage für die Strategie-Fragen im Interview.
  commander-suche [--thema SLUG] [--farben RWB] [--text TXT] [--nur-besitz] [--limit N]
        Commander finden, wenn der Nutzer keinen vorgibt (EDHREC-Themenseite oder lokale Suche).
  kandidaten <Commander> --weg 1|2 [--bracket 3] [--thema SLUG] [--budget] [--out kandidaten.csv]
        Kartenpool aus EDHREC (Bracket-/Themenfilter) + allen freien Sammlungskarten in der
        Farbidentität, mit Rollen, Synergie, Besitz, Preis. Weg 1: Machbarkeitsampel nur mit freien Karten.
  pruefen <deckdatei> [--bracket 3] [--ersetzt <deck>] [--idee I-nnn] [--combos-fehlend]
        Qualitätskontrolle eines Entwurfs: Kartenzahl, Farbidentität, Rollen gegen Template, Instant-
        Interaktion, Kurve, Farbquellen, Game Changer, MLD, Extra Turns, Combos (Commander Spellbook),
        Besitz/Kaufliste, Standardländer-Nachkauf. Am Ende: Warnungen.
  erklaerung <deckdatei> [--ersetzt <deck>] [--idee I-nnn] [--out erklaerung.csv]
        Datenbasis je Karte (Rollen, Synergie, Combo-Teil, Status, Oracle-Text, Stärke) für die Kartenerklärungen.
  upgrade <deck> [--stufe 0|1] [--max-preis 10] [--thema SLUG] [--bracket 3] [--paare 15] [--out upgrade.csv]
        Upgrade-Modus: Rollenbilanz, schwächste Deckkarten, beste freie Kandidaten je Rolle (Stufe 1: auch Käufe
        bis --max-preis), Tauschpaare „raus → rein“ als Startpunkt mit Datenbasis für „warum raus“/„warum rein“,
        Oracle-Text beider Seiten; schreibt die Paare nach <out>_paare.txt (für fazit --paare).
  passung <deck> [--thema landfall] [--kauf 3] [--kandidaten 10]
        Ausgangslage vor den Fragen (Deckänderung): Was trägt das Deck (Archetyp-Deckung), was spielt der Commander
        (EDHREC-Themen), wie viele Spielkarten haben Bezug zum Commander, welche Commander aus Deck, freier Sammlung
        (und mit --kauf vom Markt) passen besser – Befund und Optionen A–D für die Abwägung mit dem Nutzer.
  fazit --neu <Entwurf> [--alt <Soll-Stand>] [--paare paare.txt] [--thema A] [--stufe "Stufe 0"] [--out fazit.md]
        Fazit-Entwurf für kartenbilder.py: Kopf, Kacheln, Bracket-Zeile, Änderungen mit „warum raus“ und „warum rein“
        (Datenbasis), Kennzahlen vorher/nachher, Kartenerklärungen mit Status, Moxfield-Anhang – Claude füllt nur ‹…›.
  oracle <Karte …> | --alt <Soll-Stand> --neu <Entwurf> [--rulings]
        Oracle-Text (Manakosten, Typ, Stärke/Widerstand) – Pflicht vor jedem Vorschlag: neue Karten nur aus dem
        Oracle-Text beschreiben, nie aus dem Gedächtnis.
  alternativen <Karte> [--farben RWB] [--limit 5]
        Günstigere Karten mit gleicher Rolle (freie Sammlungskarten zuerst).

--ersetzt <deck>: Karten dieses Decks gelten für den Entwurf als vorhanden (Upgrade eines bestehenden Decks).
  Ohne Angabe erkennt pruefen/erklaerung ein geladenes Deck mit gleichem Dateinamen (z. B. decks/boros.txt).
--idee I-nnn: Vormerkungen dieser Idee (claude/sammlung/vormerkungen.csv) gelten für den Entwurf als frei.

Kennzahlen (einheitlich in allen Werkzeugen, Stand 27.10.2026):
  Rollen        zählen über die 99 ohne Commander (der Commander ist Plan, nicht Slot).
  Ø MV / Kurve  über alle Nichtländer inklusive Commander (wie Deck-PDF und archetypen.py).
  EDHREC-Werte  Inclusion/Synergie von der Commander-Seite mit Bracket-Filter, ohne Thema (commanders/<slug>/<bracket>);
                Themenseiten nur für die Kandidatensuche und dann als „Thema“ gekennzeichnet.
"""
import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mtg_db as M  # noqa: E402

BRACKET_PFAD = {1: "exhibition", 2: "core", 3: "upgraded", 4: "optimized", 5: "cedh"}
GC_LIMIT = {1: 0, 2: 0, 3: 3, 4: 99, 5: 99}

# Rollen: (Schlüssel, Anzeige, Minimum, Ziel, Herkunft des Richtwerts)
ROLLEN = [
    ("land", "Länder", 35, 38, "Template"),
    ("ramp", "Ramp", 10, 12, "Template"),
    ("ka", "Kartenvorteil", 10, 12, "Template"),
    ("gezielt", "Gezielte Interaktion", 10, 12, "Template"),
    ("massen", "Massen-Interaktion", 3, 6, "Template; Minimum 3 = Einschätzung"),
    ("schutz", "Schutz", 2, 4, "Erweiterung (Einschätzung)"),
    ("tutor", "Tutor", None, None, "Info"),
    ("rekursion", "Rekursion", None, None, "Info"),
]
ROLLE_NAME = {k: n for k, n, *_ in ROLLEN}
TAGS_RAMP = {"ramp", "mana-rock", "mana-dork", "land-ramp"}
TAGS_KA = {"card-advantage", "draw"}
TAGS_SCHUTZ = {"protects-all", "protects-creature", "gives-indestructible", "gives-hexproof",
               "gives-protection", "protects-permanent"}
FARBSLUG = {"W": "mono-white", "U": "mono-blue", "B": "mono-black", "R": "mono-red", "G": "mono-green"}


# ----------------------------------------------------------------- Grundlagen
def db():
    if not os.path.exists("mtg.sqlite"):
        sys.exit("mtg.sqlite fehlt – zuerst 'python3 mtg_db.py build …' ausführen")
    return sqlite3.connect("mtg.sqlite")


def card(con, oid):
    r = con.execute("SELECT oracle_id, name, mana_cost, cmc, type_line, oracle_text, color_identity, keywords,"
                    " legal_commander, game_changer, eur_min, edhrec_rank, produced_mana, pt FROM cards"
                    " WHERE oracle_id=?", (oid,)).fetchone()
    if not r:
        return None
    keys = ["oid", "name", "mana_cost", "cmc", "type_line", "text", "ci", "keywords", "legal", "gc",
            "eur", "rank", "produced", "pt"]
    return dict(zip(keys, r))


def finde(con, name):
    oid = M.resolve_name(con, name)
    if not oid:
        sys.exit(f"Karte '{name}' nicht gefunden (englischen Oracle-Namen verwenden)")
    return card(con, oid)


def tags_of(con, oid):
    return {r[0] for r in con.execute("SELECT tag FROM tags WHERE oracle_id=?", (oid,))}


def front_type(c):
    return (c["type_line"] or "").split(" // ")[0]


def rollen(con, c, tags=None):
    """Rollen einer Karte aus Typzeile und Scryfall-Funktionstags."""
    tags = tags if tags is not None else tags_of(con, c["oid"])
    if "Land" in front_type(c):
        return ["land"]
    r = []
    if tags & TAGS_RAMP and not gegner_rampe(c, tags):
        r.append("ramp")
    if tags & TAGS_KA:
        r.append("ka")
    if "spot-removal" in tags or "counterspell" in tags or ("removal" in tags and "sweeper" not in tags):
        r.append("gezielt")
    if "sweeper" in tags:
        r.append("massen")
    if tags & TAGS_SCHUTZ:
        r.append("schutz")
    if "tutor" in tags:
        r.append("tutor")
    if "recursion" in tags:
        r.append("rekursion")
    return r


def gegner_rampe(c, tags):
    """Removal, das dem Gegner ein Land gibt (Path to Exile u. Ä.), ist für uns kein Ramp."""
    return bool(tags & {"removal", "spot-removal"}) and bool(
        re.search(r"(its controller|that player|their controller)[^.]*search", (c["text"] or "").lower()))


def rollen_txt(r):
    return ",".join(ROLLE_NAME[x] for x in r) or "Plan/Synergie"


def ist_instant(c):
    return "Instant" in front_type(c) or "Flash" in (c["keywords"] or "")


IDEE = None   # mit --idee I-nnn: Vormerkungen dieser Idee gelten für den Entwurf als frei


def besitz(con, oid, ohne_deck=None):
    """(Besitz, in Decks ohne das ersetzte Deck, frei). Frei = Besitz - Decks - Vormerkungen anderer Ideen."""
    b = con.execute("SELECT COALESCE(SUM(qty),0) FROM collection WHERE oracle_id=? AND lower(proxy)<>'true'",
                    (oid,)).fetchone()[0]
    d = con.execute("SELECT COALESCE(SUM(qty),0) FROM deck_cards WHERE oracle_id=? AND deck_id IS NOT ?"
                    " AND board IN ('main','commander','sideboard','companion')", (oid, ohne_deck)).fetchone()[0]
    try:
        v = con.execute("SELECT COALESCE(SUM(qty),0) FROM vormerkungen WHERE oracle_id=? AND idee IS NOT ?",
                        (oid, IDEE)).fetchone()[0]
    except sqlite3.OperationalError:      # ältere Datenbank ohne Vormerkungen
        v = 0
    return b, d, max(b - d - v, 0)


def edh_slug(name):
    teile = [p.strip() for p in re.split(r"\s+\+\s+|\s*&\s*", name) if p.strip()]
    slugs = []
    for p in teile:
        n = re.sub(r"[^a-z0-9\s-]", "", M.fold(M.front(p)))
        slugs.append(re.sub(r"[\s-]+", "-", n).strip("-"))
    return "-".join(sorted(slugs)) if len(slugs) > 1 else slugs[0]


def edhrec(pfad, max_alter_h=72):
    os.makedirs("cache/edhrec", exist_ok=True)
    fn = os.path.join("cache/edhrec", pfad.replace("/", "__") + ".json")
    if os.path.exists(fn) and time.time() - os.path.getmtime(fn) < max_alter_h * 3600:
        return json.load(open(fn, encoding="utf-8"))
    try:
        d = M.get_json(f"https://json.edhrec.com/pages/{pfad}.json")
    except Exception:
        return None
    if not isinstance(d, dict) or "redirect" in d or "container" not in d:
        return None
    json.dump(d, open(fn, "w", encoding="utf-8"))
    return d


def edhrec_commander(name, bracket=None, thema=None, budget=False):
    """Probiert vom spezifischsten Pfad zum allgemeinsten; gibt (Daten, Pfad) zurück."""
    s = edh_slug(name)
    b = BRACKET_PFAD.get(bracket) if bracket else None
    kandidaten = []
    for teile in ([b, thema, "budget" if budget else None], [b, thema], [b, "budget" if budget else None],
                  [b], [thema], []):
        p = "/".join(["commanders", s] + [t for t in teile if t])
        if p not in kandidaten:
            kandidaten.append(p)
    for p in kandidaten:
        d = edhrec(p)
        if d:
            return d, p
    return None, None


def edh_karten(d):
    """EDHREC-Kartenlisten -> {Name: {synergy, inclusion, lift, decks, liste}}."""
    out = {}
    for cl in d["container"]["json_dict"].get("cardlists", []):
        for cv in cl.get("cardviews", []):
            n = cv.get("name")
            if not n or n in out:
                continue
            pot = cv.get("potential_decks") or 0
            out[n] = {"synergy": cv.get("synergy"), "lift": cv.get("lift"), "decks": cv.get("num_decks"),
                      "inclusion": (cv.get("num_decks") or 0) / pot if pot else None,
                      "liste": cl.get("header")}
    return out


def pct(x):
    return "" if x is None else f"{x * 100:.0f}%"


def lies_deck(con, path):
    """Deckdatei (Moxfield/ManaBox-Text oder CSV) -> (Commander-Karten, Hauptdeck-Karten) als Listen (Anzahl, card)."""
    rows = M.deck_rows(con, path)
    hinweis = M.assign_commander(con, rows, os.path.basename(path), {})
    unbekannt = [r[2] for r in rows if not r[6]]
    def sammeln(board):                         # je Karte zusammenfassen (mehrere Drucke = mehrere Zeilen)
        z = Counter()
        for r in rows:
            if r[1] == board and r[6]:
                z[r[6]] += r[3]
        return [(q, card(con, oid)) for oid, q in z.items()]
    return sammeln("commander"), sammeln("main"), unbekannt, hinweis


def basic(c):
    return front_type(c).startswith("Basic")


# ----------------------------------------------------------------- commander
def cmd_commander(con, a):
    c = finde(con, a.name)
    b, d, f = besitz(con, c["oid"])
    print(f"{c['name']}  {c['mana_cost']}  | {M.farbname(c['ci'])} | {c['type_line']}")
    print(f"Commander-legal: {c['legal']} | Game Changer: {'ja' if c['gc'] else 'nein'} | "
          f"Besitz {b}, in Decks {d}, frei {f} | ab {c['eur'] or '?'} €")
    print(f"\nOracle-Text:\n{c['text']}")
    t = sorted(tags_of(con, c["oid"]))
    print(f"\nScryfall-Funktionstags: {', '.join(t[:40])}{' …' if len(t) > 40 else ''}")
    data, pfad = edhrec_commander(c["name"], a.bracket, None, a.budget)
    if not data:
        print("\nEDHREC: keine Seite gefunden (neuer oder seltener Commander?)")
        return
    jd = data["container"]["json_dict"]
    allg, _ = edhrec_commander(c["name"])
    ges = allg["container"]["json_dict"].get("card", {}) if allg else {}
    print(f"\nEDHREC ({pfad}): {jd.get('card', {}).get('num_decks')} Decks in dieser Auswahl, "
          f"{ges.get('num_decks')} gesamt | Rang {ges.get('rank')} | Salt {round(ges.get("salt") or 0, 2)}")
    themen = data.get("panels", {}).get("taglinks", [])
    if themen:
        print("\nThemen (Decks mit diesem Thema – Grundlage für die Strategie-Frage):")
        M.table([(t["value"], t["slug"], t["count"]) for t in themen[:12]], ["Thema", "Slug", "Decks"])
    combos = [x["value"] for x in data.get("panels", {}).get("combocounts", []) if "See More" not in x["value"]]
    if combos:
        print("\nHäufige Combos laut EDHREC: " + " | ".join(combos))
    karten = edh_karten(data)
    for liste in ("Top Cards", "High Lift Cards", "High Synergy Cards"):
        sel = [(n, v) for n, v in karten.items() if v["liste"] == liste]
        if not sel:
            continue
        print(f"\n{liste}:")
        rows = []
        for n, v in sel[:12]:
            oid = M.resolve_name(con, n)
            bb, dd, ff = besitz(con, oid) if oid else (0, 0, 0)
            rows.append((n, pct(v["inclusion"]), f"{(v['synergy'] or 0) * 100:+.0f}%", ff, bb))
        M.table(rows, ["Karte", "Inclusion", "Synergie", "frei", "Besitz"])


# ----------------------------------------------------------------- commander-suche
def cmd_commander_suche(con, a):
    rows = []
    if a.thema:
        ci = set((a.farben or "").upper())
        slug = None
        if len(ci) == 1:
            slug = FARBSLUG[next(iter(ci))]
        elif 2 <= len(ci) <= 3:
            slug = M.FARBNAMEN[frozenset(ci)][0].lower()
        d = (edhrec(f"tags/{a.thema}/{slug}") if slug else None) or edhrec(f"tags/{a.thema}")
        if not d:
            sys.exit(f"EDHREC-Thema '{a.thema}' nicht gefunden (Slug wie auf edhrec.com/tags, z. B. tokens, aristocrats)")
        for cl in d["container"]["json_dict"]["cardlists"]:
            if "Commander" not in cl.get("header", ""):
                continue
            for cv in cl["cardviews"]:
                oid = M.resolve_name(con, cv["name"])
                if not oid:
                    continue
                c = card(con, oid)
                if ci and not set(c["ci"]) <= ci:
                    continue
                b, dd, f = besitz(con, oid)
                if a.nur_besitz and not b:
                    continue
                rows.append((c["name"], c["ci"], cv.get("num_decks"), b, f, c["eur"], cl["header"]))
        rows.sort(key=lambda r: (-(r[4] > 0), -(r[2] or 0)))
        M.table(rows[:a.limit], ["Commander", "Farben", "Decks (Thema)", "Besitz", "frei", "ab €", "Liste"])
        return
    where, par = ["((c.type_line LIKE '%Legendary%' AND (c.type_line LIKE '%Creature%' OR c.type_line LIKE "
                  "'%Vehicle%' OR c.type_line LIKE '%Spacecraft%')) OR c.oracle_text LIKE '%can be your commander%')",
                  "c.legal_commander='legal'"], []
    if a.farben:
        where.append("c.color_identity = ?")
        par.append(M.ci_str(a.farben.upper()))
    if a.text:
        where.append("lower(c.oracle_text) LIKE ?")
        par.append(f"%{a.text.lower()}%")
    if a.nur_besitz:
        where.append("k.besitz > 0")
    sql = (f"SELECT c.name, c.color_identity, c.edhrec_rank, k.besitz, k.frei, c.eur_min FROM cards c "
           f"JOIN v_karten k USING(oracle_id) WHERE {' AND '.join(where)} "
           f"ORDER BY (k.besitz>0) DESC, COALESCE(c.edhrec_rank, 999999) LIMIT ?")
    M.table(con.execute(sql, par + [a.limit]).fetchall(), ["Commander", "Farben", "EDHREC-Rang", "Besitz", "frei", "ab €"])


# ----------------------------------------------------------------- kandidaten
def basics_verfuegbar(con, ci, ohne_deck=None):
    out = {}
    for name, oid in con.execute("SELECT name, oracle_id FROM v_basics"):
        if name in ("Plains", "Island", "Swamp", "Mountain", "Forest"):
            farbe = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}[name]
            if farbe in ci:
                out[name] = besitz(con, oid, ohne_deck)[2]
    return out


def cmd_kandidaten(con, a):
    cmd = finde(con, a.commander)
    ci = set(cmd["ci"])
    data, pfad = edhrec_commander(cmd["name"], a.bracket, a.thema, a.budget)
    edh = edh_karten(data) if data else {}
    pool = {}
    for n, v in edh.items():
        oid = M.resolve_name(con, n)
        if oid:
            pool[oid] = dict(v, quelle="EDHREC")
    for (oid,) in con.execute("SELECT oracle_id FROM v_karten WHERE frei > 0"):
        pool.setdefault(oid, {"synergy": None, "lift": None, "inclusion": None, "decks": None,
                              "liste": None, "quelle": "Sammlung"})
    zeilen = []
    for oid, v in pool.items():
        c = card(con, oid)
        if not c or oid == cmd["oid"] or c["legal"] != "legal" or not set(c["ci"]) <= ci or basic(c):
            continue
        t = tags_of(con, oid)
        r = rollen(con, c, t)
        b, d, f = besitz(con, oid)
        zeilen.append({"name": c["name"], "rollen": r, "instant": ist_instant(c), "mv": c["cmc"],
                       "typ": front_type(c), "synergy": v["synergy"], "inclusion": v["inclusion"],
                       "lift": v["lift"], "frei": f, "besitz": b, "in_decks": d, "eur": c["eur"],
                       "gc": c["gc"], "rank": c["rank"], "quelle": v["quelle"], "liste": v["liste"]})
    zeilen.sort(key=lambda z: (-(z["frei"] > 0) if a.weg == 1 else 0, -(z["synergy"] or -1),
                               -(z["inclusion"] or 0), z["rank"] or 999999))
    out = a.out or "kandidaten.csv"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"# Kandidaten für {cmd['name']} – Weg {a.weg} – EDHREC: {pfad or 'keine Daten'} – "
                    f"Stand {time.strftime('%Y-%m-%d')}"])
        w.writerow(["Karte", "Rollen", "Instant", "MV", "Typ", "Synergie", "Inclusion", "Lift", "frei",
                    "Besitz", "in Decks", "ab EUR", "Game Changer", "Quelle", "EDHREC-Liste"])
        for z in zeilen:
            w.writerow([z["name"], rollen_txt(z["rollen"]), int(z["instant"]), z["mv"],
                        z["typ"], "" if z["synergy"] is None else round(z["synergy"], 3),
                        "" if z["inclusion"] is None else round(z["inclusion"], 3),
                        "" if z["lift"] is None else round(z["lift"], 2), z["frei"], z["besitz"],
                        z["in_decks"], z["eur"], z["gc"], z["quelle"], z["liste"] or ""])
    print(f"Commander: {cmd['name']} ({M.farbname(cmd['ci'])}) | EDHREC-Daten: {pfad or 'keine'} | "
          f"{len(zeilen)} Kandidaten -> {out}")
    # Rollenübersicht
    print("\nRollen: freie Kandidaten in der Sammlung vs. Kandidaten gesamt (EDHREC + Sammlung):")
    zus, ampel_fehler, ampel_gelb = [], [], []
    land_frei = sum(1 for z in zeilen if "land" in z["rollen"] and z["frei"] > 0)
    basics = basics_verfuegbar(con, ci)
    for k, n, mn, ziel, quelle in ROLLEN:
        frei = sum(1 for z in zeilen if k in z["rollen"] and z["frei"] > 0)
        ges = sum(1 for z in zeilen if k in z["rollen"])
        verfuegbar = frei + (sum(basics.values()) if k == "land" else 0)
        status = ""
        if mn:
            status = "ok" if verfuegbar >= mn else "knapp" if verfuegbar >= mn * 0.5 else "FEHLT"
            if k in ("land", "ramp", "ka", "gezielt", "massen"):
                if verfuegbar < mn * 0.5:
                    ampel_fehler.append(n)
                elif verfuegbar < mn:
                    ampel_gelb.append(n)
        extra = f" (+ {sum(basics.values())} freie Standardländer)" if k == "land" else ""
        zus.append((n, f"{frei}{extra}", ges, f"{mn}–{ziel}" if mn else "–", status))
    M.table(zus, ["Rolle", "frei", "gesamt", "Richtwert", "Weg 1"])
    inst = sum(1 for z in zeilen if "gezielt" in z["rollen"] and z["instant"] and z["frei"] > 0)
    plan = [z for z in zeilen if z["frei"] > 0 and (z["synergy"] or 0) >= 0.10]
    print(f"\nFreie Instant-Interaktion: {inst} | freie Plan-Karten (EDHREC-Synergie ≥ 10 %): {len(plan)}")
    print(f"Freie Standardländer in den Farben: {basics}")
    gcs = [z for z in zeilen if z["gc"]]
    if gcs:
        print("Game Changer im Pool: " + ", ".join(f"{z['name']} ({'frei' if z['frei'] else str(z['eur']) + ' €'})"
                                                   for z in gcs[:10]))
    if a.weg == 1:
        if ampel_fehler or len(plan) < 12:
            ampel = "ROT – mit freien Karten nicht sinnvoll baubar"
        elif ampel_gelb or len(plan) < 25:
            ampel = "GELB – baubar mit Abstrichen"
        else:
            ampel = "GRÜN – gut baubar"
        print(f"\nMachbarkeit Weg 1 (Einschätzung des Tools): {ampel}")
        if ampel_fehler:
            print("  zu wenig: " + ", ".join(ampel_fehler))
        if ampel_gelb:
            print("  knapp: " + ", ".join(ampel_gelb))
        if len(plan) < 25:
            print(f"  wenig commander-spezifische Karten frei ({len(plan)})")
    print("\nBeste Kandidaten je Rolle (frei zuerst):")
    for k, n, *_ in ROLLEN[1:6]:
        sel = [z for z in zeilen if k in z["rollen"]]
        sel.sort(key=lambda z: (-(z["frei"] > 0), -(z["inclusion"] or 0), z["rank"] or 999999))
        print(f"  {n}: " + "; ".join(f"{z['name']}{' (frei)' if z['frei'] else ' – ' + str(z['eur']) + ' €'}"
                                    for z in sel[:8]))
    if a.weg == 2:
        kauf = [z for z in zeilen if not z["frei"] and z["quelle"] == "EDHREC"]
        kauf.sort(key=lambda z: (-(z["synergy"] or 0) - (z["inclusion"] or 0)))
        print("\nKaufkandidaten Weg 2 (nicht frei, nach Synergie + Inclusion; Einordnung A–D durch Claude):")
        M.table([(z["name"], rollen_txt(z["rollen"]), f"{(z['synergy'] or 0) * 100:+.0f}%", pct(z["inclusion"]),
                  z["eur"], "ja" if z["gc"] else "", "in anderem Deck" if z["besitz"] else "")
                 for z in kauf[:25]], ["Karte", "Rolle", "Synergie", "Inclusion", "ab €", "GC", "Besitz"])
    sel = [z for z in zeilen if not set(z["rollen"]) & {"land"} and (z["synergy"] or 0) >= 0.15]
    sel.sort(key=lambda z: (-(z["synergy"] or 0)))
    print("  Plan/Synergie: " + "; ".join(f"{z['name']}{' (frei)' if z['frei'] else ' – ' + str(z['eur']) + ' €'}"
                                          for z in sel[:12]))


# ----------------------------------------------------------------- pruefen
PIP = re.compile(r"\{([^}]+)\}")


def pips(mana_cost):
    out = Counter()
    for sym in PIP.findall((mana_cost or "").split(" // ")[0]):
        for ch in "WUBRG":
            if ch in sym:
                out[ch] += 1
    return out


def quellen(c):
    """Farben, die ein Land liefert (inkl. Fetch/Such-Ländern über den Oracle-Text)."""
    prod = set(c["produced"] or "")
    if prod:
        return prod & set("WUBRG")
    t = c["text"] or ""
    if "search your library for" in t.lower():
        s = set()
        for typ, f in (("Plains", "W"), ("Island", "U"), ("Swamp", "B"), ("Mountain", "R"), ("Forest", "G")):
            if typ in t:
                s.add(f)
        return s or set("WUBRG") if "basic land" in t.lower() else s
    return set()


def auto_ersetzt(con, a):
    """--ersetzt oder: Deck der Datenbank mit gleichem Dateinamen (Soll-Stand wird geprüft)."""
    if a.ersetzt:
        return M.find_deck(con, a.ersetzt)
    r = con.execute("SELECT deck_id, kurz FROM decks WHERE datei=?", (os.path.basename(a.deck),)).fetchone()
    if r:
        print(f"(Soll-Stand von „{r[1]}“ erkannt – seine Karten zählen als vorhanden; sonst --ersetzt angeben)")
        return r[0]
    return None


# ----------------------------------------------------------------- Bracket-Zeile (pruefen, fazit)
def bracket_zeile(con, cmdr, main, bracket=3):
    """Game Changer, MLD, Extra Turns, 2-Karten-Combos (Commander Spellbook) -> Bracket-Zeile und Einzelteile."""
    alle = cmdr + main
    gc = [c["name"] for _, c in alle if c["gc"]]
    oids = [c["oid"] for _, c in alle]
    q = ",".join("?" * len(oids))
    mld = [r[0] for r in con.execute(f"SELECT DISTINCT c.name FROM tags t JOIN cards c USING(oracle_id) WHERE"
                                     f" t.tag='mass-land-denial' AND t.oracle_id IN ({q})", oids)]
    xt = [r[0] for r in con.execute(f"SELECT DISTINCT c.name FROM tags t JOIN cards c USING(oracle_id) WHERE"
                                    f" t.tag='extra-turn' AND t.oracle_id IN ({q})", oids)]
    combos_txt, zwei = [], []
    body = {"main": [{"card": M.front(c["name"]), "quantity": q_} for q_, c in main],
            "commanders": [{"card": M.front(c["name"]), "quantity": 1} for _, c in cmdr]}
    try:
        res = M.get_json("https://backend.commanderspellbook.com/estimate-bracket", body)
        for v in res.get("combos", []):
            cb = v["combo"]
            karten = [u["card"]["name"] for u in cb.get("uses", [])]
            art = "2 Karten" if v.get("definitelyTwoCard") else "2 Karten (strittig)" if v.get("arguablyTwoCard") else f"{len(karten)} Karten"
            if v.get("definitelyTwoCard") or v.get("arguablyTwoCard"):
                zwei.append(" + ".join(karten))
            combos_txt.append(f"{art}: {' + '.join(karten)} (Spellbook-Tag {cb.get('bracketTag')}, speed {v.get('speed')})")
        sb_tag = res.get("bracketTag")
    except Exception as e:
        sb_tag = f"nicht erreichbar ({e})"
    limit = GC_LIMIT.get(bracket, 3)
    gc_txt = f"{len(gc)}/{limit if limit < 99 else '∞'} Game Changer" + (f" ({', '.join(gc)})" if gc else "")
    zeile = (f"Bracket {bracket} – {gc_txt} – {'MLD: ' + ', '.join(mld) if mld else 'keine MLD'} – "
             f"{'Extra Turns: ' + ', '.join(xt) if xt else 'keine Extra Turns'} – "
             f"{'2-Karten-Combos: ' + '; '.join(zwei) if zwei else 'kein 2-Karten-Combo'}")
    return {"gc": gc, "mld": mld, "xt": xt, "zwei": zwei, "combos": combos_txt, "sb_tag": sb_tag, "limit": limit,
            "zeile": zeile, "body": body}


def cmd_pruefen(con, a):
    cmdr, main, unbekannt, hinweis = lies_deck(con, a.deck)
    ersetzt = auto_ersetzt(con, a)
    bracket = a.bracket
    warn = []
    if hinweis:
        warn.append(hinweis)
    if unbekannt:
        warn.append("nicht erkannte Karten: " + ", ".join(unbekannt))
    if not cmdr:
        print("Kein Commander erkannt – Commander nach einer Leerzeile ans Ende setzen.")
        return
    ci = set("".join(c["ci"] for _, c in cmdr))
    alle = cmdr + main
    total = sum(q for q, _ in alle)
    print(f"Deck: {a.deck} | Commander: {' + '.join(c['name'] for _, c in cmdr)} ({M.farbname(''.join(sorted(ci)))})"
          f" | {total} Karten")
    if total != 100:
        warn.append(f"{total} statt 100 Karten")
    dup = [c["name"] for q, c in alle if q > 1 and not basic(c) and "any number of cards named" not in (c["text"] or "")]
    if dup:
        warn.append("mehrfach (Singleton!): " + ", ".join(dup))
    aus = [c["name"] for _, c in alle if not set(c["ci"]) <= ci]
    if aus:
        warn.append("außerhalb der Farbidentität: " + ", ".join(aus))
    ban = [c["name"] for _, c in alle if c["legal"] == "banned"]
    if ban:
        warn.append("gebannt: " + ", ".join(ban))
    # Rollen
    zaehl = Counter()
    instant_int = 0
    rolle_je = {}
    for q, c in main:
        r = rollen(con, c)
        rolle_je[c["name"]] = r
        for x in r:
            zaehl[x] += q
        if "gezielt" in r and ist_instant(c):
            instant_int += q
    print("\nRollen gegen Template (Karten mit Doppelrolle zählen mehrfach):")
    rows = []
    for k, n, mn, ziel, quelle in ROLLEN:
        ist = zaehl[k]
        status = "–" if mn is None else ("ok" if ist >= mn else "ZU WENIG")
        if k == "land" and ist > 40:
            status = "VIELE"
        rows.append((n, ist, f"{mn}–{ziel}" if mn else "–", status, quelle))
        if mn and ist < mn:
            warn.append(f"{n}: {ist} (Minimum {mn}, Ziel {ziel})")
    rows.append(("davon Instant-Interaktion", instant_int, "≥ 4", "ok" if instant_int >= 4 else "WENIG",
                 "Einschätzung"))
    if instant_int < 4:
        warn.append(f"nur {instant_int} Interaktion mit Instant-Tempo")
    M.table(rows, ["Rolle", "Anzahl", "Richtwert", "Status", "Richtwert-Quelle"])
    # Kurve
    spells = [(q, c) for q, c in cmdr + main if "Land" not in front_type(c)]   # Nichtländer inkl. Commander
    kurve = Counter()
    for q, c in spells:
        kurve[min(int(c["cmc"] or 0), 7)] += q
    n_sp = sum(q for q, _ in spells)
    avg = sum((c["cmc"] or 0) * q for q, c in spells) / n_sp if n_sp else 0
    print("\nKurve (Nichtländer inkl. Commander): " + " | ".join(f"{'7+' if k == 7 else k}: {kurve[k]}" for k in range(8))
          + f" | Ø MV {avg:.2f}")
    if avg > 3.5:
        warn.append(f"hohe Kurve (Ø {avg:.2f}) – mehr Ramp/Länder oder günstigere Karten")
    # Farben
    pip = Counter()
    schwer = []
    for q, c in spells:
        p = pips(c["mana_cost"])
        pip.update({k: v * q for k, v in p.items()})
        for f, n in p.items():
            if n >= 2 and (c["cmc"] or 0) <= 3:
                schwer.append(f"{c['name']} ({f}{f})")
    src = Counter()
    for q, c in main:
        if "Land" in front_type(c):
            for f in quellen(c):
                src[f] += q
    gesamt_pips = sum(pip[f] for f in ci) or 1
    print("\nFarben (Richtwert laut Framework: ≈ 20 Quellen für Hauptfarben, ≈ 14 für Splash < 12 % der Pips):")
    rows = []
    for f in "WUBRG":
        if f not in ci:
            continue
        anteil = pip[f] / gesamt_pips
        ziel = 14 if anteil < 0.12 else 20
        rows.append((M.FARBE_DE[f], pip[f], f"{anteil * 100:.0f}%", src[f], ziel, "ok" if src[f] >= ziel else "WENIG"))
        if src[f] < ziel:
            warn.append(f"nur {src[f]} Landquellen für {M.FARBE_DE[f]} (Richtwert {ziel})")
    M.table(rows, ["Farbe", "Pips", "Anteil", "Landquellen", "Richtwert", "Status"])
    if schwer:
        print("Doppel-Pips bis MV 3 (brauchen mehr Quellen): " + ", ".join(schwer))
    # Bracket
    bz = bracket_zeile(con, cmdr, main, bracket)
    gc, mld, xt, zwei, limit, zeile, sb_tag = bz["gc"], bz["mld"], bz["xt"], bz["zwei"], bz["limit"], bz["zeile"], bz["sb_tag"]
    body = bz["body"]
    print(f"\nBracket-Zeile: {zeile}")
    print(f"Commander Spellbook Einstufung: {sb_tag} ({ {"R": "Ruthless", "S": "Spicy", "P": "Powerful", "O": "Oddball", "C": "Core", "E": "Exhibition", "B": "Banned"}.get(sb_tag, "?")})")
    for t in bz["combos"]:
        print("  Combo " + t)
    if len(gc) > limit:
        warn.append(f"{len(gc)} Game Changer – erlaubt in Bracket {bracket}: {limit}")
    if bracket <= 3 and (mld or xt):
        warn.append("MLD/Extra Turns in Bracket ≤ 3 prüfen")
    if bracket <= 3 and zwei:
        warn.append("2-Karten-Combo vorhanden – in Bracket 3 nur, wenn nicht früh im Spiel möglich (Einschätzung nötig)")
    if a.combos_fehlend:
        try:
            r = M.get_json("https://backend.commanderspellbook.com/find-my-combos", body)
            fast = (r.get("results", r) or {}).get("almostIncluded", [])
            print(f"\nCombos, denen genau 1 Karte fehlt: {len(fast)} (Auszug)")
            namen = {M.front(c["name"]) for _, c in alle}
            for v in fast[:15]:
                k = [u["card"]["name"] for u in v["uses"]]
                fehlt = [x for x in k if M.front(x) not in namen]
                print(f"  fehlt {', '.join(fehlt)} | {' + '.join(k)} | Tag {v.get('bracketTag')}")
        except Exception as e:
            print("find-my-combos nicht erreichbar:", e)
    # Besitz
    kauf, frei_n = [], 0
    for q_, c in alle:
        if basic(c):
            continue
        b, d, f = besitz(con, c["oid"], ersetzt)
        if f >= q_:
            frei_n += q_
        else:
            kauf.append((c["name"], q_ - f, c["eur"], "alle Exemplare in anderen Decks" if b > 0 else "nicht im Besitz"))
    summe = sum((e or 0) * n for _, n, e, _ in kauf)
    print(f"\nBesitz: {frei_n} Karten frei in der Sammlung | zu kaufen/tauschen: {sum(n for _, n, _, _ in kauf)}"
          f" | Summe ab {summe:.2f} € (Scryfall-EUR, günstigster Druck, {time.strftime('%d.%m.%Y')})")
    if kauf:
        M.table(sorted(kauf, key=lambda k: -(k[2] or 0)), ["Karte", "Anzahl", "ab €", "Grund"])
        print("\nKaufliste (zum Einfügen in Moxfield):")
        print("\n".join(f"{n} {k}" for k, n, _, _ in sorted(kauf)))
    # Standardländer
    plan = {}
    for q_, c in main:
        if basic(c):
            plan[c["name"]] = plan.get(c["name"], 0) + q_
    print()
    if plan:
        M.laender_tabelle(con, ersetzt, plan)
    # Warnungen
    print("\nWARNUNGEN / WAS NOCH FEHLT:" if warn else "\nKeine Warnungen.")
    for w in warn:
        print(f"  - {w}")


# ----------------------------------------------------------------- erklaerung
def cmd_erklaerung(con, a):
    cmdr, main, unbekannt, _ = lies_deck(con, a.deck)
    if not cmdr:
        sys.exit("Kein Commander erkannt")
    cname = " + ".join(c["name"] for _, c in cmdr)
    data, pfad = edhrec_commander(cname, a.bracket)
    edh = edh_karten(data) if data else {}
    combo_teil = {}
    try:
        body = {"main": [{"card": M.front(c["name"]), "quantity": q} for q, c in main],
                "commanders": [{"card": M.front(c["name"]), "quantity": 1} for _, c in cmdr]}
        res = M.get_json("https://backend.commanderspellbook.com/find-my-combos", body)
        for v in (res.get("results", res) or {}).get("included", []):
            karten = [u["card"]["name"] for u in v["uses"]]
            for k in karten:
                combo_teil.setdefault(M.front(k), []).append(" + ".join(karten))
    except Exception:
        pass
    ersetzt = auto_ersetzt(con, a)
    out = a.out or "erklaerung.csv"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"# Datenbasis für Kartenerklärungen – {cname} – EDHREC {pfad or '–'} – {time.strftime('%Y-%m-%d')}"])
        w.writerow(["Karte", "Rollen", "MV", "Typ", "Stärke", "Instant", "Synergie", "Inclusion", "Combo-Teil",
                    "Game Changer", "Status", "ab EUR", "Oracle-Text"])
        for q, c in [(q, c) for q, c in cmdr] + sorted(main, key=lambda x: x[1]["name"]):
            if basic(c):
                continue
            v = edh.get(c["name"]) or edh.get(M.front(c["name"])) or {}
            b, d, f = besitz(con, c["oid"], ersetzt)
            status = "frei" if f >= q else ("in anderem Deck" if b else "kaufen")
            w.writerow([c["name"], rollen_txt(rollen(con, c)), c["cmc"], front_type(c), c["pt"] or "",
                        int(ist_instant(c)), "" if v.get("synergy") is None else f"{v['synergy'] * 100:+.0f}%",
                        pct(v.get("inclusion")), " | ".join(combo_teil.get(M.front(c["name"]), [])),
                        c["gc"], status, c["eur"], re.sub(r"\s+", " ", c["text"] or "")])
    print(f"Datenbasis für {len(main) + len(cmdr)} Einträge -> {out} (Standardländer ausgelassen)")


# ----------------------------------------------------------------- alternativen
def cmd_alternativen(con, a):
    c = finde(con, a.karte)
    r = [x for x in rollen(con, c) if x not in ("tutor", "rekursion")] or rollen(con, c)
    farben = set((a.farben or c["ci"]).upper())
    print(f"{c['name']}: Rollen {', '.join(ROLLE_NAME[x] for x in r) or '–'} | MV {c['cmc']} | ab {c['eur']} €")
    if not r:
        print("Keine Funktionsrolle erkannt – Alternativen über Synergie/Thema suchen (kandidaten).")
        return
    kand = []
    for (oid,) in con.execute("SELECT oracle_id FROM cards WHERE legal_commander='legal' AND cmc <= ?",
                              ((c["cmc"] or 0) + 1,)):
        if oid == c["oid"]:
            continue
        x = card(con, oid)
        if not set(x["ci"]) <= farben or "Land" in front_type(x):
            continue
        rr = rollen(con, x)
        if not set(r) & set(rr):
            continue
        b, d, f = besitz(con, oid)
        if not f and c["eur"] is not None and (x["eur"] is None or x["eur"] >= c["eur"]):
            continue
        kand.append((x["name"], rollen_txt(rr), x["cmc"], x["eur"], f, x["rank"]))
    kand.sort(key=lambda k: (-(k[4] > 0), k[5] or 999999))
    M.table(kand[:a.limit], ["Alternative", "Rollen", "MV", "ab €", "frei", "EDHREC-Rang"])


# ----------------------------------------------------------------- oracle
def oracle_block(con, c, rulings=False):
    txt = (c["text"] or "").replace("\n", "\n    ")
    zeilen = [f"{c['name']}  {c['mana_cost'] or ''}  · {c['type_line']}" + (f"  · {c['pt']}" if c["pt"] else "")
              + ("  · GAME CHANGER" if c["gc"] else ""), f"    {txt}"]
    if rulings:
        for d, t in con.execute("SELECT published_at, comment FROM rulings WHERE oracle_id=? ORDER BY published_at",
                                (c["oid"],)):
            zeilen.append(f"    Ruling {d}: {t}")
    return "\n".join(zeilen)


def cmd_oracle(con, a):
    if a.alt and a.neu:
        _, alt, _, _ = lies_deck(con, a.alt)
        _, neu, _, _ = lies_deck(con, a.neu)
        a_oid, n_oid = {c["oid"] for _, c in alt}, {c["oid"] for _, c in neu}
        rein = sorted((c for _, c in neu if c["oid"] not in a_oid), key=lambda c: c["name"])
        raus = sorted((c for _, c in alt if c["oid"] not in n_oid), key=lambda c: c["name"])
        print(f"NEU IM DECK ({len(rein)}) – Beschreibung im Vorschlag nur aus diesem Text:\n")
        print("\n\n".join(oracle_block(con, c, a.rulings) for c in rein))
        print(f"\n\nRAUS ({len(raus)}):\n")
        print("\n\n".join(oracle_block(con, c) for c in raus))
        return
    if not a.karten:
        sys.exit("Karten nennen oder --alt/--neu angeben")
    print("\n\n".join(oracle_block(con, finde(con, n), a.rulings) for n in a.karten))


# ----------------------------------------------------------------- upgrade
def wert(v, c):
    """Stärke einer Karte für diesen Commander: EDHREC-Inclusion + 1,5 × Synergie (Bracket-Seite).
    Ohne EDHREC-Eintrag nur ein kleiner Wert nach EDHREC-Rang (Karte dann am Oracle-Text prüfen)."""
    if v and v.get("inclusion") is not None:
        syn = v.get("synergy") or 0
        return round((v["inclusion"] or 0) + 1.5 * syn, 3)
    r = c.get("rank") or 999999
    return 0.06 if r <= 1500 else 0.03 if r <= 5000 else 0.0


def deck_aus_ref(con, ref):
    """Deckdatei oder Deckname -> (Pfad, deck_id)."""
    if os.path.exists(ref):
        r = con.execute("SELECT deck_id FROM decks WHERE datei=?", (os.path.basename(ref),)).fetchone()
        return ref, (r[0] if r else None)
    did = M.find_deck(con, ref)
    datei = con.execute("SELECT datei FROM decks WHERE deck_id=?", (did,)).fetchone()[0]
    for kand in (datei, os.path.join("decks", datei)):
        if os.path.exists(kand):
            return kand, did
    sys.exit(f"Deckdatei {datei} nicht gefunden (im Ordner decks/ erwartet)")


def cmd_upgrade(con, a):
    pfad, did = deck_aus_ref(con, a.deck)
    cmdr, main, unbekannt, _ = lies_deck(con, pfad)
    if not cmdr:
        sys.exit("Kein Commander erkannt")
    cname = " + ".join(c["name"] for _, c in cmdr)
    ci = set("".join(c["ci"] for _, c in cmdr))
    data, epfad = edhrec_commander(cname, a.bracket)
    edh = edh_karten(data) if data else {}
    them = edh_karten(edhrec_commander(cname, a.bracket, a.thema)[0] or {"container": {"json_dict": {}}}) \
        if a.thema else {}
    im_deck = {c["oid"] for _, c in cmdr + main}
    zaehl = Counter()
    deck = []
    for q, c in main:
        r = rollen(con, c)
        for x in r:
            zaehl[x] += q
        v = edh.get(c["name"]) or edh.get(M.front(c["name"])) or {}
        deck.append({"c": c, "q": q, "rollen": r, "v": v, "wert": 0.0 if basic(c) else wert(v, c)})
    soll = {k: (mn, ziel) for k, _, mn, ziel, _ in ROLLEN if mn}
    print(f"Upgrade {os.path.basename(pfad)} | {cname} | Bracket {a.bracket} | Stufe {a.stufe}"
          + (f" (Käufe bis {a.max_preis:g} €)" if a.stufe else " (nur freie Karten)")
          + f" | EDHREC: {epfad or 'keine Daten'}" + (f" | Thema: {a.thema}" if a.thema else ""))
    print("\nRollenbilanz (99 ohne Commander):")
    M.table([(n, zaehl[k], f"{mn}–{ziel}" if mn else "–",
              "–" if not mn else "UNTER MINIMUM" if zaehl[k] < mn else
              "über Richtwert" if zaehl[k] > ziel else "ok") for k, n, mn, ziel, _ in ROLLEN],
            ["Rolle", "ist", "Richtwert", "Status"])
    gc_deck = [c["name"] for _, c in cmdr + main if c["gc"]]
    # Kandidaten
    pool = {}
    for (oid,) in con.execute("SELECT oracle_id FROM v_karten WHERE frei > 0"):
        pool[oid] = "Sammlung"
    if a.stufe:
        for n in list(edh) + list(them):
            oid = M.resolve_name(con, n)
            if oid and oid not in pool:
                pool[oid] = "EDHREC"
    kand = []
    for oid, quelle in pool.items():
        if oid in im_deck:
            continue
        c = card(con, oid)
        if not c or c["legal"] != "legal" or not set(c["ci"]) <= ci or basic(c):
            continue
        b, d, f = besitz(con, oid, did)
        if not f and (not a.stufe or c["eur"] is None or c["eur"] > a.max_preis):
            continue
        v = edh.get(c["name"]) or edh.get(M.front(c["name"])) or {}
        tv = them.get(c["name"]) or them.get(M.front(c["name"])) or {}
        kand.append({"c": c, "rollen": rollen(con, c), "v": v, "tv": tv, "wert": wert(v, c), "frei": f,
                     "status": "frei" if f else f"{c['eur']:.2f} €"})
    kand.sort(key=lambda k: -k["wert"])
    land = lambda c: "Land" in front_type(c)
    zp, beim_deck = M.deck_zeitstempel(con, did) if did else (None, None)
    beim_deck = {r[3] for r in beim_deck or []}
    for k in kand:
        if k["c"]["oid"] in beim_deck:
            k["status"] += " ⚑"
    # schwächste Deckkarten
    schwach = sorted((x for x in deck if not basic(x["c"])), key=lambda x: x["wert"])
    print("\nSchwächste Deckkarten (Wert = Inclusion + 1,5 × Synergie, EDHREC-Bracket-Seite):")
    M.table([(x["c"]["name"], rollen_txt(x["rollen"]), pct(x["v"].get("inclusion")),
              "" if x["v"].get("synergy") is None else f"{x['v']['synergy'] * 100:+.0f}%", f"{x['wert']:.2f}",
              "ohne EDHREC-Wert" if not x["v"] else "") for x in schwach[:a.paare]],
            ["Karte", "Rollen", "Inclusion", "Synergie", "Wert", "Hinweis"])
    print("\nBeste Kandidaten je Rolle (" + ("frei" if not a.stufe else "frei oder Kauf") + "):")
    for k, n, *_ in ROLLEN[1:6] + [("plan", "Plan/Synergie", None, None, None)]:
        sel = [x for x in kand if (k in x["rollen"]) or (k == "plan" and not x["rollen"])]
        if sel:
            print(f"  {n}: " + "; ".join(f"{x['c']['name']} ({x['wert']:.2f}, {x['status']})" for x in sel[:6]))
    # Tauschpaare
    paare, raus_ok, rein_ok = [], set(), set()
    ist = Counter(zaehl)

    def raus_moeglich(x, rein):
        for r in x["rollen"]:
            if r in soll and r not in rein["rollen"] and ist[r] - 1 < soll[r][0]:
                return False
        return True

    def tausch(x, k, grund):
        paare.append((x, k, grund))
        raus_ok.add(x["c"]["oid"]); rein_ok.add(k["c"]["oid"])
        for r in x["rollen"]:
            ist[r] -= 1
        for r in k["rollen"]:
            ist[r] += 1
    for r, (mn, ziel) in sorted(soll.items(), key=lambda kv: ist[kv[0]] - kv[1][0]):
        if r == "land":
            continue
        for k in [k for k in kand if r in k["rollen"] and not land(k["c"])]:
            if ist[r] >= mn or len(paare) >= a.paare:
                break
            x = next((x for x in schwach if x["c"]["oid"] not in raus_ok and not land(x["c"])
                      and raus_moeglich(x, k)), None)
            if x and k["c"]["oid"] not in rein_ok:
                tausch(x, k, f"{ROLLE_NAME[r]} unter Minimum")
    for k in kand:
        if len(paare) >= a.paare or k["c"]["oid"] in rein_ok:
            continue
        x = next((x for x in schwach if x["c"]["oid"] not in raus_ok and land(x["c"]) == land(k["c"])
                  and raus_moeglich(x, k)), None)
        if land(k["c"]) and not k["v"]:
            continue                                # Länder nur mit EDHREC-Wert tauschen
        if x and k["wert"] - x["wert"] >= a.abstand:
            tausch(x, k, "stärker laut EDHREC" if k["v"] else "Oracle prüfen (ohne EDHREC-Wert)")
    print(f"\nTauschpaare – Startpunkt, Claude prüft jedes Paar am Oracle-Text und am Spielplan ({len(paare)}):")
    M.table([(i + 1, x["c"]["name"], f"{x['wert']:.2f}", k["c"]["name"], f"{k['wert']:.2f}",
              f"{k['wert'] - x['wert']:+.2f}", k["status"], grund) for i, (x, k, grund) in enumerate(paare)],
            ["#", "raus", "Wert", "rein", "Wert", "Δ", "Status", "Grund"])
    ckurz = kurzname(cname)
    print("\nWarum raus / warum rein (Datenbasis – im Vorschlag und im Fazit in einen Satz aus dem Oracle-Text fassen):")
    for i, (x, k, _) in enumerate(paare):
        print(f"  {i + 1}. raus {x['c']['name']}: {grund_raus(x['c'], x['v'], x['rollen'], zaehl, ckurz)}")
        print(f"     rein {k['c']['name']}: {grund_rein(k['c'], k['v'], k['rollen'], zaehl, ist, ckurz, k['tv'])}")
    pfad_paare = os.path.splitext(a.out or "upgrade.csv")[0] + "_paare.txt"
    os.makedirs(os.path.dirname(pfad_paare) or ".", exist_ok=True)   # --out in einem neuen Ordner (z. B. out/)
    with open(pfad_paare, "w", encoding="utf-8") as fh:
        fh.write("# Tauschpaare „Raus -> Rein“ (eine Seite darf leer sein) – für deckbau.py fazit --paare\n")
        fh.writelines(f"{x['c']['name']} -> {k['c']['name']}\n" for x, k, _ in paare)
    if beim_deck:
        print(f"⚑ = frei, aber zusammen mit diesem Deck erfasst ({zp[:16]}): liegt vielleicht schon beim Deck "
              f"(Maybeboard oder fehlende Deckkarte) – vor dem Vorschlag mit dem Nutzer klären "
              f"(mtg_db.py exemplare <deck>).")
    gc_neu = [k["c"]["name"] for _, k, _ in paare if k["c"]["gc"]]
    gc_frei = [k["c"]["name"] for k in kand if k["c"]["gc"]][:8]
    limit = GC_LIMIT.get(a.bracket, 3)
    print(f"\nGame Changer: im Deck {len(gc_deck)}/{limit if limit < 99 else '∞'} ({', '.join(gc_deck) or '–'})"
          + (f" | durch die Paare +{len(gc_neu)} ({', '.join(gc_neu)})" if gc_neu else "")
          + (f" | verfügbar: {', '.join(gc_frei)}" if gc_frei else ""))
    if len(gc_deck) + len(gc_neu) > limit:
        print(f"  !! mehr als {limit} Game Changer – Paare anpassen")
    print("\nOracle-Text der vorgeschlagenen Karten (Pflicht: Beschreibung im Vorschlag nur hieraus):\n")
    print("\n\n".join(oracle_block(con, k["c"]) for _, k, _ in paare))
    print("\nOracle-Text der Karten, die raus sollen (auch die Raus-Begründung nur hieraus):\n")
    print("\n\n".join(oracle_block(con, x["c"]) for x, _, _ in paare))
    print(f"\nPaare -> {pfad_paare}")
    out = a.out or "upgrade.csv"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"# Upgrade {cname} – Stufe {a.stufe} – EDHREC {epfad or '–'} – {time.strftime('%Y-%m-%d')}"])
        w.writerow(["Art", "Karte", "Rollen", "Wert", "Inclusion", "Synergie", "Thema-Synergie", "Status", "MV", "Typ",
                    "Oracle-Text"])
        for x in schwach:
            w.writerow(["Deck", x["c"]["name"], rollen_txt(x["rollen"]), x["wert"], x["v"].get("inclusion"),
                        x["v"].get("synergy"), "", "im Deck", x["c"]["cmc"], front_type(x["c"]),
                        re.sub(r"\s+", " ", x["c"]["text"] or "")])
        for k in kand:
            w.writerow(["Kandidat", k["c"]["name"], rollen_txt(k["rollen"]), k["wert"], k["v"].get("inclusion"),
                        k["v"].get("synergy"), k["tv"].get("synergy"), k["status"], k["c"]["cmc"], front_type(k["c"]),
                        re.sub(r"\s+", " ", k["c"]["text"] or "")])
    print(f"\nAlle Deckkarten und {len(kand)} Kandidaten -> {out}")


# ----------------------------------------------------------------- Begründungen aus Daten (upgrade, fazit)
SOLL = {k: (mn, ziel) for k, _, mn, ziel, _ in ROLLEN if mn}
SPELLBOOK = {"R": "Ruthless", "S": "Spicy", "P": "Powerful", "O": "Oddball", "C": "Core", "E": "Exhibition", "B": "Banned"}


def kurzname(cname):
    """'Karametra, God of Harvests' -> 'Karametra' (für Sätze wie „in 27 % der Karametra-Decks“)."""
    return " + ".join(re.split(r",| of | the ", M.front(n))[0].strip() for n in cname.split(" + "))


def edh_txt(v, ckurz):
    if not v or v.get("inclusion") is None:
        return f"nicht auf der EDHREC-Seite von {ckurz}"
    syn = v.get("synergy")
    return (f"in {v['inclusion'] * 100:.0f} % der {ckurz}-Decks"
            + ("" if syn is None else f", Synergie {syn * 100:+.0f} %".replace("-", "−")))


def grund_raus(c, v, r, zaehl, ckurz):
    """Datenbasis für „warum raus“: EDHREC-Wert beim Commander, Rollen über Richtwert, keine Kernrolle."""
    teile = [edh_txt(v, ckurz)]
    for x in r:
        if x in SOLL and zaehl[x] > SOLL[x][1]:
            teile.append(f"{ROLLE_NAME[x]} über Richtwert ({zaehl[x]}/{SOLL[x][1]})")
    if not r:
        teile.append("keine Kernrolle (nur Plan/Synergie)")
    return "; ".join(teile)


def grund_rein(c, v, r, vorher, nachher, ckurz, tv=None):
    """Datenbasis für „warum rein“: EDHREC-Wert, gefüllte Rollen, Thema-Synergie."""
    teile = [edh_txt(v, ckurz)]
    if tv and tv.get("synergy") is not None:
        teile.append(f"Thema-Synergie {tv['synergy'] * 100:+.0f} %")
    for x in r:
        if x in SOLL and vorher[x] < SOLL[x][0]:
            teile.append(f"füllt {ROLLE_NAME[x]} ({vorher[x]} → {nachher[x]}, Minimum {SOLL[x][0]})")
    if c.get("gc"):
        teile.append("Game Changer")
    return "; ".join(teile)


# ----------------------------------------------------------------- passung
def lade_archetypen():
    import archetypen as A
    karten, namen, _ = A.lade_karten()
    richt = A.lade_richtwerte(os.path.join(os.path.dirname(os.path.abspath(__file__)), "archetypen_daten.json"))
    return A, karten, richt


def ziel_archetyp(A, thema, strategie):
    t = (thema or "").lower()
    if t:
        if t in A.ARCHETYPEN:
            return t
        for k, d in A.ARCHETYPEN.items():
            if t in d["edhrec"]:
                return k
    s = t or (strategie or "").lower()
    return next((v for k, v in A.STRATEGIE_ZU_ARCHETYP.items() if k in s), None)


def commander_passung(con, cname, spiel, bracket):
    """Wie gut passt ein Commander zu den Spielkarten (Nichtländer) eines Decks? Grundlage: EDHREC-Bracket-Seite.
    -> dict mit auf_seite, ohne_bezug, wert_je_karte, themen [(Name, Slug, Decks)], decks, pfad – oder None."""
    data, pfad = edhrec_commander(cname, bracket)
    if not data:
        return None
    edh = edh_karten(data)
    werte, auf, ohne = [], 0, []
    for q, c in spiel:
        v = edh.get(c["name"]) or edh.get(M.front(c["name"]))
        w = wert(v, c) if v else 0.0
        auf += 1 if v else 0
        if w <= 0:
            ohne.append(c["name"])
        werte.append(w * q)
    n = sum(q for q, _ in spiel) or 1
    jd = data["container"]["json_dict"]
    return {"auf_seite": auf, "n": n, "ohne_bezug": ohne, "wert": sum(werte) / n, "pfad": pfad,
            "decks": (jd.get("card") or {}).get("num_decks"),
            "themen": [(t["value"], t["slug"], t["count"]) for t in data.get("panels", {}).get("taglinks", [])]}


def vergleich(w, basis):
    """Ø Wert mit Faktor gegenüber dem aktuellen Commander, z. B. „0,65 (×9,4)“ oder „0,27 (−34 %)“."""
    if not basis:
        return f"{w:.2f}".replace(".", ",")
    f = w / basis
    rel = f"×{f:.1f}" if f >= 2 else f"{(f - 1) * 100:+.0f} %"
    return f"{w:.2f} ({rel.replace('-', '−')})".replace(".", ",")


def thema_beim_commander(themen, slugs):
    """-> (Rang, Name, Decks) des ersten passenden EDHREC-Themas oder None."""
    for i, (name, slug, n) in enumerate(themen):
        if slug in slugs:
            return i + 1, name, n
    return None


def cmd_passung(con, a):
    pfad, did = deck_aus_ref(con, a.deck)
    cmdr, main, unbekannt, _ = lies_deck(con, pfad)
    if not cmdr:
        sys.exit("Kein Commander erkannt")
    cname = " + ".join(c["name"] for _, c in cmdr)
    ckurz = kurzname(cname)
    strategie = None
    if did:
        r = con.execute("SELECT strategie, kurz FROM decks WHERE deck_id=?", (did,)).fetchone()
        strategie = r[0] if r else None
    A, karten, richt = lade_archetypen()
    ziel = ziel_archetyp(A, a.thema, strategie)
    spiel = [(q, c) for q, c in main if "Land" not in front_type(c)]
    deck_ci = set("".join(c["ci"] for _, c in main))
    print(f"Passung {os.path.basename(pfad)} | Commander {cname} | Ziel-Thema: "
          + (f"{A.ARCHETYPEN[ziel]['name']} ({'Vorgabe' if a.thema else 'aus Strategie „' + (strategie or '') + '“'})"
             if ziel else "keins angegeben (--thema)") + f" | Bracket {a.bracket}")
    if unbekannt:
        print("nicht erkannt: " + ", ".join(unbekannt))

    # 1. Was trägt das Deck?
    deck_z = Counter()
    for q, c in cmdr + main:
        deck_z[c["oid"]] += q
    c_oids = {c["oid"] for _, c in cmdr}
    z = A.zaehle_deck(deck_z, karten, c_oids)
    rang = sorted(A.ARCHETYPEN, key=lambda k: -A.deckung(z, richt, k))
    print("\n1) Was das Deck trägt (Kernpakete gegen den Median der EDHREC-Durchschnittsdecks, gedeckelt bei 100 %):")
    M.table([(A.ARCHETYPEN[k]["name"], f"{A.deckung(z, richt, k) * 100:.0f} %", "◆ Ziel" if k == ziel else "")
             for k in rang[:5] + ([ziel] if ziel and ziel not in rang[:5] else [])], ["Archetyp", "Deckung", ""])
    d_ziel = A.deckung(z, richt, ziel) if ziel else None
    if ziel:
        teile = []
        for key, label, _, kern in A.ARCHETYPEN[ziel]["pakete"]:
            m = (richt or {}).get("archetypen", {}).get(ziel, {}).get("pakete", {}).get(f"{ziel}.{key}")
            ist = z[f"{ziel}.{key}"]
            teile.append(f"{label}: {ist}" + (f" / {A.de(m['median'])}" + (" ⚠" if kern and ist < m["min"] else "")
                                               if m else ""))
        print(f"   Ziel {A.ARCHETYPEN[ziel]['name']}: " + " | ".join(teile))

    # 2. Was will der Commander?
    jetzt = commander_passung(con, cname, spiel, a.bracket)
    slugs = set(A.ARCHETYPEN[ziel]["edhrec"]) if ziel else set()
    print(f"\n2) Was {ckurz} laut EDHREC spielt" + (f" ({jetzt['pfad']}, {jetzt['decks']} Decks):" if jetzt else ": keine Daten"))
    th = None
    if jetzt:
        print("   Themen: " + " · ".join(f"{n} {d}" for n, _, d in jetzt["themen"][:8]))
        th = thema_beim_commander(jetzt["themen"], slugs) if slugs else None
        if ziel:
            print(f"   Ziel-Thema beim Commander: " + (f"Rang {th[0]} ({th[1]}, {th[2]} Decks)" if th else "nicht unter den Themen"))
        print(f"\n3) {ckurz} ↔ Deck: {jetzt['auf_seite']} von {jetzt['n']} Spielkarten (Nichtländer) stehen auf der "
              f"EDHREC-Seite · Ø Wert je Spielkarte {jetzt['wert']:.3f} · ohne Bezug (kein oder negativer Wert): "
              f"{len(jetzt['ohne_bezug'])}")
        if jetzt["ohne_bezug"]:
            print("   ohne Bezug: " + ", ".join(jetzt["ohne_bezug"][:25]) + (" …" if len(jetzt["ohne_bezug"]) > 25 else ""))

    # 4. Alternative Commander: im Deck, frei in der Sammlung, optional Kauf
    kand = {}
    for _, c in main:
        if M.is_commander_eligible(con, c["oid"]):
            kand[c["oid"]] = "im Deck"
    for (oid,) in con.execute("SELECT oracle_id FROM v_karten WHERE frei > 0"):
        if oid not in kand and M.is_commander_eligible(con, oid):
            kand[oid] = "frei"
    if a.kauf and ziel:
        farben = M.FARBNAMEN.get(frozenset(deck_ci), (None,))[0] if 2 <= len(deck_ci) <= 3 else \
            FARBSLUG.get(next(iter(deck_ci))) if len(deck_ci) == 1 else None
        for slug in A.ARCHETYPEN[ziel]["edhrec"][:1]:
            d = (edhrec(f"tags/{slug}/{farben.lower()}") if farben else None) or edhrec(f"tags/{slug}")
            listen = [cl for cl in (d or {}).get("container", {}).get("json_dict", {}).get("cardlists", [])
                      if "Commander" in cl.get("header", "")]
            for cl in sorted(listen, key=lambda cl: 0 if cl.get("header", "").startswith("Top") else 1):
                for cv in cl["cardviews"][:a.kauf * 3]:
                    oid = M.resolve_name(con, cv["name"])
                    if oid and oid not in kand and sum(1 for v in kand.values() if v == "Kauf") < a.kauf:
                        kand[oid] = "Kauf"
    zeilen, zu_eng = [], []
    for oid, herkunft in kand.items():
        c = card(con, oid)
        if not c or c["legal"] != "legal" or "Background" in (c["type_line"] or "") or oid in c_oids:
            continue
        illegal = [x["name"] for _, x in main if not set(x["ci"]) <= set(c["ci"])]
        if len(illegal) > a.max_illegal:
            zu_eng.append(f"{c['name']} ({c['ci'] or 'C'}, {len(illegal)} Karten außerhalb)")
            continue
        zeilen.append({"c": c, "herkunft": herkunft, "illegal": illegal})
    zeilen.sort(key=lambda x: ({"im Deck": 0, "frei": 1, "Kauf": 2}[x["herkunft"]], len(x["illegal"]),
                               x["c"]["rank"] or 999999))
    zeilen = ([x for x in zeilen if x["herkunft"] != "Kauf"][:a.kandidaten]
              + [x for x in zeilen if x["herkunft"] == "Kauf"][:a.kauf])   # Kauf-Kandidaten zusätzlich
    for x in zeilen:
        x["p"] = commander_passung(con, x["c"]["name"], [(q, c) for q, c in spiel if c["oid"] != x["c"]["oid"]],
                                   a.bracket)
    zeilen = [x for x in zeilen if x["p"]]
    zeilen.sort(key=lambda x: -x["p"]["wert"])
    basis = jetzt["wert"] if jetzt and jetzt["wert"] > 0 else None
    print(f"\n4) Alternative Commander aus Deck{', Sammlung und Kauf' if a.kauf else ' und Sammlung (frei)'} – "
          f"wie gut passen sie zu den vorhandenen Spielkarten? (Passung = Ø Wert je Spielkarte; {ckurz} jetzt: "
          f"{vergleich(jetzt['wert'], None)})" if jetzt else "\n4) Alternative Commander:")
    rows = []
    for x in zeilen:
        p = x["p"]
        tz = thema_beim_commander(p["themen"], slugs) if slugs else None
        rows.append((x["c"]["name"], x["herkunft"] + (f" {x['c']['eur']:.2f} €".replace(".", ",") if x["herkunft"] == "Kauf" and x["c"]["eur"] else ""),
                     x["c"]["ci"] or "C", len(x["illegal"]), f"{p['auf_seite']}/{p['n']}",
                     vergleich(p["wert"], basis),
                     (f"Rang {tz[0]}" if tz else "–") if ziel else "",
                     " · ".join(n for n, _, _ in p["themen"][:3])))
    M.table(rows, ["Kandidat", "Herkunft", "Farben", "nicht legal", "auf EDHREC-Seite", "Passung", "Ziel-Thema",
                   "Top-Themen"]) if rows else print("   keine Kandidaten (Farbidentität passt nicht oder keine EDHREC-Daten)")
    if zu_eng:
        print("   wegen Farbidentität weggelassen: " + "; ".join(zu_eng[:8]) + (" …" if len(zu_eng) > 8 else ""))

    # 5. Befund und Optionen – Daten für die Abwägung mit dem Nutzer (Entscheidung trifft der Nutzer)
    print("\n5) Befund (Daten-Hinweise, Abwägung im Gespräch):")
    befund = []
    bester = rang[0]
    if ziel and d_ziel is not None and d_ziel < 0.5 and bester != ziel and A.deckung(z, richt, bester) >= 0.7:
        befund.append(f"Das Deck trägt das Ziel-Thema kaum ({d_ziel * 100:.0f} %), wohl aber "
                      f"{A.ARCHETYPEN[bester]['name']} ({A.deckung(z, richt, bester) * 100:.0f} %).")
    elif ziel and d_ziel is not None and d_ziel < 0.8:
        befund.append(f"Ziel-Thema nur teilweise abgedeckt ({d_ziel * 100:.0f} %) – Pakete mit ⚠ auffüllen.")
    if jetzt and ziel and (not th or th[0] > 6):
        befund.append(f"{ckurz} wird auf EDHREC selten oder nie für das Ziel-Thema gespielt.")
    if jetzt and jetzt["ohne_bezug"] and len(jetzt["ohne_bezug"]) / jetzt["n"] >= 0.4:
        befund.append(f"{len(jetzt['ohne_bezug'])} von {jetzt['n']} Spielkarten haben keinen Bezug zu {ckurz}.")
    besser = [x for x in zeilen if basis and x["p"]["wert"] >= basis * 1.1]
    if besser:
        befund.append("Laut EDHREC-Daten passt das vorhandene Deck besser zu: "
                      + ", ".join(f"{x['c']['name']} ({vergleich(x['p']['wert'], basis)}, {x['herkunft']})" for x in besser[:3]) + ".")
    elif zeilen and basis:
        b = zeilen[0]
        befund.append(f"Kein Kandidat passt besser als {ckurz}; nächster: {b['c']['name']} "
                      f"({vergleich(b['p']['wert'], basis)}, {b['herkunft']}).")
    if slugs:
        spez = [(x, thema_beim_commander(x["p"]["themen"], slugs)) for x in zeilen]
        spez = [(x, t) for x, t in spez if t and t[0] <= 3]
        if spez:
            befund.append("Auf das Ziel-Thema spezialisiert (EDHREC-Thema unter den Top 3): "
                          + ", ".join(f"{x['c']['name']} (Rang {t[0]}, {x['herkunft']})" for x, t in spez[:4])
                          + " – Alternative, falls das Thema wichtiger ist als der Commander.")
    for b in befund or ["Commander, Deck und Ziel-Thema passen zusammen."]:
        print(f"   - {b}")
    print("\n   Optionen für die Abwägung (Claude empfiehlt, der Nutzer entscheidet):")
    if jetzt:
        luecke = 0
        if ziel and richt:
            for key, _, _, kern in A.ARCHETYPEN[ziel]["pakete"]:
                m = richt.get("archetypen", {}).get(ziel, {}).get("pakete", {}).get(f"{ziel}.{key}")
                if kern and m:
                    luecke += max(0, round(m["median"]) - z[f"{ziel}.{key}"])
        print(f"   A  {ckurz} behalten, Deck schärfen: ≈ {len(jetzt['ohne_bezug'])} Karten ohne Bezug"
              + (f", Kernpakete des Ziel-Themas ≈ {luecke} Karten unter Median" if ziel else ""))
    if besser:
        b = besser[0]
        print(f"   B  Commander wechseln zu {b['c']['name']} ({b['herkunft']}): {len(b['illegal'])} Karten außerhalb der "
              f"Farbidentität, {len(b['p']['ohne_bezug'])} ohne Bezug"
              + (f" – raus: {', '.join(b['illegal'][:6])}" if b["illegal"] else ""))
    elif zeilen:
        print(f"   B  Commander wechseln: laut Daten kein Gewinn (bester Kandidat {zeilen[0]['c']['name']}, "
              f"{vergleich(zeilen[0]['p']['wert'], basis)}) – nur, wenn der Nutzer einen anderen Spielstil will")
    d_best = A.deckung(z, richt, bester)
    if ziel and bester != ziel and jetzt and d_best >= max(0.6, (d_ziel or 0) + 0.15):
        tb = thema_beim_commander(jetzt["themen"], set(A.ARCHETYPEN[bester]["edhrec"]))
        print(f"   C  Thema an das Deck anpassen: {A.ARCHETYPEN[bester]['name']} "
              + (f"(bei {ckurz} EDHREC-Thema Rang {tb[0]}, {tb[2]} Decks)" if tb else f"(bei {ckurz} kein EDHREC-Thema)"))
    print("   D  Neubau mit anderem Commander: deckbau.py commander-suche --thema <slug> --farben <XY> --nur-besitz")


# ----------------------------------------------------------------- fazit (Entwurf des Fazit-PDF)
ROLLEN_FOLGE = ["ramp", "ka", "gezielt", "massen", "schutz", "tutor", "rekursion", None, "land"]


def haupt_rolle(r, c):
    if "Land" in front_type(c):
        return "land"
    return next((x for x in ROLLEN_FOLGE if x and x in r), None)


def rollen_name(k):
    return {None: "Plan/Synergie", "land": "Länder"}.get(k) or ROLLE_NAME[k]


def kennzahlen(con, cmdr, main):
    z = Counter()
    inst = 0
    for q, c in main:
        r = rollen(con, c)
        for x in r:
            z[x] += q
        if "gezielt" in r and ist_instant(c):
            inst += q
    sp = [(q, c) for q, c in cmdr + main if "Land" not in front_type(c)]
    n = sum(q for q, _ in sp)
    z["_mv"] = sum((c["cmc"] or 0) * q for q, c in sp) / n if n else 0
    z["_inst"] = inst
    z["_gc"] = sum(1 for _, c in cmdr + main if c["gc"])
    z["_wert"] = sum((c["eur"] or 0) * q for q, c in cmdr + main)
    return z


def lies_paare(con, pfad):
    """Datei mit Zeilen „Raus -> Rein“ (eine Seite darf leer sein) -> [(oid_raus|None, oid_rein|None)]."""
    out = []
    for z in open(pfad, encoding="utf-8"):
        z = z.split("#")[0].strip()
        if "->" not in z:
            continue
        l, r = (x.strip() for x in z.split("->", 1))
        out.append((M.resolve_name(con, l) if l else None, M.resolve_name(con, r) if r else None))
    return out


def paare_bilden(raus, rein, rollen_je, cards):
    """Automatisch: Land zu Land, gleiche Hauptrolle, dann ähnliche MV. -> [(oid_raus|None, oid_rein|None)]."""
    offen_r, paare = list(raus), []
    def punkte(o_r, o_n):
        cr, cn = cards[o_r], cards[o_n]
        lr, ln = "Land" in front_type(cr), "Land" in front_type(cn)
        if lr != ln:
            return -9
        p = 3 if haupt_rolle(rollen_je[o_r], cr) == haupt_rolle(rollen_je[o_n], cn) else 0
        p += len(set(rollen_je[o_r]) & set(rollen_je[o_n]))
        return p - abs((cr["cmc"] or 0) - (cn["cmc"] or 0)) / 4
    for o_n in sorted(rein, key=lambda o: -len(rollen_je[o])):
        if not offen_r:
            paare.append((None, o_n)); continue
        best = max(offen_r, key=lambda o_r: punkte(o_r, o_n))
        if punkte(best, o_n) <= -9:
            paare.append((None, o_n)); continue
        offen_r.remove(best)
        paare.append((best, o_n))
    paare += [(o, None) for o in offen_r]
    return paare


def einfuegeblock(pfad, cmdr_namen):
    """Entwurfsdatei -> Einfügeblock (alphabetisch, Commander nach Leerzeile am Ende), Drucke bleiben erhalten."""
    rx = re.compile(r"^\s*(\d+)x?\s+(.+?)(\s+[\(\[][A-Za-z0-9_]+[\)\]].*)?$")
    haupt, cm = [], []
    cn = {M.fold(M.front(n)) for n in cmdr_namen}
    for z in open(pfad, encoding="utf-8-sig"):
        z = z.strip()
        m = rx.match(z)
        if not m or z.startswith(("//", "#")):
            continue
        name = re.sub(r"\s+\*[A-Za-z]+\*$", "", m.group(2)).strip()
        (cm if M.fold(M.front(name)) in cn else haupt).append((M.fold(name), z))
    return "\n".join(z for _, z in sorted(haupt)) + "\n\n" + "\n".join(z for _, z in cm)


def cmd_fazit(con, a):
    cmdr, main, unbekannt, _ = lies_deck(con, a.neu)
    if not cmdr:
        sys.exit("Kein Commander im Entwurf erkannt")
    if unbekannt:
        print("nicht erkannt: " + ", ".join(unbekannt))
    cname = " + ".join(c["name"] for _, c in cmdr)
    ckurz = kurzname(cname)
    ci = "".join(x for x in "WUBRG" if x in set("".join(c["ci"] for _, c in cmdr)))
    data, epfad = edhrec_commander(cname, a.bracket)
    edh = edh_karten(data) if data else {}
    v_von = lambda c: edh.get(c["name"]) or edh.get(M.front(c["name"])) or {}
    did, cmdr_a, main_a = None, [], []
    if a.alt:
        pfad_a, did = deck_aus_ref(con, a.alt)
        cmdr_a, main_a, _, _ = lies_deck(con, pfad_a)
    upgrade = bool(a.alt)
    neu_z, alt_z, cards = Counter(), Counter(), {}
    for q, c in cmdr + main:
        neu_z[c["oid"]] += q; cards[c["oid"]] = c
    for q, c in cmdr_a + main_a:
        alt_z[c["oid"]] += q; cards[c["oid"]] = c
    rollen_je = {o: rollen(con, c) for o, c in cards.items()}
    k_alt = kennzahlen(con, cmdr_a, main_a) if upgrade else None
    k_neu = kennzahlen(con, cmdr, main)
    raus = [o for o in alt_z for _ in range(alt_z[o] - neu_z[o])] if upgrade else []   # Standardländer je Exemplar
    rein = [o for o in neu_z for _ in range(neu_z[o] - alt_z[o])] if upgrade else []
    paare = lies_paare(con, a.paare) if a.paare else paare_bilden(raus, rein, rollen_je, cards)
    for o in [o for o, _ in paare if o] + [o for _, o in paare if o]:
        if o not in cards:
            cards[o] = card(con, o); rollen_je[o] = rollen(con, cards[o])
    zp, beim_deck = M.deck_zeitstempel(con, did) if did else (None, None)
    beim_deck = {r[3] for r in beim_deck or []}

    def status(c):
        if basic(c):
            return "Standardland"
        b, d, f = besitz(con, c["oid"], did)
        if f > 0:
            return "frei" + (" ⚑" if c["oid"] in beim_deck else "")
        return "aus anderem Deck" if b > 0 else (f"Kauf ab {c['eur']:.2f} €".replace(".", ",") if c["eur"] else "Kauf")
    kauf = sum(cards[o]["eur"] or 0 for o in set(rein) if status(cards[o]).startswith("Kauf"))
    n_tausch = sum(1 for r_, n_ in paare if r_ and n_)
    n_plus, n_minus = sum(1 for r_, n_ in paare if n_ and not r_), sum(1 for r_, n_ in paare if r_ and not n_)
    bz = bracket_zeile(con, cmdr, main, a.bracket)
    # Kopf
    cfg_pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deck_namen.json")
    cfg = json.load(open(cfg_pfad, encoding="utf-8")).get(f"commander:{cname}", {}) if os.path.exists(cfg_pfad) else {}
    db_s, db_h = (con.execute("SELECT strategie, herkunft FROM decks WHERE deck_id=?", (did,)).fetchone()
                  if did else (None, None))
    deckname = a.deckname or cfg.get("name") or cfg.get("precon") or ckurz
    voll = " | ".join(["Commander", deckname, M.farbname_kurz(ci), cfg.get("strategie") or db_s or "‹Strategie›",
                       cfg.get("herkunft") or db_h or "Selfbuild"] + ([cfg["status"]] if cfg.get("status") else []))
    pset = con.execute("SELECT precon_set FROM decks WHERE deck_id=?", (did,)).fetchone()[0] if did else ""
    heute = time.strftime("%d.%m.%Y")
    art = f"Upgrade {a.stufe}" if upgrade else "Neues Deck"
    wert_txt = f"{k_neu['_wert']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    L = ["---", f"titel: {deckname}", f"oberzeile: {art} · freigegeben am {heute}",
         f"unterzeile: Fazit, Kartenerklärungen und Vorgehen · {cname} · Bracket {a.bracket}",
         f"zeile3: {voll}", f"kurz: {art}", f"farben: {ci}",
         f"fuss: Daten: Scryfall, EDHREC ({epfad or '–'}), Commander Spellbook · Stand {heute}",
         f"deckname: {deckname}", f"voll: {voll}", f"bracket_zeile: {bz['zeile']}",
         "beschreibung: ‹Moxfield-Beschreibung, höchstens 140 Zeichen›", "themen: ‹Moxfield-Themen aus der Liste›",
         "status: freigegeben – Aufbau offen", f"wert: {wert_txt} € (günstigste Drucke, {heute})",
         f"set: {pset or ''}", "---",
         "[kacheln]", f"Bracket {a.bracket} | {len(bz['gc'])}/{bz['limit'] if bz['limit'] < 99 else '∞'} Game Changer",
         (f"{n_tausch} Tausche" + (f" + {n_plus} neu" if n_plus else "") + (f" − {n_minus}" if n_minus else "")
          + f" | {a.stufe} · {kauf:.2f} €".replace(".", ",")
          if upgrade else f"{sum(neu_z.values())} Karten | {sum(1 for _, c in main if 'Land' in front_type(c))} Länder"),
         f"{wert_txt} € | Deckwert (günstigste Drucke)",
         f"{k_neu['_mv']:.2f}".replace(".", ",") + " | Ø MV (Nichtländer inkl. Commander)", "[/kacheln]", "",
         "## Fazit", "‹2–3 Sätze: Spielplan und was sich ändert›", "",
         f"> **Bracket-Zeile:** {bz['zeile']} (Commander Spellbook: {SPELLBOOK.get(bz['sb_tag'], bz['sb_tag'])})", ""]
    if upgrade:
        L += ["## Die Änderungen", "| raus | warum raus | rein | warum rein | Status |", "|---|---|---|---|---|"]
        for o_r, o_n in paare:
            cr, cn = cards.get(o_r), cards.get(o_n)
            gr = ("–" if not cr else "‹warum raus›" if basic(cr) else
                  f"‹warum raus› *({grund_raus(cr, v_von(cr), rollen_je[o_r], k_alt, ckurz)})*")
            gn = ("–" if not cn else "‹warum rein›" if basic(cn) else
                  f"‹warum rein, aus dem Oracle-Text› *({grund_rein(cn, v_von(cn), rollen_je[o_n], k_alt, k_neu, ckurz)})*")
            L.append(f"| {cr['name'] if cr else '–'} | {gr} | {cn['name'] if cn else '–'} | {gn} | {status(cn) if cn else '–'} |")
        if any("⚑" in status(cards[o]) for o in set(rein)):
            L += ["", ">! **⚑ Rückfrage:** Diese Karten wurden zusammen mit dem Deck erfasst und liegen vielleicht schon "
                  "beim Deck (Maybeboard oder fehlende Deckkarte). Beim Aufbau prüfen."]
        L += ["", "## Kennzahlen vorher und nachher", "| Kennzahl | vorher | nachher | Richtwert |", "|---|---|---|---|"]
    else:
        L += ["## Kennzahlen", "| Kennzahl | Deck | Richtwert |", "|---|---|---|"]
    for k, n, mn, ziel, _ in ROLLEN[:6]:
        L.append(f"| {n} | " + (f"{k_alt[k]} | " if upgrade else "") + f"{k_neu[k]} | {mn}–{ziel} |")
    for key, n, rw in (("_inst", "davon Instant-Interaktion", "≥ 4"), ("_mv", "Ø MV", "≤ 3,5"),
                       ("_gc", "Game Changer", f"≤ {bz['limit']}" if bz["limit"] < 99 else "–")):
        f = (lambda x: f"{x:.2f}".replace(".", ",")) if key == "_mv" else str
        L.append(f"| {n} | " + (f"{f(k_alt[key])} | " if upgrade else "") + f"{f(k_neu[key])} | {rw} |")
    if a.thema:
        A, karten, richt = lade_archetypen()
        ziel = ziel_archetyp(A, a.thema, None)
        if ziel:
            def paket_z(cm, mn):
                dz = Counter()
                for q, c in cm + mn:
                    dz[c["oid"]] += q
                return A.zaehle_deck(dz, karten, {c["oid"] for _, c in cm})
            z_n = paket_z(cmdr, main)
            z_a = paket_z(cmdr_a, main_a) if upgrade else None
            for key, label, _, kern in A.ARCHETYPEN[ziel]["pakete"]:
                m = (richt or {}).get("archetypen", {}).get(ziel, {}).get("pakete", {}).get(f"{ziel}.{key}")
                L.append(f"| {label} | " + (f"{z_a[f'{ziel}.{key}']} | " if upgrade else "")
                         + f"{z_n[f'{ziel}.{key}']} | {('Median ' + A.de(m['median'])) if m else '–'} |")
    L += ["", "## Spielplan", "- **Früh:** ‹…›", "- **Mitte:** ‹…›", "- **Spät / Siegwege:** ‹…›", "",
          "## Ehrliche Einschätzung und Abstriche", ">! ‹Was fehlt, was schwach bleibt, welche Käufe später am meisten bringen›",
          "", "## Kartenerklärungen", "| Karte | Rolle | Warum im Deck & Synergie | Commander-Bezug | Status |",
          "|---|---|---|---|---|"]
    erkl = [cards[o] for o in dict.fromkeys(rein) if not basic(cards[o])] if upgrade else [c for _, c in cmdr] + [c for _, c in main if not basic(c)]
    gruppen = {}
    for c in erkl:
        g = "commander" if any(c["oid"] == x["oid"] for _, x in cmdr) and not upgrade else haupt_rolle(rollen_je.get(c["oid"]) or rollen(con, c), c)
        gruppen.setdefault(g, []).append(c)
    for g in ["commander"] + ROLLEN_FOLGE:
        if g not in gruppen:
            continue
        L.append(f"| ## {'Commander' if g == 'commander' else rollen_name(g)} |")
        for c in sorted(gruppen[g], key=lambda c: (c["cmc"] or 0, c["name"])):
            v = v_von(c)
            daten = edh_txt(v, ckurz) if g != "commander" else "Commander"
            L.append(f"| {c['name']} | {rollen_txt(rollen_je.get(c['oid']) or rollen(con, c)).replace(',', ', ')} | ‹…› *({daten})* | ‹…› |"
                     f" {status(c) if g != 'commander' else '–'} |")
    L += ["", "## So bin ich vorgegangen",
          "1. Gespräch nach Fragenplan: ‹Ausgangslage/Passung, Richtung, Budget, Game Changer, weitere Antworten›",
          f"2. Ausgangslage: `deckbau.py passung` – ‹Befund in einem Satz›",
          f"3. Recherche: EDHREC ({epfad or '–'}, {heute}), Commander Spellbook, Scryfall-Funktionstags; "
          + ("`deckbau.py upgrade`" if upgrade else "`deckbau.py kandidaten`") + ", `oracle` für jede beschriebene Karte",
          "4. Prüfläufe: `pruefen` ohne offene Warnungen, `archetypen.py deck`",
          "5. Anpassungen: ‹Änderungen aus den Anpassungsrunden›", "", "<seitenumbruch>", "", "## Anhang: Moxfield",
          "[moxfield]", "", "```", einfuegeblock(a.neu, [c["name"] for _, c in cmdr]), "```", ""]
    out = a.out or "fazit.md"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(L))
    offen = sum(z.count("‹") for z in L)
    print(f"Fazit-Entwurf: {out} | {len(paare)} Zeilen in „Die Änderungen“ | {len(erkl)} Kartenerklärungen | "
          f"{offen} Platzhalter ‹…› zu füllen (nur Text – Zahlen, Status und Daten stehen schon drin)")
    if upgrade and not a.paare:
        print("Paare automatisch gebildet (Land↔Land, gleiche Hauptrolle, ähnliche MV) – anders gewünscht: "
              "Datei mit „Raus -> Rein“ je Zeile und --paare <datei>.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("commander")
    p.add_argument("name")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--budget", action="store_true")
    p = sp.add_parser("commander-suche")
    p.add_argument("--thema")
    p.add_argument("--farben")
    p.add_argument("--text")
    p.add_argument("--nur-besitz", action="store_true")
    p.add_argument("--limit", type=int, default=20)
    p = sp.add_parser("kandidaten")
    p.add_argument("commander")
    p.add_argument("--weg", type=int, choices=(1, 2), required=True)
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--thema")
    p.add_argument("--budget", action="store_true")
    p.add_argument("--out")
    p = sp.add_parser("pruefen")
    p.add_argument("deck")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--ersetzt")
    p.add_argument("--combos-fehlend", action="store_true")
    p.add_argument("--idee", help="Vormerkungen dieser Idee (I-nnn) als frei behandeln")
    p = sp.add_parser("erklaerung")
    p.add_argument("deck")
    p.add_argument("--idee", help="Vormerkungen dieser Idee (I-nnn) als frei behandeln")
    p.add_argument("--ersetzt")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--out")
    p = sp.add_parser("upgrade")
    p.add_argument("deck", help="Deckname oder Soll-Stand-Datei")
    p.add_argument("--stufe", type=int, default=0, choices=(0, 1))
    p.add_argument("--max-preis", type=float, default=10.0, help="Stufe 1: höchster Einzelpreis in EUR")
    p.add_argument("--thema", help="EDHREC-Thema (nur für Kandidaten, gekennzeichnet)")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--paare", type=int, default=15)
    p.add_argument("--abstand", type=float, default=0.08, help="Mindestabstand im Wert für ein Tauschpaar")
    p.add_argument("--idee", help="Vormerkungen dieser Idee (I-nnn) als frei behandeln")
    p.add_argument("--out")
    p = sp.add_parser("passung")
    p.add_argument("deck", help="Deckname oder Soll-Stand-Datei")
    p.add_argument("--thema", help="Ziel-Thema: Archetyp (landfall, counters …) oder EDHREC-Slug; sonst aus der Strategie")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--kandidaten", type=int, default=10, help="höchstens so viele Commander-Kandidaten bewerten")
    p.add_argument("--kauf", type=int, default=0, help="zusätzlich N Kauf-Commander zum Ziel-Thema (EDHREC)")
    p.add_argument("--max-illegal", type=int, default=15, help="Kandidaten mit mehr Karten außerhalb der Farbidentität weglassen")
    p = sp.add_parser("fazit")
    p.add_argument("--neu", required=True, help="Entwurf (am besten mit eigenen Drucken aus mtg_db.py drucke)")
    p.add_argument("--alt", help="Soll-Stand bzw. Deckname (Upgrade); ohne = neues Deck")
    p.add_argument("--paare", help="Datei „Raus -> Rein“ je Zeile (z. B. aus upgrade); sonst automatisch")
    p.add_argument("--thema", help="Archetyp für die Paket-Kennzahlen (landfall, tokens …)")
    p.add_argument("--stufe", default="Stufe 0", help="Text für Kachel und Oberzeile, z. B. „Stufe 1 (bis 25 €)“")
    p.add_argument("--deckname")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--idee", help="Vormerkungen dieser Idee (I-nnn) als frei behandeln")
    p.add_argument("--out")
    p = sp.add_parser("oracle")
    p.add_argument("karten", nargs="*")
    p.add_argument("--alt")
    p.add_argument("--neu")
    p.add_argument("--rulings", action="store_true")
    p = sp.add_parser("alternativen")
    p.add_argument("karte")
    p.add_argument("--farben")
    p.add_argument("--limit", type=int, default=6)
    p.add_argument("--idee", help="Vormerkungen dieser Idee (I-nnn) als frei behandeln")
    import signal
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    a = ap.parse_args()
    global IDEE
    IDEE = getattr(a, "idee", None)
    con = db()
    {"commander": cmd_commander, "commander-suche": cmd_commander_suche, "kandidaten": cmd_kandidaten,
     "pruefen": cmd_pruefen, "erklaerung": cmd_erklaerung, "alternativen": cmd_alternativen,
     "upgrade": cmd_upgrade, "oracle": cmd_oracle, "passung": cmd_passung, "fazit": cmd_fazit}[a.cmd](con, a)


if __name__ == "__main__":
    main()
