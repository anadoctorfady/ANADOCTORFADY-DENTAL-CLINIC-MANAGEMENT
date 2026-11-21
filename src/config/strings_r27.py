"""Round 27 strings: thumbnail gallery + large image viewer.

EN/AR dicts merged by src/config/strings.py. The tile glyphs
"DICOM" / "3D" are language-neutral technical acronyms and live
as constants in thumb_grid.py (the language-purity gate treats
string-table values as wording, so they cannot sit here)."""
EN = {
    "gallery.no_images": "No images yet",
    "gallery.other_file": "File",
    "viewer.close": "Close",
    "clinical.xray_delete": "Delete X-Ray",
    "clinical.xray_delete_title": "Delete",
    "clinical.xray_delete_msg": "Delete this X-Ray?\n{file}",
}
AR = {
    "gallery.no_images": "لا توجد صور بعد",
    "gallery.other_file": "ملف",
    "viewer.close": "إغلاق",
    "clinical.xray_delete": "حذف الأشعة",
    "clinical.xray_delete_title": "حذف",
    "clinical.xray_delete_msg": "حذف صورة الأشعة هذه؟\n{file}",
}
