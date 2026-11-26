"""Round 50: medications data-fix round.

Pins the 14 corrections from the independent pre-build audit
(~/workspace/med_audit_r49/REPORT.md section 6) as loaded through
the app's own medication loading path (src.utils.medications --
seed medications.json merged with user_medications.json, seed
wins by generic_en), plus a staged-install check: on an EXISTING
install whose user file still shadows the fixed names with the
old (wrong) values, the corrected seed values must win and a
genuine user-added drug must survive (the round-49 delivery
mechanism). The real user file is backed up and restored.
"""
import json
from pathlib import Path

from src.utils import medications
from src.utils.medications import (display_for, get_medication,
                                   list_medications, strength_for)

DATA = Path(__file__).resolve().parent.parent / "src" / "data"
TOTAL = 463
# name -> (field, old wrong value, corrected value) -- audit F1..F14
FIXES = {
    "Diclofenac + Misoprostol": ("strength", "50/200 mg", "50 mg/200 mcg"),
    "Perindopril + Amlodipine + Indapamide": ("strength", "4/5 mg", "4/5/1.25 mg"),
    "Amlodipine + Valsartan + Hydrochlorothiazide": ("strength", "5/160 mg", "5/160/12.5 mg"),
    "Bismuth Subcitrate + Metronidazole + Tetracycline": ("strength", "140/125 mg", "140/125/125 mg"),
    "Paracetamol + Aspirin + Caffeine": ("strength", "250/250 mg", "250/250/65 mg"),
    "Paracetamol + Diclofenac + Chlorzoxazone": ("strength", "325/50 mg", "325/50/250 mg"),
    "Rifampicin + Isoniazid + Pyrazinamide + Ethambutol": ("strength", "150/75 mg", "150/75/400/275 mg"),
    "Levodopa + Carbidopa + Entacapone": ("strength", "100/25 mg", "100/25/200 mg"),
    "Fluticasone Propionate + Umeclidinium + Vilanterol": ("strength", "100/25 mcg/dose", "100/62.5/25 mcg/dose"),
    "Calcium Carbonate + Cholecalciferol": ("strength", "600 mg", "600 mg/400 IU"),
    "Insulin Glargine + Lixisenatide": ("strength", "100 IU/ml", "100 IU/ml + 33 mcg/ml"),
    "Insulin Degludec + Liraglutide": ("strength", "100 IU/ml", "100 IU/ml + 3.6 mg/ml"),
    "Naproxen + Esomeprazole": ("class", "Analgesic", "NSAID"),
    "Levodopa": ("strength", "25/100 mg", "100 mg"),
}
assert len(FIXES) == 14


def test_all_14_fixes_via_loading_path():
    for name, (field, old, new) in FIXES.items():
        m = get_medication(name)
        assert m is not None, name
        assert m[field] == new, (name, field, m[field], new)
        assert m[field] != old, (name, field, "still the old value")
        if field == "strength":
            assert strength_for(name) == new, name


def test_display_shows_corrected_strengths():
    # F1: the 1000x unit error must not reach a prescription display.
    d = display_for("Diclofenac + Misoprostol", "en")
    assert "50 mg/200 mcg" in d and "50/200 mg" not in d, d
    d = display_for("Levodopa", "en")
    assert d.endswith("100 mg") and "25/100" not in d, d


def test_untouched_neighbours_and_count():
    seed = json.loads((DATA / "medications.json").read_text(encoding="utf-8"))
    assert len(seed) == TOTAL, len(seed)
    # Entries the audit verified as correct stay byte-identical values.
    assert strength_for("Misoprostol") == "200 mcg"
    assert strength_for("Levodopa + Carbidopa") == "100/25 mg"
    assert strength_for("Levodopa + Benserazide") == "100/25 mg"
    assert strength_for("Insulin Degludec") == "100 IU/ml"
    # No loaded entry still carries any fixed name's old value.
    for m in list_medications():
        fix = FIXES.get(m["generic_en"])
        if fix:
            assert m[fix[0]] != fix[1], (m["generic_en"], fix[0])


def test_f13_class_fix_keeps_components():
    m = get_medication("Naproxen + Esomeprazole")
    assert m["class"] == "NSAID"
    assert m["components"] == ["Naproxen", "Esomeprazole"]
    assert get_medication("Naproxen")["class"] == "NSAID"


def test_staged_install_corrected_seed_wins():
    user_path = Path(medications._USER)
    backup = user_path.read_text(encoding="utf-8") if user_path.exists() else None
    staged = []
    for name, (field, old, _new) in FIXES.items():
        entry = {"generic_en": name, "generic_ar": "ظل قديم",
                 "brand_en": "", "brand_ar": "", "category": "Other",
                 "form": "Tablet", "strength": "1 mg", "class": "StaleShadow"}
        entry[field] = old  # the stale pre-fix value an old install could hold
        staged.append(entry)
    staged.append({"generic_en": "R50USERDRUG", "generic_ar": "دواء مستخدم",
                   "brand_en": "", "brand_ar": "", "category": "Antibiotic",
                   "form": "Tablet", "strength": "250 mg", "class": "Penicillin"})
    try:
        user_path.write_text(json.dumps(staged, ensure_ascii=False),
                             encoding="utf-8")
        medications._CACHE = None
        from src.models.interactions import invalidate_drug_caches
        invalidate_drug_caches()
        for name, (field, old, new) in FIXES.items():
            m = get_medication(name)
            assert m is not None and m[field] == new, (name, field, m and m[field])
            assert m["class"] != "StaleShadow", name
        assert get_medication("R50USERDRUG") is not None  # user drug survives
        meds = list_medications()
        names = [m["generic_en"].lower() for m in meds]
        assert len(names) == len(set(names)), "duplicate generic_en"
        assert len(meds) == TOTAL + 1, len(meds)  # shadows add nothing
    finally:
        if backup is None:
            user_path.unlink(missing_ok=True)
        else:
            user_path.write_text(backup, encoding="utf-8")
        medications._CACHE = None
        from src.models.interactions import invalidate_drug_caches
        invalidate_drug_caches()
    assert len(list_medications()) >= TOTAL
