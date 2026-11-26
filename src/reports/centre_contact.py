"""Round 52, Section E: centre contact identity for print headers.

The centre's address / mobile / landline live in Settings beside
the clinic name (keys centre_address, centre_phone -- the MOBILE,
relabelled in R52 but never renamed -- and centre_landline). All
start EMPTY on every install. Round 54, Section F adds a SECOND
mobile (centre_mobile2, directly under the first mobile in
Settings, empty by default). centre_contact_flowables() renders
one centred line per NON-EMPTY field for the header block of all
four printed documents (report, prescription, invoice,
referral); when all are empty it returns [], so documents stay
byte-identical to round 51.
"""
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

from src.reports.pdf_styles import FONT_AR
from src.utils.arabic import ar, has_arabic


def _get_setting(key, default=""):
    try:
        from src.config.settings import get_setting
        return get_setting(key, default) or default
    except Exception:
        return default


def centre_contact_lines():
    """(address, mobile, mobile 2, landline) raw strings, "" when
    unset. R54: the second mobile sits between the first mobile
    and the landline."""
    return (str(_get_setting("centre_address", "") or "").strip(),
            str(_get_setting("centre_phone", "") or "").strip(),
            str(_get_setting("centre_mobile2", "") or "").strip(),
            str(_get_setting("centre_landline", "") or "").strip())


def centre_contact_flowables(st):
    """Centred contact lines for a print header: one line per
    NON-EMPTY centre field, in the header's style family (10pt,
    centred, dark). The script follows the VALUE (an Arabic address
    takes the Arabic font, even in an English document)."""
    out = []
    base = ParagraphStyle("CentreContact", parent=st["small"],
                          fontSize=10, alignment=TA_CENTER,
                          textColor=HexColor("#1C1C1E"))
    ar_st = ParagraphStyle("CentreContactAr", parent=base,
                           fontName=FONT_AR)
    for value in centre_contact_lines():
        if value:
            out.append(Paragraph(ar(value), ar_st) if has_arabic(value)
                       else Paragraph(value, base))
    return out
