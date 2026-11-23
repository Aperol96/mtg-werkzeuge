#!/usr/bin/env python3
"""protokoll.py – Protokolle, Ideen, Kaufliste und Vormerkungen lesen und pflegen, ohne die Dateien ganz zu lesen.

Alle Dateien liegen im Daten-Repo (Arbeitsordner: projekt/ → protokolle/, data/ → sammlung/). Claude liest nur, was die
Aufgabe braucht, schreibt mit diesem Werkzeug und sichert am Ende der Schreibrunde mit einem `git push` (05a, Abschnitt 6).

Dateien
  projekt/09_Aenderungsprotokoll.md     Bestand, Decks, Ideen, Entscheidungen, Hinweise
  projekt/10_Geplante-Kaeufe-und-Ideen.md  Ideen, geplante Verkäufe, „In Moxfield nachziehen“
  projekt/04_Deckregister.md            Übersicht der Decks
  data/kaufliste.csv                    Kaufliste (einzige Quelle; Spalten Idee, Name, Anzahl, Art, Preis, Stand, Status, Hinweis)
  data/vormerkungen.csv                 Vormerkungen (einzige Quelle; Idee, Name, Anzahl, Datum, Hinweis – liest mtg_db.py)
  admin/09a_Programm-Protokoll.md, admin/14_Projekt-Aufwand.md   nur Admin (Typ „Werkzeug“ geht nach 09a)
  ideen/<deck>-primer.md                Deck-Primer (Nachschlagewerk zum Deck)

Befehle
  zeigen [--deck D] [--typ T] [--suche S] [--letzte N] [--datei 09|09a]   Einträge (neueste zuerst)
  neu --typ <Typ> --thema <Deck/Thema> --zeile "…" [--zeile …] [--datum JJJJ-MM-TT]   Eintrag oben einfügen
  offen [--deck D]                  Ideen, Verkäufe, Kaufliste, Vormerkungen, „In Moxfield nachziehen“ – kompakt
  idee-neu --deck D --inhalt T --status S [--details P]   → nächste ID I-nnn (Status aus STATUS_IDEE)
  idee-status <ID> <Status>         Status einer Idee bzw. eines Verkaufs (feste Werte, Zusatz nach „ · “ erlaubt)
  idee-entfernen <ID>               Idee samt Kaufzeilen und Vormerkungen entfernen
  kauf-neu --idee ID --karte K [--anzahl N] [--preis 1,23] [--art Kauf|Standardland] [--hinweis T]
  kauf-status --idee ID <geplant|bestellt|angekommen> [--karte K]     Kaufzeilen einer Idee (oder einer Karte)
  kauf-entfernen --idee ID [--karte K]
  vormerken --idee ID --karte K [--anzahl N] [--hinweis T]  ·  vormerkung-entfernen --idee ID [--karte K]
  nachziehen --was T --aufgabe T  ·  nachziehen-erledigt <Teiltext>
  register [--deck D]               Zeile(n) des Deckregisters
  primer [--deck D]                 Primer je Deck und ob er älter ist als der Soll-Stand
  aufwand [--seit …] [--eintragen "<Was>"]   Aufwand der Sitzung (nur Admin; Claude-Code-Transkripte)
"""
import argparse
import csv
import glob
import os
import re
import sys
import time
from collections import Counter

ORDNER = "projekt"
SAMMLUNG = "data"
ADMIN = "admin"
DATEIEN = {"09": "09_Aenderungsprotokoll.md", "09a": "09a_Programm-Protokoll.md",
           "10": "10_Geplante-Kaeufe-und-Ideen.md", "04": "04_Deckregister.md", "14": "14_Projekt-Aufwand.md"}
TYPEN_09 = ["Kauf", "Verkauf", "Import", "Abgleich", "Deck neu", "Deck geändert", "Idee", "Entscheidung", "Hinweis"]
TYPEN_09A = ["Werkzeug"]
STATUS_IDEE = ["wartet auf Freigabe", "freigegeben – Aufbau offen", "teilweise gebaut", "bestellt – Ankunft offen",
               "gebaut – Buchen offen", "zurückgestellt"]
STATUS_VERKAUF = ["geplant", "eingestellt", "teilweise verkauft"]
STATUS_KAUF = ["geplant", "bestellt", "angekommen"]
KAUF_SPALTEN = ["Idee", "Name", "Anzahl", "Art", "Preis", "Stand", "Status", "Hinweis"]
VORM_SPALTEN = ["Idee", "Name", "Anzahl", "Datum", "Hinweis"]
RX_EINTRAG = re.compile(r"^### (\d{4}-\d{2}-\d{2}) · ([^·]+?) · (.+)$")


def pfad(kurz, ordner=None):
    ordner = ordner or (ADMIN if kurz in ("09a", "14") and os.path.isdir(ADMIN) else ORDNER)
    p = os.path.join(ordner, DATEIEN[kurz])
    if not os.path.exists(p):
        sys.exit(f"{p} fehlt – Daten-Repo klonen und verknüpfen (05a, Abschnitt 3)")
    return p


def status_pruefen(status, erlaubt):
    """Feste Status-Werte; ein Zusatz nach „ · “ ist erlaubt („bestellt – Ankunft offen · Rest mit der Bestellung“)."""
    kern = status.split(" · ")[0].strip()
    if kern not in erlaubt:
        sys.exit(f"Status „{status}“ – erlaubt: {' | '.join(erlaubt)} (Zusatz nach „ · “)")
    return status


def csv_lesen(datei, spalten):
    p = os.path.join(SAMMLUNG, datei)
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return [{k: (r.get(k) or "").strip() for k in spalten} for r in csv.DictReader(fh) if (r.get("Name") or "").strip()]


def csv_schreiben(datei, spalten, zeilen):
    p = os.path.join(SAMMLUNG, datei)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=spalten, lineterminator="\n")
        w.writeheader()
        w.writerows(zeilen)


def passt(zeile, idee=None, karte=None):
    return (not idee or zeile["Idee"] == idee) and (not karte or norm(zeile["Name"]) == norm(karte))


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
    kauf, vorm = csv_lesen("kaufliste.csv", KAUF_SPALTEN), csv_lesen("vormerkungen.csv", VORM_SPALTEN)
    ids = None
    if a.deck:                                   # Ideen des Decks – ihre Kauf- und Vormerkungszeilen gehören dazu
        ids = {x.split("|")[1].strip() for t in ("Offene Ideen", "Geplante Verkäufe")
               for x in tabellenzeilen(text, t) if norm(a.deck) in norm(x)}
    for titel in ("Offene Ideen", "Geplante Verkäufe"):
        z = [x for x in tabellenzeilen(text, titel) if not re.match(r"^\|\s*–\s*\|", x)]
        if ids is not None:
            z = [x for x in z if x.split("|")[1].strip() in ids]
        print(f"{titel}: " + ("–" if not z else ""))
        for x in z:
            zellen = [c.strip() for c in x.strip("|").split("|")]
            print("  " + " · ".join(c[:160] for c in zellen if c and c != "–"))
    k = [r for r in kauf if ids is None or r["Idee"] in ids]
    summe = sum(float(r["Preis"].replace(",", ".") or 0) * int(r["Anzahl"] or 1) for r in k if r["Preis"])
    print(f"Kaufliste ({SAMMLUNG}/kaufliste.csv): " + ("–" if not k else f"{len(k)} Zeilen · ab {summe:.2f} €".replace(".", ",")))
    for idee in dict.fromkeys(r["Idee"] for r in k):
        zz = [r for r in k if r["Idee"] == idee]
        st = Counter(r["Status"] or "geplant" for r in zz)
        print(f"  {idee}: " + " · ".join(f"{n} {s_}" for s_, n in st.items()) + " – "
              + ", ".join(f"{r['Name']}" + (f" ×{r['Anzahl']}" if r["Anzahl"] not in ("", "1") else "") for r in zz[:12])
              + (" …" if len(zz) > 12 else ""))
    v = [r for r in vorm if (ids is None or r["Idee"] in ids)]
    print(f"Vormerkungen ({SAMMLUNG}/vormerkungen.csv): " + ("–" if not v else ""))
    for idee in dict.fromkeys(r["Idee"] for r in v):
        zz = [r for r in v if r["Idee"] == idee]
        if idee.startswith("V-"):
            print(f"  {idee}: {len(zz)} Karten (weich – geplanter Verkauf, bleiben frei)")
        else:
            print(f"  {idee}: " + ", ".join(r["Name"] for r in zz))
    z = [x for x in tabellenzeilen(text, "In Moxfield nachziehen") if not re.match(r"^\|\s*–\s*\|", x)]
    if a.deck:
        z = [x for x in z if norm(a.deck) in norm(x)]
    print("In Moxfield nachziehen: " + ("–" if not z else ""))
    for x in z:
        print("  " + " · ".join(c.strip() for c in x.strip("|").split("|") if c.strip() and c.strip() != "–"))


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
    status_pruefen(a.status, STATUS_IDEE)
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
            status_pruefen(a.status, STATUS_VERKAUF if a.id.startswith("V-") else STATUS_IDEE)
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
    schreibe("10", "\n".join(z for z in text.splitlines() if z not in raus) + "\n")
    n = {}
    for datei, sp in (("kaufliste.csv", KAUF_SPALTEN), ("vormerkungen.csv", VORM_SPALTEN)):
        alle = csv_lesen(datei, sp)
        rest = [r for r in alle if r["Idee"] != a.id]
        n[datei] = len(alle) - len(rest)
        if n[datei]:
            csv_schreiben(datei, sp, rest)
    print(f"{a.id}: aus 10 entfernt · {n['kaufliste.csv']} Kaufzeilen · {n['vormerkungen.csv']} Vormerkungen")


def preis_norm(t):
    return (t or "").replace("€", "").strip().replace(".", ",")


def cmd_kauf_neu(a):
    alle = csv_lesen("kaufliste.csv", KAUF_SPALTEN)
    for k in a.karte:
        if any(passt(r, a.idee, k) for r in alle):
            print(f"schon in der Kaufliste: {a.idee} {k}")
            continue
        alle.append({"Idee": a.idee, "Name": k, "Anzahl": str(a.anzahl), "Art": a.art, "Preis": preis_norm(a.preis),
                     "Stand": time.strftime("%Y-%m-%d") if a.preis else "", "Status": "geplant", "Hinweis": a.hinweis or ""})
        print(f"Kaufliste + {a.idee} · {a.anzahl}× {k}" + (f" · {preis_norm(a.preis)} €" if a.preis else ""))
    csv_schreiben("kaufliste.csv", KAUF_SPALTEN, alle)


def cmd_kauf_status(a):
    status_pruefen(a.status, STATUS_KAUF)
    alle = csv_lesen("kaufliste.csv", KAUF_SPALTEN)
    n = 0
    for r in alle:
        if passt(r, a.idee, a.karte):
            r["Status"] = a.status + (f" {time.strftime('%Y-%m-%d')}" if a.status != "geplant" else "")
            n += 1
    if not n:
        sys.exit("keine passende Kaufzeile")
    csv_schreiben("kaufliste.csv", KAUF_SPALTEN, alle)
    print(f"{n} Kaufzeilen: {a.status}")


def entfernen(datei, spalten, idee, karte):
    alle = csv_lesen(datei, spalten)
    rest = [r for r in alle if not passt(r, idee, karte)]
    csv_schreiben(datei, spalten, rest)
    print(f"{datei}: {len(alle) - len(rest)} Zeilen entfernt ({idee}{' · ' + karte if karte else ''})")


def cmd_kauf_entfernen(a):
    entfernen("kaufliste.csv", KAUF_SPALTEN, a.idee, a.karte)


def cmd_vormerken(a):
    alle = csv_lesen("vormerkungen.csv", VORM_SPALTEN)
    for k in a.karte:
        if any(passt(r, a.idee, k) for r in alle):
            print(f"schon vorgemerkt: {a.idee} {k}")
            continue
        alle.append({"Idee": a.idee, "Name": k, "Anzahl": str(a.anzahl), "Datum": time.strftime("%Y-%m-%d"),
                     "Hinweis": a.hinweis or ""})
        print(f"vorgemerkt: {a.idee} · {a.anzahl}× {k}")
    csv_schreiben("vormerkungen.csv", VORM_SPALTEN, alle)
    print("Konflikte (mehr vorgemerkt als frei) meldet der nächste Datenbank-Bau.")


def cmd_vormerkung_entfernen(a):
    entfernen("vormerkungen.csv", VORM_SPALTEN, a.idee, a.karte)


def git_datum(datei):
    import subprocess
    try:
        r = subprocess.run(["git", "-C", os.path.dirname(os.path.realpath(datei)), "log", "-1", "--format=%cs", "--",
                            os.path.realpath(datei)], capture_output=True, text=True, timeout=20)
        if r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(datei)))


def cmd_primer(a):
    """Primer = Nachschlagewerk zum Deck: vorhanden? Stand gegen die letzte Änderung des Soll-Stands."""
    zeilen, gesehen = 0, set()
    for d in sorted(os.listdir("decks")) if os.path.isdir("decks") else []:
        if not d.endswith(".txt"):
            continue
        slug = d[:-4]
        kopf = open(os.path.join("decks", d), encoding="utf-8").readline()
        teile = [t.strip() for t in kopf.split("|")]
        name = teile[1] if len(teile) > 2 else slug
        if a.deck and norm(a.deck) not in norm(name) and norm(a.deck) not in norm(slug):
            continue
        zeilen += 1
        pr = os.path.join("ideen", f"{slug}-primer.md")
        gesehen.add(pr)
        if not os.path.exists(pr):
            print(f"{name}: kein Primer – Deck aus Soll-Stand und Werkzeugen erschließen; nach dem Upgrade Primer anlegen")
            continue
        m = re.search(r"Stand (\d{2})\.(\d{2})\.(\d{4})", open(pr, encoding="utf-8").read(600))
        stand = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else git_datum(pr)
        deck = git_datum(os.path.join("decks", d))
        print(f"{name}: {pr} (Stand {stand})" + (f" ⚠ Soll-Stand geändert am {deck} – Primer prüfen und nachziehen"
                                                  if deck > stand else " · aktuell"))
    for pr in sorted(glob.glob(os.path.join("ideen", "*-primer.md"))):
        if pr not in gesehen and (not a.deck or norm(a.deck).replace(" ", "-").replace(",", "") in pr):
            zeilen += 1
            print(f"{os.path.basename(pr)[:-10]}: {pr} (Idee ohne Soll-Stand)")
    if not zeilen:
        print("kein passendes Deck")


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


def main(argv=None):
    global ORDNER, SAMMLUNG, ADMIN
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ordner", default=ORDNER, help="Ordner mit 04/09/10 (Standard: projekt)")
    ap.add_argument("--sammlung", default=SAMMLUNG, help="Ordner mit kaufliste.csv und vormerkungen.csv (Standard: data)")
    ap.add_argument("--admin", default=ADMIN, help="Ordner mit 09a und 14 (Standard: admin)")
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
    p = sp.add_parser("kauf-neu")
    p.add_argument("--idee", required=True)
    p.add_argument("--karte", action="append", required=True)
    p.add_argument("--anzahl", type=int, default=1)
    p.add_argument("--preis")
    p.add_argument("--art", default="Kauf", choices=["Kauf", "Standardland"])
    p.add_argument("--hinweis")
    p = sp.add_parser("kauf-status")
    p.add_argument("--idee", required=True)
    p.add_argument("status", choices=STATUS_KAUF)
    p.add_argument("--karte")
    p = sp.add_parser("kauf-entfernen")
    p.add_argument("--idee", required=True)
    p.add_argument("--karte")
    p = sp.add_parser("vormerken")
    p.add_argument("--idee", required=True)
    p.add_argument("--karte", action="append", required=True)
    p.add_argument("--anzahl", type=int, default=1)
    p.add_argument("--hinweis")
    p = sp.add_parser("vormerkung-entfernen")
    p.add_argument("--idee", required=True)
    p.add_argument("--karte")
    p = sp.add_parser("primer")
    p.add_argument("--deck")
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
    a = ap.parse_args(argv)
    ORDNER, SAMMLUNG, ADMIN = a.ordner, a.sammlung, a.admin
    {"zeigen": cmd_zeigen, "neu": cmd_neu, "offen": cmd_offen, "idee-neu": cmd_idee_neu, "idee-status": cmd_idee_status,
     "idee-entfernen": cmd_idee_entfernen, "nachziehen": cmd_nachziehen, "nachziehen-erledigt": cmd_nachziehen_erledigt,
     "register": cmd_register, "aufwand": cmd_aufwand, "kauf-neu": cmd_kauf_neu, "kauf-status": cmd_kauf_status,
     "kauf-entfernen": cmd_kauf_entfernen, "vormerken": cmd_vormerken, "vormerkung-entfernen": cmd_vormerkung_entfernen,
     "primer": cmd_primer}[a.cmd](a)


if __name__ == "__main__":
    main()
