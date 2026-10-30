"""Abhak-Kästchen (V1.8): Tausch-, Verkaufs- und Einkaufs-PDF haben je Karte ein anklickbares Formularfeld."""
import os
import re

import pytest

kb = pytest.importorskip("kartenbilder")


class OhneBilder:
    """Ersatz für kartenbilder.Bilder: ein leeres Kartenbild, kein Netz."""
    gesperrt = False

    def __init__(self, ordner):
        from PIL import Image
        self.bild = os.path.join(ordner, "leer.png")
        Image.new("RGB", (63, 88), (236, 226, 204)).save(self.bild)

    def pfad(self, k, groesse="normal"):
        return self.bild


@pytest.fixture(scope="module")
def umgebung(tmp_path_factory):
    d = tmp_path_factory.mktemp("pdf")
    os.environ["MTG_OFFLINE"] = "1"
    kb.schriften_laden(d / "fonts")
    return d, OhneBilder(str(d))


def felder(pfad):
    roh = open(pfad, "rb").read()
    return re.findall(rb"/T \(erledigt_(\d{3})\)", roh), b"/AcroForm" in roh


def karte(name, **k):
    return dict(dict(anzahl=1, name=name, set="", nummer="", quelle="Sammlung", hinweis="", abschnitt="holen"), **k)


def test_tausch_hat_kaestchen_je_karte(umgebung):
    d, bilder = umgebung
    karten = [karte("Sol Ring"), karte("Fracture", anzahl=2), karte("Plains", anzahl=3, quelle="Standardland",
                                                                    abschnitt="basic"),
              karte("Path to Exile", abschnitt="raus"), karte("Swords to Plowshares", quelle="Kauf", abschnitt="kauf")]
    kb.tausch_pdf({"titel": "Test"}, karten, d / "tausch.pdf", bilder)
    namen, form = felder(d / "tausch.pdf")
    assert form and len(namen) == len(karten) and len(set(namen)) == len(karten)


def test_verkauf_hat_kaestchen_je_karte(umgebung):
    d, bilder = umgebung
    liste = d / "verkauf.txt"
    liste.write_text("# titel: Test\nK1 1 Daze (SOA) 15 | 2,19 € | DE |\nK2 2 Vampiric Tutor | 30,00 € | EN | Game Changer\n",
                     encoding="utf-8")
    kopf, karten = kb.lies_verkaufsliste(liste)
    kb.verkauf_pdf(kopf, karten, d / "verkauf.pdf", bilder)
    namen, form = felder(d / "verkauf.pdf")
    assert form and len(namen) == 3          # 2 Karten + „Bedenken geklärt“ für die Kat.-2-Karte


def test_einkauf_aus_liste_und_aus_10(umgebung):
    d, bilder = umgebung
    liste = d / "einkauf.txt"
    liste.write_text("# titel: Einkauf\n3 Arcane Signet | 0,50 € | I-004 Mardu Surge | günstigster Druck\n"
                     "1 Sol Ring (C21) 263 | 1,20 € | I-003 Endless Harvest |\n", encoding="utf-8")
    kopf, karten = kb.lies_einkaufsliste(liste)
    assert [k["anzahl"] for k in karten] == [3, 1] and karten[0]["zweck"] == "I-004 Mardu Surge"
    kb.einkauf_pdf(kopf, karten, d / "einkauf.pdf", bilder)
    namen, form = felder(d / "einkauf.pdf")
    assert form and len(namen) == 2

    zehn = d / "10.md"
    zehn.write_text("**Stand:** 29.10.2026\n\n## Offene Ideen\n\n| ID | Datum | Deck / Vorhaben | Inhalt | Status | Details |\n"
                    "|---|---|---|---|---|---|\n| I-001 | 26.10.2026 | Boros (Pioneer) | x | wartet | – |\n\n"
                    "## Kaufliste (Sammelbestellung)\n\n| ID | Karte | Anzahl | Art | Preis ab € (Stand) | Hinweis |\n"
                    "|---|---|---|---|---|---|\n| I-001 | Mountain | 11 | Standardland | 0,02 / Stück (25.10.2026) | erst zählen |\n\n"
                    "Summe …\n\n## Aus der Sammlung vorgemerkt\n", encoding="utf-8")
    kopf, karten = kb.einkauf_aus_10(zehn)
    assert len(karten) == 1 and karten[0]["zweck"] == "I-001 Boros (Pioneer)" and karten[0]["preis"] == 0.02
    assert "Standardland" in karten[0]["hinweis"]


def test_verkauf_bedenken_kasten_und_ueberblick(umgebung):
    d, bilder = umgebung
    liste = d / "verkauf_bedenken.txt"
    liste.write_text("# titel: Test\n# bedenken: Preise am Tag des Einstellens prüfen.\n# bedenken: Nur das gelistete Exemplar.\n"
                     "K1 1 Daze (SOA) 15 | 2,19 € | DE |\nK2 1 Vampiric Tutor | 30,00 € | EN | Game Changer mit Platz in zwei Decks\n",
                     encoding="utf-8")
    kopf, karten = kb.lies_verkaufsliste(liste)
    assert kopf["bedenken"] == ["Preise am Tag des Einstellens prüfen.", "Nur das gelistete Exemplar."]
    kb.verkauf_pdf(kopf, karten, d / "verkauf_bedenken.pdf", bilder)
    namen, form = felder(d / "verkauf_bedenken.pdf")
    assert form and len(namen) == 3          # 2 Karten + 1 Kästchen „Bedenken geklärt“ im Überblick
