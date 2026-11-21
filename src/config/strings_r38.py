"""Round 38 strings: payment entry / payments review / patient
credit / image viewer controls.

EN + AR dicts with a local reader (same pattern as
strings_r24_session): prefer these dicts, then EN, then t().
Placeholders: {amount}.
"""
from src.config.strings import t

EN = {
    "pay.entry_title": "Payment entry",
    "pay.amount": "Amount",
    "pay.date": "Date",
    "pay.note": "Note (optional)",
    "pay.bad_date": "The payment date must look like YYYY-MM-DD.",
    "pay.amount_required": "Enter a payment amount greater than zero.",
    "pay.review_title": "Payments review",
    "pay.col_amount": "Amount",
    "pay.col_currency": "Currency",
    "pay.col_doctor": "Treating doctor",
    "pay.col_by": "Recorded by",
    "pay.col_balance": "Balance after",
    "pay.col_kind": "Type",
    "pay.kind_session": "Session",
    "pay.kind_payment": "Standalone",
    "credit.balance_fmt": "Patient balance — Total {total} • Paid {paid} • Credit {remaining} — clinic owes the patient (paid in advance)",
    "alert.credit": "Patient credit: {amount} paid in advance — the clinic owes the patient",
    "viewer.zoom_in": "Zoom in +",
    "viewer.zoom_out": "Zoom out −",
    "viewer.fit": "Fit",
    "viewer.rotate_left": "⟲ Rotate left",
    "viewer.rotate_right": "Rotate right ⟳",
    "viewer.save_title": "Save changes?",
    "viewer.save_msg": "You rotated this image. Save the rotation into the file?\n(Yes = save changes, No = discard)",
}

AR = {
    "pay.entry_title": "إدخال دفعة",
    "pay.amount": "المبلغ",
    "pay.date": "التاريخ",
    "pay.note": "ملاحظة (اختياري)",
    "pay.bad_date": "يجب أن يكون تاريخ الدفعة بالشكل YYYY-MM-DD.",
    "pay.amount_required": "أدخل مبلغ دفعة أكبر من الصفر.",
    "pay.review_title": "استعراض المدفوعات",
    "pay.col_amount": "المبلغ",
    "pay.col_currency": "العملة",
    "pay.col_doctor": "الطبيب المعالج",
    "pay.col_by": "سجّلها",
    "pay.col_balance": "الرصيد بعدها",
    "pay.col_kind": "النوع",
    "pay.kind_session": "جلسة",
    "pay.kind_payment": "مستقلة",
    "credit.balance_fmt": "رصيد المريض — المجموع {total} • المدفوع {paid} • رصيد دائن {remaining} — مدفوع مقدماً (العيادة مدينة للمريض)",
    "alert.credit": "رصيد دائن للمريض: {amount} مدفوع مقدماً — العيادة مدينة للمريض",
    "viewer.zoom_in": "تكبير +",
    "viewer.zoom_out": "تصغير −",
    "viewer.fit": "ملاءمة",
    "viewer.rotate_left": "⟲ تدوير لليسار",
    "viewer.rotate_right": "تدوير لليمين ⟳",
    "viewer.save_title": "حفظ التغييرات؟",
    "viewer.save_msg": "لقد قمت بتدوير هذه الصورة. حفظ التدوير في الملف؟\n(نعم = حفظ التغييرات، لا = تجاهل)",
}


def r38_t(key, lang="en"):
    """Round-38 string: this module first, then t()."""
    d = AR if lang == "ar" else EN
    return d.get(key) or EN.get(key) or t(key, lang)
