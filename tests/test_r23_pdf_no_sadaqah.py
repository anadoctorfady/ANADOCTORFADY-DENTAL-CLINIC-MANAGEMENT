"""Round 23 (item 5, owner decision 2026-11-17, PRINT ONLY): the
free/charity (sadaqah) sentence is GONE from every printed document
-- patient report, prescription, invoice -- and from the previews
that mirror them, in EN and AR. The clinic/doctor name stays as the
prominent header at the top, CENTRED; the app name appears exactly
ONCE, in the bottom corner, small (7pt). The About tab dedication
is NOT touched (asserted below). Isolated DB; text via pdftotext."""
import contextlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

APP = "ANADOCTORFADY DENTAL CLINIC MANAGEMENT"
CLINIC = "Smile Clinic R23"
_TMP = Path(tempfile.mkdtemp(prefix="r23_pdf_"))
PATIENT = {"file_number": 77, "full_name": "Test Patient",
           "birth_date_greg": "1990-05-15",
           "birth_date_hijri": "20 Shawwal 1410",
           "age_years": 36, "age_months": 5, "age_days": 21,
           "nationality": "Syrian", "mobile1": "0791234567", "mobile2": "",
           "emergency_phone": "0799888777", "address": "Damascus",
           "created_at": "2026-11-05", "diseases": "Diabetes"}
_RX = {"date": "2026-11-15", "doctor": "fady"}
_RX_ITEMS = [{"generic": "Amoxicillin", "dose": "500 mg",
              "frequency": "3x daily", "duration_days": "5",
              "instructions": "After food"}]
_INV_ROWS = [{"visit_date": "2026-11-01",
              "updated_at": "2026-11-01 09:30:00", "tooth_number": "16",
              "total_syp": 400000, "paid_syp": 250000, "id": 1}]
_INV_TOTALS = {"total": 600000.0, "paid": 370000.0, "remaining": 230000.0}
# Forbidden sentence fragments: EN literal + AR in logical form
# (previews) and in reshaped form (PDF text layer is reshaped).
_EN_BAD = ("sadaqah", "jariyah", "completely free", "ongoing charity",
           "this app is free")
_AR_BAD = ("صدقة", "جارية", "مجاناً", "مجاني")


@contextlib.contextmanager
def isolated_db():
    """Temp DB copy pattern (same as tests/test_r16_print.py)."""
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
    if not shutil.which("pdftotext"):
        return None
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _assert_clean(text):
    """No trace of the sadaqah/free sentence, EN or AR, logical or reshaped."""
    low = text.lower()
    for bad in _EN_BAD:
        assert bad not in low, bad
    for bad in _AR_BAD:
        assert bad not in text, bad
    try:
        import arabic_reshaper
        for bad in _AR_BAD:
            assert arabic_reshaper.reshape(bad) not in text, bad
    except ImportError:
        pass


def _check_pdf(path, lang):
    """Clean; clinic in header region (before the app line); app name
    exactly once, in the footer region (final 15% of the text)."""
    txt = _pdf_text(path)
    if txt is None:
        print("SKIP pdf-text checks (no pdftotext)")
        return None
    _assert_clean(txt)
    assert txt.count(APP) == 1, (lang, txt[:200])
    assert CLINIC in txt, lang
    assert txt.index(CLINIC) < txt.index(APP), lang
    assert txt.index(APP) > 0.85 * len(txt), (lang, "footer region")
    return txt


def _build_all(lang):
    """(patient, rx, invoice) PDF paths for one language."""
    from src.reports.pdf_report import create_patient_pdf
    from src.reports.rx_report import build_rx_pdf
    from src.reports.invoice_pdf import build_invoice_pdf
    pat = create_patient_pdf(PATIENT, [], [], [], [], [], language=lang,
                             user_name="fady", out_dir=_TMP)
    rxp = build_rx_pdf(PATIENT, _RX, _RX_ITEMS, lang=lang,
                       clinic_name=CLINIC, out_dir=_TMP)
    inv = build_invoice_pdf(PATIENT, _INV_ROWS, _INV_TOTALS, "detailed",
                            lang, CLINIC, _TMP / f"inv_r23_{lang}.pdf",
                            currency="SYP")
    return pat, rxp, inv


def test_r23_sentence_gone_from_strings_about_kept():
    """Print strings no longer hold the sentence (empty tombstones
    only, for legacy imports); the About dedication is unchanged."""
    import src.config.strings_r16_print as sp
    assert sp.FOOTER_EN == "" and sp.FOOTER_AR == ""
    from src.config.settings import ABOUT_EN, ABOUT_AR
    assert "ongoing charity" in ABOUT_EN and "صدقة" in ABOUT_AR


def test_r23_pdfs_no_sadaqah_en_ar():
    """Patient report + prescription + invoice, EN and AR, plus a
    bilingual patient report (its footer printed BOTH versions)."""
    from src.models.database import set_setting
    from src.reports.pdf_report import create_patient_pdf
    with isolated_db():
        set_setting("clinic_name", CLINIC)
        for lang in ("en", "ar"):
            for path in _build_all(lang):
                _check_pdf(path, lang)
        bi = create_patient_pdf(PATIENT, [], [], [], [], [], language="en",
                                bilingual=True, user_name="fady",
                                out_dir=_TMP)
        _check_pdf(bi, "bilingual")


def test_r23_previews_no_sadaqah():
    """On-screen print previews mirror the PDFs: no sentence, clinic
    (or title) first, app name last and exactly once."""
    from src.models.database import set_setting
    from src.reports.report_text import patient_preview_lines
    from src.reports.invoice_pdf import invoice_preview_lines
    from src.ui.rx_print import rx_preview_lines
    with isolated_db():
        set_setting("clinic_name", CLINIC)
        for lang in ("en", "ar"):
            lines = patient_preview_lines(PATIENT, language=lang)
            _assert_clean("\n".join(lines))
            assert lines[0] == CLINIC and lines[-1] == APP
            assert "\n".join(lines).count(APP) == 1
            inv = invoice_preview_lines(PATIENT, _INV_ROWS, _INV_TOTALS,
                                        "detailed", lang, CLINIC, "SYP")
            _assert_clean("\n".join(inv))
            assert inv[0] == CLINIC and inv[-1] == APP
            assert "\n".join(inv).count(APP) == 1
            rx = rx_preview_lines(PATIENT, _RX, _RX_ITEMS, lang, CLINIC)
            _assert_clean("\n".join(rx))
            assert rx[0] == CLINIC and rx[-1] == APP
            assert "\n".join(rx).count(APP) == 1


def test_r23_header_centered_and_footer_corner():
    """Centering, measured: (1) style level -- header paragraphs are
    TA_CENTER at 18pt, app line TA_RIGHT at 7pt; (2) geometry level --
    pdftotext -bbox: clinic-name words on the header line (y 40..70pt,
    below the contact strip) centred on A4 width within 6pt, x3 docs."""
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from src.reports.pdf_styles import styles
    from src.reports.pdf_common import report_header, footer_block
    from src.reports.invoice_pdf import _header
    st = styles()
    with isolated_db():
        from src.models.database import set_setting
        set_setting("clinic_name", CLINIC)
        head = report_header(st, "en")
        assert head[0].style.alignment == TA_CENTER
        assert head[0].style.fontSize == 18
        assert _header(st, "en", CLINIC)[0].style.alignment == TA_CENTER
        foot = footer_block(st, "en")
        assert foot[-1].style.alignment == TA_RIGHT
        assert foot[-1].style.fontSize == 7
        if not shutil.which("pdftotext"):
            print("SKIP bbox checks (no pdftotext)")
            return
        for path in _build_all("en"):
            r = subprocess.run(["pdftotext", "-bbox", str(path), "-"],
                               capture_output=True, text=True, timeout=30)
            page_w = float(re.search(r'<page[^>]*width="([\d.]+)"',
                                     r.stdout).group(1))
            words = re.findall(
                r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" '
                r'yMax="([\d.]+)">([^<]+)</word>', r.stdout)
            hits = [w for w in words if w[4] in ("Smile", "Clinic", "R23")
                    and 40 < float(w[1]) < 70]
            assert hits, path
            centre = (float(hits[0][0]) + float(hits[-1][2])) / 2
            assert abs(centre - page_w / 2) < 6, (path, centre, page_w)
