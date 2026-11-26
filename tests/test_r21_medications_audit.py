"""R21 second-pass medication category audit (worker MEDS, item 1c).

Independent re-check of all 315 seed drugs in src/data/medications.json.
Only clear errors were fixed: the two PDE5 inhibitors stocked under
their erectile-dysfunction brands (Viagra / Cialis) sat in the broad
"Cardiovascular" bucket; they now sit in the precise existing
"Urology" category. Their interaction class ("PDE5") is unchanged, so
the Nitrate + PDE5 severe interaction still fires by class.
Pure file reads: no app imports, no display, no live DB.
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "src" / "data"


def _meds():
    return json.loads((DATA / "medications.json").read_text(encoding="utf-8"))


def test_file_parses_and_count_is_463():  # R49: 315 + 40 singles + 108 combos = 463
    meds = _meds()
    assert isinstance(meds, list)
    assert len(meds) == 463, len(meds)  # R49 count pin (was 315)


def test_no_duplicate_generic_en():
    names = [m["generic_en"] for m in _meds()]
    assert len(names) == len(set(names)), (
        [n for n in set(names) if names.count(n) > 1])


def test_every_entry_has_category_and_class():
    for m in _meds():
        assert m.get("category"), m.get("generic_en")
        assert m.get("class"), m.get("generic_en")


def test_r21_pde5_inhibitors_moved_to_urology():
    by_name = {m["generic_en"]: m for m in _meds()}
    # Stocked brands are the ED brands (Viagra / Cialis), not the
    # pulmonary-hypertension brands (Revatio / Adcirca): the precise
    # existing home is Urology, not the broad Cardiovascular bucket.
    assert by_name["Sildenafil"]["category"] == "Urology"
    assert by_name["Tadalafil"]["category"] == "Urology"
    # Interaction class untouched by the category move.
    assert by_name["Sildenafil"]["class"] == "PDE5"
    assert by_name["Tadalafil"]["class"] == "PDE5"
    # Bucket sizes pin the move (37 - 2 and 5 + 2). R49: the
    # Cardiovascular bucket grew to 68 with the antihypertensive
    # fixed-dose combinations and new cardiovascular singles.
    cats = [m["category"] for m in _meds()]
    assert cats.count("Cardiovascular") == 68
    assert cats.count("Urology") == 7


def test_pde5_interaction_class_still_defined():
    pairs = json.loads((DATA / "interactions.json").read_text(encoding="utf-8"))
    assert any(p["drug_a"] == "Nitrate" and p["drug_b"] == "PDE5"
               and p["severity"] == "severe" for p in pairs)
