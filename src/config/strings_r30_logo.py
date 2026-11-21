"""Round 30 strings: editable centre logo (Settings + print header).

EN/AR dicts merged into src/config/strings.py by the coordinator
(same pattern as strings_r27.py). Until merged, settings_storage_ui
reads these dicts directly with a fallback to t(), so the logo row
stays bilingual either way. Keys use the settings.logo_* prefix.
"""
EN = {
    "settings.logo_label": "Centre logo:",
    "settings.logo_none": "No logo",
    "settings.logo_add": "Add logo…",
    "settings.logo_change": "Change logo…",
    "settings.logo_remove": "Remove logo",
    "settings.logo_hint": "Shown centred at the top of printed reports, prescriptions, invoices and referrals, above the clinic name.",
    "settings.logo_pick_title": "Choose centre logo",
    "settings.logo_invalid_title": "Invalid image",
    "settings.logo_invalid": "That file is not a valid PNG or JPG image. Nothing was saved.",
    "settings.logo_saved": "Centre logo saved.",
    "settings.logo_removed": "Centre logo removed.",
}
AR = {
    "settings.logo_label": "شعار المركز:",
    "settings.logo_none": "لا يوجد شعار",
    "settings.logo_add": "إضافة شعار…",
    "settings.logo_change": "تغيير الشعار…",
    "settings.logo_remove": "إزالة الشعار",
    "settings.logo_hint": "يظهر في أعلى التقارير والوصفات والفواتير والإحالات المطبوعة، فوق اسم العيادة.",
    "settings.logo_pick_title": "اختيار شعار المركز",
    "settings.logo_invalid_title": "صورة غير صالحة",
    "settings.logo_invalid": "هذا الملف ليس صورة PNG أو JPG صالحة. لم يتم حفظ أي شيء.",
    "settings.logo_saved": "تم حفظ شعار المركز.",
    "settings.logo_removed": "تمت إزالة شعار المركز.",
}
