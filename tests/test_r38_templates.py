"""Round 38, item 5: ready-made template terminology — TWO distinct
cases (owner correction, 2026-11-21), kept separate:

CASE A — POOR PROGNOSIS (سوء إنذار). The owner reported a template
using "bad o'dour" for سوء إنذار and asked if that reference is
correct; it is NOT ("bad odour" = a bad smell, رائحة كريهة — nothing
to do with prognosis). An exhaustive search of ALL seed data found
NO seed template using "odour" wording for prognosis: the only
prognosis seed (the note pair below) already reads EN "poor
prognosis" / AR "سوء إنذار السن" and is pinned unchanged here. The
wording the owner saw therefore lives in his local DB's stored
phrases, which this round deliberately does NOT migrate (seeds
only) — Restore built-in templates cannot rewrite it either, since
no seed ever contained it.

CASE B — HALITOSIS (bad breath). The genuine bad-breath seeds
(AR pairs: رائحة فم كريهة) carried the lay term "Bad breath"; the
owner's standing ask is standard medical terms in ready-made
templates, so they were upgraded (spelling "odour" is correct):

  phrases_seed.json  complaint EN  "Bad breath" -> "Halitosis (bad odour)"
  specialties.json   General complaint EN    "Bad breath" -> "Halitosis (bad odour)"
  specialties.json   Periodontics complaint EN "Bad breath" -> "Halitosis (bad odour)"
  specialties.json   Pediatric symptoms EN   "Bad breath in child" -> "Halitosis in child"

Plus one clearly nonstandard AR term found in the conservative
pass: specialties.json Endodontics diagnosis AR "تموت اللب" ->
"نخر اللب" (EN pair "Pulp necrosis"). No other clear misspellings
(British spellings — Anaemia, anaesthetic, counselling — are
correct and stay). Seeds only: existing DBs keep their stored
copies; new installs + Restore built-in templates pick up case B."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "src" / "data"


def _texts():
    phrases = json.loads((DATA / "phrases_seed.json").read_text(encoding="utf-8"))
    specs = json.loads((DATA / "specialties.json").read_text(encoding="utf-8"))
    flat = [x for rows in phrases.values() for x in rows]
    for sp in specs["specialties"]:
        for rows in sp["phrases"].values():
            for pair in rows:
                flat += [pair["en"], pair["ar"]]
    return flat


def test_no_bad_breath_seed_remains():
    flat = _texts()
    assert not any("Bad breath" in x for x in flat), \
        [x for x in flat if "Bad breath" in x]
    # The misspelling itself (apostrophe form) appears nowhere.
    assert not any("o'dour" in x.lower() for x in flat)


def test_prognosis_seed_is_correct_and_untouched():
    """Case A: the only prognosis seed already says 'poor prognosis'
    / 'سوء إنذار' — and no seed pairs prognosis with odour wording."""
    phrases = json.loads((DATA / "phrases_seed.json").read_text(encoding="utf-8"))
    notes = phrases["note"]
    assert any("poor prognosis" in x for x in notes)
    assert any("سوء إنذار" in x for x in notes)
    flat = _texts()
    assert not any("prognosis" in x.lower() and "odour" in x.lower()
                   for x in flat)


def test_halitosis_is_the_standard_term():
    flat = _texts()
    assert flat.count("Halitosis (bad odour)") == 3  # phrases + general + perio
    assert "Halitosis in child" in flat
    assert "Halitosis" in flat  # periodontics symptoms: already standard


def test_arabic_necrosis_term_fixed():
    flat = _texts()
    assert "نخر اللب" in flat and "تموت اللب" not in flat
    assert "رائحة فم كريهة" in flat  # AR halitosis pair was already standard


def test_seed_counts_unchanged():
    """Terminology only: no template added or dropped."""
    phrases = json.loads((DATA / "phrases_seed.json").read_text(encoding="utf-8"))
    assert {k: len(v) for k, v in phrases.items()} == {
        "complaint": 21, "symptom": 18, "diagnosis": 20, "procedure": 19,
        "service": 17, "note": 20, "disease": 34, "referral": 14,
        "allergy": 24}
    specs = json.loads((DATA / "specialties.json").read_text(encoding="utf-8"))
    assert len(specs["specialties"]) == 8
    for sp in specs["specialties"]:
        assert sum(len(v) for v in sp["phrases"].values()) == 25
