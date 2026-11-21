"""Round 15 strings (2026-11-10): templates background + right-click
context menu on the template manager. Round 21: template search +
delete-instead-of-hide + restore built-ins.

Key prefixes (unique per job, never reuse another job's prefix):
  tpl_ctx_*  tpl_search  tpl_delete_seed_*  tpl_restore_builtins
Merged into t() by strings.py. Every key needs EN + AR.
"""
EN = {
    # Right-click context menu on a manager row (Edit / Delete / Add new).
    'tpl_ctx_edit': 'Edit', 'tpl_ctx_delete': 'Delete', 'tpl_ctx_add_new': 'Add new',
    # Round 21: search button/label + seed delete + category restore.
    'tpl_search': 'Search',
    'tpl_delete_seed_title': 'Delete built-in template',
    'tpl_delete_seed_confirm': 'Delete this built-in template? You can restore built-ins later with "Restore built-in templates".',
    'tpl_restore_builtins': 'Restore built-in templates',
}
AR = {
    "tpl_ctx_edit": "تعديل", "tpl_ctx_delete": "حذف", "tpl_ctx_add_new": "إضافة جديدة",
    "tpl_search": "بحث",
    "tpl_delete_seed_title": "حذف قالب جاهز",
    "tpl_delete_seed_confirm": "حذف هذا القالب الجاهز؟ يمكنك استعادة القوالب الجاهزة لاحقاً من «استعادة القوالب الجاهزة».",
    "tpl_restore_builtins": "استعادة القوالب الجاهزة",
}
