"""Round 21 (item 13): PDF header/footer rework. Owner rule: on
patient reports, prescriptions and invoices the clinic/doctor name
is the prominent header (18pt, alone); the app name
"ANADOCTORFADY DENTAL CLINIC MANAGEMENT" appears ONLY in the footer,
as the very last line, at 7pt. With no clinic name set the header
shows the document's own title instead -- never the app name.
SUPERSESSION (round 23, owner decision 2026-11-17, PRINT ONLY):
the round-21 rule "the sadaqah footer line stays" is SUPERSEDED --
that sentence must now be ABSENT from all printed documents and
previews (About dedication unchanged); assertions that required it
now assert its absence, the rest remain valid. PDF text via
pdftotext; text checks skip when it is unavailable. Isolated DB."""
import tempfile
from pathlib import Path

from tests.test_r16_print import PATIENT, isolated_db, _pdf_text

APP = "ANADOCTORFADY DENTAL CLINIC MANAGEMENT"
CLINIC = "Smile Clinic R21"
_TMP = Path(tempfile.mkdtemp(prefix="r21_pdf_"))
_RX_ITEMS = [{"generic": "Amoxicillin", "dose": "500 mg",
              "frequency": "3x daily", "duration_days": "5",
              "instructions": "After food"}]
_INV_ROWS = [{"visit_date": "2026-11-01",
              "updated_at": "2026-11-01 09:30:00", "tooth_number": "16",
              "total_syp": 400000, "paid_syp": 250000, "id": 1}]
_INV_TOTALS = {"total": 600000.0, "paid": 370000.0, "remaining": 230000.0}


def _paras(flowables):
    """(text, fontSize) per Paragraph in flowables (Tables recursed)."""
    out = []
    for f in flowables or []:
        if hasattr(f, "text") and hasattr(f, "style"):
            out.append((f.text, f.style.fontSize))
        for row in getattr(f, "_cellvalues", []) or []:
            out += _paras(list(row))
    return out


def _joined(flowables):
    return "\n".join(t for t, _ in _paras(flowables))


def _set_clinic(value):
    from src.models.database import set_setting
    set_setting("clinic_name", value)


def test_report_header_clinic_only_large():
    """Clinic set: first flowable IS the clinic name at 18pt; no
    header flowable mentions the app name (any language/bilingual)."""
    from src.reports.pdf_styles import styles
    from src.reports.pdf_common import report_header
    st = styles()
    with isolated_db():
        _set_clinic(CLINIC)
        for lang, bil in (("en", False), ("ar", False), ("en", True)):
            head = report_header(st, lang, bilingual=bil)
            first_text, first_size = _paras(head)[0]
            assert CLINIC in first_text, (lang, bil, first_text)
            assert first_size == 18, (lang, bil, first_size)
            assert "ANADOCTORFADY" not in _joined(head), (lang, bil)


def test_report_header_no_clinic_shows_title_not_app():
    """No clinic name: header is the report's own title line,
    still with no app name anywhere in it."""
    from src.reports.pdf_styles import styles
    from src.reports.pdf_common import report_header
    st = styles()
    with isolated_db():
        _set_clinic("")
        head = report_header(st, "en")
        assert "Patient Report" in _paras(head)[0][0]
        assert "ANADOCTORFADY" not in _joined(head)
        head_ar = report_header(st, "ar")
        assert "ANADOCTORFADY" not in _joined(head_ar)
        assert _paras(head_ar)[0][1] == 18  # title still large
        head_bi = report_header(st, "en", bilingual=True)
        assert "Patient Report" in _joined(head_bi)
        assert "ANADOCTORFADY" not in _joined(head_bi)


def test_footer_block_app_line_small_and_last():
    """footer_block(): app-name line exactly once, LAST, 7pt (< the
    18pt header). Report line still there; sadaqah line GONE (r23)."""
    from src.reports.pdf_styles import styles
    from src.reports.pdf_common import footer_block
    st = styles()
    for lang, bil in (("en", False), ("ar", False), ("en", True)):
        foot = footer_block(st, lang, bilingual=bil)
        paras = _paras(foot)
        texts = [t for t, _ in paras]
        assert sum(APP in t for t in texts) == 1, (lang, bil, texts)
        app_text, app_size = [p for p in paras if APP in p[0]][0]
        assert app_text.strip() == APP, app_text
        assert app_size == 7 and app_size < 18, app_size
        assert texts[-1].strip() == APP, (lang, bil, texts[-1])
    en = _joined(footer_block(st, "en"))
    # Round 23 supersession: sadaqah sentence ABSENT, report line kept.
    assert "Sadaqah Jariyah" not in en and "completely free" not in en and "Report:" in en


def test_rx_pdf_app_name_once_in_footer():
    """Real Rx PDFs: app name exactly once, after the clinic name
    and signature line (footer); no-clinic header is the heading."""
    from src.reports.rx_report import build_rx_pdf
    rx = {"date": "2026-11-15", "doctor": "fady"}
    out = build_rx_pdf(PATIENT, rx, _RX_ITEMS, lang="en",
                       clinic_name=CLINIC, out_dir=_TMP)
    txt = _pdf_text(out)
    if txt is None:
        print("SKIP rx pdf-text checks (no pdftotext)")
        return
    assert txt.count(APP) == 1, txt[:300]
    assert txt.index(CLINIC) < txt.index(APP)
    assert txt.index("Doctor Signature") < txt.index(APP)
    out2 = build_rx_pdf(PATIENT, rx, _RX_ITEMS, lang="en",
                        clinic_name="", out_dir=_TMP)
    txt2 = _pdf_text(out2)
    assert txt2.count(APP) == 1
    assert txt2.index("Prescription") < txt2.index(APP)
    out3 = build_rx_pdf(PATIENT, rx, _RX_ITEMS, lang="ar",
                        clinic_name=CLINIC, out_dir=_TMP)
    txt3 = _pdf_text(out3)
    assert txt3.count(APP) == 1 and CLINIC in txt3
    assert txt3.index(CLINIC) < txt3.index(APP)


def test_invoice_header_and_pdf():
    """Invoice _header flowables (clinic alone at 18pt / title when
    unset, no app name) + a real invoice PDF with the app name
    exactly once, in the footer, NO sadaqah line (round 23)."""
    from src.reports.pdf_styles import styles
    from src.reports.invoice_pdf import _header, build_invoice_pdf
    st = styles()
    head = _header(st, "en", CLINIC)
    assert CLINIC in _paras(head)[0][0] and _paras(head)[0][1] == 18
    assert "ANADOCTORFADY" not in _joined(head)
    head0 = _header(st, "en", "")
    assert "Invoice" in _paras(head0)[0][0]
    assert "ANADOCTORFADY" not in _joined(head0)
    out = build_invoice_pdf(PATIENT, _INV_ROWS, _INV_TOTALS, "detailed",
                            "en", CLINIC, _TMP / "inv_r21.pdf",
                            currency="SYP")
    txt = _pdf_text(out)
    if txt is None:
        print("SKIP invoice pdf-text checks (no pdftotext)")
        return
    assert txt.count(APP) == 1, txt[:300]
    assert txt.index(CLINIC) < txt.index(APP)
    assert "Sadaqah Jariyah" not in txt  # round 23 supersession


def test_patient_pdf_app_name_once_in_footer():
    """Real patient report (via pdf_common): app name exactly once,
    last, after the clinic header; NO sadaqah line (round 23);
    no-clinic header is the title."""
    from src.reports.pdf_report import create_patient_pdf
    with isolated_db():
        _set_clinic(CLINIC)
        out = create_patient_pdf(PATIENT, [], [], [], [], [],
                                 language="en", user_name="fady",
                                 out_dir=_TMP)
        txt = _pdf_text(out)
        if txt is None:
            print("SKIP patient pdf-text checks (no pdftotext)")
            return
        assert txt.count(APP) == 1, txt[:300]
        assert txt.index(CLINIC) < txt.index(APP)
        assert "Sadaqah Jariyah" not in txt  # round 23 supersession
        _set_clinic("")
        out2 = create_patient_pdf(PATIENT, [], [], [], [], [],
                                  language="en", user_name="fady",
                                  out_dir=_TMP)
        txt2 = _pdf_text(out2)
        assert txt2.count(APP) == 1 and "Patient Report" in txt2


def test_preview_lines_mirror_layout():
    """Previews mirror the PDFs: clinic (or title) first, app name
    only as the last line, exactly once."""
    from src.reports.report_text import patient_preview_lines
    from src.reports.invoice_pdf import invoice_preview_lines
    with isolated_db():
        _set_clinic(CLINIC)
        lines = patient_preview_lines(PATIENT, language="en")
        assert lines[0] == CLINIC and lines[-1] == APP
        assert "\n".join(lines).count(APP) == 1
        _set_clinic("")
        lines0 = patient_preview_lines(PATIENT, language="en")
        assert lines0[0] == "Patient Report" and lines0[-1] == APP
    inv = invoice_preview_lines(PATIENT, _INV_ROWS, _INV_TOTALS,
                                "detailed", "en", CLINIC, "SYP")
    assert inv[0] == CLINIC and inv[-1] == APP
    assert "\n".join(inv).count(APP) == 1
    inv0 = invoice_preview_lines(PATIENT, _INV_ROWS, _INV_TOTALS,
                                 "summary", "en", "", "SYP")
    assert inv0[0].startswith("Invoice") and inv0[-1] == APP
