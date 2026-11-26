"""Medications, interactions, prescriptions + Rx PDF."""
from pathlib import Path
from src.utils.medications import search_medications, list_medications
from src.models.interactions import check_interactions
from src.models.database import init_db, get_connection
from src.models.prescriptions import save_prescription, list_prescriptions, get_prescription_items
from src.reports.prescription_pdf import create_prescription_pdf
def test_meds_search():
    assert len(list_medications()) >= 80
    assert any(h["generic_en"] == "Amoxicillin-Clavulanate" for h in search_medications("Augmentin"))
    assert any(h["generic_en"] == "Amoxicillin" for h in search_medications("أموكسيسيلين"))
def test_interaction_severe():
    a = check_interactions("Ibuprofen", ["Warfarin"], [], [])
    assert a and a[0]["severity"] == "severe" and "Warfarin" in a[0]["message_en"]
def test_allergy_severe():
    a = check_interactions("Amoxicillin", [], ["Penicillin"], [])
    assert a and a[0]["severity"] == "severe"
def test_safe_combo():
    assert check_interactions("Paracetamol", ["Amlodipine"], [], []) == []
def test_save_and_pdf():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name,birth_date_greg,mobile1,nationality,current_medications,allergies) VALUES(?,?,?,?,?,?,?)", ("Rx", "Rx Test", "1990-01-01", "0794000111", "Syrian", "Warfarin", ""))
    fid = cur.lastrowid; conn.commit(); conn.close()
    pid = save_prescription(fid, [{"generic": "Amoxicillin", "brand": "Amoxil", "dose": "500 mg", "frequency": "3x daily", "duration_days": "5", "instructions": "After food"}], doctor="fady", acknowledged=[{"severity": "severe", "message_en": "test", "message_ar": "اختبار"}])
    assert pid and len(list_prescriptions(fid)) >= 1 and get_prescription_items(pid)[0]["generic"] == "Amoxicillin"
    out = create_prescription_pdf({"file_number": fid, "full_name": "Rx Test", "age_years": 36, "nationality": "Syrian"}, {"date": "2026-11-05", "doctor": "fady"}, get_prescription_items(pid), user_name="fady")
    assert Path(out).exists() and Path(out).stat().st_size > 3000, out
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM prescriptions WHERE patient_file=?", (fid,)); cur.execute("DELETE FROM patients WHERE file_number=?", (fid,)); conn.commit(); conn.close()