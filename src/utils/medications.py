"""Medications: src/data/medications.json (315 seed drugs, all classes)
+ user-added drugs in src/data/user_medications.json (Item 6, 2026-11-08) —
added from the prescription section, survive restarts, searched alongside."""
import json
from pathlib import Path
from src.utils.searchable import filter_list
_DATA = Path(__file__).resolve().parent.parent / "data" / "medications.json"
_USER = Path(__file__).resolve().parent.parent / "data" / "user_medications.json"
_CACHE = None

def _load():
    global _CACHE
    if _CACHE is None:
        items = list(json.loads(_DATA.read_text(encoding="utf-8")))
        try:
            user = json.loads(_USER.read_text(encoding="utf-8"))
        except Exception:
            user = []
        seen = {str(m.get("generic_en", "")).lower() for m in items}
        for m in user if isinstance(user, list) else []:
            if str(m.get("generic_en", "")).lower() not in seen:
                items.append(m)
                seen.add(str(m.get("generic_en", "")).lower())
        _CACHE = items
        try: from src.models.interactions import invalidate_drug_caches; invalidate_drug_caches()  # R30
        except Exception: pass
    return _CACHE

def list_medications(): return _load()

def _ix_drop():
    from src.models.interactions import invalidate_drug_caches; invalidate_drug_caches()

def list_user_medications():
    """Drugs the doctor added (from the user file only)."""
    try:
        data = json.loads(_USER.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []

def _lang(lang):
    """Round 17: messages are single-language; lang=None -> app language."""
    if lang in ("en", "ar"): return lang
    try:
        from src.models.database import get_setting
        return "ar" if (get_setting("language", "en") or "en") == "ar" else "en"
    except Exception:
        return "en"

def add_user_medication(item, lang=None):
    """Persist one user drug. item: generic_en (required), generic_ar,
    brand_en, brand_ar, category, form, strength, class. Returns
    (ok, message); duplicate generic_en (seed or user) is refused."""
    global _CACHE
    generic = str((item or {}).get("generic_en", "")).strip()
    ar = _lang(lang) == "ar"
    if len(generic) < 2:
        return False, ("أدخل الاسم العلمي للدواء" if ar else "Enter the drug's scientific (generic) name")
    if get_medication(generic) is not None:
        return False, (f"موجود مسبقاً: {generic}" if ar else f"Already in the list: {generic}")
    entry = {"generic_en": generic,
             "generic_ar": str(item.get("generic_ar", "")).strip(),
             "brand_en": str(item.get("brand_en", "")).strip(),
             "brand_ar": str(item.get("brand_ar", "")).strip(),
             "category": str(item.get("category", "")).strip() or "Other",
             "form": str(item.get("form", "")).strip(),
             "strength": str(item.get("strength", "")).strip(),
             "class": str(item.get("class", "")).strip()}
    user = list_user_medications()
    user.append(entry)
    _USER.parent.mkdir(parents=True, exist_ok=True)
    _USER.write_text(json.dumps(user, ensure_ascii=False, indent=1), encoding="utf-8")
    _CACHE = None  # reload merges the new drug on the next lookup
    _ix_drop()  # R30: allergy caches snapshot the drug list — drop them now
    return True, (f"تمت إضافة {generic}" if ar else f"Added: {generic}")

def remove_user_medication(generic):
    """Delete a user-added drug (seed drugs can never be deleted)."""
    global _CACHE
    g = str(generic or "").strip().lower()
    user = [m for m in list_user_medications()
            if str(m.get("generic_en", "")).lower() != g]
    if len(user) == len(list_user_medications()):
        return False
    _USER.write_text(json.dumps(user, ensure_ascii=False, indent=1), encoding="utf-8")
    _CACHE = None
    _ix_drop()  # R30: same staleness guard as add_user_medication
    return True

def search_medications(query):
    """Match generic/brand EN+AR, category."""
    # generic (scientific) name first, then brand, EN+AR, category/class
    return filter_list(_load(), query, ["generic_en", "generic_ar",
        "brand_en", "brand_ar", "category", "class"])

def get_medication(generic):
    g = (generic or "").strip().lower()
    for m in _load():
        if g in (m["generic_en"].lower(), m["generic_ar"],
                 m["brand_en"].lower(), m["brand_ar"]):
            return m
    return None

def list_by_category(category):
    if not category or category == "All":
        return _load()
    return [m for m in _load() if m.get("category") == category]

def categories():
    seen = []
    for m in _load():
        if m.get("category") not in seen:
            seen.append(m.get("category"))
    return ["All"] + sorted(seen)

def display(item, lang=None):
    """Round 24 item 7: the drug name in ONE language -- the app
    language (lang=None resolves it from the setting, like _lang).
    EN: "Amoxicillin (Amoxil) — Capsule 500 mg". AR: the Arabic
    generic only, "أموكسيسيلين — Capsule 500 mg" (generic_ar falls
    back to generic_en when empty; form/strength keep their standard
    Latin units). The old bilingual "EN (Brand) / AR" form is no
    longer produced -- generic_for() still parses it (see below).
    Round 23 wiring kept: the " — Form Strength" suffix has NO
    parentheses on purpose, so the EN "Name (Brand)" prefix and the
    dose auto-fill parsing stay byte-identical."""
    dose = " ".join(p for p in (str(item.get("form", "")).strip(),
                                str(item.get("strength", "")).strip()) if p)
    if _lang(lang) == "ar":
        base = str(item.get("generic_ar", "") or "").strip() \
            or item["generic_en"]
    else:
        brand = str(item.get("brand_en", "") or "").strip()
        base = f"{item['generic_en']} ({brand})" if brand \
            else item["generic_en"]
    return f"{base} — {dose}" if dose else base

def strength_for(generic):
    """Stored strength for a generic name ("500 mg", "1 g", "0.3%");
    "" when the drug is unknown or has no stored strength."""
    m = get_medication(generic)
    return str(m.get("strength", "")).strip() if m else ""

def _match(field, value):
    """First drug whose `field` equals value (case-insensitive)."""
    v = (value or "").strip()
    if not v:
        return None
    for m in _load():
        fv = str(m.get(field, "") or "")
        if fv and (fv == v or fv.lower() == v.lower()):
            return m
    return None

def _resolve_head(head):
    """One display head (dose suffix already stripped) -> drug, by
    LOOKUP in a fixed order: exact generic_en, exact generic_ar,
    the X of an "X (Y)" head as generic_en, brand_en, brand_ar
    (the "(Y)" part itself is also tried as a brand)."""
    for field in ("generic_en", "generic_ar"):
        m = _match(field, head)
        if m:
            return m
    outer, inner = head, ""
    if " (" in head:
        outer = head.split(" (")[0].strip()
        inner = head.split(" (", 1)[1].strip().rstrip(")").strip()
        m = _match("generic_en", outer)
        if m:
            return m
    for field in ("brand_en", "brand_ar"):
        m = _match(field, head) or (_match(field, inner) if inner else None)
        if m:
            return m
    return None

def generic_for(value):
    """Display (EN, AR or legacy bilingual) / brand / generic ->
    canonical generic_en. Resolution is by lookup (_resolve_head),
    never by position alone; only a wholly unknown drug falls back
    to the old head-before-" (" behaviour."""
    v = (value or "").strip()
    if not v:
        return ""
    head = v.split(" — ")[0].strip()  # drop the " — Form Strength"
    heads = []
    if " / " in head:  # legacy bilingual: "EN (Brand) / AR"
        heads += [p.strip() for p in head.split(" / ")]
    heads.append(head)
    for h in heads:
        m = _resolve_head(h) if h else None
        if m:
            return m["generic_en"]
    fallback = heads[0]
    return fallback.split(" (")[0].strip() if " (" in fallback else fallback

def display_for(generic, lang=None):
    m = get_medication(generic)
    return display(m, lang) if m else (generic or "")
