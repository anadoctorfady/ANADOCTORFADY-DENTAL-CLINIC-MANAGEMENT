"""Round 16 prescriptions strings (2026-11-11).

Direct-print button for a prescription + print-preview fallback.
ONLY EN and AR dicts plus the rx16_t() lookup -- nothing else.
Merged into src.config.strings (t()) by strings.py (coordinator wires
the merge); UI code reads them via rx16_t(), which prefers these
dicts and falls back to t(), so the UI is correct before and after
wiring. Every key needs EN + AR, single language per value.
"""
from src.config.strings import t

EN = {
    "rx.print_direct": "🖨 Print Prescription",
    "rx.print_preview_title": "Prescription — Print Preview",
    "rx.print_no_preview": "Print preview is not available yet — the prescription PDF was saved instead:\n{out}",
    "rx.pdf_heading": "Prescription",
    "rx.pdf_patient": "Patient", "rx.pdf_file": "File #", "rx.pdf_date": "Date",
    "rx.pdf_doctor": "Doctor", "rx.pdf_age": "Age",
    "rx.pdf_drug": "Drug", "rx.pdf_dose": "Dose", "rx.pdf_frequency": "Frequency",
    "rx.pdf_duration": "Duration", "rx.pdf_instructions": "Instructions",
    "rx.pdf_notes": "Notes", "rx.pdf_days": "days",
    "rx.pdf_signature": "Doctor Signature",
    "rx.pdf_issued": "Issued",
    "rx.pdf_by": "By",
    "rx.pdf_developer": "the developer Dr Fady Abdulkafy Dadoush",
}

AR = {
    "rx.print_direct": "🖨 طباعة الوصفة",
    "rx.print_preview_title": "الوصفة الطبية — معاينة الطباعة",
    "rx.print_no_preview": "معاينة الطباعة غير متوفرة بعد — تم حفظ ملف الوصفة بدلاً من ذلك:\n{out}",
    "rx.pdf_heading": "وصفة طبية",
    "rx.pdf_patient": "المريض", "rx.pdf_file": "رقم الملف", "rx.pdf_date": "التاريخ",
    "rx.pdf_doctor": "الطبيب", "rx.pdf_age": "العمر",
    "rx.pdf_drug": "الدواء", "rx.pdf_dose": "الجرعة", "rx.pdf_frequency": "التكرار",
    "rx.pdf_duration": "المدة", "rx.pdf_instructions": "التعليمات",
    "rx.pdf_notes": "ملاحظات", "rx.pdf_days": "يوم",
    "rx.pdf_signature": "توقيع الطبيب",
    "rx.pdf_issued": "صدرت في",
    "rx.pdf_by": "بواسطة",
    "rx.pdf_developer": "المطور د. فادي عبد الكافي دعدوش",
}


def rx16_t(key, lang="en"):
    """Round-16 Rx string: prefer this module's dicts (the coordinator
    wires them into t() later); fall back to t() meanwhile."""
    d = AR if lang == "ar" else EN
    return d.get(key) or t(key, lang)
