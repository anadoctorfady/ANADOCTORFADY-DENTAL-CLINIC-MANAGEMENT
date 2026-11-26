"""Drug-DISEASE caution checker (round 28) -- the third alert
dimension beside drug-drug interactions and allergies. Curated
aid only, NOT a substitute for clinical judgment (same disclaimer
as models.interactions). Data: data/drug_diseases.json -- 26
canonical conditions with EN/AR synonyms (the round-19 disease
templates included verbatim), class-level rules keyed on the
medications.json `class` token, drug-specific exceptions, and a
review manifest covering every class, so coverage of all 315
drugs is assertable: each drug is covered by its class rules, by
a drug-specific rule, or its class was reviewed with no major
disease caution (no_rule_classes)."""
import json
from pathlib import Path
from src.models.phrases import normalize_search_text as _nz
_DATA = Path(__file__).resolve().parent.parent / "data" / "drug_diseases.json"
_CACHE = None
_ORDER = {"severe": 0, "moderate": 1, "mild": 2}

def _load():
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(_DATA.read_text(encoding="utf-8"))
    return _CACHE

def conditions():
    return _load()["conditions"]

def _synonyms(cond):
    return ([cond["en"], cond["ar"]] + list(cond.get("synonyms_en", []))
            + list(cond.get("synonyms_ar", [])))

def match_conditions(diseases):
    """Map free-text diseases (EN/AR, str or list) to canonical
    condition keys via substring match on normalized text (the
    round-21 hamza-insensitive normalizer, applied to BOTH the
    patient text and every synonym)."""
    if isinstance(diseases, (list, tuple)):
        text = ", ".join(str(x) for x in diseases if x)
    else:
        text = str(diseases or "")
    text_n = _nz(text)
    if not text_n:
        return set()
    found = set()
    for key, cond in conditions().items():
        for syn in _synonyms(cond):
            sn = _nz(syn)
            if sn and sn in text_n:
                found.add(key)
                break
    return found

def _med(generic):
    try:
        from src.utils.medications import get_medication
        return get_medication(generic) or {}
    except Exception:
        return {}

def _classes_and_names(generic):
    """R49: (classes, names) for a drug -- for a combo, the entry's
    class plus every component's class (component entry class and
    stored component_classes token), and the generic plus every
    component name. Singles return just their own class/name."""
    med = _med(generic)
    classes, names = [], [generic]
    def _add(t):
        if t and t not in classes:
            classes.append(t)
    _add(med.get("class") or "")
    tokens = med.get("component_classes") or []
    for i, comp in enumerate(med.get("components") or []):
        names.append(comp)
        _add(_med(comp).get("class") or "")
        if i < len(tokens):
            _add(tokens[i])
    return classes, names

def check_drug_diseases(generic, diseases):
    """Alerts {severity, message_en, message_ar, drug_a, drug_b}
    in the SAME shape as models.interactions.check_interactions.
    R49 merge semantics: per condition the MAXIMUM severity wins
    (severe < moderate < mild); on a severity tie the drug-specific
    rule's note is preferred over the class rule's. Rules are
    evaluated for the drug's class AND every component class, and
    for the generic AND each component name (combos). For singles
    this reduces to the old behaviour except that a severer class
    rule is no longer downgraded by a milder drug rule."""
    conds = match_conditions(diseases)
    if not conds or not generic:
        return []
    med = _med(generic)
    gen_ar = med.get("generic_ar") or generic
    classes, names = _classes_and_names(generic)
    hits = {}  # condition -> (severity, note_en, note_ar, specific?)
    def _offer(r, specific):
        cur = hits.get(r["condition"])
        if cur is None or _ORDER[r["severity"]] < _ORDER[cur[0]] or (
                _ORDER[r["severity"]] == _ORDER[cur[0]]
                and specific and not cur[3]):
            hits[r["condition"]] = (r["severity"], r["note_en"],
                                    r["note_ar"], specific)
    for r in _load()["class_rules"]:
        if r["class"] in classes and r["condition"] in conds:
            _offer(r, False)
    for r in _load()["drug_rules"]:
        if r["drug"] in names and r["condition"] in conds:
            _offer(r, True)
    alerts = []
    for key, (sev, note_en, note_ar, _spec) in hits.items():
        cond = conditions()[key]
        alerts.append({"severity": sev,
            "message_en": f"{generic} + {cond['en']}: {note_en}",
            "message_ar": f"{gen_ar} + {cond['ar']}: {note_ar}",
            "drug_a": generic, "drug_b": cond["en"]})
    return sorted(alerts, key=lambda x: _ORDER.get(x["severity"], 9))

def review_outcome(generic):
    """Per-drug audit outcome: ('specific', drug) if the drug has
    its own rule, ('class', cls) if its class carries rules,
    ('reviewed', cls) if its class was reviewed with no major
    disease caution, else ('unreviewed', cls). R49: a combo is
    covered only if EVERY component class is covered/reviewed;
    otherwise ('unreviewed', offending class)."""
    data = _load()
    med = _med(generic)
    if med.get("components"):
        covered = {r["class"] for r in data["class_rules"]} | \
            set(data.get("no_rule_classes", [])) | \
            set(data.get("classes_reviewed", []))
        classes, _names = _classes_and_names(generic)
        for cls in classes:
            if cls not in covered:
                return ("unreviewed", cls)
        if any(r["drug"] == generic for r in data["drug_rules"]):
            return ("specific", generic)
        cls = med.get("class") or ""
        if any(r["class"] in classes for r in data["class_rules"]):
            return ("class", cls)
        return ("reviewed", cls)
    if any(r["drug"] == generic for r in data["drug_rules"]):
        return ("specific", generic)
    cls = med.get("class") or ""
    if any(r["class"] == cls for r in data["class_rules"]):
        return ("class", cls)
    if cls in data.get("no_rule_classes", []) or \
            cls in data.get("classes_reviewed", []):
        return ("reviewed", cls)
    return ("unreviewed", cls)
