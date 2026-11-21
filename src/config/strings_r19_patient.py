"""Round 19 patient strings (2026-11-14) -- Job R19-A.

Diseases-field Templates button in the patient form + the picker
category labels for the new 'disease' and 'referral' phrase
categories. ONLY EN and AR dicts + a tiny tr() lookup, copied from
strings_r16_patients / strings_r18_patients: tr() reads this module
first and falls back to t(), so labels render in both languages
before and after strings.py merges this module into t(). Every key
needs EN + AR; each value is ONE language only (total purity).
"""
EN = {
    'r19.diseases_templates_btn': '📋 Templates',
    'dlg.cat_disease': 'disease',
    'dlg.cat_referral': 'referral',
    'dlg.cat_allergy': 'allergy',
}
AR = {
    'r19.diseases_templates_btn': '📋 قوالب',
    'dlg.cat_disease': 'الأمراض',
    'dlg.cat_referral': 'التحويل',
    'dlg.cat_allergy': 'الحساسية',
}


def tr(key, lang="en"):
    """Translated string for `key`: this module first, then t()."""
    d = AR if lang == "ar" else EN
    if key in d:
        return d[key]
    from src.config.strings import t
    return t(key, lang)
