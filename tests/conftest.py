"""Gemeinsame Test-Umgebung: ein Arbeitsordner mit Testbestand, Testdeck und kleinen Scryfall-/EDHREC-Daten.

Läuft ohne Netz (MTG_OFFLINE=1): Commander Spellbook und EDHREC werden nicht erreicht, die Werkzeuge melden das
laut und rechnen mit Zwischenspeicher bzw. Oracle-Bezug weiter. Test-Daten neu bauen: tests/fixture_bauen.py.
"""
import json
import os
import shutil
import subprocess
import sys
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WERKZEUGE = os.path.join(REPO, "werkzeuge") if os.path.exists(os.path.join(REPO, "werkzeuge", "mtg_db.py")) else REPO
DATEN = os.path.join(REPO, "tests", "daten")
sys.path.insert(0, WERKZEUGE)


def frisch(pfad):
    """Zwischenspeicher gelten nur 20–72 h – Test-Daten bekommen das aktuelle Datum."""
    jetzt = time.time()
    for root, _, files in os.walk(pfad):
        for f in files:
            os.utime(os.path.join(root, f), (jetzt, jetzt))


def lauf(ordner, werkzeug, *argumente):
    env = dict(os.environ, MTG_OFFLINE="1", PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, os.path.join(WERKZEUGE, werkzeug), *argumente], cwd=ordner, env=env,
                          capture_output=True, text=True, timeout=600)


@pytest.fixture(scope="session")
def arbeit(tmp_path_factory):
    d = tmp_path_factory.mktemp("mtg")
    shutil.copytree(os.path.join(DATEN, "bulk"), d / "bulk")
    shutil.copytree(os.path.join(DATEN, "edhrec"), d / "cache" / "edhrec")
    (d / "decks").mkdir()
    shutil.copy(os.path.join(DATEN, "testdeck.txt"), d / "decks" / "testdeck.txt")
    shutil.copy(os.path.join(DATEN, "sammlung.csv"), d / "sammlung.csv")
    json.dump({"deck:testdeck": {"name": "Testdeck", "strategie": "Aggro Tokens", "herkunft": "Test"}},
              open(d / "deck_namen.json", "w", encoding="utf-8"))
    frisch(d)
    r = lauf(d, "mtg_db.py", "build", "--sammlung", "sammlung.csv", "--decks", "decks/testdeck.txt",
             "--config", "deck_namen.json", "--vormerkungen", "keine.csv")
    assert r.returncode == 0, r.stdout + r.stderr
    return d


@pytest.fixture(scope="session")
def con(arbeit):
    import sqlite3
    alt = os.getcwd()
    os.chdir(arbeit)
    os.environ["MTG_OFFLINE"] = "1"
    c = sqlite3.connect(os.path.join(arbeit, "mtg.sqlite"))
    yield c
    c.close()
    os.chdir(alt)
