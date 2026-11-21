"""Core UI strings (Job A1): shell chrome + login + dialogs.

EN holds the EXACT text shown in English mode today
(single-language: EN values contain no Arabic); AR holds natural Modern Standard
Arabic (Levantine-friendly) for a dental clinic. UI code reads
labels via t() at BUILD time -- never cache a translated string at
import time, because the language toggle rebuilds the whole UI.
Keys are globally unique; area modules (strings_clinical,
strings_ops) merge in below when their workers land them.
"""
EN = {
    "shell.theme_dark": "🌙 Dark", "shell.theme_light": "☀️ Light", "shell.logout": "Logout",
    "shell.user_default": "| Dental Clinic", "shell.new_patient": "＋ New Patient", "shell.head_name": "Name",
    "shell.head_mobile": "Mobile", "shell.tab_patients": "  Patients  ", "shell.tab_clinical": "  Clinical  ",
    "shell.tab_appointments": "  Appointments  ", "shell.tab_finances": "  Finances  ",
    "shell.tab_settings": "  Settings / Reports  ", "shell.tab_users": "  Users  ",
    "shell.tab_about": "  About  ", "shell.attendance": "Attendance", "shell.lang_title": "Language",
    "shell.lang_switched": "Switched to English", "shell.new_file": "File #: (new)",
    "shell.pdf_select_title": "Select", "shell.pdf_select_first": "Select a patient first!",
    "shell.pdf_bilingual": "Bilingual (EN+AR) PDF?", "shell.pdf_created": "PDF Created",
    "shell.pdf_saved": "Saved:", "shell.pdf_error": "PDF Error", "login.title": "Login",
    "login.username": "Username", "login.password": "Password", "login.signin": "Sign In",
    "login.error_title": "Error", "login.invalid": "Invalid credentials!",
    "dlg.sync_password_title": "Sync password", "dlg.sync_prompt": "Enter your password to sync as {username}",
    "dlg.sync_btn": "Sync", "dlg.sync_cancel": "Cancel", "dlg.sync_title": "Sync",
    "dlg.sync_now_btn": "🔄 Sync Now", "dlg.sync_offline": "Offline — check the sync server URL",
    "dlg.sync_login_failed": "Login failed — wrong password or user",
    "dlg.sync_done": "Sync done — pushed {push} • pulled patients {patients} / visits {visits} / financials {financials} / employees {employees}",
    "dlg.sync_not_logged_in": "Not logged in", "dlg.sync_cancelled": "Sync cancelled",
    "dlg.tm_title": "Manage templates", "dlg.tm_category": "Category", "dlg.tm_empty_title": "Empty",
    "dlg.tm_empty_msg": "Write the phrase in English or Arabic.", "dlg.tm_protected_title": "Protected",
    "dlg.tm_protected_edit": "Seeded phrases cannot be edited. Add a custom copy instead.",
    "dlg.tm_protected_delete": "Seeded phrases cannot be deleted.", "dlg.tm_delete_title": "Delete",
    "dlg.tm_delete_confirm": "Delete this custom phrase?", "dlg.tm_add": "Add", "dlg.tm_edit": "Edit",
    "dlg.tm_delete": "Delete", "dlg.ad_title": "Add drug",
    "dlg.ad_note": "The drug is saved permanently and appears in the drug search.",
    "dlg.ad_f_generic_en": "Scientific name (generic) *", "dlg.ad_f_generic_ar": "Arabic name",
    "dlg.ad_f_brand_en": "Brand", "dlg.ad_f_brand_ar": "Brand (Arabic)",
    "dlg.ad_f_form": "Dosage form (Tablet, Capsule, Syrup…)", "dlg.ad_f_strength": "Strength (e.g. 500 mg)",
    "dlg.ad_category": "Category", "dlg.ad_save": "💾 Save drug", "dlg.ad_cancel": "Cancel",
    "dlg.ad_error_title": "Cannot add drug", "dlg.ad_added_title": "Drug added", "dlg.at_title": "Attendance",
    "dlg.at_admin_only_msg": "Admin only — attendance is visible to the clinic admin.",
    "dlg.at_date": "Date (YYYY-MM-DD):", "dlg.at_user": "User", "dlg.at_head_user": "User",
    "dlg.at_head_action": "In/Out", "dlg.at_head_time": "Exact time", "dlg.at_head_device": "Device",
    "dlg.at_refresh": "Refresh", "dlg.at_in": "In ✓", "dlg.at_out": "Out",
    "dlg.pp_title": "Templates — {category}", "dlg.pp_heading": "Templates (all fields, one pool)",
    "dlg.pp_search": "Search", "dlg.pp_insert": "Insert", "dlg.pp_save_template": "＋ Save as template",
    "dlg.pp_favorite": "⭐ Favorite", "dlg.pp_close": "Close",
    "dlg.pp_empty_msg": "Write the phrase first (min 3 chars).", "dlg.pp_saved_title": "Saved",
    "dlg.pp_saved_msg": "Saved as a template", "dlg.pp_picker_btn": "📋 Templates",
    "dlg.pp_clip_title": "📋 Clipboard History", "dlg.pp_clip_clear": "Clear history",
    "dlg.pp_clip_refresh": "Refresh", "dlg.cat_complaint": "complaint", "dlg.cat_symptom": "symptom",
    "dlg.cat_diagnosis": "diagnosis", "dlg.cat_procedure": "procedure",
    "dlg.cp_title": "📋 Clipboard History (multi-select)",
    "dlg.cp_hint": "Tick several items, then Paste selected — one per line",
    "dlg.cp_empty": "Clipboard history is empty", "dlg.cp_paste_selected": "Paste selected",
    "dlg.cp_paste_all": "Paste all", "dlg.cp_clear": "Clear", "dlg.cp_cancel": "Cancel",
    "dlg.fg_title": "Finance unlock", "dlg.fg_prompt": "Enter your password to view finances",
    "dlg.fg_unlock": "Unlock", "dlg.fg_wrong": "Wrong password",
}
AR = {
    "shell.theme_dark": "🌙 داكن", "shell.theme_light": "☀️ فاتح", "shell.logout": "تسجيل الخروج",
    "shell.user_default": "| عيادة الأسنان", "shell.new_patient": "＋ مريض جديد", "shell.head_name": "الاسم",
    "shell.head_mobile": "الجوال", "shell.tab_patients": "  المرضى  ", "shell.tab_clinical": "  السريري  ",
    "shell.tab_appointments": "  المواعيد  ", "shell.tab_finances": "  المالية  ",
    "shell.tab_settings": "  الإعدادات / التقارير  ", "shell.tab_users": "  المستخدمون  ",
    "shell.tab_about": "  حول  ", "shell.attendance": "الحضور", "shell.lang_title": "اللغة",
    "shell.lang_switched": "تم التبديل إلى العربية", "shell.new_file": "رقم الملف: (جديد)",
    "shell.pdf_select_title": "اختيار", "shell.pdf_select_first": "اختر مريضاً أولاً!",
    "shell.pdf_bilingual": "ملف PDF ثنائي اللغة (إنجليزي + عربي)؟", "shell.pdf_created": "تم إنشاء ملف PDF",
    "shell.pdf_saved": "تم الحفظ:", "shell.pdf_error": "خطأ في ملف PDF", "login.title": "تسجيل الدخول",
    "login.username": "اسم المستخدم", "login.password": "كلمة السر", "login.signin": "دخول",
    "login.error_title": "خطأ", "login.invalid": "بيانات غير صحيحة!",
    "dlg.sync_password_title": "كلمة سر المزامنة", "dlg.sync_prompt": "أدخل كلمة السر للمزامنة باسم {username}",
    "dlg.sync_btn": "مزامنة", "dlg.sync_cancel": "إلغاء", "dlg.sync_title": "مزامنة",
    "dlg.sync_now_btn": "🔄 مزامنة الآن", "dlg.sync_offline": "بلا اتصال — تحقق من رابط خادم المزامنة",
    "dlg.sync_login_failed": "فشل الدخول — كلمة السر أو اسم المستخدم غير صحيح",
    "dlg.sync_done": "تمت المزامنة — تم الإرسال {push} • تم الاستقبال: المرضى {patients} / الزيارات {visits} / المالية {financials} / الموظفون {employees}",
    "dlg.sync_not_logged_in": "لم يتم تسجيل الدخول", "dlg.sync_cancelled": "تم إلغاء المزامنة",
    "dlg.tm_title": "إدارة القوالب", "dlg.tm_category": "الفئة:", "dlg.tm_empty_title": "فارغ",
    "dlg.tm_empty_msg": "اكتب العبارة بالإنجليزية أو بالعربية.", "dlg.tm_protected_title": "محمي",
    "dlg.tm_protected_edit": "لا يمكن تعديل العبارات الجاهزة. أضف نسخة خاصة بك بدلاً من ذلك.",
    "dlg.tm_protected_delete": "لا يمكن حذف العبارات الجاهزة.", "dlg.tm_delete_title": "حذف",
    "dlg.tm_delete_confirm": "حذف هذه العبارة الخاصة؟", "dlg.tm_add": "إضافة", "dlg.tm_edit": "تعديل",
    "dlg.tm_delete": "حذف", "dlg.ad_title": "إضافة دواء",
    "dlg.ad_note": "يُحفظ الدواء نهائياً ويظهر في البحث عن الأدوية.", "dlg.ad_f_generic_en": "الاسم العلمي *",
    "dlg.ad_f_generic_ar": "الاسم بالعربية", "dlg.ad_f_brand_en": "الاسم التجاري",
    "dlg.ad_f_brand_ar": "التجاري بالعربية", "dlg.ad_f_form": "الشكل الصيدلاني (حبة، كبسولة، شراب…)",
    "dlg.ad_f_strength": "التركيز (مثال: 500 ملغ)", "dlg.ad_category": "الفئة:", "dlg.ad_save": "💾 حفظ الدواء",
    "dlg.ad_cancel": "إلغاء", "dlg.ad_error_title": "تعذّرت إضافة الدواء",
    "dlg.ad_added_title": "تمت إضافة الدواء", "dlg.at_title": "الحضور",
    "dlg.at_admin_only_msg": "للمدير فقط — سجل الحضور مرئي لمدير العيادة فقط.",
    "dlg.at_date": "التاريخ (YYYY-MM-DD):", "dlg.at_user": "المستخدم:", "dlg.at_head_user": "المستخدم",
    "dlg.at_head_action": "دخول/خروج", "dlg.at_head_time": "الوقت الدقيق", "dlg.at_head_device": "الجهاز",
    "dlg.at_refresh": "تحديث", "dlg.at_in": "دخول ✓", "dlg.at_out": "خروج",
    "dlg.pp_title": "قوالب — {category}", "dlg.pp_heading": "قوالب (كل الحقول، مجموعة واحدة)",
    "dlg.pp_search": "بحث:", "dlg.pp_insert": "إدراج", "dlg.pp_save_template": "＋ حفظ قالب",
    "dlg.pp_favorite": "⭐ مفضلة", "dlg.pp_close": "إغلاق",
    "dlg.pp_empty_msg": "اكتب العبارة أولاً (3 أحرف على الأقل).", "dlg.pp_saved_title": "تم الحفظ",
    "dlg.pp_saved_msg": "تم حفظ القالب.", "dlg.pp_picker_btn": "📋 قوالب", "dlg.pp_clip_title": "📋 سجل الحافظة",
    "dlg.pp_clip_clear": "مسح السجل", "dlg.pp_clip_refresh": "تحديث", "dlg.cat_complaint": "الشكوى",
    "dlg.cat_symptom": "الأعراض", "dlg.cat_diagnosis": "التشخيص", "dlg.cat_procedure": "الإجراء",
    "dlg.cp_title": "📋 سجل الحافظة (اختيار متعدد)",
    "dlg.cp_hint": "حدّد عدة عناصر ثم اضغط «لصق المحدد» — عنصر في كل سطر", "dlg.cp_empty": "سجل الحافظة فارغ",
    "dlg.cp_paste_selected": "لصق المحدد", "dlg.cp_paste_all": "لصق الكل", "dlg.cp_clear": "مسح",
    "dlg.cp_cancel": "إلغاء", "dlg.fg_title": "فتح المالية", "dlg.fg_prompt": "أدخل كلمة السر لعرض المالية",
    "dlg.fg_unlock": "فتح", "dlg.fg_wrong": "كلمة السر غير صحيحة",
}

def t(key, lang="en"):
    """Translated string for `key` in `lang` ("en"/"ar").

    Falls back to the English text, then to the key itself, so a
    missing translation never crashes the UI."""
    return (AR if lang == "ar" else EN).get(key, EN.get(key, key))


try:
    from src.config.strings_clinical import EN as _CL_EN, AR as _CL_AR
    EN.update(_CL_EN); AR.update(_CL_AR)
except ImportError:
    pass
try:
    from src.config.strings_ops import EN as _OP_EN, AR as _OP_AR
    EN.update(_OP_EN); AR.update(_OP_AR)
except ImportError:
    pass
try:
    from src.config.strings_round12 import EN as _R12_EN, AR as _R12_AR
    EN.update(_R12_EN); AR.update(_R12_AR)
except ImportError:
    pass
try:
    from src.config.strings_round12b import EN as _R12B_EN, AR as _R12B_AR
    EN.update(_R12B_EN); AR.update(_R12B_AR)
except ImportError:
    pass

try:
    from src.config.strings_r15_teeth import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r15_clinical import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r15_templates import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r15_patient import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r16_patients import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r16_clinical import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r16_print import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r16_rx import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r16_settings import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r19_referral import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r19_finance import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r19_patients import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r19_patient import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r24_session import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
try:
    from src.config.strings_r27 import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
except ImportError:
    pass
