"""Round 12 strings (2026-11-09): mouse-wheel, editable templates,
clinical save gate, patient alerts, 24h edit rule, last login, scans,
quick-book, finance totals + auto-lock, permission tree.

Key prefixes (unique per job, never reuse another job's prefix):
  wheel_*  tpl_*  savegate_*  alert_*  edit24_*  loginlast_*
  scan_*  appt_*  finlock_*  fintot_*  perm_*
Merged into t() by strings.py. Every key needs EN + AR.
"""
EN = {
    # Save gate (Job 3): all four clinical fields must be filled.
    'savegate.title': 'Cannot save yet',
    'savegate.missing': 'Please fill in all four fields before saving. Missing: {fields}',
    'savegate.complaint': 'Complaint', 'savegate.symptom': 'Symptoms', 'savegate.diagnosis': 'Diagnosis',
    'savegate.procedure': 'Procedure', 'savegate.note': 'Notes',
    # Patient alerts (Job 4).
    'alert.allergy': '⚠ Drug allergy: {detail}', 'alert.meds': '⚠ Current medication: {detail}',
    'alert.balance': '⚠ Unpaid balance: {amount}',
    # Scans entry from the clinical page (Job 7b).
    'scan_add_image': '📷 Add image',
    # Clinical history edit/delete (Job 3d, 24h rule).
    'savegate.edit': 'Edit', 'savegate.delete': 'Delete', 'savegate.delete_confirm': 'Delete this record?',
    'savegate.edit_title': 'Edit record', 'savegate.not_allowed_title': 'Not allowed',
    # Scans upload discoverability (Job 7a).
    'scan.add_image': '＋ Add image', 'scan.patient': 'Patient: {name} (file #{fid})',
    'scan.no_patient': 'No patient selected — choose a patient to add images',
    # Appointments quick-book (Job 8).
    'appt.quickbook': '⚡ Quick-book', 'appt.quickbook_hint': 'Select a patient first to quick-book',
    'appt.quickbook_patient': 'Patient: {name} (file #{fid})',
    'appt.quickbook_done': 'Booked {name} today at {time}', 'appt.quickbook_done_title': 'Booked',
    'appt.slot_taken': 'Slot {time} on {date} is already booked',
    'appt.no_free_slot': 'No free slot left today',
    # Finance flexible totals (Job 9a).
    'fintot.lab': 'Lab costs', 'fintot.salaries': 'Salaries', 'fintot.expenses': 'Expenses',
    'fintot.included': 'Included in totals: {parts}', 'fintot.all': 'lab + salaries + expenses',
    'fintot.none': 'none — net = income only', 'fintot.part_lab': 'lab', 'fintot.part_salaries': 'salaries',
    'fintot.part_expenses': 'expenses',
    'fintot.doctor_note': 'Totals show your own income only — lab, salaries and centre expenses are not shown.',
    # Finance record edit/delete under the 24h rule (Job 9).
    'fintot.edit': 'Edit', 'fintot.delete': 'Delete', 'fintot.select_first': 'Select a row first',
    'fintot.delete_confirm': 'Delete this record?', 'fintot.new_amount': 'New amount:',
    'fintot.updated': 'Updated', 'fintot.deleted': 'Deleted',
    # Finance 15-minute auto-lock (Job 9b).
    'finlock.auto': 'Locked after 15 minutes without finance activity — sign in again',
    # Permission tree (Job 10).
    'perm.title': 'Extra permissions',
    'perm.subtitle': 'Tick extra permissions for the selected user — grants only add to the role default, never remove it.',
    'perm.user': 'User: {name}', 'perm.select_user': 'Select a user above to manage extra permissions',
    'perm.saved': 'Saved', 'perm.group_clinical': 'Clinical', 'perm.group_finance': 'Finance',
    'perm.group_salaries': 'Salaries', 'perm.group_users': 'Users', 'perm.group_settings': 'Settings',
    'perm.group_attendance': 'Attendance',
    # 24-hour edit rule (Job 5): single-language refusal for UI call sites.
    'edit24_blocked': 'Editing is allowed only by the admin after 24 hours',
    # Last login on this device (Job 6).
    'loginlast_title': 'Last login', 'loginlast_prev': 'Last login on this device: {when}',
    'loginlast_first': 'First login on this device — welcome!',
    # Editable, single-language templates (Job 2).
    'tpl_settings_frame': 'Templates', 'tpl_settings_lang': 'Template language:',
    'tpl_lang_auto': 'Follow app language', 'tpl_settings_save': 'Save',
    'tpl_settings_saved': 'Template language saved', 'tpl_edit_text': 'Text:', 'tpl_show_hidden': 'Show hidden',
    'tpl_hidden_mark': '[hidden] ', 'tpl_edited_mark': '✎ ', 'tpl_restore': 'Restore', 'tpl_hide_title': 'Hide',
    'tpl_hide_confirm': 'Hide this ready-made template? You can restore it later with Show hidden.',
    'tpl_select_first': 'Select a template first', 'tpl_shown_in': 'Shown in: {lang}',
    'tpl_nothing_to_restore': 'This template has no changes to restore',
}
AR = {
    # Save gate (Job 3): all four clinical fields must be filled.
    'savegate.title': 'لا يمكن الحفظ بعد',
    'savegate.missing': 'يرجى ملء الحقول الأربعة قبل الحفظ. الحقول الناقصة: {fields}',
    'savegate.complaint': 'الشكوى', 'savegate.symptom': 'الأعراض', 'savegate.diagnosis': 'التشخيص',
    'savegate.procedure': 'الإجراء', 'savegate.note': 'ملاحظات',
    # Patient alerts (Job 4).
    'alert.allergy': '⚠ حساسية دوائية: {detail}', 'alert.meds': '⚠ أدوية حالية: {detail}',
    'alert.balance': '⚠ رصيد غير مسدد: {amount}',
    # Scans entry from the clinical page (Job 7b).
    'scan_add_image': '📷 إضافة صورة',
    # Clinical history edit/delete (Job 3d, 24h rule).
    'savegate.edit': 'تعديل', 'savegate.delete': 'حذف', 'savegate.delete_confirm': 'حذف هذا السجل؟',
    'savegate.edit_title': 'تعديل السجل', 'savegate.not_allowed_title': 'غير مسموح',
    # Scans upload discoverability (Job 7a).
    'scan.add_image': '＋ إضافة صورة', 'scan.patient': 'المريض: {name} (ملف #{fid})',
    'scan.no_patient': 'لم يتم اختيار مريض — اختر مريضاً لإضافة صور',
    # Appointments quick-book (Job 8).
    'appt.quickbook': '⚡ حجز سريع', 'appt.quickbook_hint': 'اختر مريضاً أولاً للحجز السريع',
    'appt.quickbook_patient': 'المريض: {name} (ملف #{fid})',
    'appt.quickbook_done': 'تم حجز {name} اليوم الساعة {time}', 'appt.quickbook_done_title': 'تم الحجز',
    'appt.slot_taken': 'الوقت {time} في {date} محجوز مسبقاً', 'appt.no_free_slot': 'لا توجد مواعيد متاحة اليوم',
    # Finance flexible totals (Job 9a).
    'fintot.lab': 'تكاليف المختبر', 'fintot.salaries': 'الرواتب', 'fintot.expenses': 'المصاريف',
    'fintot.included': 'المشمول في الإجماليات: {parts}', 'fintot.all': 'المختبر + الرواتب + المصاريف',
    'fintot.none': 'لا شيء — الصافي = الدخل فقط', 'fintot.part_lab': 'المختبر',
    'fintot.part_salaries': 'الرواتب', 'fintot.part_expenses': 'المصاريف',
    'fintot.doctor_note': 'الإجماليات تعرض دخلك الخاص فقط — لا تُعرض تكاليف المختبر والرواتب ومصاريف المركز.',
    # Finance record edit/delete under the 24h rule (Job 9).
    'fintot.edit': 'تعديل', 'fintot.delete': 'حذف', 'fintot.select_first': 'اختر سطراً أولاً',
    'fintot.delete_confirm': 'حذف هذا السجل؟', 'fintot.new_amount': 'المبلغ الجديد:',
    'fintot.updated': 'تم التحديث', 'fintot.deleted': 'تم الحذف',
    # Finance 15-minute auto-lock (Job 9b).
    'finlock.auto': 'تم القفل بعد 15 دقيقة من عدم النشاط في المالية — سجّل الدخول مجدداً',
    # Permission tree (Job 10).
    'perm.title': 'صلاحيات إضافية',
    'perm.subtitle': 'حدّد صلاحيات إضافية للمستخدم المختار — الإضافات تضيف إلى صلاحيات الدور فقط ولا تلغيها أبداً.',
    'perm.user': 'المستخدم: {name}', 'perm.select_user': 'اختر مستخدماً أعلاه لإدارة صلاحياته الإضافية',
    'perm.saved': 'تم الحفظ', 'perm.group_clinical': 'السريري', 'perm.group_finance': 'المالية',
    'perm.group_salaries': 'الرواتب', 'perm.group_users': 'المستخدمون', 'perm.group_settings': 'الإعدادات',
    'perm.group_attendance': 'الحضور',
    # 24-hour edit rule (Job 5): single-language refusal for UI call sites.
    'edit24_blocked': 'لا يمكن التعديل بعد 24 ساعة إلا من قبل المدير',
    # Last login on this device (Job 6).
    'loginlast_title': 'آخر تسجيل دخول', 'loginlast_prev': 'آخر تسجيل دخول على هذا الجهاز: {when}',
    'loginlast_first': 'هذه أول مرة تسجّل فيها الدخول على هذا الجهاز — أهلاً بك!',
    # Editable, single-language templates (Job 2).
    'tpl_settings_frame': 'القوالب', 'tpl_settings_lang': 'لغة القوالب:', 'tpl_lang_auto': 'اتباع لغة التطبيق',
    'tpl_settings_save': 'حفظ', 'tpl_settings_saved': 'تم حفظ لغة القوالب', 'tpl_edit_text': 'النص:',
    'tpl_show_hidden': 'إظهار المخفية', 'tpl_hidden_mark': '[مخفي] ', 'tpl_edited_mark': '✎ ',
    'tpl_restore': 'استعادة', 'tpl_hide_title': 'إخفاء',
    'tpl_hide_confirm': 'إخفاء هذا القالب الجاهز؟ يمكنك استعادته لاحقاً من «إظهار المخفية».',
    'tpl_select_first': 'اختر قالباً أولاً', 'tpl_shown_in': 'تُعرض بلغة: {lang}',
    'tpl_nothing_to_restore': 'لا توجد تغييرات لاستعادتها في هذا القالب',
}
