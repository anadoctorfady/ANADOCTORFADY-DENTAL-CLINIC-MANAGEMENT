"""Single-language prescription PDF for the direct-print flow (round 16).

build_rx_pdf(patient, rx, items, lang) -> pathlib.Path.
Rules: ONE language only (the app language -- no mixed EN+AR labels);
clinic name (setting `clinic_name`) ALONE on TOP at 18pt, BLACK --
or, when unset, the prescription heading itself as the header (r21);
B&W-clear (black text on white, dark header row). The bilingual
src.reports.prescription_pdf.create_prescription_pdf stays untouched
for the old print path. <200 lines."""
import re
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape as _xml_escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from src.config.settings import REPORTS
from src.config.strings_r16_rx import rx16_t
from src.models.database import get_setting
from src.reports.centre_logo import logo_header_flowables
from src.reports.pdf_common import name_value
from src.reports.pdf_styles import FONT_AR, FONT_AR_B, FONT_EN, FONT_EN_B
from src.utils.arabic import ar
from src.utils.helpers import unique_report

BLACK = HexColor("#000000")
DARK = HexColor("#222222")
RULE = HexColor("#666666")


def _has_arabic(text):
    """True for logical Arabic (U+0600-U+06FF) and shaped forms."""
    return any("\u0600" <= ch <= "\u06ff" or "\ufb50" <= ch <= "\ufdff"
               or "\ufe70" <= ch <= "\ufeff" for ch in str(text))


def _is_shaped(text):
    """True when the text already holds presentation forms."""
    return any("\ufb50" <= ch <= "\ufdff" or "\ufe70" <= ch <= "\ufeff"
               for ch in str(text))


# Printable ASCII: exactly the range Helvetica covers and the Arabic
# font does NOT (verified cmap: NotoNaskhArabic has NO Latin letters
# and no - / | ( ) -- round 19). Any such run inside an Arabic-font
# paragraph vanished from the rendered page while pdftotext still
# extracted it, so the round-16 text tests passed on a broken PDF.
_LATIN_RUN = re.compile(r"[\x20-\x7e]+")


def _shape_mixed(text):
    """Reshape only the non-Latin segments: arabic_reshaper corrupts
    Latin runs (drops uppercase/hyphens), so split on ASCII runs,
    shape each Arabic segment, pass Latin runs through untouched."""
    parts = _LATIN_RUN.split(text)
    seps = _LATIN_RUN.findall(text)
    out = []
    for i, part in enumerate(parts):
        out.append(ar(part) if _has_arabic(part) else part)
        if i < len(seps):
            out.append(seps[i])
    return "".join(out)


def _wrap_latin(text, bold):
    """Wrap printable-ASCII runs in a Helvetica <font> tag so they
    render inside an Arabic-font paragraph (pdf_common._av pattern;
    the text is already XML-escaped, entities still parse)."""
    latin = FONT_EN_B if bold else FONT_EN
    return _LATIN_RUN.sub(
        lambda m: f'<font name="{latin}">{m.group(0)}</font>', text)


def _para(text, lang, size=9, bold=False, align=TA_LEFT, color=BLACK,
          reshape=None):
    """Single-language paragraph. Shaping follows the CONTENT, not
    the UI language (an Arabic instruction in an EN report still
    needs shaping + the Arabic font, or it prints disconnected).
    Arabic segments are reshaped (ar()); Latin segments are NEVER
    reshaped and, inside an Arabic-font paragraph, are wrapped in a
    Helvetica <font> tag -- NotoNaskhArabic has no Latin glyphs, so
    unwrapped Latin (ANADOCTORFADY, the doctor, dates, notes) was
    silently missing from the printed AR prescription (round 19)."""
    text = _xml_escape(str(text or ""))
    has_ar = _has_arabic(text)
    if reshape is None:
        reshape = has_ar and not _is_shaped(text)
    if reshape:
        text = _shape_mixed(text)
        has_ar = True
    if has_ar:
        font = FONT_AR_B if bold else FONT_AR
        align = TA_RIGHT if align == TA_LEFT else align
        text = _wrap_latin(text, bold)
    else:
        font = FONT_EN_B if bold else FONT_EN
    return Paragraph(text, ParagraphStyle(
        "x", fontName=font, fontSize=size, leading=size + 4,
        textColor=color, alignment=align))


def build_rx_pdf(patient, rx, items, lang="en", clinic_name=None,
                 out_dir=None):
    """Generate the prescription PDF in ONE language. Returns its path."""
    lang = "ar" if lang == "ar" else "en"
    if clinic_name is None:
        try:
            clinic_name = get_setting("clinic_name", "") or ""
        except Exception:
            clinic_name = ""
    # A stored "ANADOCTORFADY" is the old seed, not a clinic name
    # (printing it on top AND in the footer would print it twice):
    # treat it as unset (same rule as pdf_common.clinic_name()).
    clinic_name = str(clinic_name or "").strip()
    if clinic_name.upper() == "ANADOCTORFADY":
        clinic_name = ""
    p, r = patient or {}, rx or {}
    name = str(p.get("full_name", "patient"))
    date_s = r.get("date") or datetime.now().strftime("%Y-%m-%d")
    out = unique_report(f"RX_{name}_{date_s}", Path(out_dir) if out_dir else REPORTS,
                        p.get("file_number"))
    doc = SimpleDocTemplate(str(out), pagesize=A4, topMargin=12 * mm,
                            bottomMargin=12 * mm, leftMargin=12 * mm,
                            rightMargin=12 *mm, title=f"ANADOCTORFADY Prescription - {name}")
    L = lambda k: rx16_t(k, lang)  # noqa: E731
    story = logo_header_flowables()  # R30: centred logo above the clinic name; [] when unset
    # Round 21: clinic name ALONE on top (18pt, black); no clinic
    # name: the heading IS the header (18pt). App name: footer only.
    if clinic_name:
        story.append(_para(clinic_name, lang, size=18, bold=True, align=TA_CENTER))
        story.append(HRFlowable(width="100%", thickness=1.2, color=BLACK, spaceAfter=4))
        story.append(_para(L("rx.pdf_heading"), lang, size=13, bold=True, align=TA_CENTER))
    else:
        story.append(_para(L("rx.pdf_heading"), lang, size=18, bold=True, align=TA_CENTER))
        story.append(HRFlowable(width="100%", thickness=1.2, color=BLACK, spaceAfter=4))
    story.append(Spacer(1, 4 * mm))
    age = str(p.get("age_years", "")) or "—"
    info = [[_para(L("rx.pdf_patient"), lang, bold=True), _para(name_value(name), lang),
             _para(L("rx.pdf_file"), lang, bold=True), _para(str(p.get("file_number", "")), lang)],
            [_para(L("rx.pdf_date"), lang, bold=True), _para(str(date_s), lang),
             _para(L("rx.pdf_age"), lang, bold=True), _para(age, lang)],
            [_para(L("rx.pdf_doctor"), lang, bold=True), _para(str(r.get("doctor", "")), lang),
             _para("", lang), _para("", lang)]]
    t = Table(info, colWidths=[28 * mm, 57 * mm, 28 * mm, 57 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, RULE),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t)
    story.append(Spacer(1, 5 * mm))
    head = [_para(L("rx.pdf_drug"), lang, bold=True, color=HexColor("#FFFFFF")),
            _para(L("rx.pdf_dose"), lang, bold=True, color=HexColor("#FFFFFF")),
            _para(L("rx.pdf_frequency"), lang, bold=True, color=HexColor("#FFFFFF")),
            _para(L("rx.pdf_duration"), lang, bold=True, color=HexColor("#FFFFFF")),
            _para(L("rx.pdf_instructions"), lang, bold=True, color=HexColor("#FFFFFF"))]
    rows = [head]
    for it in items or []:
        drug = str(it.get("generic", ""))
        if it.get("brand"):
            drug += f" ({it['brand']})"
        dur = str(it.get("duration_days", ""))
        if dur:
            # Mixed "5 يوم": _para shapes the Arabic word only and
            # wraps the digit in Helvetica -- never reshape it whole.
            dur = dur + " " + L("rx.pdf_days")
        rows.append([_para(drug, "en"), _para(str(it.get("dose", "")), "en"),
                     _para(str(it.get("frequency", "")), "en"),
                     _para(dur, lang), _para(str(it.get("instructions", "")), lang)])
    dt = Table(rows, colWidths=[52 * mm, 24 * mm, 28 * mm, 24 * mm, 42 * mm])
    dt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), DARK),
                            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#FFFFFF")),
                            ("GRID", (0, 0), (-1, -1), 0.5, RULE),
                            ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(dt)
    story.append(Spacer(1, 4 * mm))
    if r.get("notes"):
        # Raw logical text: _para shapes the Arabic label/body and
        # wraps any Latin body in Helvetica (a Latin note used to
        # vanish from the AR printout -- round 19).
        story.append(_para(f"{L('rx.pdf_notes')}: {r['notes']}", lang))
        story.append(Spacer(1, 3 * mm))
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=RULE))
    issued = (f"{L('rx.pdf_issued')}: {datetime.now():%Y-%m-%d %H:%M} | "
              f"{L('rx.pdf_by')}: {r.get('doctor', '')} | ANADOCTORFADY")
    story.append(_para(issued, lang, size=8, align=TA_CENTER))  # R37: 8pt (was 7pt, owner 2026-11-21) so the 7pt app line stays uniquely smallest
    # Round 23 (item 5): no developer dedication line in print.
    story.append(Spacer(1, 10 * mm))
    story.append(_para("___________________________", lang, size=8, align=TA_CENTER))
    story.append(_para(L("rx.pdf_signature"), lang, size=8, align=TA_CENTER))
    # Round 21/31: app name only here -- very bottom, 7pt, in the
    # trailing corner (right EN / left AR), with a >=14mm clear gap
    # below the signature (17mm spacer + paragraph leading).
    story.append(Spacer(1, 17 * mm))
    story.append(_para("ANADOCTORFADY DENTAL CLINIC MANAGEMENT", lang,
                       size=7, align=TA_LEFT if lang == "ar" else TA_RIGHT))
    doc.build(story)
    return Path(out)
