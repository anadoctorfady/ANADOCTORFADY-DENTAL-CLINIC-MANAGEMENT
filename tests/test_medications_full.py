"""All-drug list (300+) by scientific name + class-level interactions."""
import json
from pathlib import Path
from src.utils.medications import search_medications, list_medications, list_by_category
from src.models.interactions import check_interactions
def test_count_all_classes():
    meds = list_medications()
    # R19-C audit pin: exactly 315 seed drugs (311 audited + 4 added);
    # any future add/remove must update this pin deliberately.
    assert len(meds) == 315, len(meds)
    cats = {m["category"] for m in meds}
    for c in ["Antibiotic", "Cardiovascular", "Diabetes", "Respiratory", "CNS", "GI"]:
        assert c in cats, c
    assert all(m.get("generic_en") and m.get("class") for m in meds)
def test_search_scientific_first():
    assert any(m["generic_en"] == "Atorvastatin" for m in search_medications("Atorvastatin"))
    assert any(m["generic_en"] == "Salbutamol" for m in search_medications("Salbutamol"))
    assert any(m["generic_en"] == "Sertraline" for m in search_medications("Sertraline"))
    assert any(m["generic_en"] == "Empagliflozin" for m in search_medications("Empagliflozin"))
    assert len(list_by_category("Cardiovascular")) >= 30
def test_interactions_count():
    data = json.loads((Path(__file__).resolve().parent.parent / "src" / "data" / "interactions.json").read_text(encoding="utf-8"))
    assert len(data) >= 120, len(data)
def test_class_interactions_non_dental():
    a = check_interactions("Clarithromycin", ["Atorvastatin"], [], [])
    assert a and a[0]["severity"] == "severe"  # Statin + Macrolide
    a = check_interactions("Sertraline", ["Tramadol"], [], [])
    assert a and a[0]["severity"] == "severe"  # SSRI + Tramadol
    a = check_interactions("Diclofenac", ["Warfarin"], [], [])
    assert a and a[0]["severity"] == "severe"  # Anticoagulant + NSAID
    a = check_interactions("Ibuprofen", ["Apixaban"], [], [])
    assert a and a[0]["severity"] == "severe"  # any DOAC + any NSAID
    a = check_interactions("Metoprolol", ["Verapamil"], [], [])
    assert a and a[0]["severity"] == "severe"  # BetaBlocker + CCB
def test_r19_audit_coherence_and_additions():
    meds = list_medications()
    by_name = {m["generic_en"]: m for m in meds}
    # Added in R19-C: both diclofenac salts + two dental local
    # anaesthetics that were missing (prilocaine, topical benzocaine).
    for name in ["Diclofenac Potassium", "Diclofenac Sodium",
                 "Prilocaine", "Benzocaine"]:
        assert name in by_name, name
    assert by_name["Diclofenac Potassium"]["category"] == "NSAID"
    assert by_name["Diclofenac Sodium"]["class"] == "NSAID"
    assert by_name["Prilocaine"]["category"] == "Local anaesthetic"
    # The previously-missing classics exist as base entries.
    for name in ["Ibuprofen", "Naproxen", "Ketorolac", "Paracetamol"]:
        assert name in by_name, name
    assert by_name["Paracetamol"]["category"] == "Analgesic"
    # Coherence: every NSAID-class drug sits in the NSAID category,
    # and the merged duplicate buckets are gone.
    assert all(m["category"] == "NSAID" for m in meds
               if m.get("class") == "NSAID")
    cats = {m["category"] for m in meds}
    for gone in ["Antidiabetic", "Antihypertensive", "Sedative",
                 "Antiplatelet / NSAID"]:
        assert gone not in cats, gone
    # Class-named categories hold all their class members.
    for cls, cat in [("Statin", "Statin"), ("PPI", "PPI"),
                     ("Anticoagulant", "Anticoagulant"),
                     ("Antiplatelet", "Antiplatelet"),
                     ("Diuretic", "Diuretic"),
                     ("Antihistamine", "Antihistamine"),
                     ("Antiepileptic", "Antiepileptic")]:
        assert all(m["category"] == cat for m in meds
                   if m.get("class") == cls), cls
    # New NSAID salts trigger the class-level severe interactions.
    a = check_interactions("Diclofenac Potassium", ["Warfarin"], [], [])
    assert a and a[0]["severity"] == "severe"
    a = check_interactions("Diclofenac Sodium", ["Apixaban"], [], [])
    assert a and a[0]["severity"] == "severe"
def test_safe_still_safe():
    assert check_interactions("Paracetamol", ["Amlodipine"], [], []) == []
    assert check_interactions("Salbutamol", ["Amlodipine"], [], []) == []
