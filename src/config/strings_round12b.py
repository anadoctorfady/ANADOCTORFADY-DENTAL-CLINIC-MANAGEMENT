"""Round 12 strings, part 2 (2026-11-09). Overflow for
strings_round12.py, which reached 183/200 lines while agents were
still adding keys. Same prefix rules as part 1:
  wheel_*  tpl_*  savegate_*  alert_*  edit24_*  loginlast_*
  scan_*  appt_*  finlock_*  fintot_*  perm_*
Merged into t() by strings.py. Every key needs EN + AR.
"""
EN = {
    # Finance record edit/delete is admin-only (Job 9, coordinator ruling).
    "fintot.admin_only": "Only the admin can edit or delete finance records",
    # Per-user last-login list on the login window (Item D, 2026-11-09).
    "pay_no_change_title": "No new amount",
    "pay_no_change_msg": "The Total / Paid are unchanged — nothing was saved.",
    "loginlist_heading": "Last login on this device",
    "loginlist_empty": "No logins yet on this device",
    "loginlist_more": "+{n} more",
}
AR = {
    "fintot.admin_only": "فقط المدير يمكنه تعديل أو حذف سجلات المالية",
    "pay_no_change_title": "لا يوجد مبلغ جديد",
    "pay_no_change_msg": "المجموع / المدفوع لم يتغيّر — لم يُحفظ شيء.",
    "loginlist_heading": "آخر تسجيل دخول على هذا الجهاز",
    "loginlist_empty": "لا توجد عمليات تسجيل دخول بعد على هذا الجهاز",
    "loginlist_more": "+{n} آخرون",
}
