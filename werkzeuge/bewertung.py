#!/usr/bin/env python3
"""bewertung.py – Bewertungslogik für den Commander-Deckbau (eine Quelle für alle Werkzeuge, V1.6).

Keine Befehle – Bibliothek für deckbau.py, archetypen.py und simulation.py. Alle Funktionen arbeiten mit
einem einfachen Karten-Dict (Name, Typzeile, Oracle-Text, Schlüsselwörter, Scryfall-Funktionstags), damit
sie ohne Datenbank testbar sind (tests/).

Inhalt
  1. Rollen mit Qualitätsregeln   rollen_detail() – Ramp, Kartenvorteil, gezielte/Massen-Interaktion, Schutz,
                                  Tutor, Rekursion; mit Ausschlüssen (symmetrischer Ramp, Rituale, Landsuche ist
                                  kein Tutor, Removal nur gegen Spieler/Planeswalker, Path to Exile u. Ä.)
  2. Wert für einen Commander     wert_edhrec() (None = nicht auf der EDHREC-Seite = unbekannt, nicht schwach),
                                  gesamtwert() = max(EDHREC-Wert, Oracle-Schätzung)
  3. Synergie                      commander_profil() + karte_bezug(): Auslöser und Ressourcen aus dem
                                  Commander-Text gegen Text, Typen und Tags jeder Karte → Bezug 0–1 mit „warum“
  4. Archetyp-Regeln               richtwerte() (Archetyp-Richtwert vor Template), zerstoert_plan()
                                  (eigene Wipes im Go-wide-Deck), GO_WIDE
  5. Kompromiss-Stufen, Klassen    funktionsgrad(), kompromiss_stufe(), wirkung(), klasse() (A–D aus 01, Abschnitt 6)

Grundsatz (08): EDHREC ist ein Anhaltspunkt. Entscheidend sind Oracle-Text, Rolle und Spielplan – deshalb
bewertet dieses Modul jede Karte zuerst aus Text und Funktionstags und nimmt EDHREC nur dazu.
"""
import math
import re

# ----------------------------------------------------------------- Karten-Sicht
TAGS_RAMP = {"ramp", "mana-rock", "mana-dork", "land-ramp"}
TAGS_KA = {"card-advantage", "draw"}
TAGS_SCHUTZ = {"protects-all", "protects-creature", "gives-indestructible", "gives-hexproof",
               "gives-protection", "protects-permanent"}
TAGS_REMOVAL_ZIEL = {"removal-creature", "removal-artifact", "removal-enchantment", "removal-nonland",
                     "removal-permanent", "removal-noncreature", "removal-aura", "removal-equipment", "removal-vehicle"}
ROLLEN_NAME = {"land": "Länder", "ramp": "Ramp", "ka": "Kartenvorteil", "gezielt": "Gezielte Interaktion",
               "massen": "Massen-Interaktion", "schutz": "Schutz", "tutor": "Tutor", "rekursion": "Rekursion"}
GENERISCHE_TYPEN = {"Creature", "Legendary", "Artifact", "Enchantment", "Snow", "Basic", "World", "Kindred",
                    "Tribal", "Token", "Land", "Instant", "Sorcery", "Planeswalker", "Battle", "Time", "Lord",
                    "Equipment", "Aura", "Vehicle", "Saga", "Class", "Case", "Room", "Food", "Treasure", "Clue"}


def sicht(name, typ, text, keywords, tags, cmc=None, pt=None):
    """Einheitliches Karten-Dict für dieses Modul (deckbau: type_line/keywords-Text, archetypen: typ/kw-Menge)."""
    if isinstance(keywords, str):
        kw = {k.strip().lower() for k in keywords.split(",") if k.strip()}
    else:
        kw = {k.lower() for k in (keywords or ())}
    return {"name": name or "", "typ": typ or "", "text": text or "", "tl": (text or "").lower(), "kw": kw,
            "t": set(tags or ()), "cmc": cmc or 0, "pt": pt}


def vorne(k):
    return k["typ"].split(" // ")[0]


def ist_land(k):
    return "Land" in vorne(k)


def ist_kreatur(k):
    return "Creature" in vorne(k)


def ist_spontan(k):
    return any(x in vorne(k) for x in ("Instant", "Sorcery"))


def untertypen(k):
    """Kreatur-Untertypen der Vorderseite, z. B. {'Orc', 'Warrior'}."""
    t = vorne(k)
    if "—" not in t:
        return set()
    return {w for w in t.split("—", 1)[1].split() if w not in GENERISCHE_TYPEN}


# ----------------------------------------------------------------- 1. Rollen mit Qualitätsregeln
RX_GEGNER_SUCHT = re.compile(r"(its controller|that player|their controller)[^.]*search")
RX_SUCHE = re.compile(r"search (?:your|their|its owner's) library for ([^.]*?)(?:card|cards)\b")
LANDWORT = r"(land|forest|plains|island|swamp|mountain|gate|desert)"
RX_LAND_AUFS_FELD = re.compile(LANDWORT + r"( cards?|s)?\b[^.]*onto the battlefield")
RX_MANA = re.compile(r"\badds?\b[^.]*(\{[wubrgcsx0-9]\}|mana)")


RX_EXTRA_LAND = re.compile(r"play (an|two|three) additional lands?")
RX_MANA_NUR_TYP = re.compile(r"[Ss]pend this mana only to cast ([A-Z][a-z]+) spells")


def _ramp_ok(k, hinweis, typen=frozenset()):
    t, tl = k["t"], k["tl"]
    if not t & TAGS_RAMP and not RX_EXTRA_LAND.search(tl):
        return False
    m = RX_MANA_NUR_TYP.search(k["text"])
    if m and m.group(1) not in typen:
        hinweis["ramp"] = f"Mana nur für {m.group(1)}-Zauber – zählt nur in einem {m.group(1)}-Deck"
        return False
    if t & {"removal", "spot-removal"} and RX_GEGNER_SUCHT.search(tl):
        hinweis["ramp"] = "gibt dem Gegner ein Land – kein Ramp"
        return False
    if "symmetrical" in t or "group-hug" in t or re.search(r"\b(each|a) player\b[^.]*\b(adds?|taps?)\b", tl):
        hinweis["ramp"] = "symmetrisch (alle Spieler bekommen Mana) – zählt nicht"
        return False
    if "ritual" in t:
        hinweis["ramp"] = "Ritual (einmalig) – zählt nicht"
        return False
    if ist_spontan(k) and not (RX_LAND_AUFS_FELD.search(tl) or RX_EXTRA_LAND.search(tl)):
        hinweis["ramp"] = "einmaliger Effekt ohne Land aufs Feld – zählt nicht"
        return False
    if not (RX_MANA.search(tl) or RX_LAND_AUFS_FELD.search(tl) or RX_EXTRA_LAND.search(tl) or "treasure" in tl or "cost-reducer" in " ".join(t)
            or re.search(r"costs? \{\d\} less", tl)):
        hinweis["ramp"] = "erzeugt kein Mana und bringt kein Land aufs Feld – zählt nicht"
        return False
    return True


def _gezielt_ok(k, hinweis):
    t = k["t"]
    if "counterspell" in t or "spot-removal" in t:
        return True
    if "removal" in t and "sweeper" not in t:
        if t & TAGS_REMOVAL_ZIEL:
            return True
        hinweis["gezielt"] = "trifft nur Spieler oder Planeswalker – zählt nicht"
    return False


def _tutor_ok(k, hinweis):
    if "tutor" not in k["t"]:
        return False
    suchen = RX_SUCHE.findall(k["tl"])
    if suchen and all(re.search(LANDWORT, s) for s in suchen):
        hinweis["tutor"] = "sucht nur Länder – kein Tutor (zählt als Ramp)"
        return False
    return True


def rollen_detail(k, typen=frozenset()):
    """-> (Rollen-Liste, Hinweise {Rolle: Grund für den Ausschluss}). Länder haben nur die Rolle 'land'.
    typen: Kreaturtypen, um die das Deck spielt (Commander-Profil) – Mana nur für diese Typen zählt dann als Ramp."""
    hinweis = {}
    if ist_land(k):
        return ["land"], hinweis
    t = k["t"]
    r = []
    if _ramp_ok(k, hinweis, typen):
        r.append("ramp")
    if t & TAGS_KA:
        r.append("ka")
    if _gezielt_ok(k, hinweis):
        r.append("gezielt")
    if "sweeper" in t:
        r.append("massen")
    if t & TAGS_SCHUTZ:
        r.append("schutz")
    if _tutor_ok(k, hinweis):
        r.append("tutor")
    if "recursion" in t:
        r.append("rekursion")
    return r, hinweis


def rollen(k, typen=frozenset()):
    return rollen_detail(k, typen)[0]


def ist_instant_tempo(k):
    return "Instant" in vorne(k) or "flash" in k["kw"]


def symmetrischer_wipe(k):
    """Massen-Removal gegen Kreaturen, das auch die eigenen trifft."""
    t = k["t"]
    return "sweeper" in t and "sweeper-one-sided" not in t and bool(
        t & {"removal-creature", "removal-permanent", "removal-nonland"} or "creature" in k["tl"])


def interaktion_ziele(k):
    """Welche Ziele eine Interaktion trifft: {'kreatur', 'artefakt', 'verzauberung', 'friedhof', 'zauber'}."""
    t, z = k["t"], set()
    if not t & {"removal", "spot-removal", "counterspell", "sweeper", "hate-graveyard", "sweeper-graveyard"}:
        return z
    breit = bool(t & {"removal-nonland", "removal-permanent"})
    if breit or "removal-creature" in t:
        z.add("kreatur")
    if breit or "removal-artifact" in t:
        z.add("artefakt")
    if breit or "removal-enchantment" in t:
        z.add("verzauberung")
    if t & {"hate-graveyard", "sweeper-graveyard", "single-minded-graveyard-hate"}:
        z.add("friedhof")
    if "counterspell" in t:
        z.add("zauber")
    return z


# ----------------------------------------------------------------- 2. Wert für einen Commander
SCHAETZ_FAKTOR = 0.6          # Bezug 1,0 entspricht etwa einem EDHREC-Wert von 0,6 (solide Karte beim Commander)


def wert_edhrec(v):
    """EDHREC-Wert = Inclusion + 1,5 × Synergie (Commander-Seite mit Bracket-Filter); None = nicht gelistet."""
    if not v or v.get("inclusion") is None:
        return None
    return round((v["inclusion"] or 0) + 1.5 * (v.get("synergy") or 0), 3)


def rang_bonus(rank):
    """Allgemeine Spielstärke aus dem EDHREC-Rang (alle Decks): kleiner Zuschlag, nie ausschlaggebend."""
    r = rank or 999999
    return 0.08 if r <= 1000 else 0.05 if r <= 5000 else 0.02 if r <= 15000 else 0.0


def gesamtwert(edh, bezug, rank):
    """-> (Wert, Quelle). Wert = max(EDHREC-Wert, Schätzung aus Oracle-Bezug + Rangzuschlag).
    Quelle 'EDHREC' oder '≈ Bezug' (geschätzt, Karte nicht auf der EDHREC-Seite bzw. dort schwächer)."""
    schaetz = round(SCHAETZ_FAKTOR * (bezug or 0) + rang_bonus(rank), 3)
    if edh is not None and edh >= schaetz:
        return edh, "EDHREC"
    return schaetz, "≈ Bezug"


# ----------------------------------------------------------------- 3. Synergie: Commander-Profil und Bezug
# Jedes Thema: Erkennung im Commander-Text (erzeugt = der Commander liefert die Ressource, nutzt = er belohnt sie)
# und Prüfungen für Karten (geber = liefert die Ressource, nutzer = profitiert davon).
def _rx(*muster):
    return re.compile("|".join(muster))


def _t(k, *tags):
    return bool(k["t"] & set(tags))


RX_TOKEN_EIGEN = re.compile(r"\bcreates?\b[^.]*?\btokens?\b")
RX_TOKEN_FREMD = re.compile(r"(its controller|that player|target opponent|an opponent|each opponent|each player|its owner)"
                            r"[^.]*\bcreates?\b")


def _token_geber(k):
    if ist_land(k):
        return False
    if _t(k, "repeatable-creature-tokens"):          # „repeatable-token-generator“ zählt auch Clues/Food – nicht hier
        return True
    for satz in re.split(r"(?<=[.\n])", k["tl"]):
        if RX_TOKEN_EIGEN.search(satz) and "creature token" in satz and not RX_TOKEN_FREMD.search(satz):
            return True
    return False


def _token_nutzer(k):
    return _t(k, "anthem", "overrun", "token-doubler", "token-increaser", "synergy-token", "synergy-token-creature",
              "power-boost-to-all") or bool(re.search(r"tokens? you control|for each (creature )?token|"
                                                       r"creatures you control get \+", k["tl"]))


def _opfer_geber(k):
    return _t(k, "repeatable-sacrifice-outlet", "free-sacrifice-outlet", "sacrifice-outlet-creature",
              "sacrifice-outlet-token") or bool(re.search(r"sacrifice (a|another|one or more) (creature|token)", k["tl"]))


def _tod_nutzer(k):
    return bool(k["t"] & {"blood-artist-ability", "your-sacrifice-matters", "morbid", "sacrifice-matters"} or
                re.search(r"\b(another|a|one or more|each)( other)?( nontoken)? creatures?( tokens?)?"
                          r"( you control)? (dies|die|leaves? the battlefield)", k["tl"])
                or re.search(r"whenever (equipped|enchanted) creature dies", k["tl"]))


def _angriff_geber(k):
    return _t(k, "gives-haste", "extra-combat-phase") or bool(
        re.search(r"creatures you control (have|gain|get)[^.]*haste|additional combat phase|"
                  r"untap all (attacking )?creatures you control", k["tl"]))


def _angriff_nutzer(k):
    return _t(k, "attacking-matters") or bool(
        re.search(r"whenever (a|one or more|another)( other)? creatures? you control attacks?|whenever you attack|"
                  r"battle cry|myriad|exalted|attacking creatures you control", k["tl"]))


def _schaden_geber(k):
    return _t(k, "gives-evasion") or bool(re.search(
        r"creatures you control (have|gain|get)[^.]*(flying|trample|menace|can't be blocked|double strike)", k["tl"]))


def _schaden_nutzer(k):
    return bool(re.search(r"deals? combat damage to (a player|an opponent|one or more players)|"
                          r"are dealt combat damage", k["tl"]))


def _counter_geber(k):
    return _t(k, "gives-pp-counters", "repeatable-pp-counters", "gains-pp-counters")


def _counter_nutzer(k):
    return _t(k, "pp-counters-matter", "counters-matter", "counter-doubler", "counter-increaser") or "proliferate" in k["tl"]


def _leben_geber(k):
    return _t(k, "repeatable-lifegain", "gives-lifelink") or "lifelink" in k["kw"]


def _leben_nutzer(k):
    return _t(k, "lifegain-matters", "pridemate", "lifegain-to-damage", "lifegain-increaser")


def _land_geber(k):
    return _t(k, "extra-land", "play-additional-land") or (_t(k, "land-ramp") and not ist_land(k)) or (
        ist_land(k) and _t(k, "fetchland"))


def _land_nutzer(k):
    return _t(k, "landfall") or bool(re.search(r"whenever a land( you control)? enters", k["tl"]))


THEMEN = {
    # Schlüssel: (Anzeige, Commander erzeugt, Commander nutzt, Karte gibt, Karte nutzt, Grund-Wörter)
    "tokens": ("Tokens", _rx(r"\bcreates?\b[^.]*\btokens?\b", r"\bmobilize\b", r"\bpopulate\b", r"\bamass\b",
                             r"\bfabricate\b", r"\bincubate\b"),
               _rx(r"tokens? you control", r"whenever (a|one or more) (creature )?tokens?"),
               _token_geber, _token_nutzer, ("Token-Quelle", "Token-Payoff")),
    "tod": ("Opfern/Tod", _rx(r"sacrifice (it|that token|them|this creature)", r"\bmobilize\b"),
            _rx(r"\b(dies|die)\b", r"leaves the battlefield", r"whenever you sacrifice", r"\bsacrifice (a|another)"),
            _opfer_geber, _tod_nutzer, ("Opfer-Outlet", "Tod-Payoff")),
    "angriff": ("Angriff", _rx(r"\bmobilize\b", r"attacking"),
                _rx(r"whenever [^.]*\battacks?\b", r"\battacking\b", r"\bmobilize\b"),
                _angriff_geber, _angriff_nutzer, ("Angriff ermöglichen", "Angriffs-Trigger")),
    "kampfschaden": ("Kampfschaden", None, _rx(r"deals? combat damage to (a player|an opponent|one or more players)"),
                     _schaden_geber, _schaden_nutzer, ("Evasion", "Kampfschaden-Trigger")),
    "counters": ("+1/+1-Counter", _rx(r"put [^.]*\+1/\+1 counters?"), _rx(r"\+1/\+1 counters? on", r"with a \+1/\+1"),
                 _counter_geber, _counter_nutzer, ("Counter-Quelle", "Counter-Payoff")),
    "leben": ("Lifegain", _rx(r"\byou gain \w+ life", r"\blifelink\b"), _rx(r"whenever you gain life"),
              _leben_geber, _leben_nutzer, ("Lebens-Quelle", "Lifegain-Payoff")),
    "land": ("Länder/Landfall", _rx(r"play an additional land", r"put [^.]*land[^.]*onto the battlefield",
                                    r"search your library for an? (basic )?(land|forest|plains|island|swamp|mountain)"),
             _rx(r"\blandfall\b", r"whenever a land( you control)? enters", r"lands? you control"),
             _land_geber, _land_nutzer, ("Land-Ramp/Extra-Land", "Landfall")),
    "artefakte": ("Artefakte", _rx(r"create[^.]*artifact"), _rx(r"\bartifacts?\b(?! creature token)"),
                  lambda k: "Artifact" in vorne(k) and not ist_land(k),
                  lambda k: _t(k, "synergy-artifact", "artifact-count-matters"), ("Artefakt", "Artefakt-Payoff")),
    "verzauberungen": ("Verzauberungen", None, _rx(r"\benchantments?\b", r"\bconstellation\b", r"\bauras?\b"),
                       lambda k: "Enchantment" in vorne(k),
                       lambda k: _t(k, "enchantment-engine", "synergy-enchantment"),
                       ("Verzauberung", "Verzauberungs-Payoff")),
    "zauber": ("Spontanzauber/Hexereien", None,
               _rx(r"instant or sorcery", r"noncreature spells?", r"\bmagecraft\b", r"\bprowess\b"),
               ist_spontan, lambda k: _t(k, "synergy-instant", "synergy-sorcery") or "prowess" in k["kw"],
               ("Zauber", "Zauber-Payoff")),
    "friedhof": ("Friedhof", _rx(r"\bmill\b", r"\bdiscard\b"), _rx(r"from your graveyard", r"cards? in your graveyard"),
                 lambda k: _t(k, "mill-self", "loot", "rummage", "discard-outlet", "tutor-to-graveyard"),
                 lambda k: _t(k, "reanimate-creature", "mass-reanimation", "reanimate", "recursion")
                 or "from your graveyard" in k["tl"], ("Friedhof füllen", "Friedhof nutzen")),
    "etb": ("Eintritt/Blink", _rx(r"exile [^.]*then return", r"return [^.]* to the battlefield"),
            _rx(r"whenever (another|a|one or more)( nontoken)? creatures?( you control)? enters?", r"\bevoke\b"),
            lambda k: _t(k, "flicker", "flicker-creature", "flicker-permanent", "flicker-nonland"),
            lambda k: ist_kreatur(k) and bool(re.search(r"^when (this creature|[^.]*) enters", k["tl"], re.M)),
            ("Blink", "Eintritts-Wert")),
    "kreaturen": ("Kreaturen wirken", None, _rx(r"whenever you cast a creature spell", r"creature spells you cast"),
                  lambda k: ist_kreatur(k) and not ist_land(k),
                  lambda k: _t(k, "cost-reducer-creature") or bool(re.search(r"creature spells you cast cost", k["tl"])),
                  ("Kreatur", "Kreaturen-Payoff")),
    "ausruestung": ("Ausrüstung/Auren", None, _rx(r"\bequip(ped|ment)?\b", r"\benchanted creature\b", r"\bauras?\b"),
                    lambda k: any(x in vorne(k) for x in ("Equipment", "Aura")),
                    lambda k: _t(k, "synergy-equipment", "synergy-aura"), ("Ausrüstung/Aura", "Voltron-Payoff")),
    "legendaer": ("Legendär/Historic", None, _rx(r"\blegendary\b", r"\bhistoric\b"),
                  lambda k: "Legendary" in vorne(k), lambda k: bool(re.search(r"\blegendary\b|\bhistoric\b", k["tl"])),
                  ("legendär", "Legendär-Payoff")),
    "schatz": ("Treasure/Food/Clue", _rx(r"create[^.]*\b(treasure|food|clue)\b"),
               _rx(r"sacrifice (a|an) (artifact|treasure|food|clue)", r"\btreasures? you control\b"),
               lambda k: _t(k, "repeatable-treasures", "repeatable-artifact-tokens") or bool(
                   re.search(r"create[^.]*\b(treasure|food|clue)\b", k["tl"])),
               lambda k: bool(re.search(r"sacrifice (a|an) (artifact|treasure)", k["tl"])),
               ("Treasure-Quelle", "Artefakt opfern")),
    "fliegen": ("Flieger", _rx(r"creatures you control (have|gain) flying"), _rx(r"creatures? with flying"),
                lambda k: "flying" in k["kw"], lambda k: bool(re.search(r"creatures you control (have|gain) flying|"
                                                                        r"creatures? with flying", k["tl"])),
                ("Flieger", "Flieger-Payoff")),
}

# Breite „ist X“-Prüfungen (jede Kreatur, jedes Artefakt …) zählen auf der Geber-Seite nur anteilig
GEBER_FAKTOR = {"kreaturen": 0.5, "artefakte": 0.6, "verzauberungen": 0.6, "zauber": 0.6, "legendaer": 0.5,
                "fliegen": 0.5}

# EDHREC-Themen (Slug) → Thema dieses Moduls; zählen nur als Zusatzhinweis (Gewicht 0,4)
EDHREC_THEMA = {"tokens": "tokens", "aristocrats": "tod", "sacrifice": "tod", "plus-1-plus-1-counters": "counters",
                "counters": "counters", "lifegain": "leben", "landfall": "land", "lands-matter": "land",
                "artifacts": "artefakte", "enchantress": "verzauberungen", "auras": "ausruestung",
                "equipment": "ausruestung", "voltron": "ausruestung", "spellslinger": "zauber",
                "reanimator": "friedhof", "graveyard": "friedhof", "self-mill": "friedhof", "blink": "etb",
                "treasure": "schatz", "legends": "legendaer", "historic": "legendaer", "flying": "fliegen",
                "go-wide": "tokens", "combat": "angriff", "attack-triggers": "angriff"}


def _name_raus(text, name):
    """Eigenen Namen im Text durch '~' ersetzen (Kurzname vor dem Komma zählt mit)."""
    t = text
    for n in {name, name.split(",")[0], name.split(" // ")[0]}:
        if n and len(n) > 2:
            t = t.replace(n.lower(), "~")
    return t


LANDTYPEN = {"Forest", "Plains", "Island", "Swamp", "Mountain", "Desert", "Gate", "Cave", "Town", "Sphere"}


def kreaturtypen(typzeilen, mindestens=3):
    """Kreatur-Untertypen aus allen Typzeilen (Vorderseite); nur Typen mit ≥ `mindestens` Karten, ohne Landtypen –
    filtert Einzelfälle wie 'The' oder 'Forest' (Dryad Arbor) heraus."""
    from collections import Counter
    z = Counter()
    for tl in typzeilen:
        f = (tl or "").split(" // ")[0]
        if "—" in f and "Creature" in f.split("—")[0]:
            z.update(w for w in f.split("—", 1)[1].split() if w[:1].isupper())
    return frozenset(w for w, n in z.items() if n >= mindestens and w not in GENERISCHE_TYPEN | LANDTYPEN)


def token_typen(text):
    """Kreaturtypen der Tokens, die ein Text erzeugt: '1/1 red Warrior creature token' → {'Warrior'}."""
    out = set()
    for m in re.finditer(r"\b[\dX]+/[\dX]+ (?:[a-z]+ )*?((?:[A-Z][a-z]+ ?)+)(?:artifact |enchantment )?creature tokens?", text):
        out |= {w for w in m.group(1).split() if w not in GENERISCHE_TYPEN and w.lower() not in
                ("white", "blue", "black", "red", "green", "colorless")}
    return out


def commander_profil(commander, alle_typen=frozenset(), edhrec_themen=()):
    """commander: Liste von sicht()-Dicts (Partner = 2). -> Profil-Dict:
    themen {Schlüssel: {'erzeugt': bool, 'nutzt': bool, 'gewicht': 1.0|0.4, 'beleg': Textstück}},
    typen {Kreaturtyp: Gewicht} (1.0 = im Text genannt oder als Token erzeugt, 0.3 = nur eigener Typ)."""
    themen, typen = {}, {}
    for k in commander:
        tl = _name_raus(k["tl"], k["name"].lower())
        for key, (_, rx_erz, rx_nutzt, *_r) in THEMEN.items():
            e = bool(rx_erz and rx_erz.search(tl))
            n = bool(rx_nutzt and rx_nutzt.search(tl))
            if e or n:
                d = themen.setdefault(key, {"erzeugt": False, "nutzt": False, "gewicht": 1.0, "beleg": ""})
                d["erzeugt"] |= e
                d["nutzt"] |= n
                m = (rx_nutzt.search(tl) if n else rx_erz.search(tl))
                d["beleg"] = d["beleg"] or m.group(0)
        for typ in token_typen(k["text"]):
            typen[typ] = 1.0
        for typ in alle_typen:
            if typ[:1].isupper() and typ not in GENERISCHE_TYPEN and re.search(rf"\b{re.escape(typ)}s?\b", k["text"]):
                typen[typ] = 1.0
        for typ in untertypen(k):
            typen.setdefault(typ, 0.3)
    for slug in list(edhrec_themen)[:3]:
        key = EDHREC_THEMA.get(slug)
        if key and key not in themen:
            themen[key] = {"erzeugt": True, "nutzt": True, "gewicht": 0.4, "beleg": f"EDHREC-Thema {slug}"}
        elif not key and slug.endswith("s") and slug[:-1].title() in alle_typen and slug[:-1].title() not in typen:
            typen[slug[:-1].title()] = 0.4                       # z. B. EDHREC „warriors“ → Warrior
    return {"themen": themen, "typen": typen}


def karte_bezug(profil, k):
    """-> (Punkte, Gründe). Je Thema zählt die stärkere Seite der Karte; Gewicht nach Rolle des Commanders:
    nutzt der Commander die Ressource, wiegt eine Karte, die sie liefert, voll (1,0); liefert er sie, wiegt eine
    Karte, die davon profitiert, voll. Kreaturtypen: im Kartentext genannt 1,0 · Karte hat den Typ 0,5."""
    punkte, gruende = 0.0, []
    for key, d in profil["themen"].items():
        name, _, _, geber, nutzer, worte = THEMEN[key]
        try:
            g, n = geber(k), nutzer(k)
        except Exception:
            g, n = False, False
        w = 0.0
        if g:
            w = max(w, (1.0 if d["nutzt"] else 0.5) * GEBER_FAKTOR.get(key, 1.0))
        if n:
            w = max(w, 1.0 if d["erzeugt"] else 0.6)
        if w:
            punkte += w * d["gewicht"]
            gruende.append(worte[0] if g and (d["nutzt"] or not n) else worte[1])
    eigene = untertypen(k)
    wechsel = "changeling" in k["kw"]
    for typ, gw in sorted(profil["typen"].items(), key=lambda x: -x[1]):
        if re.search(rf"\b{re.escape(typ)}s?\b", k["text"]):
            punkte += 1.0 * gw
            gruende.append(f"{typ}-Bezug")
        elif typ in eigene or (wechsel and ist_kreatur(k)):
            punkte += 0.5 * gw
            gruende.append(f"ist {typ}")
    return round(punkte, 2), gruende


def bezug_norm(punkte):
    """Punkte → Bezug 0–1 (1,5 Punkte = 1,0; z. B. ein voll passendes Thema ≈ 0,67)."""
    return round(min(1.0, (punkte or 0) / 1.5), 2)


BEZUG_SPERRE = 0.5            # ab diesem Bezug verlässt eine Karte das Deck nicht automatisch (Raus-Sperre)


# ----------------------------------------------------------------- 4. Archetyp-Regeln
TEMPLATE = {"land": (35, 38), "ramp": (10, 12), "ka": (10, 12), "gezielt": (10, 12), "massen": (3, 6), "schutz": (2, 4)}
GO_WIDE = {"tokens", "aristokraten", "kindred", "counters", "voltron", "blink"}   # Plan hängt an eigenen Kreaturen


def richtwerte(archetyp=None, daten=None):
    """{Rolle: (Minimum, Ziel, Quelle)} – Archetyp-Richtwert vor Template (08, Vorrangregel).
    Minimum = Median der EDHREC-Durchschnittsdecks des Archetyps (abgerundet), Ziel = Minimum + 2 (Länder + 3)."""
    out = {r: (mn, z, "Template") for r, (mn, z) in TEMPLATE.items()}
    roll = ((daten or {}).get("archetypen", {}).get(archetyp or "", {}) or {}).get("rollen") or {}
    for r in TEMPLATE:
        m = roll.get(f"rolle.{r}")
        if m and m.get("median") is not None:
            mn = int(math.floor(m["median"]))
            if r == "massen":
                mn = max(mn, 1)
            out[r] = (mn, mn + (3 if r == "land" else 2), f"Archetyp {archetyp}")
    return out


def zerstoert_plan(k, archetyp):
    """True, wenn die Karte den eigenen Plan zerstört: symmetrischer Kreaturen-Wipe in einem Go-wide-Deck.
    Eine solche Karte zählt nicht für ihre Rolle und wird nicht vorgeschlagen (08, Vorrangregel)."""
    if archetyp == "tokens" and re.search(r"\bnontoken creatures\b", k["tl"]):
        return False                        # Hour of Reckoning u. Ä. verschonen Tokens – im Token-Deck einseitig
    return archetyp in GO_WIDE and symmetrischer_wipe(k)


# ----------------------------------------------------------------- 5. Kompromiss-Stufen und Klassen A–D
STUFEN = ("gleichwertig", "funktional, aber langsamer", "nur Platzhalter")


def funktionsgrad(k, rolle):
    """Wie gut erfüllt die Karte die Rolle (0–1)? Einfache, prüfbare Regeln je Rolle – Einschätzung."""
    t, tl, mv = k["t"], k["tl"], k["cmc"] or 0
    if rolle == "ramp":
        g = 1.0 if mv <= 2 else 0.8 if mv <= 3 else 0.5
        dauerhaft = bool(re.search(r"\{t\}[^.:]*: add", tl) or RX_LAND_AUFS_FELD.search(tl)
                         or re.search(r"costs? \{\d\} less", tl) or re.search(r"\bwhenever\b[^.]*(treasure|\badd)", tl))
        if not dauerhaft:                        # nur einmalig (Spawn, Treasure) oder an Bedingung geknüpft
            g -= 0.3
        return round(g if not ist_spontan(k) else min(g, 0.8), 2)
    if rolle == "ka":
        g = 1.0 if t & {"repeatable-draw", "draw-engine", "repeatable-card-advantage"} else 0.6
        return g - (0.2 if "cantrip" in t and g < 1 else 0)
    if rolle == "gezielt":
        breit = bool(t & {"removal-nonland", "removal-permanent"}) or "counterspell" in t
        g = 1.0 if breit else 0.8 if "removal-creature" in t else 0.6
        if re.search(r"(power|toughness|mana value) (\d|x) or (less|greater)|attacking or blocking|tapped creature", tl):
            g -= 0.2
        if not ist_instant_tempo(k):
            g -= 0.1
        if mv >= 4:
            g -= 0.1
        return max(round(g, 2), 0.2)
    if rolle == "massen":
        return 1.0 if "sweeper-one-sided" in t else 0.6
    if rolle == "schutz":
        return 1.0 if re.search(r"(creatures|permanents) you control", tl) else 0.6
    return 0.7


def kompromiss_stufe(frei_wert, frei_grad, kauf_wert=None):
    """Kompromiss-Stufe einer freien Karte gegenüber der besten Kauf-Alternative:
    q = ½ × Funktionsgrad + ½ × min(1, Wert frei / Wert Kauf) (ohne Kauf-Alternative: nur Funktionsgrad).
    q ≥ 0,8 gleichwertig · ≥ 0,5 funktional, aber langsamer · darunter nur Platzhalter."""
    if kauf_wert and kauf_wert > 0:
        q = 0.5 * frei_grad + 0.5 * min(1.0, max(frei_wert, 0) / kauf_wert)
    else:
        q = frei_grad
    return (STUFEN[0] if q >= 0.8 else STUFEN[1] if q >= 0.5 else STUFEN[2]), round(q, 2)


def aufpreis_satz(frei, kauf):
    """Ein Satz, was der Aufpreis bringt – aus den Daten (frei/kauf: dict name, wert, quelle, eur, cmc, instant)."""
    teile = [f"Wert {frei['wert']:.2f} → {kauf['wert']:.2f}".replace(".", ",")]
    if kauf.get("cmc") is not None and frei.get("cmc") is not None and kauf["cmc"] < frei["cmc"]:
        teile.append(f"MV {frei['cmc']:g} → {kauf['cmc']:g}")
    if kauf.get("instant") and not frei.get("instant"):
        teile.append("Instant statt Sorcery-Tempo")
    eur = kauf.get("eur") or 0
    return (f"{kauf['name']} für {eur:.2f} € bringt: ".replace(".", ",", 1) + ", ".join(teile)
            + (" (EDHREC)" if kauf.get("quelle") == "EDHREC" else ""))


def wirkung(wert, fuellt_rolle=False, gc=False):
    """Wirkung 1–5 (01, Abschnitt 6) aus dem Wert für diesen Commander; +1, wenn die Karte eine Rolle unter dem
    Minimum füllt. Einschätzung aus Daten – Claude prüft am Oracle-Text."""
    w = 1 if wert < 0.10 else 2 if wert < 0.25 else 3 if wert < 0.45 else 4 if wert < 0.70 else 5
    return min(5, w + (1 if fuellt_rolle else 0))


def klasse(wirk, eur, gc_zuviel=False, ersatz_80=False):
    """Klasse A–D (01, Abschnitt 6) aus Wirkung und Preis:
    D – bracket-schädlich (z. B. 4. Game Changer) oder Wirkung ≤ 2 bei ≥ 5 € ·
    A – Wirkung ≥ 4 und kein Ersatz mit 80 % der Wirkung für einen Bruchteil ·
    B – Euro je Wirkungspunkt über 1 ≤ 2 € (gutes Verhältnis) · sonst C – Luxus."""
    eur = eur or 0
    if gc_zuviel or (wirk <= 2 and eur >= 5):
        return "D"
    if wirk >= 4 and not ersatz_80:
        return "A"
    if eur / max(wirk - 1, 0.5) <= 2:
        return "B"
    return "C"
