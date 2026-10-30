#!/usr/bin/env python3
"""simulation.py – Konsistenz-Simulation eines Commander-Decks (Monte-Carlo, V1.6).

Spielt viele Starthände und die ersten Züge allein durch („Goldfish“) und misst, wie zuverlässig das Deck
Länder, Mana und den Commander auf den Tisch bringt. Grundlage der Bracket-3-Abnahme (08) und des Gegentests.

Befehl
  python3 simulation.py <deckdatei|Deckname> [--n 10000] [--seed 1] [--zuege 5] [--json out.json]

Regeln (Comprehensive Rules, geprüft am Regelwerk-PDF im Projekt):
  - London-Mulligan (103.5): neue 7, dann so viele Karten unter die Bibliothek, wie Mulligans genommen wurden.
  - Mehrspieler (103.5c): der erste Mulligan ist frei. 103.8c: niemand übergeht das Ziehen im ersten Zug.

Annahmen (Einschätzung, im Ergebnis genannt):
  - Behalten: 3–5 Länder; 2 Länder mit Ramp bis MV 2; nach dem freien Mulligan gleich; nach zwei echten
    Mulligans jede Hand mit 2–5 Ländern, danach jede Hand. Unter die Bibliothek: überzählige Länder, sonst die teuersten Karten.
  - Je Zug: ziehen, ein Land spielen (ungetappt bevorzugt, wenn es den Commander oder Ramp ermöglicht), Ramp wirken
    (billigste zuerst), dann den Commander, sobald Mana und Farben reichen.
  - Länder „enters tapped“ kommen getappt; „… tapped unless …“ in Zug 1–2 getappt, danach ungetappt (Näherung).
    Mana-Steine liefern sofort, Mana-Kreaturen ab dem nächsten Zug, Land-Ramp legt das Land (getappt laut Text).
    Einmalige Effekte (Rituale, Treasure) zählen nicht.
"""
import argparse
import json
import os
import random
import re
import sys
from collections import Counter

FARBEN = "WUBRG"
LANDTYP_FARBE = {"plains": "W", "island": "U", "swamp": "B", "mountain": "R", "forest": "G"}


# ----------------------------------------------------------------- Karten für die Simulation
def manakosten(mana_cost):
    """'{2}{R}{W}' -> (generisch, Counter je Farbe, MV). Hybrid zählt als eine der Farben (erste)."""
    gen, pips = 0, Counter()
    for sym in re.findall(r"\{([^}]+)\}", (mana_cost or "").split(" // ")[0]):
        if sym.isdigit():
            gen += int(sym)
        elif sym in ("X", "C", "S"):
            gen += 0 if sym == "X" else 1
        else:
            farbe = next((ch for ch in sym if ch in FARBEN), None)
            if farbe and "P" not in sym:
                pips[farbe] += 1
            else:
                gen += 1
    return gen, pips, gen + sum(pips.values())


def land_farben(text, produced, ci):
    prod = set(produced or "") & set(FARBEN)
    if prod:
        return prod
    tl = (text or "").lower()
    s = {f for typ, f in LANDTYP_FARBE.items() if typ in tl}
    if "search your library" in tl and "basic land" in tl and not s:
        s = set(ci or FARBEN)
    return s


def mana_ertrag(text, ci):
    """Mana-Stein/-Kreatur: (Menge je Tap, Farben). 'Add {C}{C}' -> (2, {}), 'any color' -> (1, Farbidentität)."""
    tl = (text or "").lower()
    m = re.search(r"\{t\}[^.]*?: add ([^.]*)", tl)
    if not m:
        return 0, set()
    teil = m.group(1)
    if "any color" in teil or "any type" in teil or "chosen color" in teil:
        return 1, set(ci or FARBEN)
    syms = re.findall(r"\{([wubrgc])\}", teil)
    menge = len(syms) if " or " not in teil else 1
    return max(menge, 1), {s.upper() for s in syms if s != "c"}


def sim_karte(c, rollen, ci):
    """Karten-Dict aus der Datenbank (deckbau.card) + Rollen -> kompaktes Dict für die Simulation."""
    typ = (c.get("type_line") or "")
    vorne, _, hinten = typ.partition(" // ")
    text = c.get("text") or ""
    tl = text.lower()
    gen, pips, mv = manakosten(c.get("mana_cost"))
    k = {"name": c["name"], "mv": c.get("cmc") or mv, "gen": gen, "pips": pips, "art": "zauber"}
    if "Land" in vorne:
        k["art"] = "land"
    elif "Land" in hinten:
        k["art"] = "mdfc"
    if k["art"] in ("land", "mdfc"):
        k["farben"] = land_farben(text, c.get("produced"), ci)
        getappt = "enters tapped" in tl or "enters the battlefield tapped" in tl or (
            "search your library" in tl and "tapped" in tl)
        k["getappt"] = "bedingt" if getappt and "unless" in tl else bool(getappt) or k["art"] == "mdfc"
        return k
    if "ramp" in rollen:
        menge, farben = mana_ertrag(text, ci)
        if menge and "Creature" in vorne:
            k.update(art="dork", menge=menge, farben=farben)
        elif menge:
            k.update(art="stein", menge=menge, farben=farben, getappt="enters tapped" in tl)
        elif re.search(r"(land|forest|plains|island|swamp|mountain)[^.]*onto the battlefield", tl):
            k.update(art="landramp", getappt="tapped" in tl.split("onto the battlefield")[1][:12]
                     if "onto the battlefield" in tl else True, farben=set(ci or FARBEN))
    return k


# ----------------------------------------------------------------- Bezahlen
def bezahle(gen, pips, quellen):
    """quellen: Liste von Farbmengen (je eine Mana-Einheit). Gierige Zuordnung, knappe Farben zuerst.
    -> verbleibende Quellen oder None, wenn es nicht reicht."""
    if len(quellen) < gen + sum(pips.values()):
        return None
    frei = sorted(quellen, key=len)
    for farbe, n in sorted(pips.items(), key=lambda x: sum(1 for q in quellen if x[0] in q)):
        for _ in range(n):
            idx = next((i for i, q in enumerate(frei) if farbe in q), None)
            if idx is None:
                return None
            frei.pop(idx)
    if len(frei) < gen:
        return None
    frei.sort(key=len, reverse=True)                     # generisch mit den am wenigsten vielseitigen Quellen zahlen
    return sorted(frei, key=len)[gen:] if gen else frei


def kann_zahlen(gen, pips, quellen):
    return bezahle(gen, pips, quellen) is not None


# ----------------------------------------------------------------- Ein Spiel
def ist_land(k):
    return k["art"] in ("land", "mdfc")


def behalten(hand, mulligans):
    land = sum(1 for k in hand if ist_land(k))
    ramp_frueh = any(k["art"] in ("stein", "dork", "landramp") and k["mv"] <= 2 for k in hand)
    if mulligans >= 3:
        return True
    if mulligans == 2:
        return 2 <= land <= 5
    return 3 <= land <= 5 or (land == 2 and ramp_frueh)


def unter_bibliothek(hand, n):
    """n Karten zurück: überzählige Länder (über 4), sonst die teuersten Nichtländer. -> (Hand, zurückgelegt)."""
    hand, zurueck = list(hand), []
    for _ in range(n):
        laender = [i for i, k in enumerate(hand) if ist_land(k)]
        if len(laender) > 4:
            i = laender[-1]
        else:
            rest = [i for i, k in enumerate(hand) if not ist_land(k)] or list(range(len(hand)))
            i = max(rest, key=lambda j: hand[j]["mv"])
        zurueck.append(hand.pop(i))
    return hand, zurueck


def spiel(deck, commander, rng, zuege):
    """-> dict mit Mulligans, Ländern/Mana je Zug, Commander-Zug, Farbproblem, gesehene Länder."""
    mull = 0
    while True:
        rng.shuffle(deck)
        if behalten(deck[:7], mull):
            break
        mull += 1
    hand, zurueck = unter_bibliothek(deck[:7], max(0, mull - 1))        # 103.5c: erster Mulligan frei
    bib = deck[7:] + zurueck
    feld_land, steine, dorks, dorks_neu = [], [], [], []
    cmd_zug, farbproblem = None, False
    laender_zug, mana_zug = [], []
    gesehen_land = sum(1 for k in hand if ist_land(k))
    for zug in range(1, zuege + 1):
        karte = bib.pop(0)                                              # 103.8c: auch im ersten Zug ziehen
        hand.append(karte)
        gesehen_land += ist_land(karte)
        dorks += dorks_neu
        dorks_neu = []
        for l in feld_land:
            l["bereit"] = True
        laender = [k for k in hand if k["art"] == "land"] or [k for k in hand if k["art"] == "mdfc"]
        if laender:
            def getappt(k):
                return k["getappt"] is True or (k["getappt"] == "bedingt" and zug <= 2)
            laender.sort(key=lambda k: (getappt(k), -len(k["farben"])))
            l = laender[0]
            hand.remove(l)
            feld_land.append({"farben": l["farben"], "bereit": not getappt(l)})
        quellen = [l["farben"] or {"C"} for l in feld_land if l["bereit"]]
        for x in steine + dorks:
            quellen += [x["farben"] or {"C"}] * x["menge"]
        mana_zug.append(len(quellen))
        for k in sorted([k for k in hand if k["art"] in ("stein", "dork", "landramp")], key=lambda k: k["mv"]):
            rest = bezahle(k["gen"], k["pips"], quellen)
            if rest is None:
                continue
            quellen = rest
            hand.remove(k)
            if k["art"] == "stein":
                steine.append(k)
                if not k.get("getappt"):
                    quellen += [k["farben"] or {"C"}] * k["menge"]
            elif k["art"] == "dork":
                dorks_neu.append(k)
            else:
                feld_land.append({"farben": k["farben"], "bereit": not k["getappt"]})
                if not k["getappt"]:
                    quellen.append(k["farben"])
        if cmd_zug is None and commander:
            if bezahle(commander["gen"], commander["pips"], quellen) is not None:
                cmd_zug = zug
            elif len(quellen) >= commander["mv"]:
                farbproblem = True
        laender_zug.append(len(feld_land))
    return {"mull": mull, "laender": laender_zug, "mana": mana_zug, "cmd": cmd_zug,
            "farbe": farbproblem and cmd_zug is None, "gesehen_land": gesehen_land}


def simuliere(deck, commander, n=10000, seed=1, zuege=None):
    """deck: 99 Sim-Karten (sim_karte), commander: Sim-Karte (bei Partnern die teurere) oder None -> Kennzahlen."""
    rng = random.Random(seed)
    deck = list(deck)
    zuege = zuege or max(5, int(commander["mv"]) + 1 if commander else 5)   # Commander mit MV 5 → bis Zug 6
    erg = [spiel(deck, commander, rng, zuege) for _ in range(n)]
    def anteil(f):
        return round(sum(1 for e in erg if f(e)) / n, 3)
    mv = int(commander["mv"]) if commander else None
    k = {
        "n": n, "seed": seed, "zuege": zuege,
        "ohne_mulligan": anteil(lambda e: e["mull"] == 0),
        "zwei_plus_mulligans": anteil(lambda e: e["mull"] >= 2),
        "landdrops_bis_4": anteil(lambda e: all(e["laender"][t - 1] >= t for t in range(1, min(4, zuege) + 1))),
        "fehlstart": anteil(lambda e: e["laender"][min(3, zuege) - 1] < 3),
        "ueberflutung": anteil(lambda e: e["gesehen_land"] >= 8),
        "mana": [round(sum(e["mana"][t] for e in erg) / n, 2) for t in range(zuege)],
        "mana4_in_zug3": anteil(lambda e: zuege >= 3 and e["mana"][2] >= 4),
    }
    if commander:
        k.update(commander_mv=mv,
                 commander_puenktlich=anteil(lambda e: e["cmd"] is not None and e["cmd"] <= max(mv, 1)),
                 commander_plus1=anteil(lambda e: e["cmd"] is not None and e["cmd"] <= max(mv, 1) + 1),
                 commander_bis_zug=anteil(lambda e: e["cmd"] is not None),
                 farbproblem=anteil(lambda e: e["farbe"]))
    return k


# Vorläufige Schwellen – festgelegt nach der ersten Messung am 29.10.2026 (drei Commander-Decks des Admin-Projekts): Mulligan 9–13 % zwei+, Landdrops 85–91 %, Fehlstart 3–5 %, Commander +1 73–83 %,
# Farbproblem 0,5–9 %. Nach weiteren Abnahmen nachschärfen (08, Bracket-3-Abnahme).
SCHWELLEN = {
    "zwei_plus_mulligans": (0.15, "≤", "zwei oder mehr Mulligans (echter Kartenverlust)"),
    "landdrops_bis_4": (0.80, "≥", "Landdrops in Zug 1–4"),
    "fehlstart": (0.08, "≤", "weniger als 3 Länder in Zug 3"),
    "commander_plus1": (0.70, "≥", "Commander spätestens einen Zug nach seinem MV"),
    "farbproblem": (0.08, "≤", "genug Mana, falsche Farben für den Commander"),
}


def bewerte(k):
    """-> Liste (Kennzahl, Wert, Schwelle, ok) für die Abnahme."""
    out = []
    for key, (s, op, text) in SCHWELLEN.items():
        if key not in k:
            continue
        ok = k[key] >= s if op == "≥" else k[key] <= s
        out.append((text, k[key], f"{op} {s * 100:.0f} %", ok))
    return out


def tabelle(k):
    pct = lambda x: f"{x * 100:.1f} %".replace(".", ",")
    zeilen = [("Hände ohne Mulligan", pct(k["ohne_mulligan"])),
              ("zwei oder mehr Mulligans", pct(k["zwei_plus_mulligans"])),
              ("Landdrops in Zug 1–4 getroffen", pct(k["landdrops_bis_4"])),
              ("Fehlstart (< 3 Länder in Zug 3)", pct(k["fehlstart"])),
              ("Überflutung (≥ 8 Länder in 12 Karten)", pct(k["ueberflutung"])),
              ("Ø Mana verfügbar in Zug " + "/".join(str(i + 1) for i in range(k["zuege"])),
               " / ".join(f"{m:.1f}".replace(".", ",") for m in k["mana"])),
              ("≥ 4 Mana in Zug 3", pct(k["mana4_in_zug3"]))]
    if "commander_mv" in k:
        zeilen += [(f"Commander (MV {k['commander_mv']}) pünktlich", pct(k["commander_puenktlich"])),
                   ("Commander spätestens einen Zug später", pct(k["commander_plus1"])),
                   (f"Commander bis Zug {k['zuege']}", pct(k["commander_bis_zug"])),
                   ("genug Mana, aber falsche Farben", pct(k["farbproblem"]))]
    return zeilen


def aus_deck(con, pfad):
    """Deckdatei -> (99 Sim-Karten, Commander-Sim-Karte, Commander-Namen). Braucht deckbau.py und mtg.sqlite."""
    import deckbau as D
    cmdr, main, unbekannt, _ = D.lies_deck(con, pfad)
    if unbekannt:
        print("nicht erkannt (fehlen in der Simulation): " + ", ".join(unbekannt), file=sys.stderr)
    ci = "".join(sorted(set("".join(c["ci"] for _, c in cmdr)))) if cmdr else ""
    deck = []
    for q, c in main:
        k = sim_karte(c, D.rollen(con, c), ci)
        deck += [k] * q
    cs = [sim_karte(c, [], ci) for _, c in cmdr]
    return deck, (max(cs, key=lambda k: k["mv"]) if cs else None), [c["name"] for _, c in cmdr]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", help="Deckdatei oder Deckname (wie deckbau.py)")
    ap.add_argument("--n", type=int, default=10000, help="Anzahl Spiele (Standard 10.000)")
    ap.add_argument("--seed", type=int, default=1, help="Zufallsstart – gleicher Wert, gleiches Ergebnis")
    ap.add_argument("--zuege", type=int, help="Züge je Spiel (Standard: 5, bei teurem Commander MV + 1)")
    ap.add_argument("--json", help="Kennzahlen zusätzlich als JSON-Datei")
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import deckbau as D
    con = D.db()
    pfad, _ = D.deck_aus_ref(con, a.deck)
    deck, cmd, namen = aus_deck(con, pfad)
    if len(deck) < 40:
        sys.exit(f"Zu wenige Karten für eine Simulation ({len(deck)})")
    k = simuliere(deck, cmd, a.n, a.seed, a.zuege)
    print(f"Simulation {os.path.basename(pfad)} | Commander: {' + '.join(namen) or '–'} | {len(deck)} Karten | "
          f"{a.n} Spiele, Seed {a.seed} | Regeln 103.5/103.5c/103.8c")
    for t, w in tabelle(k):
        print(f"  {t:44} {w}")
    print("\nSchwellen (vorläufig):")
    for t, w, s, ok in bewerte(k):
        print(f"  {'✓' if ok else '✗'} {t}: {w * 100:.1f} % ({s})".replace(".", ","))
    if a.json:
        json.dump(k, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"-> {a.json}")


if __name__ == "__main__":
    main()
