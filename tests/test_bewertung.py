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


def _s(name, text, tags, cmc):
    return B.sicht(name, "Sorcery", text, "", set(tags), cmc)


def test_ramp_funktionsgrad_gegentest():
    """Funde aus dem Gegentest Endless Harvest (29.10.2026): Aktivierungskosten, Wiederholbarkeit, Kampfschaden."""
    font = B.sicht("Font of Fertility", "Enchantment", "{1}{G}, Sacrifice this enchantment: Search your library for a "
                   "basic land card, put it onto the battlefield tapped, then shuffle.", "", {"land-ramp", "ramp"}, 1)
    roamer = _s("Roamer's Routine", "Search your library for a basic land card, put it onto the battlefield tapped, then "
                "shuffle.\nHarmonize {4}{G}", {"land-ramp", "ramp"}, 3)
    cult = _s("Cultivate", "Search your library for up to two basic land cards, reveal those cards, put one onto the "
              "battlefield tapped and the other into your hand, then shuffle.", {"land-ramp"}, 3)
    one = B.sicht("One with Nature", "Enchantment — Aura", "Enchant creature\nWhenever enchanted creature deals combat "
                  "damage to a player, you may search your library for a basic land card, put that card onto the "
                  "battlefield tapped, then shuffle.", "", {"land-ramp"}, 1)
    assert B.aktivierung_mv(font) == 2 and B.aktivierung_mv(cult) == 0
    assert B.wiederholbar(roamer) and not B.wiederholbar(cult)
    assert B.funktionsgrad(roamer, "ramp") > B.funktionsgrad(font, "ramp") == B.funktionsgrad(cult, "ramp")
    assert B.funktionsgrad(one, "ramp") < B.funktionsgrad(cult, "ramp")


def test_nicht_tragbar():
    ctx = {"anteil": {"W": 0.37, "G": 0.63, "U": 0, "B": 0, "R": 0}, "mv": 3.5}
    moon = {"c": {"mana_cost": "{5}{W}{W}{W}", "cmc": 8}}
    hoof = {"c": {"mana_cost": "{5}{G}{G}", "cmc": 7}}
    klein = {"c": {"mana_cost": "{2}{G}", "cmc": 3}}
    assert "WWW" in D.nicht_tragbar(ctx, moon)
    assert D.nicht_tragbar(ctx, hoof) is None                       # GG im Hauptfarbton ist tragbar
    assert "Kurve" in D.nicht_tragbar(ctx, hoof, klein)            # Wert-Tausch 3 → 7 bei hoher Kurve
    assert D.nicht_tragbar(ctx, klein, hoof) is None
