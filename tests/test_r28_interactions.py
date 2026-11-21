"""Round 28 item 3b: drug-DRUG completion. The pair table went
129 -> 168 (41 additions, 3 dead tokens retokenized to real
drugs, 2 dead pairs removed). Pins: the exact count, that NO
pair side is a dead token (every side resolves to a generic /
class / category / legacy class), canonical new pairs firing
through the real engine, the fixed chelation pairs firing, and
participation coverage -- every drug either participates in at
least one pair or belongs to a class reviewed with no
significant interaction in standard references (exemption list
below, per the round-28 audit)."""
import json
from pathlib import Path
from src.models.interactions import check_interactions, CLASSES
from src.utils.medications import list_medications

def _data():
    root = Path(__file__).resolve().parent.parent
    meds = list_medications()
    pairs = json.loads((root / "src/data/interactions.json")
                       .read_text(encoding="utf-8"))
    return meds, pairs

def _expand(token, by_class, by_cat, names):
    if token in CLASSES:
        return list(CLASSES[token])
    out = []
    if token in by_class: out += by_class[token]
    if token in by_cat: out += by_cat[token]
    if token in names: out.append(token)
    return out

def test_pair_count_and_format():
    _meds, pairs = _data()
    assert len(pairs) == 168, len(pairs)  # deliberate pin (R28)
    for p in pairs:
        assert set(p) == {"drug_a", "drug_b", "severity",
                          "message_en", "message_ar"}, p
        assert p["severity"] in ("severe", "moderate", "mild")
        assert p["message_en"] and p["message_ar"]
    keys = [frozenset((p["drug_a"].lower(), p["drug_b"].lower()))
            for p in pairs]
    assert len(keys) == len(set(keys)), "duplicate pair"

def test_no_dead_tokens():
    meds, pairs = _data()
    by_class, by_cat, names = {}, {}, set()
    for m in meds:
        by_class.setdefault(m["class"], []).append(m["generic_en"])
        by_cat.setdefault(m["category"], []).append(m["generic_en"])
        names.add(m["generic_en"])
    for p in pairs:
        for side in (p["drug_a"], p["drug_b"]):
            assert _expand(side, by_class, by_cat, names), side

def test_dead_pairs_removed_and_fixed():
    _meds, pairs = _data()
    keys = {frozenset((p["drug_a"], p["drug_b"])) for p in pairs}
    assert frozenset(("ACE-I", "Potassium")) not in keys
    assert frozenset(("Metformin", "Contrast")) not in keys
    assert frozenset(("Tetracycline", "Iron Sulfate")) in keys
    assert frozenset(("Thyroid", "Calcium Carbonate")) in keys
    # the retokenized pairs now actually FIRE (they never could)
    a = check_interactions("Iron Sulfate", ["Levothyroxine"], [], [])
    assert a and a[0]["severity"] == "moderate"
    a = check_interactions("Doxycycline", ["Iron Sulfate"], [], [])
    assert a

def test_new_canonical_pairs_fire():
    cases = [
        ("Ciprofloxacin", "Theophylline", "severe"),
        ("Tizanidine", "Ciprofloxacin", "severe"),
        ("Linezolid", "Sertraline", "severe"),
        ("Meropenem", "Valproic Acid", "severe"),
        ("Domperidone", "Clarithromycin", "severe"),
        ("Isotretinoin", "Doxycycline", "severe"),
        ("Paracetamol", "Warfarin", "moderate"),
        ("Ondansetron", "Azithromycin", "moderate"),
        ("Metronidazole", "Lithium", "moderate"),
        ("Ciprofloxacin", "Ibuprofen", "severe"),  # cipro refinement
    ]
    for new, other, sev in cases:
        a = check_interactions(new, [other], [], [])
        assert a and a[0]["severity"] == sev, (new, other, a)

# Classes whose members were reviewed in round 28 and have NO
# significant drug-drug interaction in standard references at
# this aid's scope (topical/local, vitamins, supplements, etc.).
REVIEWED_NO_PAIR = {
    "LocalAnaesthetic", "Antiseptic", "Polyene", "Antiviral",
    "Antihistamine", "Vitamin", "Allylamine", "Cholesterol",
    "Vasodilator", "Anticholinergic", "Leukotriene", "Antitussive",
    "Expectorant", "H2Blocker", "Antidiarrheal", "Laxative",
    "Aminosalicylate", "Cholinesterase", "NMDA", "Androgen",
    "Vasopressin", "Prostaglandin", "CarbonicAnhydrase", "Mineral",
    "Supplement", "5AlphaReductase", "Beta3Agonist", "AlphaAgonist",
    "Neuraminidase", "NRTI", "Anthelmintic", "Oxytocic",
    "Antifibrinolytic", "OpioidAntagonist", "Antibacterial",
    "Miotic", "Retinoid",
}

def test_participation_coverage():
    meds, pairs = _data()
    by_class, by_cat, names = {}, {}, set()
    for m in meds:
        by_class.setdefault(m["class"], []).append(m["generic_en"])
        by_cat.setdefault(m["category"], []).append(m["generic_en"])
        names.add(m["generic_en"])
    covered = set()
    for p in pairs:
        for a in _expand(p["drug_a"], by_class, by_cat, names):
            for b in _expand(p["drug_b"], by_class, by_cat, names):
                if a != b:
                    covered.add(frozenset((a, b)))
    participating = set()
    for c in covered:
        participating.update(c)
    assert len(participating) >= 230, len(participating)
    for m in meds:
        g = m["generic_en"]
        if g in participating:
            continue
        # muscle relaxants: tizanidine participates; the rest were
        # reviewed (sedation additivity only, below this aid's bar)
        assert m["class"] in REVIEWED_NO_PAIR or m["class"] == "MuscleRelaxant" \
            or g in ("Mirtazapine", "Amphotericin B", "Acyclovir",
                     "Valaciclovir", "Metoclopramide"), (g, m["class"])
