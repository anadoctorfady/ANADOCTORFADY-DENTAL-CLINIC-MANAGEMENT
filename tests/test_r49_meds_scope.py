"""R49 owner addition (2026-11-23 18:17): forms + strengths are
mandatory data, and the interaction/allergy checks explicitly cover
(a) the same prescription, (b) the patient's recorded CURRENT
medications, (c) the patient's recorded allergies -- for singles AND
combos.

Forms/strengths: pinned over the WHOLE list (stronger than new-only):
zero entries with an empty form or strength.

Scope: the real prescription flow (src/ui/prescriptions.py) reads the
patient record via _meds_allergies() -- parse_list(current_medications)
+ parse_list(allergies) -- and _check() calls
check_interactions(generic, meds, allergies, prescribed).  These tests
drive EXACTLY that call shape with a patient record as stored, so the
patient-file scope is pinned end to end at the model seam the UI uses.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils.medications import get_medication, list_medications
from src.models.interactions import check_interactions, parse_list

FAILS = []
def check(name, cond, detail=""):
    if cond: print("PASS", name)
    else: print("FAIL", name, detail); FAILS.append(name)

meds = list_medications()
combos = [m for m in meds if m.get("components")]

# ---- 1. forms + strengths: zero blanks anywhere --------------------
check("no_empty_form_anywhere",
      all(str(m.get("form", "")).strip() for m in meds),
      str([m["generic_en"] for m in meds
           if not str(m.get("form", "")).strip()][:5]))
check("no_empty_strength_anywhere",
      all(str(m.get("strength", "")).strip() for m in meds),
      str([m["generic_en"] for m in meds
           if not str(m.get("strength", "")).strip()][:5]))
check("combos_all_have_form_and_strength", len(combos) == 110 and all(
    str(m.get("form", "")).strip() and str(m.get("strength", "")).strip()
    for m in combos))
check("combo_strength_style_two_part",
      "/" in get_medication("Amlodipine + Valsartan")["strength"],
      get_medication("Amlodipine + Valsartan")["strength"])

# ---- 2. patient-file scope: current medications --------------------
# A patient record as stored in the DB: free-text fields, parsed by the
# same parse_list the prescription form uses.
patient = {"current_medications": "Warfarin", "allergies": ""}
p_meds = parse_list(patient.get("current_medications", ""))
p_allergies = parse_list(patient.get("allergies", ""))

# Owner's named case: the file's current med (Warfarin) interacts with
# a COMPONENT (Ibuprofen) of a newly added combo -> alert on prescribing.
alerts = check_interactions("Paracetamol + Ibuprofen",
                            p_meds, p_allergies, [])
check("patientfile_current_med_vs_combo_component_alerts",
      any("Warfarin" in (a["drug_a"] + a["drug_b"]) for a in alerts),
      str(alerts))

# The same flow for a SINGLE (pre-existing behaviour, pinned so the
# combo coverage is proven to ride the same path, not a new one).
alerts = check_interactions("Ibuprofen", p_meds, p_allergies, [])
check("patientfile_current_med_vs_single_alerts",
      any("Warfarin" in (a["drug_a"] + a["drug_b"]) for a in alerts),
      str(alerts))

# ---- 3. patient-file scope: recorded allergies ---------------------
patient = {"current_medications": "", "allergies": "Penicillin"}
p_meds = parse_list(patient.get("current_medications", ""))
p_allergies = parse_list(patient.get("allergies", ""))
alerts = check_interactions("Amoxicillin + Metronidazole",
                            p_meds, p_allergies, [])
check("patientfile_allergy_vs_combo_component_alerts",
      any(a["severity"] == "severe" and "Penicillin" in a["drug_b"]
          for a in alerts), str(alerts))
alerts = check_interactions("Amoxicillin", p_meds, p_allergies, [])
check("patientfile_allergy_vs_single_alerts",
      any(a["severity"] == "severe" and "Penicillin" in a["drug_b"]
          for a in alerts), str(alerts))

# ---- 4. same-prescription scope still fires for combos -------------
alerts = check_interactions("Paracetamol + Ibuprofen",
                            [], [], ["Warfarin"])
check("same_prescription_vs_combo_component_alerts",
      any("Warfarin" in (a["drug_a"] + a["drug_b"]) for a in alerts),
      str(alerts))

if FAILS:
    raise SystemExit("FAILURES: " + ", ".join(FAILS))
print("ALL R49 MEDS SCOPE TESTS PASSED")
