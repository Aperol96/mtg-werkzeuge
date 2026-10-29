"""Regeln aus bewertung.py an echten Karten (Oracle-Text und Scryfall-Tags aus den Test-Daten)."""
import bewertung as B
import deckbau as D


def karte(con, name):
    c = D.finde(con, name)
    return D.sicht(con, c)


def test_ramp_regeln(con):
    assert "ramp" in B.rollen(karte(con, "Sol Ring"))
    assert "ramp" in B.rollen(karte(con, "Wood Elves"))
    assert "ramp" in B.rollen(karte(con, "Cultivate"))
    assert "ramp" in B.rollen(karte(con, "Explore"))              # zusätzliches Land = Ramp
    r, h = B.rollen_detail(karte(con, "Path to Exile"))
    assert "ramp" not in r and "Gegner" in h["ramp"]               # gibt dem Gegner ein Land
    r, h = B.rollen_detail(karte(con, "Dark Ritual"))
    assert "ramp" not in r                                         # Ritual zählt nicht
    r, h = B.rollen_detail(karte(con, "Collective Voyage"))
    assert "ramp" not in r                                         # symmetrisch
    r, h = B.rollen_detail(karte(con, "Flamebraider"))
    assert "ramp" not in r and "Elemental" in h["ramp"]            # Mana nur für Elementare …
    assert "ramp" in B.rollen(karte(con, "Flamebraider"), frozenset({"Elemental"}))   # … außer im Elementar-Deck


def test_landsuche_ist_kein_tutor(con):
    r, h = B.rollen_detail(karte(con, "Wood Elves"))
    assert "tutor" not in r and "Länder" in h["tutor"]
    assert "tutor" in B.rollen(karte(con, "Demonic Tutor"))


def test_removal_nur_gegen_spieler_zaehlt_nicht(con):
    assert "gezielt" in B.rollen(karte(con, "Swords to Plowshares"))
    assert "gezielt" in B.rollen(karte(con, "Lightning Bolt"))


def test_eigene_wipes_im_go_wide_deck(con):
    farewell = karte(con, "Farewell")
    assert B.zerstoert_plan(karte(con, "Wrath of God"), "tokens")
    assert not B.zerstoert_plan(karte(con, "Wrath of God"), "kontrolle")
    assert not B.zerstoert_plan(karte(con, "Hour of Reckoning"), "tokens")   # verschont Tokens
    assert "massen" in B.rollen(farewell)


def test_wert_unbekannt_ist_nicht_schwach():
    assert B.wert_edhrec({}) is None                                # nicht auf der Seite = unbekannt
    w, q = B.gesamtwert(None, 1.0, 500)
    assert q == "≈ Bezug" and w > 0.6
    w, q = B.gesamtwert(0.9, 0.2, 500)
    assert q == "EDHREC" and w == 0.9


def test_synergie_profil(con):
    zurgo = karte(con, "Zurgo Stormrender")
    prof = B.commander_profil([zurgo], D.kreaturtypen(con))
    assert {"tokens", "tod", "angriff"} <= set(prof["themen"])
    assert prof["typen"].get("Warrior") == 1.0
    p, gruende = B.karte_bezug(prof, karte(con, "Mindblade Render"))
    assert B.bezug_norm(p) >= B.BEZUG_SPERRE and "Warrior-Bezug" in gruende
    p, _ = B.karte_bezug(prof, karte(con, "Intangible Virtue"))
    assert B.bezug_norm(p) >= B.BEZUG_SPERRE
    p, _ = B.karte_bezug(prof, karte(con, "Mind Stone"))
    assert p == 0


def test_richtwerte_archetyp_vor_template():
    daten = {"archetypen": {"tokens": {"rollen": {"rolle.ramp": {"median": 11.0}, "rolle.massen": {"median": 0.5}}}}}
    r = B.richtwerte("tokens", daten)
    assert r["ramp"][:2] == (11, 13) and r["ramp"][2] == "Archetyp tokens"
    assert r["massen"][0] == 1                                      # mindestens 1
    assert r["ka"][2] == "Template"


def test_kompromiss_und_klassen(con):
    stufe, q = B.kompromiss_stufe(0.6, 1.0, 0.6)
    assert stufe == "gleichwertig"
    stufe, q = B.kompromiss_stufe(0.5, 0.8, 1.0)
    assert stufe == "funktional, aber langsamer"
    stufe, q = B.kompromiss_stufe(0.0, 0.4, 1.0)
    assert stufe == "nur Platzhalter"
    assert B.klasse(5, 30) == "A"
    assert B.klasse(2, 8) == "D"
    assert B.klasse(3, 1) == "B"
    assert B.klasse(3, 9) == "C"
    assert B.klasse(5, 1, gc_zuviel=True) == "D"
    assert B.funktionsgrad(karte(con, "Mind Stone"), "ramp") == 1.0
    assert B.funktionsgrad(karte(con, "Cultivate"), "ramp") <= 0.8                # Sorcery-Tempo
