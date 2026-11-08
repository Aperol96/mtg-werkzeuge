"""paket.py (Datenpaket mit 04/09/10, Rundlauf) und protokoll.py (Einträge und Ideen ohne die ganze Datei)."""
import os
import shutil

from conftest import DATEN, lauf

P09 = """# Änderungsprotokoll

## Regeln (für Claude)

| Typ | Anlass |
|---|---|
| Kauf | … |
| Hinweis | … |
| Werkzeug | … |

---

## Einträge

### 2026-10-01 · Kauf · Testdeck
- Buchung: B-001 Sol Ring
- Status: umgesetzt
"""
P10 = """# Geplante Käufe / Ideen

## Offene Ideen

| ID | Datum | Deck / Vorhaben | Inhalt | Status | Details |
|---|---|---|---|---|---|
| I-001 | 01.10.2026 | Testdeck | Länder | wartet auf Freigabe | – |

## Geplante Verkäufe (weich vorgemerkt – Karten bleiben frei)

| ID | Datum | Inhalt | Summe (Stand) | Status | Details |
|---|---|---|---|---|---|

## Kaufliste (Sammelbestellung)

| ID | Karte | Anzahl | Art | Preis ab € (Stand) | Hinweis |
|---|---|---|---|---|---|
| I-001 | Plains | 2 | Standardland | 0,02 | – |

## Aus der Sammlung vorgemerkt (kein Kauf, nicht frei)

| ID | Karte | Anzahl | frei in der Sammlung |
|---|---|---|---|

## In Moxfield nachziehen / Wartung

| Seit | Was | Aufgabe |
|---|---|---|
| – | derzeit nichts offen | – |
"""
P04 = """# Deckregister

## Commander

| Deckname | Name (einheitlich) | Commander |
|---|---|---|
| Testdeck | Commander \\| Testdeck | Zurgo Stormrender |

## Pflege-Regeln
- …
"""


def projekt(tmp_path):
    q = tmp_path / "quelle"
    for unter in ("claude/sammlung", "claude/decks", "claude/ideen", "claude/tools"):
        (q / unter).mkdir(parents=True)
    shutil.copy(os.path.join(DATEN, "sammlung.csv"), q / "claude/sammlung/basis.csv")
    (q / "claude/sammlung/buchungen.csv").write_text('"Count","Name"\n', encoding="utf-8")
    shutil.copy(os.path.join(DATEN, "testdeck.txt"), q / "claude/decks/testdeck.txt")
    (q / "claude/tools/deck_namen.json").write_text("{}", encoding="utf-8")
    (q / "claude/04_Deckregister.md").write_text(P04, encoding="utf-8")
    (q / "claude/09_Aenderungsprotokoll.md").write_text(P09, encoding="utf-8")
    (q / "claude/10_Geplante-Kaeufe-und-Ideen.md").write_text(P10, encoding="utf-8")
    return q


def test_datenpaket_rundlauf(tmp_path):
    q = projekt(tmp_path)
    ziel = tmp_path / "arbeit"
    ziel.mkdir()
    r = lauf(ziel, "paket.py", "packen", "--art", "daten", "--quelle", str(q), "--out", str(tmp_path / "daten.txt"))
    assert r.returncode == 0, r.stderr
    r = lauf(ziel, "paket.py", "auspacken", str(tmp_path / "daten.txt"), str(tmp_path / "daten-basis.txt"),
             "--ziel", str(ziel))                    # seit V1.9.6: Basis im eigenen Teil
    assert r.returncode == 0, r.stderr
    assert (ziel / "projekt/09_Aenderungsprotokoll.md").exists()
    assert (ziel / "data/basis.csv").exists() and (ziel / "decks/testdeck.txt").exists()
    assert "data/basis.csv" in r.stdout                     # Bau-Befehl nennt die Basis
    # protokoll.py schreibt, paket.py geaendert findet die Datei mit Projektpfad
    r = lauf(ziel, "protokoll.py", "neu", "--typ", "Entscheidung", "--thema", "Testdeck", "--zeile", "Grund: Test")
    assert r.returncode == 0, r.stderr
    r = lauf(ziel, "paket.py", "geaendert", "--ziel", str(ziel))
    assert "claude/09_Aenderungsprotokoll.md" in r.stdout
    r = lauf(ziel, "paket.py", "packen", "--art", "daten", "--arbeit", str(ziel), "--out", str(tmp_path / "d2.txt"))
    assert r.returncode == 0 and "claude/09_Aenderungsprotokoll.md" in open(tmp_path / "d2.txt", encoding="utf-8").read()


def test_protokoll(tmp_path):
    (tmp_path / "projekt").mkdir()
    (tmp_path / "projekt/09_Aenderungsprotokoll.md").write_text(P09, encoding="utf-8")
    (tmp_path / "projekt/10_Geplante-Kaeufe-und-Ideen.md").write_text(P10, encoding="utf-8")
    (tmp_path / "projekt/04_Deckregister.md").write_text(P04, encoding="utf-8")
    r = lauf(tmp_path, "protokoll.py", "neu", "--typ", "Deck geändert", "--thema", "Testdeck",
             "--zeile", "raus (1): A / rein (1): B", "--zeile", "Status: umgesetzt", "--datum", "2026-10-29")
    assert r.returncode == 0, r.stderr
    r = lauf(tmp_path, "protokoll.py", "zeigen", "--deck", "Testdeck")
    assert r.stdout.index("2026-10-29") < r.stdout.index("2026-10-01")     # neueste zuerst
    r = lauf(tmp_path, "protokoll.py", "neu", "--typ", "Werkzeug", "--thema", "x", "--zeile", "y")
    assert r.returncode != 0                                               # 09a fehlt – nur Admin
    r = lauf(tmp_path, "protokoll.py", "idee-neu", "--deck", "Testdeck", "--inhalt", "mehr Ramp", "--status",
             "wartet auf Freigabe")
    assert "I-002" in r.stdout
    assert lauf(tmp_path, "protokoll.py", "idee-status", "I-002", "freigegeben – Aufbau offen").returncode == 0
    r = lauf(tmp_path, "protokoll.py", "offen", "--deck", "Testdeck")
    assert "freigegeben – Aufbau offen" in r.stdout and "Plains" in r.stdout
    assert lauf(tmp_path, "protokoll.py", "idee-entfernen", "I-001").returncode == 0
    text = (tmp_path / "projekt/10_Geplante-Kaeufe-und-Ideen.md").read_text(encoding="utf-8")
    assert "I-001" not in text and "I-002" in text
    assert lauf(tmp_path, "protokoll.py", "nachziehen", "--was", "Deck Testdeck", "--aufgabe", "TXT importieren").returncode == 0
    assert "derzeit nichts offen" not in (tmp_path / "projekt/10_Geplante-Kaeufe-und-Ideen.md").read_text(encoding="utf-8")
    assert lauf(tmp_path, "protokoll.py", "nachziehen-erledigt", "Deck Testdeck").returncode == 0
    assert "derzeit nichts offen" in (tmp_path / "projekt/10_Geplante-Kaeufe-und-Ideen.md").read_text(encoding="utf-8")
    r = lauf(tmp_path, "protokoll.py", "register", "--deck", "Testdeck")
    assert "Zurgo Stormrender" in r.stdout


def test_aufwand_messen_und_summe(tmp_path):
    """Aufwand aus einem Transkript: Token je Art, API-Gegenwert, aktive Zeit ohne lange Lücken; Summenzeile in 14."""
    import json
    import protokoll as P
    f = tmp_path / "s.jsonl"
    zeilen = []
    for ts, model in (("2026-10-29T10:00:00Z", "claude-opus-5-5"), ("2026-10-29T10:20:00Z", "claude-sonnet-5-5"),
                      ("2026-10-29T12:00:00Z", "claude-opus-5-5")):
        zeilen.append(json.dumps({"type": "assistant", "timestamp": ts, "message": {"model": model, "usage": {
            "input_tokens": 1000, "output_tokens": 1000, "cache_read_input_tokens": 1_000_000,
            "cache_creation_input_tokens": 0}}}))
    f.write_text("\n".join(zeilen))
    r = P.aufwand_messen([str(f)])
    assert r["minuten"] == 20                       # Lücke 10:20 → 12:00 zählt nicht
    assert r["token"]["cache_lesen"] == 3_000_000 and r["usd"] > 0
    text = ("| Datum | Was | Zeit | Token | API-Gegenwert | Quelle |\n|---|---|---|---|---|---|\n"
            "| 25.10.2026 | a | – | – | – | nicht gemessen |\n| 29.10.2026 | b | 1,5 h | 200,0 Mio. | 80 € | gemessen |\n"
            "\n**Summe:** alt\n")
    s = P.summen_setzen(text)
    assert "2 Arbeitstage seit 25.10.2026 · gemessen 1,5 h · 200 Mio. Token · ≈ 80 €" in s


def test_datenpaket_teile(tmp_path):
    """V1.9.6: Basis in Teilen, Datenpaket in Teilen „haupt“/„basis“ ≤ GRENZE; unveränderte Teile nicht neu."""
    import paket
    q = projekt(tmp_path)
    r = lauf(tmp_path, "mtg_db.py", "basis-teilen", "--out", str(q / "claude/sammlung"))
    assert r.returncode == 0, r.stderr
    teile = sorted(p.name for p in (q / "claude/sammlung").glob("basis*.csv"))
    assert "basis.csv" not in teile and teile and all(t.startswith("basis-") for t in teile)
    (q / "claude/ideen/gross.txt").write_text(os.urandom(45000).hex(), encoding="utf-8")   # erzwingt Folgeteile
    pk = tmp_path / "pk"
    pk.mkdir()
    r = lauf(tmp_path, "paket.py", "packen", "--art", "daten", "--quelle", str(q), "--out", str(pk / "datenpaket.txt"))
    assert r.returncode == 0, r.stderr
    dateien = sorted(p.name for p in pk.iterdir())
    assert {"datenpaket.txt", "datenpaket-2.txt", "datenpaket-basis.txt"} <= set(dateien), dateien
    assert all(os.path.getsize(pk / d) <= paket.GRENZE for d in dateien)
    ziel = tmp_path / "arbeit"
    ziel.mkdir()
    r = lauf(ziel, "paket.py", "auspacken", *[str(pk / d) for d in dateien], "--ziel", str(ziel))
    assert r.returncode == 0, r.stderr
    assert (ziel / "ideen/gross.txt").exists() and (ziel / f"data/{teile[0]}").exists()
    assert f"data/{teile[0]}" in r.stdout and "data/buchungen.csv" in r.stdout          # Bau-Befehl mit allen Teilen
    # Teil fehlt -> klare Meldung
    r = lauf(ziel, "paket.py", "auspacken", str(pk / "datenpaket.txt"), str(pk / "datenpaket-basis.txt"),
             "--ziel", str(tmp_path / "x"))
    assert r.returncode != 0 and "unvollständig" in r.stderr
    # nur 09 geändert: Teil basis unverändert, haupt neu; großer Entwurf weg -> Folgeteil überzählig
    (ziel / "ideen/gross.txt").unlink()
    assert lauf(ziel, "protokoll.py", "neu", "--typ", "Entscheidung", "--thema", "Testdeck",
                "--zeile", "Grund: Test").returncode == 0
    r = lauf(ziel, "paket.py", "packen", "--art", "daten", "--arbeit", str(ziel), "--out", str(pk / "datenpaket.txt"))
    assert r.returncode == 0, r.stderr
    assert "unverändert  claude/pakete/datenpaket-basis.txt" in r.stdout
    assert "neu          claude/pakete/datenpaket.txt" in r.stdout and "überzählig" in r.stdout
    assert not (pk / "datenpaket-2.txt").exists()
    # neue Basis-Datei im Arbeitsordner wird als neu gemeldet
    (ziel / "data/basis-zz.csv").write_text((ziel / f"data/{teile[0]}").read_text(encoding="utf-8"), encoding="utf-8")
    r = lauf(ziel, "paket.py", "geaendert", "--ziel", str(ziel))
    assert "claude/sammlung/basis-zz.csv" in r.stdout


def test_moxfield_export_basis_teile(arbeit):
    """moxfield-export liest alle Basis-Teile (Standard data/basis*.csv) – Summe wie aus einer Datei."""
    import csv as _csv
    r = lauf(arbeit, "mtg_db.py", "basis-teilen", os.path.join(DATEN, "sammlung.csv"), "--out", str(arbeit / "bt"))
    assert r.returncode == 0, r.stderr
    from mtg_db import netto_bestand
    ein, _ = netto_bestand([os.path.join(DATEN, "sammlung.csv")], str(arbeit / "fehlt.csv"))
    aus, _ = netto_bestand(sorted(str(p) for p in (arbeit / "bt").glob("basis*.csv")), str(arbeit / "fehlt.csv"))
    assert sum(int(r["Count"]) for r in ein) == sum(int(r["Count"]) for r in aus) > 0
