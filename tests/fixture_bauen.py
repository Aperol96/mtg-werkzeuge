#!/usr/bin/env python3
"""Baut die Test-Daten in tests/daten/ aus den vollständigen Scryfall-Bulk-Dateien (nur Admin, bei Bedarf).

  python3 tests/fixture_bauen.py --bulk bulk --edhrec cache/edhrec

Ergebnis (wird mit dem Repo ausgeliefert, damit die Tests ohne Netz laufen):
  tests/daten/bulk/default_cards.jsonl.gz   je Testkarte ein englischer Druck
  tests/daten/bulk/oracle_tags.jsonl.gz     alle Tags (für die Vorfahren-Kette), Zuordnungen nur der Testkarten
  tests/daten/bulk/rulings.jsonl.gz         Rulings der Testkarten
  tests/daten/sammlung.csv                  Testbestand (Moxfield-Format): Testdeck + freie Karten
  tests/daten/edhrec/*.json                 EDHREC-Seiten des Test-Commanders (Zwischenspeicher-Format)
"""
import argparse
import gzip
import json
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HIER), "skills", "mtg-commander-deckbauer", "werkzeuge"))
import mtg_db as M  # noqa: E402

# Freie Karten im Testbestand (nicht im Testdeck) – je eine Prüfung in tests/test_werkzeuge.py
FREI = ["Venerated Stormsinger", "Duty Beyond Death", "Skittering Precursor", "Magnifying Glass", "Sunfall",
        "Farewell", "Hour of Reckoning", "Shatter the Sky", "Nightblade Brigade", "Mind Stone", "Flamebraider",
        "Wood Elves", "Path to Exile", "Explore", "Swords to Plowshares", "Blood Artist", "Intangible Virtue",
        "Plains", "Swamp", "Mountain"]
NUR_DATENBANK = ["Pitiless Plunderer", "Cultivate", "Rampant Growth", "Dark Ritual", "Collective Voyage",
                 "Demonic Tutor", "Lightning Bolt", "Wrath of God", "Heroic Intervention"]
EDHREC = ["commanders__zurgo-stormrender__upgraded.json"]


def namen_aus_deck(pfad):
    out = []
    for z in open(pfad, encoding="utf-8"):
        m = re.match(r"^\s*(\d+)x?\s+(.+?)\s*$", z)
        if m:
            out.append((int(m.group(1)), m.group(2)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bulk", default="bulk")
    ap.add_argument("--edhrec", default="cache/edhrec")
    a = ap.parse_args()
    deck = namen_aus_deck(os.path.join(HIER, "daten", "testdeck.txt"))
    gesucht = {M.fold(n) for _, n in deck} | {M.fold(n) for n in FREI + NUR_DATENBANK}
    gesucht |= {M.fold(M.front(n)) for n in list(gesucht)}
    drucke, oids = {}, set()
    for c in M.iter_jsonl(os.path.join(a.bulk, "default_cards.jsonl.gz")):
        n = M.fold(c.get("name", ""))
        if (n in gesucht or M.fold(M.front(c.get("name", ""))) in gesucht) and c.get("lang") == "en" \
                and c.get("layout") not in ("token", "art_series") and not c.get("digital"):
            oid = c.get("oracle_id") or (c.get("card_faces") or [{}])[0].get("oracle_id")
            if oid and oid not in drucke:
                drucke[oid] = c
                oids.add(oid)
    fehlt = gesucht - {M.fold(c["name"]) for c in drucke.values()} - {M.fold(M.front(c["name"])) for c in drucke.values()}
    if fehlt:
        print("nicht gefunden:", ", ".join(sorted(fehlt)), file=sys.stderr)
    ziel = os.path.join(HIER, "daten", "bulk")
    os.makedirs(ziel, exist_ok=True)
    with gzip.open(os.path.join(ziel, "default_cards.jsonl.gz"), "wt", encoding="utf-8") as fh:
        for c in drucke.values():
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    with gzip.open(os.path.join(ziel, "oracle_tags.jsonl.gz"), "wt", encoding="utf-8") as fh:
        for t in M.iter_jsonl(os.path.join(a.bulk, "oracle_tags.jsonl.gz")):
            tg = [x for x in t.get("taggings", []) if x.get("oracle_id") in oids]
            fh.write(json.dumps({"id": t["id"], "slug": t["slug"], "parent_ids": t.get("parent_ids", []),
                                 "description": None, "taggings": [{"oracle_id": x["oracle_id"]} for x in tg]}) + "\n")
    with gzip.open(os.path.join(ziel, "rulings.jsonl.gz"), "wt", encoding="utf-8") as fh:
        for r in M.iter_jsonl(os.path.join(a.bulk, "rulings.jsonl.gz")):
            if r.get("oracle_id") in oids:
                fh.write(json.dumps({"oracle_id": r["oracle_id"], "published_at": r["published_at"],
                                     "comment": r["comment"]}, ensure_ascii=False) + "\n")
    # Testbestand: alle Deckkarten + freie Karten (Standardländer zusätzlich 10×)
    nach_name = {M.fold(c["name"]): c for c in drucke.values()}
    nach_name.update({M.fold(M.front(c["name"])): c for c in drucke.values()})
    kopf = ["Count", "Tradelist Count", "Name", "Edition", "Condition", "Language", "Foil", "Tags", "Last Modified",
            "Collector Number", "Alter", "Proxy", "Purchase Price"]
    zeilen = [(q, n) for q, n in deck] + [(10 if n in ("Plains", "Swamp", "Mountain") else 1, n) for n in FREI]
    with open(os.path.join(HIER, "daten", "sammlung.csv"), "w", encoding="utf-8") as fh:
        fh.write(",".join(f'"{k}"' for k in kopf) + "\n")
        for q, n in zeilen:
            c = nach_name.get(M.fold(n)) or nach_name.get(M.fold(M.front(n)))
            if not c:
                continue
            werte = [q, q, c["name"], c["set"], "Near Mint", "English", "", "", "2026-01-01 00:00:00.000000",
                     c["collector_number"], "False", "False", ""]
            fh.write(",".join(f'"{w}"' for w in werte) + "\n")
    os.makedirs(os.path.join(HIER, "daten", "edhrec"), exist_ok=True)
    for fn in EDHREC:                            # nur die Felder, die die Werkzeuge lesen
        d = json.load(open(os.path.join(a.edhrec, fn), encoding="utf-8"))
        jd = d.get("container", {}).get("json_dict", {})
        klein = {"container": {"json_dict": {
            "card": {k: jd.get("card", {}).get(k) for k in ("name", "num_decks", "rank", "salt")},
            "cardlists": [{"header": cl.get("header"),
                           "cardviews": [{k: cv.get(k) for k in ("name", "sanitized", "num_decks", "potential_decks",
                                                                 "synergy", "lift")} for cv in cl.get("cardviews", [])]}
                          for cl in jd.get("cardlists", [])]}},
            "panels": {k: d.get("panels", {}).get(k) for k in ("taglinks", "combocounts")}}
        json.dump(klein, open(os.path.join(HIER, "daten", "edhrec", fn), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(drucke)} Karten, {len(zeilen)} Bestandszeilen -> {os.path.join(HIER, 'daten')}")


if __name__ == "__main__":
    main()
