"""PDF: Arabic patient أحمد محمد علي الحسن."""
from pathlib import Path
from src.reports.pdf_report import create_patient_pdf
PATIENT = {"file_number": 77, "full_name": "أحمد محمد علي الحسن",
    "birth_date_greg": "1990-05-15", "birth_date_hijri": "20 شوال 1410هـ",
    "age_years": 36, "age_months": 5, "age_days": 21, "age_total_days": 13323,
    "nationality": "سورية", "mobile1": "0791234567", "mobile2": "",
    "emergency_phone": "0799888777", "address": "دمشق", "created_at": "2026-11-05"}
def test_pdf_ar():
    out = create_patient_pdf(PATIENT, [{"complaint": "ألم", "symptoms": "حساسية", "visit_date": "2026-11-05"}],
        [{"visit_date": "2026-11-05", "tooth_number": "36", "diagnosis": "تسوس عميق"}],
        [{"visit_date": "2026-11-05", "tooth_number": "36", "procedure_done": "سحب عصب"}],
        [{"total_cost": 120000, "paid_amount": 50000, "remaining": 70000}],
        [], language="ar", bilingual=False, user_name="fady", tooth_selection=["36"])
    assert Path(out).exists() and Path(out).stat().st_size > 5000, out
def test_pdf_bilingual():
    out = create_patient_pdf(PATIENT, [], [], [], [], [], language="ar", bilingual=True, user_name="fady")
    assert Path(out).exists()
