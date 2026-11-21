"""Round 16 clinical strings (2026-11-11).

One save button, Health-panel diseases line, chart treated-tooth
legend, right-panel detail dialogs, one-line patient header. ONLY EN
and AR dicts + the r16_t() reader -- nothing else. The coordinator
merges these into src.config.strings (t()) later; UI code reads them
via r16_t(), which prefers these dicts and falls back to t(), so the
UI is correct before and after wiring. Every key needs EN + AR.
Placeholders: {age}, {n}, {date}, {what}, {paid}, {total}, {pid},
{doctor}, {drugs}, {drug}, {dose}, {freq}.
"""
from src.config.strings import t

EN = {
    'r16.save.visit': 'Save visit',
    'r16.panels.diseases_label': 'Diseases:',
    'r16.chart.legend': '✓ Treated tooth',
    'r16.panels.payment_detail_title': 'Payment details',
    'r16.panels.payment_detail_fmt': '{date} — {what}\nPaid: {paid} / Total: {total}',
    'r16.panels.rx_detail_title': 'Prescription #{pid}',
    'r16.panels.rx_detail_fmt': '{doctor} — {date}\n{drugs}',
    'r16.panels.rx_drug_fmt': '{drug} — {dose}, {freq}',
    'r16.header.patient_title': 'Patient',
    'r16.header.meta_fmt': '· {age} yrs · File #: {n}',
    'r16.header.meta_no_age_fmt': '· File #: {n}',
    'r16.header.meta_no_file_fmt': '· {age} yrs',
}

AR = {
    'r16.save.visit': 'حفظ الزيارة',
    'r16.panels.diseases_label': 'الأمراض:',
    'r16.chart.legend': '✓ سن تم علاجه',
    'r16.panels.payment_detail_title': 'تفاصيل الدفعة',
    'r16.panels.payment_detail_fmt': '{date} — {what}\nالمدفوع: {paid} / الإجمالي: {total}',
    'r16.panels.rx_detail_title': 'الوصفة رقم {pid}',
    'r16.panels.rx_detail_fmt': 'الطبيب {doctor} — {date}\n{drugs}',
    'r16.panels.rx_drug_fmt': '{drug} — {dose}، {freq}',
    'r16.header.patient_title': 'المريض',
    'r16.header.meta_fmt': '· {age} سنة · رقم الملف: {n}',
    'r16.header.meta_no_age_fmt': '· رقم الملف: {n}',
    'r16.header.meta_no_file_fmt': '· {age} سنة',
}


def r16_t(key, lang="en"):
    """Round-16 string: prefer this module's dicts, then EN, then t()."""
    d = AR if lang == "ar" else EN
    return d.get(key) or EN.get(key) or t(key, lang)
