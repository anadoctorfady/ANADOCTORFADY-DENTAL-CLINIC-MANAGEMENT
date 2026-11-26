"""Round 49 Section A: combination-drug ENGINE acceptance tests.

(a) NSAID combo vs Warfarin -> drug-drug alert (component class).
(b) Two combos sharing a component class -> alert.
(c) Penicillin allergy + Amoxicillin combo -> allergy alert.
(d) Sulfa allergy + Sulfamethoxazole-Trimethoprim -> allergy alert.
(e) NSAID allergy + Paracetamol + Ibuprofen -> allergy alert.
(f) Severer component's disease alert wins the max-severity merge.
(g) Combo + standalone component -> duplicate-ingredient alert.
"""
from src.models import drug_diseases as dd
from src.models.drug_diseases import check_drug_diseases, review_outcome
from src.models.interactions import check_interactions


def test_a_nsaid_combo_vs_warfarin():
    a = check_interactions("Paracetamol + Ibuprofen", ["Warfarin"], [], [])
    assert a and a[0]["severity"] == "severe", a


def test_b_two_combos_sharing_component_class():
    a = check_interactions("Paracetamol + Diclofenac",
                           ["Paracetamol + Ibuprofen"], [], [])
    assert a, "no alert for two NSAID/paracetamol combos"


def test_c_penicillin_allergy_amoxicillin_combo():
    for combo in ("Amoxicillin + Metronidazole", "Amoxicillin-Clavulanate"):
        a = check_interactions(combo, [], ["Penicillin"], [])
        assert a and a[0]["severity"] == "severe", (combo, a)


def test_d_sulfa_allergy_cotrimoxazole():
    a = check_interactions("Sulfamethoxazole-Trimethoprim", [], ["Sulfa"], [])
    assert a and a[0]["severity"] == "severe", a


def test_e_nsaid_allergy_nsaid_combo():
    a = check_interactions("Paracetamol + Ibuprofen", [], ["NSAID"], [])
    assert a and a[0]["severity"] == "severe", a


def test_f_max_severity_merge_real_combo():
    # Renal impairment: the NSAID component's class rule is severe,
    # paracetamol's Analgesic class rule is only moderate -- the
    # severer component must win (the pre-R49 single-class merge
    # could silently downgrade this).
    a = check_drug_diseases("Paracetamol + Ibuprofen", "Kidney disease")
    renal = [x for x in a if x["drug_b"] == "Kidney disease"]
    assert renal and renal[0]["severity"] == "severe", a


def test_f_max_severity_merge_synthetic_regression():
    # Inject a MILD drug-specific rule for Ibuprofen in renal
    # impairment: it must NOT downgrade the severe NSAID class rule.
    orig = dd._CACHE
    try:
        data = dict(orig)
        data["drug_rules"] = list(orig["drug_rules"]) + [{
            "drug": "Ibuprofen", "condition": "renal_impairment",
            "severity": "mild", "note_en": "synthetic mild",
            "note_ar": "خفيف اصطناعي"}]
        dd._CACHE = data
        a = check_drug_diseases("Ibuprofen", "Kidney disease")
        renal = [x for x in a if x["drug_b"] == "Kidney disease"]
        assert renal and renal[0]["severity"] == "severe", a
    finally:
        dd._CACHE = orig


def test_g_duplication_combo_plus_component():
    a = check_interactions("Paracetamol + Ibuprofen", [], [], ["Paracetamol"])
    dup = [x for x in a if x["message_en"].startswith("Duplicate ingredient:")]
    assert len(dup) == 1, a
    assert dup[0]["severity"] == "moderate"
    assert dup[0]["message_en"] == (
        "Duplicate ingredient: Paracetamol in both "
        "Paracetamol + Ibuprofen and Paracetamol.")
    assert "مكوّن مكرر" in dup[0]["message_ar"]


def test_review_outcome_combo_covered_and_unreviewed():
    kind, _key = review_outcome("Paracetamol + Ibuprofen")
    assert kind != "unreviewed"
    # Synthetic: strip NSAID coverage from the manifest + rules --
    # the combo must report unreviewed naming the NSAID class.
    orig = dd._CACHE
    try:
        data = dict(orig)
        data["classes_reviewed"] = [c for c in orig["classes_reviewed"]
                                    if c != "NSAID"]
        data["no_rule_classes"] = [c for c in orig.get("no_rule_classes", [])
                                   if c != "NSAID"]
        data["class_rules"] = [r for r in orig["class_rules"]
                               if r["class"] != "NSAID"]
        dd._CACHE = data
        kind, key = review_outcome("Paracetamol + Ibuprofen")
        assert kind == "unreviewed" and key == "NSAID", (kind, key)
        # Single-drug behaviour is unchanged in shape.
        kind2, _ = review_outcome("Amoxicillin")
        assert kind2 != "unreviewed"
    finally:
        dd._CACHE = orig
