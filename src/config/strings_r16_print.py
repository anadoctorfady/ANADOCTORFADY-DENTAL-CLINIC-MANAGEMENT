"""Round 16 worker C (printing / PDF / About) strings.

New strings ONLY — this module is merged into src/config/strings.py
by the integration worker (add the same try/except merge block the
other strings_r15_* modules use). UI code must NOT import strings.py
for these keys until that merge lands; print_preview.py reads them
via pp_t() here. Report text (footer / labels) lives here too so
pdf_report.py and tests share one source of truth.
"""
EN = {
    "pp.title": "Print Preview",
    "pp.language": "Report language",
    "pp.print": "Print",
    "pp.save_pdf": "Save PDF",
    "pp.cancel": "Cancel",
    "pp.saved": "Saved:",
    "pp.print_done": "Sent to printer",
    "pp.print_failed": "Printing failed",
    "pp.no_printer": "No printer found — use Save PDF instead.",
    "pp.no_text": "Text preview unavailable for this PDF — see page count and size below.",
    "pp.build_failed": "Could not build the report:",
    "pp.info": "PDF • {pages} page(s) • {kb} KB",
}
AR = {
    "pp.title": "معاينة الطباعة",
    "pp.language": "لغة التقرير",
    "pp.print": "طباعة",
    "pp.save_pdf": "حفظ PDF",
    "pp.cancel": "إلغاء",
    "pp.saved": "تم الحفظ:",
    "pp.print_done": "تم الإرسال إلى الطابعة",
    "pp.print_failed": "فشلت الطباعة",
    "pp.no_printer": "لم يتم العثور على طابعة — استخدم «حفظ PDF» بدلاً من ذلك.",
    "pp.no_text": "معاينة النص غير متاحة لهذا الملف — انظر عدد الصفحات والحجم أدناه.",
    "pp.build_failed": "تعذّر إنشاء التقرير:",
    "pp.info": "PDF • {pages} صفحة • {kb} ك.ب",
}


def pp_t(key, lang="en"):
    """Translated print-preview string; English fallback, then the key."""
    return (AR if lang == "ar" else EN).get(key, EN.get(key, key))


# Round 23 (owner decision 2026-11-17, PRINT ONLY): the former
# FOOTER_EN / FOOTER_AR "completely free / Sadaqah Jariyah" sentence
# is REMOVED from all printed documents and their previews, and its
# text no longer lives here. The names survive ONLY as empty
# tombstones so legacy imports (tests/test_r16_print.py and its
# dependents) do not break; no print path reads them any more, and
# the sentence must not be re-added. The About tab's dedication is
# a separate text (ABOUT_EN / ABOUT_AR in src/config/settings.py)
# and is unchanged by this decision.
FOOTER_EN = ""
FOOTER_AR = ""

# Single-language report labels. The patient PDF is single-language by
# default (the app language); bilingual=True keeps the legacy
# two-column layout. Keys used by pdf_report.py / pdf_common.py only.
PDF_LABELS = {
    "en": {
        "sub": "Dental Clinic Management System",
        "clinic_sub": "ANADOCTORFADY — Dental Clinic Management",
        "patient_info": "1. Patient Information",
        "complaint": "2. Complaint & Symptoms",
        "diagnosis": "3. Initial Diagnosis",
        "procedures": "4. Procedures Performed",
        "cost": "5. Cost Summary",
        "xrays": "6. X-Ray Images",
        "notes": "7. Notes",
        "diseases": "Diseases",
        "none": "None",
        "file_number": "File Number",
        "full_name": "Full Name",
        "birth": "Birth (Greg.)",
        "birth_hijri": "Birth (Hijri)",
        "age": "Age",
        "nationality": "Nationality",
        "mobile": "Mobile 1 / 2",
        "emergency": "Emergency",
        "address": "Address",
        "created": "Created",
        "selected_teeth": "Selected Teeth",
        "date": "Date",
        "tooth": "Tooth",
        "diagnosis_col": "Diagnosis",
        "total": "Total",
        "paid": "Paid",
        "remaining": "Remaining",
        "status": "Status",
        "paid_status": "Paid",
        "due_status": "Due",
        "doctor_signature": "Doctor Signature",
        "report": "Report",
        "user": "User",
        "no_complaints": "No complaints.",
        "no_xrays": "No X-rays.",
        "no_notes": "No notes.",
    },
    "ar": {
        "sub": "نظام إدارة عيادة الأسنان",
        "clinic_sub": "ANADOCTORFADY — إدارة عيادة الأسنان",
        "patient_info": "١. معلومات المريض",
        "complaint": "٢. الشكوى والأعراض",
        "diagnosis": "٣. التشخيص الأولي",
        "procedures": "٤. الإجراءات العلاجية",
        "cost": "٥. ملخص التكلفة",
        "xrays": "٦. صور الأشعة",
        "notes": "٧. ملاحظات",
        "diseases": "الأمراض",
        "none": "لا يوجد",
        "file_number": "رقم الملف",
        "full_name": "الاسم الكامل",
        "birth": "تاريخ الميلاد (ميلادي)",
        "birth_hijri": "تاريخ الميلاد (هجري)",
        "age": "العمر",
        "nationality": "الجنسية",
        "mobile": "موبايل ١ / ٢",
        "emergency": "هاتف الطوارئ",
        "address": "العنوان",
        "created": "تاريخ الإنشاء",
        "selected_teeth": "الأسنان المختارة",
        "date": "التاريخ",
        "tooth": "السن",
        "diagnosis_col": "التشخيص",
        "total": "المجموع",
        "paid": "المدفوع",
        "remaining": "المتبقي",
        "status": "الحالة",
        "paid_status": "مدفوع",
        "due_status": "مستحق",
        "doctor_signature": "توقيع الطبيب",
        "report": "التقرير",
        "user": "المستخدم",
        "no_complaints": "لا توجد شكوى.",
        "no_xrays": "لا توجد صور أشعة.",
        "no_notes": "لا توجد ملاحظات.",
    },
}
