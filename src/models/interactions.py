"""Drug interaction checker (curated aid, NOT a substitute for clinical judgment)."""
import json
from pathlib import Path
_DATA = Path(__file__).resolve().parent.parent / "data" / "interactions.json"
_CACHE = None
# Class tokens used in interactions.json (drug_b may be a class); legacy members.
CLASSES = {
    "NSAID": ["Ibuprofen", "Diclofenac", "Diclofenac Potassium", "Diclofenac Sodium", "Naproxen", "Mefenamic Acid", "Ketorolac", "Celecoxib", "Aspirin", "Ketoprofen", "Meloxicam", "Piroxicam", "Indomethacin", "Etoricoxib", "Aceclofenac", "Dexketoprofen"],
    "Penicillin": ["Amoxicillin", "Amoxicillin-Clavulanate", "Ampicillin", "Penicillin V", "Piperacillin"],
}
_MED_CACHE = None
def _getter():
    global _MED_CACHE
    if _MED_CACHE is None:
        try:
            from src.utils.medications import get_medication
            _MED_CACHE = get_medication
        except Exception:
            _MED_CACHE = False
    return _MED_CACHE or None
def _entry(name):
    g = _getter()
    return g(name) if g else None
def _med_class(name):
    """Class(es) via medications.json. R49: a combo unions [class, category] of itself AND every component PLUS its component_classes tokens."""
    m = _entry(name)
    if not m:
        return []
    out = [c for c in [m.get("class"), m.get("category")] if c]
    for comp in m.get("components") or []:
        cm = _entry(comp)
        if cm:
            out += [c for c in [cm.get("class"), cm.get("category")] if c]
    out += [t for t in m.get("component_classes") or [] if t]
    return list(dict.fromkeys(out))
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
def _norm(s): return (s or "").strip().lower()
def _expand(name):
    """A class token expands to all its member generics; a generic
    expands to itself + its class(es) so class-level pairs match it."""
    if name in CLASSES:
        return CLASSES[name]
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
# --- Round 29: allergy matching (relation-based; see _allergy_relation).
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
    """Class tokens for allergy matching: medications.json `class` plus legacy CLASSES (`category` excluded). R49: combos union over components + component_classes."""
    global _CLASS_CACHE
    if _CLASS_CACHE is None:
        cache = {}  # build locally: list_medications() may re-entrantly invalidate (R30)
        try:
            from src.utils.medications import list_medications
            meds = list_medications()
            raw = {_norm(m.get("generic_en")): _norm(m.get("class")) for m in meds if _norm(m.get("class"))}
            for m in meds:
                toks = {raw[_norm(m["generic_en"])]} if _norm(m.get("generic_en")) in raw else set()
                toks |= {_norm(t) for t in m.get("component_classes") or [] if t}
                for comp in m.get("components") or []:
                    if _norm(comp) in raw:
                        toks.add(raw[_norm(comp)])
                if toks:
                    cache[_norm(m.get("generic_en"))] = toks
        except Exception:
            pass
        _CLASS_CACHE = cache
    out = set(_CLASS_CACHE.get(_norm(name)) or set())
    out |= {_norm(c) for c, mem in CLASSES.items() if _norm(name) in [_norm(x) for x in mem]}
    return out
_NAMED_CACHE = None
def _named_classes(a):
    """Tracked class tokens of drugs NAMED in the allergy text (generic/brand, EN/AR); untracked classes never alert on their own."""
    global _NAMED_CACHE
    if _NAMED_CACHE is None:
        named = []  # build locally: list_medications() may re-entrantly invalidate (R30)
        try:
            from src.utils.medications import list_medications
            for m in list_medications():
                names = {_norm(m.get(f)) for f in ("generic_en", "generic_ar", "brand_en", "brand_ar") if len(_norm(m.get(f))) >= 4}
                named.append((m.get("generic_en", ""), names))
        except Exception:
            pass
        _NAMED_CACHE = named
    out = set()
    for generic, names in _NAMED_CACHE:
        if any(n in a for n in names):
            out |= _drug_class_tokens(generic) & _TRACKED_CLASSES
    out |= {_norm(c) for c, mem in CLASSES.items() if _norm(c) in _TRACKED_CLASSES and any(_norm(x) in a for x in mem)}
    return out
def _allergy_relation(a, new_drug):
    """Genuine relation only: the allergen names the drug's class, a drug of the same (tracked) class, or the drug itself."""
    drug = _norm(new_drug)
    if not a or not drug:
        return False
    classes = _drug_class_tokens(new_drug)
    if any(tok in classes and any(k in a for k in keys) for keys, tok in _ALLERGEN_CLASS_KEYS):
        return True
    if _named_classes(a) & classes:
        return True
    return (len(drug) >= 4 and drug in a) or (len(a) >= 4 and a in drug)
def _comp_map(name):
    """norm -> display map of the drug itself + its components (R49)."""
    out = {_norm(name): name}
    for comp in (_entry(name) or {}).get("components") or []:
        out[_norm(comp)] = comp
    return out
def check_interactions(new_drug, patient_meds=None, allergies=None, prescribed=None):
    """Alerts {severity, message_en, message_ar, drug_a, drug_b}: new drug vs patient meds + prescribed, plus allergy alerts only for a genuine relation (round-29; see _allergy_relation). R49 adds a duplicate-ingredient check over component sets."""
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
                    alerts.append({"severity": e["severity"], "message_en": e["message_en"], "message_ar": e["message_ar"], "drug_a": e["drug_a"], "drug_b": e["drug_b"]})
    new_map, dup_seen = _comp_map(new_drug), set()
    for other in others:
        if _norm(other) == _norm(new_drug):
            continue
        omap = _comp_map(other)
        for k in sorted(set(new_map) & set(omap)):
            if (k, _norm(other)) in dup_seen:
                continue
            dup_seen.add((k, _norm(other)))
            comp = new_map.get(k, omap.get(k))
            alerts.append({"severity": "moderate",
                "message_en": f"Duplicate ingredient: {comp} in both {new_drug} and {other}.",
                "message_ar": f"مكوّن مكرر: {comp} في كل من {new_drug} و {other}.",
                "drug_a": new_drug, "drug_b": other})
    for al in (allergies or []):
        a = _norm(al)
        if not a:
            continue
        pen = "penicillin" in a or "بنسلين" in a
        if pen and _norm(new_drug) in [_norm(x) for x in CLASSES["Penicillin"]]:
            alerts.append({"severity": "severe", "message_en": f"Known penicillin allergy - do NOT prescribe {new_drug}.", "message_ar": f"حساسية معروفة من البنسلين - لا تصف {new_drug}.", "drug_a": new_drug, "drug_b": "Penicillin allergy"})
        elif _allergy_relation(a, new_drug):
            alerts.append({"severity": "severe", "message_en": f"Known allergy to {al} - do NOT prescribe {new_drug}.", "message_ar": f"حساسية معروفة من {al} - لا تصف {new_drug}.", "drug_a": new_drug, "drug_b": al})
        elif ("sulfa" in a or "سلفا" in a) and "sulfamethoxazole" in _norm(new_drug):
            alerts.append({"severity": "severe", "message_en": "Known sulfa allergy - do NOT prescribe sulfamethoxazole.", "message_ar": "حساسية معروفة من السلفا - لا تصف السلفاميثوكسازول.", "drug_a": new_drug, "drug_b": "Sulfa allergy"})
    order = {"severe": 0, "moderate": 1, "mild": 2}
    return sorted(alerts, key=lambda x: order.get(x["severity"], 9))
def parse_list(text):
    return [x.strip() for x in str(text or "").replace("،", ",").split(",") if x.strip()]
