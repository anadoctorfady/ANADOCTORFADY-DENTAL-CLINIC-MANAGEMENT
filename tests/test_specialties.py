"""Phase 1: dental specialties, custom templates, patient notes, notes in PDF.
Item 5 (2026-11-08): the specialty PICKER is gone - the 8 specialties'
seed phrases now form ONE combined pool (all_phrases) behind every
field's picker button. The JSON data, custom-template CRUD and notes
behaviour below are unchanged."""
import sqlite3
from pathlib import Path
from src.models.specialties import (load_specialties, list_specialties,
    phrases_for, all_phrases)
from src.models import specialty_templates as tpl
from src.models import notes as notes_model
from src.models.phrases import save_phrase, search_phrases, delete_phrase
from src.models.database import get_connection
from src.reports.pdf_report import create_patient_pdf
from tests.test_pdf import PATIENT
SPEC_IDS = {"orthodontics", "oral_surgery", "endodontics", "pediatric",
            "periodontics", "implantology", "prosthodontics", "general"}
CATS = ("complaint", "symptoms", "diagnosis", "procedures")
def _mem():
    conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row; return conn
def _pdf_text(path):
    """Extract text from a reportlab PDF with stdlib only.
    Prefers pypdf/PyPDF2 when installed; otherwise decodes every content
    stream (Flate, or ASCII85+Flate as reportlab emits) and joins them.
    Latin text in this app's PDFs is plain ASCII inside Tj operators."""
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            PdfReader = None
    if PdfReader is not None:
        try:
            return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
        except Exception:
            pass
    import base64, re, zlib
    data = Path(path).read_bytes()
    parts = [data.decode("latin-1", errors="ignore")]
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        raw = m.group(1).rstrip(b"\r\n")
        for dec in (lambda b: zlib.decompress(b),
                    lambda b: zlib.decompress(base64.a85decode(b, adobe=True))):
            try:
                parts.append(dec(raw).decode("latin-1", errors="ignore"))
                break
            except Exception:
                continue
    return "\n".join(parts)
def test_specialties_json_loads():
    specs = load_specialties()
    assert len(specs) == 8
    assert {s["id"] for s in specs} == SPEC_IDS
    assert len(list_specialties()) == 8
    for s in specs:
        assert s["name_en"] and s["name_ar"]
        for cat in CATS:
            items = s["phrases"][cat]
            assert len(items) >= 6, (s["id"], cat)
            assert all(p.get("en") and p.get("ar") for p in items)
    assert len(phrases_for("orthodontics", "complaint")) >= 6
    assert all(isinstance(p, tuple) and len(p) == 2 for p in phrases_for("general", "diagnosis"))
    assert phrases_for("orthodontics", "symptom") == phrases_for("orthodontics", "symptoms")
    assert phrases_for("no_such_specialty", "complaint") == phrases_for("general", "complaint")
def test_custom_template_crud():
    conn = _mem(); tpl.ensure_tables(conn)
    assert len(tpl.list_templates(conn, specialty="orthodontics", category="complaint")) >= 6
    tid = tpl.add_template(conn, "orthodontics", "complaint", "TEST_CUSTOM_EN_XYZ", "اختبار مخصص", created_by="fady")
    assert tid
    rows = tpl.list_templates(conn, specialty="orthodontics", category="complaint")
    mine = [r for r in rows if r["id"] == tid]
    assert mine and mine[0]["is_custom"] == 1 and mine[0]["text_en"] == "TEST_CUSTOM_EN_XYZ"
    assert tpl.update_template(conn, tid, text_en="TEST_CUSTOM_EN_XYZ2") is True
    rows = tpl.list_templates(conn, specialty="orthodontics", category="complaint")
    assert any(r["id"] == tid and r["text_en"] == "TEST_CUSTOM_EN_XYZ2" for r in rows)
    seeded = [r for r in rows if r["is_custom"] == 0][0]
    assert tpl.update_template(conn, seeded["id"], text_en="NOPE") is False
    assert tpl.delete_template(conn, seeded["id"]) is False
    assert tpl.delete_template(conn, tid) is True
    assert not [r for r in tpl.list_templates(conn, specialty="orthodontics", category="complaint") if r["id"] == tid]
    slug = tpl.add_specialty(conn, "Test Specialty XYZ", "تخصص اختبار")
    assert slug and any(s["id"] == slug for s in tpl.list_custom_specialties(conn))
    assert any(s["id"] == slug for s in tpl.list_all_specialties(conn))
    conn.close()
def test_notes_crud():
    conn = _mem(); notes_model.ensure_tables(conn)
    nid = notes_model.add_note(conn, 123, "fady", "Follow up in one week")
    assert nid
    assert notes_model.add_note(conn, 123, "fady", "   ") is None
    rows = notes_model.list_notes(conn, 123)
    assert len(rows) == 1 and rows[0]["note"] == "Follow up in one week" and rows[0]["author"] == "fady"
    assert notes_model.list_notes(conn, 999) == []
    assert notes_model.update_note(conn, nid, "fady", "Follow up in two weeks") is True
    assert notes_model.list_notes(conn, 123)[0]["note"] == "Follow up in two weeks"
    assert notes_model.update_note(conn, nid, "other_doctor", "HACKED") is False
    assert notes_model.list_notes(conn, 123)[0]["note"] == "Follow up in two weeks"
    assert notes_model.update_note(conn, nid, "other_doctor", "Admin override", role="admin") is True
    assert notes_model.delete_note(conn, nid, "other_doctor") is False
    assert notes_model.delete_note(conn, nid, "fady") is True
    assert notes_model.list_notes(conn, 123) == []
    conn.close()
def test_combined_pool_merges_all_specialties():
    """Item 5: one combined pool - phrases from EVERY specialty appear
    for a field, with no specialty selection anywhere."""
    pool = dict(all_phrases("complaint"))
    assert "Crooked teeth" in pool  # orthodontics
    assert "Wisdom tooth pain" in pool  # oral surgery
    assert "Severe throbbing tooth pain" in pool  # endodontics
    assert "My child has tooth pain" in pool  # pediatric
    assert "Bleeding gums when brushing" in pool  # periodontics
    assert "Missing tooth" in pool  # implantology
    assert "Broken crown" in pool  # prosthodontics
    assert "Toothache when chewing" in pool  # general
    assert len(all_phrases("complaint")) >= 40
    assert len(all_phrases("diagnosis")) >= 30
    assert len(all_phrases("symptom")) >= 30
    assert len(all_phrases("procedure")) >= 30
    # Deduped: no (en, ar) pair appears twice.
    assert len(all_phrases("complaint")) == len(set(all_phrases("complaint")))
    # Unknown category -> empty, not a crash.
    assert all_phrases("no_such_category") == []

def test_phrase_specialty_filter():
    for r in search_phrases("complaint", "TEST_SPEC_PHRASE_XYZ"):
        delete_phrase(r["id"])
    pid = save_phrase("complaint", "TEST_SPEC_PHRASE_XYZ ألم اختبار", specialty="orthodontics")
    assert pid
    try:
        assert any(r["id"] == pid for r in search_phrases("complaint", "TEST_SPEC_PHRASE_XYZ", specialty="orthodontics"))
        assert not any(r["id"] == pid for r in search_phrases("complaint", "TEST_SPEC_PHRASE_XYZ", specialty="general"))
        assert any(r["id"] == pid for r in search_phrases("complaint", "TEST_SPEC_PHRASE_XYZ"))
    finally:
        delete_phrase(pid)
def test_notes_in_pdf():
    marker = "TESTNOTE_FOLLOWUP_XYZ"
    out = create_patient_pdf(dict(PATIENT), [], [], [], [], [], language="en",
                             notes=[{"visit_date": "2026-11-07", "author": "fady", "note": marker}])
    assert Path(out).exists()
    assert marker in _pdf_text(out), out
def test_notes_in_pdf_from_db():
    marker = "TESTNOTE_DB_XYZ"
    patient = dict(PATIENT); patient["file_number"] = 999997
    conn = get_connection(); notes_model.ensure_tables(conn)
    nid = notes_model.add_note(conn, 999997, "fady", marker)
    conn.close()
    try:
        out = create_patient_pdf(patient, [], [], [], [], [], language="en")
        assert marker in _pdf_text(out), out
    finally:
        conn = get_connection()
        notes_model.delete_note(conn, nid, "fady", role="admin")
        conn.close()
