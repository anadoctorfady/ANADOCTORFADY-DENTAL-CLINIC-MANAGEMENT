"""Round 24 strings: the unified clinical (session) table.

EN + AR dicts, merged into src.config.strings (t()) by strings.py;
sess_t() is the local reader (same pattern as r16_t): prefer these
dicts, then EN, then t(). Placeholders: {date}, {tooth}, {paid},
{cap}, {total}, {remaining}, {fields}.
"""
from src.config.strings import t

EN = {
    "sess.save": "Save session",
    "sess.edit": "Edit session",
    "sess.delete": "Delete session",
    "sess.cancel_edit": "Cancel edit",
    "sess.editing": "Editing session of {date} (tooth {tooth}) — date and tooth are fixed",
    "sess.editing_notooth": "Editing session of {date} — date and tooth are fixed",
    "sess.money_locked": "Money locked: clinical text only — editing payment amounts needs the finance permission (admin).",
    "sess.delete_money_denied": "This session has payments attached. Deleting it needs the finance permission (admin), which you do not have.",
    "sess.overpay_title": "Payment too large",
    "sess.overpay_msg": "Paid {paid} is more than can be accepted for this session. The maximum payable now is {cap} (the patient's earlier balance plus this session's total). Nothing was saved.",
    "sess.delete_title": "Delete session",
    "sess.delete_confirm": "Delete this whole session — its clinical rows and its payments?",
    "sess.select_first": "Select a session row first.",
    "sess.no_change": "Nothing new to save.",
    "sess.pat_balance": "Patient balance — Total {total} • Paid {paid} • Remaining {remaining}",
    "sess.money_only_note": "Money only: the clinical part of this date is already saved.",
}

AR = {
    "sess.save": "حفظ الجلسة",
    "sess.edit": "تعديل الجلسة",
    "sess.delete": "حذف الجلسة",
    "sess.cancel_edit": "إلغاء التعديل",
    "sess.editing": "تعديل جلسة {date} (السن {tooth}) — التاريخ والسن ثابتان",
    "sess.editing_notooth": "تعديل جلسة {date} — التاريخ والسن ثابتان",
    "sess.money_locked": "المبالغ مقفلة: يمكن تعديل النص السريري فقط — تعديل مبالغ المدفوعات يحتاج صلاحية المالية (المدير).",
    "sess.delete_money_denied": "هذه الجلسة مرتبطة بمدفوعات. حذفها يحتاج صلاحية المالية (المدير) وهي غير متوفرة لديك.",
    "sess.overpay_title": "الدفعة أكبر من المسموح",
    "sess.overpay_msg": "المدفوع {paid} أكبر مما يمكن قبوله لهذه الجلسة. الحد الأقصى القابل للدفع الآن هو {cap} (رصيد المريض السابق زائد مجموع هذه الجلسة). لم يتم حفظ أي شيء.",
    "sess.delete_title": "حذف الجلسة",
    "sess.delete_confirm": "حذف هذه الجلسة بالكامل — صفوفها السريرية ومدفوعاتها؟",
    "sess.select_first": "اختر صف جلسة أولاً.",
    "sess.no_change": "لا يوجد جديد لحفظه.",
    "sess.pat_balance": "رصيد المريض — المجموع {total} • المدفوع {paid} • المتبقي {remaining}",
    "sess.money_only_note": "مبلغ فقط: الجزء السريري لهذا التاريخ محفوظ مسبقاً.",
}


def sess_t(key, lang="en"):
    """Round-24 session string: this module first, then t()."""
    d = AR if lang == "ar" else EN
    return d.get(key) or EN.get(key) or t(key, lang)
