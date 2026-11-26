"""Round 49 Section A: combination-drug DATA + delivery/upgrade path.

Data: 463 seed entries = 315 originals + 40 previously-missing
single components + 108 NEW fixed-dose combinations; the 2 combos
that already existed (Amoxicillin-Clavulanate,
Sulfamethoxazole-Trimethoprim) were upgraded IN PLACE with a
components/component_classes field (their generic_en is unchanged
because stored prescriptions in clinic DBs reference it).

Delivery: drugs are file-based -- src/data/medications.json merged
with user_medications.json by generic_en (seed wins) in
src/utils/medications.py. The delivery test below stages a
user_medications.json the way an EXISTING install would have one
after the upgrade: a user-added drug must survive, and a user entry
shadowing a NEW combo name must not duplicate or replace the seed
combo. The real user file is backed up and restored.
"""
import json
from pathlib import Path

from src.utils import medications
from src.utils.medications import get_medication, list_medications

DATA = Path(__file__).resolve().parent.parent / "src" / "data"
TOTAL = 463
NEW_SINGLES = ["Aceclofenac", "Alogliptin", "Amiloride", "Artemether",
    "Bempedoic Acid", "Benserazide", "Bismuth Subcitrate", "Caffeine",
    "Carbidopa", "Cefoperazone", "Chlorzoxazone", "Clavulanic Acid",
    "Desogestrel", "Dexketoprofen", "Drospirenone", "Entacapone",
    "Glimepiride", "Glycopyrronium", "Hydrocodone", "Indacaterol",
    "Lercanidipine", "Lixisenatide", "Lumefantrine", "Methocarbamol",
    "Olodaterol", "Ornidazole", "Piperacillin", "Pyrimethamine",
    "Sacubitril", "Sulbactam", "Sulfadoxine", "Sulfamethoxazole",
    "Tazobactam", "Telmisartan", "Thiocolchicoside", "Trandolapril",
    "Triamterene", "Umeclidinium", "Vilanterol", "Vildagliptin"]
UPGRADED = {"Amoxicillin-Clavulanate": ["Amoxicillin", "Clavulanic Acid"],
            "Sulfamethoxazole-Trimethoprim": ["Sulfamethoxazole", "Trimethoprim"]}


def _seed():
    return json.loads((DATA / "medications.json").read_text(encoding="utf-8"))


def test_counts_and_combo_shape():
    seed = _seed()
    assert len(seed) == TOTAL, len(seed)
    combos = [m for m in seed if m.get("components")]
    assert len(combos) == 110, len(combos)  # 108 new + 2 upgraded
    by_name = {m["generic_en"]: m for m in seed}
    for name, comps in UPGRADED.items():
        assert by_name[name]["components"] == comps, name
        assert len(by_name[name]["component_classes"]) == len(comps)
    for m in combos:
        assert len(m["component_classes"]) == len(m["components"]), m["generic_en"]
        assert m["brand_en"] == "" and m["brand_ar"] == "" or \
            m["generic_en"] in UPGRADED, m["generic_en"]
        for comp in m["components"]:
            assert comp in by_name, (m["generic_en"], comp)
            assert by_name[comp].get("generic_ar"), comp
        # generic_ar is the components' Arabic names joined with " + "
        expect = " + ".join(by_name[c]["generic_ar"] for c in m["components"])
        if m["generic_en"] not in UPGRADED:
            assert m["generic_ar"] == expect, m["generic_en"]


def test_new_singles_present():
    for name in NEW_SINGLES:
        m = get_medication(name)
        assert m is not None, name
        assert m["class"] and m["category"] and m["strength"], name


def test_delivery_existing_install_user_file():
    user_path = Path(medications._USER)
    backup = user_path.read_text(encoding="utf-8") if user_path.exists() else None
    staged = [
        {"generic_en": "R49USERDRUG", "generic_ar": "دواء مستخدم",
         "brand_en": "", "brand_ar": "", "category": "Antibiotic",
         "form": "Tablet", "strength": "250 mg", "class": "Penicillin"},
        {"generic_en": "Paracetamol + Ibuprofen", "generic_ar": "ظل",
         "brand_en": "", "brand_ar": "", "category": "Analgesic",
         "form": "Tablet", "strength": "1 mg", "class": "UserShadow"},
    ]
    try:
        user_path.write_text(json.dumps(staged, ensure_ascii=False),
                             encoding="utf-8")
        medications._CACHE = None
        from src.models.interactions import invalidate_drug_caches
        invalidate_drug_caches()
        seed = _seed()
        combos = [m for m in seed if m.get("components")]
        assert len(combos) == 110
        for m in combos:  # all 108 new + 2 upgraded combos resolve
            got = get_medication(m["generic_en"])
            assert got is not None and got.get("components"), m["generic_en"]
        for name in NEW_SINGLES:
            assert get_medication(name) is not None, name
        # The user-added drug survives the upgrade.
        assert get_medication("R49USERDRUG") is not None
        # The shadowing user entry does NOT replace the seed combo.
        assert get_medication("Paracetamol + Ibuprofen")["class"] != "UserShadow"
        meds = list_medications()
        names = [m["generic_en"].lower() for m in meds]
        assert len(names) == len(set(names)), "duplicate generic_en"
        assert len(meds) == TOTAL + 1, len(meds)  # +1 user drug only
    finally:
        if backup is None:
            user_path.unlink(missing_ok=True)
        else:
            user_path.write_text(backup, encoding="utf-8")
        medications._CACHE = None
        from src.models.interactions import invalidate_drug_caches
        invalidate_drug_caches()
    assert len(list_medications()) >= TOTAL
