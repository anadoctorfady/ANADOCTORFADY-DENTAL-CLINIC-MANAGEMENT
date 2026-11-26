"""Round 16 item 10: chart <-> clinical-tables wiring.

Procedures are stored per tooth in the procedures (and diagnoses)
tables: tooth_number holds the comma-joined teeth selected when the
row was saved (clinical_tables.save_all). teeth_records is never
written anywhere in the app, so it is NOT a source here.

- treated_teeth(fid): every tooth with a recorded procedure or
  diagnosis for this patient (for the chart status markers).
- Round 23 item 3: tooth_history / treated_details (delegated to
  chart_tooltip) carry the procedure TEXT behind each mark, and
  refresh_chart_status pushes those details into the chart too,
  so its hover tooltip + history popup work. It runs from
  clinical.load(), which Save visit reaches via
  app.refresh_clinical() -- so marks, tooltips and popups refresh
  after every save and on every patient switch.
- refresh_chart_status(tab): push that set into the chart.
- insert_selected_teeth(tab, teeth): selecting teeth auto-inserts
  their numbers into ALL FOUR clinical fields (complaint, symptoms,
  diagnosis, procedures), each number at most once per field
  (round 17 item 6; round 16 had procedures only).
"""
import tkinter as tk

from src.models.database import get_connection
from src.ui.chart_tooltip import (format_history, open_history_popup,
                                  tooth_history, treated_details)

__all__ = ["treated_teeth", "refresh_chart_status", "tooth_history",
           "treated_details", "insert_selected_teeth"]


def treated_teeth(patient_file):
    """Sorted tooth numbers with a recorded procedure/diagnosis."""
    if not patient_file:
        return []
    try:
        conn = get_connection(); cur = conn.cursor()
        found = set()
        for table in ("procedures", "diagnoses"):
            cur.execute(f"SELECT tooth_number FROM {table} "
                        "WHERE patient_file=?", (patient_file,))
            for (raw,) in cur.fetchall():
                found.update(n.strip() for n in str(raw or "").split(",")
                             if n.strip())
        conn.close()
    except Exception:
        return []
    return sorted(found)


def refresh_chart_status(tab):
    """Mark the chart's treated teeth for the current patient,
    WITH their procedure details (round 23: tooltip + popup text
    and the count badge). A patient with no procedures pushes an
    empty detail map, so no stale text survives a switch."""
    chart = getattr(tab, "chart", None)
    if chart is None or not hasattr(chart, "set_treated"):
        return
    patient = getattr(tab.app, "current_patient", None) or {}
    fid = patient.get("file_number")
    if hasattr(chart, "set_treated_details"):
        chart.set_treated_details(treated_details(fid))
    else:
        chart.set_treated(treated_teeth(fid))


# --- Round 23: chart tooltip / popup glue (called by dental_chart) ---

def bind_treated_cell(chart, widgets, tooth):
    """Hover tooltip + double-click history popup on a treated
    tooth's widgets. Bindings use add='+' so the plain-click toggle
    binding on the same widgets keeps working untouched."""
    for w in widgets:
        w.bind("<Enter>", lambda e, nn=tooth: show_tip(chart, e, nn), add="+")
        w.bind("<Leave>", lambda _e: chart._tip.hide(), add="+")
        w.bind("<Double-Button-1>",
               lambda _e, nn=tooth: open_chart_history(chart, nn), add="+")


def show_tip(chart, event, tooth):
    """Show the hover tooltip with the tooth's full history text
    at the cursor (hides instead when there are no entries)."""
    entries = chart.treated_details.get(str(tooth)) or []
    if entries:
        chart._tip.show(event.x_root, event.y_root,
                        format_history(str(tooth), entries, chart.lang))
    else:
        chart._tip.hide()


def open_chart_history(chart, tooth):
    """Open (replacing any previous) the history popup for a tooth;
    returns the popup, or None when the tooth is untreated."""
    entries = chart.treated_details.get(str(tooth)) or []
    if chart._history_win is not None:
        try:
            chart._history_win.destroy()
        except Exception:
            pass
        chart._history_win = None
    chart._history_win = open_history_popup(chart, str(tooth), entries,
                                            chart.lang)
    return chart._history_win


# The four clinical text widgets, in display order (attrs are set by
# clinical_table_style.build_field_row via clinical_tables).
FIELD_ATTRS = ("txt_complaint", "txt_sym", "txt_diagnosis", "txt_procedure")


def _insert_into(widget, teeth):
    """Append the tooth numbers not already present in `widget` as a
    comma-joined suffix (the round-16 procedures convention), keeping
    any typed text untouched."""
    cur = widget.get("1.0", tk.END).strip()
    have = {n for n in cur.replace(",", " ").split() if n}
    missing = [n for n in teeth if n not in have]
    if not missing:
        return
    new = (cur + ", " if cur else "") + ", ".join(missing)
    widget.delete("1.0", tk.END)
    widget.insert("1.0", new)


def insert_selected_teeth(tab, teeth):
    """Append newly selected tooth numbers to ALL FOUR clinical
    fields (complaint, symptoms, diagnosis, procedures), each number
    once per field; deselecting never deletes typed text."""
    if not teeth:
        return
    teeth = [str(n) for n in teeth]
    for attr in FIELD_ATTRS:
        w = getattr(tab, attr, None)
        if w is not None:
            _insert_into(w, teeth)


def _scrub_field(widget, drop):
    """Remove auto-inserted tooth numbers (the `drop` set) from one
    field: a comma segment is removed only when it consists solely
    of dropped numbers, so typed text -- even text containing a
    number inside a sentence -- is never touched."""
    cur = widget.get("1.0", tk.END).strip()
    if not cur:
        return
    kept = []
    for seg in cur.split(","):
        toks = seg.split()
        if toks and all(tok in drop for tok in toks):
            continue  # a pure auto-inserted number segment
        if seg.strip():
            kept.append(seg.strip())
    new = ", ".join(kept)
    if new != cur:
        widget.delete("1.0", tk.END)
        if new:
            widget.insert("1.0", new)


def remove_teeth_from_fields(tab, teeth):
    """Round 43: jaw-button toggle-off scrub -- remove `teeth`'
    numbers from ALL FOUR clinical fields (the exact fields
    insert_selected_teeth appends to). Scoped to the jaw buttons:
    single-tooth deselection still never deletes (round 16 rule)."""
    drop = {str(n) for n in teeth}
    if not drop:
        return
    for attr in FIELD_ATTRS:
        w = getattr(tab, attr, None)
        if w is not None:
            _scrub_field(w, drop)
