"""Nationalities from src/data/countries.json (249 countries). <60 lines."""
import json
from pathlib import Path
from src.utils.searchable import filter_list
_DATA = Path(__file__).resolve().parent.parent / "data" / "countries.json"
_CACHE = None
# Common names that differ from the official country_en in the data.
ALIASES = {"turkey": "TR", "usa": "US", "america": "US", "uk": "GB",
    "britain": "GB", "england": "GB", "great britain": "GB",
    "russia": "RU", "south korea": "KR", "north korea": "KP",
    "czech republic": "CZ", "ivory coast": "CI", "cape verde": "CV",
    "swaziland": "SZ", "vietnam": "VN", "laos": "LA", "vatican": "VA",
    "palestine": "PS", "taiwan": "TW", "syria": "SY", "iran": "IR"}
# Legacy v1/v2 stored feminine Arabic adjectives (e.g. سورية); map to EN.
LEGACY_AR = {"سورية": "Syrian", "لبنانية": "Lebanese", "أردنية": "Jordanian",
    "عراقية": "Iraqi", "مصرية": "Egyptian", "سعودية": "Saudi", "إماراتية": "Emirati",
    "كويتية": "Kuwaiti", "قطرية": "Qatari", "بحرينية": "Bahraini", "عمانية": "Omani",
    "يمنية": "Yemeni", "فلسطينية": "Palestinian", "تركية": "Turkish",
    "إيرانية": "Iranian", "أمريكية": "American", "كندية": "Canadian",
    "ألمانية": "German", "فرنسية": "French", "بريطانية": "British",
    "روسية": "Russian", "أخرى": "Other"}

def _load():
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(_DATA.read_text(encoding="utf-8"))
    return _CACHE

def list_nationalities():
    return _load()

def search_nationalities(query):
    hits = filter_list(_load(), query, ["code", "country_en", "country_ar",
                                        "nationality_en", "nationality_ar"])
    q = (query or "").strip().lower()
    if q in ALIASES:
        extra = [i for i in _load() if i["code"] == ALIASES[q] and i not in hits]
        hits = extra + hits
    return hits

def _resolve_lang(lang):
    """Explicit 'en'/'ar' wins; otherwise the app language setting."""
    if lang in ("en", "ar"):
        return lang
    try:
        from src.models.database import get_setting
        return "ar" if (get_setting("language", "en") or "en") == "ar" else "en"
    except Exception:
        return "en"

def _legacy_display(item):
    """Pre-round-17 bilingual form, kept ONLY so _find() can parse
    values shown by older builds. Never displayed any more."""
    return f"{item['nationality_en']} / {item['nationality_ar']}"

def display(item, lang=None):
    """One nationality in ONE language (round 17 language purity):
    'Syrian' (en) or 'سوري' (ar) — mirrors utils/currencies.display."""
    return item["nationality_ar"] if _resolve_lang(lang) == "ar" else item["nationality_en"]

def _find(value):
    v = (value or "").strip()
    for it in _load():
        if v in (it["code"], it["nationality_en"], it["nationality_ar"],
                 it["country_en"], it["country_ar"],
                 display(it, "en"), display(it, "ar"), _legacy_display(it)):
            return it
    return None

def display_for(value, lang=None):
    """Any stored form (EN, AR, legacy feminine, code) -> the name in
    ONE language: 'Syrian' (en) or 'سوري' (ar)."""
    if (value or "").strip() in ("Other", "أخرى"):
        return "أخرى" if _resolve_lang(lang) == "ar" else "Other"
    it = _find(value)
    if it:
        return display(it, lang)
    if value in LEGACY_AR:
        return display_for(LEGACY_AR[value], lang)
    return display_for("Syrian", lang)

def nationality_en_for(value):
    """Display/legacy/AR value -> stored English nationality (DB value)."""
    it = _find(value)
    if it:
        return it["nationality_en"]
    if value in LEGACY_AR:
        return LEGACY_AR[value]
    if " / " in str(value):
        return str(value).split(" / ")[0].strip()
    return (value or "Syrian").strip()
