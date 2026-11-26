"""Prescription PDF - bilingual, saved in reports/ as
ANADOCTORFADY_RX_<patient>_<date>.pdf. <150 lines."""
import json
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable)
from reportlab.lib.styles import ParagraphStyle
from src.reports.pdf_styles import styles, IOS, FONT_EN, FONT_AR
from src.utils.arabic import ar, has_arabic
from src.utils.helpers import unique_report
from src.config.settings import REPORTS
from src.reports.pdf_common import top_strip

def _value(text, st):
    """Patient-supplied value in the font its OWN script needs
    (round 19): Arabic in Helvetica prints as nothing/boxes and
    Latin in NotoNaskhArabic prints as nothing (its cmap has no
    Latin glyphs) -- the font follows the content, never the UI
    language. Returns a Paragraph in cell_ar / cell_en."""
    s = str(text or "")
    if has_arabic(s):
        return Paragraph(ar(s), st["cell_ar"])
    return Paragraph(s, st["cell_en"])

def create_prescription_pdf(patient, prescription, items, language="en",
                            user_name="fady", warnings=None):
    p = patient
    name = str(p.get("full_name", "patient"))
    date_s = prescription.get("date", datetime.now().strftime("%Y-%m-%d"))
    out = unique_report(f"RX_{name}_{date_s}", REPORTS, p.get("file_number"))
    doc = SimpleDocTemplate(str(out), pagesize=A4, topMargin=12*mm,
        bottomMargin=12*mm, leftMargin=12*mm, rightMargin=12*mm,
        title=f"ANADOCTORFADY Prescription - {name}")
    st = styles(); story = []
    small_ar = ParagraphStyle('S_AR', parent=st["small"], fontName=FONT_AR)
    story.append(Table([[Paragraph("<b>ANADOCTORFADY</b>", st["title_en"]),
        Paragraph(ar("وصفة طبية - عيادة أنا دكتور فادي"), st["title_ar"])]],
        colWidths=[85*mm, 85*mm]))
    # The Arabic half needs its own <font> tag: st["sub"] is
    # Helvetica, which has no Arabic glyphs (it printed blank).
    story.append(Paragraph(
        f"Dental Clinic — Prescription / <font name=\"{FONT_AR}\">{ar('وصفة طبية')}</font>",
        st["sub"]))
    story.append(HRFlowable(width="100%", thickness=1.2,
        color=IOS["primary"], spaceAfter=6))
    age = f"{p.get('age_years', '')}y"
    info = [[Paragraph("Patient", st["cell_bold_en"]),
             _value(name, st),
             Paragraph(ar("رقم الملف"), st["cell_bold_ar"]),
             Paragraph(str(p.get("file_number", "")), st["cell_en"])],
            [Paragraph("Date", st["cell_bold_en"]),
             Paragraph(date_s, st["cell_en"]),
             Paragraph(ar("العمر"), st["cell_bold_ar"]),
             Paragraph(age, st["cell_en"])],
            [Paragraph("Doctor", st["cell_bold_en"]),
             Paragraph(str(prescription.get("doctor", user_name)), st["cell_en"]),
             Paragraph(ar("الجنسية"), st["cell_bold_ar"]),
             _value(p.get("nationality", ""), st)]]
    t = Table(info, colWidths=[28*mm, 57*mm, 28*mm, 57*mm])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, -1), IOS["primary"]),
        ('BACKGROUND', (2, 0), (2, -1), IOS["dark"]),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#D1D1D6"))]))
    story.append(t); story.append(Spacer(1, 5*mm))
    story.append(Paragraph(
        f"Rx — Medications / <font name=\"{FONT_AR}\">{ar('الأدوية')}</font>",
        st["h2_en"]))
    rows = [[Paragraph("Drug", st["cell_bold_en"]),
             Paragraph("Dose", st["cell_bold_en"]),
             Paragraph("Frequency", st["cell_bold_en"]),
             Paragraph("Duration", st["cell_bold_en"])]]
    for it in items:
        drug = str(it.get('generic', ''))
        if it.get('brand'):
            drug += f" ({it['brand']})"
        rows.append([Paragraph(drug, st["cell_en"]),
            Paragraph(str(it.get("dose", "")), st["cell_en"]),
            Paragraph(str(it.get("frequency", "")), st["cell_en"]),
            Paragraph(f"{it.get('duration_days','')} days", st["cell_en"])])
        if it.get("instructions"):
            # Was: ar()-shaped Arabic in the HELVETICA style -- the
            # instructions row printed completely blank (round 19).
            rows.append([_value(it["instructions"], st),
                         Paragraph("", st["cell_en"]), Paragraph("", st["cell_en"]),
                         Paragraph("", st["cell_en"])])
    dt = Table(rows, colWidths=[70*mm, 30*mm, 35*mm, 35*mm])
    dt.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), HexColor("#5E5CE6")),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#D1D1D6")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(dt); story.append(Spacer(1, 4*mm))
    if prescription.get("notes"):
        _notes = str(prescription["notes"])
        if has_arabic(_notes):
            story.append(Paragraph(f"Notes: {ar(_notes)}", st["normal_ar"]))
        else:
            story.append(Paragraph(f"Notes: {_notes}", st["normal_en"]))
    warns = warnings
    if warns is None:
        try:
            warns = json.loads(prescription.get("acknowledged_warnings") or "[]")
        except Exception:
            warns = []
    if warns:
        story.append(Spacer(1, 3*mm))
        story.append(Paragraph("Acknowledged interaction warnings:",
            st["h2_en"]))
        for w in warns:
            msg = w.get("message_en", "") if isinstance(w, dict) else str(w)
            story.append(Paragraph(f"⚠ {msg}", st["normal_en"]))
            if isinstance(w, dict) and w.get("message_ar"):
                story.append(Paragraph(ar(w["message_ar"]), st["normal_ar"]))
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#D1D1D6")))
    story.append(Paragraph(f"Issued: {datetime.now():%Y-%m-%d %H:%M} | By: {user_name} | ANADOCTORFADY",
        st["small"]))
    story.append(Spacer(1, 10*mm))
    story.append(Table([[Paragraph("___________________________", st["small"]),
        Paragraph("___________________________", st["small"])],
        [Paragraph("Doctor Signature", st["small"]),
         Paragraph(ar("توقيع الطبيب"), small_ar)]],
        colWidths=[85*mm, 85*mm]))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("Interaction data is a curated aid only - it does not replace clinical judgment.",
        st["small"]))
    def footer(canvas, doc):
        canvas.saveState(); canvas.setFillColor(IOS["primary"])
        canvas.roundRect(10*mm, 282*mm, 190*mm, 6*mm, 2*mm, fill=1, stroke=0)
        canvas.setFillColor(white); canvas.setFont(FONT_EN, 8)  # R37: banner 8pt (was 7pt); app footer stays the only 7pt
        canvas.drawCentredString(105*mm, 284.5*mm, top_strip())
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return str(out)
