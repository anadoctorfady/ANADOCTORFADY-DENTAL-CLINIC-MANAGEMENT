"""PDF styles + fonts (Noto Arabic). <120 lines."""
import sys
from pathlib import Path
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
BASE = Path(__file__).resolve().parent.parent.parent
# Frozen EXE: bundled fonts live in the PyInstaller temp dir (_MEIPASS).
FONTS = (Path(getattr(sys, "_MEIPASS", BASE)) / "assets" / "fonts"
         if getattr(sys, "frozen", False) else BASE / "assets" / "fonts")
FONT_AR, FONT_AR_B = "Helvetica", "Helvetica-Bold"
FONT_EN, FONT_EN_B = "Helvetica", "Helvetica-Bold"
def register():
    global FONT_AR, FONT_AR_B
    for name, fname in [("NotoAr", "NotoNaskhArabic-Regular.ttf"),
                        ("NotoArBold", "NotoNaskhArabic-Bold.ttf")]:
        p = FONTS / fname
        if p.exists():
            try:
                pdfmetrics.registerFont(TTFont(name, str(p)))
                if "Bold" in name:
                    FONT_AR_B = name
                else:
                    FONT_AR = name
            except Exception:
                pass
    if FONT_AR_B == "Helvetica-Bold" and FONT_AR != "Helvetica":
        FONT_AR_B = FONT_AR
register()
IOS = {"primary": HexColor("#0A84FF"), "dark": HexColor("#0051D5"),
       "secondary": HexColor("#5E5CE6"), "muted": HexColor("#8E8E93"),
       "text": HexColor("#1C1C1E"), "accent": HexColor("#A85F33")}
def styles():
    s = getSampleStyleSheet()
    return {
        "title_en": ParagraphStyle('T_EN', parent=s['Heading1'], fontName=FONT_EN_B,
            fontSize=16, textColor=IOS["primary"], alignment=TA_CENTER),
        "title_ar": ParagraphStyle('T_AR', parent=s['Heading1'], fontName=FONT_AR_B,
            fontSize=16, textColor=IOS["primary"], alignment=TA_CENTER),
        "sub": ParagraphStyle('Sub', parent=s['Normal'], fontName=FONT_EN,
            fontSize=9, textColor=IOS["muted"], alignment=TA_CENTER),
        "h2_en": ParagraphStyle('H2_EN', parent=s['Heading2'], fontName=FONT_EN_B,
            fontSize=11, textColor=IOS["dark"], backColor=HexColor("#E8F4FF")),
        "h2_ar": ParagraphStyle('H2_AR', parent=s['Heading2'], fontName=FONT_AR_B,
            fontSize=11, textColor=IOS["dark"], backColor=HexColor("#E8F4FF"),
            alignment=TA_RIGHT),
        "normal_en": ParagraphStyle('N_EN', parent=s['Normal'], fontName=FONT_EN,
            fontSize=9, textColor=IOS["text"], leading=13, alignment=TA_LEFT),
        "normal_ar": ParagraphStyle('N_AR', parent=s['Normal'], fontName=FONT_AR,
            fontSize=9, textColor=IOS["text"], leading=14, alignment=TA_RIGHT),
        "cell_en": ParagraphStyle('C_EN', parent=s['Normal'], fontName=FONT_EN,
            fontSize=8.5, leading=11),
        "cell_ar": ParagraphStyle('C_AR', parent=s['Normal'], fontName=FONT_AR,
            fontSize=8.5, leading=12, alignment=TA_RIGHT),
        "cell_bold_en": ParagraphStyle('CB_EN', parent=s['Normal'],
            fontName=FONT_EN_B, fontSize=8.5, textColor=white),
        "cell_bold_ar": ParagraphStyle('CB_AR', parent=s['Normal'],
            fontName=FONT_AR_B, fontSize=8.5, textColor=white, alignment=TA_CENTER),
        # Round 37 (owner decision 2026-11-21): the footer `small`
        # style is 8pt (was 7pt through round 36) so the 7pt app-name
        # footer line is the UNIQUE smallest text in every document.
        "small": ParagraphStyle('S', parent=s['Normal'], fontName=FONT_EN,
            fontSize=8, textColor=IOS["muted"], alignment=TA_CENTER),
    }
