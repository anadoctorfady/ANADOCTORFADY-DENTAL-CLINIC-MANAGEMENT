"""Dental specialty seed phrases (EN+AR) from src/data/specialties.json.
8 built-in specialties x 4 categories. Graceful fallback: [] if the
JSON is missing/unreadable. Category names accept singular or plural
(symptom/symptoms, procedure/procedures). <120 lines."""
import json
from pathlib import Path
FILE = Path(__file__).resolve().parent.parent / "data" / "specialties.json"
_CACHE = None
_CATS = {"complaint": "complaint", "symptom": "symptoms",
         "symptoms": "symptoms", "diagnosis": "diagnosis",
         "procedure": "procedures", "procedures": "procedures"}
def load_specialties():
    """List of specialty dicts: {id, name_en, name_ar, phrases{cat:[{en,ar}]}}."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        _CACHE = data.get("specialties", []) if isinstance(data, dict) else data
    except Exception:
        _CACHE = []
    return _CACHE
def list_specialties():
    """[{id, name_en, name_ar}] for the 8 built-in specialties."""
    return [{"id": s.get("id", ""), "name_en": s.get("name_en", ""),
             "name_ar": s.get("name_ar", "")} for s in load_specialties()]
def phrases_for(specialty_id, category):
    """[(en, ar)] seed phrases for a specialty + category.
    Unknown specialty falls back to 'general'; unknown category -> []."""
    cat = _CATS.get((category or "").lower(), "")
    if not cat:
        return []
    for s in load_specialties():
        if s.get("id") == specialty_id:
            items = (s.get("phrases") or {}).get(cat, [])
            return [(p.get("en", ""), p.get("ar", "")) for p in items
                    if p.get("en") or p.get("ar")]
    if specialty_id != "general":
        return phrases_for("general", category)
    return []

def all_phrases(category):
    """COMBINED pool (Item 5, 2026-11-08): seed phrases for ONE category
    from ALL 8 specialties merged, deduped, in specialty order. The
    specialty picker is gone, so the template picker searches this one
    pool instead of one specialty at a time. Returns [(en, ar)]."""
    cat = _CATS.get((category or "").lower(), "")
    if not cat:
        return []
    out, seen = [], set()
    for s in load_specialties():
        for en, ar in phrases_for(s.get("id", ""), category):
            key = (en.strip().lower(), ar.strip())
            if key not in seen and (en or ar):
                seen.add(key)
                out.append((en, ar))
    return out

def combined_count(category):
    """How many phrases the combined pool holds for a category."""
    return len(all_phrases(category))
def specialty_name(specialty_id, language="en"):
    """Display name of a built-in specialty ('general' if unknown)."""
    for s in load_specialties():
        if s.get("id") == specialty_id:
            return s.get("name_ar" if language == "ar" else "name_en", "")
    return specialty_name("general", language) if specialty_id != "general" else ""
