"""Round 18 (item 8): patient invoice PDF — DETAILED (every payment:
date + time, amount, what it was for) or SUMMARY (current bill only).
`payments` are financials rows (dicts). Round 23 (item 6): the invoice
is issued in the currency the patient PAID in — RAW paid_amount /
total_cost in each row's OWN currency (never the converted *_syp base
amounts): one currency -> the whole document is in it; mixed ->
per-payment lines in their own currencies plus a per-currency
Total/Paid/Remaining breakdown (group_raw_amounts). The `totals` /
`currency` params are only a fallback when there are no rows at all.
Rows are DELTAS, so a payment row = a row whose paid component is
non-zero. A row's "what for" is its tooth_number (financials has NO description
column); the time of day lives in updated_at (visit_date is date-only,
created_at is NULL for save_financial rows). Header/footer follow
pdf_report.py (round 21): clinic name ALONE on top at 18pt -- or the
invoice title when unset -- app name only in the footer at 7pt,
dark text (clear in B&W); REMAINING is amber + bold (patient_alerts
BALANCE tokens). Single language per `lang`; Arabic shaped via
src.utils.arabic.ar + the pdf_styles Arabic fonts, as pdf_report.py."""
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable)
from src.reports.pdf_styles import styles, IOS, FONT_EN, FONT_EN_B, FONT_AR, FONT_AR_B
from src.reports.pdf_common import reports_dir, footer_block, _av, APP_LINE, clinic_name as _clinic_setting, name_value, name_style, top_strip
from src.reports.centre_logo import logo_header_flowables
from src.config.strings_r16_print import PDF_LABELS
from src.config.strings_r18_invoice import inv_t
from src.utils.arabic import ar, has_arabic
from src.utils.helpers import unique_report
from src.models.finance_totals import group_raw_amounts
REM_BG, REM_FG = HexColor("#F59E0B"), HexColor("#1F2937")  # BALANCE_BG/FG
PAID_BG = HexColor("#E7E5E4")
def _fmt(v): return f"{float(v or 0):,.2f}"
def _paid_base(row):
    v = row.get("paid_syp")
    return float(v) if v is not None else float(row.get("paid_amount") or 0)
def _rows(payments, raw):
    """Payment rows: paid rows only, oldest first. raw=True -> RAW paid_amount + own currency (R23); raw=False -> base amounts, pre-R23 shape."""
    out = []
    for r in payments or []:
        amt = float(r.get("paid_amount") or 0) if raw else _paid_base(r)
        if abs(amt) < 1e-9: continue
        stamp = str(r.get("updated_at") or r.get("created_at") or "")
        time = stamp[11:16] if len(stamp) >= 16 and stamp[10] in "T " else ""
        date = str(r.get("visit_date") or "")[:10]
        d = {"when": f"{date} {time}".strip(), "amount": amt,
             "tooth": str(r.get("tooth_number") or "").strip(), "_k": (date, r.get("id") or 0)}
        if raw: d["currency"] = _row_cur(r)
        out.append(d)
    out.sort(key=lambda x: x["_k"])
    for o in out: o.pop("_k", None)
    return out
def payment_rows(payments):
    return _rows(payments, False)
def _for_plain(row, lang):
    return inv_t("inv.tooth", lang).format(tooth=row["tooth"]) if row["tooth"] else inv_t("inv.general", lang)
def _row_cur(row):
    return (str(row.get("currency") or "").strip().upper()) or _currency(None)
def _detail_rows(payments):
    return _rows(payments, True)
def _doc_groups(payments, totals, currency):
    """Per-currency RAW totals, grouped from the rows; `totals` (base) only when row-less."""
    groups = group_raw_amounts(payments)
    if groups: return groups
    th = _totals(payments, totals)
    return [{"currency": _currency(currency), "total": th["total"], "paid": th["paid"], "remaining": th["remaining"]}]
def _totals(payments, totals):
    if totals is not None:
        return {k: float(totals.get(k) or 0) for k in ("total", "paid", "remaining")}
    tot = sum(float(r.get("total_syp") if r.get("total_syp") is not None else (r.get("total_cost") or 0)) for r in payments or [])
    paid = sum(_paid_base(r) for r in payments or [])
    return {"total": tot, "paid": paid, "remaining": tot - paid}
def _currency(currency):
    if currency: return currency
    try:
        from src.models.currency import default_currency
        return default_currency()
    except Exception: return "SYP"
def _clinic(clinic_name):
    c = _clinic_setting() if clinic_name is None else str(clinic_name or "")
    return "" if c.strip().upper() == "ANADOCTORFADY" else c.strip()
def _header(st, lang, clinic):
    """Round 21 header: clinic name ALONE at 18pt when set, else the invoice title; app name only in the footer."""
    _ar = lang == "ar"
    if clinic:
        _ct, _cf = (ar(clinic), FONT_AR_B) if has_arabic(clinic) else (clinic, FONT_EN_B)
        _txt, _fnt = f"<b>{_ct}</b>", _cf
    elif _ar: _txt, _fnt = ar(inv_t("inv.title", "ar")), FONT_AR_B
    else: _txt, _fnt = f"<b>{inv_t('inv.title', 'en')}</b>", FONT_EN_B
    head_st = ParagraphStyle("InvHead", parent=st["title_en"], fontName=_fnt, fontSize=18, textColor=HexColor("#1C1C1E"), alignment=TA_CENTER)
    from src.reports.centre_contact import centre_contact_flowables; return logo_header_flowables() + [Paragraph(_txt, head_st)] + centre_contact_flowables(st) + [HRFlowable(width="100%", thickness=1.2, color=IOS["primary"], spaceAfter=6)]
def invoice_preview_lines(patient, payments, totals, kind="detailed", lang="en", clinic_name=None, currency=None):
    """Plain-text rendering of the invoice in ONE language — same sections/order as the PDF; used by the print preview + tests."""
    p = patient or {}; clinic = _clinic(clinic_name)
    L = PDF_LABELS["ar" if lang == "ar" else "en"]; groups = _doc_groups(payments, totals, currency)
    from src.reports.centre_contact import centre_contact_lines
    _contact = [v for v in centre_contact_lines() if v]
    lines = ([clinic] + _contact + [""] if clinic else _contact) + [f"{inv_t('inv.title', lang)} — {inv_t('inv.' + kind, lang)}",
             f"{inv_t('inv.patient', lang)}: {p.get('full_name', '')}",
             f"{inv_t('inv.file_number', lang)}: {p.get('file_number', '')}",
             f"{inv_t('inv.issued', lang)}: {datetime.now():%Y-%m-%d %H:%M}", ""]
    if kind == "detailed":
        lines.append(inv_t("inv.payments_title", lang))
        rows = _detail_rows(payments)
        lines += [f"{r['when']} | {_for_plain(r, lang)} | {_fmt(r['amount'])} {r['currency']}" for r in rows] or [inv_t("inv.no_payments", lang)]
        lines.append("")
    else:
        lines += [inv_t("inv.summary_note", lang), ""]
    for g in groups:  # one currency -> plain lines; mixed -> one block per currency, code on every line
        sfx = f" ({g['currency']})" if len(groups) > 1 else ""
        lines += [f"{inv_t('inv.total', lang)}{sfx}: {_fmt(g['total'])} {g['currency']}",
                  f"{inv_t('inv.paid', lang)}{sfx}: {_fmt(g['paid'])} {g['currency']}",
                  f"{inv_t('inv.remaining', lang)}{sfx}: {_fmt(g['remaining'])} {g['currency']}"]
    # Round 23 (2026-11-17, print only): no free/charity (sadaqah)
    # sentence -- app name alone, last, as in PDF.
    lines += ["", APP_LINE]
    return lines
def _out_file(patient, out_path):
    base = f"INVOICE_{patient.get('full_name', 'patient')}"
    if out_path is None: return Path(unique_report(base, reports_dir(), patient.get("file_number")))
    p = Path(out_path)
    if p.is_dir() or not p.suffix:
        p.mkdir(parents=True, exist_ok=True)
        return Path(unique_report(base, p, patient.get("file_number")))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
def invoice_data(fid):
    """(patient dict, financials rows, patient_totals) for one patient file."""
    from src.models.database import get_connection
    from src.models.finance import patient_totals
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE file_number=?", (fid,)); pat = dict(cur.fetchone())
    cur.execute("SELECT * FROM financials WHERE patient_file=? ORDER BY id", (fid,))
    rows = [dict(r) for r in cur.fetchall()]; conn.close()
    return pat, rows, patient_totals(fid)
def build_invoice_pdf(patient, payments, totals, kind="detailed", lang="en", clinic_name=None, out_path=None, currency=None, user_name="fady"):
    """Build the invoice PDF; returns the output path (str)."""
    kind = kind if kind in ("detailed", "summary") else "summary"
    lang = "ar" if lang == "ar" else "en"; _ar = lang == "ar"
    p = patient or {}; groups = _doc_groups(payments, totals, currency)
    out = _out_file(p, out_path)
    doc = SimpleDocTemplate(str(out), pagesize=A4, topMargin=12 * mm, bottomMargin=12 * mm, leftMargin=10 * mm, rightMargin=10 * mm, title=f"ANADOCTORFADY Invoice - {p.get('full_name', '')}")
    st = styles(); story = _header(st, lang, _clinic(clinic_name))
    _lab = lambda k: ar(inv_t(k, "ar")) if _ar else inv_t(k, "en")
    hbold = st["cell_bold_ar"] if _ar else st["cell_bold_en"]
    _cv = st["cell_ar"] if _ar else st["cell_en"]; _nv = st["normal_ar"] if _ar else st["normal_en"]; _P = Paragraph
    story.append(_P(ar(f"{inv_t('inv.title', 'ar')} — {inv_t('inv.' + kind, 'ar')}") if _ar else f"{inv_t('inv.title', 'en')} — {inv_t('inv.' + kind, 'en')}", st["h2_ar"] if _ar else st["h2_en"]))
    name_v = name_value(p.get("full_name", ""))  # R25: word order + font follow the NAME's script, not the document language
    info = [[_P(_lab("inv.patient"), hbold), _P(name_v, name_style(st, p.get("full_name", ""))), _P(_lab("inv.file_number"), hbold), _P(str(p.get("file_number", "")), st["cell_en"])],
            [_P(_lab("inv.issued"), hbold), _P(f"{datetime.now():%Y-%m-%d %H:%M}", st["cell_en"]), _P("", hbold), _P("", st["cell_en"])]]
    t = Table(info, colWidths=[32 * mm, 58 * mm, 32 * mm, 58 * mm])
    t.setStyle(TableStyle([("ROWBACKGROUNDS", (0, 0), (-1, -1), [white, HexColor("#F2F8FF")]), ("BACKGROUND", (0, 0), (0, -1), IOS["primary"]), ("BACKGROUND", (2, 0), (2, -1), IOS["dark"]), ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#D1D1D6")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(t); story.append(Spacer(1, 4 * mm))
    if kind == "detailed":
        story.append(_P(_lab("inv.payments_title"), st["h2_ar"] if _ar else st["h2_en"]))
        rows = _detail_rows(payments)
        if rows:
            body = [[_P(_lab("inv.col_datetime"), hbold), _P(_lab("inv.col_for"), hbold), _P(_lab("inv.col_amount"), hbold)]]
            for r in rows:
                if _ar and r["tooth"]: _for = ar(inv_t("inv.tooth", "ar").split("{")[0].strip()) + f" <font name=\"Helvetica\">{r['tooth']}</font>"
                elif _ar: _for = ar(inv_t("inv.general", "ar"))
                else: _for = _for_plain(r, "en")
                body.append([_P(r["when"], st["cell_en"]), _P(_for, _cv), _P(f"{_fmt(r['amount'])} {r['currency']}", st["cell_en"])])
            dt = Table(body, colWidths=[52 * mm, 78 * mm, 50 * mm])
            dt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), HexColor("#5E5CE6")), ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#D1D1D6")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.append(dt)
        else: story.append(_P(_lab("inv.no_payments"), _nv))
        story.append(Spacer(1, 4 * mm))
    else:
        story.append(_P(_lab("inv.summary_note"), _nv)); story.append(Spacer(1, 2 * mm))
    rem_st = ParagraphStyle("InvRem", parent=st["cell_en"], fontName=FONT_EN_B, fontSize=11, textColor=REM_FG)  # amounts stay Latin-font in AR too (NotoAr drops Latin)
    lab_rem = ParagraphStyle("InvRemLab", parent=hbold, fontSize=11, textColor=REM_FG)
    # Totals: one 3-row block per currency (R23); single currency = the pre-R23 table.
    trows, tstyle = [], [("GRID", (0, 0), (-1, -1), 0.5, HexColor("#D1D1D6")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for gi, g in enumerate(groups):
        sfx = f" ({g['currency']})" if len(groups) > 1 else ""
        lab_t = (_lab("inv.total") + (f' <font name="Helvetica">{g["currency"]}</font>' if _ar and sfx else sfx))
        lab_p = (_lab("inv.paid") + (f' <font name="Helvetica">{g["currency"]}</font>' if _ar and sfx else sfx))
        lab_r0 = ar(inv_t("inv.remaining", "ar")) if _ar else inv_t("inv.remaining", "en")
        lab_r = lab_r0 + (f' <font name="Helvetica">{g["currency"]}</font>' if _ar and sfx else sfx)
        base_i = gi * 3
        trows += [[_P(lab_t, hbold), _P(f"{_fmt(g['total'])} {g['currency']}", st["cell_en"])],
                  [_P(lab_p, hbold), _P(f"{_fmt(g['paid'])} {g['currency']}", st["cell_en"])],
                  [_P(lab_r, lab_rem), _P(f"{_fmt(g['remaining'])} {g['currency']}", rem_st)]]
        tstyle += [("BACKGROUND", (0, base_i), (0, base_i + 1), HexColor("#FF9F0A")),
                   ("BACKGROUND", (0, base_i + 2), (-1, base_i + 2), REM_BG if g["remaining"] > 0 else PAID_BG)]
    tot = Table(trows, colWidths=[45 * mm, 135 * mm]); tot.setStyle(TableStyle(tstyle))
    story.append(tot); story += footer_block(st, lang, False, user_name)
    def _banner(canvas, doc_):
        canvas.saveState(); canvas.setFillColor(IOS["primary"])
        canvas.roundRect(10 * mm, 282 * mm, 190 * mm, 6 * mm, 2 * mm, fill=1, stroke=0)
        canvas.setFillColor(white); canvas.setFont(FONT_EN, 8)  # R37: banner 8pt (was 7pt); app footer stays the only 7pt
        canvas.drawCentredString(105 * mm, 284.5 * mm, top_strip())
        canvas.restoreState()
    doc.build(story, onFirstPage=_banner, onLaterPages=_banner)
    return str(out)
