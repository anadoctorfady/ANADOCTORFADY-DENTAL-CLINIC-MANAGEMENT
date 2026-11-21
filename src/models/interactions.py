"""Drug interaction checker (curated aid, NOT a substitute for clinical judgment)."""
import json
from pathlib import Path
_DATA = Path(__file__).resolve().parent.parent / "data" / "interactions.json"
_CACHE = None
# Class tokens used in interactions.json (drug_b may be a class); legacy members.
CLASSES = {
    "NSAID": ["Ibuprofen", "Diclofenac", "Diclofenac Potassium",
              "Diclofenac Sodium", "Naproxen", "Mefenamic Acid",
              "Ketorolac", "Celecoxib", "Aspirin", "Ketoprofen", "Meloxicam",
              "Piroxicam", "Indomethacin", "Etoricoxib"],
    "Penicillin": ["Amoxicillin", "Amoxicillin-Clavulanate", "Ampicillin",
                   "Penicillin V"],
}
_MED_CACHE = None
def _med_class(name):
    """Resolve a drug name to its class(es) via medications.json."""
    global _MED_CACHE
    if _MED_CACHE is None:
        try:
            from src.utils.medications import get_medication
            _MED_CACHE = get_medication
        except Exception:
            _MED_CACHE = None
    if _MED_CACHE:
        m = _MED_CACHE(name)
        if m:
            return [c for c in [m.get("class"), m.get("category")] if c]
    return []
def _classes_of(name):
    out = [name]
    for cls, members in CLASSES.items():
        if _norm(name) in [_norm(x) for x in members]:
            out.append(cls)
    out += _med_class(name)
    return out
SEVERITY_COLORS = {
    "severe": ("#DC2626", "#FEE2E2"),   # red text on light-red bg
    "moderate": ("#D97706", "#FEF3C7"),  # amber
    "mild": ("#CA8A04", "#FEF9C3"),      # yellow
}
DISCLAIMER_EN = "Interaction data is a curated aid only - it does not replace clinical judgment. Always verify before prescribing."
DISCLAIMER_AR = "بيانات التداخلات الدوائية مساعدة فقط ولا تغني عن الحكم السريري للطبيب. تحقق دائماً قبل وصف الدواء."

def _load():
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(_DATA.read_text(encoding="utf-8"))
    return _CACHE

def _norm(s):
    return (s or "").strip().lower()

def _expand(name):
    """A class token expands to all its member generics; a generic
    expands to itself + its class(es) so class-level pairs match it."""
    if name in CLASSES:
        return CLASSES[name]
    # class names used in interactions.json: look up members by class
    try:
        from src.utils.medications import list_medications
        members = [m["generic_en"] for m in list_medications()
                   if _norm(m.get("class")) == _norm(name)
                   or _norm(m.get("category")) == _norm(name)]
        if members:
            return members + [name]
    except Exception:
        pass
    return [name]

def _matches(entry_side, drug):
    if _norm(entry_side) == _norm(drug):
        return True
    if _norm(drug) in [_norm(x) for x in _expand(entry_side)]:
        return True
    # drug's class matches the entry side (e.g. Clarithromycin is a Macrolide)
    return _norm(entry_side) in [_norm(c) for c in _classes_of(drug)]

# --- Round 29: allergy matching --------------------------------------
# The old test `a in _norm(al)` (a == _norm(al)) was a tautology that
# fired SEVERE for EVERY drug when ANY allergy text existed. Matching
# is now relation-based. Keywords (EN+AR) -> `class` token:
_ALLERGEN_CLASS_KEYS = (
    (("penicillin", "بنسلين"), "penicillin"),
    (("cephalosporin", "سيفالوسبورين", "سفالوسبورين"), "cephalosporin"),
    (("nsaid", "nonsteroidal", "non-steroidal", "مضادات الالتهاب"), "nsaid"),
    (("tetracycline", "تتراسيكلين"), "tetracycline"),
    (("macrolide", "ماكروليد"), "macrolide"),
    (("opioid", "أفيون"), "opioid"),
    (("local anaesthetic", "local anesthetic", "مخدرات موضعية", "مخدرات الموضعية", "المخدرات الموضعية", "مخدر موضعي", "تخدير موضعي"), "localanaesthetic"),
    (("sulfa", "sulpha", "sulfonamide", "sulphonamide", "سلفا"), "sulfonamide"),
)
_TRACKED_CLASSES = {tok for _keys, tok in _ALLERGEN_CLASS_KEYS}
_CLASS_CACHE = None
def invalidate_drug_caches(): global _CLASS_CACHE, _NAMED_CACHE; _CLASS_CACHE = _NAMED_CACHE = None  # R30: medications._load() calls this whenever its merged list rebuilds (user drug added/removed mid-session), so allergy class/named matching never works from a stale snapshot
def _drug_class_tokens(name):
    """Class tokens for allergy matching: medications.json `class`
    plus legacy CLASSES (`category` excluded -- too broad)."""
    global _CLASS_CACHE
    if _CLASS_CACHE is None:
        cache = {}  # build locally: list_medications() may re-entrantly invalidate (R30)
        try:
            from src.utils.medications import list_medications
            for m in list_medications():
                if _norm(m.get("class")):
                    cache[_norm(m.get("generic_en"))] = _norm(m["class"])
        except Exception:
            pass
        _CLASS_CACHE = cache
    out = {_CLASS_CACHE[_norm(name)]} if _CLASS_CACHE.get(_norm(name)) else set()
    out |= {_norm(c) for c, mem in CLASSES.items() if _norm(name) in [_norm(x) for x in mem]}
    return out
_NAMED_CACHE = None
def _named_classes(a):
    """Tracked class tokens of drugs NAMED in the allergy text
    (generic/brand, EN/AR): 'Aspirin allergy' names Aspirin (tracked
    class NSAID); untracked classes never alert on their own."""
    global _NAMED_CACHE
    if _NAMED_CACHE is None:
        named = []  # build locally: list_medications() may re-entrantly invalidate (R30)
        try:
            from src.utils.medications import list_medications
            for m in list_medications():
                names = {_norm(m.get(f)) for f in ("generic_en", "generic_ar",
                         "brand_en", "brand_ar") if len(_norm(m.get(f))) >= 4}
                named.append((m.get("generic_en", ""), names))
        except Exception:
            pass
        _NAMED_CACHE = named
    out = set()
    for generic, names in _NAMED_CACHE:
        if any(n in a for n in names):
            out |= _drug_class_tokens(generic) & _TRACKED_CLASSES
    out |= {_norm(c) for c, mem in CLASSES.items()
            if _norm(c) in _TRACKED_CLASSES
            and any(_norm(x) in a for x in mem)}
    return out
def _allergy_relation(a, new_drug):
    """Genuine relation only: the allergen names the drug's class, a
    drug of the same (tracked) class, or the drug itself. Non-drug
    allergens (latex, iodine) / 'no known allergy' match nothing."""
    drug = _norm(new_drug)
    if not a or not drug:
        return False
    classes = _drug_class_tokens(new_drug)
    if any(tok in classes and any(k in a for k in keys)
           for keys, tok in _ALLERGEN_CLASS_KEYS):
        return True
    if _named_classes(a) & classes:
        return True
    return (len(drug) >= 4 and drug in a) or (len(a) >= 4 and a in drug)

def check_interactions(new_drug, patient_meds=None, allergies=None,
                       prescribed=None):
    """Return list of alerts {severity, message_en, message_ar, drug_a,
    drug_b}. Checks new drug vs patient meds + already-prescribed items,
    plus known allergies: an allergy alert fires only for a genuine
    relation (same drug, same tracked class, or a class keyword) --
    round-29 fix; see _allergy_relation."""
    alerts, seen = [], set()
    others = list(patient_meds or []) + list(prescribed or [])
    for other in others:
        if _norm(other) == _norm(new_drug):
            continue
        for e in _load():
            if ((_matches(e["drug_a"], new_drug) and _matches(e["drug_b"], other))
                    or (_matches(e["drug_b"], new_drug) and _matches(e["drug_a"], other))):
                # one alert per (new drug, other drug, severity):
                # explicit + class-level pairs for the same drugs collapse
                key = (e["severity"], _norm(new_drug), _norm(other))
                if key not in seen:
                    seen.add(key)
                    alerts.append({"severity": e["severity"],
                        "message_en": e["message_en"], "message_ar": e["message_ar"],
                        "drug_a": e["drug_a"], "drug_b": e["drug_b"]})
    for al in (allergies or []):
        a = _norm(al)
        if not a:
            continue
        pen = "penicillin" in a or "بنسلين" in a
        if pen and _norm(new_drug) in [_norm(x) for x in CLASSES["Penicillin"]]:
            alerts.append({"severity": "severe",
                "message_en": f"Known penicillin allergy - do NOT prescribe {new_drug}.",
                "message_ar": f"حساسية معروفة من البنسلين - لا تصف {new_drug}.",
                "drug_a": new_drug, "drug_b": "Penicillin allergy"})
        elif _allergy_relation(a, new_drug):
            alerts.append({"severity": "severe",
                "message_en": f"Known allergy to {al} - do NOT prescribe {new_drug}.",
                "message_ar": f"حساسية معروفة من {al} - لا تصف {new_drug}.",
                "drug_a": new_drug, "drug_b": al})
        elif ("sulfa" in a or "سلفا" in a) and "sulfamethoxazole" in _norm(new_drug):
            alerts.append({"severity": "severe",
                "message_en": "Known sulfa allergy - do NOT prescribe sulfamethoxazole.",
                "message_ar": "حساسية معروفة من السلفا - لا تصف السلفاميثوكسازول.",
                "drug_a": new_drug, "drug_b": "Sulfa allergy"})
    order = {"severe": 0, "moderate": 1, "mild": 2}
    return sorted(alerts, key=lambda x: order.get(x["severity"], 9))

def parse_list(text):
    return [x.strip() for x in str(text or "").replace("،", ",").split(",") if x.strip()]
