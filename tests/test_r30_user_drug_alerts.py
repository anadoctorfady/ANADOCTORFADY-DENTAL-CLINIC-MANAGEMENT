"""Round 30 item 3 (Worker C): user-added drugs + the alert engines.

Pre-fix fact (verified from code by the coordinator): the Add New
Drug dialog never collected the pharmacological CLASS, so
add_user_medication stored class="" and ALL THREE class-keyed
engines (drug-drug interactions, drug-disease cautions, relation-
based allergy matching) silently skipped user drugs. This module
proves, against the REAL engines:
  1. user Penicillin-class drug + penicillin allergy -> SEVERE
  2. user NSAID-class drug + kidney disease SEVERE / hypertension
     MODERATE (the round-28 canonical cases, via a user drug)
  3. user Macrolide-class drug vs a seed Statin med -> pair fires
  4. REVERSE: user Statin-class drug in the patient's meds vs a
     prescribed seed Macrolide -> pair fires
  5. user drug with class="" -> NO class-based alert in any
     engine, while an exact-name allergy match still fires
plus: get_medication() returns the user drug WITH its class (the
merge claim, asserted not assumed) and the class-token source /
category ordering. The GUI half (dialog picker behaviour, Rx
alert-area lines) lives in tests/test_r30_user_drug_gui.py.

User drugs live in src/data/user_medications.json (NOT the data
dir), so every test uses unique R30T_ names and removes them in
`finally`; the interaction engines' class caches are reset after
each add/remove so in-process lookups see the current store."""
import tkinter as tk

from src.models import interactions
from src.models.interactions import check_interactions, CLASSES
from src.models.drug_diseases import check_drug_diseases
from src.utils import medications
from src.utils.medications import (add_user_medication,
    remove_user_medication, get_medication, list_medications)
from src.utils.drug_classes import (class_tokens,
    ordered_class_tokens, classes_for_category,
    is_unclassified_user_drug)

PEN, NSAID_U, MACRO, STAT, NONE = ("R30T_PenDrug", "R30T_NsaidDrug",
    "R30T_MacroDrug", "R30T_StatDrug", "R30T_NoClassDrug")
ALL = (PEN, NSAID_U, MACRO, STAT, NONE)


def _fresh():
    medications._CACHE = None
    interactions._CLASS_CACHE = None
    interactions._NAMED_CACHE = None


def _cleanup():
    for n in ALL:
        remove_user_medication(n)
    _fresh()


def _seed_user_drugs():
    _cleanup()
    specs = [(PEN, "Antibiotic", "Penicillin"),
             (NSAID_U, "NSAID", "NSAID"),
             (MACRO, "Antibiotic", "Macrolide"),
             (STAT, "Statin", "Statin"),
             (NONE, "Other", "")]
    for name, cat, cls in specs:
        ok, msg = add_user_medication({"generic_en": name,
            "category": cat, "class": cls, "form": "Tablet",
            "strength": "10 mg"})
        assert ok, (name, msg)
    _fresh()


def test_get_medication_merges_user_drug_with_class():
    _seed_user_drugs()
    try:
        med = get_medication(PEN)
        assert med is not None, "user drug missing from merged list"
        assert med["class"] == "Penicillin", med
        assert med["category"] == "Antibiotic", med
        assert any(m["generic_en"] == MACRO and m["class"] == "Macrolide"
                   for m in list_medications())
        assert get_medication(NONE)["class"] == ""
        assert is_unclassified_user_drug(NONE) is True
        assert is_unclassified_user_drug(PEN) is False
        assert is_unclassified_user_drug("Amoxicillin") is False
    finally:
        _cleanup()
    assert get_medication(PEN) is None


def test_case1_user_penicillin_class_fires_allergy_severe():
    _seed_user_drugs()
    try:
        for allergen in ("Penicillin", "Penicillin allergy"):
            a = check_interactions(PEN, [], [allergen], [])
            assert a and a[0]["severity"] == "severe", (allergen, a)
        # An unrelated allergy stays silent for the same drug.
        assert check_interactions(PEN, [], ["Latex allergy"], []) == []
    finally:
        _cleanup()


def test_case2_user_nsaid_class_fires_disease_alerts():
    _seed_user_drugs()
    try:
        renal = check_drug_diseases(NSAID_U, "Kidney disease")
        assert renal and renal[0]["severity"] == "severe", renal
        assert "Kidney disease" in renal[0]["message_en"]
        htn = check_drug_diseases(NSAID_U, "Hypertension")
        assert htn and htn[0]["severity"] == "moderate", htn
        ar = check_drug_diseases(NSAID_U, "أمراض الكلى")
        assert ar and ar[0]["severity"] == "severe", ar
    finally:
        _cleanup()


def test_case3_user_macrolide_vs_seed_statin_med():
    _seed_user_drugs()
    try:
        a = check_interactions(MACRO, ["Atorvastatin"], [], [])
        assert a and any(x["severity"] == "severe" for x in a), a
        assert any("Macrolide" in x["message_en"] for x in a), a
    finally:
        _cleanup()


def test_case4_seed_macrolide_vs_user_statin_med():
    _seed_user_drugs()
    try:
        a = check_interactions("Clarithromycin", [STAT], [], [])
        assert a and any(x["severity"] == "severe" for x in a), a
        assert any("Macrolide" in x["message_en"] for x in a), a
    finally:
        _cleanup()


def test_case5_unclassified_user_drug_no_class_alerts():
    _seed_user_drugs()
    try:
        # Drug-drug + allergy dimensions: nothing class-based fires
        # (Warfarin pairs with NSAIDs/antibiotics by class; a
        # penicillin allergy covers the Penicillin class).
        assert check_interactions(NONE, ["Warfarin"],
                                  ["Penicillin"], []) == []
        # Disease dimension: the NSAID canonical diseases stay silent.
        assert check_drug_diseases(
            NONE, "Kidney disease, Hypertension") == []
        # ...but an EXACT-NAME allergy match still fires.
        a = check_interactions(NONE, [], [f"{NONE} allergy"], [])
        assert a and a[0]["severity"] == "severe", a
    finally:
        _cleanup()


def test_class_token_source_and_category_ordering():
    toks = class_tokens()
    data_toks = {m["class"] for m in list_medications() if m["class"]}
    assert set(toks) == data_toks | set(CLASSES.keys())
    assert "Penicillin" in toks and "NSAID" in toks
    assert "Macrolide" in toks and toks == sorted(toks)
    # Category mapping exists in the data and drives the ordering:
    abx = classes_for_category("Antibiotic")
    assert {"Penicillin", "Macrolide", "Cephalosporin"} <= abx
    ordered = ordered_class_tokens("Antibiotic")
    assert set(ordered) == set(toks)
    assert ordered[:len(abx)] == sorted(abx), ordered[:6]
    assert ordered_class_tokens(None) == toks


def test_allergy_caches_invalidate_on_add_remove():
    """Regression (coordinator, R30): the allergy engine snapshots
    the drug list in _CLASS_CACHE/_NAMED_CACHE. A drug added
    MID-SESSION — after an earlier check built the snapshots — was
    invisible to allergy class matching until the next launch.
    add/remove_user_medication must drop the snapshots at write
    time; this test deliberately never resets them by hand between
    the add and the check (the state that exposed the bug)."""
    name = "R30T_CacheDrug"
    remove_user_medication(name)
    interactions._CLASS_CACHE = None; interactions._NAMED_CACHE = None
    try:
        interactions._drug_class_tokens("Aspirin")
        interactions._named_classes("aspirin")
        assert interactions._CLASS_CACHE is not None
        ok, msg = add_user_medication({"generic_en": name,
            "category": "Antibiotic", "class": "Penicillin",
            "form": "Tablet", "strength": "10 mg"})
        assert ok, msg
        assert interactions._CLASS_CACHE is None  # dropped at write
        a = check_interactions(name, [], ["Penicillin"], [])
        assert a and a[0]["severity"] == "severe", a
        remove_user_medication(name)
        assert check_interactions(name, [], ["Penicillin"], []) == []
    finally:
        remove_user_medication(name)
        _fresh()


