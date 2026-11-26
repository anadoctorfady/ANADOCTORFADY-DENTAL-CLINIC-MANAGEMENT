"""Round 16 prescriptions helpers (worker D): refresh the clinical
right-side panels after an Rx save, and direct-print a prescription
via the print-preview contract. Kept out of prescriptions.py so that
file stays <=200 lines. <200 lines."""
from pathlib import Path
from tkinter import messagebox
from src.config.strings import t
from src.config.strings_r16_rx import rx16_t
from src.models.database import get_setting
from src.models.prescriptions import get_prescription, get_prescription_items
from src.reports.rx_report import build_rx_pdf


def _clinical_tab(rx_tab):
    """The ClinicalTab that owns this Rx section: via app.clinical in
    the real shell, else by walking up the widget tree (the section
    lives inside the clinical page's scrollable left column)."""
    app = getattr(rx_tab, "app", None)
    tab = getattr(app, "clinical", None) if app is not None else None
    if tab is not None and getattr(tab, "panel_texts", None):
        return tab
    w = getattr(rx_tab, "master", None)
    while w is not None:
        if getattr(w, "panel_texts", None):
            return w
        w = getattr(w, "master", None)
    return None


def refresh_panels_after_save(rx_tab):
    """Repaint the right-side panels after PrescriptionsTab.save().
    Calls the clinical worker's canonical `refresh_right_panels(tab)`
    when it exists; falls back to the existing
    `refresh_panels(tab, force=True)` -- force is REQUIRED because
    refresh_panels() no-ops when the patient file_number is unchanged.
    Never raises: a stale panel must never break a successful save."""
    tab = _clinical_tab(rx_tab)
    if tab is None:
        return False
    try:
        from src.ui.clinical_panels import refresh_right_panels
        refresh_right_panels(tab)
        return True
    except ImportError:
        pass
    except Exception:
        return False
    try:
        from src.ui.clinical_panels import refresh_panels
        refresh_panels(tab, force=True)
        return True
    except Exception:
        return False


def _selected_rx(rx_tab):
    """(rx dict, items) for the history row currently selected, or
    (None, None) with a warning already shown."""
    lang = getattr(rx_tab, "lang", "en")
    sel = rx_tab.tree_hist.selection()
    if not sel or not rx_tab._patient():
        messagebox.showwarning(t("rx.select_title", lang),
                               t("rx.select_rx", lang))
        return None, None
    pid = int(rx_tab.tree_hist.item(sel[0], "values")[0])
    return get_prescription(pid), get_prescription_items(pid)


def rx_preview_lines(patient, rx, items, lang="en", clinic_name=""):
    """Plain-text rendering of the prescription in ONE language, in
    the PDF's own order -- the preview_text for show_print_preview.
    Round 19 root cause: the Rx preview was the ONLY preview with no
    preview_text, so it fell back to extract_pdf_text(), which needs
    the external `pdftotext` binary. That binary exists on the Linux
    dev machines (tests passed) but is NOT part of the Windows EXE,
    and the no-pdftotext fallback scrapes raw PDF streams -- embedded
    font programs included -- producing unintelligible symbols in
    BOTH languages on the owner's machine. Logical (unshaped) text:
    Tk renders it correctly."""
    lang = "ar" if lang == "ar" else "en"
    L = lambda k: rx16_t(k, lang)  # noqa: E731
    p, r = patient or {}, rx or {}
    clinic = str(clinic_name or "").strip()
    # Round 21 (item 13): mirror the reworked PDF -- the header is
    # the clinic name alone (or the Rx heading when unset), and the
    # app-name line appears only at the very end (footer, small).
    # R54 (Section E): the preview shows the same centre-contact
    # block as the PDF header (only the fields the centre set).
    from src.reports.pdf_common import APP_LINE
    from src.reports.centre_contact import centre_contact_lines
    _contact = [v for v in centre_contact_lines() if v]
    if clinic and clinic.upper() != "ANADOCTORFADY":
        lines = [clinic] + _contact + [L("rx.pdf_heading"), ""]
    else:
        lines = [L("rx.pdf_heading")] + _contact + [""]
    lines += [f"{L('rx.pdf_patient')}: {p.get('full_name', '')}",
              f"{L('rx.pdf_file')}: {p.get('file_number', '')}",
              f"{L('rx.pdf_date')}: {r.get('date', '')}",
              f"{L('rx.pdf_age')}: {p.get('age_years', '')}",
              f"{L('rx.pdf_doctor')}: {r.get('doctor', '')}", ""]
    for it in items or []:
        drug = str(it.get("generic", ""))
        if it.get("brand"):
            drug += f" ({it['brand']})"
        dur = str(it.get("duration_days", ""))
        if dur:
            dur += " " + L("rx.pdf_days")
        lines.append(" — ".join(x for x in (drug, str(it.get("dose", "")),
                       str(it.get("frequency", "")), dur,
                       str(it.get("instructions", ""))) if x))
    if r.get("notes"):
        lines += ["", f"{L('rx.pdf_notes')}: {r['notes']}"]
    # Round 23 (item 5): no developer dedication line in print preview
    # either -- it mirrors the printed prescription.
    lines += ["", L("rx.pdf_signature"), APP_LINE]
    return lines


def print_rx_preview(rx_tab):
    """Direct-print button: preview FIRST (printing worker's contract,
    lazy import so this works before/after their module lands),
    language choice inside the preview, single language = app language
    by default. Falls back to saving the PDF directly when the preview
    module is not there yet."""
    lang = getattr(rx_tab, "lang", "en")
    rx, items = _selected_rx(rx_tab)
    if rx is None:
        return
    patient = rx_tab._patient()
    try:
        clinic = get_setting("clinic_name", "") or ""
    except Exception:
        clinic = ""

    def build_pdf_fn(chosen_lang):
        return build_rx_pdf(patient, rx, items, lang=chosen_lang,
                            clinic_name=clinic)

    def preview_text(chosen_lang):
        return rx_preview_lines(patient, rx, items, chosen_lang, clinic)

    try:
        from src.reports.print_preview import show_print_preview
    except ImportError:
        out = build_pdf_fn(lang)
        messagebox.showinfo(t("rx.pdf_title", lang),
                            rx16_t("rx.print_no_preview", lang).format(out=Path(out).name))  # R25: file NAME only, never the path
        return
    title = rx16_t("rx.print_preview_title", lang)
    # preview_text is part of the real preview contract (round 16);
    # the signature check only keeps older test doubles / partial
    # preview modules working -- they fall back to PDF extraction,
    # which report_files now keeps free of font-binary gibberish.
    import inspect
    if "preview_text" in inspect.signature(show_print_preview).parameters:
        show_print_preview(rx_tab, title, build_pdf_fn, lang,
                           preview_text=preview_text)
    else:
        show_print_preview(rx_tab, title, build_pdf_fn, lang)
