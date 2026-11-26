"""Round 29: allergy-branch false-positive fix.

Root cause: the name-match branch of check_interactions tested
`a in _norm(al)` where a == _norm(al) -- a tautology -- so ANY
recorded allergy fired a SEVERE alert for EVERY prescribed drug
(round-28 shot 67: penicillin allergy + ibuprofen -> "[SEVERE]
Known allergy to Penicillin - do NOT prescribe Ibuprofen").
Matching is now relation-based only: the allergen names the drug
itself, names its class (the tracked classes of the app's own
allergy templates, EN + AR), or names a drug of the same class.
Expected firing sets below are derived from the medications data
(class field + legacy CLASSES), not from the implementation."""
from src.models.interactions import check_interactions, CLASSES
from src.models.drug_diseases import check_drug_diseases
from src.utils.medications import list_medications

MEDS = list_medications()
ALL_DRUGS = [m["generic_en"] for m in MEDS]
BY_CLASS = {}
for _m in MEDS:
    BY_CLASS.setdefault(_m["class"], set()).add(_m["generic_en"])

def _fired(allergen):
    """Drugs for which this single allergy entry raises an alert
    (no current meds / prescribed items, so every alert returned
    comes from the allergy branch)."""
    return {d for d in ALL_DRUGS if check_interactions(d, [], [allergen], [])}

# Round 49 (Section A): matching is component-aware -- a
# combination fires for the classes of ALL its components, not
# only its own `class`. Expected sets are derived the same way
# from the data (own class + component_classes + each
# component's own class), else every combo reads as a false
# positive against the round-29 expectations.
_BY_NAME = {m["generic_en"]: m for m in MEDS}

def _class_tokens(m):
    toks = {m.get("class") or ""}
    toks |= set(m.get("component_classes") or [])
    for comp in m.get("components") or []:
        cm = _BY_NAME.get(comp)
        if cm:
            toks.add(cm.get("class") or "")
    return {t for t in toks if t}

def _expected(cls):
    s = {m["generic_en"] for m in MEDS if cls in _class_tokens(m)}
    for legacy, members in CLASSES.items():
        if legacy.lower() == cls.lower():
            s |= set(members)
    return s

def test_shot67_scenario_diseases_fire_allergy_silent():
    # The exact shot-67 patient: penicillin allergy, kidney disease
    # + hypertension, prescribed ibuprofen. Pre-fix this produced a
    # false SEVERE allergy line on top of the two disease alerts.
    inter = check_interactions("Ibuprofen", [], ["Penicillin"], [])
    assert inter == [], inter
    merged = inter + check_drug_diseases("Ibuprofen", "Kidney disease, Hypertension")
    merged.sort(key=lambda a: {"severe": 0, "moderate": 1, "mild": 2}[a["severity"]])
    assert [a["severity"] for a in merged] == ["severe", "moderate"], merged
    assert "Kidney disease" in merged[0]["message_en"]
    assert "Hypertension" in merged[1]["message_en"]
    assert not any("allerg" in a["message_en"].lower() for a in merged)

def test_penicillin_true_positives_stay_severe():
    for drug in ("Amoxicillin", "Amoxicillin-Clavulanate", "Ampicillin", "Penicillin V"):
        a = check_interactions(drug, [], ["Penicillin"], [])
        assert a and a[0]["severity"] == "severe", (drug, a)
        assert "penicillin" in a[0]["message_en"].lower()
    # ...while unrelated drugs stay silent for the same record.
    for drug in ("Ibuprofen", "Paracetamol", "Metronidazole", "Lidocaine", "Cephalexin"):
        assert check_interactions(drug, [], ["Penicillin"], []) == [], drug

def test_class_templates_fire_exactly_their_class_en():
    cases = {"Penicillin allergy": "Penicillin",
             "Cephalosporin allergy": "Cephalosporin",
             "NSAID allergy": "NSAID",
             "Tetracycline allergy": "Tetracycline",
             "Macrolide allergy": "Macrolide",
             "Opioid allergy": "Opioid",
             "Local anaesthetic allergy": "LocalAnaesthetic",
             "Sulfa drug allergy": "Sulfonamide"}
    for allergen, cls in cases.items():
        got, want = _fired(allergen), _expected(cls)
        assert got == want, (allergen, sorted(got - want), sorted(want - got))

def test_aspirin_allergen_fires_nsaid_class_not_antiplatelets():
    # Aspirin is an NSAID for hypersensitivity (legacy CLASSES) even
    # though its data class is Antiplatelet: the allergen fires for
    # aspirin + every NSAID, but NOT for other antiplatelets such as
    # clopidogrel (the standard substitute) and NOT for paracetamol.
    got = _fired("Aspirin allergy")
    assert got == _expected("NSAID") | {"Aspirin"}, sorted(got)
    assert "Clopidogrel" not in got and "Paracetamol" not in got

def test_non_drug_and_no_known_allergens_never_fire():
    for allergen in ("Latex allergy", "Iodine allergy", "No known drug allergy",
                     "حساسية للاتكس", "حساسية لليود", "لا توجد حساسية معروفة للأدوية"):
        got = _fired(allergen)
        assert got == set(), (allergen, sorted(got))

def test_arabic_templates_match_english_firing_sets():
    pairs = {"حساسية للبنسلين": "Penicillin allergy",
             "حساسية للسيفالوسبورينات": "Cephalosporin allergy",
             "حساسية لمضادات الالتهاب غير الستيرويدية": "NSAID allergy",
             "حساسية للتتراسيكلين": "Tetracycline allergy",
             "حساسية للماكروليدات": "Macrolide allergy",
             "حساسية للأدوية الأفيونية": "Opioid allergy",
             "حساسية للمخدرات الموضعية": "Local anaesthetic allergy",
             "حساسية لأدوية السلفا": "Sulfa drug allergy",
             "حساسية للأسبرين": "Aspirin allergy"}
    for ar, en in pairs.items():
        assert _fired(ar) == _fired(en), ar
    # Bare Arabic allergen word behaves like the bare English one.
    a = check_interactions("Amoxicillin", [], ["بنسلين"], [])
    assert a and a[0]["severity"] == "severe"
    assert check_interactions("Ibuprofen", [], ["بنسلين"], []) == []

def test_same_class_cross_and_boundary_cases():
    # Same-class true positives (one per tracked class family).
    assert check_interactions("Diclofenac", [], ["NSAID allergy"], [])
    assert check_interactions("Cefixime", [], ["Cephalosporin allergy"], [])
    assert check_interactions("Articaine", [], ["Local anaesthetic allergy"], [])
    assert check_interactions("Sulfamethoxazole-Trimethoprim", [], ["Sulfa drug allergy"], [])
    assert check_interactions("Sulfamethoxazole-Trimethoprim", [], ["Sulfa"], [])
    # Free-text allergen naming one drug covers its whole class.
    assert check_interactions("Diclofenac", [], ["Ibuprofen"], [])
    assert check_interactions("Ampicillin", [], ["Amoxicillin"], [])
    # Boundaries that must stay silent:
    # - clindamycin is the classic macrolide substitute (lincosamide).
    assert check_interactions("Clindamycin", [], ["Macrolide allergy"], []) == []
    # - the app's data keeps cephalosporin allergy as its OWN entry;
    #   no penicillin<->cephalosporin cross-reactivity rule is encoded
    #   in the allergy data, so neither direction fires.
    assert check_interactions("Cephalexin", [], ["Penicillin allergy"], []) == []
    assert check_interactions("Amoxicillin", [], ["Cephalosporin allergy"], []) == []
    # - an unrelated class never fires.
    assert check_interactions("Paracetamol", [], ["Ibuprofen"], []) == []

def test_no_allergies_no_alerts():
    for drug in ("Amoxicillin", "Ibuprofen", "Sulfamethoxazole-Trimethoprim"):
        assert check_interactions(drug, [], [], []) == []
        assert check_interactions(drug, [], [""], []) == []
        assert check_interactions(drug, [], None, []) == []
