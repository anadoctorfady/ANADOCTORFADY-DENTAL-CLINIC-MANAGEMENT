"""Round 19 (item 11) referral strings: the "Refer patient"
button, the refer dialog (internal doctor selector / external
name, templates note) and the Referrals history tab.

Same pattern as strings_r18_patients.py: ONLY EN and AR dicts +
a tiny tr() lookup; tr() reads this module first and falls back
to t(), so labels render before and after the coordinator merges
this module into src.config.strings. Every key needs EN + AR;
each value is ONE language only (total language purity).
{patient} is the open patient's full name, {fid} a file number.
"""
EN = {
    'refer.btn': '➡️ Refer patient',
    'refer.title': 'Refer patient — {patient}',
    'refer.internal': 'Clinic doctor',
    'refer.external_check': 'External doctor (not in the clinic)',
    'refer.external_name': 'External doctor name',
    'refer.note': 'Referral note',
    'refer.templates_btn': '📋 Templates',
    'refer.save_btn': '💾 Save referral',
    'refer.cancel_btn': 'Cancel',
    'refer.error_title': 'Cannot refer',
    'refer.no_doctor': 'Choose a clinic doctor or type an external doctor name first.',
    'refer.saved_title': 'Referral saved',
    'refer.saved_msg': 'Patient referred to {doctor}.',
    'refer.hist_tab': 'Referrals',
    'refer.col_date': 'Date',
    'refer.col_to': 'Referred to',
    'refer.col_from': 'From',
    'refer.col_note': 'Note',
    # Round 24 (item 1): referral printing -- dialog/section Print
    # buttons, the saved confirmation, and the PDF/preview labels.
    'refer.print_btn': '🖨 Print referral',
    'refer.close_btn': 'Close',
    'refer.saved_status': '✓ Referral saved — you can print it now.',
    'refer.pdf_title': 'Patient Referral',
    'refer.pdf_patient': 'Patient',
    'refer.pdf_file': 'File Number',
    'refer.pdf_date': 'Referral date',
    'refer.pdf_from': 'Referring doctor',
    'refer.pdf_to': 'Referred to',
    'refer.pdf_reason': 'Reason / notes',
    'refer.pdf_no_note': 'No note recorded.',
    'refer.pdf_signature': 'Referring doctor signature',
}
AR = {
    'refer.btn': '➡️ تحويل المريض',
    'refer.title': 'تحويل المريض — {patient}',
    'refer.internal': 'طبيب في المركز',
    'refer.external_check': 'طبيب خارجي (ليس في المركز)',
    'refer.external_name': 'اسم الطبيب الخارجي',
    'refer.note': 'ملاحظة التحويل',
    'refer.templates_btn': '📋 القوالب',
    'refer.save_btn': '💾 حفظ التحويل',
    'refer.cancel_btn': 'إلغاء',
    'refer.error_title': 'تعذّر التحويل',
    'refer.no_doctor': 'اختر طبيباً في المركز أو اكتب اسم طبيب خارجي أولاً.',
    'refer.saved_title': 'تم حفظ التحويل',
    'refer.saved_msg': 'تم تحويل المريض إلى {doctor}.',
    'refer.hist_tab': 'التحويلات',
    'refer.col_date': 'التاريخ',
    'refer.col_to': 'محال إلى',
    'refer.col_from': 'من',
    'refer.col_note': 'الملاحظة',
    'refer.print_btn': '🖨 طباعة التحويل',
    'refer.close_btn': 'إغلاق',
    'refer.saved_status': '✓ تم حفظ التحويل — يمكنك طباعته الآن.',
    'refer.pdf_title': 'تحويل مريض',
    'refer.pdf_patient': 'المريض',
    'refer.pdf_file': 'رقم الملف',
    'refer.pdf_date': 'تاريخ التحويل',
    'refer.pdf_from': 'الطبيب المحوِّل',
    'refer.pdf_to': 'محال إلى',
    'refer.pdf_reason': 'سبب التحويل / ملاحظات',
    'refer.pdf_no_note': 'لا توجد ملاحظة.',
    'refer.pdf_signature': 'توقيع الطبيب المحوِّل',
}


def tr(key, lang="en"):
    """Translated string for `key`: this module first, then t()."""
    d = AR if lang == "ar" else EN
    if key in d:
        return d[key]
    from src.config.strings import t
    return t(key, lang)
