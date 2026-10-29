#!/usr/bin/env python3
"""Monatlicher Rauchtest mit Live-Daten (GitHub Actions, Zeitplan): Sind die Quellen erreichbar und ihre Formate
unverändert? Bricht mit Fehlercode ab, wenn eine Quelle fehlt oder ein Feld, das die Werkzeuge lesen, verschwunden ist.

  python3 tests/rauchtest.py
"""
import json
import sys
import urllib.request

UA = {"User-Agent": "MTG-Projekt/1.0 (Rauchtest)", "Accept": "application/json"}
fehler = []


def hole(url, daten=None):
    kopf = dict(UA)
    if daten is not None:
        kopf["Content-Type"] = "application/json"
        daten = json.dumps(daten).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=daten, headers=kopf), timeout=60) as r:
        return json.load(r)


def pruefe(name, fn):
    try:
        fn()
        print(f"ok      {name}")
    except Exception as e:                       # noqa: BLE001 – jeder Fehler ist ein Befund
        fehler.append(name)
        print(f"FEHLER  {name}: {e.__class__.__name__}: {e}")


def scryfall():
    d = {x["type"]: x for x in hole("https://api.scryfall.com/bulk-data")["data"]}
    for t in ("default_cards", "oracle_tags", "rulings"):
        assert t in d, f"Bulk-Typ {t} fehlt"
        assert d[t].get("jsonl_download_uri") or d[t].get("download_uri"), f"{t}: kein Download-Link"
    karte = hole("https://api.scryfall.com/cards/named?exact=Sol%20Ring")
    for k in ("oracle_id", "oracle_text", "color_identity", "legalities", "prices", "game_changer"):
        assert k in karte, f"Kartenfeld {k} fehlt"


def edhrec():
    d = hole("https://json.edhrec.com/pages/commanders/zurgo-stormrender/upgraded.json")
    jd = d["container"]["json_dict"]
    cv = jd["cardlists"][0]["cardviews"][0]
    for k in ("name", "num_decks", "potential_decks", "synergy"):
        assert k in cv, f"Kartenfeld {k} fehlt"
    assert "taglinks" in d.get("panels", {}), "Themen (panels.taglinks) fehlen"
    a = hole("https://json.edhrec.com/pages/average-decks/krenko-mob-boss/upgraded/tokens.json")
    assert a.get("container", {}).get("json_dict", {}).get("cardlists"), "Durchschnittsdeck ohne Kartenlisten"


def spellbook():
    body = {"main": [{"card": "Sol Ring", "quantity": 1}], "commanders": [{"card": "Zurgo Stormrender", "quantity": 1}]}
    r = hole("https://backend.commanderspellbook.com/estimate-bracket", body)
    assert "bracketTag" in r, "estimate-bracket ohne bracketTag"
    r = hole("https://backend.commanderspellbook.com/find-my-combos", body)
    assert "included" in (r.get("results", r) or {}), "find-my-combos ohne included"


pruefe("Scryfall (Bulk-Liste, Kartenfelder)", scryfall)
pruefe("EDHREC (Commander-Seite, Durchschnittsdeck)", edhrec)
pruefe("Commander Spellbook (estimate-bracket, find-my-combos)", spellbook)
sys.exit(1 if fehler else 0)
