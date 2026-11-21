"""Round 30 strings: Add New Drug class picker + unclassified
user-drug notice (Worker C).

ONLY EN and AR dicts plus the r30_t() lookup -- nothing else.
Merged into src.config.strings (t()) by strings.py (coordinator
wires the merge); UI code reads them via r30_t(), which prefers
these dicts and falls back to t(), so the UI is correct before
and after wiring. Every key needs EN + AR, single language
per value. Class tokens themselves are Latin data tokens and
are never translated."""
from src.config.strings import t

EN = {
    "dlg.ad_class": "Drug class (for interaction checks)",
    "dlg.ad_class_none": "(No class)",
    "dlg.ad_class_note": "Without a class, this drug cannot be "
        "checked for interactions or diseases — only exact-name "
        "allergy matches will be found.",
    "rx.unclassified_info": "This drug has no recorded class, so "
        "interaction and disease checks are limited to name "
        "matches only.",
}

AR = {
    "dlg.ad_class": "الفئة الدوائية (لفحص التداخلات)",
    "dlg.ad_class_none": "(بدون فئة)",
    "dlg.ad_class_note": "بدون فئة دوائية لا يمكن فحص هذا الدواء "
        "ضد التداخلات أو الأمراض — ستُكتشف فقط مطابقات الحساسية "
        "بالاسم الدقيق.",
    "rx.unclassified_info": "هذا الدواء ليس له فئة مسجلة، لذا "
        "يقتصر فحص التداخلات والأمراض على مطابقة الاسم فقط.",
}


def r30_t(key, lang="en"):
    """Round-30 string: prefer this module's dicts (the coordinator
    wires them into t() later); fall back to t() meanwhile."""
    d = AR if lang == "ar" else EN
    return d.get(key) or t(key, lang)
