"""Round 31 (item 3): printed footer -- signature space + app name.

For all four LIVE builders (patient report pdf_report, prescription
rx_report.build_rx_pdf -- the builder src/ui/rx_print.py calls; the
bilingual prescription_pdf.create_prescription_pdf is legacy and not
used by the UI -- invoice_pdf, referral_pdf), in EN and AR:
- APP_LINE appears EXACTLY ONCE, as the last text line, at exactly
  7pt (Tf operator in the content stream);
- it sits in the trailing corner: bottom-right for EN, bottom-left
  for AR (margin-aware, from pdftotext -bbox geometry);
- the clear glyph gap from the signature block (underscores line +
  signature label) to the app line is >= 14mm on the prescription
  and >= 10mm on the other three documents;
- a typical document still fits on ONE page.
Geometry checks skip when pdftotext is unavailable (house pattern);
the flowable-level footer_block checks always run. Isolated DB.

ROUND 37 RE-PIN NOTE (owner decision 2026-11-21): the three OTHER
7pt micro-texts this file renders alongside -- the footer `small`
style, the Rx Issued line, the top banner strip -- rose to 8pt so
the app line is the unique 7pt minimum. THIS file's pins are
unchanged (app line exactly 7.0pt, gaps >= 14/10mm) and were
re-verified against the round-37 tree; the 8pt pins live in
tests/test_r37_micro_text_8pt.py."""
import base64, re, shutil, subprocess, tempfile, zlib
import xml.etree.ElementTree as ET
from pathlib import Path

from tests.test_r16_print import PATIENT, isolated_db

APP_LINE = "ANADOCTORFADY DENTAL CLINIC MANAGEMENT"
APP_WORDS = APP_LINE.split()
_TMP = Path(tempfile.mkdtemp(prefix="r31_footer_"))
_RX = {"date": "2026-11-19", "doctor": "fady", "notes": "Take full course"}
_ITEMS = [{"generic": "Amoxicillin", "brand": "Amoxil", "dose": "500 mg",
           "frequency": "3x daily", "duration_days": "5",
           "instructions": "After food"},
          {"generic": "Ibuprofen", "brand": "Brufen", "dose": "400 mg",
           "frequency": "3x daily", "duration_days": "3",
           "instructions": "After food"}]
_ROWS = [{"visit_date": "2026-11-01", "updated_at": "2026-11-01 09:30:00",
          "tooth_number": "16", "total_cost": 400000, "paid_amount": 250000,
          "currency": "SYP", "id": 1}]
_TOTALS = {"total": 600000.0, "paid": 370000.0, "remaining": 230000.0}
_REF = {"id": 5, "patient_id": 77, "from_user": "fady",
        "to_doctor": "Dr. Sami Haddad", "note": "Please evaluate.",
        "created_at": "2026-11-17 09:15:00"}
# Side margins (pt) per builder: report/invoice/referral 10mm, Rx 12mm.
_MARGIN = {"report": 28.35, "rx": 34.02, "invoice": 28.35, "referral": 28.35}
_MIN_GAP = {"report": 10.0, "rx": 14.0, "invoice": 10.0, "referral": 10.0}
_PT2MM = 25.4 / 72.0
_NS = "{http://www.w3.org/1999/xhtml}"


def _build_all(lang, root):
    from src.reports.invoice_pdf import build_invoice_pdf
    from src.reports.pdf_report import create_patient_pdf
    from src.reports.referral_pdf import build_referral_pdf
    from src.reports.rx_report import build_rx_pdf
    root.mkdir(parents=True, exist_ok=True)
    return {
        "report": Path(create_patient_pdf(
            PATIENT, [], [], [], _ROWS, [], language=lang,
            user_name="fady", out_dir=root / "rep")),
        "rx": Path(build_rx_pdf(PATIENT, _RX, _ITEMS, lang=lang,
                                clinic_name="", out_dir=root / "rx")),
        "invoice": Path(build_invoice_pdf(
            PATIENT, _ROWS, _TOTALS, "detailed", lang, "",
            root / "inv.pdf", currency="SYP")),
        "referral": Path(build_referral_pdf(
            PATIENT, _REF, lang=lang, clinic_name="",
            out_path=root / "ref.pdf"))}


def _pages_words(pdf):
    r = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    root = ET.fromstring(r.stdout)
    pages = root.findall(f".//{_NS}page")
    words = [(w.text, float(w.get("xMin")), float(w.get("yMin")),
              float(w.get("xMax")), float(w.get("yMax")))
             for w in root.iter(f"{_NS}word")]
    page = pages[0]
    return len(pages), float(page.get("width")), words


def _app_group(words):
    """The 4 APP_LINE words on one line, x-ordered (the lone
    'ANADOCTORFADY' in the report/issued line must not match)."""
    for w in words:
        if w[0] != APP_WORDS[0]:
            continue
        line = sorted((x for x in words if abs(x[2] - w[2]) < 2.0),
                      key=lambda x: x[1])
        texts = [x[0] for x in line]
        for j in range(len(texts) - 3):
            if texts[j:j + 4] == APP_WORDS:
                return line[j:j + 4]
    return None


def _gap_mm(words, app):
    app_top = min(w[2] for w in app)
    und = [w for w in words if w[0] and set(w[0]) == {"_"}]
    assert und, "no signature underscores line found"
    u = und[-1]
    sig_bottom = max(w[4] for w in words
                     if w[2] >= u[2] - 1 and w[2] < app_top)
    return (app_top - sig_bottom) * _PT2MM


def _drawn_sizes(pdf):
    """text -> Tf size for every Tj in the content streams
    (ReportLab stores streams as ASCII85 + Flate)."""
    out = {}
    for m in re.finditer(rb"stream\r?\n(.*?)endstream",
                         Path(pdf).read_bytes(), re.S):
        try:
            s = zlib.decompress(base64.a85decode(
                m.group(1).strip(), adobe=True)).decode("latin-1")
        except Exception:
            continue
        cur = None
        for tok in re.finditer(r"/F\w+ ([\d.]+) Tf|\((.*?)(?<!\\)\) Tj", s):
            if tok.group(1):
                cur = float(tok.group(1))
            elif tok.group(2) is not None and cur is not None:
                out.setdefault(tok.group(2), cur)
    return out


def _pdf_text(pdf):
    r = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_footer_block_flowable_corner_and_size():
    """footer_block: app line LAST, 7pt, right for EN / left for AR,
    right again for bilingual (shared-layer contract, no PDF needed)."""
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT
    from src.reports.pdf_common import footer_block
    from src.reports.pdf_styles import styles
    st = styles()
    for lang, bil, want in (("en", False, TA_RIGHT),
                            ("ar", False, TA_LEFT),
                            ("en", True, TA_RIGHT)):
        foot = footer_block(st, lang, bilingual=bil)
        last = foot[-1]
        assert last.text.strip() == APP_LINE, (lang, bil, last.text)
        assert last.style.fontSize == 7, (lang, bil)
        assert last.style.alignment == want, (lang, bil, last.style.alignment)


def test_all_builders_footer_geometry_en_ar():
    if not shutil.which("pdftotext"):
        print("SKIP r31 geometry (no pdftotext)")
        return
    with isolated_db():
        from src.models.database import set_setting
        set_setting("clinic_name", "")
        for lang in ("en", "ar"):
            for kind, pdf in _build_all(lang, _TMP / lang).items():
                tag = (kind, lang, pdf.name)
                assert _pdf_text(pdf).count(APP_LINE) == 1, tag
                npages, width, words = _pages_words(pdf)
                assert npages == 1, tag  # spacer must not orphan it
                app = _app_group(words)
                assert app, tag
                ax0, ay0 = min(w[1] for w in app), min(w[2] for w in app)
                ax1 = max(w[3] for w in app)
                assert ay0 >= max(w[2] for w in words) - 0.5, tag  # last
                margin = _MARGIN[kind]
                if lang == "en":  # bottom-right: ends at the right margin
                    assert abs((width - margin) - ax1) <= 8, (tag, ax1)
                else:             # bottom-left: starts at the left margin
                    assert abs(ax0 - margin) <= 8, (tag, ax0)
                gap = _gap_mm(words, app)
                assert gap >= _MIN_GAP[kind], (tag, f"gap={gap:.2f}mm")
                drawn = _drawn_sizes(pdf)
                assert drawn.get(APP_LINE) == 7.0, (tag, drawn.get(APP_LINE))
                if kind == "rx":  # smaller than drug names + signature
                    drug = next(v for k, v in drawn.items()
                                if "Amoxicillin" in k)
                    assert drawn[APP_LINE] < drug, tag
                    assert drawn[APP_LINE] < drawn["___________________________"], tag
