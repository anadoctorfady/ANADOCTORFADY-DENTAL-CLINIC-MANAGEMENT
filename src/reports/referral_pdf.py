"""Round 24 (item 1): patient referral PDF — the printed form of
a referrals row (round 19): clinic header, patient + file number,
referral date, referring doctor (from_user), referred-to doctor
(to_doctor), the reason / notes (template text included), and a
signature space for the referring doctor.

Conventions follow invoice_pdf.py / pdf_common.py (round 21/23):
the clinic name ALONE on top at 18pt centred when set -- otherwise
the referral title itself is the header (report_header()'s own
fallback is the *patient report* title, so the invoice-style
header is used here); the footer is pdf_common.footer_block():
report line + doctor-signature space + the app name exactly
once at 7pt in the corner, NO sadaqah sentence. Single language
per document (`lang`); Arabic is shaped via src.utils.arabic.ar
and values pass through pdf_common._av, exactly as pdf_report.py
handles Arabic. Saved as ANADOCTORFADY_REFERRAL_<patient>_<date>.pdf
in the reports folder (unique_report sanitizes the name). <200 lines.
"""
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from src.config.strings_r19_referral import tr
from src.reports.pdf_styles import styles, IOS, FONT_EN_B, FONT_AR_B
from src.reports.centre_logo import logo_header_flowables
from src.reports.pdf_common import (reports_dir, footer_block, name_value,
                                    name_style, APP_LINE, clinic_name as _clinic_setting)
from src.utils.arabic import ar, has_arabic
from src.utils.helpers import unique_report


def referral_data(referral_id):
    """(patient dict, referral dict) for one referral id, or None
    when the referral does not exist. A missing patient row yields
    a stub carrying just the file number, so printing never crashes
    on a patient with missing optional fields."""
    from src.models.database import get_connection
    from src.models.referrals import get_referral
    ref = get_referral(referral_id)
    if not ref:
        return None
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM patients WHERE file_number=?",
                           (ref.get("patient_id"),)).fetchone()
    finally:
        conn.close()
    pat = dict(row) if row else {"file_number": ref.get("patient_id"),
                                 "full_name": ""}
    return pat, ref


def _clinic(clinic_name):
    c = _clinic_setting() if clinic_name is None else str(clinic_name or "")
    return "" if c.strip().upper() == "ANADOCTORFADY" else c.strip()


def _date(referral):
    return str((referral or {}).get("created_at") or "")[:10] \
        or datetime.now().strftime("%Y-%m-%d")


def _header(st, lang, clinic):
    """Clinic name ALONE at 18pt centred when set, else the
    referral title at 18pt (invoice_pdf._header pattern)."""
    _ar = lang == "ar"
    if clinic:
        _ct, _cf = (ar(clinic), FONT_AR_B) if has_arabic(clinic) \
            else (clinic, FONT_EN_B)
        _txt, _fnt = f"<b>{_ct}</b>", _cf
    elif _ar:
        _txt, _fnt = ar(tr("refer.pdf_title", "ar")), FONT_AR_B
    else:
        _txt, _fnt = f"<b>{tr('refer.pdf_title', 'en')}</b>", FONT_EN_B
    head_st = ParagraphStyle("RefHead", parent=st["title_en"],
                             fontName=_fnt, fontSize=18,
                             textColor=HexColor("#1C1C1E"),
                             alignment=TA_CENTER)
    return logo_header_flowables() + [Paragraph(_txt, head_st),
            HRFlowable(width="100%", thickness=1.2, color=IOS["primary"],
                       spaceAfter=6)]


def _out_file(patient, referral, out_path):
    base = f"REFERRAL_{patient.get('full_name', 'patient')}_{_date(referral)}"
    if out_path is None:
        return Path(unique_report(base, reports_dir(),
                                  patient.get("file_number")))
    p = Path(out_path)
    if p.is_dir() or not p.suffix:
        p.mkdir(parents=True, exist_ok=True)
        return Path(unique_report(base, p, patient.get("file_number")))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def referral_preview_lines(patient, referral, lang="en", clinic_name=None):
    """Plain-text rendering of the referral in ONE language — same
    sections/order as the PDF; used by the print preview + tests."""
    p, r = patient or {}, referral or {}
    clinic = _clinic(clinic_name)
    note = str(r.get("note") or "").strip()
    lines = ([clinic, ""] if clinic else []) + [
        tr("refer.pdf_title", lang),
        f"{tr('refer.pdf_patient', lang)}: {p.get('full_name', '')}",
        f"{tr('refer.pdf_file', lang)}: {p.get('file_number', '')}",
        f"{tr('refer.pdf_date', lang)}: {_date(r)}",
        f"{tr('refer.pdf_from', lang)}: {r.get('from_user', '')}",
        f"{tr('refer.pdf_to', lang)}: {r.get('to_doctor', '')}",
        f"{tr('refer.pdf_reason', lang)}: "
        f"{note or tr('refer.pdf_no_note', lang)}",
        "", "___________________________",
        tr("refer.pdf_signature", lang), "", APP_LINE]
    return lines


def build_referral_pdf(patient, referral, lang="en", clinic_name=None,
                       out_path=None, user_name="fady"):
    """Build the referral PDF in ONE language; returns its path (str)."""
    lang = "ar" if lang == "ar" else "en"
    _ar = lang == "ar"
    p, r = patient or {}, referral or {}
    clinic = _clinic(clinic_name)
    out = _out_file(p, r, out_path)
    doc = SimpleDocTemplate(str(out), pagesize=A4, topMargin=12 * mm,
                            bottomMargin=12 * mm, leftMargin=10 * mm,
                            rightMargin=10 * mm,
                            title=f"ANADOCTORFADY Referral - "
                                  f"{p.get('full_name', '')}")
    st = styles()
    story = _header(st, lang, clinic)
    _lab = lambda k: ar(tr(k, "ar")) if _ar else tr(k, "en")  # noqa: E731
    # Round 25: values (the patient name above all) follow the shared
    # name rule -- Arabic reshaped in EN and AR documents alike, with
    # the value's own-script font (name_style) at each cell.
    _val = lambda v: name_value(v)  # noqa: E731
    hbold = st["cell_bold_ar"] if _ar else st["cell_bold_en"]
    _cv = st["cell_ar"] if _ar else st["cell_en"]
    _nv = st["normal_ar"] if _ar else st["normal_en"]
    _P = Paragraph
    if clinic:  # clinic name was the header; the title follows as h2
        story.append(_P(_lab("refer.pdf_title"),
                        st["h2_ar"] if _ar else st["h2_en"]))
        story.append(Spacer(1, 2 * mm))
    info = [[_P(_lab("refer.pdf_patient"), hbold),
             _P(_val(p.get("full_name", "")), name_style(st, p.get("full_name", ""))),
             _P(_lab("refer.pdf_file"), hbold),
             _P(str(p.get("file_number", "")), st["cell_en"])],
            [_P(_lab("refer.pdf_date"), hbold),
             _P(_date(r), st["cell_en"]),
             _P(_lab("refer.pdf_from"), hbold),
             _P(_val(r.get("from_user", "")), name_style(st, r.get("from_user", "")))],
            [_P(_lab("refer.pdf_to"), hbold),
             _P(_val(r.get("to_doctor", "")), name_style(st, r.get("to_doctor", ""))), _P("", hbold),
             _P("", _cv)]]
    t = Table(info, colWidths=[32 * mm, 58 * mm, 32 * mm, 58 * mm])
    t.setStyle(TableStyle([
        ("SPAN", (1, 2), (-1, 2)),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [white, HexColor("#F2F8FF")]),
        ("BACKGROUND", (0, 0), (0, -1), IOS["primary"]),
        ("BACKGROUND", (2, 0), (2, 1), IOS["dark"]),
        ("BACKGROUND", (2, 2), (2, 2), IOS["primary"]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#D1D1D6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(t)
    story.append(Spacer(1, 5 * mm))
    story.append(_P(_lab("refer.pdf_reason"),
                    st["h2_ar"] if _ar else st["h2_en"]))
    story.append(Spacer(1, 2 * mm))
    note = str(r.get("note") or "").strip()
    _nst = (st["normal_ar"] if has_arabic(note) else st["normal_en"]) if note else _nv
    story.append(_P(_val(note) if note else _lab("refer.pdf_no_note"), _nst))
    # footer_block: report line + signature space for the doctor +
    # the app name once at 7pt (round 21/23 rules; no sadaqah line).
    story += footer_block(st, lang, False, user_name)
    doc.build(story)
    return str(out)
