"""Befehle der Werkzeuge im Test-Arbeitsordner (ohne Netz). Prüft vor allem die Regeln aus dem Review vom 29.10.2026:
Raus-Sperren im Upgrade, eigene Wipes im Go-wide-Deck, laute EDHREC-Fehler, Abnahme und Gegentest."""
import os
import re

from conftest import lauf


def ok(r):
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    return r.stdout


def test_upgrade_sperren(arbeit):
    out = ok(lauf(arbeit, "deckbau.py", "upgrade", "Testdeck", "--out", "out/upgrade.csv"))
    paare = [z.split("#")[0].strip().split(" -> ") for z in open(os.path.join(arbeit, "out", "upgrade_paare.txt"),
                                                                    encoding="utf-8") if "->" in z.split("#")[0]]
    raus = {p[0] for p in paare}
    rein = {p[1] for p in paare}
    # Commander-Bezug und Kernpaket (Anthems) bleiben im Deck
    for karte in ("Mindblade Render", "Commander's Insignia", "Angel of Invention"):
        assert karte not in raus, f"{karte} darf nicht raus"
    # symmetrische Wipes zerstören den Token-Plan und werden nicht vorgeschlagen
    assert not rein & {"Farewell", "Sunfall", "Shatter the Sky"}
    assert "zerstört den eigenen Plan" in out
    # Hour of Reckoning verschont Tokens – darf vorgeschlagen werden, wird aber nicht als Plan-Zerstörer geführt
    assert "Hour of Reckoning" not in out.split("zerstört den eigenen Plan")[1].split("\n")[0]
    # kurze Ausgabe ist Standard, die CSV ist vollständig
    assert "Schwächste Deckkarten" not in out
    assert sum(1 for _ in open(os.path.join(arbeit, "out", "upgrade.csv"), encoding="utf-8")) > 90
    assert "Raus-Sperren" in out


def test_upgrade_meldet_fehlendes_edhrec_laut(arbeit):
    r = lauf(arbeit, "deckbau.py", "commander", "Pitiless Plunderer")
    assert "EDHREC nicht erreichbar" in r.stderr


def test_thema_als_anzeigename(arbeit):
    """--thema darf ein Anzeigename sein („Lands Matter / Landfall“): daraus werden gültige EDHREC-Slugs, nie eine
    ungültige Adresse (Fund aus dem Gegentest vom 29.10.2026)."""
    import deckbau
    assert deckbau.thema_slugs("Lands Matter / Landfall")[:2] == ["lands-matter", "landfall"]
    assert deckbau.thema_slugs("tokens") == ["tokens"]
    assert deckbau.thema_slugs(None) == []
    assert deckbau.edhrec("commanders/x/Lands Matter / Landfall") is None
    r = lauf(arbeit, "deckbau.py", "upgrade", "Testdeck", "--thema", "Tokens (Go-wide)", "--out", "out/upgrade_thema.csv")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "InvalidURL" not in r.stderr and "Ziel-Archetyp Tokens" in r.stdout


def test_pruefen_und_abnahme(arbeit):
    out = ok(lauf(arbeit, "deckbau.py", "pruefen", "decks/testdeck.txt"))
    assert "Richtwert-Quelle" in out and "Archetyp tokens" in out
    assert "Bracket-Zeile: Bracket 3" in out
    out = ok(lauf(arbeit, "deckbau.py", "abnahme", "Testdeck", "--n", "500"))
    punkte = re.findall(r"^  (✓|✗|offen|–)\s", out, re.M)
    assert len(punkte) == 8
    assert "Urteil:" in out and "Stärke-Index" in out


def test_synergie_findet_karten_ohne_edhrec(arbeit):
    out = ok(lauf(arbeit, "deckbau.py", "synergie", "Testdeck"))
    assert "Venerated Stormsinger" in out
    assert "Profil: Tokens" in out


def test_fazit_mit_abnahme(arbeit):
    entwurf = os.path.join(arbeit, "out", "entwurf.txt")
    zeilen = open(os.path.join(arbeit, "decks", "testdeck.txt"), encoding="utf-8").read().replace(
        "1 Grenzo, Havoc Raiser\n", "1 Venerated Stormsinger\n")
    open(entwurf, "w", encoding="utf-8").write(zeilen)
    ok(lauf(arbeit, "deckbau.py", "fazit", "--neu", "out/entwurf.txt", "--alt", "Testdeck", "--out", "out/fazit.md"))
    md = open(os.path.join(arbeit, "out", "fazit.md"), encoding="utf-8").read()
    assert "| Grenzo, Havoc Raiser |" in md and "Venerated Stormsinger" in md
    assert "## Bracket-3-Abnahme" in md and "Stärke-Index" in md


def test_gegentest(arbeit):
    out = ok(lauf(arbeit, "deckbau.py", "gegentest", "Testdeck", "out/entwurf.txt", "--n", "500",
                  "--namen", "Projekt,Konkurrenz"))
    assert "Überschneidung: 98 gemeinsame Karten" in out or "Überschneidung:" in out
    assert "Stärke-Index" in out
    # drei Listen mit Ausgangsstand: Abwägungsgrundlage (Konsens-Tausche)
    out = ok(lauf(arbeit, "deckbau.py", "gegentest", "out/entwurf.txt", "Testdeck", "out/entwurf.txt",
                  "--basis", "Testdeck", "--n", "300", "--namen", "Projekt,K1,K2"))
    assert "Abwägung gegen den Ausgangsstand" in out and "K2" in out


def test_gegenlauf_konkurrenten():
    """Konkurrenten mit festem Commit, Lizenz und Lesedateien; Auftrag nennt Unabhängigkeit und Methodik-Modus."""
    import deckbau as D
    assert len(D.KONKURRENTEN) == 2
    for k in D.KONKURRENTEN.values():
        assert re.fullmatch(r"[0-9a-f]{40}", k["commit"]) and k["lizenz"] and k["lesen"]
    t = D.GEGENLAUF_AUFTRAG
    assert "NICHT ausgeführt" in t and "Unabhängig" in t and "{key}" in t


def test_weitere_befehle(arbeit):
    ok(lauf(arbeit, "deckbau.py", "passung", "Testdeck"))
    ok(lauf(arbeit, "deckbau.py", "kandidaten", "Zurgo Stormrender", "--weg", "1", "--out", "out/k.csv"))
    ok(lauf(arbeit, "deckbau.py", "verkauf", "--min-preis", "0", "--out", "out/verkauf.txt"))
    out = ok(lauf(arbeit, "deckbau.py", "oracle", "Sol Ring"))
    assert "{T}: Add {C}{C}." in out
    out = ok(lauf(arbeit, "archetypen.py", "deck", "decks/testdeck.txt"))
    assert "Tokens (Go-wide)" in out
    out = ok(lauf(arbeit, "simulation.py", "Testdeck", "--n", "500"))
    assert "Schwellen" in out
    out = ok(lauf(arbeit, "mtg_db.py", "frei", "Sol Ring", "Venerated Stormsinger"))
    assert "Sol Ring" in out


def test_upgrade_durchlauf_und_tragbarkeit(arbeit):
    """Sammlungs-Durchlauf zeigt alle freien Kandidaten je Lücke; untragbare Karten stehen nicht in den Paaren."""
    out = ok(lauf(arbeit, "deckbau.py", "upgrade", "Testdeck", "--out", "out/upgrade2.csv"))
    if "Kernpakete:" in out and "✗" in out.split("Kernpakete:")[1].split("\n")[0]:
        assert "Sammlungs-Durchlauf" in out


def test_bracket_einstufung_und_waechter():
    """Bracket-Wächter (V1.9): Ausgangsbracket aus den harten Grenzen, Warnung nur bei ungewolltem Wechsel."""
    import deckbau as D

    def bz(gc=(), mld=(), xt=(), zwei=(), tag=None):
        return {"gc": list(gc), "mld": list(mld), "xt": list(xt), "zwei": list(zwei), "sb_tag": tag}
    assert D.bracket_einstufung(bz())["stufe"] == 2
    assert D.bracket_einstufung(bz(gc=["Demonic Tutor"]))["stufe"] == 3
    assert D.bracket_einstufung(bz(zwei=["A + B"]))["stufe"] == 3
    assert D.bracket_einstufung(bz(gc=["a", "b", "c", "d"]))["stufe"] == 4
    assert D.bracket_einstufung(bz(mld=["Armageddon"]))["stufe"] == 4
    assert D.bracket_einstufung(bz(xt=["Time Warp"]))["stufe"] == 2          # eine Karte ist noch keine Kette
    assert D.bracket_einstufung(bz(xt=["Time Warp", "Temporal Mastery"]))["stufe"] == 4

    def stand(**k):
        b = bz(**k)
        return {"bz": b, "ein": D.bracket_einstufung(b)}
    # Ziel = Ausgang: neuer Game Changer hebt 2 -> 3 -> Warnung mit Auslöser
    warn, _, ausl = D.bracket_waechter(stand(), stand(gc=["Demonic Tutor"]), 2)
    assert warn and "2 auf 3" in warn[0] and ("Demonic Tutor", "neuer Game Changer", "hoch") in ausl
    # letzter Game Changer geht raus: 3 -> 2 -> Warnung nach unten
    warn, _, _ = D.bracket_waechter(stand(gc=["Demonic Tutor"]), stand(), 3)
    assert warn and "nach unten" in warn[0]
    # neue 2-Karten-Combo im selben Bracket -> Warnung (früh?)
    warn, _, _ = D.bracket_waechter(stand(gc=["X"]), stand(gc=["X"], zwei=["A + B"]), 3)
    assert warn and "2-Karten-Combo" in warn[0]
    # gleiche Combo in anderer Reihenfolge ist nicht neu
    warn, _, _ = D.bracket_waechter(stand(zwei=["A + B"]), stand(zwei=["B + A"]), 3)
    assert not warn
    # Ziel ≠ Ausgang: Umbau aufs Ziel ist gewollt, nur Überschreiten warnt
    warn, hinw, _ = D.bracket_waechter(stand(), stand(gc=["Demonic Tutor"]), 3)
    assert not warn and "gewollter Umbau" in hinw[0]
    warn, _, _ = D.bracket_waechter(stand(), stand(gc=["a", "b", "c", "d"]), 3)
    assert warn and "überschreitet" in warn[0]


def test_bracket_befehl(arbeit):
    out = ok(lauf(arbeit, "deckbau.py", "bracket", "Testdeck"))
    assert "Ausgangsbracket: Bracket" in out
    zeilen = open(os.path.join(arbeit, "decks", "testdeck.txt"), encoding="utf-8").read().splitlines()
    tausch = next(i for i, z in enumerate(zeilen) if z.startswith("1 ") and "Zurgo" not in z and "Plains" not in z
                  and "Mountain" not in z and "Swamp" not in z)
    zeilen[tausch] = "1 Demonic Tutor"
    os.makedirs(os.path.join(arbeit, "out"), exist_ok=True)
    open(os.path.join(arbeit, "out", "bracket_entwurf.txt"), "w", encoding="utf-8").write("\n".join(zeilen) + "\n")
    out = ok(lauf(arbeit, "deckbau.py", "bracket", "Testdeck", "--neu", "out/bracket_entwurf.txt"))
    if "Ausgangsbracket: Bracket 2" in out:
        assert "⚠ Bracket-Wechsel" in out and "Demonic Tutor (neuer Game Changer)" in out
        assert "im Bracket bleiben statt Demonic Tutor" in out and "WARNUNG" in out
    out = ok(lauf(arbeit, "deckbau.py", "bracket", "Testdeck", "--neu", "out/bracket_entwurf.txt", "--ziel", "3",
                  "--ausgang", "2"))
    assert "gewollter Umbau" in out and "hält das Ziel-Bracket ein" in out
