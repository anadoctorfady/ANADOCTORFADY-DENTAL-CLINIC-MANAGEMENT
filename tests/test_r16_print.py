"""Round 16 worker C (printing / PDF / About).

About names brothers / إخوته (UNCHANGED -- the dedication lives in
the About tab only); the print preview opens with Print / Save /
Cancel; reports are single-language (app language) with a language
override; the clinic-name header puts the clinic name above the app
name when set and the app name alone when unset; reports_dir changes
the save folder; diseases appear in the report when set.

ROUND 23 SUPERSESSION (owner decision 2026-11-17, item 5): the
round-16 print footer that named "the developer Dr Fady" / "المطور
د. فادي" (the sadaqah/free sentence) is REMOVED from all printed
output. The footer assertions below now assert its ABSENCE; the
About-text assertions are unchanged because About keeps the
dedication.

DB work runs on an isolated temp copy (never the live DB); PDFs go
to temp folders. GUI tests skip gracefully with no display.
"""
import contextlib
import re
import shutil
import tempfile
from pathlib import Path

from src.config.settings import ABOUT_EN, ABOUT_AR
from src.config.strings_r16_print import FOOTER_EN, FOOTER_AR

PATIENT = {"file_number": 77, "full_name": "Test Patient",
           "birth_date_greg": "1990-05-15",
           "birth_date_hijri": "20 Shawwal 1410",
           "age_years": 36, "age_months": 5, "age_days": 21,
           "nationality": "Syrian", "mobile1": "0944234456", "mobile2": "",
           "emergency_phone": "0999888777", "address": "Damascus",
           "created_at": "2026-11-05", "diseases": "Diabetes, Hypertension"}
_TMP = Path(tempfile.mkdtemp(prefix="r16_print_"))
_AR = re.compile(r"[\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF]")


@contextlib.contextmanager
def isolated_db():
    """Temp DB (same pattern as tests/test_templates_edit.py)."""
    import src.models.database as DBmod
    db_path = _TMP / "iso_clinic.db"
    for suf in ("", "-wal", "-shm"):
        q = Path(str(db_path) + suf)
        if q.exists():
            q.unlink()
    old = DBmod.DB
    DBmod.DB = db_path
    try:
        from src.models.database import init_db
        init_db()
        yield
    finally:
        DBmod.DB = old


def _pdf_text(path):
    """Extracted PDF text via pdftotext, or None when unavailable."""
    if not shutil.which("pdftotext"):
        print("SKIP pdf-text check (no pdftotext)")
        return None
    import subprocess
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _make_pdf(patient=None, out_dir=None, language="en", **kw):
    from src.reports.pdf_report import create_patient_pdf
    return create_patient_pdf(patient or PATIENT, [], [], [], [], [],
                              language=language, user_name="fady",
                              out_dir=out_dir, **kw)


def test_footer_wording():
    # Round 23 (owner decision 2026-11-17): the sadaqah/developer
    # footer sentence is gone from print. FOOTER_EN / FOOTER_AR are
    # empty tombstones kept only so old imports do not break; no
    # print path reads them.
    assert FOOTER_EN == "" and FOOTER_AR == ""
    for frag in ("the developer", "Sadaqah", "charity", "completely free"):
        assert frag not in FOOTER_EN
    for frag in ("المطور", "صدقة", "مجاني"):
        assert frag not in FOOTER_AR


def test_about_final_text_brothers():
    assert ABOUT_EN == ("This app is completely free and we ask Allah to "
                        "make it ongoing charity for the developer Dr Fady "
                        "Abdulkafy Dadoush and his parents, brothers, wife "
                        "and children")
    assert ABOUT_AR == ("هذا التطبيق مجاناً بالكامل و نسأل الله تعالى أن "
                        "يكون صدقة جارية عن المطور د. فادي عبد الكافي "
                        "دعدوش و عن والديه و إخوته و زوجته و أولاده")
    assert "brothers" in ABOUT_EN and "إخوته" in ABOUT_AR


def test_preview_lines_single_language():
    from src.reports.report_text import patient_preview_lines
    en = "\n".join(patient_preview_lines(PATIENT, language="en"))
    assert "Diseases: Diabetes, Hypertension" in en
    assert not _AR.search(en), "EN report must contain no Arabic chars"
    ar = "\n".join(patient_preview_lines(PATIENT, language="ar"))
    assert "الأمراض: Diabetes, Hypertension" in ar
    # Purity is about LABELS, not stored values: an AR report for a
    # Latin-named patient still holds Latin values (name, diseases,
    # address). No English label may appear in the AR rendering.
    _EN_LABELS = ("Patient Information", "Complaint", "Diagnosis",
                  "Procedures", "Cost Summary", "X-Ray", "Notes",
                  "Diseases:", "File Number", "Full Name", "Birth",
                  "Age", "Nationality", "Mobile", "Emergency",
                  "Address", "Created", "Total:", "Paid:", "Remaining:",
                  "Status:", "Selected Teeth", "Doctor Signature",
                  "No complaints", "No X-rays", "No notes")
    assert not any(lbl in ar for lbl in _EN_LABELS), \
        [lbl for lbl in _EN_LABELS if lbl in ar]
    # Round 23: no sadaqah/developer footer in previews either.
    assert "المطور" not in ar and "صدقة" not in ar
    assert "the developer" not in en and "Sadaqah" not in en


def test_preview_lines_language_override_and_missing_diseases():
    from src.reports.report_text import patient_preview_lines
    en = patient_preview_lines(PATIENT, language="en")
    ar = patient_preview_lines(PATIENT, language="ar")
    assert en != ar
    assert any("Diseases:" in ln for ln in en)
    assert any("الأمراض:" in ln for ln in ar)
    no_dis = dict(PATIENT)
    no_dis.pop("diseases")
    lines = "\n".join(patient_preview_lines(no_dis, language="en"))
    assert "Diseases: None" in lines  # missing key = empty, no crash


def test_clinic_name_header():
    """Round 21 (item 13) supersedes the round-16 header spec: the
    header is the clinic name ALONE (or the report's own title
    when unset -- never the app name); the app-name line appears
    only as the LAST line (footer, small)."""
    from src.models.database import set_setting
    from src.reports.pdf_common import APP_LINE, clinic_name
    from src.reports.report_text import patient_preview_lines
    with isolated_db():
        set_setting("clinic_name", "Smile Clinic")
        assert clinic_name() == "Smile Clinic"
        lines = patient_preview_lines(PATIENT, language="en")
        assert lines[0] == "Smile Clinic"
        assert lines[-1] == APP_LINE
        assert "ANADOCTORFADY" not in lines[1]
        set_setting("clinic_name", "")
        assert clinic_name() == ""
        assert patient_preview_lines(PATIENT, language="en")[0] == "Patient Report"
        set_setting("clinic_name", "ANADOCTORFADY")  # legacy seed value
        assert clinic_name() == ""  # app name itself counts as unset
        assert patient_preview_lines(PATIENT, language="en")[0] == "Patient Report"


def test_footer_and_diseases_in_pdf():
    out = _make_pdf(out_dir=_TMP)
    assert Path(out).exists() and Path(out).stat().st_size > 2000
    txt = _pdf_text(out)
    if txt is None:
        return
    # Round 23: the sadaqah/developer sentence must NOT appear.
    assert "the developer Dr Fady" not in txt
    assert "Sadaqah" not in txt and "charity" not in txt.lower()
    assert "Diabetes, Hypertension" in txt
    assert not _AR.search(txt), "EN PDF must contain no Arabic chars"
    out_ar = _make_pdf(language="ar", out_dir=_TMP)
    txt_ar = _pdf_text(out_ar)
    # Arabic in the PDF is stored reshaped (presentation forms), so
    # match the reshaped word, not the logical spelling.
    import arabic_reshaper
    assert txt_ar is not None
    assert arabic_reshaper.reshape("المطور") not in txt_ar
    assert arabic_reshaper.reshape("صدقة") not in txt_ar
    # Regression: AR table-header labels used to render blank (Arabic
    # set in Helvetica) — diagnosis + cost headers must extract.
    from src.reports.pdf_report import create_patient_pdf
    full_ar = create_patient_pdf(
        PATIENT,
        [{"complaint": "ألم", "symptoms": "حساسية", "visit_date": "2026-11-11"}],
        [{"visit_date": "2026-11-11", "tooth_number": "36", "diagnosis": "تسوس عميق"}],
        [{"visit_date": "2026-11-11", "tooth_number": "36", "procedure_done": "سحب عصب"}],
        [{"total_cost": 120000, "paid_amount": 50000, "currency": "SYP"}],
        [], language="ar", user_name="fady", out_dir=_TMP)
    txt_full = _pdf_text(full_ar)
    assert txt_full is not None
    for word in ("التاريخ", "السن", "التشخيص", "المجموع", "المدفوع",
                 "المتبقي", "الحالة", "الأمراض"):
        assert arabic_reshaper.reshape(word) in txt_full, word
    # Latin stored values must survive in an AR report too (NotoAr
    # drops Latin glyphs unless wrapped in a Helvetica font tag):
    # patient name, diseases, nationality.
    assert "Test Patient" in txt_full
    assert "Diabetes, Hypertension" in txt_full
    assert "Syrian" in txt_full
