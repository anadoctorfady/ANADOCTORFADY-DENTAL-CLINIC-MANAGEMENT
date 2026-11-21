"""Round 16 patient strings (2026-11-11) -- worker A (patients).

ONLY EN and AR dicts + a tiny tr() lookup. Merged into
src.config.strings (t()) by strings.py once the coordinator wires
the merge; until then tr() reads this module first and falls back
to t(), so the new labels already render in both languages.
Every key needs EN + AR. {fid} is the existing file number.
"""
EN = {
    'patient.diseases': 'Diseases (comma-separated)',
    'patient.err_duplicate': 'A patient with this name already exists — file #{fid}.',
    'patient.dup_open': 'Open the existing patient file #{fid}?',
    'patient.dup_title': 'Duplicate patient',
    'search.advanced': 'Advanced Search',
    'search.first': 'First name',
    'search.father': "Father's name",
    'search.family': 'Family name',
    'search.phone': 'Any phone',
    'search.btn': 'Search',
    'search.clear': 'Clear',
    'search.hint': 'List shows only search results (or the open patient).',
}
AR = {
    'patient.diseases': 'الأمراض (مفصولة بفاصلة)',
    'patient.err_duplicate': 'يوجد مريض بهذا الاسم مسبقاً — ملف رقم {fid}.',
    'patient.dup_open': 'فتح ملف المريض الموجود رقم {fid}؟',
    'patient.dup_title': 'مريض مكرر',
    'search.advanced': 'بحث متقدم',
    'search.first': 'الاسم الأول',
    'search.father': 'اسم الأب',
    'search.family': 'الكنية',
    'search.phone': 'أي رقم هاتف',
    'search.btn': 'بحث',
    'search.clear': 'مسح',
    'search.hint': 'القائمة تعرض نتائج البحث فقط (أو المريض المفتوح).',
}


def tr(key, lang="en"):
    """Translated string for `key`: this module first, then t()."""
    d = AR if lang == "ar" else EN
    if key in d:
        return d[key]
    from src.config.strings import t
    return t(key, lang)
