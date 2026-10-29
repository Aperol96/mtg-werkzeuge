#!/usr/bin/env python3
"""deckbau.py – Werkzeuge für das geführte Commander-Deckbau-Verfahren (Projektdatei 08_Deckbau-Verfahren).

Setzt eine mit mtg_db.py gebaute Datenbank voraus (mtg.sqlite im aktuellen Ordner, mtg_db.py daneben).
Bewertungsregeln (Rollen, Wert, Synergie, Kompromiss-Stufen, Klassen A–D) stehen in bewertung.py,
die Konsistenz-Simulation in simulation.py.

Befehle (Details: python3 deckbau.py <befehl> --help)
  commander <Name>               Steckbrief: Oracle-Text, Besitz, EDHREC-Themen, Top-/High-Lift-Karten, Combos
  commander-suche                Commander finden (EDHREC-Thema bzw. eigener Bestand)
  synergie <Commander|Deck>      Welche freien Karten passen zum Commander-Text – auch ohne EDHREC-Eintrag?
                                 Rangliste mit Bezug, „warum“, Paket-Bedarf und EDHREC als Zusatzpunkt
  kandidaten <Commander> --weg 1|2   Kartenpool (EDHREC + Sammlung) mit Rollen, Bezug, Wert, Besitz, Preis
  pruefen <entwurf>              Qualitätskontrolle: Kartenzahl, Rollen gegen Richtwert (Archetyp vor Template),
                                 Interaktion nach Ziel, Kurve, Farbquellen, Bracket-Zeile, Kaufliste, Warnungen
  abnahme <deck|entwurf>         Bracket-3-Abnahme (Definition of Done, 08): harte Grenzen, Rollen, Interaktion
                                 nach Ziel, ≥ 2 Siegwege, Kernpakete ≥ 80 %, Simulation, stärker als die Basis
  upgrade <deck>                 Upgrade-Modus mit Raus-Sperren (Kernpaket unter Median, Commander-Bezug, Rolle unter
                                 Minimum), Kompromiss-Stufen, Klassen A–D; kurze Ausgabe (--voll für alle Listen)
  passung <deck>                 Passt das Deck zu Commander und Ziel? Alternative Commander, Befund, Optionen A–D
  fazit --neu <entwurf>          Fazit-Entwurf für kartenbilder.py (Zahlen, Status, Abnahme vorbefüllt)
  gegentest <A> <B> | --prompt   Zwei Decks vergleichen (z. B. Projekt gegen Konkurrenz-Skill) bzw. Auftrag für
                                 den Konkurrenz-Agenten erzeugen (08a, Gegentest)
  erklaerung <entwurf>           Datenbasis je Karte für die Kartenerklärungen
  oracle <Karte …> | --alt --neu Oracle-Text – Pflicht vor jedem Vorschlag
  alternativen <Karte>           günstigere Karten mit gleicher Rolle (frei zuerst)
  verkauf                        Verkaufsprüfung der freien Karten (Kat. 1, Kat. 2, Behalten)

--ersetzt <deck>: Karten dieses Decks gelten für den Entwurf als vorhanden (Upgrade eines bestehenden Decks).
--idee I-nnn: Vormerkungen dieser Idee (claude/sammlung/vormerkungen.csv) gelten für den Entwurf als frei.
Geplante Verkäufe (Ideen „V-nnn“) sind weiche Vormerkungen: frei, aber mit Hinweis „Verkauf geplant“.

Kennzahlen (einheitlich in allen Werkzeugen):
  Rollen        zählen über die 99 ohne Commander; Regeln mit Qualitätsfiltern aus bewertung.py.
  Ø MV / Kurve  über alle Nichtländer inklusive Commander.
  EDHREC-Werte  Commander-Seite mit Bracket-Filter, ohne Thema. Nicht gelistet = unbekannt (nicht schwach).
  Wert          max(EDHREC-Wert, Schätzung aus Oracle-Bezug); „≈“ = geschätzt.
EDHREC nicht erreichbar → laute Meldung, ältere Zwischenspeicher-Daten mit Datum, sonst nur Oracle-Bezug.
"""
import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bewertung as B  # noqa: E402
import mtg_db as M  # noqa: E402

BRACKET_PFAD = {1: "exhibition", 2: "core", 3: "upgraded", 4: "optimized", 5: "cedh"}
GC_LIMIT = {1: 0, 2: 0, 3: 3, 4: 99, 5: 99}
ROLLEN = [("land", "Länder"), ("ramp", "Ramp"), ("ka", "Kartenvorteil"), ("gezielt", "Gezielte Interaktion"),
          ("massen", "Massen-Interaktion"), ("schutz", "Schutz"), ("tutor", "Tutor"), ("rekursion", "Rekursion")]
ROLLE_NAME = dict(ROLLEN)
KERN = ["land", "ramp", "ka", "gezielt", "massen", "schutz"]
FARBSLUG = {"W": "mono-white", "U": "mono-blue", "B": "mono-black", "R": "mono-red", "G": "mono-green"}
SPELLBOOK = {"R": "Ruthless", "S": "Spicy", "P": "Powerful", "O": "Oddball", "C": "Core", "E": "Exhibition", "B": "Banned"}
IDEE = None            # mit --idee I-nnn: Vormerkungen dieser Idee gelten für den Entwurf als frei
EDH_STATUS = []        # Meldungen zu EDHREC (nicht erreichbar, alte Daten) – erscheinen in der Ausgabe
INTERAKTION_ZIEL = {"kreatur": 5, "artefakt": 2, "verzauberung": 2, "friedhof": 1}   # Abnahme, Einschätzung


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


def sicht(con, c, tags=None):
    """Karten-Dict der Datenbank -> Sicht für bewertung.py."""
    return B.sicht(c["name"], c["type_line"], c["text"], c["keywords"],
                   tags if tags is not None else tags_of(con, c["oid"]), c["cmc"], c["pt"])


def rollen(con, c, tags=None):
    """Rollen einer Karte – eine Regel für alle Werkzeuge (bewertung.rollen_detail, mit Qualitätsfiltern)."""
    return B.rollen(sicht(con, c, tags))


def rollen_txt(r):
    return ",".join(ROLLE_NAME[x] for x in r) or "Plan/Synergie"


def ist_instant(c):
    return "Instant" in front_type(c) or "Flash" in (c["keywords"] or "")


def basic(c):
    return front_type(c).startswith("Basic")


def besitz(con, oid, ohne_deck=None):
    """(Besitz, in Decks ohne das ersetzte Deck, frei). Frei = Besitz - Decks - Vormerkungen anderer Ideen."""
    b = con.execute("SELECT COALESCE(SUM(qty),0) FROM collection WHERE oracle_id=? AND lower(proxy)<>'true'",
                    (oid,)).fetchone()[0]
    d = con.execute("SELECT COALESCE(SUM(qty),0) FROM deck_cards WHERE oracle_id=? AND deck_id IS NOT ?"
                    " AND board IN ('main','commander','sideboard','companion')", (oid, ohne_deck)).fetchone()[0]
    try:
        v = con.execute("SELECT COALESCE(SUM(qty),0) FROM vormerkungen WHERE oracle_id=? AND idee IS NOT ?"
                        " AND COALESCE(weich,0)=0", (oid, IDEE)).fetchone()[0]
    except sqlite3.OperationalError:      # ältere Datenbank ohne (weiche) Vormerkungen
        v = 0
    return b, d, max(b - d - v, 0)


def verkauf_geplant(con, oid):
    """Geplanter Verkauf (weiche Vormerkung „V-nnn“) → z. B. 'V-001', sonst ''. Sperrt nicht, nur Hinweis."""
    try:
        r = con.execute("SELECT GROUP_CONCAT(DISTINCT idee) FROM vormerkungen WHERE oracle_id=? AND weich=1",
                        (oid,)).fetchone()
    except sqlite3.OperationalError:
        return ""
    return (r[0] or "") if r else ""


def pct(x):
    return "" if x is None else f"{x * 100:.0f}%"


def de(x, n=2):
    return f"{x:.{n}f}".replace(".", ",")


def lies_deck(con, path):
    """Deckdatei -> (Commander [(Anzahl, card)], Hauptdeck [(Anzahl, card)], unbekannte Namen, Hinweis)."""
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


def cname_von(cmdr):
    return " + ".join(c["name"] for _, c in cmdr)


def kurzname(cname):
    """'Karametra, God of Harvests' -> 'Karametra' (für Sätze wie „in 27 % der Karametra-Decks“)."""
    return " + ".join(re.split(r",| of | the ", M.front(n))[0].strip() for n in cname.split(" + "))


# ----------------------------------------------------------------- EDHREC (laut bei Fehlern, mit Rückfall)
def edh_slug(name):
    teile = [p.strip() for p in re.split(r"\s+\+\s+|\s*&\s*", name) if p.strip()]
    slugs = []
    for p in teile:
        n = re.sub(r"[^a-z0-9\s-]", "", M.fold(M.front(p)))
        slugs.append(re.sub(r"[\s-]+", "-", n).strip("-"))
    return "-".join(sorted(slugs)) if len(slugs) > 1 else slugs[0]


def edhrec(pfad, max_alter_h=72):
    """EDHREC-JSON mit Zwischenspeicher (3 Tage). Seite fehlt → None (still). Netzfehler → Meldung auf stderr und in
    EDH_STATUS; dann ältere Zwischenspeicher-Daten mit Datum, sonst None (Bewertung nur aus Oracle-Bezug)."""
    os.makedirs("cache/edhrec", exist_ok=True)
    fn = os.path.join("cache/edhrec", pfad.replace("/", "__") + ".json")
    if os.path.exists(fn) and time.time() - os.path.getmtime(fn) < max_alter_h * 3600:
        return json.load(open(fn, encoding="utf-8"))
    try:
        d = M.get_json(f"https://json.edhrec.com/pages/{pfad}.json")
    except Exception as e:                       # urllib.error.HTTPError 404 = Seite gibt es nicht
        if getattr(e, "code", None) in (403, 404):
            return None
        alt = os.path.exists(fn)
        grund = str(getattr(e, "reason", "") or e.__class__.__name__)[:80]
        meldung = (f"EDHREC nicht erreichbar ({grund}) – "
                   + (f"nutze Zwischenspeicher vom {time.strftime('%d.%m.%Y', time.localtime(os.path.getmtime(fn)))}"
                      if alt else "keine EDHREC-Werte, Bewertung nur aus Oracle-Bezug"))
        if meldung not in EDH_STATUS:
            EDH_STATUS.append(meldung)
            print(f"!! {meldung} [{pfad}]", file=sys.stderr)
        return json.load(open(fn, encoding="utf-8")) if alt else None
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
    for cl in (d or {}).get("container", {}).get("json_dict", {}).get("cardlists", []):
        for cv in cl.get("cardviews", []):
            n = cv.get("name")
            if not n or n in out:
                continue
            pot = cv.get("potential_decks") or 0
            out[n] = {"synergy": cv.get("synergy"), "lift": cv.get("lift"), "decks": cv.get("num_decks"),
                      "inclusion": (cv.get("num_decks") or 0) / pot if pot else None,
                      "liste": cl.get("header")}
    return out


def edh_themen(d):
    return [t["slug"] for t in (d or {}).get("panels", {}).get("taglinks", [])]


def edh_von(edh, c):
    return edh.get(c["name"]) or edh.get(M.front(c["name"])) or {}


def edh_txt(v, ckurz):
    if not v or v.get("inclusion") is None:
        return f"nicht auf der EDHREC-Seite von {ckurz} (unbekannt)"
    syn = v.get("synergy")
    return (f"in {v['inclusion'] * 100:.0f} % der {ckurz}-Decks"
            + ("" if syn is None else f", Synergie {syn * 100:+.0f} %".replace("-", "−")))


def edh_zeile(epfad):
    return f"EDHREC: {epfad or 'keine Daten'}" + (" · " + " · ".join(EDH_STATUS) if EDH_STATUS else "")


# ----------------------------------------------------------------- Bewertung je Karte (Bezug, Wert)
_KTYPEN = {}


def kreaturtypen(con):
    if "t" not in _KTYPEN:
        _KTYPEN["t"] = B.kreaturtypen(r[0] for r in con.execute("SELECT type_line FROM cards"))
    return _KTYPEN["t"]


def profil_fuer(con, cmdr_karten, data=None):
    """Commander-Profil (Themen, Kreaturtypen) aus Commander-Text, EDHREC-Themen nur als Zusatz (Gewicht 0,4)."""
    return B.commander_profil([sicht(con, c) for c in cmdr_karten], kreaturtypen(con), edh_themen(data))


def bewerte(con, prof, edh, c, tags=None):
    """-> dict: v (EDHREC-Eintrag), edh (Wert oder None), bezug (0–1), gruende, wert, quelle ('EDHREC'|'≈ Bezug')."""
    s = sicht(con, c, tags)
    v = edh_von(edh, c)
    e = B.wert_edhrec(v)
    pkt, gr = B.karte_bezug(prof, s) if prof else (0, [])
    bz = B.bezug_norm(pkt)
    w, q = B.gesamtwert(e, bz, c.get("rank"))
    return {"v": v, "edh": e, "bezug": bz, "gruende": gr, "wert": w, "quelle": q, "sicht": s}


def wert_txt(b):
    return ("" if b["quelle"] == "EDHREC" else "≈") + de(b["wert"])


# ----------------------------------------------------------------- Archetyp-Kontext (Pakete, Richtwerte)
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


def strategie_von(con, did):
    if not did:
        return None
    r = con.execute("SELECT strategie FROM decks WHERE deck_id=?", (did,)).fetchone()
    return r[0] if r else None


def archetyp_kontext(con, cmdr, main, did=None, thema=None, AK=None):
    """Ziel-Archetyp (Vorgabe → Strategie im Register → best abgedeckter), Paketzählung, Richtwerte."""
    A, karten, richt = AK or lade_archetypen()
    dz = Counter()
    for q, c in cmdr + main:
        dz[c["oid"]] += q
    z = A.zaehle_deck(dz, karten, {c["oid"] for _, c in cmdr})
    ziel = ziel_archetyp(A, thema, strategie_von(con, did))
    herkunft = "Vorgabe" if thema and ziel else "Strategie im Register" if ziel else "am besten abgedeckt"
    if not ziel:
        ziel = max(A.ARCHETYPEN, key=lambda k: A.deckung(z, richt, k))
    pakete = []
    for key, label, fn, kern in A.ARCHETYPEN[ziel]["pakete"]:
        m = (richt or {}).get("archetypen", {}).get(ziel, {}).get("pakete", {}).get(f"{ziel}.{key}") or {}
        pakete.append({"key": key, "label": label, "kern": kern, "median": m.get("median"), "min": m.get("min"),
                       "ist": z[f"{ziel}.{key}"], "fn": fn})
    return {"A": A, "karten": karten, "richt": richt, "ziel": ziel, "herkunft": herkunft, "z": z, "pakete": pakete,
            "soll": B.richtwerte(ziel, richt), "name": A.ARCHETYPEN[ziel]["name"]}


def karte_pakete(ak, oid, typen=frozenset()):
    """Kernpakete des Ziel-Archetyps, zu denen die Karte gehört (Schlüssel). Kindred: nur Karten, die einen Typ des
    Decks nennen oder einen Typ wählen lassen (ein Golem-Lord ist kein Payoff für ein Elementar-Deck)."""
    k = ak["karten"].get(oid)
    out = set()
    if k and ak["ziel"] == "kindred" and typen and not (
            k["t"] & {"typal-choose", "typal-share"} or "changeling" in k["kw"]
            or any(re.search(rf"\b{re.escape(t)}s?\b", k["text"] or "") for t in typen)):
        return out
    for p in ak["pakete"]:
        try:
            if k and p["kern"] and p["fn"](k):
                out.add(p["key"])
        except Exception:
            pass
    return out


def deck_typen(prof):
    """Kreaturtypen, um die das Deck spielt (Commander-Profil) – Mana nur für diese Typen zählt als Ramp."""
    return frozenset((prof or {}).get("typen", {}))


def rollen_im_plan(con, c, ziel, tags=None, typen=frozenset()):
    """Rollen, die im Plan zählen: ein Wipe, der den eigenen Plan zerstört (Go-wide), zählt nicht als Massen-Interaktion."""
    s = sicht(con, c, tags)
    r = B.rollen(s, typen)
    if "massen" in r and B.zerstoert_plan(s, ziel):
        r = [x for x in r if x != "massen"]
    return r


def zaehle_rollen(con, main, ziel, typen=frozenset()):
    z, inst = Counter(), 0
    for q, c in main:
        r = rollen_im_plan(con, c, ziel, typen=typen)
        for x in r:
            z[x] += q
        if "gezielt" in r and ist_instant(c):
            inst += q
    return z, inst


# ----------------------------------------------------------------- commander
def cmd_commander(con, a):
    c = finde(con, a.name)
    b, d, f = besitz(con, c["oid"])
    print(f"{c['name']}  {c['mana_cost']}  | {M.farbname(c['ci'])} | {c['type_line']}")
    print(f"Commander-legal: {c['legal']} | Game Changer: {'ja' if c['gc'] else 'nein'} | "
          f"Besitz {b}, in Decks {d}, frei {f} | ab {c['eur'] or '?'} €")
    print(f"\nOracle-Text:\n{c['text']}")
    prof = profil_fuer(con, [c])
    print("\nProfil aus dem Oracle-Text: " + (" · ".join(
        f"{B.THEMEN[k][0]} ({'erzeugt' if d_['erzeugt'] else ''}{'/' if d_['erzeugt'] and d_['nutzt'] else ''}"
        f"{'nutzt' if d_['nutzt'] else ''})" for k, d_ in prof["themen"].items()) or "keine Themen erkannt")
          + (" · Typen: " + ", ".join(f"{t}" for t, w in prof["typen"].items() if w >= 1) if prof["typen"] else ""))
    t = sorted(tags_of(con, c["oid"]))
    print(f"Scryfall-Funktionstags: {', '.join(t[:40])}{' …' if len(t) > 40 else ''}")
    data, pfad = edhrec_commander(c["name"], a.bracket, None, a.budget)
    if not data:
        print("\nEDHREC: keine Seite gefunden (neuer oder seltener Commander?)" + (" – " + "; ".join(EDH_STATUS)
                                                                                 if EDH_STATUS else ""))
        return
    jd = data["container"]["json_dict"]
    allg, _ = edhrec_commander(c["name"])
    ges = allg["container"]["json_dict"].get("card", {}) if allg else {}
    print(f"\nEDHREC ({pfad}): {jd.get('card', {}).get('num_decks')} Decks in dieser Auswahl, "
          f"{ges.get('num_decks')} gesamt | Rang {ges.get('rank')} | Salt {round(ges.get('salt') or 0, 2)}")
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
            sys.exit(f"EDHREC-Thema '{a.thema}' nicht gefunden (Slug wie auf edhrec.com/tags, z. B. tokens, aristocrats)"
                     + (" – " + "; ".join(EDH_STATUS) if EDH_STATUS else ""))
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


# ----------------------------------------------------------------- synergie
def commander_und_deck(con, ref):
    """Commander-Name oder Deck -> (Commander-Karten, Hauptdeck, Pfad, deck_id)."""
    oid = M.resolve_name(con, ref)
    if oid and not os.path.exists(ref) and M.is_commander_eligible(con, oid):
        return [card(con, oid)], [], None, None
    pfad, did = deck_aus_ref(con, ref)
    cmdr, main, _, _ = lies_deck(con, pfad)
    if not cmdr:
        sys.exit("Kein Commander erkannt")
    return [c for _, c in cmdr], main, pfad, did


def cmd_synergie(con, a):
    cmdr_k, main, pfad, did = commander_und_deck(con, a.ref)
    cname = " + ".join(c["name"] for c in cmdr_k)
    ci = set("".join(c["ci"] for c in cmdr_k))
    data, epfad = edhrec_commander(cname, a.bracket)
    edh = edh_karten(data)
    prof = profil_fuer(con, cmdr_k, data)
    ak = archetyp_kontext(con, [(1, c) for c in cmdr_k], main, did, a.thema) if main or a.thema else None
    luecken = {p["key"]: p for p in (ak["pakete"] if ak else []) if p["kern"] and p["median"] and p["ist"] < p["median"]}
    im_deck = {c["oid"] for _, c in main} | {c["oid"] for c in cmdr_k}
    print(f"Synergie {cname} | {M.farbname(''.join(sorted(ci)))} | {edh_zeile(epfad)}")
    print("Profil: " + (" · ".join(f"{B.THEMEN[k][0]} ({'liefert' if d['erzeugt'] else ''}"
                                   f"{'+' if d['erzeugt'] and d['nutzt'] else ''}{'nutzt' if d['nutzt'] else ''}"
                                   f"{', EDHREC-Hinweis' if d['gewicht'] < 1 else ''})"
                                   for k, d in prof["themen"].items()) or "keine Themen im Text erkannt")
          + ("".join(" · Typen: " + ", ".join(ts) for ts in [[t for t, w in prof["typen"].items() if w >= 0.4]] if ts)))
    if ak:
        print(f"Ziel-Archetyp: {ak['name']} ({ak['herkunft']}) · Pakete: " + " | ".join(
            f"{p['label']} {p['ist']}/{A_de(p['median'])}{' ⚠' if p['key'] in luecken else ''}" for p in ak["pakete"]
            if p["kern"]))
    zeilen = []
    for (oid,) in con.execute("SELECT oracle_id FROM v_karten WHERE frei > 0"):
        if oid in im_deck:
            continue
        c = card(con, oid)
        if not c or c["legal"] != "legal" or not set(c["ci"]) <= ci or basic(c):
            continue
        b = bewerte(con, prof, edh, c)
        pk = karte_pakete(ak, oid, deck_typen(prof)) & set(luecken) if ak else set()
        if b["bezug"] <= 0 and not pk and b["edh"] is None and not a.alle:
            continue
        s = b["sicht"]
        stoert = ak and B.zerstoert_plan(s, ak["ziel"])
        zeilen.append({"c": c, "b": b, "pakete": pk, "rollen": B.rollen(s), "stoert": stoert,
                       "punkte": b["bezug"] + (0.2 if pk else 0) + 0.2 * max(0, min(b["edh"] or 0, 1)),
                       "verkauf": verkauf_geplant(con, oid)})
    zeilen.sort(key=lambda z: -z["punkte"])
    print(f"\nFreie Karten mit Bezug ({len(zeilen)}; Bezug = Oracle-Text gegen das Profil, EDHREC nur als Zusatzpunkt):")
    M.table([(z["c"]["name"], de(z["b"]["bezug"]), "; ".join(z["b"]["gruende"][:4]) or "–",
              ", ".join(luecken[p]["label"] for p in z["pakete"]) or "", rollen_txt(z["rollen"]),
              pct(z["b"]["v"].get("inclusion")) or "–",
              ("zerstört Plan" if z["stoert"] else "") + (f" Verkauf geplant ({z['verkauf']})" if z["verkauf"] else ""))
             for z in zeilen[:a.top]],
            ["Karte", "Bezug", "warum", "füllt Paket", "Rollen", "EDHREC", "Hinweis"])
    ohne = [z for z in zeilen if z["b"]["edh"] is None and z["b"]["bezug"] >= B.BEZUG_SPERRE]
    if ohne:
        print(f"\nStarker Bezug, aber nicht auf der EDHREC-Seite ({len(ohne)}) – genau die Karten, die EDHREC übersieht: "
              + ", ".join(z["c"]["name"] for z in ohne[:15]) + (" …" if len(ohne) > 15 else ""))
    if main:
        deckz = []
        for q, c in main:
            if "Land" in front_type(c):
                continue
            b = bewerte(con, prof, edh, c)
            deckz.append((c["name"], de(b["bezug"]), "; ".join(b["gruende"][:3]) or "–", wert_txt(b)))
        deckz.sort(key=lambda r: float(r[3].lstrip("≈").replace(",", ".")))
        print("\nDeckkarten mit dem geringsten Wert (max. aus EDHREC und Bezug; Raus-Kandidaten prüfen, nicht automatisch raus):")
        M.table(deckz[:12], ["Karte", "Bezug", "warum", "Wert"])
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Karte", "Bezug", "Gründe", "füllt Paket", "Rollen", "EDHREC-Wert", "Wert", "Quelle", "zerstört Plan"])
            for z in zeilen:
                w.writerow([z["c"]["name"], z["b"]["bezug"], "; ".join(z["b"]["gruende"]),
                            ", ".join(z["pakete"]), rollen_txt(z["rollen"]), z["b"]["edh"], z["b"]["wert"],
                            z["b"]["quelle"], int(bool(z["stoert"]))])
        print(f"\nVollständige Liste -> {a.out}")


def A_de(x):
    return "–" if x is None else f"{x:g}".replace(".", ",")


# ----------------------------------------------------------------- kandidaten
def basics_verfuegbar(con, ci, ohne_deck=None):
    out = {}
    for name, oid in con.execute("SELECT name, oracle_id FROM v_basics"):
        if name in ("Plains", "Island", "Swamp", "Mountain", "Forest"):
            farbe = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}[name]
            if farbe in ci:
                out[name] = besitz(con, oid, ohne_deck)[2]
    return out


def kandidaten_pool(con, cmd, edh, prof):
    pool = {}
    for n, v in edh.items():
        oid = M.resolve_name(con, n)
        if oid:
            pool[oid] = "EDHREC"
    for (oid,) in con.execute("SELECT oracle_id FROM v_karten WHERE frei > 0"):
        pool.setdefault(oid, "Sammlung")
    ci = set(cmd["ci"])
    zeilen = []
    for oid, quelle in pool.items():
        c = card(con, oid)
        if not c or oid == cmd["oid"] or c["legal"] != "legal" or not set(c["ci"]) <= ci or basic(c):
            continue
        t = tags_of(con, oid)
        b = bewerte(con, prof, edh, c, t)
        bb, d, f = besitz(con, oid)
        zeilen.append({"c": c, "name": c["name"], "rollen": B.rollen(b["sicht"]), "instant": ist_instant(c),
                       "b": b, "frei": f, "besitz": bb, "in_decks": d, "quelle": quelle,
                       "verkauf": verkauf_geplant(con, oid) if f else ""})
    return zeilen


def ampel_weg1(zeilen, basics, soll=None):
    fehler, gelb, zus = [], [], []
    soll = soll or B.TEMPLATE
    for k, n in ROLLEN:
        frei = sum(1 for z in zeilen if k in z["rollen"] and z["frei"] > 0)
        ges = sum(1 for z in zeilen if k in z["rollen"])
        mn, ziel = soll.get(k, (None, None))
        verfuegbar = frei + (sum(basics.values()) if k == "land" else 0)
        status = ""
        if mn:
            status = "ok" if verfuegbar >= mn else "knapp" if verfuegbar >= mn * 0.5 else "FEHLT"
            if k in ("land", "ramp", "ka", "gezielt", "massen"):
                (fehler if verfuegbar < mn * 0.5 else gelb if verfuegbar < mn else []).append(n)
        extra = f" (+ {sum(basics.values())} freie Standardländer)" if k == "land" else ""
        zus.append((n, f"{frei}{extra}", ges, f"{mn}–{ziel}" if mn else "–", status))
    return zus, fehler, gelb


def cmd_kandidaten(con, a):
    cmd = finde(con, a.commander)
    ci = set(cmd["ci"])
    data, pfad = edhrec_commander(cmd["name"], a.bracket, a.thema, a.budget)
    edh = edh_karten(data)
    prof = profil_fuer(con, [cmd], data)
    zeilen = kandidaten_pool(con, cmd, edh, prof)
    zeilen.sort(key=lambda z: (-(z["frei"] > 0) if a.weg == 1 else 0, -z["b"]["wert"], z["c"]["rank"] or 999999))
    out = a.out or "kandidaten.csv"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"# Kandidaten für {cmd['name']} – Weg {a.weg} – EDHREC: {pfad or 'keine Daten'} – "
                    f"Stand {time.strftime('%Y-%m-%d')}"])
        w.writerow(["Karte", "Rollen", "Instant", "MV", "Typ", "Bezug", "Gründe", "Wert", "Wert-Quelle", "Synergie",
                    "Inclusion", "frei", "Besitz", "in Decks", "ab EUR", "Game Changer", "Quelle", "Verkauf geplant"])
        for z in zeilen:
            b, c = z["b"], z["c"]
            w.writerow([c["name"], rollen_txt(z["rollen"]), int(z["instant"]), c["cmc"], front_type(c), b["bezug"],
                        "; ".join(b["gruende"]), b["wert"], b["quelle"],
                        "" if b["v"].get("synergy") is None else round(b["v"]["synergy"], 3),
                        "" if b["v"].get("inclusion") is None else round(b["v"]["inclusion"], 3),
                        z["frei"], z["besitz"], z["in_decks"], c["eur"], c["gc"], z["quelle"], z["verkauf"]])
    print(f"Commander: {cmd['name']} ({M.farbname(cmd['ci'])}) | {edh_zeile(pfad)} | {len(zeilen)} Kandidaten -> {out}")
    vk = [f"{z['name']} ({z['verkauf']})" for z in zeilen if z["verkauf"]]
    if vk:
        print("Achtung – frei, aber zum Verkauf vorgesehen (vor dem Einplanen mit dem Nutzer klären): " + ", ".join(vk))
    basics = basics_verfuegbar(con, ci)
    soll = None
    if a.thema:
        A, _, richt = lade_archetypen()
        ziel = ziel_archetyp(A, a.thema, None)
        if ziel:
            soll = {r: (mn, z) for r, (mn, z, _) in B.richtwerte(ziel, richt).items()}
            print(f"Richtwerte: Archetyp {A.ARCHETYPEN[ziel]['name']} (vor Template)")
    zus, fehler, gelb = ampel_weg1(zeilen, basics, soll)
    print("\nRollen: freie Kandidaten in der Sammlung vs. Kandidaten gesamt (EDHREC + Sammlung):")
    M.table(zus, ["Rolle", "frei", "gesamt", "Richtwert", "Weg 1"])
    inst = sum(1 for z in zeilen if "gezielt" in z["rollen"] and z["instant"] and z["frei"] > 0)
    plan = [z for z in zeilen if z["frei"] > 0 and (z["b"]["bezug"] >= 0.33 or (z["b"]["v"].get("synergy") or 0) >= 0.10)]
    print(f"\nFreie Instant-Interaktion: {inst} | freie Plan-Karten (Oracle-Bezug ≥ 0,33 oder EDHREC-Synergie ≥ 10 %): "
          f"{len(plan)}")
    print(f"Freie Standardländer in den Farben: {basics}")
    gcs = [z for z in zeilen if z["c"]["gc"]]
    if gcs:
        print("Game Changer im Pool: " + ", ".join(f"{z['name']} ({'frei' if z['frei'] else str(z['c']['eur']) + ' €'})"
                                                   for z in gcs[:10]))
    if a.weg == 1:
        ampel = ("ROT – mit freien Karten nicht sinnvoll baubar" if fehler or len(plan) < 12 else
                 "GELB – baubar mit Abstrichen" if gelb or len(plan) < 25 else "GRÜN – gut baubar")
        print(f"\nMachbarkeit Weg 1 (Einschätzung des Tools): {ampel}")
        for txt, l in (("zu wenig", fehler), ("knapp", gelb)):
            if l:
                print(f"  {txt}: " + ", ".join(l))
        if len(plan) < 25:
            print(f"  wenig commander-spezifische Karten frei ({len(plan)})")
    print("\nBeste Kandidaten je Rolle (frei zuerst, nach Wert):")
    for k, n in ROLLEN[1:6]:
        sel = sorted([z for z in zeilen if k in z["rollen"]], key=lambda z: (-(z["frei"] > 0), -z["b"]["wert"]))
        print(f"  {n}: " + "; ".join(f"{z['name']}{' (frei)' if z['frei'] else ' – ' + str(z['c']['eur']) + ' €'}"
                                    for z in sel[:8]))
    sel = sorted([z for z in zeilen if "land" not in z["rollen"] and z["b"]["bezug"] >= 0.33],
                 key=lambda z: -z["b"]["bezug"])
    print("  Plan/Synergie (Oracle-Bezug): " + "; ".join(
        f"{z['name']}{' (frei)' if z['frei'] else ' – ' + str(z['c']['eur']) + ' €'}" for z in sel[:12]))
    if a.weg == 2:
        kauf = sorted([z for z in zeilen if not z["frei"] and z["quelle"] == "EDHREC"], key=lambda z: -z["b"]["wert"])
        print("\nKaufkandidaten Weg 2 (nicht frei, nach Wert; Wirkung und Klasse aus bewertung.py, Claude prüft):")
        rows = []
        for z in kauf[:25]:
            wk = B.wirkung(z["b"]["wert"])
            rows.append((z["name"], rollen_txt(z["rollen"]), wert_txt(z["b"]), z["c"]["eur"], wk,
                         B.klasse(wk, z["c"]["eur"]), "ja" if z["c"]["gc"] else "", "in anderem Deck" if z["besitz"] else ""))
        M.table(rows, ["Karte", "Rolle", "Wert", "ab €", "Wirkung", "Klasse", "GC", "Besitz"])


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
    if getattr(a, "ersetzt", None):
        return M.find_deck(con, a.ersetzt)
    r = con.execute("SELECT deck_id, kurz FROM decks WHERE datei=?", (os.path.basename(a.deck),)).fetchone()
    if r:
        print(f"(Soll-Stand von „{r[1]}“ erkannt – seine Karten zählen als vorhanden; sonst --ersetzt angeben)")
        return r[0]
    return None


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
    combos_txt, zwei, alle_combos = [], [], []
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
            alle_combos.append(karten)
            combos_txt.append(f"{art}: {' + '.join(karten)} (Spellbook-Tag {cb.get('bracketTag')}, speed {v.get('speed')})")
        sb_tag = res.get("bracketTag")
    except Exception as e:
        sb_tag = f"nicht erreichbar ({e})"
        print(f"!! Commander Spellbook nicht erreichbar ({e}) – Combos ungeprüft", file=sys.stderr)
    limit = GC_LIMIT.get(bracket, 3)
    gc_txt = f"{len(gc)}/{limit if limit < 99 else '∞'} Game Changer" + (f" ({', '.join(gc)})" if gc else "")
    zeile = (f"Bracket {bracket} – {gc_txt} – {'MLD: ' + ', '.join(mld) if mld else 'keine MLD'} – "
             f"{'Extra Turns: ' + ', '.join(xt) if xt else 'keine Extra Turns'} – "
             f"{'2-Karten-Combos: ' + '; '.join(zwei) if zwei else 'kein 2-Karten-Combo'}")
    return {"gc": gc, "mld": mld, "xt": xt, "zwei": zwei, "combos": combos_txt, "combo_karten": alle_combos,
            "sb_tag": sb_tag, "limit": limit, "zeile": zeile, "body": body}


def interaktion_nach_ziel(con, main):
    z, karten = Counter(), defaultdict(list)
    for q, c in main:
        for ziel in B.interaktion_ziele(sicht(con, c)):
            z[ziel] += q
            karten[ziel].append(c["name"])
    return z, karten


def legal_warnungen(cmdr, main):
    warn = []
    ci = set("".join(c["ci"] for _, c in cmdr))
    alle = cmdr + main
    total = sum(q for q, _ in alle)
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
    return warn


def pruefe_kurve_farben(cmdr, main, ci, warn):
    spells = [(q, c) for q, c in cmdr + main if "Land" not in front_type(c)]
    kurve = Counter()
    for q, c in spells:
        kurve[min(int(c["cmc"] or 0), 7)] += q
    n_sp = sum(q for q, _ in spells)
    avg = sum((c["cmc"] or 0) * q for q, c in spells) / n_sp if n_sp else 0
    print("\nKurve (Nichtländer inkl. Commander): " + " | ".join(f"{'7+' if k == 7 else k}: {kurve[k]}" for k in range(8))
          + f" | Ø MV {avg:.2f}")
    if avg > 3.5:
        warn.append(f"hohe Kurve (Ø {avg:.2f}) – mehr Ramp/Länder oder günstigere Karten")
    pip, schwer = Counter(), []
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


def pruefe_besitz(con, alle, main, ersetzt):
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
    plan = {}
    for q_, c in main:
        if basic(c):
            plan[c["name"]] = plan.get(c["name"], 0) + q_
    print()
    if plan:
        M.laender_tabelle(con, ersetzt, plan)


def cmd_pruefen(con, a):
    cmdr, main, unbekannt, hinweis = lies_deck(con, a.deck)
    ersetzt = auto_ersetzt(con, a)
    warn = ([hinweis] if hinweis else []) + (["nicht erkannte Karten: " + ", ".join(unbekannt)] if unbekannt else [])
    if not cmdr:
        print("Kein Commander erkannt – Commander nach einer Leerzeile ans Ende setzen.")
        return
    ci = set("".join(c["ci"] for _, c in cmdr))
    alle = cmdr + main
    print(f"Deck: {a.deck} | Commander: {cname_von(cmdr)} ({M.farbname(''.join(sorted(ci)))})"
          f" | {sum(q for q, _ in alle)} Karten")
    warn += legal_warnungen(cmdr, main)
    ak = archetyp_kontext(con, cmdr, main, ersetzt, a.archetyp)
    typen = deck_typen(profil_fuer(con, [c for _, c in cmdr]))
    zaehl, instant_int = zaehle_rollen(con, main, ak["ziel"], typen)
    print(f"\nRollen gegen Richtwert ({ak['name']}, {ak['herkunft']}; Archetyp-Richtwert vor Template; Doppelrollen zählen "
          f"mehrfach):")
    rows = []
    for k, n in ROLLEN:
        mn, ziel, quelle = ak["soll"].get(k, (None, None, "Info"))
        ist = zaehl[k]
        status = "–" if mn is None else ("ok" if ist >= mn else "ZU WENIG")
        if k == "land" and ist > 40:
            status = "VIELE"
        rows.append((n, ist, f"{mn}–{ziel}" if mn else "–", status, quelle))
        if mn and ist < mn:
            warn.append(f"{n}: {ist} (Minimum {mn}, Ziel {ziel}, {quelle})")
    rows.append(("davon Instant-Interaktion", instant_int, "≥ 4", "ok" if instant_int >= 4 else "WENIG", "Einschätzung"))
    if instant_int < 4:
        warn.append(f"nur {instant_int} Interaktion mit Instant-Tempo")
    M.table(rows, ["Rolle", "Anzahl", "Richtwert", "Status", "Richtwert-Quelle"])
    iz, _ = interaktion_nach_ziel(con, main)
    print("Interaktion nach Ziel: " + " · ".join(f"{z.capitalize()} {iz[z]} (≥ {n})" for z, n in INTERAKTION_ZIEL.items()))
    for z, n in INTERAKTION_ZIEL.items():
        if iz[z] < n:
            warn.append(f"wenig Interaktion gegen {z.capitalize()} ({iz[z]}, Richtwert ≥ {n})")
    ausgeschlossen = []
    for q, c in main:
        s = sicht(con, c)
        _, h = B.rollen_detail(s, typen)
        ausgeschlossen += [f"{c['name']} ({ROLLE_NAME[r]}: {t})" for r, t in h.items() if r != "tutor"]
        if B.zerstoert_plan(s, ak["ziel"]):
            warn.append(f"{c['name']}: symmetrischer Wipe im {ak['name']}-Deck – zerstört den eigenen Plan, "
                        "zählt nicht als Massen-Interaktion")
    if ausgeschlossen:
        print("Nicht mitgezählt (Qualitätsregel): " + "; ".join(ausgeschlossen))
    pruefe_kurve_farben(cmdr, main, ci, warn)
    bz = bracket_zeile(con, cmdr, main, a.bracket)
    print(f"\nBracket-Zeile: {bz['zeile']}")
    print(f"Commander Spellbook Einstufung: {bz['sb_tag']} ({SPELLBOOK.get(bz['sb_tag'], '?')})")
    for t in bz["combos"]:
        print("  Combo " + t)
    if len(bz["gc"]) > bz["limit"]:
        warn.append(f"{len(bz['gc'])} Game Changer – erlaubt in Bracket {a.bracket}: {bz['limit']}")
    if a.bracket <= 3 and (bz["mld"] or bz["xt"]):
        warn.append("MLD/Extra Turns in Bracket ≤ 3 prüfen")
    if a.bracket <= 3 and bz["zwei"]:
        warn.append("2-Karten-Combo vorhanden – in Bracket 3 nur, wenn nicht früh im Spiel möglich (Einschätzung nötig)")
    if a.combos_fehlend:
        combos_fehlend(con, bz["body"], alle)
    pruefe_besitz(con, alle, main, ersetzt)
    print("\nWARNUNGEN / WAS NOCH FEHLT:" if warn else "\nKeine Warnungen.")
    for w in warn:
        print(f"  - {w}")


def combos_fehlend(con, body, alle):
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
        print("!! find-my-combos nicht erreichbar:", e)


# ----------------------------------------------------------------- erklaerung, alternativen, oracle
def cmd_erklaerung(con, a):
    cmdr, main, unbekannt, _ = lies_deck(con, a.deck)
    if not cmdr:
        sys.exit("Kein Commander erkannt")
    cname = cname_von(cmdr)
    data, pfad = edhrec_commander(cname, a.bracket)
    edh = edh_karten(data)
    prof = profil_fuer(con, [c for _, c in cmdr], data)
    combo_teil = {}
    try:
        body = {"main": [{"card": M.front(c["name"]), "quantity": q} for q, c in main],
                "commanders": [{"card": M.front(c["name"]), "quantity": 1} for _, c in cmdr]}
        res = M.get_json("https://backend.commanderspellbook.com/find-my-combos", body)
        for v in (res.get("results", res) or {}).get("included", []):
            karten = [u["card"]["name"] for u in v["uses"]]
            for k in karten:
                combo_teil.setdefault(M.front(k), []).append(" + ".join(karten))
    except Exception as e:
        print(f"!! Commander Spellbook nicht erreichbar ({e}) – Spalte Combo-Teil leer", file=sys.stderr)
    ersetzt = auto_ersetzt(con, a)
    out = a.out or "erklaerung.csv"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"# Datenbasis für Kartenerklärungen – {cname} – EDHREC {pfad or '–'} – {time.strftime('%Y-%m-%d')}"])
        w.writerow(["Karte", "Rollen", "MV", "Typ", "Stärke", "Instant", "Bezug", "Gründe", "Synergie", "Inclusion",
                    "Combo-Teil", "Game Changer", "Status", "ab EUR", "Oracle-Text"])
        for q, c in [(q, c) for q, c in cmdr] + sorted(main, key=lambda x: x[1]["name"]):
            if basic(c):
                continue
            b = bewerte(con, prof, edh, c)
            bb, d, f = besitz(con, c["oid"], ersetzt)
            status = "frei" if f >= q else ("in anderem Deck" if bb else "kaufen")
            v = b["v"]
            w.writerow([c["name"], rollen_txt(B.rollen(b["sicht"])), c["cmc"], front_type(c), c["pt"] or "",
                        int(ist_instant(c)), b["bezug"], "; ".join(b["gruende"]),
                        "" if v.get("synergy") is None else f"{v['synergy'] * 100:+.0f}%",
                        pct(v.get("inclusion")), " | ".join(combo_teil.get(M.front(c["name"]), [])),
                        c["gc"], status, c["eur"], re.sub(r"\s+", " ", c["text"] or "")])
    print(f"Datenbasis für {len(main) + len(cmdr)} Einträge -> {out} (Standardländer ausgelassen)")


def cmd_alternativen(con, a):
    c = finde(con, a.karte)
    r = [x for x in rollen(con, c) if x not in ("tutor", "rekursion")] or rollen(con, c)
    farben = set((a.farben or c["ci"]).upper())
    print(f"{c['name']}: Rollen {', '.join(ROLLE_NAME[x] for x in r) or '–'} | MV {c['cmc']} | ab {c['eur']} €")
    if not r:
        print("Keine Funktionsrolle erkannt – Alternativen über Synergie/Thema suchen (synergie, kandidaten).")
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
def upgrade_kontext(con, a):
    """Deck, Commander, EDHREC, Profil, Archetyp und Bewertung jeder Deckkarte."""
    pfad, did = deck_aus_ref(con, a.deck)
    cmdr, main, unbekannt, _ = lies_deck(con, pfad)
    if not cmdr:
        sys.exit("Kein Commander erkannt")
    cname = cname_von(cmdr)
    data, epfad = edhrec_commander(cname, a.bracket)
    edh = edh_karten(data)
    them = edh_karten(edhrec_commander(cname, a.bracket, a.thema)[0]) if a.thema else {}
    prof = profil_fuer(con, [c for _, c in cmdr], data)
    ak = archetyp_kontext(con, cmdr, main, did, a.thema)
    typen = deck_typen(prof)
    deck = []
    for q, c in main:
        b = bewerte(con, prof, edh, c)
        deck.append({"c": c, "q": q, "rollen": rollen_im_plan(con, c, ak["ziel"], typen=typen), "b": b,
                     "pakete": karte_pakete(ak, c["oid"], typen)})
    zaehl, inst = zaehle_rollen(con, main, ak["ziel"], typen)
    return {"pfad": pfad, "did": did, "cmdr": cmdr, "main": main, "cname": cname, "ckurz": kurzname(cname),
            "ci": set("".join(c["ci"] for _, c in cmdr)), "edh": edh, "them": them, "epfad": epfad, "prof": prof,
            "ak": ak, "deck": deck, "zaehl": zaehl, "inst": inst, "soll": {k: v for k, v in ak["soll"].items()},
            "typen": typen,
            "im_deck": {c["oid"] for _, c in cmdr + main}}


def upgrade_kandidaten(con, ctx, a):
    """Freie Karten (Stufe 1: auch Käufe bis --max-preis) mit Bewertung; Karten, die den Plan zerstören, getrennt."""
    pool = {oid: "Sammlung" for (oid,) in con.execute("SELECT oracle_id FROM v_karten WHERE frei > 0")}
    if a.stufe:
        for n in list(ctx["edh"]) + list(ctx["them"]):
            oid = M.resolve_name(con, n)
            if oid and oid not in pool:
                pool[oid] = "EDHREC"
    zp, beim_deck = M.deck_zeitstempel(con, ctx["did"]) if ctx["did"] else (None, None)
    beim_deck = {r[3] for r in beim_deck or []}
    kand, stoert = [], []
    for oid, quelle in pool.items():
        if oid in ctx["im_deck"]:
            continue
        c = card(con, oid)
        if not c or c["legal"] != "legal" or not set(c["ci"]) <= ctx["ci"] or basic(c):
            continue
        bb, d, f = besitz(con, oid, ctx["did"])
        if not f and (not a.stufe or c["eur"] is None or c["eur"] > a.max_preis):
            continue
        b = bewerte(con, ctx["prof"], ctx["edh"], c)
        if B.zerstoert_plan(b["sicht"], ctx["ak"]["ziel"]):
            stoert.append(c["name"])
            continue
        vk = verkauf_geplant(con, oid) if f else ""
        k = {"c": c, "rollen": B.rollen(b["sicht"], ctx["typen"]), "b": b, "tv": edh_von(ctx["them"], c), "frei": f,
             "pakete": karte_pakete(ctx["ak"], oid, ctx["typen"]),
             "status": ("frei" + (f" · Verkauf geplant ({vk})" if vk else "") + (" ⚑" if oid in beim_deck else ""))
             if f else f"{c['eur']:.2f} €"}
        kand.append(k)
    kand.sort(key=lambda k: -k["b"]["wert"])
    return kand, stoert, (zp if beim_deck else None)


def kauf_alternativen(con, ctx):
    """Beste Kauf-Alternative je Rolle aus der EDHREC-Liste des Commanders (nur zur Abwägung neben freien Karten)."""
    out = {}
    for n, v in ctx["edh"].items():
        oid = M.resolve_name(con, n)
        if not oid or oid in ctx["im_deck"]:
            continue
        c = card(con, oid)
        if not c or c["legal"] != "legal" or not set(c["ci"]) <= ctx["ci"] or basic(c) or c["eur"] is None:
            continue
        if besitz(con, oid, ctx["did"])[2]:
            continue
        b = bewerte(con, ctx["prof"], ctx["edh"], c)
        if B.zerstoert_plan(b["sicht"], ctx["ak"]["ziel"]):
            continue
        for r in B.rollen(b["sicht"], ctx.get("typen", frozenset())):
            if r not in out or b["wert"] > out[r]["b"]["wert"]:
                out[r] = {"c": c, "b": b}
    return out


class Tausch:
    """Zustand der Tauschpaar-Suche: Rollen- und Paketzählung laufen mit, Sperren prüfen jedes Paar."""

    def __init__(self, ctx, abstand):
        self.ctx, self.abstand = ctx, abstand
        self.ist = Counter(ctx["zaehl"])
        self.paket = Counter({p["key"]: p["ist"] for p in ctx["ak"]["pakete"]})
        self.median = {p["key"]: p["median"] for p in ctx["ak"]["pakete"] if p["kern"] and p["median"] is not None}
        self.label = {p["key"]: p["label"] for p in ctx["ak"]["pakete"]}
        self.paare, self.raus_ok, self.rein_ok = [], set(), set()
        self.gesperrt, self.phase = {}, 1
        self.iz = Counter()
        for x in ctx["deck"]:
            for z in B.interaktion_ziele(x["b"]["sicht"]):
                self.iz[z] += x["q"]

    def sperre(self, x, k, streng=False):
        """Grund, warum x nicht für k das Deck verlassen darf – oder None (08, Raus-Sperren).
        streng (reine Wertverbesserung): Karten mit Commander-Bezug gehen nur für eine laut EDHREC klar stärkere Karte."""
        for p in x["pakete"]:
            m = self.median.get(p)
            if m is not None and self.paket[p] - 1 < int(m) and p not in k["pakete"]:
                return f"Kernpaket {self.label[p]} ({self.paket[p]}/{A_de(m)})"
        bx, bk = x["b"], k["b"]
        if bx["bezug"] >= B.BEZUG_SPERRE:
            gleich = bk["bezug"] >= bx["bezug"] and set(bk["gruende"]) & set(bx["gruende"])
            if streng:
                gleich = gleich and bk["edh"] is not None and bk["edh"] - bx["wert"] >= self.abstand
            if not gleich:
                return f"Commander-Bezug {de(bx['bezug'])} ({', '.join(bx['gruende'][:2])})"
        k_ziele = B.interaktion_ziele(k["b"]["sicht"])
        for z in B.interaktion_ziele(x["b"]["sicht"]):
            if z in INTERAKTION_ZIEL and z not in k_ziele and self.iz[z] - 1 < INTERAKTION_ZIEL[z]:
                return f"Interaktion gegen {z.capitalize()} an der Untergrenze ({self.iz[z]}/{INTERAKTION_ZIEL[z]})"
        soll = self.ctx["soll"]
        stufe = 1 if streng or self.phase >= 2 else 0      # Rollen auffüllen: bis Minimum · sonst: Ziel halten
        for r in x["rollen"]:
            if r in soll and self.ist[r] - 1 < soll[r][stufe]:
                was = "Minimum" if stufe == 0 else "Ziel"
                if r not in k["rollen"]:
                    return f"{ROLLE_NAME[r]} unter {was} ({self.ist[r]}/{soll[r][stufe]})"
                if B.funktionsgrad(k["b"]["sicht"], r) < B.funktionsgrad(x["b"]["sicht"], r) - 0.05:
                    return f"{ROLLE_NAME[r]} unter {was} (Ersatz erfüllt die Rolle schlechter)"
        return None

    def raus_fuer(self, k, schwach, rolle=None, paket=None, max_wert=None, streng=False):
        """Schwächste erlaubte Deckkarte für k. rolle/paket: Die Karte, die geht, darf diese Rolle bzw. dieses Paket
        nicht selbst tragen (sonst steigt die Zahl nicht). max_wert: höchstens so stark (Rolle füllen kostet wenig)."""
        land = "Land" in front_type(k["c"])
        for x in schwach:
            if x["c"]["oid"] in self.raus_ok or ("Land" in front_type(x["c"])) != land:
                continue
            if (rolle and rolle in x["rollen"]) or (paket and paket in x["pakete"]):
                continue
            if max_wert is not None and x["b"]["wert"] > max_wert:
                break
            g = self.sperre(x, k, streng)
            if g:
                self.gesperrt.setdefault(x["c"]["name"], g)
                continue
            return x
        return None

    def tausche(self, x, k, grund):
        vorher = Counter(self.ist)
        self.raus_ok.add(x["c"]["oid"])
        self.rein_ok.add(k["c"]["oid"])
        for r in x["rollen"]:
            self.ist[r] -= 1
        for r in k["rollen"]:
            self.ist[r] += 1
        for p in x["pakete"]:
            self.paket[p] -= 1
        for p in k["pakete"]:
            self.paket[p] += 1
        for z in B.interaktion_ziele(x["b"]["sicht"]):
            self.iz[z] -= 1
        for z in B.interaktion_ziele(k["b"]["sicht"]):
            self.iz[z] += 1
        self.paare.append((x, k, grund, vorher, Counter(self.ist)))


def kompromiss(k, rolle, kauf_alt):
    """Kompromiss-Stufe einer freien Karte für eine Rolle gegenüber der besten Kauf-Alternative."""
    alt = kauf_alt.get(rolle)
    grad = B.funktionsgrad(k["b"]["sicht"], rolle)
    stufe, q = B.kompromiss_stufe(k["b"]["wert"], grad, alt["b"]["wert"] if alt else None)
    satz = ""
    if alt:
        satz = B.aufpreis_satz({"wert": k["b"]["wert"], "cmc": k["c"]["cmc"], "instant": ist_instant(k["c"])},
                               {"name": alt["c"]["name"], "wert": alt["b"]["wert"], "quelle": alt["b"]["quelle"],
                                "eur": alt["c"]["eur"], "cmc": alt["c"]["cmc"], "instant": ist_instant(alt["c"])})
    return stufe, q, satz


def bilde_paare(ctx, kand, kauf_alt, a):
    t = Tausch(ctx, a.abstand)
    schwach = sorted((x for x in ctx["deck"] if not basic(x["c"])), key=lambda x: x["b"]["wert"])
    soll = ctx["soll"]
    # 1. Rollen unter dem Minimum – freie Karten zuerst (Rückfall vor Kauf), Kompromiss-Stufe je Karte
    for r, (mn, ziel, _) in sorted(soll.items(), key=lambda kv: t.ist[kv[0]] - kv[1][0]):
        if r == "land":
            continue
        passend = [k for k in kand if r in k["rollen"] and "Land" not in front_type(k["c"])]
        passend.sort(key=lambda k: (not k["frei"], -B.funktionsgrad(k["b"]["sicht"], r) * k["b"]["wert"] - k["b"]["wert"]))
        for k in passend:
            if t.ist[r] >= mn or len(t.paare) >= a.paare:
                break
            if k["c"]["oid"] in t.rein_ok:
                continue
            grad = B.funktionsgrad(k["b"]["sicht"], r)
            x = t.raus_fuer(k, schwach, rolle=r, max_wert=k["b"]["wert"] * grad + 0.1)
            if x:
                if k["frei"]:
                    k["kompromiss"] = kompromiss(k, r, kauf_alt)
                t.tausche(x, k, f"{ROLLE_NAME[r]} unter Minimum")
    # 2. Kernpakete unter dem Median (Rollen bleiben ab hier auf dem Ziel)
    t.phase = 2
    for key, m in sorted(t.median.items(), key=lambda kv: t.paket[kv[0]] - kv[1]):
        for k in [k for k in kand if key in k["pakete"]]:
            if t.paket[key] >= m or len(t.paare) >= a.paare:
                break
            if k["c"]["oid"] in t.rein_ok:
                continue
            x = t.raus_fuer(k, schwach, paket=key, max_wert=k["b"]["wert"])
            if x:
                t.tausche(x, k, f"Kernpaket {t.label[key]} unter Median")
    # 3. Wert verbessern (Länder nur gegen Länder und nur mit EDHREC-Wert)
    for k in kand:
        if len(t.paare) >= a.paare or k["c"]["oid"] in t.rein_ok:
            continue
        if "Land" in front_type(k["c"]) and k["b"]["edh"] is None:
            continue
        x = t.raus_fuer(k, schwach, streng=True)
        # nur geschätzter Wert (nicht auf der EDHREC-Seite) → doppelter Mindestabstand
        if x and k["b"]["wert"] - x["b"]["wert"] >= a.abstand * (2 if k["b"]["quelle"] != "EDHREC" else 1):
            t.tausche(x, k, "stärker laut EDHREC" if k["b"]["quelle"] == "EDHREC" else "stärkerer Oracle-Bezug")
    return t


def grund_raus(x, zaehl, soll, ckurz):
    """Datenbasis für „warum raus“: EDHREC beim Commander, Bezug, Rolle über Richtwert, keine Kernrolle."""
    teile = [edh_txt(x["b"]["v"], ckurz), f"Bezug {de(x['b']['bezug'])}" + (
        f" ({', '.join(x['b']['gruende'][:2])})" if x["b"]["gruende"] else "")]
    for r in x["rollen"]:
        if r in soll and zaehl[r] > soll[r][1]:
            teile.append(f"{ROLLE_NAME[r]} über Richtwert ({zaehl[r]}/{soll[r][1]})")
    if not x["rollen"]:
        teile.append("keine Kernrolle (nur Plan/Synergie)")
    return "; ".join(teile)


def grund_rein(k, vorher, nachher, soll, ckurz):
    """Datenbasis für „warum rein“: EDHREC, Bezug, gefüllte Rollen/Pakete, Thema-Synergie, Kompromiss-Stufe."""
    teile = [edh_txt(k["b"]["v"], ckurz)]
    if k["b"]["gruende"]:
        teile.append(f"Bezug {de(k['b']['bezug'])} ({', '.join(k['b']['gruende'][:3])})")
    if k.get("kompromiss"):
        teile.append(f"Kompromiss aus der Sammlung: {k['kompromiss'][0]}")
    if k.get("tv") and k["tv"].get("synergy") is not None:
        teile.append(f"Thema-Synergie {k['tv']['synergy'] * 100:+.0f} %")
    for r in k["rollen"]:
        if r in soll and vorher[r] < soll[r][0]:
            teile.append(f"füllt {ROLLE_NAME[r]} ({vorher[r]} → {nachher[r]}, Minimum {soll[r][0]})")
    if k["c"].get("gc"):
        teile.append("Game Changer")
    return "; ".join(teile)


def upgrade_ausgabe(con, ctx, kand, stoert, t, kauf_alt, zp, a):
    ak, soll, zaehl = ctx["ak"], ctx["soll"], ctx["zaehl"]
    print(f"Upgrade {os.path.basename(ctx['pfad'])} | {ctx['cname']} | Bracket {a.bracket} | Stufe {a.stufe}"
          + (f" (Käufe bis {a.max_preis:g} €)" if a.stufe else " (nur freie Karten)")
          + f" | {edh_zeile(ctx['epfad'])}" + (f" | Thema: {a.thema}" if a.thema else ""))
    print(f"Ziel-Archetyp {ak['name']} ({ak['herkunft']}) – Richtwerte: Archetyp vor Template")
    print("Rollen (99 ohne Commander): " + " · ".join(
        f"{ROLLE_NAME[k]} {zaehl[k]}/{soll[k][0]}{' ✗' if zaehl[k] < soll[k][0] else ''}" for k in KERN))
    print("Kernpakete: " + " · ".join(f"{p['label']} {p['ist']}/{A_de(p['median'])}"
                                      + (" ✗" if p["median"] and p["ist"] < p["median"] else "")
                                      for p in ak["pakete"] if p["kern"]))
    if a.voll:
        schwach = sorted((x for x in ctx["deck"] if not basic(x["c"])), key=lambda x: x["b"]["wert"])
        print("\nSchwächste Deckkarten (Wert = max(EDHREC, Oracle-Bezug); ≈ = geschätzt):")
        M.table([(x["c"]["name"], rollen_txt(x["rollen"]), wert_txt(x["b"]), de(x["b"]["bezug"]),
                  "; ".join(x["b"]["gruende"][:2]) or "–") for x in schwach[:a.paare]],
                ["Karte", "Rollen", "Wert", "Bezug", "warum"])
        print("\nBeste Kandidaten je Rolle (" + ("frei" if not a.stufe else "frei oder Kauf") + "):")
        for k_, n in ROLLEN[1:6] + [("plan", "Plan/Synergie")]:
            sel = [x for x in kand if (k_ in x["rollen"]) or (k_ == "plan" and not x["rollen"])]
            if sel:
                print(f"  {n}: " + "; ".join(f"{x['c']['name']} ({wert_txt(x['b'])}, {x['status']})" for x in sel[:6]))
    if t.gesperrt:
        print(f"\nRaus-Sperren ({len(t.gesperrt)} Deckkarten bleiben, Auszug): "
              + "; ".join(f"{n} – {g}" for n, g in list(t.gesperrt.items())[:8]))
    if stoert:
        print(f"Nicht vorgeschlagen – zerstört den eigenen Plan ({ak['name']}): {', '.join(stoert[:8])}")
    print(f"\nTauschpaare – Startpunkt, Claude prüft jedes Paar am Oracle-Text und am Spielplan ({len(t.paare)}):")
    M.table([(i + 1, x["c"]["name"], wert_txt(x["b"]), k["c"]["name"], wert_txt(k["b"]),
              f"{k['b']['wert'] - x['b']['wert']:+.2f}".replace(".", ","), k["status"], grund)
             for i, (x, k, grund, *_) in enumerate(t.paare)], ["#", "raus", "Wert", "rein", "Wert", "Δ", "Status", "Grund"])
    komp = [(x, k) for x, k, *_ in t.paare if k.get("kompromiss")]
    if komp:
        print("\nKompromiss-Stufen (freie Karte gegen die beste Kauf-Alternative der Rolle):")
        for x, k in komp:
            stufe, q, satz = k["kompromiss"]
            print(f"  {k['c']['name']}: {stufe} (Erfüllung {de(q)})" + (f" · {satz}" if satz else ""))
    kaeufe = [(x, k) for x, k, *_ in t.paare if not k["frei"]]
    if kaeufe:
        print("\nKäufe (Wirkung 1–5, Klasse A–D nach 01, Abschnitt 6; € je Wertpunkt):")
        gc_n = sum(1 for _, c in ctx["cmdr"] + ctx["main"] if c["gc"])
        for x, k in kaeufe:
            fuellt = any(r in soll and zaehl[r] < soll[r][0] for r in k["rollen"])
            wk = B.wirkung(k["b"]["wert"], fuellt)
            gc_zu = bool(k["c"]["gc"]) and gc_n >= GC_LIMIT.get(a.bracket, 3)
            delta = max(k["b"]["wert"] - x["b"]["wert"], 0.01)
            print(f"  {k['c']['name']}: {k['c']['eur']:.2f} € · Wirkung {wk} · Klasse {B.klasse(wk, k['c']['eur'], gc_zu)}"
                  f" · {de(k['c']['eur'] / delta)} € je Wertpunkt (Δ {de(delta)})")
    if a.voll:
        rueck = [k for k in kand if k["frei"] and k["b"]["wert"] < 0.10 and k["rollen"]]
        if rueck:
            print("\nFreie Karten mit Rolle, aber geringem Wert (Rückfall-Pool – am Oracle-Text prüfen):")
            for k_, n in ROLLEN:
                sel = [x["c"]["name"] for x in rueck if k_ in x["rollen"]]
                if sel:
                    print(f"  {n}: " + ", ".join(sel[:10]) + (f" (+{len(sel) - 10})" if len(sel) > 10 else ""))
    print("\nWarum raus / warum rein (Datenbasis – im Vorschlag und im Fazit in einen Satz aus dem Oracle-Text fassen):")
    for i, (x, k, _, vorher, nachher) in enumerate(t.paare):
        print(f"  {i + 1}. raus {x['c']['name']}: {grund_raus(x, vorher, soll, ctx['ckurz'])}")
        print(f"     rein {k['c']['name']}: {grund_rein(k, vorher, nachher, soll, ctx['ckurz'])}")
    if zp:
        print(f"⚑ = frei, aber zusammen mit diesem Deck erfasst ({zp[:16]}): liegt vielleicht schon beim Deck – "
              "vor dem Vorschlag mit dem Nutzer klären (mtg_db.py exemplare <deck>).")
    gc_deck = [c["name"] for _, c in ctx["cmdr"] + ctx["main"] if c["gc"]]
    gc_neu = [k["c"]["name"] for _, k, *_ in t.paare if k["c"]["gc"]]
    gc_frei = [k["c"]["name"] for k in kand if k["c"]["gc"]][:8]
    limit = GC_LIMIT.get(a.bracket, 3)
    print(f"\nGame Changer: im Deck {len(gc_deck)}/{limit if limit < 99 else '∞'} ({', '.join(gc_deck) or '–'})"
          + (f" | durch die Paare +{len(gc_neu)} ({', '.join(gc_neu)})" if gc_neu else "")
          + (f" | verfügbar: {', '.join(gc_frei)}" if gc_frei else ""))
    if len(gc_deck) + len(gc_neu) > limit:
        print(f"  !! mehr als {limit} Game Changer – Paare anpassen")
    print("\nOracle-Text der vorgeschlagenen Karten (Pflicht: Beschreibung im Vorschlag nur hieraus):\n")
    print("\n\n".join(oracle_block(con, k["c"]) for _, k, *_ in t.paare))
    print("\nOracle-Text der Karten, die raus sollen (auch die Raus-Begründung nur hieraus):\n")
    print("\n\n".join(oracle_block(con, x["c"]) for x, *_ in t.paare))


def upgrade_dateien(ctx, kand, t, a):
    pfad_paare = os.path.splitext(a.out or "upgrade.csv")[0] + "_paare.txt"
    os.makedirs(os.path.dirname(pfad_paare) or ".", exist_ok=True)
    with open(pfad_paare, "w", encoding="utf-8") as fh:
        fh.write("# Tauschpaare „Raus -> Rein“ (eine Seite darf leer sein) – für deckbau.py fazit --paare\n")
        fh.writelines(f"{x['c']['name']} -> {k['c']['name']}"
                      + (f"  # Kompromiss: {k['kompromiss'][0]}" if k.get("kompromiss") else "") + "\n"
                      for x, k, *_ in t.paare)
    out = a.out or "upgrade.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([f"# Upgrade {ctx['cname']} – Stufe {a.stufe} – EDHREC {ctx['epfad'] or '–'} – {time.strftime('%Y-%m-%d')}"])
        w.writerow(["Art", "Karte", "Rollen", "Wert", "Wert-Quelle", "Bezug", "Gründe", "Inclusion", "Synergie",
                    "Thema-Synergie", "Kernpakete", "Raus-Sperre", "Status", "MV", "Typ", "Oracle-Text"])
        for x in sorted(ctx["deck"], key=lambda x: x["b"]["wert"]):
            b = x["b"]
            w.writerow(["Deck", x["c"]["name"], rollen_txt(x["rollen"]), b["wert"], b["quelle"], b["bezug"],
                        "; ".join(b["gruende"]), b["v"].get("inclusion"), b["v"].get("synergy"), "",
                        ", ".join(x["pakete"]), t.gesperrt.get(x["c"]["name"], ""), "im Deck", x["c"]["cmc"],
                        front_type(x["c"]), re.sub(r"\s+", " ", x["c"]["text"] or "")])
        for k in kand:
            b = k["b"]
            w.writerow(["Kandidat", k["c"]["name"], rollen_txt(k["rollen"]), b["wert"], b["quelle"], b["bezug"],
                        "; ".join(b["gruende"]), b["v"].get("inclusion"), b["v"].get("synergy"), k["tv"].get("synergy"),
                        ", ".join(k["pakete"]), "", k["status"], k["c"]["cmc"], front_type(k["c"]),
                        re.sub(r"\s+", " ", k["c"]["text"] or "")])
    print(f"\nPaare -> {pfad_paare} | alle Deckkarten und {len(kand)} Kandidaten -> {out}")


def cmd_upgrade(con, a):
    ctx = upgrade_kontext(con, a)
    kand, stoert, zp = upgrade_kandidaten(con, ctx, a)
    kauf_alt = kauf_alternativen(con, ctx)
    t = bilde_paare(ctx, kand, kauf_alt, a)
    upgrade_ausgabe(con, ctx, kand, stoert, t, kauf_alt, zp, a)
    upgrade_dateien(ctx, kand, t, a)


# ----------------------------------------------------------------- Abnahme (Bracket-3-Definition of Done)
SIEGWEGE = [
    # (Name, Prüfung je Karte, Mindestanzahl)
    ("Kampf / Go-wide", lambda s: bool(s["t"] & {"overrun", "anthem", "power-boost-to-all", "extra-combat-phase"}), 3),
    ("Drain / Aristokraten", lambda s: bool(s["t"] & {"opponent-loses-life", "drain-life", "blood-artist-ability",
                                                       "burn-player-each"}), 3),
    ("Commander-Schaden / Voltron", lambda s: any(x in s["typ"] for x in ("Equipment", "Aura"))
     and bool(s["t"] & {"gives-evasion", "gives-double-strike", "power-boost"}), 4),
    ("Große Kreaturen", lambda s: B.ist_kreatur(s) and _staerke(s) >= 6, 5),
    ("Direktschaden", lambda s: "burn-player" in s["t"] and "repeatable-removal" in s["t"], 3),
    ("Alternativer Sieg", lambda s: "alternate-win-condition" in s["t"], 1),
    ("Mill", lambda s: bool(s["t"] & {"mill-opponent", "mill-each"}), 4),
]


def _staerke(s):
    m = re.match(r"(\d+)/", s.get("pt") or "")
    return int(m.group(1)) if m else 0


def siegwege(con, cmdr, main, combos):
    out = []
    karten = [(c, sicht(con, c)) for _, c in cmdr + main]
    for name, fn, mindest in SIEGWEGE:
        treffer = [c["name"] for c, s in karten if fn(s)]
        if len(treffer) >= mindest:
            out.append((name, treffer))
    if combos:
        out.append(("Combo (Commander Spellbook)", [" + ".join(k) for k in combos[:3]]))
    return out


def staerke_index(teile):
    """Ein Wert 0–1 aus Rollen-Erfüllung, Kernpaket-Deckung, Ø Wert der Spielkarten (w/(w+0,5)), Ø Commander-Bezug und
    Simulation – gleich gewichtet. Vergleichsgröße für „messbar stärker“, kein absolutes Urteil."""
    return round(sum(teile.values()) / len(teile), 3)


def abnahme_daten(con, pfad, bracket=3, archetyp=None, n=5000, did=None):
    """Alle Größen der Abnahme für eine Deckdatei (wird auch von fazit und gegentest genutzt)."""
    import simulation as S
    cmdr, main, unbekannt, _ = lies_deck(con, pfad)
    if not cmdr:
        sys.exit(f"{pfad}: kein Commander erkannt")
    cname = cname_von(cmdr)
    data, epfad = edhrec_commander(cname, bracket)
    edh = edh_karten(data)
    prof = profil_fuer(con, [c for _, c in cmdr], data)
    ak = archetyp_kontext(con, cmdr, main, did, archetyp)
    zaehl, inst = zaehle_rollen(con, main, ak["ziel"])
    bz = bracket_zeile(con, cmdr, main, bracket)
    iz, iz_karten = interaktion_nach_ziel(con, main)
    sw = siegwege(con, cmdr, main, bz["combo_karten"])
    deck, cmd, _ = S.aus_deck(con, pfad)
    sim = S.simuliere(deck, cmd, n=n, seed=1)
    spiel = [(q, c) for q, c in main if "Land" not in front_type(c)]
    werte = [bewerte(con, prof, edh, c) for _, c in spiel]
    n_sp = sum(q for q, _ in spiel) or 1
    o_wert = sum(b["wert"] * q for b, (q, _) in zip(werte, spiel)) / n_sp
    o_bezug = sum(b["bezug"] * q for b, (q, _) in zip(werte, spiel)) / n_sp
    rollen_erf = sum(min(zaehl[k] / ak["soll"][k][0], 1) for k in KERN) / len(KERN)
    deckung = ak["A"].deckung(ak["z"], ak["richt"], ak["ziel"])
    sim_score = (sim["landdrops_bis_4"] + sim.get("commander_plus1", 1) + (1 - sim["fehlstart"])
                 + (1 - sim.get("farbproblem", 0))) / 4
    teile = {"rollen": rollen_erf, "pakete": deckung, "wert": o_wert / (o_wert + 0.5), "bezug": o_bezug,
             "simulation": sim_score}
    return {"pfad": pfad, "cmdr": cmdr, "main": main, "cname": cname, "unbekannt": unbekannt, "ak": ak,
            "zaehl": zaehl, "inst": inst, "bz": bz, "iz": iz, "iz_karten": iz_karten, "siegwege": sw, "sim": sim,
            "o_wert": o_wert, "o_bezug": o_bezug, "teile": teile, "index": staerke_index(teile), "epfad": epfad,
            "legal": legal_warnungen(cmdr, main), "bracket": bracket}


def abnahme_punkte(d, basis=None):
    """-> Liste (Prüfpunkt, Ergebnis, Status ✓/✗/offen/–) – Definition of Done aus 08, Abschnitt 8a."""
    import simulation as S
    ak, z, bz = d["ak"], d["zaehl"], d["bz"]
    pk = []
    pk.append(("Deck legal (100 Karten, Singleton, Farbidentität, Banlist)",
               "; ".join(d["legal"]) or "ok", "✗" if d["legal"] else "✓"))
    hart = []
    if len(bz["gc"]) > bz["limit"]:
        hart.append(f"{len(bz['gc'])} Game Changer (erlaubt {bz['limit']})")
    if bz["mld"]:
        hart.append("MLD: " + ", ".join(bz["mld"]))
    if bz["xt"]:
        hart.append("Extra Turns: " + ", ".join(bz["xt"]))
    status = "✗" if hart else ("offen" if bz["zwei"] else "✓")
    pk.append(("Harte Grenzen (Game Changer, MLD, Extra-Turn-Ketten, frühe 2-Karten-Combos)",
               "; ".join(hart) or (f"2-Karten-Combo prüfen (früh?): {'; '.join(bz['zwei'])}" if bz["zwei"] else
                                   f"{len(bz['gc'])}/{bz['limit']} Game Changer, keine MLD/Extra Turns/2-Karten-Combos"),
               status))
    unter = [f"{ROLLE_NAME[k]} {z[k]}/{ak['soll'][k][0]}" for k in KERN if z[k] < ak["soll"][k][0]]
    pk.append((f"Rollen auf Richtwert ({ak['soll']['ramp'][2]})", "; ".join(unter) or "alle Rollen ≥ Minimum",
               "✗" if unter else "✓"))
    iz = d["iz"]
    fehlt = [f"{zl.capitalize()} {iz[zl]}/{n}" for zl, n in INTERAKTION_ZIEL.items() if iz[zl] < n]
    pk.append(("Interaktion nach Ziel (Kreatur ≥ 5, Artefakt ≥ 2, Verzauberung ≥ 2, Friedhof ≥ 1)",
               "; ".join(fehlt) or " · ".join(f"{zl.capitalize()} {iz[zl]}" for zl in INTERAKTION_ZIEL),
               "✗" if fehlt else "✓"))
    sw = d["siegwege"]
    pk.append(("Mindestens zwei Siegwege mit konkreten Karten",
               " · ".join(f"{n}: {', '.join(k[:4])}{' …' if len(k) > 4 else ''}" for n, k in sw) or "keiner erkannt",
               "✓" if len(sw) >= 2 else "✗"))
    kp = [p for p in ak["pakete"] if p["kern"] and p["median"]]
    unter_p = [f"{p['label']} {p['ist']}/{A_de(p['median'])}" for p in kp if p["ist"] < 0.8 * p["median"]]
    pk.append((f"Kernpakete ≥ 80 % des Medians ({ak['name']})", "; ".join(unter_p) or "alle Kernpakete ≥ 80 %",
               "✗" if unter_p else "✓"))
    sim_b = S.bewerte(d["sim"])
    fail = [f"{t} {w * 100:.0f} % ({s})" for t, w, s, ok in sim_b if not ok]
    pk.append(("Konsistenz-Simulation (vorläufige Schwellen)", "; ".join(fail) or "alle Schwellen erfüllt",
               "✗" if fail else "✓"))
    if basis:
        besser = d["index"] > basis["index"] + 0.005
        pk.append(("Messbar stärker als der Ausgangsstand",
                   f"Stärke-Index {de(basis['index'], 3)} → {de(d['index'], 3)} ("
                   + ", ".join(f"{k} {de(basis['teile'][k], 2)}→{de(v, 2)}" for k, v in d["teile"].items()) + ")",
                   "✓" if besser else "✗"))
    else:
        pk.append(("Messbar stärker als der Ausgangsstand", "keine Basis angegeben (--basis)", "–"))
    return pk


def urteil(pk):
    if any(s == "✗" for _, _, s in pk):
        return f"NICHT BESTANDEN ({sum(1 for _, _, s in pk if s == '✗')} Punkte offen)"
    if any(s == "offen" for _, _, s in pk):
        return "BEDINGT – Einschätzung nötig (offene Punkte)"
    return "BESTANDEN"


def cmd_abnahme(con, a):
    pfad, did = deck_aus_ref(con, a.deck)
    basis = None
    if a.basis:                       # Basis zuerst: ihr Ziel-Archetyp (Strategie im Register) gilt auch für den Entwurf
        bpfad, bdid = deck_aus_ref(con, a.basis)
        basis = abnahme_daten(con, bpfad, a.bracket, a.archetyp, a.n, bdid)
    d = abnahme_daten(con, pfad, a.bracket, a.archetyp or (basis["ak"]["ziel"] if basis else None), a.n, did)
    pk = abnahme_punkte(d, basis)
    print(f"Bracket-{a.bracket}-Abnahme {os.path.basename(pfad)} | {d['cname']} | Ziel-Archetyp {d['ak']['name']} "
          f"({d['ak']['herkunft']}) | {edh_zeile(d['epfad'])}")
    for name, erg, st in pk:
        print(f"  {st:5} {name}\n        {erg}")
    print(f"\nUrteil: {urteil(pk)} · Stärke-Index {de(d['index'], 3)}"
          + (f" (Basis {de(basis['index'], 3)})" if basis else ""))
    print("Schwellen für Interaktion und Simulation sind vorläufig (Einschätzung, 08 Abschnitt 8a) – nach weiteren "
          "Abnahmen nachschärfen.")


# ----------------------------------------------------------------- Gegentest (Projekt gegen Konkurrenz-Skill)
def kosten_fuer_uns(con, cmdr, main):
    frei = anderes = 0
    kauf, kauf_eur = [], 0.0
    for q, c in cmdr + main:
        if basic(c):
            continue
        b, d, f = besitz(con, c["oid"])
        if f >= q:
            frei += q
        elif b:
            anderes += q
        else:
            kauf.append(c["name"])
            kauf_eur += (c["eur"] or 0) * q
    return frei, anderes, kauf, kauf_eur


GEGENTEST_PROMPT = """Du bist ein unabhängiger Deckbauer und arbeitest ausschließlich nach der Anleitung des Skills
„{skill}“ (Datei: {skill_pfad}). Lies die Anleitung vollständig und folge ihr für einen Neubau („build from scratch“).
Du hast keinen Zugriff auf andere Projekte oder Dateien außer der Skill-Anleitung, ihren Skripten und diesem Auftrag.

Vorgaben des Nutzers (beantworten alle Fragen des Interviews – stelle keine Rückfragen):
- Commander: {commander}
- Format: Commander, Ziel-Bracket {bracket} (offizielle Brackets: max. 3 Game Changer in Bracket 3, keine MLD,
  keine Extra-Turn-Ketten, keine 2-Karten-Combos im frühen Spiel)
- Budget: {budget}
- Thema/Strategie: {thema}
- Spielstil: {stil}
- Spielgruppe: 3–5 Spieler, Casual
{sammlung}
Ergebnis: die fertige 100-Karten-Liste im Moxfield-Format (eine Karte je Zeile „1 Kartenname“, Commander nach einer
Leerzeile am Ende) als Datei {ausgabe}, dazu in 5–10 Zeilen: Spielplan, Siegwege, wichtigste Entscheidungen.
Preise des Skills dürfen in USD sein. Halte dich an die Skill-Anleitung, nicht an eigene Vorlieben."""


def cmd_gegentest(con, a):
    if a.prompt:
        if not a.commander:
            sys.exit("--prompt braucht --commander")
        sammlung = (f"- Sammlung: Bevorzuge Karten aus dieser Liste freier Karten (eine Karte je Zeile): {a.mit_sammlung}"
                    if a.mit_sammlung else "- Sammlung: keine Vorgabe (Kartenpool ohne Beschränkung)")
        print(GEGENTEST_PROMPT.format(skill=a.skill, skill_pfad=a.skill_pfad, commander=a.commander,
                                      bracket=a.bracket, budget=a.budget, thema=a.thema or "nach Commander-Text",
                                      stil=a.stil, sammlung=sammlung, ausgabe=a.ausgabe))
        return
    if not (a.a and a.b):
        sys.exit("zwei Decks angeben (gegentest <A> <B>) oder --prompt")
    namen = (a.namen or "A (Projekt),B (Konkurrenz)").split(",")
    pa, da = deck_aus_ref(con, a.a)
    pb, db_ = deck_aus_ref(con, a.b)
    d1 = abnahme_daten(con, pa, a.bracket, a.archetyp, a.n, da)
    d2 = abnahme_daten(con, pb, a.bracket, d1["ak"]["ziel"], a.n, db_)
    pk1, pk2 = abnahme_punkte(d1), abnahme_punkte(d2)
    print(f"Gegentest | {namen[0]}: {os.path.basename(pa)} · {namen[1]}: {os.path.basename(pb)} | "
          f"Commander {d1['cname']}" + ("" if d1["cname"] == d2["cname"] else f" bzw. {d2['cname']}")
          + f" | Ziel-Archetyp {d1['ak']['name']} | Bracket {a.bracket}")
    zeilen = []
    for (n1, e1, s1), (_, e2, s2) in zip(pk1, pk2):
        zeilen.append((n1.split(" (")[0], s1, s2))
    M.table(zeilen, ["Abnahme-Punkt", namen[0], namen[1]])
    s1, s2 = d1["sim"], d2["sim"]
    pctd = lambda x: f"{x * 100:.0f} %"
    vergl = [("Stärke-Index", de(d1["index"], 3), de(d2["index"], 3)),
             ("Ø Wert der Spielkarten", de(d1["o_wert"]), de(d2["o_wert"])),
             ("Ø Commander-Bezug", de(d1["o_bezug"]), de(d2["o_bezug"])),
             ("Kernpaket-Deckung", pctd(d1["teile"]["pakete"]), pctd(d2["teile"]["pakete"])),
             ("Rollen-Erfüllung", pctd(d1["teile"]["rollen"]), pctd(d2["teile"]["rollen"])),
             ("Siegwege", str(len(d1["siegwege"])), str(len(d2["siegwege"]))),
             ("Landdrops Zug 1–4", pctd(s1["landdrops_bis_4"]), pctd(s2["landdrops_bis_4"])),
             ("Commander +1 Zug", pctd(s1.get("commander_plus1", 0)), pctd(s2.get("commander_plus1", 0))),
             ("Game Changer", str(len(d1["bz"]["gc"])), str(len(d2["bz"]["gc"])))]
    for k in KERN:
        vergl.append((ROLLE_NAME[k], str(d1["zaehl"][k]), str(d2["zaehl"][k])))
    f1, a1, k1, e1 = kosten_fuer_uns(con, d1["cmdr"], d1["main"])
    f2, a2, k2, e2 = kosten_fuer_uns(con, d2["cmdr"], d2["main"])
    vergl += [("frei in der Sammlung", str(f1), str(f2)), ("in anderen Decks", str(a1), str(a2)),
              ("Kauf (Karten / ab €)", f"{len(k1)} / {de(e1)} €", f"{len(k2)} / {de(e2)} €")]
    print()
    M.table(vergl, ["Kennzahl", namen[0], namen[1]])
    o1 = {c["oid"]: c for _, c in d1["main"]}
    o2 = {c["oid"]: c for _, c in d2["main"]}
    gemeinsam = set(o1) & set(o2)
    print(f"\nÜberschneidung: {len(gemeinsam)} gemeinsame Karten · nur {namen[0]}: {len(set(o1) - set(o2))} · "
          f"nur {namen[1]}: {len(set(o2) - set(o1))}")
    data, _ = edhrec_commander(d1["cname"], a.bracket)
    edh, prof = edh_karten(data), profil_fuer(con, [c for _, c in d1["cmdr"]], data)
    for titel, nur in ((f"Stärkste Karten nur bei {namen[1]}", set(o2) - set(o1)),
                       (f"Stärkste Karten nur bei {namen[0]}", set(o1) - set(o2))):
        quelle = o2 if namen[1] in titel else o1
        best = sorted(((bewerte(con, prof, edh, quelle[o]), quelle[o]) for o in nur if "Land" not in front_type(quelle[o])),
                      key=lambda x: -x[0]["wert"])[:10]
        print(f"{titel}: " + "; ".join(f"{c['name']} ({wert_txt(b)}{', frei' if besitz(con, c['oid'])[2] else ''})"
                                       for b, c in best))
    print(f"\nUrteil Abnahme: {namen[0]} {urteil(pk1)} · {namen[1]} {urteil(pk2)}")
    print("Datenbasis für Claudes Bewertung – Unterschiede am Oracle-Text und Spielplan prüfen; Preise des Konkurrenz-Skills "
          "sind USD, hier zählt EUR (Scryfall/Cardmarket).")


# ----------------------------------------------------------------- verkauf
NOT_SCHWELLE = 0.10    # EDHREC-Wert, ab dem eine freie Karte als Upgrade-Kandidat eines Decks gilt


def cmd_verkauf(con, a):
    """Verkaufsprüfung: freie Exemplare ab --min-preis gegen alle Decks prüfen.
    Behalten: Upgrade-Kandidat eines Commander-Decks (EDHREC-Wert ≥ 0,10 oder Oracle-Bezug ≥ 0,5; je Deck ein Exemplar).
    Kat. 2 (Verkauf möglich, mit Hinweis): füllt eine Rolle unter Minimum (Kompromiss) · Game Changer · Playset-Ergänzung
    eines 60-Karten-Decks · ⚑ zusammen mit einem Deck erfasst. Kat. 1: alles andere."""
    stand = dict(con.execute("SELECT key, value FROM meta").fetchall()).get("bulk_default_cards", "")[:10]
    cdecks, kdecks = verkauf_decks(con, a)
    flags = {d["flag"]: d["kurz"] for d in cdecks + kdecks if d["flag"]}
    limit = GC_LIMIT.get(a.bracket, 3)
    ex = con.execute("""SELECT e.oracle_id, e.name, UPPER(e.set_code), e.cn, e.finish, e.lang, e.modified,
        COALESCE(e.verkauf, ''), CASE e.finish WHEN 'foil' THEN COALESCE(p.eur_foil, p.eur)
        WHEN 'etched' THEN COALESCE(p.eur_etched, p.eur) ELSE COALESCE(p.eur, p.eur_foil) END
        FROM exemplare e LEFT JOIN prints p ON p.set_code=e.set_code AND p.cn=e.cn AND p.oracle_id=e.oracle_id
        AND p.lang='en' WHERE e.deck_id IS NULL AND e.idee IS NULL ORDER BY e.name, e.nr""").fetchall()
    je = defaultdict(list)
    for r in ex:
        je[r[0]].append(r)
    kat1, kat2, halten = [], [], []
    for oid, kopien in je.items():
        c = card(con, oid)
        if not c or basic(c):
            continue
        preis = lambda r: r[8] if r[8] is not None else (c["eur"] or 0)
        kopien = sorted(kopien, key=lambda r: -preis(r))
        if preis(kopien[0]) < a.min_preis:
            continue
        verkauf_einordnen(con, c, oid, kopien, preis, cdecks, kdecks, flags, limit, kat1, kat2, halten)
    verkauf_ausgabe(kat1, kat2, halten, stand, a)


def verkauf_decks(con, a):
    cdecks, kdecks = [], []
    for did, kurz, fmt in con.execute("SELECT deck_id, kurz, format FROM decks ORDER BY kurz").fetchall():
        zp, beim = M.deck_zeitstempel(con, did)
        flag = zp if beim else None
        if fmt == "commander":
            pfad, _ = deck_aus_ref(con, kurz)
            cmdr, main, _, _ = lies_deck(con, pfad)
            if not cmdr:
                continue
            data, _ = edhrec_commander(cname_von(cmdr), a.bracket)
            ak = archetyp_kontext(con, cmdr, main, did)
            zaehl, _ = zaehle_rollen(con, main, ak["ziel"])
            unter = {r for r in KERN if zaehl[r] < ak["soll"][r][0]}
            cdecks.append(dict(did=did, kurz=kurz, ci=set("".join(c["ci"] for _, c in cmdr)), edh=edh_karten(data),
                               prof=profil_fuer(con, [c for _, c in cmdr], data), unter=unter,
                               gc=sum(1 for _, c in cmdr + main if c["gc"]), flag=flag, ziel=ak["ziel"]))
        else:
            q = Counter()
            for oid, n in con.execute("SELECT oracle_id, qty FROM deck_cards WHERE deck_id=? AND board IN"
                                      " ('main','sideboard') AND oracle_id IS NOT NULL", (did,)):
                q[oid] += n
            kdecks.append(dict(did=did, kurz=kurz, fmt=fmt, q=q, flag=flag))
    return cdecks, kdecks


def verkauf_einordnen(con, c, oid, kopien, preis, cdecks, kdecks, flags, limit, kat1, kat2, halten):
    r_c = rollen(con, c)
    behalten, notl = [], defaultdict(list)
    for d in cdecks:
        if c["legal"] != "legal" or not set(c["ci"]) <= d["ci"]:
            continue
        b = bewerte(con, d["prof"], d["edh"], c)
        if B.zerstoert_plan(b["sicht"], d["ziel"]):
            continue
        if (b["edh"] or 0) >= NOT_SCHWELLE or b["bezug"] >= B.BEZUG_SPERRE:
            behalten.append(f"Upgrade-Kandidat {d['kurz']} ("
                            + (f"{pct(b['v'].get('inclusion'))}, Synergie {(b['v'].get('synergy') or 0) * 100:+.0f} %"
                               if b["edh"] is not None else f"Bezug {de(b['bezug'])}: {', '.join(b['gruende'][:2])}") + ")")
        elif d["unter"] & set(r_c):
            for x in r_c:
                if x in d["unter"]:
                    notl[ROLLE_NAME[x]].append(d["kurz"])
    playset = []
    for d in kdecks:
        n = d["q"].get(oid, 0)
        legal = con.execute(f"SELECT legal_{d['fmt']} FROM cards WHERE oracle_id=?", (oid,)).fetchone() \
            if d["fmt"] in ("standard", "pioneer", "modern", "legacy", "vintage", "pauper") else None
        if 0 < n < 4 and legal and legal[0] == "legal":
            playset += [f"Playset-Ergänzung {d['kurz']} (im Deck {n}×)"] * (4 - n)
    gc_txt = ""
    if c["gc"]:
        platz = [d["kurz"] for d in cdecks if set(c["ci"]) <= d["ci"] and d["gc"] < limit]
        gc_txt = "Game Changer" + (f" – Platz in {', '.join(platz)}" if platz else "")
    for i, r in enumerate(kopien):
        sprache = {"de": "DE", "en": "EN"}.get(r[5], (r[5] or "").upper()) + (" Foil" if r[4] == "foil" else "")
        z = dict(name=r[1], druck=f"{r[2]} {r[3]}", set=r[2], cn=r[3], sprache=sprache, preis=preis(r),
                 verkauf=r[7], grund="")
        if i < len(behalten):
            z["grund"] = behalten[i] + (f" · trotzdem Verkauf geplant ({r[7]}) – mit dem Nutzer klären" if r[7] else "")
            halten.append(z)
            continue
        j = i - len(behalten)
        hin = []
        if j < len(playset):
            hin.append(playset[j])
        if r[6] in flags:
            hin.insert(0, f"⚑ mit {flags[r[6]]} erfasst")
        if gc_txt:
            hin.append(gc_txt)
        hin += [f"Kompromiss für {rolle} ({', '.join(ds)})" for rolle, ds in notl.items()]
        if r[7]:
            hin.append(f"Verkauf geplant ({r[7]})")
        z["grund"] = " · ".join(hin)
        (kat2 if any(not h.startswith("Verkauf geplant") for h in hin) else kat1).append(z)


def verkauf_ausgabe(kat1, kat2, halten, stand, a):
    summe = lambda l: sum(z["preis"] for z in l)
    eur = lambda x: f"{x:.2f}".replace(".", ",") + " €"
    for titel, l in (("Kat. 1 – ohne Bedenken verkaufen", kat1), ("Kat. 2 – Verkauf möglich, mit Hinweis", kat2),
                     ("Behalten – wird gebraucht", halten)):
        print(f"\n{titel}: {len(l)} Karten · {eur(summe(l))}")
        if l:
            M.table([(z["name"], z["druck"], z["sprache"], eur(z["preis"]), z["grund"])
                     for z in sorted(l, key=lambda z: -z["preis"])], ["Karte", "Druck", "Sprache", "Preis", "Hinweis"])
    print(f"\nPreise: eigener Druck, Scryfall-EUR (Quelle Cardmarket), Stand {stand} · deutsche Exemplare zum Preis "
          f"der englischen Version – auf Cardmarket meist etwas darunter; Gebühren und Versand gehen ab.")
    print("Kompromiss = Rolle im Deck unter Minimum, Karte füllt sie (Rückfall vor Kauf, 08 Grundsatz 14) · "
          "⚑ = zur selben Zeit wie das Deck erfasst, liegt vielleicht beim Deck – vor dem Verkauf nachsehen.")
    print("Kat. 2 und Behalten sind Datenbasis – jede Karte vor dem Vorschlag am Oracle-Text und Spielplan prüfen.")
    out = a.out or "out/verkauf.txt"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(f"# titel: Verkaufsliste Cardmarket\n# deck: Sammlung (freie Karten) ab {eur(a.min_preis)}\n"
                 f"# datum: {time.strftime('%d.%m.%Y')}\n# preise: Cardmarket über Scryfall, Stand {stand}\n")
        for k, l in (("K1", kat1), ("K2", kat2)):
            for z in sorted(l, key=lambda z: z["name"]):
                fh.write(f"{k} 1 {z['name']} ({z['set']}) {z['cn']} | {eur(z['preis'])} | {z['sprache']} | "
                         f"{z['grund']}\n")
    print(f"\nVerkaufsliste -> {out}  (PDF: python3 kartenbilder.py verkauf {out} --out out/verkauf --mobil)")


# ----------------------------------------------------------------- passung
def commander_passung(con, cname, cmdr_karten, spiel, bracket):
    """Wie gut passt ein Commander zu den Spielkarten (Nichtländer) eines Decks? Wert je Karte = max(EDHREC-Wert,
    Oracle-Bezug) – so zählen auch Karten, die auf der EDHREC-Seite fehlen. -> dict oder None (gar keine Daten)."""
    data, pfad = edhrec_commander(cname, bracket)
    edh = edh_karten(data)
    prof = profil_fuer(con, cmdr_karten, data)
    werte, auf, ohne = [], 0, []
    for q, c in spiel:
        b = bewerte(con, prof, edh, c)
        auf += 1 if b["edh"] is not None else 0
        if b["wert"] < 0.10:
            ohne.append(c["name"])
        werte.append(b["wert"] * q)
    n = sum(q for q, _ in spiel) or 1
    jd = (data or {}).get("container", {}).get("json_dict", {})
    return {"auf_seite": auf, "n": n, "ohne_bezug": ohne, "wert": sum(werte) / n, "pfad": pfad,
            "decks": (jd.get("card") or {}).get("num_decks"),
            "themen": [(t["value"], t["slug"], t["count"]) for t in (data or {}).get("panels", {}).get("taglinks", [])]}


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


def passung_alternativen(con, a, cmdr, main, spiel, ziel, A):
    c_oids = {c["oid"] for _, c in cmdr}
    deck_ci = set("".join(c["ci"] for _, c in main))
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
              + [x for x in zeilen if x["herkunft"] == "Kauf"][:a.kauf])
    for x in zeilen:
        x["p"] = commander_passung(con, x["c"]["name"], [x["c"]],
                                   [(q, c) for q, c in spiel if c["oid"] != x["c"]["oid"]], a.bracket)
    zeilen = [x for x in zeilen if x["p"]]
    zeilen.sort(key=lambda x: -x["p"]["wert"])
    return zeilen, zu_eng


def passung_befund(A, z, richt, ziel, d_ziel, rang, jetzt, th, zeilen, basis, slugs, ckurz):
    befund = []
    bester = rang[0]
    if ziel and d_ziel is not None and d_ziel < 0.5 and bester != ziel and A.deckung(z, richt, bester) >= 0.7:
        befund.append(f"Das Deck trägt das Ziel-Thema kaum ({d_ziel * 100:.0f} %), wohl aber "
                      f"{A.ARCHETYPEN[bester]['name']} ({A.deckung(z, richt, bester) * 100:.0f} %).")
    elif ziel and d_ziel is not None and d_ziel < 0.8:
        befund.append(f"Ziel-Thema nur teilweise abgedeckt ({d_ziel * 100:.0f} %) – Pakete mit ⚠ auffüllen.")
    if jetzt and ziel and jetzt["themen"] and (not th or th[0] > 6):
        befund.append(f"{ckurz} wird auf EDHREC selten oder nie für das Ziel-Thema gespielt.")
    if jetzt and jetzt["ohne_bezug"] and len(jetzt["ohne_bezug"]) / jetzt["n"] >= 0.4:
        befund.append(f"{len(jetzt['ohne_bezug'])} von {jetzt['n']} Spielkarten haben keinen Bezug zu {ckurz}.")
    besser = [x for x in zeilen if basis and x["p"]["wert"] >= basis * 1.1]
    if besser:
        befund.append("Laut Daten passt das vorhandene Deck besser zu: " + ", ".join(
            f"{x['c']['name']} ({vergleich(x['p']['wert'], basis)}, {x['herkunft']})" for x in besser[:3]) + ".")
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
    return befund, besser


def passung_optionen(A, z, richt, ziel, d_ziel, rang, jetzt, besser, zeilen, basis, ckurz):
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
    bester = rang[0]
    d_best = A.deckung(z, richt, bester)
    if ziel and bester != ziel and jetzt and d_best >= max(0.6, (d_ziel or 0) + 0.15):
        tb = thema_beim_commander(jetzt["themen"], set(A.ARCHETYPEN[bester]["edhrec"]))
        print(f"   C  Thema an das Deck anpassen: {A.ARCHETYPEN[bester]['name']} "
              + (f"(bei {ckurz} EDHREC-Thema Rang {tb[0]}, {tb[2]} Decks)" if tb else f"(bei {ckurz} kein EDHREC-Thema)"))
    print("   D  Neubau mit anderem Commander: deckbau.py commander-suche --thema <slug> --farben <XY> --nur-besitz")


def cmd_passung(con, a):
    pfad, did = deck_aus_ref(con, a.deck)
    cmdr, main, unbekannt, _ = lies_deck(con, pfad)
    if not cmdr:
        sys.exit("Kein Commander erkannt")
    cname, ckurz = cname_von(cmdr), kurzname(cname_von(cmdr))
    A, karten, richt = lade_archetypen()
    ziel = ziel_archetyp(A, a.thema, strategie_von(con, did))
    spiel = [(q, c) for q, c in main if "Land" not in front_type(c)]
    print(f"Passung {os.path.basename(pfad)} | Commander {cname} | Ziel-Thema: "
          + (f"{A.ARCHETYPEN[ziel]['name']} ({'Vorgabe' if a.thema else 'aus der Strategie im Register'})"
             if ziel else "keins angegeben (--thema)") + f" | Bracket {a.bracket}")
    if unbekannt:
        print("nicht erkannt: " + ", ".join(unbekannt))
    dz = Counter()
    for q, c in cmdr + main:
        dz[c["oid"]] += q
    z = A.zaehle_deck(dz, karten, {c["oid"] for _, c in cmdr})
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
    jetzt = commander_passung(con, cname, [c for _, c in cmdr], spiel, a.bracket)
    slugs = set(A.ARCHETYPEN[ziel]["edhrec"]) if ziel else set()
    print(f"\n2) Was {ckurz} spielt – EDHREC ({jetzt['pfad'] or 'keine Daten'}, {jetzt['decks'] or '–'} Decks)"
          + (f" · {'; '.join(EDH_STATUS)}" if EDH_STATUS else ""))
    th = None
    if jetzt["themen"]:
        print("   Themen: " + " · ".join(f"{n} {d}" for n, _, d in jetzt["themen"][:8]))
        th = thema_beim_commander(jetzt["themen"], slugs) if slugs else None
        if ziel:
            print("   Ziel-Thema beim Commander: " + (f"Rang {th[0]} ({th[1]}, {th[2]} Decks)" if th else "nicht unter den Themen"))
    print(f"\n3) {ckurz} ↔ Deck: {jetzt['auf_seite']} von {jetzt['n']} Spielkarten stehen auf der EDHREC-Seite · "
          f"Ø Wert je Spielkarte {jetzt['wert']:.3f} (EDHREC oder Oracle-Bezug) · ohne Bezug: {len(jetzt['ohne_bezug'])}")
    if jetzt["ohne_bezug"]:
        print("   ohne Bezug: " + ", ".join(jetzt["ohne_bezug"][:25]) + (" …" if len(jetzt["ohne_bezug"]) > 25 else ""))
    zeilen, zu_eng = passung_alternativen(con, a, cmdr, main, spiel, ziel, A)
    basis = jetzt["wert"] if jetzt["wert"] > 0 else None
    print(f"\n4) Alternative Commander aus Deck{', Sammlung und Kauf' if a.kauf else ' und Sammlung (frei)'} – Passung = "
          f"Ø Wert je Spielkarte ({ckurz} jetzt: {vergleich(jetzt['wert'], None)})")
    rows = []
    for x in zeilen:
        p = x["p"]
        tz = thema_beim_commander(p["themen"], slugs) if slugs else None
        rows.append((x["c"]["name"], x["herkunft"] + (f" {x['c']['eur']:.2f} €".replace(".", ",")
                                                      if x["herkunft"] == "Kauf" and x["c"]["eur"] else ""),
                     x["c"]["ci"] or "C", len(x["illegal"]), f"{p['auf_seite']}/{p['n']}", vergleich(p["wert"], basis),
                     (f"Rang {tz[0]}" if tz else "–") if ziel else "", " · ".join(n for n, _, _ in p["themen"][:3])))
    M.table(rows, ["Kandidat", "Herkunft", "Farben", "nicht legal", "auf EDHREC-Seite", "Passung", "Ziel-Thema",
                   "Top-Themen"]) if rows else print("   keine Kandidaten (Farbidentität passt nicht oder keine Daten)")
    if zu_eng:
        print("   wegen Farbidentität weggelassen: " + "; ".join(zu_eng[:8]) + (" …" if len(zu_eng) > 8 else ""))
    print("\n5) Befund (Daten-Hinweise, Abwägung im Gespräch):")
    befund, besser = passung_befund(A, z, richt, ziel, d_ziel, rang, jetzt, th, zeilen, basis, slugs, ckurz)
    for b in befund or ["Commander, Deck und Ziel-Thema passen zusammen."]:
        print(f"   - {b}")
    passung_optionen(A, z, richt, ziel, d_ziel, rang, jetzt, besser, zeilen, basis, ckurz)


# ----------------------------------------------------------------- fazit (Entwurf des Fazit-PDF)
ROLLEN_FOLGE = ["ramp", "ka", "gezielt", "massen", "schutz", "tutor", "rekursion", None, "land"]


def haupt_rolle(r, c):
    if "Land" in front_type(c):
        return "land"
    return next((x for x in ROLLEN_FOLGE if x and x in r), None)


def rollen_name(k):
    return {None: "Plan/Synergie", "land": "Länder"}.get(k) or ROLLE_NAME[k]


def kennzahlen(con, cmdr, main, ziel=None):
    z, inst = zaehle_rollen(con, main, ziel)
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
        if ("Land" in front_type(cr)) != ("Land" in front_type(cn)):
            return -9
        p = 3 if haupt_rolle(rollen_je[o_r], cr) == haupt_rolle(rollen_je[o_n], cn) else 0
        p += len(set(rollen_je[o_r]) & set(rollen_je[o_n]))
        return p - abs((cr["cmc"] or 0) - (cn["cmc"] or 0)) / 4
    for o_n in sorted(rein, key=lambda o: -len(rollen_je[o])):
        if not offen_r:
            paare.append((None, o_n))
            continue
        best = max(offen_r, key=lambda o_r: punkte(o_r, o_n))
        if punkte(best, o_n) <= -9:
            paare.append((None, o_n))
            continue
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


def fazit_status(con, f, c, kauf_alt):
    """Status einer Karte im Fazit: Standardland · frei [· Kompromiss-Stufe] [⚑] · aus anderem Deck · Kauf."""
    if basic(c):
        return "Standardland"
    b, d, fr = besitz(con, c["oid"], f["did"])
    if fr > 0:
        st = "frei"
        r = next((x for x in f["rollen_je"].get(c["oid"], []) if x in KERN and x != "land"
                  and f["k_alt"] and f["k_alt"][x] < f["soll"][x][0]), None) if f["upgrade"] else None
        if r:
            stufe, _, _ = kompromiss({"c": c, "b": bewerte(con, f["prof"], f["edh"], c)}, r, kauf_alt)
            st += f" · {stufe}"
        return st + (" ⚑" if c["oid"] in f["beim_deck"] else "")
    return "aus anderem Deck" if b > 0 else (f"Kauf ab {c['eur']:.2f} €".replace(".", ",") if c["eur"] else "Kauf")


def fazit_kopf(f, bz, a, k_neu, n_tausch, n_plus, n_minus, kauf):
    heute = time.strftime("%d.%m.%Y")
    art = f"Upgrade {a.stufe}" if f["upgrade"] else "Neues Deck"
    wert_txt_ = f"{k_neu['_wert']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ["---", f"titel: {f['deckname']}", f"oberzeile: {art} · freigegeben am {heute}",
            f"unterzeile: Fazit, Kartenerklärungen und Vorgehen · {f['cname']} · Bracket {a.bracket}",
            f"zeile3: {f['voll']}", f"kurz: {art}", f"farben: {f['ci']}",
            f"fuss: Daten: Scryfall, EDHREC ({f['epfad'] or '–'}), Commander Spellbook · Stand {heute}",
            f"deckname: {f['deckname']}", f"voll: {f['voll']}", f"bracket_zeile: {bz['zeile']}",
            "beschreibung: ‹Moxfield-Beschreibung, höchstens 140 Zeichen›", "themen: ‹Moxfield-Themen aus der Liste›",
            "status: freigegeben – Aufbau offen", f"wert: {wert_txt_} € (günstigste Drucke, {heute})",
            f"set: {f['pset'] or ''}", "---",
            "[kacheln]", f"Bracket {a.bracket} | {len(bz['gc'])}/{bz['limit'] if bz['limit'] < 99 else '∞'} Game Changer",
            (f"{n_tausch} Tausche" + (f" + {n_plus} neu" if n_plus else "") + (f" − {n_minus}" if n_minus else "")
             + f" | {a.stufe} · {kauf:.2f} €".replace(".", ",")
             if f["upgrade"] else f"{f['n_karten']} Karten | {f['n_laender']} Länder"),
            f"{wert_txt_} € | Deckwert (günstigste Drucke)",
            f"{k_neu['_mv']:.2f}".replace(".", ",") + " | Ø MV (Nichtländer inkl. Commander)", "[/kacheln]", "",
            "## Fazit", "‹2–3 Sätze: Spielplan und was sich ändert›", "",
            f"> **Bracket-Zeile:** {bz['zeile']} (Commander Spellbook: {SPELLBOOK.get(bz['sb_tag'], bz['sb_tag'])})", ""]


def fazit_aenderungen(con, f, paare, cards, status):
    L = ["## Die Änderungen", "| raus | warum raus | rein | warum rein | Status |", "|---|---|---|---|---|"]
    for o_r, o_n in paare:
        cr, cn = cards.get(o_r), cards.get(o_n)
        gr = gn = "–"
        if cr:
            xr = {"c": cr, "b": bewerte(con, f["prof"], f["edh"], cr), "rollen": f["rollen_je"][o_r]}
            gr = "‹warum raus›" if basic(cr) else f"‹warum raus› *({grund_raus(xr, f['k_alt'], f['soll'], f['ckurz'])})*"
        if cn:
            st = status(cn)
            kn = {"c": cn, "b": bewerte(con, f["prof"], f["edh"], cn), "rollen": f["rollen_je"][o_n],
                  "kompromiss": (st.split(" · ")[1].replace(" ⚑", ""),) if st.startswith("frei · ") else None}
            gn = ("‹warum rein›" if basic(cn) else
                  f"‹warum rein, aus dem Oracle-Text› *({grund_rein(kn, f['k_alt'], f['k_neu'], f['soll'], f['ckurz'])})*")
        L.append(f"| {cr['name'] if cr else '–'} | {gr} | {cn['name'] if cn else '–'} | {gn} | {status(cn) if cn else '–'} |")
    return L


def fazit_kennzahlen(f, bz, a, cmdr, main, cmdr_a, main_a):
    up = f["upgrade"]
    L = (["", "## Kennzahlen vorher und nachher", "| Kennzahl | vorher | nachher | Richtwert |", "|---|---|---|---|"] if up
         else ["## Kennzahlen", "| Kennzahl | Deck | Richtwert |", "|---|---|---|"])
    for k in KERN:
        mn, ziel, _ = f["soll"][k]
        L.append(f"| {ROLLE_NAME[k]} | " + (f"{f['k_alt'][k]} | " if up else "") + f"{f['k_neu'][k]} | {mn}–{ziel} |")
    for key, n, rw in (("_inst", "davon Instant-Interaktion", "≥ 4"), ("_mv", "Ø MV", "≤ 3,5"),
                       ("_gc", "Game Changer", f"≤ {bz['limit']}" if bz["limit"] < 99 else "–")):
        fm = (lambda x: f"{x:.2f}".replace(".", ",")) if key == "_mv" else str
        L.append(f"| {n} | " + (f"{fm(f['k_alt'][key])} | " if up else "") + f"{fm(f['k_neu'][key])} | {rw} |")
    ak = f["ak"]
    A = ak["A"]
    if ak:
        def paket_z(cm, mn):
            dz = Counter()
            for q, c in cm + mn:
                dz[c["oid"]] += q
            return A.zaehle_deck(dz, ak["karten"], {c["oid"] for _, c in cm})
        z_n = paket_z(cmdr, main)
        z_a = paket_z(cmdr_a, main_a) if up else None
        for p in ak["pakete"]:
            key = f"{ak['ziel']}.{p['key']}"
            L.append(f"| {p['label']} | " + (f"{z_a[key]} | " if up else "")
                     + f"{z_n[key]} | {('Median ' + A_de(p['median'])) if p['median'] is not None else '–'} |")
    return L


def fazit_erklaerungen(con, f, rein, cmdr, main, cards, status):
    L = ["", "## Spielplan", "- **Früh:** ‹…›", "- **Mitte:** ‹…›", "- **Spät / Siegwege:** ‹…›", "",
         "## Ehrliche Einschätzung und Abstriche", ">! ‹Was fehlt, was schwach bleibt, welche Käufe später am meisten bringen›",
         "", "## Kartenerklärungen", "| Karte | Rolle | Warum im Deck & Synergie | Commander-Bezug | Status |",
         "|---|---|---|---|---|"]
    up = f["upgrade"]
    erkl = ([cards[o] for o in dict.fromkeys(rein) if not basic(cards[o])] if up
            else [c for _, c in cmdr] + [c for _, c in main if not basic(c)])
    gruppen = {}
    for c in erkl:
        g = "commander" if any(c["oid"] == x["oid"] for _, x in cmdr) and not up else \
            haupt_rolle(f["rollen_je"].get(c["oid"]) or rollen(con, c), c)
        gruppen.setdefault(g, []).append(c)
    for g in ["commander"] + ROLLEN_FOLGE:
        if g not in gruppen:
            continue
        L.append(f"| ## {'Commander' if g == 'commander' else rollen_name(g)} |")
        for c in sorted(gruppen[g], key=lambda c: (c["cmc"] or 0, c["name"])):
            if g == "commander":
                daten = "Commander"
            else:
                b = bewerte(con, f["prof"], f["edh"], c)
                daten = edh_txt(b["v"], f["ckurz"]) + (f"; Bezug {de(b['bezug'])} ({', '.join(b['gruende'][:2])})"
                                                       if b["gruende"] else "")
            L.append(f"| {c['name']} | {rollen_txt(f['rollen_je'].get(c['oid']) or rollen(con, c)).replace(',', ', ')} |"
                     f" ‹…› *({daten})* | ‹…› | {status(c) if g != 'commander' else '–'} |")
    return L, len(erkl)


def fazit_abnahme(con, a, did):
    try:
        d = abnahme_daten(con, a.neu, a.bracket, a.thema, 3000, did)
        basis = abnahme_daten(con, deck_aus_ref(con, a.alt)[0], a.bracket, d["ak"]["ziel"], 3000, did) if a.alt else None
    except SystemExit:
        return []
    pk = abnahme_punkte(d, basis)
    L = ["", f"## Bracket-{a.bracket}-Abnahme", "| Prüfpunkt | Ergebnis | Status |", "|---|---|---|"]
    L += [f"| {n} | {e} | {s} |" for n, e, s in pk]
    L += ["", f"> **Urteil:** {urteil(pk)} · Stärke-Index {de(d['index'], 3)}"
          + (f" (vorher {de(basis['index'], 3)})" if basis else "") + " – Schwellen für Interaktion und Simulation vorläufig."]
    return L


def cmd_fazit(con, a):
    cmdr, main, unbekannt, _ = lies_deck(con, a.neu)
    if not cmdr:
        sys.exit("Kein Commander im Entwurf erkannt")
    if unbekannt:
        print("nicht erkannt: " + ", ".join(unbekannt))
    cname = cname_von(cmdr)
    data, epfad = edhrec_commander(cname, a.bracket)
    did, cmdr_a, main_a = None, [], []
    if a.alt:
        pfad_a, did = deck_aus_ref(con, a.alt)
        cmdr_a, main_a, _, _ = lies_deck(con, pfad_a)
    upgrade = bool(a.alt)
    ak = archetyp_kontext(con, cmdr, main, did, a.thema)
    f = {"upgrade": upgrade, "did": did, "cname": cname, "ckurz": kurzname(cname), "edh": edh_karten(data),
         "prof": profil_fuer(con, [c for _, c in cmdr], data), "ak": ak, "soll": ak["soll"], "epfad": epfad,
         "ci": "".join(x for x in "WUBRG" if x in set("".join(c["ci"] for _, c in cmdr)))}
    neu_z, alt_z, cards = Counter(), Counter(), {}
    for q, c in cmdr + main:
        neu_z[c["oid"]] += q
        cards[c["oid"]] = c
    for q, c in cmdr_a + main_a:
        alt_z[c["oid"]] += q
        cards[c["oid"]] = c
    f["rollen_je"] = {o: rollen_im_plan(con, c, ak["ziel"]) for o, c in cards.items()}
    f["k_alt"] = kennzahlen(con, cmdr_a, main_a, ak["ziel"]) if upgrade else None
    f["k_neu"] = kennzahlen(con, cmdr, main, ak["ziel"])
    raus = [o for o in alt_z for _ in range(alt_z[o] - neu_z[o])] if upgrade else []
    rein = [o for o in neu_z for _ in range(neu_z[o] - alt_z[o])] if upgrade else []
    paare = lies_paare(con, a.paare) if a.paare else paare_bilden(raus, rein, f["rollen_je"], cards)
    for o in [o for o, _ in paare if o] + [o for _, o in paare if o]:
        if o not in cards:
            cards[o] = card(con, o)
            f["rollen_je"][o] = rollen_im_plan(con, cards[o], ak["ziel"])
    zp, beim_deck = M.deck_zeitstempel(con, did) if did else (None, None)
    f["beim_deck"] = {r[3] for r in beim_deck or []}
    ctx = {"edh": f["edh"], "im_deck": set(cards), "ci": set(f["ci"]), "prof": f["prof"], "ak": ak, "did": did}
    kauf_alt = kauf_alternativen(con, ctx)
    status = lambda c: fazit_status(con, f, c, kauf_alt)
    kauf = sum(cards[o]["eur"] or 0 for o in set(rein) if status(cards[o]).startswith("Kauf"))
    n_tausch = sum(1 for r_, n_ in paare if r_ and n_)
    n_plus, n_minus = sum(1 for r_, n_ in paare if n_ and not r_), sum(1 for r_, n_ in paare if r_ and not n_)
    bz = bracket_zeile(con, cmdr, main, a.bracket)
    cfg_pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deck_namen.json")
    cfg = json.load(open(cfg_pfad, encoding="utf-8")).get(f"commander:{cname}", {}) if os.path.exists(cfg_pfad) else {}
    db_s, db_h = (con.execute("SELECT strategie, herkunft FROM decks WHERE deck_id=?", (did,)).fetchone()
                  if did else (None, None))
    f["deckname"] = a.deckname or cfg.get("name") or cfg.get("precon") or f["ckurz"]
    f["voll"] = " | ".join(["Commander", f["deckname"], M.farbname_kurz(f["ci"]), cfg.get("strategie") or db_s or "‹Strategie›",
                            cfg.get("herkunft") or db_h or "Selfbuild"] + ([cfg["status"]] if cfg.get("status") else []))
    f["pset"] = con.execute("SELECT precon_set FROM decks WHERE deck_id=?", (did,)).fetchone()[0] if did else ""
    f["n_karten"] = sum(neu_z.values())
    f["n_laender"] = sum(1 for _, c in main if "Land" in front_type(c))
    L = fazit_kopf(f, bz, a, f["k_neu"], n_tausch, n_plus, n_minus, kauf)
    if upgrade:
        L += fazit_aenderungen(con, f, paare, cards, status)
        if any("⚑" in status(cards[o]) for o in set(rein)):
            L += ["", ">! **⚑ Rückfrage:** Diese Karten wurden zusammen mit dem Deck erfasst und liegen vielleicht schon "
                  "beim Deck (Maybeboard oder fehlende Deckkarte). Beim Aufbau prüfen."]
    L += fazit_kennzahlen(f, bz, a, cmdr, main, cmdr_a, main_a)
    L += fazit_abnahme(con, a, did)
    erkl_L, n_erkl = fazit_erklaerungen(con, f, rein, cmdr, main, cards, status)
    heute = time.strftime("%d.%m.%Y")
    L += erkl_L + ["", "## So bin ich vorgegangen",
                   "1. Gespräch nach Fragenplan: ‹Ausgangslage/Passung, Richtung, Budget, Game Changer, weitere Antworten›",
                   "2. Ausgangslage: `deckbau.py passung` – ‹Befund in einem Satz›",
                   f"3. Recherche: EDHREC ({epfad or '–'}, {heute}) als Anhaltspunkt, `synergie` (Oracle-Bezug), Commander "
                   "Spellbook, Scryfall-Funktionstags; " + ("`deckbau.py upgrade`" if upgrade else "`deckbau.py kandidaten`")
                   + ", `oracle` für jede beschriebene Karte",
                   "4. Prüfläufe: `pruefen` ohne offene Warnungen, `abnahme`, `simulation.py`",
                   "5. Anpassungen: ‹Änderungen aus den Anpassungsrunden›", "", "<seitenumbruch>", "", "## Anhang: Moxfield",
                   "[moxfield]", "", "```", einfuegeblock(a.neu, [c["name"] for _, c in cmdr]), "```", ""]
    out = a.out or "fazit.md"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(L))
    offen = sum(z.count("‹") for z in L)
    print(f"Fazit-Entwurf: {out} | {len(paare)} Zeilen in „Die Änderungen“ | {n_erkl} Kartenerklärungen | "
          f"{offen} Platzhalter ‹…› zu füllen (nur Text – Zahlen, Status, Abnahme und Daten stehen schon drin)")
    if upgrade and not a.paare:
        print("Paare automatisch gebildet (Land↔Land, gleiche Hauptrolle, ähnliche MV) – anders gewünscht: "
              "Datei mit „Raus -> Rein“ je Zeile und --paare <datei>.")


# ----------------------------------------------------------------- Kommandozeile
def parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    idee = {"help": "Vormerkungen dieser Idee (I-nnn) als frei behandeln"}
    p = sp.add_parser("commander", help="Steckbrief eines Commanders")
    p.add_argument("name")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--budget", action="store_true")
    p = sp.add_parser("commander-suche", help="Commander finden")
    p.add_argument("--thema")
    p.add_argument("--farben")
    p.add_argument("--text")
    p.add_argument("--nur-besitz", action="store_true")
    p.add_argument("--limit", type=int, default=20)
    p = sp.add_parser("synergie", help="freie Karten mit Bezug zum Commander-Text (auch ohne EDHREC)")
    p.add_argument("ref", help="Commander-Name oder Deck (Deckname/Soll-Stand)")
    p.add_argument("--thema", help="Ziel-Archetyp für den Paket-Bedarf (tokens, landfall …)")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--top", type=int, default=30)
    p.add_argument("--alle", action="store_true", help="auch Karten ohne jeden Bezug in die CSV")
    p.add_argument("--out", help="vollständige Rangliste als CSV")
    p = sp.add_parser("kandidaten", help="Kartenpool für einen neuen Bau")
    p.add_argument("commander")
    p.add_argument("--weg", type=int, choices=(1, 2), required=True)
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--thema")
    p.add_argument("--budget", action="store_true")
    p.add_argument("--out")
    p = sp.add_parser("pruefen", help="Qualitätskontrolle eines Entwurfs")
    p.add_argument("deck")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--ersetzt")
    p.add_argument("--archetyp", help="Ziel-Archetyp für die Richtwerte (sonst Strategie im Register bzw. Deckung)")
    p.add_argument("--combos-fehlend", action="store_true")
    p.add_argument("--idee", **idee)
    p = sp.add_parser("abnahme", help="Bracket-3-Abnahme (Definition of Done)")
    p.add_argument("deck", help="Deckname, Soll-Stand oder Entwurf")
    p.add_argument("--basis", help="Ausgangsstand zum Vergleich (Soll-Stand bzw. Precon-Liste)")
    p.add_argument("--archetyp")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--n", type=int, default=5000, help="Spiele in der Simulation")
    p.add_argument("--idee", **idee)
    p = sp.add_parser("erklaerung", help="Datenbasis für Kartenerklärungen")
    p.add_argument("deck")
    p.add_argument("--idee", **idee)
    p.add_argument("--ersetzt")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--out")
    p = sp.add_parser("upgrade", help="Upgrade-Modus mit Raus-Sperren")
    p.add_argument("deck", help="Deckname oder Soll-Stand-Datei")
    p.add_argument("--stufe", type=int, default=0, choices=(0, 1))
    p.add_argument("--max-preis", type=float, default=10.0, help="Stufe 1: höchster Einzelpreis in EUR")
    p.add_argument("--thema", help="Ziel-Archetyp bzw. EDHREC-Thema (sonst Strategie im Register)")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--paare", type=int, default=15)
    p.add_argument("--abstand", type=float, default=0.08, help="Mindestabstand im Wert für ein Tauschpaar")
    p.add_argument("--voll", action="store_true", help="alle Listen ausgeben (sonst kurz; alles steht in der CSV)")
    p.add_argument("--kurz", action="store_true", help="kurze Ausgabe (Standard; nur aus Kompatibilität)")
    p.add_argument("--idee", **idee)
    p.add_argument("--out")
    p = sp.add_parser("verkauf", help="Verkaufsprüfung der freien Karten")
    p.add_argument("--min-preis", type=float, default=1.0, help="nur Karten ab diesem Preis (eigener Druck), Standard 1 €")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--out", help="Verkaufsliste (Standard out/verkauf.txt)")
    p = sp.add_parser("passung", help="Passt das Deck zu Commander und Ziel?")
    p.add_argument("deck", help="Deckname oder Soll-Stand-Datei")
    p.add_argument("--thema", help="Ziel-Thema: Archetyp (landfall, counters …) oder EDHREC-Slug; sonst aus der Strategie")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--kandidaten", type=int, default=10, help="höchstens so viele Commander-Kandidaten bewerten")
    p.add_argument("--kauf", type=int, default=0, help="zusätzlich N Kauf-Commander zum Ziel-Thema (EDHREC)")
    p.add_argument("--max-illegal", type=int, default=15, help="Kandidaten mit mehr Karten außerhalb der Farbidentität weglassen")
    p = sp.add_parser("fazit", help="Fazit-Entwurf für kartenbilder.py")
    p.add_argument("--neu", required=True, help="Entwurf (am besten mit eigenen Drucken aus mtg_db.py drucke)")
    p.add_argument("--alt", help="Soll-Stand bzw. Deckname (Upgrade); ohne = neues Deck")
    p.add_argument("--paare", help="Datei „Raus -> Rein“ je Zeile (z. B. aus upgrade); sonst automatisch")
    p.add_argument("--thema", help="Archetyp für Richtwerte und Paket-Kennzahlen (landfall, tokens …)")
    p.add_argument("--stufe", default="Stufe 0", help="Text für Kachel und Oberzeile, z. B. „Stufe 1 (bis 25 €)“")
    p.add_argument("--deckname")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--idee", **idee)
    p.add_argument("--out")
    p = sp.add_parser("gegentest", help="zwei Decks vergleichen bzw. Auftrag für den Konkurrenz-Agenten")
    p.add_argument("a", nargs="?", help="Deck A (z. B. Vorschlag des Projekts)")
    p.add_argument("b", nargs="?", help="Deck B (z. B. Ergebnis des Konkurrenz-Skills)")
    p.add_argument("--namen", help="Anzeigenamen „A,B“")
    p.add_argument("--archetyp")
    p.add_argument("--bracket", type=int, default=3)
    p.add_argument("--n", type=int, default=5000)
    p.add_argument("--prompt", action="store_true", help="Auftrag für den Konkurrenz-Agenten ausgeben")
    p.add_argument("--commander")
    p.add_argument("--budget", default="offen – Stufen zeigen")
    p.add_argument("--thema")
    p.add_argument("--stil", default="Midrange")
    p.add_argument("--skill", default="deck-wizard")
    p.add_argument("--skill-pfad", default="/home/claude/fremd/mtg-skills/deck-wizard/SKILL.md")
    p.add_argument("--mit-sammlung", help="Pfad einer Liste freier Karten, die der Konkurrenz-Agent bevorzugen soll")
    p.add_argument("--ausgabe", default="/home/claude/gegentest/konkurrenz.txt")
    p = sp.add_parser("oracle", help="Oracle-Text (Pflicht vor jedem Vorschlag)")
    p.add_argument("karten", nargs="*")
    p.add_argument("--alt")
    p.add_argument("--neu")
    p.add_argument("--rulings", action="store_true")
    p = sp.add_parser("alternativen", help="günstigere Karten mit gleicher Rolle")
    p.add_argument("karte")
    p.add_argument("--farben")
    p.add_argument("--limit", type=int, default=6)
    p.add_argument("--idee", **idee)
    return ap


BEFEHLE = {"commander": cmd_commander, "commander-suche": cmd_commander_suche, "synergie": cmd_synergie,
           "kandidaten": cmd_kandidaten, "pruefen": cmd_pruefen, "abnahme": cmd_abnahme, "erklaerung": cmd_erklaerung,
           "alternativen": cmd_alternativen, "upgrade": cmd_upgrade, "oracle": cmd_oracle, "passung": cmd_passung,
           "fazit": cmd_fazit, "verkauf": cmd_verkauf, "gegentest": cmd_gegentest}


def main(argv=None):
    import signal
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    a = parser().parse_args(argv)
    global IDEE
    IDEE = getattr(a, "idee", None)
    if a.cmd == "gegentest" and a.prompt:
        return cmd_gegentest(None, a)
    BEFEHLE[a.cmd](db(), a)


if __name__ == "__main__":
    main()
