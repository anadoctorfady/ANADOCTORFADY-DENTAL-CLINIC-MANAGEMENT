"""Round 16 worker C: plain-text rendering of the patient report
in ONE language (the app language, or the preview's override).
Same sections, in the same order, as create_patient_pdf() — used by
the print preview, and the test hook for single-language purity (no
Arabic chars in an EN rendering; no Latin words apart from the app
name, codes and numbers in an AR one). <200 lines.
"""
from src.config.strings_r16_print import PDF_LABELS
from src.models.currency import default_currency
from src.models.finance_totals import group_raw_amounts
from src.reports.pdf_common import _labels, clinic_name, APP_LINE, REPORT_TITLE


def patient_preview_lines(patient, complaints=None, diagnoses=None,
                          procedures=None, financial=None, xrays=None,
                          language="en", tooth_selection=None, notes=None):
    """Plain-text rendering of the patient report in ONE language
    (the app language, or the preview's override): same sections, in
    the same order, as create_patient_pdf(). Used by the print
    preview; also the test hook for single-language purity (no Arabic
    chars in an EN rendering, no Latin words — apart from the app
    name, codes and numbers — in an AR one)."""
    L = _labels(language)
    p = patient or {}
    lines = []
    clinic = clinic_name()
    # Round 21 mirror of report_header(): clinic name alone, else
    # the report's own title; the app name is the LAST line only.
    lines.append(clinic if clinic else REPORT_TITLE["ar" if language == "ar" else "en"])
    lines.append("")
    try:
        from src.utils.hijri_age import format_birth_date, format_hijri_date
        birth = format_birth_date(p.get("birth_date_greg", ""))
        # Re-derive Hijri from the Gregorian value in the report's
        # language -- never the stored string (may be other-language).
        birth_hijri = format_hijri_date(p.get("birth_date_greg", ""), language)
    except Exception:
        birth = str(p.get("birth_date_greg", ""))
        birth_hijri = ""
    age = f"{p.get('age_years', 0)}y {p.get('age_months', 0)}m {p.get('age_days', 0)}d"
    lines.append(L["patient_info"])
    for key, val in ((L["file_number"], p.get("file_number", "")),
                     (L["full_name"], p.get("full_name", "")),
                     (L["birth"], birth),
                     (L["birth_hijri"], birth_hijri),
                     (L["age"], age),
                     (L["nationality"], p.get("nationality", "")),
                     (L["mobile"], f"{p.get('mobile1', '')} / {p.get('mobile2', '')}"),
                     (L["emergency"], p.get("emergency_phone", "")),
                     (L["address"], p.get("address", "")),
                     (L["created"], str((p.get("created_at") or "")[:10]))):
        lines.append(f"{key}: {val}")
    dis = str(p.get("diseases") or "").strip()
    lines.append(f"{L['diseases']}: {dis or L['none']}")
    lines.append("")
    if tooth_selection:
        lines.append(L["selected_teeth"])
        lines.append(", ".join(tooth_selection))
        lines.append("")
    lines.append(L["complaint"])
    if complaints:
        for c in complaints:
            txt = c.get("complaint", "") + (" | " + c.get("symptoms", "")
                                            if c.get("symptoms") else "")
            lines.append(txt)
    else:
        lines.append(L["no_complaints"])
    lines.append("")
    lines.append(L["diagnosis"])
    if diagnoses:
        for d in diagnoses:
            lines.append(f"{d.get('visit_date', '')} - {d.get('tooth_number', '')}: "
                         f"{d.get('diagnosis', '')}")
    lines.append("")
    lines.append(L["procedures"])
    for pr in procedures or []:
        lines.append(f"{pr.get('visit_date', '')} - {pr.get('tooth_number', '')}: "
                     f"{pr.get('procedure_done', '')}")
    lines.append("")
    lines.append(L["cost"])
    rows = financial if isinstance(financial, list) else ([financial] if financial else [])
    if rows:
        # R23 item 6: per-currency RAW totals (mirrors the PDF) --
        # never summed across currencies under the first row's code.
        groups = group_raw_amounts(rows)
        for g in groups:
            sfx = f" ({g['currency']})" if len(groups) > 1 else ""
            lines.append(f"{L['total']}{sfx}: {g['total']:.2f} {g['currency']}")
            lines.append(f"{L['paid']}{sfx}: {g['paid']:.2f} {g['currency']}")
            lines.append(f"{L['remaining']}{sfx}: {g['remaining']:.2f} {g['currency']}")
            lines.append(f"{L['status']}{sfx}: {L['paid_status'] if g['remaining'] <= 0 else L['due_status']}")
    lines.append("")
    lines.append(L["xrays"])
    if xrays:
        for xr in xrays:
            lines.append(f"• {xr.get('description', '') or xr.get('file_path', '')}")
    else:
        lines.append(L["no_xrays"])
    lines.append("")
    lines.append(L["notes"])
    if notes is None:
        notes = []
        try:
            from src.models.notes import fetch_notes
            notes = fetch_notes(p.get("file_number"))
        except Exception:
            notes = []
    if notes:
        for n in notes:
            if isinstance(n, str):
                lines.append(n)
            else:
                _t = n.get("note", "")
                _a, _d = n.get("author", ""), n.get("visit_date", "")
                lines.append(f"{_d} - {_a}: {_t}" if (_a or _d) else _t)
    else:
        lines.append(L["no_notes"])
    lines.append("")
    # Round 23 (2026-11-17, print only): no free/charity (sadaqah)
    # sentence in the preview either -- it mirrors the PDF, whose
    # last line is the app name alone (footer corner, 7pt in PDF).
    lines.append(APP_LINE)
    return lines
