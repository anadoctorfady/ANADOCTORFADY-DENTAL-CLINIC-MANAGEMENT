"""Round 18 (item 8) invoice strings: the patient invoice (detailed /
summary) + its print-preview kind control + the clinical "Print
invoice" button. Same pattern as strings_r16_print.py: this module is
standalone (inv_t()) until the coordinator merges EN/AR into
src/config/strings.py; invoice code imports inv_t() from HERE.
Single-language purity: EN holds no Arabic, AR holds no English
labels (the app name ANADOCTORFADY and currency codes are data, not
labels). <200 lines.
"""
EN = {
    "inv.title": "Invoice",
    "inv.detailed": "Detailed",
    "inv.summary": "Summary",
    "inv.kind": "Invoice type",
    "inv.print_invoice": "🧾 Print invoice",
    "inv.patient": "Patient",
    "inv.file_number": "File No.",
    "inv.issued": "Date of issue",
    "inv.total": "Total",
    "inv.paid": "Paid",
    "inv.remaining": "Remaining",
    "inv.payments_title": "Payments",
    "inv.col_datetime": "Date & time",
    "inv.col_amount": "Amount",
    "inv.col_for": "For",
    "inv.tooth": "Tooth {tooth}",
    "inv.general": "General payment",
    "inv.no_payments": "No payments recorded yet.",
    "inv.summary_note": "Summary invoice — totals only, no payment details.",
    "inv.select_patient": "Select a patient first!",
}
AR = {
    "inv.title": "فاتورة",
    "inv.detailed": "مفصّلة",
    "inv.summary": "ملخّص",
    "inv.kind": "نوع الفاتورة",
    "inv.print_invoice": "🧾 طباعة الفاتورة",
    "inv.patient": "المريض",
    "inv.file_number": "رقم الملف",
    "inv.issued": "تاريخ الإصدار",
    "inv.total": "المجموع",
    "inv.paid": "المدفوع",
    "inv.remaining": "المتبقي",
    "inv.payments_title": "الدفعات",
    "inv.col_datetime": "التاريخ والوقت",
    "inv.col_amount": "المبلغ",
    "inv.col_for": "مقابل",
    "inv.tooth": "السن {tooth}",
    "inv.general": "دفعة عامة",
    "inv.no_payments": "لا توجد دفعات مسجّلة بعد.",
    "inv.summary_note": "فاتورة ملخّصة — المجاميع فقط، دون تفاصيل الدفعات.",
    "inv.select_patient": "اختر مريضاً أولاً!",
}


def inv_t(key, lang="en"):
    """Translated invoice string; English fallback, then the key."""
    return (AR if lang == "ar" else EN).get(key, EN.get(key, key))
