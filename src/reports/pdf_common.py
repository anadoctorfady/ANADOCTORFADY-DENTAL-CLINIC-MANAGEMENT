"""Round 16 worker C: shared patient-report helpers.

- reports_dir(): honour the `reports_dir` setting ("" = the default
  reports folder); `clinic_name` setting ("" = no clinic name set;
  the legacy seeded value "ANADOCTORFADY" also counts as unset).
- report_header() / footer_block() (round 21): the header is the
  clinic name ONLY, large, when set -- otherwise the report's own
  title. The app name (APP_LINE) appears ONLY in footer_block(),
  at the very bottom in 7pt, so it never competes with the clinic.
- _av(): Latin stored values inside Arabic-font paragraphs.
PDF inspection (page count / text) lives in report_files.py; the
plain-text rendering in report_text.py. <200 lines.
"""
import re
from pathlib import Path
from datetime import datetime
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, HRFlowable
from src.config.settings import REPORTS, APP_NAME
from src.config.strings_r16_print import PDF_LABELS
from src.reports.centre_logo import logo_header_flowables
from src.reports.centre_contact import centre_contact_flowables
from src.reports.pdf_styles import IOS, FONT_EN, FONT_EN_B, FONT_AR, FONT_AR_B
from src.utils.arabic import ar, has_arabic

APP_LINE = "ANADOCTORFADY DENTAL CLINIC MANAGEMENT"
REPORT_TITLE = {"en": "Patient Report", "ar": "تقرير المريض"}


def _get_setting(key, default=""):
    try:
        from src.config.settings import get_setting
        return get_setting(key, default) or default
    except Exception:
        return default


def reports_dir():
    """Save folder for reports: `reports_dir` setting, or REPORTS."""
    d = str(_get_setting("reports_dir", "") or "").strip()
    if not d:
        return REPORTS
    p = Path(d).expanduser()
    try:
        p.mkdir(parents=True, exist_ok=True)
    except OSError:
        return REPORTS
    return p


def clinic_name():
    """Distinct clinic name, or "" when unset. The DB used to seed
    clinic_name=ANADOCTORFADY (the app name itself); that legacy
    value is NOT a distinct clinic name, so it counts as unset —
    otherwise the header would print ANADOCTORFADY twice."""
    name = str(_get_setting("clinic_name", "") or "").strip()
    if not name or name.upper() == APP_NAME.upper():
        return ""
    return name


def top_strip():
    """8pt banner text for the printed documents (R45): the
    `centre_phone` segment appears only when the centre set one —
    no dangling separator when it is empty."""
    p = str(_get_setting("centre_phone", "") or "").strip()
    return "ANADOCTORFADY • Dental Clinic" + (f" • {p}" if p else "")


def _p(text, style):
    return Paragraph(text, style)


def _labels(language):
    return PDF_LABELS["ar" if language == "ar" else "en"]


def _av(value):
    """Value for an Arabic-font paragraph: NotoAr drops Latin letters,
    so Latin values (name, English diseases) are wrapped in a
    Helvetica <font> tag; Arabic values are reshaped as usual."""
    s = str(value or "")
    if has_arabic(s):
        return ar(s)
    if re.search(r"[A-Za-z]", s):
        return f"<font name=\"Helvetica\">{s}</font>"
    return s


def name_value(value):
    """Patient-name value for a PDF paragraph (round 25): the word
    order follows the NAME's script, not the document language --
    a name holding any Arabic-script character (U+0600-U+06FF) is
    reshaped / bidi-displayed (_av) in EN and AR documents alike,
    so it reads first -> father -> grandfather -> family in both;
    a Latin name keeps its natural order (plain str)."""
    s = str(value or "")
    if any("\u0600" <= c <= "\u06ff" for c in s):
        return _av(s)
    return s


def name_style(styles_map, value):
    """Paragraph style matching the NAME's own script (round 25):
    an Arabic name needs the Arabic font in EVERY document
    language (Helvetica has no Arabic glyphs -- the name printed
    as boxes); a Latin name the Latin font (NotoAr drops Latin)."""
    s = str(value or "")
    return styles_map["cell_ar"] if has_arabic(s) else styles_map["cell_en"]


def report_header(st, language, bilingual=False):
    """Header flowables (round 21). The clinic name ONLY, large
    (18pt) and centred, when set; otherwise the report's own title
    line -- never the app name, which lives only in the footer.
    Bilingual keeps two-language content under the same rule.
    Fonts + reshaping follow the text, not just the report language:
    an Arabic clinic name in Helvetica renders blank, and unreshaped
    Arabic renders disconnected; a Latin clinic name in an AR report
    still needs the Latin bold font (NotoAr drops Latin, cf. _av)."""
    clinic = clinic_name()
    _logo = logo_header_flowables()  # R30: centred logo above the name; [] when unset
    if clinic and has_arabic(clinic):
        _ct, _cf = ar(clinic), FONT_AR_B
    else:
        _ct, _cf = clinic, FONT_EN_B
    # Round 23: centering is EXPLICIT here (not only inherited from
    # title_en) -- the clinic/doctor name is centred on the page.
    clinic_st = ParagraphStyle("ClinicName", parent=st["title_en"],
                               fontName=_cf, alignment=TA_CENTER,
                               fontSize=18, textColor=HexColor("#1C1C1E"))
    hr = HRFlowable(width="100%", thickness=1.2,
                    color=IOS["primary"], spaceAfter=6)
    contact = centre_contact_flowables(st)  # R52: [] when unset
    if bilingual:
        if clinic:
            return _logo + [_p(f"<b>{_ct}</b>", clinic_st)] + contact + [hr]
        return _logo + [Table([[_p(f"<b>{REPORT_TITLE['en']}</b>", st["title_en"]),
                        _p(ar(REPORT_TITLE["ar"]), st["title_ar"])]],
                       colWidths=[90 * mm, 90 * mm])] + contact + [hr]
    if clinic:
        return _logo + [_p(f"<b>{_ct}</b>", clinic_st)] + contact + [hr]
    if language == "ar":
        title_st = ParagraphStyle("ReportTitleAr", parent=st["title_ar"],
                                  fontName=FONT_AR_B, fontSize=18,
                                  alignment=TA_CENTER,
                                  textColor=HexColor("#1C1C1E"))
        return _logo + [_p(ar(REPORT_TITLE["ar"]), title_st)] + contact + [hr]
    title_st = ParagraphStyle("ReportTitle", parent=st["title_en"],
                              fontName=FONT_EN_B, fontSize=18,
                              alignment=TA_CENTER,
                              textColor=HexColor("#1C1C1E"))
    return _logo + [_p(f"<b>{REPORT_TITLE['en']}</b>", title_st)] + contact + [hr]


def footer_block(st, language, bilingual=False, user_name="fady"):
    """Report line + signature, in the report language only (both
    languages when bilingual), then the app name (APP_LINE) as the
    very last line in 7pt in the corner (round 21). Round 23 (owner
    decision 2026-11-17, PRINT ONLY): NO free/charity (sadaqah)
    sentence is printed any more. Dark text only, so the page stays
    clear in B&W. Round 31: the spacer before the app line is 12mm
    (measured signature->app-line glyph gap >= 10mm), and the corner
    follows the reading direction -- bottom-right for EN, bottom-left
    for AR (bilingual keeps right)."""
    L = _labels(language)
    # BUG FIX (round 16): st["small"] is Helvetica, which has no Arabic
    # glyphs — the Arabic footer / report line used to print as tofu
    # boxes (pdftotext showed ■). Arabic lines use the Arabic font.
    small_ar = ParagraphStyle("SmallAr", parent=st["small"], fontName=FONT_AR)
    out = [Spacer(1, 6 * mm),
           HRFlowable(width="100%", thickness=0.5, color=HexColor("#D1D1D6")),
           _p(f"{L['report']}: {datetime.now():%Y-%m-%d %H:%M} | "
              f"{L['user']}: {user_name} | ANADOCTORFADY",
              small_ar if language == "ar" else st["small"]),
           Spacer(1, 8 * mm)]
    if bilingual:
        out.append(Table([[_p("___________________________", st["small"]),
                           _p(ar("___________________________"), st["small"])],
                          [_p("Doctor Signature", st["small"]),
                           _p(ar("توقيع الطبيب"), small_ar)]],
                         colWidths=[90 * mm, 90 * mm]))
    else:
        out.append(_p("___________________________", st["small"]))
        out.append(_p(L["doctor_signature"],
                      small_ar if language == "ar" else st["small"]))
    out.append(Spacer(1, 12 * mm))
    # Round 21: the app name lives ONLY here -- very bottom, 7pt,
    # corner-aligned, subordinate to everything above. Pure Latin,
    # so always the Latin font (NotoAr has no Latin glyphs).
    app_st = ParagraphStyle("AppFooter", parent=st["small"],
                            fontName=FONT_EN, fontSize=7,
                            alignment=TA_LEFT if (language == "ar"
                                                  and not bilingual)
                            else TA_RIGHT)
    out.append(_p(APP_LINE, app_st))
    return out
