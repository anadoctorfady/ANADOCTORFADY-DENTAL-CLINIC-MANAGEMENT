"""Round 28 item 3a: the drug-DISEASE alert layer. Coverage:
every one of the 315 drugs has a disease-review outcome (class
rules / drug-specific rule / class reviewed with no major
caution) and every round-19 disease template string (EN+AR)
resolves to a canonical condition. Behaviour: canonical cases
fire in EN and AR patient records, at model level and through
the real PrescriptionsTab._check (merged with the existing
drug-drug + allergy dimensions, severe gates via has_severe)."""
import json
import tkinter as tk
from pathlib import Path
from src.models.drug_diseases import (check_drug_diseases,
    match_conditions, review_outcome, conditions)
from src.models.interactions import check_interactions
from src.utils.medications import list_medications, get_medication

def test_coverage_all_315_reviewed():
    meds = list_medications()
    assert len(meds) == 463, len(meds)  # R49 count pin (was 315)
    outcomes = {}
    for m in meds:
        kind, _key = review_outcome(m["generic_en"])
        assert kind != "unreviewed", m["generic_en"]
        outcomes[kind] = outcomes.get(kind, 0) + 1
    assert sum(outcomes.values()) == 463  # R49 count pin (was 315)
    assert outcomes.get("class", 0) > 200, outcomes  # class-driven

def test_dataset_manifests_complete():
    data = json.loads((Path(__file__).resolve().parent.parent
                       / "src/data/drug_diseases.json").read_text(encoding="utf-8"))
    classes = {m["class"] for m in list_medications()}
    assert set(data["classes_reviewed"]) == classes
    assert set(data["categories_reviewed"]) == {m["category"] for m in list_medications()}
    assert len(data["conditions"]) >= 21
    for r in data["class_rules"] + data["drug_rules"]:
        assert r["severity"] in ("severe", "moderate"), r
        assert r["condition"] in data["conditions"], r
        assert r["note_en"] and r["note_ar"], r

def test_all_disease_templates_resolve():
    seed = json.loads((Path(__file__).resolve().parent.parent
                       / "src/data/phrases_seed.json").read_text(encoding="utf-8"))
    assert len(seed["disease"]) == 34
    for text in seed["disease"]:
        assert match_conditions(text), text

def test_normalizer_variants():
    assert match_conditions("Kidney disease") == {"renal_impairment"}
    assert match_conditions("أمراض الكلى") == {"renal_impairment"}
    assert match_conditions("CKD, on dialysis") == {"renal_impairment"}
    assert match_conditions("داء السكري") == {"diabetes"}
    assert match_conditions(["Hypertension", "Asthma"]) == \
        {"hypertension", "asthma_copd"}
    assert match_conditions("") == set()
    assert match_conditions(None) == set()

def test_canonical_cases_en():
    ibu_renal = check_drug_diseases("Ibuprofen", "Kidney disease")
    assert ibu_renal and ibu_renal[0]["severity"] == "severe"
    assert "Kidney disease" in ibu_renal[0]["message_en"]
    ibu_htn = check_drug_diseases("Ibuprofen", "Hypertension")
    assert ibu_htn and ibu_htn[0]["severity"] == "moderate"
    bb = check_drug_diseases("Atenolol", "Asthma")
    assert bb and bb[0]["severity"] == "severe"
    met = check_drug_diseases("Metformin", "Kidney disease")
    assert met and met[0]["severity"] == "severe"  # drug-specific
    # Drug-specific rules override the class rule for the same
    # condition (real overlap: Aspirin in peptic ulcer is severe
    # by its drug rule, moderate by the Antiplatelet class rule).
    asp = check_drug_diseases("Aspirin", "Peptic ulcer")
    assert asp and asp[0]["severity"] == "severe", asp
    assert check_drug_diseases("Chlorhexidine", "Diabetes") == []
    assert check_drug_diseases("Ibuprofen", "") == []

def test_canonical_cases_ar():
    al = check_drug_diseases("Ibuprofen", "أمراض الكلى")
    assert al and al[0]["severity"] == "severe"
    assert "أمراض الكلى" in al[0]["message_ar"]
    assert "إيبوبروفين" in al[0]["message_ar"]
    assert check_drug_diseases("Atenolol", "الربو") != []

def test_existing_dimensions_unchanged():
    dd = check_interactions("Ibuprofen", ["Warfarin"], [], [])
    assert dd and dd[0]["severity"] == "severe"
    alg = check_interactions("Amoxicillin", [], ["Penicillin"], [])
    assert alg and alg[0]["severity"] == "severe"

def test_nystatin_class_correction():
    # Audit #4 (round 28): Nystatin is a polyene antifungal; its
    # class token duplicated its category and matched nothing.
    assert get_medication("Nystatin")["class"] == "Polyene"
    assert get_medication("Nystatin")["category"] == "Antifungal"
    for m in list_medications():
        assert m["class"] and m["category"], m["generic_en"]

def _root():
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw(); return root

def _rx_tab(patient, lang):
    from src.ui.prescriptions import PrescriptionsTab
    from tests.test_clinical_save_gate import _stub_app
    root = _root()
    if root is None: return None, None
    rx = PrescriptionsTab(root, _stub_app(patient, lang=lang), narrow=True)
    rx.pack(); root.update_idletasks(); return root, rx

def test_rx_check_fires_disease_alert_en():
    patient = {"file_number": 0, "diseases": "Kidney disease",
               "current_medications": "", "allergies": ""}
    root, rx = _rx_tab(patient, "en")
    if rx is None: print("SKIP r28 rx disease en"); return
    try:
        rx._check("Ibuprofen")
        hits = [a for a in rx.alerts if a["drug_b"] == "Kidney disease"]
        assert hits and hits[0]["severity"] == "severe", rx.alerts
        assert rx.has_severe is True
        assert "Kidney disease" in rx.alert_box.cget("text")
    finally:
        root.destroy()

def test_rx_check_fires_disease_alert_ar():
    patient = {"file_number": 0, "diseases": "أمراض الكلى",
               "current_medications": "", "allergies": ""}
    root, rx = _rx_tab(patient, "ar")
    if rx is None: print("SKIP r28 rx disease ar"); return
    try:
        rx._check("Ibuprofen")
        hits = [a for a in rx.alerts if a["drug_b"] == "Kidney disease"]
        assert hits and hits[0]["severity"] == "severe", rx.alerts
        assert rx.has_severe is True
        assert "أمراض الكلى" in rx.alert_box.cget("text")
    finally:
        root.destroy()
