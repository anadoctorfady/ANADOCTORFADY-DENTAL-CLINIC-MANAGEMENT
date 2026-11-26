"""Patient PDF - single-language by default (app language). Clinic name
on top when set, app name smaller black under it; diseases included."""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, Image as RLImage)
from src.reports.pdf_styles import styles, IOS, FONT_EN
from src.reports.pdf_common import (reports_dir, report_header,
                                    footer_block, _av, name_value, name_style, top_strip)
from src.config.strings_r16_print import PDF_LABELS
from src.utils.arabic import ar
from src.utils.hijri_age import format_birth_date, format_hijri_date
from src.utils.helpers import unique_report_filename
from src.models.currency import default_currency, LABELS
from src.models.finance_totals import group_raw_amounts
def _p(text, style):
    return Paragraph(text, style)
def create_patient_pdf(patient, complaints=None, diagnoses=None,
        procedures=None, financial=None, xrays=None, language="en",
        bilingual=False, user_name="fady", tooth_selection=None, notes=None,
        out_dir=None):
    complaints, diagnoses = complaints or [], diagnoses or []
    procedures, financial, xrays = procedures or [], financial or [], xrays or []
    # Save location: `reports_dir` setting ("" = default reports
    # folder); out_dir lets the preview generate into a temp folder first.
    out = unique_report_filename(patient.get("full_name", "patient"),
                                 out_dir or reports_dir(),
                                 patient.get("file_number"))
    doc = SimpleDocTemplate(str(out), pagesize=A4, topMargin=12*mm,
        bottomMargin=12*mm, leftMargin=10*mm, rightMargin=10*mm,
        title=f"ANADOCTORFADY - {patient.get('full_name')}")
    st = styles(); story = []
    L = PDF_LABELS["ar" if language == "ar" else "en"]
    _ar = language == "ar" and not bilingual  # single-language Arabic
    # Arabic labels need reshaping + the Arabic font: raw Arabic in
    # Helvetica renders blank, unreshaped extracts reversed.
    _lab = lambda k: ar(L[k]) if _ar else PDF_LABELS["en"][k]
    hbold = st["cell_bold_ar"] if _ar else st["cell_bold_en"]
    _cv = st["cell_ar"] if _ar else st["cell_en"]
    story += report_header(st, language, bilingual)
    def title(en, ar_t):
        if bilingual:
            return Table([[ _p(en, st["h2_en"]), _p(ar(ar_t), st["h2_ar"]) ]],
                         colWidths=[90*mm, 90*mm])
        return _p(ar(ar_t) if language == "ar" else en,
                  st["h2_ar"] if language == "ar" else st["h2_en"])
    p = patient
    # Birth DD/MM/YYYY in every language (DB stores ISO); Hijri is RE-DERIVED per cell language, never the stored string (R25).
    try: birth_display = format_birth_date(p.get("birth_date_greg", ""))
    except Exception: birth_display = str(p.get("birth_date_greg", ""))
    story.append(title("1. Patient Information", "١. معلومات المريض"))
    age = f"{p.get('age_years',0)}y {p.get('age_months',0)}m {p.get('age_days',0)}d"
    if bilingual:
        data = [
            [_p("File No", st["cell_bold_en"]), _p(str(p.get("file_number","")), st["cell_en"]),
             _p(ar("رقم الملف"), st["cell_bold_ar"]), _p(str(p.get("file_number","")), st["cell_en"])],
            [_p("Full Name", st["cell_bold_en"]), _p(name_value(p.get("full_name","")), name_style(st, p.get("full_name",""))),
             _p(ar("الاسم الكامل"), st["cell_bold_ar"]), _p(name_value(p.get("full_name","")), name_style(st, p.get("full_name","")))],
            [_p("Birth (Greg.)", st["cell_bold_en"]), _p(birth_display, st["cell_en"]),
             _p(ar("الميلاد (هجري)"), st["cell_bold_ar"]), _p(_av(format_hijri_date(p.get("birth_date_greg",""), "ar")), st["cell_ar"])],
            [_p("Age", st["cell_bold_en"]), _p(age, st["cell_en"]),
             _p(ar("الجنسية"), st["cell_bold_ar"]), _p(_av(p.get("nationality","")), st["cell_ar"])],
            [_p("Mobile 1 / 2", st["cell_bold_en"]), _p(f"{p.get('mobile1','')} / {p.get('mobile2','')}", st["cell_en"]),
             _p(ar("هاتف الطوارئ"), st["cell_bold_ar"]), _p(str(p.get("emergency_phone","")), st["cell_en"])],
            [_p("Address", st["cell_bold_en"]), _p(str(p.get("address","")), st["cell_en"]),
             _p(ar("تاريخ الإنشاء"), st["cell_bold_ar"]), _p(str((p.get("created_at") or "")[:10]), st["cell_en"])],
        ]
    elif language == "ar":
        data = [
            [_p(ar("رقم الملف"), st["cell_bold_ar"]), _p(str(p.get("file_number","")), st["cell_en"]),
             _p(ar("الاسم الكامل"), st["cell_bold_ar"]), _p(name_value(p.get("full_name","")), name_style(st, p.get("full_name","")))],
            [_p(ar("تاريخ الميلاد (ميلادي)"), st["cell_bold_ar"]), _p(birth_display, st["cell_en"]),
             _p(ar("تاريخ الميلاد (هجري)"), st["cell_bold_ar"]), _p(_av(format_hijri_date(p.get("birth_date_greg",""), "ar")), st["cell_ar"])],
            [_p(ar("العمر"), st["cell_bold_ar"]), _p(age, st["cell_en"]),
             _p(ar("الجنسية"), st["cell_bold_ar"]), _p(_av(p.get("nationality","")), st["cell_ar"])],
            [_p(ar("موبايل ١ / ٢"), st["cell_bold_ar"]), _p(f"{p.get('mobile1','')} / {p.get('mobile2','')}", st["cell_en"]),
             _p(ar("هاتف الطوارئ"), st["cell_bold_ar"]), _p(str(p.get("emergency_phone","")), st["cell_en"])],
            [_p(ar("العنوان"), st["cell_bold_ar"]), _p(_av(p.get("address","")), st["cell_ar"]),
             _p(ar("تاريخ الإنشاء"), st["cell_bold_ar"]), _p(str((p.get("created_at") or "")[:10]), st["cell_en"])],
        ]
    else:
        data = [
            [_p("File Number", st["cell_bold_en"]), _p(str(p.get("file_number","")), st["cell_en"]),
             _p("Full Name", st["cell_bold_en"]), _p(name_value(p.get("full_name","")), name_style(st, p.get("full_name","")))],
            [_p("Birth (Greg.)", st["cell_bold_en"]), _p(birth_display, st["cell_en"]),
             _p("Birth (Hijri)", st["cell_bold_en"]), _p(format_hijri_date(p.get("birth_date_greg",""), "en"), st["cell_en"])],
            [_p("Age", st["cell_bold_en"]), _p(age, st["cell_en"]),
             _p("Nationality", st["cell_bold_en"]), _p(str(p.get("nationality","")), st["cell_en"])],
            [_p("Mobile 1 / 2", st["cell_bold_en"]), _p(f"{p.get('mobile1','')} / {p.get('mobile2','')}", st["cell_en"]),
             _p("Emergency", st["cell_bold_en"]), _p(str(p.get("emergency_phone","")), st["cell_en"])],
            [_p("Address", st["cell_bold_en"]), _p(str(p.get("address","")), st["cell_en"]),
             _p("Created", st["cell_bold_en"]), _p(str((p.get("created_at") or "")[:10]), st["cell_en"])],
        ]
    t = Table(data, colWidths=[32*mm, 58*mm, 32*mm, 58*mm])
    t.setStyle(TableStyle([('ROWBACKGROUNDS', (0,0), (-1,-1), [white, HexColor("#F2F8FF")]),
        ('BACKGROUND', (0,0), (0,-1), IOS["primary"]),
        ('BACKGROUND', (2,0), (2,-1), IOS["dark"]),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor("#D1D1D6")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(t); story.append(Spacer(1, 4*mm))
    # Diseases from the patient row (missing key = empty, never crash).
    _dis = str(p.get("diseases") or "").strip()
    if bilingual:
        story.append(_p(f"Diseases: {_dis or 'None'}", st["normal_en"]))
        story.append(_p(f"{ar("الأمراض")}: {_av(_dis) if _dis else ar('لا يوجد')}", st["normal_ar"]))
    else:
        story.append(_p(f"{_lab('diseases')}: {_av(_dis) if _dis else _lab('none')}",
                        st["normal_ar"] if _ar else st["normal_en"]))
    story.append(Spacer(1, 2*mm))
    if tooth_selection:
        story.append(title("Selected Teeth", "الأسنان المختارة"))
        story.append(_p(", ".join(tooth_selection), st["normal_en"]))
    story.append(title("2. Complaint & Symptoms", "٢. الشكوى والأعراض"))
    for c in complaints or [None]:
        if c is None:
            story.append(_p("No complaints." if language=="en" else ar("لا توجد شكوى."), st["normal_ar"] if _ar else st["normal_en"])); break
        txt = c.get("complaint","") + (" | "+c.get("symptoms","") if c.get("symptoms") else "")
        story.append(_p(ar(txt) if language=="ar" else txt, st["normal_ar"] if language=="ar" else st["normal_en"]))
    story.append(title("3. Initial Diagnosis", "٣. التشخيص الأولي"))
    if diagnoses:
        rows = [[_p(_lab("date"), hbold), _p(_lab("tooth"), hbold), _p(_lab("diagnosis_col"), hbold)]]
        for d in diagnoses:
            rows.append([_p(d.get("visit_date",""), st["cell_en"]), _p(d.get("tooth_number",""), st["cell_en"]),
                         _p(ar(d.get("diagnosis","")) if language=="ar" else d.get("diagnosis",""), st["cell_ar"] if language=="ar" else st["cell_en"])])
        dt = Table(rows, colWidths=[35*mm, 25*mm, 120*mm])
        dt.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), HexColor("#5E5CE6")),
            ('GRID', (0,0), (-1,-1), 0.5, HexColor("#D1D1D6"))]))
        story.append(dt)
    story.append(title("4. Procedures Performed", "٤. الإجراءات العلاجية"))
    for pr in procedures or []:
        _line = f"{pr.get('visit_date','')} - {pr.get('tooth_number','')}: {pr.get('procedure_done','')}"
        story.append(_p(ar(_line) if language == "ar" else _line, st["normal_ar"] if language == "ar" else st["normal_en"]))
    story.append(title("5. Cost Summary", "٥. ملخص التكلفة"))
    if financial:
        rows = financial if isinstance(financial, list) else [financial]
        # R23 item 6: group by each row's OWN currency (raw amounts,
        # NO conversion, NO cross-currency sums). One currency -> the
        # document's cost summary is entirely in that currency; mixed
        # -> one row per currency with its own Total/Paid/Remaining.
        groups = group_raw_amounts(rows)
        if len(groups) == 1:
            g = groups[0]; cur = g["currency"]
            ft = Table([[ _p(_lab("total"), hbold), _p(f"{g['total']:.2f} {cur}", st["cell_en"]),
                          _p(_lab("paid"), hbold), _p(f"{g['paid']:.2f} {cur}", st["cell_en"])],
                         [_p(_lab("remaining"), hbold), _p(f"{g['remaining']:.2f} {cur}", st["cell_en"]),
                          _p(_lab("status"), hbold), _p(_lab("paid_status") if g["remaining"]<=0 else _lab("due_status"), _cv) ]],
                       colWidths=[30*mm, 60*mm, 30*mm, 60*mm])
            ft.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), HexColor("#FF9F0A")), ('BACKGROUND', (2,0), (2,-1), HexColor("#FF9F0A")),
                ('GRID', (0,0), (-1,-1), 0.5, HexColor("#D1D1D6"))]))
            story.append(ft)
        else:
            mrows = [[_p("", hbold), _p(_lab("total"), hbold), _p(_lab("paid"), hbold), _p(_lab("remaining"), hbold)]]
            for g in groups:
                mrows.append([_p(g["currency"], st["cell_bold_en"]), _p(f"{g['total']:.2f} {g['currency']}", st["cell_en"]),
                              _p(f"{g['paid']:.2f} {g['currency']}", st["cell_en"]), _p(f"{g['remaining']:.2f} {g['currency']}", st["cell_en"])])
            mt = Table(mrows, colWidths=[30*mm, 50*mm, 50*mm, 50*mm])
            mt.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), HexColor("#FF9F0A")),
                ('GRID', (0,0), (-1,-1), 0.5, HexColor("#D1D1D6"))]))
            story.append(mt)
    story.append(title("6. X-Ray Images", "٦. صور الأشعة"))
    for xr in xrays or []:
        story.append(_p(f"• {xr.get('description','') or xr.get('file_path','')}", st["normal_ar"] if language == "ar" else st["normal_en"]))
        fp = xr.get("file_path","")
        if fp and Path(fp).exists() and Path(fp).suffix.lower() in (".jpg",".jpeg",".png"):
            try: story.append(RLImage(fp, width=80*mm, height=60*mm, kind='proportional'))
            except Exception: pass
    if not xrays:
        story.append(_p("No X-rays." if language=="en" else ar("لا توجد صور أشعة."), st["normal_ar"] if _ar else st["normal_en"]))
    story.append(title("7. Notes", "٧. ملاحظات"))
    if notes is None:  # fetch from DB by patient file number
        notes = []
        try:
            from src.models.notes import fetch_notes
            notes = fetch_notes(p.get("file_number"))
        except Exception:
            notes = []
    if notes:
        for n in notes:
            if isinstance(n, str):
                _t, _a, _d = n, "", ""
            else:
                _t, _a, _d = n.get("note", ""), n.get("author", ""), n.get("visit_date", "")
            _line = f"{_d} - {_a}: {_t}" if (_a or _d) else _t
            story.append(_p(ar(_line) if language == "ar" else _line, st["normal_ar"] if language == "ar" else st["normal_en"]))
    else:
        story.append(_p("No notes." if language == "en" else ar("لا توجد ملاحظات."), st["normal_ar"] if _ar else st["normal_en"]))
    # Report line + signature + app-name footer (pdf_common; round 23:
    # no free/charity (sadaqah) sentence in print), dark text for B&W.
    story += footer_block(st, language, bilingual, user_name)
    def footer(canvas, doc):
        canvas.saveState(); canvas.setFillColor(IOS["primary"])
        canvas.roundRect(10*mm, 282*mm, 190*mm, 6*mm, 2*mm, fill=1, stroke=0)
        canvas.setFillColor(white); canvas.setFont(FONT_EN, 8)  # R37: banner 8pt (was 7pt); app footer stays the only 7pt
        canvas.drawCentredString(105*mm, 284.5*mm, top_strip())
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return str(out)
