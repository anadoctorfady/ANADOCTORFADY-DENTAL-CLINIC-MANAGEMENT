"""Round 15 clinical strings (2026-11-10).

Clinical tables restyle (2x2 grid) + right-side panels. ONLY EN and
AR dicts -- nothing else. Merged into src.config.strings (t()) by
strings.py (coordinator wires the merge); UI code reads them via
src.ui.clinical_table_style.r15_t(), which prefers these dicts and
falls back to t(), so the UI is correct before and after wiring.
Every key needs EN + AR. Placeholders: {date}, {what}, {amt}, {pid},
{doctor}, {drugs}, {label}.
"""
EN = {
    'clinical.symptoms_title': 'Symptoms', 'r15.panels.meds_title': 'Health — Medicines & Allergies',
    'r15.panels.payments_title': 'Recent Payments', 'r15.panels.rx_title': 'Prescriptions',
    'r15.panels.proc_title': 'Therapeutic Procedures',
    'r15.panels.none': 'None', 'r15.panels.none_meds': 'No medicines or allergies recorded',
    'r15.panels.none_payments': 'No payments yet', 'r15.panels.none_rx': 'No prescriptions yet',
    'r15.panels.none_proc': 'No procedures yet', 'r15.panels.proc_fmt': '{date} — {what}: {proc}',
    'r15.panels.no_patient': 'Select a patient first', 'r15.panels.meds_label': 'Medicines:',
    'r15.panels.allergies_label': 'Allergies:', 'r15.panels.paid_fmt': '{date} — {what}: paid {amt}',
    'r15.panels.rx_fmt': '#{pid} • {date} • {doctor}: {drugs}', 'r15.panels.tooth_fmt': 'Tooth {teeth}',
    'r15.panels.visit': 'Visit',
}
AR = {
    'clinical.symptoms_title': 'الأعراض', 'r15.panels.meds_title': 'الصحة — الأدوية والحساسية',
    'r15.panels.payments_title': 'الدفعات الأخيرة', 'r15.panels.rx_title': 'الوصفات الطبية',
    'r15.panels.proc_title': 'الإجراءات العلاجية',
    'r15.panels.none': 'لا يوجد', 'r15.panels.none_meds': 'لا توجد أدوية أو حساسية مسجلة',
    'r15.panels.none_payments': 'لا توجد دفعات بعد', 'r15.panels.none_rx': 'لا توجد وصفات بعد',
    'r15.panels.none_proc': 'لا توجد إجراءات بعد', 'r15.panels.proc_fmt': '{date} — {what}: {proc}',
    'r15.panels.no_patient': 'اختر مريضاً أولاً', 'r15.panels.meds_label': 'الأدوية:',
    'r15.panels.allergies_label': 'الحساسية:', 'r15.panels.paid_fmt': '{date} — {what}: المدفوع {amt}',
    'r15.panels.rx_fmt': '#{pid} • {date} • {doctor}: {drugs}', 'r15.panels.tooth_fmt': 'السن {teeth}',
    'r15.panels.visit': 'زيارة',
}
