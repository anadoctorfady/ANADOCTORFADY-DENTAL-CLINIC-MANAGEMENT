"""Round 18 patient strings (2026-11-14) -- worker W2.

Patient info block + Edit/Delete (soft, admin-only) in the shell's
left column, and the Advanced Search grandfather field. ONLY EN and
AR dicts + a tiny tr() lookup, copied from strings_r16_patients:
tr() reads this module first and falls back to t(), so the labels
render in both languages before the coordinator merges this module
into src.config.strings. Every key needs EN + AR. {name} is the
patient's full name, {fid} a file number.
"""
EN = {
    'search.grandfather': 'Grandfather',
    'patient_info.title': 'Patient info',
    'patient_info.name': 'Name',
    'patient_info.father': "Father",
    'patient_info.grandfather': 'Grandfather',
    'patient_info.family': 'Family',
    'patient_info.birth': 'Birth',
    'patient_info.age': 'Age',
    'patient_info.birth_date': 'Birth date',
    'patient_info.hijri': 'Hijri',
    'patient_info.age_fmt': '{y} years, {m} months, {d} days',
    'patient_info.mobile1': 'Mobile 1',
    'patient_info.mobile2': 'Mobile 2',
    'patient_info.emergency': 'Emergency phone',
    'patient_info.address': 'Address',
    'patient_info.nationality': 'Nationality',
    'patient_info.diseases': 'Diseases',
    'patient_info.meds': 'Current medications',
    'patient_info.allergies': 'Allergies',
    'patient_info.balance': 'Balance',
    'patient_info.adherence': 'Appointments',
    'patient.edit_btn': '✏️ Edit',
    'patient.delete_btn': '🗑 Delete',
    'patient.edit_title': 'Edit patient — file #{fid}',
    'patient.delete_title': 'Delete patient',
    'patient.delete_confirm': ('Delete patient {name}?\n\n'
        'The patient will be hidden from the list and search, but all '
        'treatments, prescriptions, scans and financial records are '
        'KEPT in the database. This cannot be undone from the app.'),
    'patient.delete_admin_only': 'Only the admin can delete a patient.',
    'patient.deleted_msg': 'Patient {name} was deleted (hidden). '
                           'Treatments and financials are preserved.',
}
AR = {
    'search.grandfather': 'اسم الجد',
    'patient_info.title': 'معلومات المريض',
    'patient_info.name': 'الاسم',
    'patient_info.father': 'الأب',
    'patient_info.grandfather': 'الجد',
    'patient_info.family': 'الكنية',
    'patient_info.birth': 'الولادة',
    'patient_info.age': 'العمر',
    'patient_info.birth_date': 'تاريخ الميلاد',
    'patient_info.hijri': 'الهجري',
    'patient_info.age_fmt': '{y} سنة، {m} شهر، {d} يوم',
    'patient_info.mobile1': 'الجوال 1',
    'patient_info.mobile2': 'الجوال 2',
    'patient_info.emergency': 'هاتف الطوارئ',
    'patient_info.address': 'العنوان',
    'patient_info.nationality': 'الجنسية',
    'patient_info.diseases': 'الأمراض',
    'patient_info.meds': 'الأدوية الحالية',
    'patient_info.allergies': 'الحساسية',
    'patient_info.balance': 'الرصيد',
    'patient_info.adherence': 'المواعيد',
    'patient.edit_btn': '✏️ تعديل',
    'patient.delete_btn': '🗑 حذف',
    'patient.edit_title': 'تعديل المريض — ملف رقم {fid}',
    'patient.delete_title': 'حذف المريض',
    'patient.delete_confirm': ('حذف المريض {name}؟\n\n'
        'سيختفي المريض من القائمة والبحث، لكن جميع المعالجات والوصفات '
        'والصور والسجلات المالية ستبقى محفوظة في قاعدة البيانات. '
        'لا يمكن التراجع عن هذا من داخل التطبيق.'),
    'patient.delete_admin_only': 'يمكن للمدير فقط حذف مريض.',
    'patient.deleted_msg': 'تم حذف المريض {name} (إخفاؤه). '
                           'المعالجات والسجلات المالية محفوظة.',
}


def tr(key, lang="en"):
    """Translated string for `key`: this module first, then t()."""
    d = AR if lang == "ar" else EN
    if key in d:
        return d[key]
    from src.config.strings import t
    return t(key, lang)
