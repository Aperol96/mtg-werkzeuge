"""Konsistenz-Simulation: reproduzierbar, Mulligan-Regeln (CR 103.5, 103.5c), Grenzfälle."""
import os

import simulation as S


def land(name="Plains", farben=("W",), getappt=False):
    return {"name": name, "mv": 0, "gen": 0, "pips": {}, "art": "land", "farben": set(farben), "getappt": getappt}


def zauber(name, mv, pips=None):
    pips = pips or {}
    return {"name": name, "mv": mv, "gen": mv - sum(pips.values()), "pips": pips, "art": "zauber"}


def test_manakosten():
    gen, pips, mv = S.manakosten("{2}{W}{B}")
    assert gen == 2 and pips == {"W": 1, "B": 1} and mv == 4


def test_bezahlen_mit_farben():
    quellen = [{"W"}, {"B"}, {"W", "B"}]
    assert S.kann_zahlen(1, {"W": 1, "B": 1}, quellen)
    assert not S.kann_zahlen(0, {"R": 1}, quellen)


def test_mulligan_regel():
    hand = [land()] * 3 + [zauber("x", 3)] * 4
    assert S.behalten(hand, 0)
    assert not S.behalten([land()] * 1 + [zauber("x", 3)] * 6, 0)
    assert not S.behalten([land()] * 7, 0)
    assert S.behalten([land()] * 1 + [zauber("x", 3)] * 6, 3)          # nach drei Mulligans wird behalten


def test_reproduzierbar_und_grenzfaelle():
    deck = [land() for _ in range(37)] + [zauber(f"z{i}", 3, {"W": 1}) for i in range(62)]
    cmd = zauber("Commander", 4, {"W": 1})
    a = S.simuliere(deck, cmd, n=2000, seed=7)
    b = S.simuliere(deck, cmd, n=2000, seed=7)
    assert a == b
    assert a["landdrops_bis_4"] > 0.7 and a["farbproblem"] == 0
    ohne = S.simuliere([zauber(f"z{i}", 3) for i in range(99)], cmd, n=500, seed=1)
    assert ohne["fehlstart"] == 1.0


def test_aus_deck(con):
    deck, cmd, namen = S.aus_deck(con, os.path.join("decks", "testdeck.txt"))
    assert len(deck) == 99 and cmd["name"] == "Zurgo Stormrender"
    k = S.simuliere(deck, cmd, n=1000, seed=1)
    assert 0.5 < k["landdrops_bis_4"] <= 1
    assert all(len(z) == 4 for z in S.bewerte(k))
