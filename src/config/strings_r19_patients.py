"""Round 19 patient strings (debtors-only filter, Job R19-E).

The "Debtors only" toggle button beside the patient list / search
controls. ONLY EN and AR dicts + a tiny tr() lookup, copied from
the round-18 modules: tr() reads this module first and falls back
to t(). The coordinator wiring in src.config.strings merges these
dicts into t() as well. Every key needs EN + AR.
"""
EN = {
    'patients.debtors_only': 'Debtors only',
    'patients.debtors_only_on': '✓ Debtors only',
}
AR = {
    'patients.debtors_only': 'المديونون فقط',
    'patients.debtors_only_on': '✓ المديونون فقط',
}


def tr(key, lang="en"):
    """Translated string for `key`: this module first, then t()."""
    d = AR if lang == "ar" else EN
    if key in d:
        return d[key]
    from src.config.strings import t
    return t(key, lang)
