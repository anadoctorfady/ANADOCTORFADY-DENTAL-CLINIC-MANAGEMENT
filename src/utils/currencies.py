"""Currencies from src/data/currencies.json (178 ISO codes).

Round 17 (language purity): display strings are SINGLE-language —
'USD - US Dollar' in EN mode, 'USD - دولار أمريكي' in AR mode.
display()/display_for_code() take lang=None, which resolves to the
app language (the 'language' setting); callers that know their UI
language pass it explicitly. code_for()/_find() still parse the
LEGACY bilingual form 'USD - US Dollar / دولار أمريكي' (values
stored/shown before round 17) as well as both new single-language
forms, bare names and bare codes. <80 lines."""
import json
from pathlib import Path
_DATA = Path(__file__).resolve().parent.parent / "data" / "currencies.json"
_CACHE = None

def _load():
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(_DATA.read_text(encoding="utf-8"))
    return _CACHE

def _resolve_lang(lang):
    """Explicit 'en'/'ar' wins; otherwise the app language setting."""
    if lang in ("en", "ar"):
        return lang
    try:
        from src.models.database import get_setting
        return "ar" if (get_setting("language", "en") or "en") == "ar" else "en"
    except Exception:
        return "en"

def list_currencies():
    return _load()

def search_currencies(query):
    """Substring match on code / EN name / AR name / symbol."""
    q = (query or "").strip().lower()
    if not q:
        return list(_load())
    return [c for c in _load()
            if any(q in str(c.get(f, "") or "").lower()
                   for f in ("code", "name_en", "name_ar", "symbol"))]

def _legacy_display(item):
    """Pre-round-17 bilingual form, kept ONLY so code_for() can parse
    values stored/shown by older builds. Never displayed any more."""
    return f"{item['code']} - {item['name_en']} / {item['name_ar']}"

def display(item, lang=None):
    """One currency in ONE language: 'USD - US Dollar' (en) or
    'USD - دولار أمريكي' (ar)."""
    name = item["name_ar"] if _resolve_lang(lang) == "ar" else item["name_en"]
    return f"{item['code']} - {name}"

def _find(value):
    v = (value or "").strip()
    for c in _load():
        if v in (c["code"], c["name_en"], c["name_ar"],
                 display(c, "en"), display(c, "ar"), _legacy_display(c)):
            return c
    return None

def display_for_code(code, lang=None):
    """Any stored form (code, EN/AR name, legacy or new display) ->
    the single-language display for `lang` (default: app language)."""
    c = _find(code)
    return display(c, lang) if c else (code or "SYP").strip().upper()

def code_for(value):
    """Display / name / code -> ISO code. Parses the legacy bilingual
    display ('USD - US Dollar / دولار أمريكي'), both new
    single-language displays, bare EN/AR names and bare codes."""
    c = _find(value)
    if c:
        return c["code"]
    v = (value or "").strip()
    for sep in (" - ", " / "):
        if sep in v:
            v = v.split(sep)[0].strip()
            break
    return v.upper() if len(v) == 3 and v.isalpha() else (v or "SYP")
