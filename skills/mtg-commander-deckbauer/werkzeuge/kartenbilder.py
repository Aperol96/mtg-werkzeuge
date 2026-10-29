#!/usr/bin/env python3
"""Kartenbilder für das MTG-Projekt – Tauschübersicht und Deck-PDF mit Scryfall-Bildern.

Befehle
  tausch  Tauschübersicht (Pickliste) für eine Deckänderung, geordnet nach der Box-Ablage
          des Nutzers: Farbe = erstes farbiges Manasymbol von links (Mehrfarbige also bei
          ihrer ersten Farbe), darin eine Box je Kartentyp; Länder und Standardländer haben
          eigene Boxen.
  verkauf Verkaufs-PDF aus der Verkaufsliste von deckbau.py verkauf: Abschnitte Kat. 1 (ohne Bedenken) und
          Kat. 2 (mit Hinweis) mit Anzahl und Summe, je Karte Box-Etikett, Druck, Sprache, Preis und voller
          Hinweis (bis 2 Zeilen); Ordnung je Abschnitt = Box-Ablage. Zeile: K1 1 Name (SET) Nr | 4,14 € | DE | Hinweis
  deck    Deck-PDF: Deckblatt mit Kurzdaten, Commander mit Oracle-Text, Manakurve, Farben,
          danach alle Karten nach Kategorien.
  vorlage Markdown-Vorlage des Fazit-PDF ausgeben (Abschnitte wie in 08a_Lieferung-Buchen-Gegentest, Abschnitt 3).
  bericht Fazit-PDF (Fazit, Änderungen, Kennzahlen, Kartenerklärungen, Vorgehen, Moxfield-Anhang) aus einer
          Markdown-Datei im selben Design – Aufbau der Datei: Funktion bericht_pdf (Kopf zwischen ---,
          [kacheln] … [/kacheln], ## / ###, Absätze, - / 1. Listen, > Kasten (>! rot, >+ grün, >? blau),
          | Tabellen | (Zeile „| ## Gruppe |“ = Gruppenzeile), ``` Einfügeblock ```, <seitenumbruch>).

  lieferung  nach der Freigabe alles in einem Lauf: Fazit-PDF, Tauschübersicht (PDF + PNG, nur mit --alt), Deck-PDF und
          Einfügeblock als TXT – Angaben aus dem Kopf des Fazits (deckbau.py fazit), Bilder parallel, Handy-Größe
          (--druck = volle Auflösung). Bricht ab, solange Platzhalter ‹…› offen sind (--entwurf = Vorschau).
          python3 kartenbilder.py lieferung fazit.md --neu entwurf_drucke.txt --alt decks/<deck>.txt --out out/<deck>

Für alle Befehle: --stempel "TESTLAUF – nicht gebucht" (roter Stempel auf Seite 1), --mobil (kleinere Bilder,
PDF für das Handy, ≈ ein Viertel der Größe). Lange Titel werden verkleinert statt abgeschnitten.

Bilder: Scryfall, englische Druckversion (Edition + Nummer, falls angegeben; sonst bevorzugtes
Set bzw. Scryfall-Standarddruck). Ohne Bildserver zeichnet das Skript Platzhalter.

Tauschliste (Modus 1), eine Karte pro Zeile:
    +3 Fields of Strife (SOS) 255 | Sammlung | besitzt: Deutsch
    +1 Sol Ring | Deck: Mardu Surge
    +1 Swords to Plowshares | Kauf
    +10 Plains | Standardland | 9 frei, 1 kaufen
    -1 Luminous Bonds (GRN) 21 | Sammlung
  Kopfzeilen: # titel: …  # deck: …  # datum: …
  +  kommt ins Deck · -  geht aus dem Deck (zurück in die Box)

Datenbank (Modus 3, empfohlen): --db mtg.sqlite --alt <Soll-Stand> --neu <Entwurf> [--idee I-nnn] – Quelle, Druck
  und Sprache je Exemplar aus der Exemplar-Zuordnung von mtg_db.py (frei / anderes Deck / Kauf / Standardland).
  Die Tauschübersicht kommt immer zusätzlich als PNG (--ohne-png schaltet das ab).

Vergleich (Modus 2): --alt <Soll-Stand> --neu <Entwurf> erzeugt die Tauschliste selbst.
  Quelle je neuer Karte: frei in der Sammlung (--frei 07) → Sammlung; Standardland → Standardland
  (frei/kaufen); steckt in anderem Deck (--bestand 06) → Deck: <Name>; sonst Kauf.
  --vormerkungen + --idee I-nnn: die Vormerkungen genau dieser Idee zählen als frei.
  --haves Basis.csv [buchungen.csv]: eigene Druckversion und Sprache je Karte.

Beispiele
  python3 kartenbilder.py tausch tausch/boros.txt --out out/tausch_boros --png
  python3 kartenbilder.py tausch --alt decks/boros.txt --neu entwurf.txt --frei 07.csv \\
      --bestand 06.csv --vormerkungen data/vormerkungen.csv --idee I-001 \\
      --haves data/basis.csv data/buchungen.csv --deckname Boros --out out/tausch_boros
  python3 kartenbilder.py deck decks/mardu-surge.txt --set tdc --bracket "…" \\
      --beschreibung "…" --themen "…" --out out/deck_mardu-surge --png
"""
import argparse, csv, html, json, re, subprocess, sys, time, urllib.error, urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

HIER = Path(__file__).resolve().parent
UA = {"User-Agent": "MTG-Projekt-Kartenbilder/2.0", "Accept": "application/json"}
HEUTE = date.today().strftime("%d.%m.%Y")

# ---------------------------------------------------------------- Schriften
GF = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
DV = Path("/usr/share/fonts/truetype/dejavu")
SCHRIFTEN = {  # Name: (statische Datei, variable Quelle, Gewicht, Ersatz)
    "Titel": ("Cinzel-Bold.ttf", "cinzel/Cinzel%5Bwght%5D.ttf", 700, "DejaVuSerif-Bold.ttf"),
    "TitelM": ("Cinzel-Medium.ttf", "cinzel/Cinzel%5Bwght%5D.ttf", 500, "DejaVuSerif.ttf"),
    "Text": ("EBGaramond-Regular.ttf", "ebgaramond/EBGaramond%5Bwght%5D.ttf", 400, "DejaVuSerif.ttf"),
    "TextB": ("EBGaramond-SemiBold.ttf", "ebgaramond/EBGaramond%5Bwght%5D.ttf", 600, "DejaVuSerif-Bold.ttf"),
    "TextI": ("EBGaramond-Italic.ttf", "ebgaramond/EBGaramond-Italic%5Bwght%5D.ttf", 400, "DejaVuSerif-Italic.ttf"),
}


def schriften_laden(ordner):
    """Cinzel + EB Garamond (OFL, Google Fonts über GitHub); fehlen sie, DejaVu Serif."""
    ordner.mkdir(parents=True, exist_ok=True)
    for name, (datei, quelle, gewicht, ersatz) in SCHRIFTEN.items():
        ziel = ordner / datei
        if not ziel.exists():
            try:
                from fontTools.ttLib import TTFont as FT
                from fontTools.varLib.instancer import instantiateVariableFont
                roh = ordner / Path(quelle).name.replace("%5B", "[").replace("%5D", "]")
                if not roh.exists():
                    with urllib.request.urlopen(GF + quelle, timeout=30) as r:
                        roh.write_bytes(r.read())
                f = FT(str(roh)); instantiateVariableFont(f, {"wght": gewicht}, inplace=True); f.save(str(ziel))
            except Exception:
                ziel = DV / ersatz
        if ziel.parent == ordner:  # eigener PostScript-Name je Schnitt, sonst legt das PDF Bold/Medium/Regular zusammen
            try:
                from fontTools.ttLib import TTFont as FT
                f = FT(str(ziel)); ps = ziel.stem
                if f["name"].getDebugName(6) != ps:
                    for pid, eid, lid in ((3, 1, 0x409), (1, 0, 0)):
                        f["name"].setName(ps, 6, pid, eid, lid)
                        f["name"].setName(ps.replace("-", " "), 4, pid, eid, lid)
                    f.save(str(ziel))
            except Exception:
                pass
        pdfmetrics.registerFont(TTFont(name, str(ziel)))
    pdfmetrics.registerFont(TTFont("Sans", str(DV / "DejaVuSans-Bold.ttf")))
    # Ausweichschrift für Zeichen, die Cinzel/EB Garamond nicht haben (z. B. ①, ⚑, ✓) – siehe laeufe()
    pdfmetrics.registerFont(TTFont("Ersatz", str(DV / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("ErsatzB", str(DV / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily("Text", normal="Text", bold="TextB", italic="TextI", boldItalic="TextB")


# ---------------------------------------------------------------- Farben und Begriffe
PAPIER, PAPIER2, TINTE, GOLD, GOLD_H, NACHT, GRAU = (HexColor(x) for x in (
    "#F6F0E3", "#ECE2CC", "#2A2420", "#A6823A", "#DDBB63", "#1F1B18", "#6E655B"))
PIP = {"W": "#F7F1D3", "U": "#AFD3EC", "B": "#C7BEBA", "R": "#F0A487", "G": "#A3D1B2", "C": "#D4CDC8"}
FARBEN = ["W", "U", "B", "R", "G", "Farblos", "Land", "Standardland"]
FARBNAME = {"W": "Weiß", "U": "Blau", "B": "Schwarz", "R": "Rot", "G": "Grün", "Farblos": "Farblos",
            "Land": "Länder", "Standardland": "Standardländer"}
TYPEN = ["Kreatur", "Planeswalker", "Schlacht", "Spontanzauber", "Hexerei", "Artefakt", "Verzauberung", "Sonstige"]
TYP_EN = [("Creature", "Kreatur"), ("Planeswalker", "Planeswalker"), ("Battle", "Schlacht"),
          ("Instant", "Spontanzauber"), ("Sorcery", "Hexerei"), ("Artifact", "Artefakt"),
          ("Enchantment", "Verzauberung")]
KATEGORIEN = [("Kreatur", "Kreaturen"), ("Planeswalker", "Planeswalker"), ("Schlacht", "Schlachten"),
              ("Spontanzauber", "Spontanzauber"), ("Hexerei", "Hexereien"), ("Artefakt", "Artefakte"),
              ("Verzauberung", "Verzauberungen"), ("Sonstige", "Sonstige"), ("Land", "Länder"),
              ("Standardland", "Standardländer")]
TYP_PLURAL = dict(KATEGORIEN)
ABSCHNITTE = [  # Schlüssel, Überschrift, Farbe
    ("holen", "Aus der Sammlung holen", HexColor("#2E6B3F")),
    ("deck", "Aus anderem Deck nehmen", HexColor("#9A6A12")),
    ("raus", "Aus dem Deck nehmen – zurück in die Box", HexColor("#9C2F2A")),
    ("kauf", "Kaufen", HexColor("#2F4F86")),
    ("basic", "Standardländer", HexColor("#5E5850")),
]
SPRACHE = {"English": "Englisch", "German": "Deutsch", "French": "Französisch", "Italian": "Italienisch",
           "Spanish": "Spanisch", "Japanese": "Japanisch"}


# ---------------------------------------------------------------- Karten einlesen
ZEILE = re.compile(r"^\s*([+-])\s*(\d+)\s*x?\s+(.+?)\s*(?:\(([A-Za-z0-9]+)\)\s*([^\s|]+))?\s*(?:\|(.*))?$")
DECKZEILE = re.compile(r"^\s*(\d+)\s*x?\s+(.+?)\s*(?:[\(\[]([A-Za-z0-9]+)[\)\]]\s*([^\s*]+))?\s*(\*[FE]\*)?\s*$")


def ist_basic(name):
    return name.split(" // ")[0] in {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes",
                                      "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
                                      "Snow-Covered Mountain", "Snow-Covered Forest"}


def lies_deck(pfad):
    """Moxfield-/Soll-Stand-Format → (kopf, karten, commander). Commander: nach '// Commander'
    oder als letzter Block nach einer Leerzeile (Moxfield-Export)."""
    kopf, bloecke, akt, cmd_markiert, cmd = {}, [], [], False, []
    for roh in Path(pfad).read_text(encoding="utf-8").splitlines():
        z = roh.strip()
        if z.startswith("//"):
            t = z[2:].strip()
            if t.lower().startswith("commander"):
                cmd_markiert = True
            elif t.startswith("Soll-Stand:"):
                kopf["voll"] = t.split(":", 1)[1].strip()
            elif "Stand:" in t:
                for teil in t.split("|"):
                    teil = teil.strip()
                    if teil.startswith("Stand:"):
                        kopf["stand"] = teil.split(":", 1)[1].strip()
                    elif teil.upper().startswith("VORLÄUFIG"):
                        kopf["vorlaeufig"] = teil
            continue
        if not z:
            if akt:
                bloecke.append(akt); akt = []
            continue
        if re.match(r"^(Commander|Mainboard|Deck|Sideboard|Maybeboard|Tokens)\b", z, re.I):
            continue
        m = DECKZEILE.match(z)
        if not m:
            continue
        k = dict(anzahl=int(m.group(1)), name=m.group(2).strip(), set=(m.group(3) or "").lower(),
                 nummer=m.group(4) or "")
        (cmd if cmd_markiert else akt).append(k)
    if akt:
        bloecke.append(akt)
    karten = [k for b in bloecke for k in b]
    if not cmd and len(bloecke) > 1 and len(bloecke[-1]) <= 2 and sum(k["anzahl"] for k in karten) in (100, 99 + len(bloecke[-1])):
        cmd = bloecke[-1]; karten = [k for b in bloecke[:-1] for k in b]
    return kopf, karten, cmd


def lies_tauschliste(pfad):
    kopf, karten = {}, []
    for nr, roh in enumerate(Path(pfad).read_text(encoding="utf-8").splitlines(), 1):
        z = roh.strip()
        if not z:
            continue
        if z.startswith("#"):
            m = re.match(r"#\s*(\w+)\s*:\s*(.*)", z)
            if m:
                kopf[m.group(1).lower()] = m.group(2).strip()
            continue
        m = ZEILE.match(z)
        if not m:
            sys.exit(f"Zeile {nr} nicht lesbar: {roh}")
        vz, anz, name, ed, num, rest = m.groups()
        felder = [f.strip() for f in (rest or "").split("|")]
        quelle = felder[0] if felder and felder[0] else "Sammlung"
        karten.append(dict(anzahl=int(anz), name=name.strip(), set=(ed or "").lower(), nummer=num or "",
                           quelle=quelle, hinweis=felder[1] if len(felder) > 1 else "",
                           abschnitt=abschnitt_von(vz, quelle)))
    return kopf, karten


def abschnitt_von(vz, quelle):
    q = quelle.lower()
    if vz == "-":
        return "raus"
    if q.startswith("deck"):
        return "deck"
    if q.startswith("kauf"):
        return "kauf"
    if q.startswith("standard"):
        return "basic"
    return "holen"


def lies_liste(pfad):
    """06/07-CSV (erste Zeile Kommentar) → Liste von Dicts."""
    zeilen = [z for z in Path(pfad).read_text(encoding="utf-8-sig").splitlines()
              if z.strip() and not z.lstrip('"').startswith("#")]
    return list(csv.DictReader(zeilen))


def drucke_aus_haves(pfade):
    """Moxfield-Bestand (+ Journal) → je Name: Counter{(set, nummer, sprache, foil): anzahl}."""
    d = defaultdict(Counter)
    for p in pfade:
        for z in csv.DictReader(Path(p).read_text(encoding="utf-8-sig").splitlines()):
            try:
                n = int(z.get("Count") or 0)
            except ValueError:
                continue
            d[z["Name"]][(z["Edition"].lower(), z["Collector Number"], z.get("Language", ""), z.get("Foil", ""))] += n
    return {name: Counter({k: v for k, v in c.items() if v > 0}) for name, c in d.items()}


def vergleich_zu_tausch(a):
    _, alt, alt_cmd = lies_deck(a.alt)
    _, neu, neu_cmd = lies_deck(a.neu)
    def zaehl(lst):
        z = Counter()
        for k in lst:
            z[k["name"]] += k["anzahl"]
        return z
    c_alt, c_neu = zaehl(alt + alt_cmd), zaehl(neu + neu_cmd)
    druck_neu = {k["name"]: (k["set"], k["nummer"]) for k in neu + neu_cmd if k["set"]}
    frei = Counter()
    if a.frei:
        for z in lies_liste(a.frei):
            frei[z["Name"]] = int(float(z.get("frei") or 0))
    in_decks = {}
    if a.bestand:
        for z in lies_liste(a.bestand):
            in_decks[z["Name"]] = [d.strip() for d in (z.get("Decks") or "").split(",") if d.strip()]
            if not a.frei:
                frei[z["Name"]] = int(float(z.get("frei") or 0))
    if a.vormerkungen and a.idee:
        for z in csv.DictReader(Path(a.vormerkungen).read_text(encoding="utf-8").splitlines()):
            if z["Idee"].strip() == a.idee:
                frei[z["Name"].strip()] += int(z["Anzahl"])
    drucke = drucke_aus_haves(a.haves) if a.haves else {}

    def druck_und_sprache(name):
        c = drucke.get(name) or Counter()
        if name in druck_neu:
            s, n = druck_neu[name]
            passend = [(x, v) for x, v in c.items() if x[0] == s and x[1].lower() == n.lower()]
            if passend:
                (_, _, spr, foil), _ = max(passend, key=lambda t: t[1])
                return s, n, "besitzt: " + SPRACHE.get(spr, spr) + (" Foil" if foil else "")
            return s, n, ""
        if not c:
            return "", "", ""
        (s, n, spr, foil), _ = c.most_common(1)[0]
        hinweis = "besitzt: " + SPRACHE.get(spr, spr) + (" Foil" if foil else "")
        if len({(x[0], x[1]) for x in c}) > 1:
            hinweis += " · mehrere Drucke"
        return s, n, hinweis

    zeilen = []
    for name in sorted(set(c_neu) | set(c_alt)):
        diff = c_neu[name] - c_alt[name]
        if diff == 0:
            continue
        s, n, hinweis = druck_und_sprache(name)
        if diff < 0:
            zeilen.append(dict(anzahl=-diff, name=name, set=s, nummer=n, quelle="Sammlung",
                               hinweis=hinweis, abschnitt="raus"))
            continue
        if ist_basic(name):
            f = frei[name]
            zeilen.append(dict(anzahl=diff, name=name, set=s, nummer=n, quelle="Standardland",
                               hinweis=f"{min(f, diff)} frei, {max(0, diff - f)} kaufen" if a.frei or a.bestand else "",
                               abschnitt="basic"))
            continue
        nimm = min(diff, frei[name])
        if nimm:
            zeilen.append(dict(anzahl=nimm, name=name, set=s, nummer=n, quelle="Sammlung",
                               hinweis=hinweis, abschnitt="holen"))
        rest = diff - nimm
        if rest:
            andere = [d for d in in_decks.get(name, []) if d != a.deckname]
            if andere:
                zeilen.append(dict(anzahl=rest, name=name, set=s, nummer=n, quelle="Deck: " + andere[0],
                                   hinweis="Ersatz im abgebenden Deck nötig", abschnitt="deck"))
            else:
                zeilen.append(dict(anzahl=rest, name=name, set="", nummer="", quelle="Kauf",
                                   hinweis="", abschnitt="kauf"))
    return zeilen


def schreibe_tauschliste(pfad, kopf, karten):
    vz = {"raus": "-"}
    out = [f"# {k}: {v}" for k, v in kopf.items() if v]
    for k in karten:
        druck = f" ({k['set'].upper()}) {k['nummer']}" if k["set"] and k["nummer"] else ""
        teile = [k["quelle"]] + ([k["hinweis"]] if k["hinweis"] else [])
        out.append(f"{vz.get(k['abschnitt'], '+')}{k['anzahl']} {k['name']}{druck} | " + " | ".join(teile))
    Path(pfad).write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- Scryfall
def scryfall(karten, bevorzugt=""):
    """Ergänzt k['scry'] per /cards/collection (je 75); Set+Nummer > Name+bevorzugtes Set > Name."""
    def hole(ids):
        daten = []
        for i in range(0, len(ids), 75):
            req = urllib.request.Request("https://api.scryfall.com/cards/collection",
                                         data=json.dumps({"identifiers": ids[i:i + 75]}).encode(),
                                         headers={**UA, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r:
                daten += json.load(r).get("data", [])
            time.sleep(0.12)
        return daten

    def namen(c):
        return {c["name"].lower(), c["name"].split(" // ")[0].lower()}

    erste = []
    for k in karten:
        if k.get("set") and k.get("nummer"):
            erste.append({"set": k["set"], "collector_number": k["nummer"]})
        elif bevorzugt:
            erste.append({"name": k["name"].split(" // ")[0], "set": bevorzugt})
        else:
            erste.append({"name": k["name"].split(" // ")[0]})
    sn, ns, nn = {}, {}, {}
    for c in hole(erste):
        sn[(c["set"], c["collector_number"].lower())] = c
        for n in namen(c):
            ns[(n, c["set"])] = c; nn.setdefault(n, c)
    fehlend = [k for k in karten if not finde(k, sn, ns, nn, bevorzugt)]
    if fehlend:  # zweite Runde: nur Name
        for c in hole([{"name": k["name"].split(" // ")[0]} for k in fehlend]):
            for n in namen(c):
                nn.setdefault(n, c)
    for k in karten:
        k["scry"] = finde(k, sn, ns, nn, bevorzugt)
    return [k["name"] for k in karten if not k["scry"]]


def finde(k, sn, ns, nn, bevorzugt):
    n = k["name"].lower()
    if k.get("set") and k.get("nummer"):
        c = sn.get((k["set"], k["nummer"].lower()))
        if c:
            return c
    if bevorzugt and (n, bevorzugt) in ns:
        return ns[(n, bevorzugt)]
    return nn.get(n) or nn.get(n.split(" // ")[0])


def vorderseite(c):
    faces = c.get("card_faces") or []
    if faces and (c.get("layout") in ("transform", "modal_dfc", "split", "adventure", "flip", "prototype")
                  or not c.get("mana_cost") and faces[0].get("mana_cost")):
        f = faces[0]
        return f.get("type_line", c.get("type_line", "")), f.get("mana_cost", ""), f
    return c.get("type_line", ""), c.get("mana_cost", ""), c


def erste_farbe(mana):
    """Erstes farbiges Manasymbol von links ({R/W} → R, {W/P} → W); keins → Farblos."""
    for sym in re.findall(r"\{([^}]+)\}", mana or ""):
        for ch in sym:
            if ch in "WUBRG":
                return ch
    return "Farblos"


def typ_von(typzeile):
    vorne = typzeile.split(" // ")[0]
    if "Land" in vorne.split("—")[0]:
        return "Standardland" if "Basic" in vorne else "Land"
    for en, de in TYP_EN:
        if en in vorne.split("—")[0]:
            return de
    return "Sonstige"


def box(c, name=""):
    """Box-Ablage des Nutzers → (Farbe, Typ). Länder/Standardländer haben eigene Boxen."""
    if not c:
        return ("Standardland", "Standardland") if ist_basic(name) else ("Farblos", "Sonstige")
    typzeile, mana, _ = vorderseite(c)
    typ = typ_von(typzeile)
    if typ in ("Land", "Standardland"):
        return typ, typ
    return erste_farbe(mana), typ


def box_rang(b):
    return (FARBEN.index(b[0]), TYPEN.index(b[1]) if b[1] in TYPEN else 0)


def preis(c):
    p = (c or {}).get("prices") or {}
    for key in ("eur", "eur_foil", "eur_etched"):
        try:
            if p.get(key):
                return float(p[key])
        except ValueError:
            pass
    return None


def eur(x):
    return f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------- Bilder
def bild_url(c, groesse):
    if not c:
        return None
    quellen = [c] + (c.get("card_faces") or [])
    for q in quellen:
        if "image_uris" in q:
            return q["image_uris"].get(groesse) or q["image_uris"].get("normal")
    return None


class Bilder:
    def __init__(self, cache, mobil=False):
        self.cache = Path(cache); self.cache.mkdir(parents=True, exist_ok=True)
        self.gesperrt = False; self.echt = 0; self.platzhalter = 0; self.mobil = mobil

    def pfad(self, k, groesse="normal"):
        p = self._pfad(k, groesse)
        if not self.mobil:
            return p
        ziel = p.with_name(p.stem + "_m.jpg")      # Handy: kleinere JPEGs, PDF ≈ ein Viertel so groß
        if not ziel.exists():
            im = Image.open(p).convert("RGB")
            b = 480 if groesse == "large" else 230
            im.thumbnail((b, int(b * 1.4)))
            im.save(ziel, quality=72, optimize=True)
        return ziel

    def vorladen(self, karten, gross=(), parallel=8):
        """Lädt fehlende Bilder parallel in den Cache (statt nacheinander beim Zeichnen) – spart bei 100 Karten ≈ 2/3 der Zeit."""
        from concurrent.futures import ThreadPoolExecutor
        auftraege = []
        for k in karten:
            for g in (("normal", "large") if k in gross else ("normal",)):
                url = bild_url(k.get("scry"), g)
                if url:
                    datei = self.cache / f"{k['scry']['id']}_{g}.jpg"
                    if not datei.exists():
                        auftraege.append((url, datei))

        def hole(auftrag):
            url, datei = auftrag
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
                with urllib.request.urlopen(req, timeout=25) as r:
                    datei.write_bytes(r.read())
                return True
            except (urllib.error.URLError, OSError, TimeoutError):
                return False
        with ThreadPoolExecutor(parallel) as ex:
            ok = sum(ex.map(hole, auftraege))
        return ok, len(auftraege)

    def _pfad(self, k, groesse="normal"):
        c = k.get("scry")
        url = bild_url(c, groesse)
        if url and not self.gesperrt:
            datei = self.cache / f"{c['id']}_{groesse}.jpg"
            try:
                if not datei.exists():
                    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
                    with urllib.request.urlopen(req, timeout=25) as r:
                        datei.write_bytes(r.read())
                    time.sleep(0.03)
                self.echt += 1
                return datei
            except (urllib.error.URLError, OSError, TimeoutError):
                self.gesperrt = True
        self.platzhalter += 1
        datei = self.cache / f"platzhalter_{re.sub(r'[^A-Za-z0-9]+', '_', k['name'])[:60]}.jpg"
        if not datei.exists():
            platzhalter(k).save(datei, quality=88)
        return datei


def platzhalter(k, w=488, h=680):
    c = k.get("scry") or {}
    farbe, _ = box(c, k["name"])
    grund = PIP.get(farbe if farbe in PIP else "C")
    img = Image.new("RGB", (w, h), (31, 27, 24))
    d = ImageDraw.Draw(img)
    fb = ImageFont.truetype(str(DV / "DejaVuSerif-Bold.ttf"), 28)
    f = ImageFont.truetype(str(DV / "DejaVuSerif.ttf"), 22)
    d.rounded_rectangle([16, 16, w - 16, h - 16], radius=20, fill=grund)
    d.rectangle([34, 34, w - 34, 92], fill=(246, 240, 227))
    name = c.get("name", k["name"])
    while d.textlength(name, font=fb) > w - 100 and len(name) > 4:
        name = name[:-2] + "…" if not name.endswith("…") else name[:-3] + "…"
    d.text((46, 48), name, font=fb, fill=(30, 26, 22))
    d.rectangle([34, 108, w - 34, 380], fill=(236, 226, 204))
    d.text((w / 2, 244), "Bild nicht verfügbar", font=f, fill=(90, 80, 70), anchor="mm")
    typ, mana, _ = vorderseite(c) if c else ("", "", None)
    d.rectangle([34, 396, w - 34, 440], fill=(246, 240, 227))
    d.text((46, 406), (typ or "")[:34], font=f, fill=(30, 26, 22))
    d.rectangle([34, 456, w - 34, h - 60], fill=(246, 240, 227))
    d.text((46, 470), mana or "", font=f, fill=(60, 54, 48))
    d.text((46, h - 50), f"{(c.get('set') or k.get('set') or '').upper()} {c.get('collector_number', k.get('nummer', ''))}",
           font=f, fill=(30, 26, 22))
    return img


# ---------------------------------------------------------------- Zeichenhilfen
W, H = A4
RAND = 12 * mm


def seite_grund(c):
    c.setFillColor(PAPIER); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setStrokeColor(GOLD); c.setLineWidth(0.9); c.rect(6 * mm, 6 * mm, W - 12 * mm, H - 12 * mm)
    c.setStrokeColor(TINTE); c.setLineWidth(0.3); c.rect(7.3 * mm, 7.3 * mm, W - 14.6 * mm, H - 14.6 * mm)
    for x, y in ((6, 6), (W / mm - 6, 6), (6, H / mm - 6), (W / mm - 6, H / mm - 6)):
        raute(c, x * mm, y * mm, 1.8 * mm, GOLD)


def raute(c, x, y, r, farbe):
    p = c.beginPath(); p.moveTo(x, y + r); p.lineTo(x + r, y); p.lineTo(x, y - r); p.lineTo(x - r, y); p.close()
    c.setFillColor(farbe); c.drawPath(p, fill=1, stroke=0)


def zierlinie(c, x1, x2, y):
    c.setStrokeColor(GOLD); c.setLineWidth(0.6); c.line(x1, y, x2, y)
    raute(c, (x1 + x2) / 2, y, 1.3 * mm, GOLD)


def pip(c, x, y, r, sym):
    """Manasymbol als Kreis; x/y = Mittelpunkt. Hybrid wird geteilt gezeichnet."""
    teile = sym.split("/")
    farben = [t for t in teile if t in "WUBRG"]
    if len(farben) == 2:
        c.setFillColor(HexColor(PIP[farben[0]])); c.wedge(x - r, y - r, x + r, y + r, 45, 180, stroke=0, fill=1)
        c.setFillColor(HexColor(PIP[farben[1]])); c.wedge(x - r, y - r, x + r, y + r, 225, 180, stroke=0, fill=1)
        text = ""
    else:
        grund = farben[0] if farben else "C"
        c.setFillColor(HexColor(PIP[grund])); c.circle(x, y, r, fill=1, stroke=0)
        text = farben[0] if farben else ("◇" if sym == "C" else sym)
        if "P" in teile and farben:
            text = farben[0] + "ᵖ"
    c.setStrokeColor(TINTE); c.setLineWidth(0.35); c.circle(x, y, r, fill=0, stroke=1)
    if text:
        c.setFillColor(TINTE); c.setFont("Sans", r * 1.15)
        c.drawCentredString(x, y - r * 0.4, text)


def pips(c, x, y, mana, r):
    """Manakosten von links nach rechts ab x (linker Rand); gibt Breite zurück."""
    syms = re.findall(r"\{([^}]+)\}", mana or "")
    for i, s in enumerate(syms):
        pip(c, x + r + i * 2.3 * r, y, r, s)
    return len(syms) * 2.3 * r


ERSATZ = {"Titel": "ErsatzB", "TextB": "ErsatzB", "Sans": "ErsatzB"}   # sonst "Ersatz"
_GLYPHEN = {}


def _hat(font, ch):
    """Hat die Schrift ein Zeichen für ch? (TrueType-Tabelle; unbekannt → ja)"""
    k = (font, ch)
    if k not in _GLYPHEN:
        try:
            _GLYPHEN[k] = ord(ch) in pdfmetrics.getFont(font).face.charToGlyph
        except Exception:
            _GLYPHEN[k] = True
    return _GLYPHEN[k]


def laeufe(text, font):
    """Text in Abschnitte je Schrift zerlegen: Zeichen, die die Schrift nicht hat, kommen aus DejaVu Sans
    (sonst erscheinen sie im PDF als Kästchen – Befund Testlauf 29.10.2026)."""
    ers = ERSATZ.get(font, "Ersatz")
    out = []
    for ch in text:
        f = font if ch == " " or _hat(font, ch) or not _hat(ers, ch) else ers
        if out and out[-1][0] == f:
            out[-1][1] += ch
        else:
            out.append([f, ch])
    return out


def textbreite(text, font, size):
    return sum(stringWidth(t, f, size) for f, t in laeufe(text, font))


def schreibe(c, x, y, text, font, size, rechts=False):
    """drawString mit Ausweichschrift; rechts=True = rechtsbündig an x."""
    if rechts:
        x -= textbreite(text, font, size)
    for f, t in laeufe(text, font):
        c.setFont(f, size); c.drawString(x, y, t)
        x += stringWidth(t, f, size)


def kuerzen(text, font, size, breite_max):
    if textbreite(text, font, size) <= breite_max:
        return text
    while text and textbreite(text + "…", font, size) > breite_max:
        text = text[:-1]
    return text.rstrip() + "…"


def umbrechen(text, font, size, breite_max, zeilen=2):
    """Text auf höchstens `zeilen` Zeilen umbrechen; erst die letzte Zeile wird gekürzt."""
    worte, out = text.split(), []
    while worte and len(out) < zeilen:
        z = worte.pop(0)
        while worte and textbreite(z + " " + worte[0], font, size) <= breite_max:
            z += " " + worte.pop(0)
        out.append(z)
    if worte:
        out[-1] = kuerzen(out[-1] + " " + " ".join(worte), font, size, breite_max)
    return [kuerzen(z, font, size, breite_max) for z in out]


def passend(text, font, gross, klein, breite):
    """Schriftgröße so weit verkleinern, dass der Text passt (höchstens bis klein), erst dann kürzen."""
    g = gross
    while g > klein and stringWidth(text, font, g) > breite:
        g -= 0.5
    return g, kuerzen(text, font, g, breite)


ROT = HexColor("#9C2F2A")


def stempel(c, text, x=None, y=None, winkel=10):
    """Roter Stempel (z. B. „TESTLAUF – nicht gebucht“) schräg oben rechts auf Seite 1."""
    if not text:
        return
    c.saveState()
    c.translate(x or W - 48 * mm, y or H - 56 * mm)
    c.rotate(winkel)
    breite = stringWidth(text.upper(), "TitelM", 10) + 8 * mm
    c.setFillColor(HexColor("#FFFFFF")); c.setStrokeColor(ROT); c.setLineWidth(1.4)
    c.roundRect(-breite / 2, -4.6 * mm, breite, 9.2 * mm, 1.6 * mm, fill=1, stroke=1)
    c.setFillColor(ROT); c.setFont("TitelM", 10)
    c.drawCentredString(0, -1.5 * mm, text.upper())
    c.restoreState()


def kartenbild(c, pfad, x, y_oben, w, h):
    c.saveState()
    p = c.beginPath(); p.roundRect(x, y_oben - h, w, h, w * 0.045)
    c.clipPath(p, stroke=0, fill=0)
    c.drawImage(str(pfad), x, y_oben - h, w, h)
    c.restoreState()


def plakette(c, x, y, text, farbe, r=4.4 * mm):
    c.setFillColor(PAPIER); c.circle(x, y, r + 0.5 * mm, fill=1, stroke=0)
    c.setFillColor(farbe); c.circle(x, y, r, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF")); c.setFont("TextB", 10.5)
    c.drawCentredString(x, y - 1.5 * mm, text)


def fusszeile(c, links, seite):
    c.setFont("Text", 7.5); c.setFillColor(GRAU)
    c.drawString(RAND, 9.5 * mm, links)
    c.drawRightString(W - RAND, 9.5 * mm, f"Seite {seite}")


class Raster:
    """Kartenraster mit Seitenumbruch."""
    def __init__(self, c, spalten, abst, cap, kopf_fn, fuss_fn, oben_start):
        self.c, self.sp, self.abst, self.cap = c, spalten, abst, cap
        self.kw = (W - 2 * RAND - (spalten - 1) * abst) / spalten
        self.kh = self.kw * 88 / 63
        self.kopf_fn, self.fuss_fn = kopf_fn, fuss_fn
        self.y = oben_start; self.seite = 1

    def platz(self, hoehe):
        if self.y - hoehe < 15 * mm:
            self.fuss_fn(self.seite); self.c.showPage(); self.seite += 1
            seite_grund(self.c); self.y = self.kopf_fn()

    def zeile_karten(self, karten, zeichne):
        for i in range(0, len(karten), self.sp):
            self.platz(self.kh + self.cap)
            for j, k in enumerate(karten[i:i + self.sp]):
                zeichne(k, RAND + j * (self.kw + self.abst), self.y)
            self.y -= self.kh + self.cap + 2.5 * mm


# ---------------------------------------------------------------- Tauschübersicht
def tausch_pdf(kopf, karten, ziel, bilder):
    c = canvas.Canvas(str(ziel), pagesize=A4)
    c.setTitle(kopf.get("titel", "Tauschübersicht")); c.setAuthor("MTG-Projekt")
    seite_grund(c)
    titel = kopf.get("titel", "Tauschübersicht")
    deckzeile = kopf.get("deck", "")

    def kopf_folgeseite():
        c.setFont("TitelM", 9); c.setFillColor(GRAU)
        c.drawString(RAND, H - RAND - 2 * mm, kuerzen(titel.upper(), "TitelM", 9, W - 2 * RAND))
        zierlinie(c, RAND, W - RAND, H - RAND - 4.5 * mm)
        return H - RAND - 9 * mm

    def fuss(s):
        q = "Bilder: Scryfall, englische Druckversion" if not bilder.gesperrt else "Bilder teils Platzhalter (Bildserver nicht erreichbar)"
        fusszeile(c, f"{q} · erstellt {kopf.get('datum', HEUTE)}", s)

    # Kopf Seite 1
    y = H - RAND
    c.setFillColor(TINTE)
    g, t = passend(titel, "Titel", 19, 12, W - 2 * RAND)
    c.setFont("Titel", g); c.drawString(RAND, y - 7 * mm, t)
    g, t = passend(" · ".join(x for x in [deckzeile, kopf.get("datum", HEUTE)] if x), "TextI", 11, 8, W - 2 * RAND)
    c.setFont("TextI", g); c.setFillColor(GRAU)
    c.drawString(RAND, y - 13 * mm, t)

    summen = [f"{t.split(' –')[0]}: {sum(k['anzahl'] for k in karten if k['abschnitt'] == s)}"
              for s, t, _ in ABSCHNITTE if any(k["abschnitt"] == s for k in karten)]
    c.setFont("Text", 10.5); c.setFillColor(TINTE)
    c.drawString(RAND, y - 19 * mm, "   ·   ".join(summen))
    stempel(c, kopf.get("stempel"), W - RAND - 32 * mm, y - 18 * mm, 4)
    zierlinie(c, RAND, W - RAND, y - 22.5 * mm)
    r = Raster(c, 4, 5 * mm, 15 * mm, kopf_folgeseite, fuss, y - 28 * mm)

    for key, titel_ab, farbe in ABSCHNITTE:
        teil = [k for k in karten if k["abschnitt"] == key]
        if not teil:
            continue
        r.platz(10 * mm + r.kh + r.cap)
        c.setFillColor(farbe); c.rect(RAND, r.y - 6.5 * mm, 2.4 * mm, 6.5 * mm, fill=1, stroke=0)
        c.setFillColor(TINTE); c.setFont("Titel", 12.5)
        c.drawString(RAND + 5 * mm, r.y - 5.2 * mm, titel_ab)
        c.setFont("TextI", 10.5); c.setFillColor(GRAU)
        c.drawRightString(W - RAND, r.y - 5 * mm, f"{sum(k['anzahl'] for k in teil)} Karten")
        r.y -= 10 * mm
        # Reihenfolge = Box-Ablage (Farbe → Typ), beim Abschnitt "deck" nach Herkunftsdeck
        def rang(k):
            b = box(k.get("scry"), k["name"])
            vorne = (k["quelle"],) if key == "deck" else ()
            return vorne + box_rang(b) + (k["name"],)
        ks = sorted(teil, key=rang)

        def zeichne(k, x, y_oben, farbe=farbe, key=key):
            kartenbild(c, bilder.pfad(k), x, y_oben, r.kw, r.kh)
            if k["anzahl"] > 1 or key == "basic":
                plakette(c, x + r.kw - 6 * mm, y_oben - r.kh * 0.36, f"{k['anzahl']}×", farbe)
            sc = k.get("scry") or {}
            yc = y_oben - r.kh
            c.setFillColor(TINTE)
            schreibe(c, x, yc - 3.9 * mm, kuerzen(k["name"], "TextB", 9.2, r.kw), "TextB", 9.2)
            # Box-Etikett mit Farbsymbol
            etikett(c, x, yc - 7.9 * mm, r.kw, k, key)
            druck = f"{(sc.get('set') or k['set']).upper()} {sc.get('collector_number', k['nummer'])}".strip()
            selten = {"common": "C", "uncommon": "U", "rare": "R", "mythic": "M"}.get(sc.get("rarity", ""), "")
            c.setFillColor(GRAU)
            zeile = " · ".join(t for t in [druck, selten, k.get("hinweis", "")] if t)
            schreibe(c, x, yc - 11.7 * mm, kuerzen(zeile, "TextI", 7.8, r.kw), "TextI", 7.8)
        r.zeile_karten(ks, zeichne)
        r.y -= 2 * mm
    fuss(r.seite); c.save()


def etikett(c, x, y, breite, k, key):
    """Kleines Etikett unter der Karte: wohin greifen bzw. zurücklegen."""
    b = box(k.get("scry"), k["name"])
    if key == "deck":
        text, sym = "aus " + k["quelle"].split(":", 1)[-1].strip(), None
    elif b[0] in ("Land", "Standardland"):
        text, sym = "Box " + FARBNAME[b[0]], None
    else:
        text, sym = f"Box {FARBNAME[b[0]]} · {TYP_PLURAL.get(b[1], b[1])}", (b[0] if b[0] in "WUBRG" else "C")
    if key == "kauf":
        text = "später: " + text
    c.setFillColor(PAPIER2); c.setStrokeColor(GOLD); c.setLineWidth(0.4)
    c.roundRect(x, y - 1.3 * mm, breite, 4.4 * mm, 1.2 * mm, fill=1, stroke=1)
    tx = x + 1.6 * mm
    if sym:
        pip(c, x + 2.6 * mm, y + 0.9 * mm, 1.55 * mm, sym); tx = x + 5.3 * mm
    else:
        raute(c, x + 2.3 * mm, y + 0.9 * mm, 1.1 * mm, GOLD); tx = x + 4.6 * mm
    c.setFillColor(TINTE)
    schreibe(c, tx, y + 0.1 * mm, kuerzen(text, "Text", 8.4, breite - (tx - x) - 1 * mm), "Text", 8.4)


# ---------------------------------------------------------------- Verkaufsliste
VERKAUF_KAT = [  # Schlüssel, Überschrift, Farbe
    ("1", "Kat. 1 – ohne Bedenken verkaufen", HexColor("#2E6B3F")),
    ("2", "Kat. 2 – Verkauf möglich, mit Hinweis", HexColor("#9A6A12")),
]
VERKAUFSZEILE = re.compile(r"^\s*K([12])\s+(\d+)\s*x?\s+(.+?)\s*(?:\(([A-Za-z0-9]+)\)\s*([^\s|]+))?\s*(?:\|(.*))?$")


def euro_wert(text):
    m = re.search(r"(\d+(?:[.,]\d+)?)", text or "")
    return float(m.group(1).replace(",", ".")) if m else 0.0


def lies_verkaufsliste(pfad):
    """Verkaufsliste (deckbau.py verkauf): Kopf `# titel:` … und je Exemplar
    `K1 1 Name (SET) Nr | 4,14 € | DE | Hinweis` – K1 = ohne Bedenken, K2 = mit Hinweis."""
    kopf, karten = {}, []
    for nr, roh in enumerate(Path(pfad).read_text(encoding="utf-8").splitlines(), 1):
        z = roh.strip()
        if not z:
            continue
        if z.startswith("#"):
            m = re.match(r"#\s*(\w+)\s*:\s*(.*)", z)
            if m:
                kopf[m.group(1).lower()] = m.group(2).strip()
            continue
        m = VERKAUFSZEILE.match(z)
        if not m:
            sys.exit(f"Zeile {nr} nicht lesbar: {roh}")
        kat, anz, name, ed, num, rest = m.groups()
        f = [x.strip() for x in (rest or "").split("|")] + ["", "", ""]
        karten.append(dict(kat=kat, anzahl=int(anz), name=name.strip(), set=(ed or "").lower(), nummer=num or "",
                           preis=euro_wert(f[0]), preis_txt=f[0], sprache=f[1], hinweis=f[2], quelle="Sammlung",
                           abschnitt="holen"))
    return kopf, karten


def eur_de(x):
    return f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def verkauf_pdf(kopf, karten, ziel, bilder):
    """Verkaufs-PDF: Abschnitte je Kategorie mit Anzahl und Summe, je Karte Box-Etikett, Druck, Preis, Sprache
    und – bei Kat. 2 – der volle Hinweis (bis 2 Zeilen). Ordnung in jedem Abschnitt = Box-Ablage."""
    c = canvas.Canvas(str(ziel), pagesize=A4)
    titel = kopf.get("titel", "Verkaufsliste")
    c.setTitle(titel); c.setAuthor("MTG-Projekt")
    seite_grund(c)

    def kopf_folgeseite():
        c.setFillColor(GRAU)
        schreibe(c, RAND, H - RAND - 2 * mm, kuerzen(titel.upper(), "TitelM", 9, W - 2 * RAND), "TitelM", 9)
        zierlinie(c, RAND, W - RAND, H - RAND - 4.5 * mm)
        return H - RAND - 9 * mm

    def fuss(s):
        q = "Bilder: Scryfall, englische Druckversion" if not bilder.gesperrt else "Bilder teils Platzhalter"
        fusszeile(c, f"{q} · Preise: {kopf.get('preise', 'Cardmarket über Scryfall')} · erstellt "
                     f"{kopf.get('datum', HEUTE)}", s)

    summe = lambda ks: sum(k["preis"] * k["anzahl"] for k in ks)
    anzahl = lambda ks: sum(k["anzahl"] for k in ks)
    y = H - RAND
    c.setFillColor(TINTE)
    g, t = passend(titel, "Titel", 19, 12, W - 2 * RAND)
    schreibe(c, RAND, y - 7 * mm, t, "Titel", g)
    unter = " · ".join(x for x in [kopf.get("deck", ""), kopf.get("datum", HEUTE)] if x)
    g, t = passend(unter, "TextI", 11, 8, W - 2 * RAND)
    c.setFillColor(GRAU); schreibe(c, RAND, y - 13 * mm, t, "TextI", g)
    teile = [f"Kat. {s}: {anzahl([k for k in karten if k['kat'] == s])} · "
             f"{eur_de(summe([k for k in karten if k['kat'] == s]))}" for s, _, _ in VERKAUF_KAT
             if any(k["kat"] == s for k in karten)]
    teile.append(f"zusammen {anzahl(karten)} Karten · {eur_de(summe(karten))}")
    platz = W - 2 * RAND - (66 * mm if kopf.get("stempel") else 0)     # Stempel nicht überdecken
    c.setFillColor(TINTE)
    schreibe(c, RAND, y - 19 * mm, kuerzen("   ·   ".join(teile), "Text", 10.5, platz), "Text", 10.5)
    stempel(c, kopf.get("stempel"), W - RAND - 32 * mm, y - 18 * mm, 4)
    zierlinie(c, RAND, W - RAND, y - 22.5 * mm)
    r = Raster(c, 4, 5 * mm, 15 * mm, kopf_folgeseite, fuss, y - 28 * mm)
    for key, titel_ab, farbe in VERKAUF_KAT:
        teil = [k for k in karten if k["kat"] == key]
        if not teil:
            continue
        r.cap = 21.5 * mm if any(k["hinweis"] for k in teil) else 15 * mm   # Platz für 2 Zeilen Hinweis
        r.platz(10 * mm + r.kh + r.cap)
        c.setFillColor(farbe); c.rect(RAND, r.y - 6.5 * mm, 2.4 * mm, 6.5 * mm, fill=1, stroke=0)
        c.setFillColor(TINTE); schreibe(c, RAND + 5 * mm, r.y - 5.2 * mm, titel_ab, "Titel", 12.5)
        c.setFillColor(GRAU)
        schreibe(c, W - RAND, r.y - 5 * mm, f"{anzahl(teil)} Karten · {eur_de(summe(teil))}", "TextI", 10.5, rechts=True)
        r.y -= 10 * mm
        ks = sorted(teil, key=lambda k: box_rang(box(k.get("scry"), k["name"])) + (k["name"],))

        def zeichne(k, x, y_oben, farbe=farbe):
            kartenbild(c, bilder.pfad(k), x, y_oben, r.kw, r.kh)
            if k["anzahl"] > 1:
                plakette(c, x + r.kw - 6 * mm, y_oben - r.kh * 0.36, f"{k['anzahl']}×", farbe)
            sc = k.get("scry") or {}
            yc = y_oben - r.kh
            c.setFillColor(TINTE)
            schreibe(c, x, yc - 3.9 * mm, kuerzen(k["name"], "TextB", 9.2, r.kw), "TextB", 9.2)
            etikett(c, x, yc - 7.9 * mm, r.kw, k, "holen")
            druck = f"{(sc.get('set') or k['set']).upper()} {sc.get('collector_number', k['nummer'])}".strip()
            zeile = " · ".join(t for t in [druck, k["sprache"]] if t)
            c.setFillColor(GRAU)
            schreibe(c, x, yc - 11.7 * mm, kuerzen(zeile, "TextI", 7.8, r.kw - 15 * mm), "TextI", 7.8)
            c.setFillColor(TINTE)
            schreibe(c, x + r.kw, yc - 11.7 * mm, k["preis_txt"] or eur_de(k["preis"]), "TextB", 8.6, rechts=True)
            if k["hinweis"]:
                c.setFillColor(farbe)
                for i, z in enumerate(umbrechen(k["hinweis"], "TextI", 7.6, r.kw, 2)):
                    schreibe(c, x, yc - (15.1 + 3.1 * i) * mm, z, "TextI", 7.6)
        r.zeile_karten(ks, zeichne)
        r.y -= 2 * mm
    fuss(r.seite); c.save()


# ---------------------------------------------------------------- Deck-PDF
def deck_pdf(info, karten, commander, ziel, bilder):
    alle = commander + karten
    c = canvas.Canvas(str(ziel), pagesize=A4)
    c.setTitle(f"{info['name']} – Deck"); c.setAuthor("MTG-Projekt")
    seite_grund(c)

    # Kennzahlen
    def front(k):
        return vorderseite(k["scry"]) if k.get("scry") else ("", "", {})
    laender = [k for k in alle if typ_von(front(k)[0]) in ("Land", "Standardland")]
    basics = [k for k in laender if typ_von(front(k)[0]) == "Standardland"]
    nichtland = [k for k in alle if k not in laender]
    n_ges = sum(k["anzahl"] for k in alle)
    n_land = sum(k["anzahl"] for k in laender)
    mv = [((k.get("scry") or {}).get("cmc", 0), k["anzahl"]) for k in nichtland]
    o_mv = sum(m * a for m, a in mv) / max(1, sum(a for _, a in mv))
    kurve = Counter()
    for m, a in mv:
        kurve[min(int(m), 7)] += a
    pips_z, quellen = Counter(), Counter()
    for k in nichtland:
        for s in re.findall(r"\{([^}]+)\}", front(k)[1] or ""):
            for ch in set(s):
                if ch in "WUBRG":
                    pips_z[ch] += k["anzahl"]
    for k in laender:
        for ch in (k.get("scry") or {}).get("produced_mana", []) or []:
            if ch in "WUBRG":
                quellen[ch] += k["anzahl"]
    gc = [k["name"] for k in alle if (k.get("scry") or {}).get("game_changer")]
    wert = info.get("wert")
    if not wert:
        summe = sum((preis(k.get("scry")) or 0) * k["anzahl"] for k in alle)
        wert = f"{eur(summe)} (abgebildete Drucke, Scryfall-EUR {HEUTE})"
    typen = Counter()
    for k in karten:
        typen[typ_von(front(k)[0])] += k["anzahl"]
    # Farben: Kürzel aus dem Namen („Mardu (RWB)“) > Commander-Manakosten > Farben der Nichtländer
    kuerzel = re.search(r"\(([WUBRG]+)\)", info.get("farben") or "")
    if kuerzel:
        identitaet = list(kuerzel.group(1))
    elif commander:
        identitaet = []
        for k in commander:
            for ch in re.findall(r"[WUBRG]", vorderseite(k["scry"])[1] if k.get("scry") else ""):
                if ch not in identitaet:
                    identitaet.append(ch)
        for k in commander:
            for ch in sorted((k.get("scry") or {}).get("color_identity", []), key="WUBRG".index):
                if ch not in identitaet:
                    identitaet.append(ch)
    else:
        farbmenge = {ch for k in nichtland for ch in ((k.get("scry") or {}).get("colors")
                     or ((k.get("scry") or {}).get("card_faces") or [{}])[0].get("colors", []) or [])}
        identitaet = [ch for ch in "WUBRG" if ch in farbmenge]
    # Titelkarte: Commander – bei Decks ohne Commander --titelkarte bzw. häufigste Nichtland-Karte
    if commander:
        titel, titel_label = commander, "COMMANDER"
    else:
        wahl = [k for k in karten if info.get("titelkarte") and k["name"].lower() == info["titelkarte"].lower()]
        if not wahl:
            kand = [k for k in karten if k not in laender] or karten
            wahl = [max(kand, key=lambda k: (k["anzahl"], preis(k.get("scry")) or 0))]
        titel, titel_label = wahl, "TITELKARTE"

    # --- Deckblatt: Kopfband
    band_o, band_u = H - 7.3 * mm, H - 46 * mm
    c.setFillColor(NACHT); c.rect(7.3 * mm, band_u, W - 14.6 * mm, band_o - band_u, fill=1, stroke=0)
    c.setStrokeColor(GOLD); c.setLineWidth(0.8); c.line(7.3 * mm, band_u, W - 7.3 * mm, band_u)
    c.setFillColor(GOLD_H)
    g, t = passend(info["name"].upper(), "Titel", 27, 16, W - 2 * RAND - 45 * mm)
    c.setFont("Titel", g); c.drawString(RAND + 2 * mm, H - 24 * mm, t)
    c.setFillColor(HexColor("#E9DFC9"))
    unter = " · ".join(x for x in [info.get("format"), info.get("farben"), info.get("strategie"), info.get("herkunft")] if x)
    g, t = passend(unter, "TextI", 11.5, 8.5, W - 2 * RAND - 45 * mm)
    c.setFont("TextI", g); c.drawString(RAND + 2 * mm, H - 32 * mm, t)
    c.setFont("Text", 9.5); c.setFillColor(HexColor("#BFB39C"))
    c.drawString(RAND + 2 * mm, H - 39.5 * mm, f"{n_ges} Karten · Stand {info.get('stand') or HEUTE}"
                 + (f" · {info['hinweis']}" if info.get("hinweis") else ""))
    for i, ch in enumerate(identitaet):
        pip(c, W - RAND - 6 * mm - (len(identitaet) - 1 - i) * 11 * mm, H - 26 * mm, 4.4 * mm, ch)
    stempel(c, info.get("stempel"), W - RAND - 32 * mm, band_u - 1 * mm)

    # --- Commander
    y0 = band_u - 6 * mm
    bw = 72 * mm if len(titel) == 1 else 50 * mm
    bh = bw * 88 / 63
    yb = y0
    for k in titel:
        c.setFillColor(GOLD); c.roundRect(RAND - 1.2 * mm, yb - bh - 1.2 * mm, bw + 2.4 * mm, bh + 2.4 * mm, bw * 0.06, fill=1, stroke=0)
        kartenbild(c, bilder.pfad(k, "large"), RAND, yb, bw, bh)
        yb -= bh + 5 * mm
    xr = RAND + bw + 8 * mm
    br = W - RAND - xr
    y = y0
    for k in titel:
        sc = k.get("scry") or {}
        c.setFont("TitelM", 9); c.setFillColor(GOLD)
        c.drawString(xr, y - 3 * mm, titel_label + (f"  ·  {k['anzahl']}× im Deck" if not commander and k["anzahl"] > 1 else ""))
        name = sc.get("name", k["name"])
        g, t = passend(name, "Titel", 15, 9.5, br - 25 * mm)
        c.setFont("Titel", g); c.setFillColor(TINTE)
        c.drawString(xr, y - 10 * mm, t)
        mana = vorderseite(sc)[1] if sc else ""
        breite = len(re.findall(r"\{", mana)) * 2.3 * 2.3 * mm
        pips(c, W - RAND - breite, y - 8.8 * mm, mana, 2.3 * mm)
        c.setFont("TextI", 10.5); c.setFillColor(GRAU)
        c.drawString(xr, y - 15.5 * mm, kuerzen(sc.get("type_line", ""), "TextI", 10.5, br))
        y -= 19 * mm
        text = sc.get("oracle_text") or "\n\n".join(f.get("oracle_text", "") for f in sc.get("card_faces", []))
        text = html.escape(text).replace("\n", "<br/>")
        text = re.sub(r"\(([^)]*)\)", r"<i>(\1)</i>", text)
        stil = ParagraphStyle("o", fontName="Text", fontSize=10.6, leading=13.4, textColor=TINTE)
        p = Paragraph(text, stil)
        _, ph = p.wrap(br - 8 * mm, 200 * mm)
        pt = sc.get("power")
        extra = 6 * mm if pt is not None else 0
        c.setFillColor(PAPIER2); c.setStrokeColor(GOLD); c.setLineWidth(0.6)
        c.roundRect(xr, y - ph - 8 * mm - extra, br, ph + 8 * mm + extra, 2.5 * mm, fill=1, stroke=1)
        p.drawOn(c, xr + 4 * mm, y - ph - 4 * mm)
        if pt is not None:
            c.setFont("TextB", 11); c.setFillColor(TINTE)
            c.drawRightString(xr + br - 4 * mm, y - ph - 4 * mm - extra + 1 * mm, f"{pt}/{sc.get('toughness')}")
        y -= ph + 8 * mm + extra + 6 * mm

    # --- Kurzdaten
    c.setFont("TitelM", 9); c.setFillColor(GOLD); c.drawString(xr, y - 3 * mm, "KURZDATEN")
    y -= 7.5 * mm
    if commander:
        kopfzeilen = [("Bracket", info.get("bracket") or "–"),
                      ("Game Changer", f"{len(gc)}/3" + (f" ({', '.join(gc)})" if gc else "") + " · live laut Scryfall")]
    else:
        kopfzeilen = [("Format", info.get("bracket") or info.get("format") or "–")]
    zeilen = kopfzeilen + [
              ("Karten", f"{n_ges} · {n_land} Länder, davon {sum(k['anzahl'] for k in basics)} Standardländer"),
              ("Ø Manawert", f"{o_mv:.2f}".replace(".", ",") + " (Nichtländer inkl. Commander)"),
              ("Deckwert", wert),
              ("Themen", info.get("themen") or "–"),
              ("Status", info.get("status") or "–")]
    stil_w = ParagraphStyle("w", fontName="Text", fontSize=9.6, leading=11.6, textColor=TINTE)
    for lab, wtext in zeilen:
        c.setFont("TextB", 9.6); c.setFillColor(GRAU); c.drawString(xr, y - 3.2 * mm, lab)
        p = Paragraph(html.escape(wtext), stil_w); _, ph = p.wrap(br - 27 * mm, 50 * mm)
        p.drawOn(c, xr + 27 * mm, y - ph + 0.5 * mm)
        y -= max(ph, 4.2 * mm) + 1.6 * mm
    y_unten = min(y, yb) - 3 * mm

    # --- Moxfield-Beschreibung
    if info.get("beschreibung"):
        zierlinie(c, RAND, W - RAND, y_unten)
        stil_b = ParagraphStyle("b", fontName="TextI", fontSize=11, leading=14, textColor=TINTE, alignment=1)
        p = Paragraph("„" + html.escape(info["beschreibung"]) + "“", stil_b)
        _, ph = p.wrap(W - 2 * RAND - 20 * mm, 40 * mm)
        p.drawOn(c, RAND + 10 * mm, y_unten - ph - 3 * mm)
        y_unten -= ph + 7 * mm

    # --- Diagramme: Manakurve | Farben + Typen
    hoehe = min(max(40 * mm, y_unten - 24 * mm), 85 * mm)
    ob = y_unten - 2 * mm
    halb = (W - 2 * RAND - 8 * mm) / 2
    # Manakurve
    c.setFont("TitelM", 9); c.setFillColor(GOLD); c.drawString(RAND, ob - 3 * mm, "MANAKURVE")
    c.setFont("TextI", 8.5); c.setFillColor(GRAU); c.drawRightString(RAND + halb, ob - 3 * mm, "ohne Länder")
    ch_o, ch_u = ob - 9 * mm, ob - hoehe + 7 * mm
    maxv = max(kurve.values() or [1])
    spw = halb / 8
    for i in range(8):
        v = kurve.get(i, 0)
        hh = (ch_o - ch_u - 4 * mm) * v / maxv if maxv else 0
        x = RAND + i * spw + spw * 0.18
        c.setFillColor(GOLD if v else PAPIER2)
        c.rect(x, ch_u, spw * 0.64, max(hh, 0.6), fill=1, stroke=0)
        c.setFillColor(TINTE); c.setFont("TextB", 9)
        if v:
            c.drawCentredString(x + spw * 0.32, ch_u + hh + 1.2 * mm, str(v))
        c.setFont("Text", 9); c.setFillColor(GRAU)
        c.drawCentredString(x + spw * 0.32, ch_u - 4 * mm, "7+" if i == 7 else str(i))
    c.setStrokeColor(TINTE); c.setLineWidth(0.4); c.line(RAND, ch_u, RAND + halb, ch_u)
    # Farben
    xf = RAND + halb + 8 * mm
    c.setFont("TitelM", 9); c.setFillColor(GOLD); c.drawString(xf, ob - 3 * mm, "FARBEN")
    c.setFont("TextI", 8.5); c.setFillColor(GRAU); c.drawRightString(xf + halb, ob - 3 * mm, "Pips in Kosten · Länder als Quelle")
    yy = ob - 10 * mm
    maxp = max(list(pips_z.values()) + list(quellen.values()) + [1])
    for ch in identitaet or ["C"]:
        pip(c, xf + 2.6 * mm, yy - 1.2 * mm, 2.4 * mm, ch)
        bl = halb - 46 * mm
        c.setFillColor(HexColor(PIP.get(ch, PIP["C"]))); c.setStrokeColor(TINTE); c.setLineWidth(0.3)
        c.rect(xf + 8 * mm, yy - 0.2 * mm, bl * pips_z[ch] / maxp, 2.2 * mm, fill=1, stroke=1)
        c.setFillColor(GOLD); c.rect(xf + 8 * mm, yy - 3.2 * mm, bl * quellen[ch] / maxp, 2.2 * mm, fill=1, stroke=0)
        c.setFont("Text", 8.8); c.setFillColor(TINTE)
        c.drawRightString(xf + halb, yy - 2.3 * mm, f"{pips_z[ch]} Pips · {quellen[ch]} Quellen")
        yy -= 7.5 * mm
    # Typen
    yy -= 1 * mm
    c.setFont("TitelM", 9); c.setFillColor(GOLD); c.drawString(xf, yy - 3 * mm, "KARTENTYPEN")
    yy -= 7 * mm
    teile = [f"{TYP_PLURAL[t]} {typen[t]}" for t, _ in KATEGORIEN if typen.get(t)]
    stil_t = ParagraphStyle("t", fontName="Text", fontSize=9.6, leading=12, textColor=TINTE)
    p = Paragraph(" · ".join(teile), stil_t); _, ph = p.wrap(halb, 30 * mm); p.drawOn(c, xf, yy - ph + 3 * mm)

    def fuss(s):
        q = "Bilder: Scryfall, englische Druckversion" if not bilder.gesperrt else "Bilder teils Platzhalter"
        fusszeile(c, f"{info['name']} · {q} · erstellt {HEUTE}", s)

    # --- Kategorieseiten
    fuss(1); c.showPage(); seite_grund(c)

    def kopf_folge():
        c.setFont("Titel", 10); c.setFillColor(TINTE)
        c.drawString(RAND, H - RAND - 2.5 * mm, info["name"].upper())
        for i, ch in enumerate(identitaet):
            pip(c, W - RAND - 2 * mm - (len(identitaet) - 1 - i) * 5 * mm, H - RAND - 1.3 * mm, 2 * mm, ch)
        zierlinie(c, RAND, W - RAND, H - RAND - 5 * mm)
        return H - RAND - 10 * mm

    r = Raster(c, 5, 4 * mm, 9.5 * mm, kopf_folge, fuss, kopf_folge())
    r.seite = 2
    gruppen = defaultdict(list)
    for k in karten:
        gruppen[typ_von(front(k)[0])].append(k)
    for typ, titel in KATEGORIEN:
        ks = gruppen.get(typ)
        if not ks:
            continue
        ks.sort(key=lambda k: ((k.get("scry") or {}).get("cmc", 0), k["name"]))
        r.platz(9 * mm + r.kh + r.cap)
        c.setFont("Titel", 13); c.setFillColor(TINTE)
        c.drawString(RAND, r.y - 5 * mm, titel)
        tw = stringWidth(titel, "Titel", 13)
        c.setFont("TextI", 10.5); c.setFillColor(GRAU)
        c.drawString(RAND + tw + 3 * mm, r.y - 5 * mm, f"({sum(k['anzahl'] for k in ks)})")
        c.setStrokeColor(GOLD); c.setLineWidth(0.5)
        c.line(RAND + tw + 16 * mm, r.y - 3.8 * mm, W - RAND, r.y - 3.8 * mm)
        r.y -= 9 * mm

        def zeichne(k, x, y_oben):
            kartenbild(c, bilder.pfad(k), x, y_oben, r.kw, r.kh)
            if k["anzahl"] > 1:
                plakette(c, x + r.kw - 5 * mm, y_oben - r.kh * 0.36, f"{k['anzahl']}×", NACHT, r=3.8 * mm)
            sc = k.get("scry") or {}
            c.setFillColor(TINTE); c.setFont("TextB", 8.2)
            c.drawString(x, y_oben - r.kh - 3.4 * mm, kuerzen(k["name"], "TextB", 8.2, r.kw))
            pr = preis(sc)
            zeile = f"MV {int(sc.get('cmc', 0))}" if typ not in ("Land", "Standardland") else (sc.get("set", "").upper())
            if pr is not None:
                zeile += f" · {eur(pr)}"
            c.setFont("Text", 7.6); c.setFillColor(GRAU)
            c.drawString(x, y_oben - r.kh - 6.6 * mm, zeile)
        r.zeile_karten(ks, zeichne)
        r.y -= 1.5 * mm
    fuss(r.seite); c.save()


# ---------------------------------------------------------------- Tausch aus der Datenbank
SPRACHE_KURZ = {"en": "Englisch", "de": "Deutsch", "fr": "Französisch", "it": "Italienisch", "es": "Spanisch",
                "ja": "Japanisch", "pt": "Portugiesisch"}
ZUORDNUNG_RANG = "CASE e.zuordnung WHEN 'druck' THEN 0 WHEN 'zeitstempel' THEN 1 WHEN 'set' THEN 2 ELSE 3 END"


def vergleich_db(a):
    """Tauschliste aus Soll-Stand und Entwurf mit der Exemplar-Zuordnung der Datenbank (mtg_db.py build)."""
    import sqlite3
    sys.path.insert(0, str(HIER))
    import mtg_db as M
    con = sqlite3.connect(a.db)
    _, alt, alt_cmd = lies_deck(a.alt)
    _, neu, neu_cmd = lies_deck(a.neu)

    def zaehl(lst):
        z = Counter()
        for k in lst:
            z[k["name"]] += k["anzahl"]
        return z
    c_alt, c_neu = zaehl(alt + alt_cmd), zaehl(neu + neu_cmd)
    wunsch = defaultdict(list)
    for k in neu + neu_cmd:
        if k["set"]:
            wunsch[k["name"]].append((k["set"], k["nummer"].lower()))
    r = con.execute("SELECT deck_id, kurz FROM decks WHERE datei=?", (Path(a.alt).name,)).fetchone()
    did, kurz = (r if r else (M.find_deck(con, a.deckname), a.deckname)) if (r or a.deckname) else (None, "")
    sprache = lambda l, f: SPRACHE_KURZ.get(l, l) + {"foil": " Foil", "etched": " Etched"}.get(f, "")
    zeilen = []

    def gruppen(kopien):
        g = Counter((s, n, l, f) for s, n, l, f, *_ in kopien)
        return [(k, v) for k, v in g.items()]
    for name in sorted(set(c_neu) | set(c_alt)):
        diff = c_neu[name] - c_alt[name]
        if diff == 0:
            continue
        oid = M.resolve_name(con, name)
        if diff < 0:
            kopien = con.execute(f"SELECT e.set_code, e.cn, e.lang, e.finish, e.zuordnung FROM exemplare e WHERE"
                                 f" e.deck_id=? AND e.oracle_id=? ORDER BY {ZUORDNUNG_RANG}", (did, oid)).fetchall()
            kopien = kopien[len(kopien) + diff:] if len(kopien) >= -diff else kopien
            sicher = all(k[4] in ("druck", "zeitstempel", "set") for k in kopien)
            for (s_, n_, l_, f_), v in gruppen(kopien) or [(("", "", "", ""), -diff)]:
                hinweis = ("zurück zu den Standardländern" if ist_basic(name) else
                           (sprache(l_, f_) if l_ else "") + ("" if sicher else " · Druck geschätzt"))
                zeilen.append(dict(anzahl=v, name=name, set=s_, nummer=n_, quelle="Sammlung", hinweis=hinweis.strip(" ·"),
                                   abschnitt="raus"))
            continue
        frei = con.execute("SELECT e.set_code, e.cn, e.lang, e.finish FROM exemplare e WHERE e.oracle_id=? AND"
                           " e.deck_id IS NULL AND (e.idee IS NULL OR e.idee=?) ORDER BY e.lang<>'en', e.set_code",
                           (oid, a.idee or "")).fetchall()
        if ist_basic(name):
            zeilen.append(dict(anzahl=diff, name=name, set="", nummer="", quelle="Standardland",
                               hinweis=f"{min(len(frei), diff)} frei, {max(0, diff - len(frei))} kaufen", abschnitt="basic"))
            continue
        bevorzugt = wunsch.get(name, [])
        frei.sort(key=lambda k: (k[0], k[1].lower()) not in bevorzugt)
        nimm, uebrig = frei[:diff], frei[diff:]
        for (s_, n_, l_, f_), v in gruppen(nimm):
            andere = sorted({f"{x[0].upper()} {x[1]} {SPRACHE_KURZ.get(x[2], x[2])}" for x in uebrig
                             if (x[0], x[1], x[2]) != (s_, n_, l_)})
            zeilen.append(dict(anzahl=v, name=name, set=s_, nummer=n_, quelle="Sammlung",
                               hinweis="besitzt: " + sprache(l_, f_) + (f" · auch frei: {', '.join(andere[:2])}" if andere else ""),
                               abschnitt="holen"))
        rest = diff - len(nimm)
        if rest:
            fremd = con.execute(f"SELECT k.kurz, e.set_code, e.cn, e.lang, e.finish FROM exemplare e JOIN decks k"
                                f" USING(deck_id) WHERE e.oracle_id=? AND e.deck_id IS NOT ? ORDER BY {ZUORDNUNG_RANG}",
                                (oid, did)).fetchall()[:rest]
            for dk, s_, n_, l_, f_ in fremd:
                zeilen.append(dict(anzahl=1, name=name, set=s_, nummer=n_, quelle="Deck: " + dk,
                                   hinweis=sprache(l_, f_) + " · Ersatz im abgebenden Deck nötig", abschnitt="deck"))
            rest -= len(fremd)
        if rest:
            zeilen.append(dict(anzahl=rest, name=name, set="", nummer="", quelle="Kauf", hinweis="", abschnitt="kauf"))
    return zeilen, kurz


# Schneller: „deckbau.py fazit --neu <Entwurf> --alt <Soll-Stand>“ schreibt diese Datei mit allen Zahlen, Daten und
# Status vorbefüllt; Claude füllt nur die Platzhalter ‹…›. Die Vorlage hier ist der Aufbau zum Nachschlagen.
FAZIT_VORLAGE = """---
titel: <Deckname>
oberzeile: <Upgrade Stufe 0 | Neues Deck> · freigegeben am <TT.MM.JJJJ>
unterzeile: Fazit, Kartenerklärungen und Vorgehen · <Commander> · Bracket <B>
zeile3: <voller Name nach Namensschema>
kurz: <Upgrade Stufe 0>
farben: <WUBRG-Kürzel, z. B. GW>
fuss: Daten: Scryfall, EDHREC (Bracket-Seite), Commander Spellbook · Stand <TT.MM.JJJJ>
deckname: <Deckname>
voll: <voller Name nach Namensschema>
bracket_zeile: <Bracket-Zeile>
beschreibung: <Moxfield-Beschreibung, höchstens 140 Zeichen>
themen: <Moxfield-Themen>
status: freigegeben – Aufbau offen
wert: <Deckwert € (günstigste Drucke, Datum)>
set: <Precon-Set für Karten ohne Druck, sonst leer>
---
[kacheln]
Bracket <B> | <n>/3 Game Changer
<n> Tausche | Stufe <0> · <0 €>
<Wert> € | Deckwert (günstigste Drucke)
<3,48> | Ø MV (Nichtländer inkl. Commander)
[/kacheln]

## Fazit
<2–3 Sätze Spielplan und was sich ändert.>

> **Bracket-Zeile:** <Bracket 3 – n/3 Game Changer (…) – keine MLD, keine Extra-Turn-Ketten, kein frühes 2-Karten-Combo>

## Die Änderungen
| raus | warum raus | rein | warum rein | Status |
|---|---|---|---|---|
| <Karte> | <ein Satz aus dem Oracle-Text> *(Daten)* | <Karte> | <ein Satz aus dem Oracle-Text> *(Daten)* | <frei / Kauf x,xx €> |

## Kennzahlen vorher und nachher
| Kennzahl | vorher | nachher | Richtwert |
|---|---|---|---|
| Ramp | <n> | <n> | 10–12 |

## Spielplan
- **Früh:** <…>
- **Mitte:** <…>
- **Spät / Siegwege:** <…>

## Ehrliche Einschätzung und Abstriche
>! <Was fehlt, was schwach bleibt, welche Käufe später am meisten bringen.>

## Kartenerklärungen
| Karte | Rolle | Warum im Deck & Synergie | Commander-Bezug | Status |
|---|---|---|---|---|
| ## Ramp |
| <Karte> | <Rolle> | <aus dem Oracle-Text> | <…> | <frei> |

## So bin ich vorgegangen
1. <Gespräch, Recherche (Quellen mit Datum), Prüfläufe, Anpassungen>

## Anhang: Moxfield
[moxfield]

```
<Einfügeblock – derselbe Inhalt wie die .txt-Datei>
```
"""


def md_kopf(md):
    m = re.match(r"^---\n(.*?)\n---[ \t]*\n", md, re.S)
    kopf = {}
    for z in (m.group(1).splitlines() if m else []):
        if ":" in z:
            k, v = z.split(":", 1)
            kopf[k.strip().lower()] = v.strip()
    return kopf


def md_pruefen(md):
    """-> Liste von Hinweisen (offene Platzhalter ‹…›, Beschreibung > 140, Name > 100 Zeichen)."""
    kopf, out = md_kopf(md), []
    n = md.count("‹")
    if n:
        zeilen = [z.strip()[:60] for z in md.splitlines() if "‹" in z]
        out.append(f"{n} Platzhalter ‹…› offen, z. B.: " + " | ".join(zeilen[:3]))
    if len(kopf.get("beschreibung", "")) > 140:
        out.append(f"Moxfield-Beschreibung hat {len(kopf['beschreibung'])} Zeichen (max. 140)")
    if len(kopf.get("voll", "")) > 100:
        out.append(f"Deckname hat {len(kopf['voll'])} Zeichen (max. 100)")
    return out


def stempel_md(md, stempel):
    if not stempel:
        return md
    return ("---\nstempel: " + stempel + "\n" + md[4:]) if md.startswith("---\n") else "---\nstempel: " + stempel + "\n---\n" + md


def einfuege_aus_md(md):
    m = re.search(r"## Anhang: Moxfield.*?```\n(.*?)\n```", md, re.S)
    return m.group(1).strip() + "\n" if m else None


# ---------------------------------------------------------------- Bericht (Fazit-PDF aus Markdown)
def bericht_pdf(md, ziel):
    """Fazit-PDF im Kartenbilder-Design aus einer Markdown-Datei.

    Kopf (zwischen zwei Zeilen ---): titel, oberzeile, unterzeile, zeile3, farben (z. B. GW), fuss, stempel.
    Blöcke: [kacheln] Wert | Beschriftung … [/kacheln] · ## Abschnitt (nummeriert) · ### Unterabschnitt ·
    Absätze · - Liste (zwei Leerzeichen = Unterpunkt) · 1. nummeriert · > Kasten (>! rot, >+ grün, >? blau) ·
    | Tabelle | (erste Zeile = Kopf; „| ## Text |“ = Gruppenzeile) · ``` Einfügeblock ``` (lange Blöcke zweispaltig) ·
    <seitenumbruch> · Inline: **fett**, *kursiv*, `Code`."""
    from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, PageBreak,
                                    PageTemplate, Spacer, Table, TableStyle)
    pdfmetrics.registerFont(TTFont("Mono", str(DV / "DejaVuSansMono.ttf")))
    RANDB, BAND = 14 * mm, 44 * mm
    GRUEN, BLAU, GOLD_HELL = HexColor("#2E6B3F"), HexColor("#2F4F86"), HexColor("#E9D9AE")
    kopf, rumpf = {}, md
    m = re.match(r"^---\n(.*?)\n---[ \t]*\n(.*)$", md, re.S)
    if m:
        for z in m.group(1).splitlines():
            if ":" in z:
                k, v = z.split(":", 1)
                kopf[k.strip().lower()] = v.strip()
        rumpf = m.group(2)
    if "[moxfield]" in rumpf:
        voll, besch, themen = kopf.get("voll") or kopf.get("zeile3", ""), kopf.get("beschreibung", ""), kopf.get("themen", "")
        rumpf = rumpf.replace("[moxfield]", f"- **Name:** {voll} ({len(voll)}/100 Zeichen)\n"
                              f"- **Beschreibung:** {besch} ({len(besch)}/140 Zeichen)\n- **Themen:** {themen}")

    def st(name, **kw):
        b = dict(fontName="Text", fontSize=10.6, leading=14.2, textColor=TINTE)
        b.update(kw)
        return ParagraphStyle(name, **b)
    TEXT, KLEIN = st("t"), st("k", fontSize=8.8, leading=11)
    KOPFZ = st("kz", fontName="TitelM", fontSize=7.6, leading=9.4, textColor=GOLD_H)
    ZAHL = st("z", fontName="Titel", fontSize=17, leading=20, alignment=1)
    ZAHL_L = st("zl", fontSize=8.6, leading=10.4, textColor=GRAU, alignment=1)
    MONO = st("m", fontName="Mono", fontSize=7.4, leading=9.2)
    LISTE = st("l", leftIndent=11, bulletIndent=1, spaceAfter=2.4, bulletFontName="Sans", bulletFontSize=6.5,
               bulletColor=GOLD)
    LISTE_N = st("ln", leftIndent=13, bulletIndent=1, spaceAfter=2.4, bulletFontName="TextB", bulletColor=GOLD)
    LISTE2 = st("l2", leftIndent=22, bulletIndent=13, spaceAfter=2, fontSize=10, bulletFontName="Text",
                bulletColor=GRAU)

    def inline(t):
        t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        t = re.sub(r"`([^`]+)`", r'<font name="Mono" size="8.4" color="#5A4320">\1</font>', t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<i>\1</i>", t)
        return re.sub("([⚑⚠✓✗→←↔◆★])", r'<font name="Sans">\1</font>', t)   # Zeichen, die EB Garamond fehlen

    class Kopf(Flowable):
        def __init__(self, text, nr):
            super().__init__(); self.text, self.nr = text, nr
        def wrap(self, aw, ah):
            self.aw = aw; return aw, 13 * mm
        def draw(self):
            c = self.canv; x = 0
            if self.nr:
                c.setFillColor(GOLD); c.circle(3.2 * mm, 5.6 * mm, 3.2 * mm, fill=1, stroke=0)
                c.setFillColor(NACHT); c.setFont("Titel", 10); c.drawCentredString(3.2 * mm, 4.3 * mm, str(self.nr))
                x = 8.5 * mm
            g, t = passend(self.text, "Titel", 14.5, 10, self.aw - x)
            c.setFillColor(TINTE); c.setFont("Titel", g); c.drawString(x, 3.6 * mm, t)
            zierlinie(c, 0, self.aw, 0.8 * mm)

    class Unterkopf(Flowable):
        def __init__(self, text):
            super().__init__(); self.text = text
        def wrap(self, aw, ah):
            self.aw = aw; return aw, 8 * mm
        def draw(self):
            c = self.canv
            raute(c, 1.4 * mm, 3.3 * mm, 1.3 * mm, GOLD)
            g, t = passend(self.text.upper(), "TitelM", 10.5, 8, self.aw - 5 * mm)
            c.setFillColor(TINTE); c.setFont("TitelM", g); c.drawString(4.2 * mm, 2.2 * mm, t)

    breite = W - 2 * RANDB

    def kasten(inhalt, balken=None):
        if balken:
            t = Table([["", inhalt]], colWidths=[2.4 * mm, breite - 2.4 * mm])
            stil = [("BACKGROUND", (0, 0), (0, 0), balken), ("BACKGROUND", (1, 0), (1, 0), PAPIER2),
                    ("BOX", (0, 0), (-1, -1), 0.6, GOLD), ("LEFTPADDING", (1, 0), (1, 0), 4 * mm),
                    ("RIGHTPADDING", (1, 0), (1, 0), 4 * mm), ("TOPPADDING", (1, 0), (1, 0), 2.6 * mm),
                    ("BOTTOMPADDING", (1, 0), (1, 0), 2.6 * mm), ("LEFTPADDING", (0, 0), (0, 0), 0),
                    ("RIGHTPADDING", (0, 0), (0, 0), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]
        else:
            t = Table([[inhalt]], colWidths=[breite])
            stil = [("BACKGROUND", (0, 0), (-1, -1), PAPIER2), ("BOX", (0, 0), (-1, -1), 0.6, GOLD),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4.5 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 4.5 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 3 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm)]
        t.setStyle(TableStyle(stil))
        return t

    def tabelle(zeilen):
        daten = [[x.strip() for x in z.strip().strip("|").split("|")] for z in zeilen
                 if not re.match(r"^\|[\s:|-]+\|$", z.strip())]
        n = max(len(r) for r in daten)
        daten = [r + [""] * (n - len(r)) for r in daten]
        gruppen = [i for i, r in enumerate(daten) if i and r[0].startswith("## ")]
        laenge = [max([len(r[j]) for i, r in enumerate(daten) if i not in gruppen] + [4]) for j in range(n)]
        gew = [min(l, 70) ** 0.85 for l in laenge]
        breiten = [max(18 * mm, breite * g / sum(gew)) for g in gew]
        f = breite / sum(breiten)
        breiten = [b * f for b in breiten]
        zellen = []
        for i, r in enumerate(daten):
            if i in gruppen:
                zellen.append([Paragraph(inline(r[0][3:]), st("g", fontName="Titel", fontSize=9.6, leading=12))]
                              + [""] * (n - 1))
            else:
                zellen.append([Paragraph(inline(x), KOPFZ if i == 0 else KLEIN) for x in r])
        t = Table(zellen, colWidths=breiten, repeatRows=1)
        stil = [("BACKGROUND", (0, 0), (-1, 0), NACHT), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, GOLD), ("LINEBELOW", (0, 1), (-1, -1), 0.25, GOLD_HELL),
                ("BOX", (0, 0), (-1, -1), 0.6, GOLD), ("LEFTPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.2 * mm), ("TOPPADDING", (0, 0), (-1, -1), 1.3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm)]
        k = 0
        for i in range(1, len(zellen)):
            if i in gruppen:
                stil += [("SPAN", (0, i), (-1, i)), ("BACKGROUND", (0, i), (-1, i), GOLD_HELL)]
                k = 0
                continue
            if k % 2:
                stil.append(("BACKGROUND", (0, i), (-1, i), PAPIER2))
            k += 1
        t.setStyle(TableStyle(stil))
        return t

    def kacheln(eintraege):
        proreihe = 4 if len(eintraege) != 3 else 3
        bw = breite / proreihe
        reihen = []
        for i in range(0, len(eintraege), proreihe):
            teil = eintraege[i:i + proreihe]
            reihen.append([[Paragraph(inline(w), ZAHL), Paragraph(inline(l), ZAHL_L)] for w, l in teil]
                          + [""] * (proreihe - len(teil)))
        t = Table(reihen, colWidths=[bw] * proreihe)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PAPIER2), ("INNERGRID", (0, 0), (-1, -1), 0.4, GOLD),
                               ("BOX", (0, 0), (-1, -1), 0.7, GOLD), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("TOPPADDING", (0, 0), (-1, -1), 2.4 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4 * mm)]))
        return t

    def code(zeilen):
        if len(zeilen) <= 24:
            return kasten([Paragraph("<br/>".join(inline(z) or "&nbsp;" for z in zeilen), MONO)])
        sp = 3 if len(zeilen) > 70 else 2
        je = -(-len(zeilen) // sp)
        spalten = [Paragraph("<br/>".join(inline(z) or "&nbsp;" for z in zeilen[i * je:(i + 1) * je]), MONO)
                   for i in range(sp)]
        t = Table([spalten], colWidths=[(breite - 9 * mm) / sp] * sp)
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        return kasten([t])

    fl, zeilen, i, nr, absatz = [], rumpf.splitlines(), 0, 0, []

    def absatz_ende():
        if absatz:
            fl.append(Paragraph(inline(" ".join(absatz)), TEXT)); fl.append(Spacer(1, 1.6 * mm)); absatz.clear()
    while i < len(zeilen):
        z = zeilen[i].rstrip()
        s_ = z.strip()
        if not s_:
            absatz_ende(); i += 1; continue
        if s_ == "[kacheln]":
            absatz_ende(); e = []; i += 1
            while i < len(zeilen) and zeilen[i].strip() != "[/kacheln]":
                if "|" in zeilen[i]:
                    w, l = zeilen[i].split("|", 1); e.append((w.strip(), l.strip()))
                i += 1
            fl += [kacheln(e), Spacer(1, 4 * mm)]; i += 1; continue
        if s_.lower() in ("<seitenumbruch>", "<pagebreak>"):
            absatz_ende(); fl.append(PageBreak()); i += 1; continue
        if s_.startswith("## "):
            absatz_ende(); nr += 1
            fl += [CondPageBreak(45 * mm), Spacer(1, 2 * mm),
                   Kopf(s_[3:], nr if kopf.get("nummern", "ja") != "nein" else None), Spacer(1, 2.4 * mm)]
            i += 1; continue
        if s_.startswith("### "):
            absatz_ende(); fl += [CondPageBreak(30 * mm), Unterkopf(s_[4:]), Spacer(1, 1 * mm)]; i += 1; continue
        if s_.startswith("```"):
            absatz_ende(); block = []; i += 1
            while i < len(zeilen) and not zeilen[i].strip().startswith("```"):
                block.append(zeilen[i].rstrip()); i += 1
            fl += [code(block), Spacer(1, 3 * mm)]; i += 1; continue
        if s_.startswith(">"):
            absatz_ende(); block = []; balken = {"!": ROT, "+": GRUEN, "?": BLAU}.get(s_[1:2])
            while i < len(zeilen) and zeilen[i].strip().startswith(">"):
                t = zeilen[i].strip()[1:]
                block.append(t[1:].strip() if t[:1] in "!+?" else t.strip()); i += 1
            inhalt, txt = [], []
            for t in block + [""]:
                if t.startswith("- "):
                    if txt:
                        inhalt.append(Paragraph(inline(" ".join(txt)), TEXT)); txt = []
                    inhalt.append(Paragraph(inline(t[2:]), LISTE, bulletText="◆"))
                elif t:
                    txt.append(t)
                elif txt:
                    inhalt.append(Paragraph(inline(" ".join(txt)), TEXT)); txt = []
            fl += [kasten(inhalt, balken), Spacer(1, 3 * mm)]; continue
        if s_.startswith("|"):
            absatz_ende(); block = []
            while i < len(zeilen) and zeilen[i].strip().startswith("|"):
                block.append(zeilen[i]); i += 1
            fl += [tabelle(block), Spacer(1, 3 * mm)]; continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", z)
        if m:
            absatz_ende()
            unter = len(m.group(1)) >= 2
            marke = m.group(2) if m.group(2)[0].isdigit() else ("–" if unter else "◆")
            stil = LISTE2 if unter else (LISTE_N if m.group(2)[0].isdigit() else LISTE)
            fl.append(Paragraph(inline(m.group(3)), stil, bulletText=marke))
            i += 1; continue
        absatz.append(s_); i += 1
    absatz_ende()

    titel = kopf.get("titel", "Bericht")
    farben = [ch for ch in kopf.get("farben", "") if ch in "WUBRG"]

    def fuss(c, doc):
        c.setFont("Text", 7.5); c.setFillColor(GRAU)
        c.drawString(RANDB, 9.5 * mm, kuerzen(kopf.get("fuss", f"erstellt {HEUTE}"), "Text", 7.5, W - 2 * RANDB - 20 * mm))
        c.drawRightString(W - RANDB, 9.5 * mm, f"Seite {doc.page}")

    def erste(c, doc):
        seite_grund(c)
        c.setFillColor(NACHT); c.rect(7.3 * mm, H - BAND, W - 14.6 * mm, BAND - 7.3 * mm, fill=1, stroke=0)
        c.setStrokeColor(GOLD); c.setLineWidth(0.8); c.line(7.3 * mm, H - BAND, W - 7.3 * mm, H - BAND)
        frei = W - 2 * RANDB - (len(farben) * 11 * mm + 4 * mm if farben else 0)
        if kopf.get("oberzeile"):
            g, t = passend(kopf["oberzeile"].upper(), "TitelM", 9, 7, frei)
            c.setFont("TitelM", g); c.setFillColor(GOLD); c.drawString(RANDB, H - 15 * mm, t)
        g, t = passend(titel.upper(), "Titel", 27, 16, frei)
        c.setFillColor(GOLD_H); c.setFont("Titel", g); c.drawString(RANDB, H - 26.5 * mm, t)
        if kopf.get("unterzeile"):
            g, t = passend(kopf["unterzeile"], "TextI", 11.5, 8.5, W - 2 * RANDB)
            c.setFont("TextI", g); c.setFillColor(HexColor("#E9DFC9")); c.drawString(RANDB, H - 33.5 * mm, t)
        if kopf.get("zeile3"):
            g, t = passend(kopf["zeile3"], "Text", 9, 7, W - 2 * RANDB)
            c.setFont("Text", g); c.setFillColor(HexColor("#BFB39C")); c.drawString(RANDB, H - 39.5 * mm, t)
        for j, ch in enumerate(farben):
            pip(c, W - RANDB - 4 * mm - (len(farben) - 1 - j) * 11 * mm, H - 24 * mm, 4.4 * mm, ch)
        stempel(c, kopf.get("stempel"), W - RANDB - 34 * mm, H - BAND - 1 * mm)
        fuss(c, doc)

    def folge(c, doc):
        seite_grund(c)
        g, t = passend(titel.upper() + (" · " + kopf["kurz"].upper() if kopf.get("kurz") else ""), "Titel", 9.5, 7.5,
                       W - 2 * RANDB - 15 * mm)
        c.setFont("Titel", g); c.setFillColor(TINTE); c.drawString(RANDB, H - 13.5 * mm, t)
        for j, ch in enumerate(farben):
            pip(c, W - RANDB - 2 * mm - (len(farben) - 1 - j) * 5 * mm, H - 12.4 * mm, 2 * mm, ch)
        zierlinie(c, RANDB, W - RANDB, H - 16 * mm)
        fuss(c, doc)

    doc = BaseDocTemplate(str(ziel), pagesize=A4, title=titel, author="MTG-Projekt")
    f1 = Frame(RANDB, 15 * mm, breite, H - BAND - 21 * mm, id="f1", leftPadding=0, rightPadding=0)
    f2 = Frame(RANDB, 15 * mm, breite, H - 36 * mm, id="f2", leftPadding=0, rightPadding=0)
    from reportlab.platypus import NextPageTemplate
    doc.addPageTemplates([PageTemplate("erste", [f1], onPage=erste), PageTemplate("folge", [f2], onPage=folge)])
    doc.build([NextPageTemplate("folge")] + fl)


# ---------------------------------------------------------------- Hauptprogramm
def png(ziel, dpi, nur_erste=False):
    for alt in ziel.parent.glob(ziel.stem + "-*.png"):
        alt.unlink()
    args = ["pdftoppm", "-png", "-r", str(dpi)] + (["-f", "1", "-l", "1"] if nur_erste else []) + [str(ziel), str(ziel.with_suffix(""))]
    subprocess.run(args, check=True)
    return sorted(ziel.parent.glob(ziel.stem + "-*.png"))


def lieferung(a):
    """Fazit-PDF + Tauschübersicht (PDF + PNG, nur mit --alt) + Deck-PDF + Einfügeblock-TXT in einem Lauf.
    Angaben für Deck-PDF und Tausch kommen aus dem Kopf des Fazits (deckname, voll, bracket_zeile, beschreibung,
    themen, status, wert, set); Kartendaten werden einmal geholt, Bilder parallel geladen."""
    t0 = time.time()
    md = Path(a.fazit).read_text(encoding="utf-8")
    hinweise = md_pruefen(md)
    if hinweise and any("Platzhalter" in h for h in hinweise) and not a.entwurf:
        sys.exit("Erst ausfüllen: " + "; ".join(hinweise) + " (Vorschau: --entwurf)")
    for h in hinweise:
        print("Hinweis: " + h)
    kopf = md_kopf(md)
    schriften_laden(Path(a.fonts))
    bilder = Bilder(a.cache, mobil=not a.druck)
    basis = Path(a.out); basis.parent.mkdir(parents=True, exist_ok=True)
    stempel = a.stempel or kopf.get("stempel")
    ziele = {"fazit": basis.with_name(basis.name + "_fazit.pdf"), "tausch": basis.with_name(basis.name + "_tausch.pdf"),
             "deck": basis.with_name(basis.name + "_deck.pdf"), "txt": basis.with_name(basis.name + "_moxfield.txt")}
    bericht_pdf(stempel_md(md, stempel), ziele["fazit"])
    deckname = a.deckname or kopf.get("deckname", "")
    karten_t = []
    if a.alt:
        karten_t, _ = vergleich_db(argparse.Namespace(db=a.db, alt=a.alt, neu=a.neu, idee=a.idee, deckname=deckname))
        schreibe_tauschliste(ziele["tausch"].with_suffix(".txt"),
                             {"titel": f"Tauschübersicht {deckname}".strip(), "deck": kopf.get("voll", ""), "datum": HEUTE},
                             karten_t)
    dkopf, karten_d, commander = lies_deck(a.neu)
    fehlt = scryfall(karten_t + commander + karten_d, (kopf.get("set") or "").lower())
    geladen, auftraege = bilder.vorladen(karten_t + commander + karten_d, gross=commander)
    if karten_t:
        tausch_pdf({"titel": f"Tauschübersicht {deckname}".strip(), "deck": kopf.get("voll", ""), "datum": HEUTE,
                    "stempel": stempel}, karten_t, ziele["tausch"], bilder)
        pngs = png(ziele["tausch"], a.dpi)
    teile = [x.strip() for x in kopf.get("voll", "").split("|")]
    info = dict(format=teile[0] if teile else "", name=deckname or (teile[1] if len(teile) > 1 else Path(a.neu).stem),
                farben=teile[2] if len(teile) > 2 else "", strategie=teile[3] if len(teile) > 3 else "",
                herkunft=teile[4] if len(teile) > 4 else "", stand=HEUTE, titelkarte=None, hinweis="",
                bracket=kopf.get("bracket_zeile"), beschreibung=kopf.get("beschreibung"), themen=kopf.get("themen"),
                status=kopf.get("status"), wert=kopf.get("wert"), stempel=stempel)
    deck_pdf(info, karten_d, commander, ziele["deck"], bilder)
    block = einfuege_aus_md(md) or Path(a.neu).read_text(encoding="utf-8")
    ziele["txt"].write_text(block, encoding="utf-8")
    print(f"Lieferung in {time.time() - t0:.0f} s (Bilder: {geladen}/{auftraege} neu geladen, parallel):")
    for k in ("fazit", "tausch", "deck", "txt"):
        if ziele[k].exists() and (k != "tausch" or karten_t):
            print(f"  {k:7s} {ziele[k]}  ({ziele[k].stat().st_size / 1e6:.1f} MB)")
    if karten_t:
        print("  png     " + ", ".join(str(p) for p in pngs))
    if bilder.platzhalter:
        print(f"Hinweis: {bilder.platzhalter} Platzhalter statt Bild" + (" (Bildserver nicht erreichbar)" if bilder.gesperrt else ""))
    if fehlt:
        print("Nicht bei Scryfall gefunden: " + ", ".join(fehlt))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="befehl", required=True)
    t = sub.add_parser("tausch", help="Tauschübersicht")
    t.add_argument("tauschliste", nargs="?")
    t.add_argument("--alt"); t.add_argument("--neu")
    t.add_argument("--frei"); t.add_argument("--bestand"); t.add_argument("--vormerkungen"); t.add_argument("--idee")
    t.add_argument("--haves", nargs="+"); t.add_argument("--deckname", default="")
    t.add_argument("--titel"); t.add_argument("--deck", dest="deckzeile")
    t.add_argument("--db", help="mtg.sqlite: Quelle, Druck und Sprache aus der Exemplar-Zuordnung (empfohlen)")
    t.add_argument("--ohne-png", action="store_true", help="keine PNG-Seiten (Standard: PNG für den Tisch)")
    v = sub.add_parser("verkauf", help="Verkaufs-PDF aus einer Verkaufsliste (deckbau.py verkauf)")
    v.add_argument("verkaufsliste")
    v.add_argument("--titel")
    v.add_argument("--ohne-png", action="store_true", help="keine PNG-Seiten (Standard: PNG fürs Handy)")
    d = sub.add_parser("deck", help="Deck-PDF")
    d.add_argument("deckdatei")
    d.add_argument("--set", default="", help="bevorzugtes Set für Karten ohne Druckangabe (z. B. tdc)")
    for opt in ("name", "bracket", "beschreibung", "themen", "status", "wert", "hinweis", "voll", "stand", "titelkarte"):
        d.add_argument("--" + opt)
    b = sub.add_parser("bericht", help="Fazit-PDF aus Markdown")
    b.add_argument("markdown")
    sub.add_parser("vorlage", help="Markdown-Vorlage für das Fazit-PDF ausgeben")
    li = sub.add_parser("lieferung", help="nach der Freigabe alles in einem Lauf: Fazit-PDF, Tausch (PDF+PNG), Deck-PDF, TXT")
    li.add_argument("fazit", help="Fazit-Markdown (aus deckbau.py fazit, Platzhalter gefüllt)")
    li.add_argument("--neu", required=True, help="Entwurf mit eigenen Drucken (mtg_db.py drucke)")
    li.add_argument("--alt", help="Soll-Stand (bearbeitetes Deck) – ohne: neues Deck, keine Tauschübersicht")
    li.add_argument("--db", default="mtg.sqlite"); li.add_argument("--idee"); li.add_argument("--deckname", default="")
    li.add_argument("--entwurf", action="store_true", help="Vorschau trotz offener Platzhalter")
    li.add_argument("--druck", action="store_true", help="volle Bildauflösung (Standard: Handy-Größe)")
    li.add_argument("--stempel")
    li.add_argument("--out", required=True, help="Ausgabe-Präfix, z. B. out/endless-harvest")
    li.add_argument("--dpi", type=int, default=110)
    li.add_argument("--cache", default=str(HIER / "cache" / "kartenbilder"))
    li.add_argument("--fonts", default=str(HIER / "fonts"))
    for p in (t, v, d, b):
        p.add_argument("--stempel", help="roter Stempel auf Seite 1, z. B. 'TESTLAUF – nicht gebucht'")
        p.add_argument("--mobil", action="store_true", help="kleinere Bilder (Handy)")
    for p in (t, v, d, b):
        p.add_argument("--out", required=True, help="Ausgabe ohne Endung")
        p.add_argument("--png", action="store_true", help="PNG für das Handy (Deck: nur Deckblatt)")
        p.add_argument("--dpi", type=int, default=110)
        p.add_argument("--cache", default=str(HIER / "cache" / "kartenbilder"))
        p.add_argument("--fonts", default=str(HIER / "fonts"))
    a = ap.parse_args()
    if a.befehl == "vorlage":
        print(FAZIT_VORLAGE, end="")
        return
    if a.befehl == "lieferung":
        return lieferung(a)
    schriften_laden(Path(a.fonts))
    bilder = Bilder(a.cache, a.mobil)
    ziel = Path(a.out).with_suffix(".pdf"); ziel.parent.mkdir(parents=True, exist_ok=True)

    if a.befehl == "bericht":
        md = Path(a.markdown).read_text(encoding="utf-8")
        for h in md_pruefen(md):
            print("Hinweis: " + h)
        bericht_pdf(stempel_md(md, a.stempel), ziel)
        print(f"PDF: {ziel}  ({ziel.stat().st_size / 1e6:.1f} MB)")
        return
    if a.befehl == "verkauf":
        kopf, karten = lies_verkaufsliste(a.verkaufsliste)
        if not karten:
            sys.exit("Verkaufsliste ist leer.")
        if a.titel:
            kopf["titel"] = a.titel
        kopf["stempel"] = a.stempel or kopf.get("stempel")
        fehlt = scryfall(karten)
        verkauf_pdf(kopf, karten, ziel, bilder)
    elif a.befehl == "tausch":
        if a.db and a.alt and a.neu:
            karten, kurz = vergleich_db(a)
            kopf = {"titel": a.titel or f"Tauschübersicht {a.deckname or kurz}".strip(), "deck": a.deckzeile or "",
                    "datum": HEUTE}
            schreibe_tauschliste(ziel.with_suffix(".txt"), kopf, karten)
            print(f"Tauschliste: {ziel.with_suffix('.txt')}")
        elif a.alt and a.neu:
            karten = vergleich_zu_tausch(a)
            kopf = {"titel": a.titel or f"Tauschübersicht {a.deckname}".strip(), "deck": a.deckzeile or "",
                    "datum": HEUTE}
            schreibe_tauschliste(ziel.with_suffix(".txt"), kopf, karten)
            print(f"Tauschliste: {ziel.with_suffix('.txt')}")
        elif a.tauschliste:
            kopf, karten = lies_tauschliste(a.tauschliste)
            if a.titel: kopf["titel"] = a.titel
        else:
            sys.exit("Tauschliste oder --alt/--neu angeben")
        if not karten:
            sys.exit("Keine Unterschiede – nichts zu tauschen.")
        kopf["stempel"] = a.stempel or kopf.get("stempel")
        fehlt = scryfall(karten)
        tausch_pdf(kopf, karten, ziel, bilder)
    else:
        kopf, karten, commander = lies_deck(a.deckdatei)
        teile = [x.strip() for x in (a.voll or kopf.get("voll", "")).split("|")]
        info = dict(format=teile[0] if teile else "", name=a.name or (teile[1] if len(teile) > 1 else Path(a.deckdatei).stem),
                    farben=teile[2] if len(teile) > 2 else "", strategie=teile[3] if len(teile) > 3 else "",
                    herkunft=teile[4] if len(teile) > 4 else "", stand=a.stand or kopf.get("stand", ""),
                    titelkarte=a.titelkarte,
                    hinweis=a.hinweis or ("vorläufig" if kopf.get("vorlaeufig") else ""),
                    bracket=a.bracket, beschreibung=a.beschreibung, themen=a.themen, status=a.status, wert=a.wert,
                    stempel=a.stempel)
        if info["stand"] and re.match(r"\d{4}-\d{2}-\d{2}", info["stand"]):
            j, m, t_ = info["stand"].split("-"); info["stand"] = f"{t_}.{m}.{j}"
        fehlt = scryfall(commander + karten, a.set.lower())
        deck_pdf(info, karten, commander, ziel, bilder)
    print(f"PDF: {ziel}  ({ziel.stat().st_size / 1e6:.1f} MB)")
    print(f"Bilder echt: {bilder.echt} · Platzhalter: {bilder.platzhalter}")
    if bilder.gesperrt:
        print("Hinweis: Bildserver cards.scryfall.io nicht erreichbar – Platzhalter verwendet.")
    if fehlt:
        print("Nicht bei Scryfall gefunden: " + ", ".join(fehlt))
    if a.png or (a.befehl in ("tausch", "verkauf") and not a.ohne_png):
        print("PNG: " + ", ".join(str(p) for p in png(ziel, a.dpi, nur_erste=(a.befehl == "deck"))))


if __name__ == "__main__":
    main()
