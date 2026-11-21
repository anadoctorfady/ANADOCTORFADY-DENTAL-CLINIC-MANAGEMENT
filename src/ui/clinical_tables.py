"""Clinical tables: complaint/symptoms, diagnosis, procedures sections
(Item 5, 2026-11-08; round 12 Jobs 3a-3d; round 15 restyle).

Round 15: the four fields are FOUR separate tables (compact
height-2 fields with their own internal scrollbar + wheel scrolling,
see clinical_table_style.build_field_row), each coloured in the
app's main iOS27 family with PROGRESSIVE darkening (violet ->
magenta -> coral -> teal, each darker than the previous, light and
dark mode); every text pair stays >= 4.5:1. Round 19 (item 3):
the tables sit ALL IN ONE ROW (1x4, superseding the round-15 2x2
grid) at the top of the clinical RIGHT area, with the visit-notes
row and the Save visit button directly under them (clinical_
save_row), reachable without scrolling.

Each field has a SMALL picker button beside it that opens the template
picker over the COMBINED pool (all specialties merged - no specialty
tabs/picker any more). The doctor can also type free text.
Multi-select clipboard (Ctrl+Shift+V) still works on every field,
silently: there are no per-row action buttons and no text mentioning
that feature anywhere in this UI.

Round 16 (2026-11-11): ONE "Save visit" button below the 2x2 grid
saves all four inputs at once (clinical_save.save_all); the
per-table Add buttons are gone. That also fixes the "text required"
bug: the old per-kind add() read only txt_<kind>, while the symptom
table's Add button was wired to kind "complaint" -- text typed in
the Symptoms box was invisible to it. The tables are SHORTER than
round 15: the Add-button row is gone and paddings are tighter (the
fields stay height 2, pinned by test_clinical_tables_r15).

Round 12: every field is NARROWER, with a SMALL notes field beside
it. Round 17 (item 6): those four per-field notes are REPLACED by
ONE visit-notes entry in the save row, immediately before the Save
visit button; it is part of the visit but NOT required (the save
gate below never includes it). On save its text is written to every
saved row's notes column (complaints.notes / symptoms_notes,
diagnoses.notes, procedures.notes - see clinical_save.save_all).
Saving is BLOCKED until ALL FOUR fields are filled (complaint,
symptoms, diagnosis, procedure) - the error names the missing
field(s) and nothing is saved. Every insert records the author
(logged-in user) and created_at, which the 24h edit rule needs.
<200 lines."""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from src.config.strings import t
from src.config.strings_r16_clinical import r16_t
from src.config.theme import current, is_dark, RADIUS_TABLE
from src.models.database import get_connection
from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame
from src.ui.clinical_table_style import ORDER, build_field_row, r15_t, table_colors
from src.ui import clinical_save_row as _save_row
from src.ui.rounded_lists import RoundedText  # the tables' fields ARE RoundedText (built by build_field_row); kept for the round-13 static guard
TABLES = {"complaint": ("complaints", "complaint"),
          "diagnosis": ("diagnoses", "diagnosis"),
          "procedure": ("procedures", "procedure_done")}
TITLES = {"complaint": "clinical.complaint_title",
          "symptom": "clinical.symptoms_title",
          "diagnosis": "clinical.diagnosis_title",
          "procedure": "clinical.procedure_title"}
FIELD_LABELS = {"complaint": "clinical.complaint_label",
                "symptom": "clinical.symptoms_label",
                "diagnosis": "clinical.diagnosis_label",
                "procedure": "clinical.procedure_label"}
FIELD_ATTRS = {"complaint": "txt_complaint", "symptom": "txt_sym",
               "diagnosis": "txt_diagnosis", "procedure": "txt_procedure"}
# (field key, widget attr, table that stores it) - the save gate.
FIELDS = (("complaint", "txt_complaint", "complaints"),
          ("symptom", "txt_sym", "complaints"),
          ("diagnosis", "txt_diagnosis", "diagnoses"),
          ("procedure", "txt_procedure", "procedures"))
FIELD_KEYS = {"complaint": "savegate.complaint",
              "symptom": "savegate.symptom",
              "diagnosis": "savegate.diagnosis",
              "procedure": "savegate.procedure"}

def _text(tab, attr):
    w = getattr(tab, attr, None)
    return w.get("1.0", tk.END).strip() if w is not None else ""

def _has_today(fid, table):
    """True when a row of `table` was already saved for this patient
    today (a field saved earlier in this visit still counts)."""
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM {table} WHERE patient_file=? "
                    "AND visit_date=? LIMIT 1",
                    (fid, datetime.now().strftime("%Y-%m-%d")))
        row = cur.fetchone(); conn.close()
        return row is not None
    except Exception:
        return False

def missing_fields(tab):
    """Field keys not yet filled: empty text AND no row saved today
    for this patient. Empty list = the visit may be saved."""
    fid = (getattr(tab.app, "current_patient", None) or {}).get("file_number")
    missing = []
    for key, attr, table in FIELDS:
        if _text(tab, attr):
            continue
        if fid and table and _has_today(fid, table):
            continue
        missing.append(key)
    return missing

def display_kinds(lang):
    """Round 23 (item 1): the four tables' on-screen left-to-right
    order for `lang`. EN keeps ORDER (complaint -> symptoms ->
    diagnosis -> procedure); AR REVERSES it, so complaint is
    RIGHTMOST and the row reads complaint -> symptoms ->
    diagnosis -> procedure from the right. The UI is rebuilt on
    language toggle, so build_sections reads the app language at
    build time."""
    return ORDER if lang != "ar" else tuple(reversed(ORDER))


def build_sections(tab, parent):
    """Create the four entry tables ALL IN ONE ROW (round 19 item
    3: 1x4, each about a quarter of the right area's width). Sets
    tab.txt_complaint / txt_sym / txt_diagnosis / txt_procedure and
    tab.picker_buttons {field: button} (one small picker per field).
    Round 17: NO per-field notes in the row - ONE visit-notes entry
    (tab.txt_visit_note) sits in the notes row under the tables,
    with the Save visit button in its own row directly under that
    (clinical_save_row.build_save_row, called with `parent`).
    tab.sections_grid is the row frame; tab.table_frames maps each
    kind to its RoundedFrame (tests assert the 1x4 positions).
    Round 23: grid columns follow display_kinds(app language) --
    tab.table_order records that left-to-right kind order."""
    tab.picker_buttons = {}
    tab.table_frames = {}
    grid = tk.Frame(parent, bg=parent["bg"])
    grid.pack(fill="x", pady=0)
    for col in range(len(ORDER)):
        grid.columnconfigure(col, weight=1)
    tab.sections_grid = grid
    kinds = display_kinds(getattr(tab.app, "lang", "en"))
    tab.table_order = kinds
    for i, kind in enumerate(kinds):
        _section(tab, grid, kind, 0, i)
    # Notes row + Save row (visit-notes entry, Templates, Save
    # button) live in clinical_save_row.py (200-line cap here).
    _save_row.build_save_row(tab, parent, lambda: add(tab))

def _section(tab, grid, kind, row, col):
    """One coloured table in the one-row layout: title + one compact
    field. No per-table Add button (round 16): the single Save
    button below the row saves all four inputs at once."""
    lang = getattr(tab.app, "lang", "en")
    cols = table_colors(kind, is_dark())
    frm = RoundedFrame(grid, bg=cols["bg"], border=current()["border"], radius=RADIUS_TABLE)
    frm.grid(row=row, column=col, sticky="nsew", padx=3, pady=1)
    tab.table_frames[kind] = frm
    # Round 19: quarter-width tables - the title wraps at its real
    # width (dynamic wraplength) instead of clipping mid-word.
    _title = tk.Label(frm.inner, text=r15_t(TITLES[kind], lang), bg=cols["bg"], fg=cols["title_fg"],
             font=("Segoe UI", 8, "bold"), justify="left")
    _title.pack(anchor="w", padx=8, pady=(2, 0))
    _title.bind("<Configure>", lambda e: _title.config(wraplength=max(e.width - 4, 40)))
    build_field_row(tab, frm.inner, kind, FIELD_ATTRS[kind],
                    t(FIELD_LABELS[kind], lang), height=2)
    # Round 17: no per-field notes in the grid (one visit-notes
    # entry in the save row instead) - drop the widget build_field_row
    # created beside this field.
    _save_row.drop_field_note(tab, kind, FIELD_ATTRS[kind])

def add(tab, kind=None):
    """Save the visit (round 16): one button saves all four inputs.
    `kind` is ignored, kept so older callers (tests, ClinicalTab.add)
    keep working. Round 24: when the tab carries the unified table
    (entry money widgets present), the save routes to the unified
    Save-session handler (clinical + session money together);
    standalone hosts keep clinical_save.save_all."""
    if getattr(tab, "e_sess_total", None) is not None:
        from src.ui.clinical_session_save import save_session
        return save_session(tab)
    from src.ui.clinical_save import save_all
    return save_all(tab)

def _clear(tab, kind):
    """Clear the saved field; the <field>_note names all alias the
    ONE visit-notes widget (round 17), so clearing any saved kind
    also clears the visit note. A complaint save also clears the
    symptoms field, which shares its row."""
    for attr in (f"txt_{kind}", f"txt_{kind}_note"):
        w = getattr(tab, attr, None)
        if w is not None:
            w.delete("1.0", tk.END)
    if kind == "complaint":
        for attr in ("txt_sym", "txt_sym_note"):
            w = getattr(tab, attr, None)
            if w is not None:
                w.delete("1.0", tk.END)
