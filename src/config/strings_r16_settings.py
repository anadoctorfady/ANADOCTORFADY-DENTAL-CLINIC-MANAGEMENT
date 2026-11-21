"""Round 16 strings (2026-11-11): Settings storage section (clinic
name + reports/scans folders) and Users tab layout.

Key prefixes (unique per job, never reuse another job's prefix):
  settings.storage_* / settings.clinic_*
Merged into t() by strings.py (coordinator wires the import, as with
strings_r15_templates.py). Until then, settings_storage_ui.py reads
these dicts directly with a fallback to t(), so the section is
bilingual either way. Every key needs EN + AR.
"""
EN = {
    # Section title: clinic name + where reports/scans are stored.
    "settings.storage_frame": "Clinic name & storage folders",
    # Clinic name shown on reports above the app name; empty = hidden.
    "settings.clinic_name": "Clinic name:",
    "settings.clinic_name_hint": "Shown on reports above the app name. Leave empty to hide it.",
    # Folder pickers: reports (PDFs) and scans (X-ray / scan images).
    "settings.reports_dir": "Reports folder:",
    "settings.scans_dir": "Scans folder:",
    "settings.choose_folder": "Choose…",
    "settings.use_default": "Default",
    # The owner fears losing files without a backup: say plainly that
    # the new folder is used from now on and nothing is moved for him.
    "settings.storage_note": "These folders are used from now on. Existing reports and scans are NOT moved automatically — copy them yourself if you want them in the new folder.",
    "settings.storage_current": "Current: {path}",
    "settings.storage_saved": "Clinic name and folders saved.",
    "settings.storage_save": "Save clinic name",
}
AR = {
    "settings.storage_frame": "اسم العيادة ومجلدات التخزين",
    "settings.clinic_name": "اسم العيادة:",
    "settings.clinic_name_hint": "يظهر في التقارير فوق اسم التطبيق. اتركه فارغاً لإخفائه.",
    "settings.reports_dir": "مجلد التقارير:",
    "settings.scans_dir": "مجلد الصور والأشعة:",
    "settings.choose_folder": "اختيار…",
    "settings.use_default": "الافتراضي",
    "settings.storage_note": "تُستخدم هذه المجلدات من الآن فصاعداً. التقارير والصور الحالية لا تُنقل تلقائياً — انسخها بنفسك إذا أردتها في المجلد الجديد.",
    "settings.storage_current": "الحالي: {path}",
    "settings.storage_saved": "تم حفظ اسم العيادة والمجلدات.",
    "settings.storage_save": "حفظ اسم العيادة",
}
