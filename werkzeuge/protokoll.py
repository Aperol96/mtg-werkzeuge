#!/usr/bin/env python3
"""protokoll.py – Änderungsprotokoll, Ideenliste und Deckregister lesen und pflegen, ohne sie ganz zu lesen (V1.6).

Die Dateien kommen mit dem Datenpaket in den Arbeitsordner (projekt/…). Claude liest nur, was die Aufgabe braucht,
und schreibt Einträge mit diesem Werkzeug; danach `paket.py geaendert` → project_write(local_path=…) → Datenpaket neu.

Dateien (Projektpfad → Arbeitsordner)
  claude/09_Aenderungsprotokoll.md   projekt/09_Aenderungsprotokoll.md   Bestand, Decks, Ideen, Entscheidungen, Hinweise
  claude/09a_Programm-Protokoll.md   projekt/09a_Programm-Protokoll.md   Werkzeug-Einträge (nur Admin)
  claude/10_Geplante-Kaeufe-und-Ideen.md  projekt/10_…                   Ideen, Verkäufe, Kaufliste, Moxfield nachziehen
  claude/04_Deckregister.md          projekt/04_Deckregister.md          Übersicht der Decks

Befehle
  zeigen [--deck <Name>] [--typ <Typ>] [--suche <Text>] [--letzte N] [--datei 09|09a]
        Einträge (neueste zuerst), gefiltert. Ohne Filter die letzten 5.
  neu --typ <Typ> --thema <Deck/Thema> --zeile "<Text>" [--zeile …] [--datum JJJJ-MM-TT] [--datei 09|09a]
        Eintrag oben unter „## Einträge“ einfügen. Typ „Werkzeug“ geht automatisch nach 09a.
  offen [--deck <Name>]
        Offene Ideen, geplante Verkäufe, Kaufliste, Vormerkungen und „In Moxfield nachziehen“ aus 10 – kompakt.
  idee-neu --deck <Deck> --inhalt <Text> --status <Status> [--details <Pfad>]   → nächste ID I-nnn
  idee-status <ID> <Status>          Status einer Idee oder eines Verkaufs (I-nnn, V-nnn) ändern
  idee-entfernen <ID>                Idee/Verkauf samt ihrer Kauf- und Vormerkungszeilen aus 10 entfernen
                                     (Vormerkungen in claude/sammlung/vormerkungen.csv entfernt mtg_db/Claude getrennt)
  nachziehen --was <Text> --aufgabe <Text>      Zeile „In Moxfield nachziehen / Wartung“ anlegen
  nachziehen-erledigt <Teiltext>               passende Zeile entfernen
  register [--deck <Name>]           Zeile(n) des Deckregisters
  aufwand [--seit JJJJ-MM-TT] [--eintragen "<Was>"] [--willkommen <projektanweisungen.md>]
        Aufwand dieser Sitzung aus den Claude-Code-Transkripten (aktive Zeit, Token, API-Gegenwert in €);
        mit --eintragen als Zeile in 14_Projekt-Aufwand.md (nur Admin), mit --willkommen den Vermerk 🕒 in der
        Willkommensnachricht neu setzen. In claude.ai-Chats ohne Transkript: Zeile von Hand („nicht gemessen“).
"""
import argparse
import os
import re
import sys
import time

ORDNER = "projekt"
DATEIEN = {"09": "09_Aenderungsprotokoll.md", "09a": "09a_Programm-Protokoll.md",
           "10": "10_Geplante-Kaeufe-und-Ideen.md", "04": "04_Deckregister.md", "14": "14_Projekt-Aufwand.md"}
TYPEN_09 = ["Kauf", "Verkauf", "Import", "Abgleich", "Deck neu", "Deck geändert", "Idee", "Entscheidung", "Hinweis"]
TYPEN_09A = ["Werkzeug"]
RX_EINTRAG = re.compile(r"^### (\d{4}-\d{2}-\d{2}) · ([^·]+?) · (.+)$")


def pfad(kurz, ordner=None):
    p = os.path.join(ordner or ORDNER, DATEIEN[kurz])
    if not os.path.exists(p):
        sys.exit(f"{p} fehlt – Datenpaket auspacken (paket.py auspacken …)")
    return p


def lies(kurz):
    return open(pfad(kurz), encoding="utf-8").read()


def schreibe(kurz, text):
    open(pfad(kurz), "w", encoding="utf-8").write(text)


def eintraege(text):
    """-> [(Kopfzeile, Datum, Typ, Thema, Block)] in Dateireihenfolge (neueste oben)."""
    teil = text.split("## Einträge", 1)[1] if "## Einträge" in text else text
    bloecke = re.split(r"(?m)^(?=### \d{4}-\d{2}-\d{2} · )", teil)
    out = []
    for b in bloecke:
        m = RX_EINTRAG.match(b.splitlines()[0]) if b.strip() else None
        if m:
            out.append((b.splitlines()[0], m.group(1), m.group(2).strip(), m.group(3).strip(), b.rstrip()))
    return out


def norm(s):
    return re.sub(r"\s+", " ", (s or "").lower())


def cmd_zeigen(a):
    dateien = [a.datei] if a.datei else ["09"] + (["09a"] if a.typ == "Werkzeug" else [])
    treffer = []
    for d in dateien:
        for e in eintraege(lies(d)):
            if a.typ and norm(e[2]) != norm(a.typ):
                continue
            if a.deck and norm(a.deck) not in norm(e[4]):
                continue
            if a.suche and norm(a.suche) not in norm(e[4]):
                continue
            treffer.append(e)
    treffer.sort(key=lambda e: e[1], reverse=True)
    n = a.letzte or (5 if not (a.deck or a.typ or a.suche) else 15)
    for e in treffer[:n]:
        print(e[4] + "\n")
    print(f"({min(n, len(treffer))} von {len(treffer)} Einträgen" + (" – mehr mit --letzte N)" if len(treffer) > n else ")"))


def cmd_neu(a):
    datei = a.datei or ("09a" if a.typ == "Werkzeug" else "09")
    erlaubt = TYPEN_09A if datei == "09a" else TYPEN_09
    if a.typ not in erlaubt:
        sys.exit(f"Typ „{a.typ}“ gehört nicht nach {datei} – erlaubt: {', '.join(erlaubt)}")
    datum = a.datum or time.strftime("%Y-%m-%d")
    block = f"### {datum} · {a.typ} · {a.thema}\n" + "\n".join(
        z if z.startswith("- ") else f"- {z}" for z in a.zeile) + "\n\n"
    text = lies(datei)
    if "## Einträge" not in text:
        sys.exit(f"{DATEIEN[datei]}: Überschrift „## Einträge“ fehlt")
    kopf, rest = text.split("## Einträge", 1)
    text = kopf + "## Einträge\n\n" + block + rest.lstrip("\n")
    schreibe(datei, text)
    print(f"Eintrag in {DATEIEN[datei]}:\n{block.rstrip()}")


def abschnitt(text, titel):
    """-> (Start, Ende) des Abschnitts '## <titel…>' (bis zur nächsten '## ')."""
    m = re.search(rf"(?m)^## {re.escape(titel)}.*$", text)
    if not m:
        return None
    n = re.search(r"(?m)^## ", text[m.end():])
    return m.start(), (m.end() + n.start()) if n else len(text)


def tabellenzeilen(text, titel):
    ab = abschnitt(text, titel)
    if not ab:
        return []
    zeilen = text[ab[0]:ab[1]].splitlines()
    return [z for z in zeilen if z.startswith("|") and not re.match(r"^\|[-| ]+\|$", z)][1:]


def cmd_offen(a):
    text = lies("10")
    ids = set()
    if a.deck:                                   # Ideen des Decks – ihre Kauf- und Vormerkungszeilen gehören dazu
        for titel in ("Offene Ideen", "Geplante Verkäufe"):
            ids |= {x.split("|")[1].strip() for x in tabellenzeilen(text, titel) if norm(a.deck) in norm(x)}
    for titel in ("Offene Ideen", "Geplante Verkäufe", "Kaufliste", "Aus der Sammlung vorgemerkt",
                  "In Moxfield nachziehen"):
        z = tabellenzeilen(text, titel)
        if a.deck:
            z = [x for x in z if norm(a.deck) in norm(x) or x.split("|")[1].strip() in ids]
        z = [x for x in z if not re.match(r"^\|\s*–\s*\|", x)]
        print(f"{titel}: " + ("–" if not z else ""))
        for x in z:
            zellen = [c.strip() for c in x.strip("|").split("|")]
            print("  " + " · ".join(c[:160] for c in zellen if c and c != "–"))


def naechste_id(text, praefix):
    ids = [int(x) for x in re.findall(rf"\b{praefix}-(\d{{3}})\b", text)]
    return f"{praefix}-{(max(ids) + 1 if ids else 1):03d}"


def zeile_einfuegen(text, titel, zeile):
    ab = abschnitt(text, titel)
    if not ab:
        sys.exit(f"Abschnitt „## {titel}“ fehlt in 10")
    block = text[ab[0]:ab[1]]
    zeilen = block.splitlines()
    trenner = next((i for i, z in enumerate(zeilen) if re.match(r"^\|[-| ]+\|$", z)), None)
    if trenner is None:
        sys.exit(f"Tabelle in „{titel}“ nicht gefunden")
    zeilen = [z for i, z in enumerate(zeilen) if not (i > trenner and re.match(r"^\|\s*–\s*\|", z))]
    zeilen.insert(trenner + 1, zeile)
    return text[:ab[0]] + "\n".join(zeilen) + ("\n" if block.endswith("\n") else "") + text[ab[1]:]


def cmd_idee_neu(a):
    text = lies("10")
    iid = naechste_id(text, "I")
    zeile = (f"| {iid} | {time.strftime('%d.%m.%Y')} | {a.deck} | {a.inhalt.replace('|', '/')} | {a.status} | "
             f"{a.details or '–'} |")
    schreibe("10", zeile_einfuegen(text, "Offene Ideen", zeile))
    print(f"{iid} angelegt: {zeile}")


def cmd_idee_status(a):
    text = lies("10")
    zeilen = text.splitlines()
    for i, z in enumerate(zeilen):
        zellen = z.split("|")
        if len(zellen) > 6 and zellen[1].strip() == a.id and z.startswith("|"):
            zellen[-3] = f" {a.status} "
            zeilen[i] = "|".join(zellen)
            schreibe("10", "\n".join(zeilen) + "\n")
            print(f"{a.id}: Status „{a.status}“")
            return
    sys.exit(f"{a.id} nicht in den Tabellen „Offene Ideen“/„Geplante Verkäufe“")


def cmd_idee_entfernen(a):
    text = lies("10")
    raus = [z for z in text.splitlines() if z.startswith("|") and z.split("|")[1].strip() == a.id]
    if not raus:
        sys.exit(f"{a.id} nicht gefunden")
    text = "\n".join(z for z in text.splitlines() if z not in raus) + "\n"
    schreibe("10", text)
    print(f"{a.id}: {len(raus)} Zeilen entfernt (Idee, Kauf- und Vormerkungszeilen). Vormerkungen in "
          "claude/sammlung/vormerkungen.csv getrennt entfernen.")


def cmd_nachziehen(a):
    text = lies("10")
    zeile = f"| {time.strftime('%d.%m.%Y')} | {a.was.replace('|', '/')} | {a.aufgabe.replace('|', '/')} |"
    schreibe("10", zeile_einfuegen(text, "In Moxfield nachziehen", zeile))
    print(f"angelegt: {zeile}")


def cmd_nachziehen_erledigt(a):
    text = lies("10")
    ab = abschnitt(text, "In Moxfield nachziehen")
    block = text[ab[0]:ab[1]]
    zeilen = block.splitlines()
    treffer = [z for z in zeilen if z.startswith("|") and norm(a.text) in norm(z) and not re.match(r"^\|[-| ]+\|$", z)]
    if len(treffer) != 1:
        sys.exit(f"{len(treffer)} Zeilen passen zu „{a.text}“ – genauer angeben")
    zeilen.remove(treffer[0])
    if not [z for z in zeilen if z.startswith("|")][2:]:
        zeilen.append("| – | derzeit nichts offen | – |")
    schreibe("10", text[:ab[0]] + "\n".join(zeilen) + ("\n" if block.endswith("\n") else "") + text[ab[1]:])
    print(f"erledigt: {treffer[0]}")


def cmd_register(a):
    text = lies("04")
    for z in text.splitlines():
        if z.startswith("| ") and not z.startswith("| Deckname") and (not a.deck or norm(a.deck) in norm(z)):
            print(z)


# ----------------------------------------------------------------- Aufwand (Zeit, Token, €)
# Listenpreise USD je Mio. Token (platform.claude.com/docs/en/about-claude/pricing, abgerufen 29.10.2026):
# Eingabe, Cache schreiben 5 min, Cache schreiben 1 h, Cache lesen, Ausgabe
PREISE = {"opus": (4.0, 5.0, 8.0, 0.20, 20.0), "sonnet": (2.0, 2.5, 4.0, 0.10, 10.0), "haiku": (0.5, 0.625, 1.0, 0.05, 2.5)}
EUR_JE_USD = 1 / 1.15            # EZB-Referenzkurs ≈ 1,15 USD/EUR (Sept./Okt. 2026) – beim Eintragen mit Datum nennen
PAUSE_MIN = 30                   # Lücken über 30 Minuten zählen nicht als Arbeitszeit


def transkripte(muster=None):
    import glob
    basis = os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude"))
    return sorted(glob.glob(muster or os.path.join(basis, "projects", "*", "**", "*.jsonl"), recursive=True))


def aufwand_messen(dateien, seit=None):
    """-> dict: aktive Minuten, Token je Art, USD. Unteragenten (Unterordner) zählen mit; ihre Zeit läuft parallel –
    die Zeitstempel aller Dateien bilden eine gemeinsame Zeitachse, Lücken über PAUSE_MIN zählen nicht."""
    import json
    from datetime import datetime
    tok = {"eingabe": 0, "cache_5m": 0, "cache_1h": 0, "cache_lesen": 0, "ausgabe": 0}
    usd, zeiten, erster = 0.0, [], None
    for f in dateien:
        for zeile in open(f, encoding="utf-8", errors="replace"):
            try:
                d = json.loads(zeile)
            except ValueError:
                continue
            ts = d.get("timestamp")
            if seit and ts and ts[:10] < seit:
                continue
            if ts:
                zeiten.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
            m = d.get("message") if isinstance(d.get("message"), dict) else None
            u = m.get("usage") if m else None
            if d.get("type") != "assistant" or not u:
                continue
            modell = next((k for k in PREISE if k in (m.get("model") or "")), "opus")
            pr = PREISE[modell]
            cc = u.get("cache_creation") or {}
            c1h = cc.get("ephemeral_1h_input_tokens")
            c5m = cc.get("ephemeral_5m_input_tokens")
            if c1h is None and c5m is None:
                c1h, c5m = u.get("cache_creation_input_tokens", 0) or 0, 0
            werte = (u.get("input_tokens", 0) or 0, c5m or 0, c1h or 0, u.get("cache_read_input_tokens", 0) or 0,
                     u.get("output_tokens", 0) or 0)
            for k, w in zip(tok, werte):
                tok[k] += w
            usd += sum(w * p for w, p in zip(werte, pr)) / 1e6
    zeiten.sort()
    aktiv = sum(min((b - a).total_seconds(), PAUSE_MIN * 60) for a, b in zip(zeiten, zeiten[1:])
                if (b - a).total_seconds() <= PAUSE_MIN * 60) / 60
    return {"minuten": aktiv, "token": tok, "summe": sum(tok.values()), "usd": usd, "eur": usd * EUR_JE_USD,
            "von": zeiten[0].isoformat()[:16] if zeiten else "", "bis": zeiten[-1].isoformat()[:16] if zeiten else ""}


def de1(x, n=1):
    return f"{x:.{n}f}".replace(".", ",")


def mio(x):
    return f"{x / 1e6:.1f}".replace(".", ",")


def cmd_aufwand(a):
    dateien = transkripte(a.transkripte)
    if not dateien:
        sys.exit("Keine Claude-Code-Transkripte gefunden (claude.ai-Chat?) – Aufwand von Hand eintragen: "
                 "Datum, Dauer geschätzt, Token „nicht gemessen“.")
    r = aufwand_messen(dateien, a.seit)
    t = r["token"]
    from datetime import datetime
    spanne = ((datetime.fromisoformat(r["bis"]) - datetime.fromisoformat(r["von"])).total_seconds() / 3600
              if r["von"] else 0)
    print(f"Sitzung {r['von']} – {r['bis']} UTC · Zeitspanne {de1(spanne)} h, davon aktiv ≈ {de1(r['minuten'] / 60)} h "
          f"(Lücken > {PAUSE_MIN} min nicht gezählt) · {len(dateien)} Transkripte (inkl. Unteragenten)")
    print(f"Token: {mio(r['summe'])} Mio. verarbeitet – Cache lesen {mio(t['cache_lesen'])}, Cache schreiben "
          f"{mio(t['cache_5m'] + t['cache_1h'])}, Ausgabe {mio(t['ausgabe'])}, Eingabe {mio(t['eingabe'])}")
    print(f"API-Gegenwert: {de1(r['usd'], 2)} USD ≈ {de1(r['eur'], 2)} € (Listenpreise, Kurs {de1(1 / EUR_JE_USD, 2)} USD/EUR); "
          "im Abo zählt es aufs Nutzungslimit, nicht als Rechnung")
    if a.eintragen:
        text = lies("14")
        datum = (r["von"] or time.strftime("%Y-%m-%d"))[:10]
        zeile = (f"| {datum[8:10]}.{datum[5:7]}.{datum[:4]} | {a.eintragen.replace('|', '/')} | "
                 f"{de1(r['minuten'] / 60)} h | {mio(r['summe'])} Mio. | {r['eur']:.0f} € | gemessen |")
        zeilen = text.splitlines()
        i = max(n for n, z in enumerate(zeilen) if z.startswith("|"))
        zeilen.insert(i + 1, zeile)
        text = "\n".join(zeilen) + "\n"
        text = summen_setzen(text)
        schreibe("14", text)
        print(f"14: Zeile eingetragen – {zeile}")
        if a.willkommen:
            willkommen_setzen(a.willkommen, text)


def summen_setzen(text):
    """Summenzeile aus der Tabelle neu rechnen (nur gemessene Zeilen; Arbeitstage = verschiedene Daten)."""
    h = tok = eur = 0.0
    tage = set()
    for z in text.splitlines():
        zellen = [c.strip() for c in z.strip("|").split("|")]
        if len(zellen) >= 6 and re.match(r"\d\d\.\d\d\.\d{4}", zellen[0]):
            tage.add(zellen[0])
            if zellen[5] == "gemessen":
                h += float(zellen[2].split()[0].replace(",", "."))
                tok += float(zellen[3].split()[0].replace(",", "."))
                eur += float(zellen[4].split()[0].replace(",", "."))
    neu = (f"**Summe:** {len(tage)} Arbeitstage seit {min(tage, key=lambda d: d[6:] + d[3:5] + d[:2]) if tage else '–'}"
           f" · gemessen {de1(h)} h · {tok:.0f} Mio. Token · ≈ {eur:.0f} € API-Gegenwert")
    return re.sub(r"^\*\*Summe:\*\*.*$", neu, text, flags=re.M)


def willkommen_setzen(pfad, text):
    """Vermerk 🕒 am Ende der Willkommensnachricht aus der Summenzeile von 14 setzen."""
    m = re.search(r"^\*\*Summe:\*\* (.*)$", text, flags=re.M)
    if not m:
        return
    stand = time.strftime("%d.%m.%Y")
    vermerk = f"> 🕒 *Bisher in diesem Projekt: {m.group(1)} (Stand {stand})*"
    w = open(pfad, encoding="utf-8").read()
    w2 = re.sub(r"^> 🕒 .*$", vermerk, w, flags=re.M)
    open(pfad, "w", encoding="utf-8").write(w2)
    print(f"Willkommensnachricht in {pfad}: {vermerk}" if w2 != w else f"!! kein Vermerk 🕒 in {pfad} gefunden")


def main(argv=None):
    global ORDNER
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ordner", default=ORDNER, help="Ordner mit den Projektdateien (Standard: projekt)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("zeigen")
    p.add_argument("--deck")
    p.add_argument("--typ")
    p.add_argument("--suche")
    p.add_argument("--letzte", type=int)
    p.add_argument("--datei", choices=("09", "09a"))
    p = sp.add_parser("neu")
    p.add_argument("--typ", required=True)
    p.add_argument("--thema", required=True)
    p.add_argument("--zeile", action="append", required=True)
    p.add_argument("--datum")
    p.add_argument("--datei", choices=("09", "09a"))
    p = sp.add_parser("offen")
    p.add_argument("--deck")
    p = sp.add_parser("idee-neu")
    p.add_argument("--deck", required=True)
    p.add_argument("--inhalt", required=True)
    p.add_argument("--status", required=True)
    p.add_argument("--details")
    p = sp.add_parser("idee-status")
    p.add_argument("id")
    p.add_argument("status")
    p = sp.add_parser("idee-entfernen")
    p.add_argument("id")
    p = sp.add_parser("nachziehen")
    p.add_argument("--was", required=True)
    p.add_argument("--aufgabe", required=True)
    p = sp.add_parser("nachziehen-erledigt")
    p.add_argument("text")
    p = sp.add_parser("register")
    p.add_argument("--deck")
    p = sp.add_parser("aufwand")
    p.add_argument("--seit")
    p.add_argument("--transkripte", help="Glob-Muster der Transkripte (Standard: alle unter ~/.claude/projects)")
    p.add_argument("--eintragen", help="Kurzbeschreibung der Sitzung für 14_Projekt-Aufwand.md")
    p.add_argument("--willkommen", help="Projektanweisungen (projektanweisungen.md): Vermerk 🕒 neu setzen")
    a = ap.parse_args(argv)
    ORDNER = a.ordner
    {"zeigen": cmd_zeigen, "neu": cmd_neu, "offen": cmd_offen, "idee-neu": cmd_idee_neu, "idee-status": cmd_idee_status,
     "idee-entfernen": cmd_idee_entfernen, "nachziehen": cmd_nachziehen, "nachziehen-erledigt": cmd_nachziehen_erledigt,
     "register": cmd_register, "aufwand": cmd_aufwand}[a.cmd](a)


if __name__ == "__main__":
    main()
