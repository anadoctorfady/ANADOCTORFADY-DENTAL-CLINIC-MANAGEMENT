"""Round 19 finance strings (per-currency view, Job R19-E).

Finance tab currency selector + clinical per-currency breakdown.
ONLY EN and AR dicts + a tiny tr() lookup, copied from the round-18
modules: tr() reads this module first and falls back to t(). The
coordinator wiring in src.config.strings merges these dicts into
t() as well. Currency codes (SYP, USD, ...) are data, never
translated. Every key needs EN + AR.
"""
EN = {
    'fincur.selector_label': 'Currency:',
    'fincur.all': 'All currencies',
    'fincur.raw_note': 'Raw totals in {cur} (no conversion)',
    'fincur.breakdown_title': 'Per-currency breakdown',
    'fincur.patient_line': '{cur}: Total {total} · Paid {paid} · Remaining {rem}',
}
AR = {
    'fincur.selector_label': 'العملة:',
    'fincur.all': 'كل العملات',
    'fincur.raw_note': 'مجاميع خام بـ {cur} (بدون تحويل)',
    'fincur.breakdown_title': 'التفصيل حسب العملة',
    'fincur.patient_line': '{cur}: الإجمالي {total} · المدفوع {paid} · المتبقي {rem}',
}


def tr(key, lang="en"):
    """Translated string for `key`: this module first, then t()."""
    d = AR if lang == "ar" else EN
    if key in d:
        return d[key]
    from src.config.strings import t
    return t(key, lang)
