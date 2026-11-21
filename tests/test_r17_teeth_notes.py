"""Round 17 item 6: tooth numbers in ALL FOUR fields + ONE visit note.

(a) Selecting teeth on the chart inserts their numbers into the
    complaint, symptoms, diagnosis AND procedures fields (round 16
    had procedures only), each number at most once per field, typed
    text never deleted on deselect.
(b) The four per-field note entries are gone from the 2x2 grid;
    ONE visit-notes entry sits in the save row immediately before
    the "Save visit" button. It is NOT part of the all-four-fields
    save gate, and on save its text is written to every saved row's
    notes column (complaints.notes + symptoms_notes,
    diagnoses.notes, procedures.notes).

GUI tests skip gracefully with no display; run with DISPLAY=:98
against the isolated gate copy (ANADOCTORFADY_DATA_DIR).
"""
import tkinter as tk
from unittest import mock

from src.models.database import get_connection
from src.ui import clinical_tables
from src.ui.chart_status import insert_selected_teeth
from src.ui.rounded_lists import RoundedText
from tests.test_clinical_save_gate import (
    _build_tab, _cleanup, _count, _fill, _seed_patient)

FIELDS = ("txt_complaint", "txt_sym", "txt_diagnosis", "txt_procedure")
NOTE = "review in one week"

def _text(tab, attr):
    return getattr(tab, attr).get("1.0", tk.END).strip()

def _tokens(tab, attr):
    return _text(tab, attr).replace(",", " ").split()

def _cleanup_all(fid):
    try:
        conn = get_connection(); cur = conn.cursor()
        for tbl in ("complaints", "diagnoses", "procedures"):
            cur.execute(f"DELETE FROM {tbl} WHERE patient_file=?", (fid,))
        conn.commit(); conn.close()
    except Exception:
        pass
    _cleanup(fid)

def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)

def test_teeth_inserted_into_all_four_fields_no_duplicates():
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid); print("SKIP (no display)"); return
    try:
        # Typed text first: numbers are appended, never replacing it.
        tab.txt_complaint.insert("1.0", "Toothache")
        tab.chart.toggle("16")
        tab.chart.toggle("11")
        root.update_idletasks()
        for attr in FIELDS:
            toks = _tokens(tab, attr)
            assert toks.count("16") == 1, (attr, _text(tab, attr))
            assert toks.count("11") == 1, (attr, _text(tab, attr))
        assert _text(tab, "txt_complaint").startswith("Toothache"), \
            _text(tab, "txt_complaint")
        # Empty fields get the plain comma-joined convention.
        assert _text(tab, "txt_procedure") == "16, 11", \
            _text(tab, "txt_procedure")
        # Deselect + reselect: no duplicates, nothing deleted.
        tab.chart.toggle("16")
        root.update_idletasks()
        for attr in FIELDS:
            assert "16" in _tokens(tab, attr), (attr, _text(tab, attr))
        tab.chart.toggle("16")
        insert_selected_teeth(tab, ["16", "11"])
        root.update_idletasks()
        for attr in FIELDS:
            toks = _tokens(tab, attr)
            assert toks.count("16") == 1 and toks.count("11") == 1, \
                (attr, _text(tab, attr))
    finally:
        root.destroy(); _cleanup_all(fid)

def test_visit_saves_with_empty_visit_notes():
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid); print("SKIP (no display)"); return
    try:
        _fill(tab)
        assert _text(tab, "txt_visit_note") == ""
        # The gate looks at the four fields only, never the note.
        assert clinical_tables.missing_fields(tab) == []
        with mock.patch.object(clinical_tables.messagebox,
                               "showerror") as err:
            tab.btn_save_visit.invoke()
        assert not err.called, f"empty note blocked the save: {err.call_args}"
        assert _count("complaints", fid) == 1
        assert _count("diagnoses", fid) == 1
        assert _count("procedures", fid) == 1
        conn = get_connection(); cur = conn.cursor()
        row = cur.execute("SELECT notes, symptoms_notes FROM complaints "
                          "WHERE patient_file=?", (fid,)).fetchone()
        assert not row["notes"] and not row["symptoms_notes"], dict(row)
        conn.close()
    finally:
        root.destroy(); _cleanup_all(fid)

def test_visit_note_persists_on_rows_and_visible_after_load():
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid); print("SKIP (no display)"); return
    try:
        _fill(tab)
        tab.txt_visit_note.insert("1.0", NOTE)
        with mock.patch.object(clinical_tables.messagebox,
                               "showerror") as err:
            tab.btn_save_visit.invoke()
        assert not err.called, f"save failed: {err.call_args}"
        conn = get_connection(); cur = conn.cursor()
        row = cur.execute("SELECT * FROM complaints WHERE patient_file=?",
                          (fid,)).fetchone()
        assert row["notes"] == NOTE and row["symptoms_notes"] == NOTE, dict(row)
        row = cur.execute("SELECT * FROM diagnoses WHERE patient_file=?",
                          (fid,)).fetchone()
        assert row["notes"] == NOTE, dict(row)
        row = cur.execute("SELECT * FROM procedures WHERE patient_file=?",
                          (fid,)).fetchone()
        assert row["notes"] == NOTE, dict(row)
        conn.close()
        # The entry cleared with the rest of the saved visit.
        assert _text(tab, "txt_visit_note") == ""
        # History load path. ROUND-24 SUPERSESSION: the per-table
        # row dicts are gone; the loaded SESSION carries the texts,
        # and the note is what the unified edit restores into
        # txt_visit_note (clinical_session_entry.session_note).
        from src.ui.clinical_session_entry import session_note
        tab.app.current_patient = {"file_number": fid}
        tab.load(fid)
        root.update_idletasks()
        assert len(tab._history_sessions) == 1, tab._history_sessions
        sess = tab._history_sessions[0]
        assert sess["diagnosis"] and sess["procedure"]
        assert session_note(sess) == NOTE, sess
    finally:
        root.destroy(); _cleanup_all(fid)

def test_no_per_field_note_widgets_in_grid():
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid); print("SKIP (no display)"); return
    try:
        # Round 18 moved the save row into a sticky bottom bar (item 5);
        # its geometry only resolves once the window is really mapped,
        # so map it at the owner's size before the x-order check below.
        root.geometry("1380x1000"); root.deiconify()
        root.update_idletasks(); root.update()
        # Each table frame holds exactly ONE RoundedText: its field.
        for kind, frm in tab.table_frames.items():
            texts = [w for w in _walk(frm) if isinstance(w, RoundedText)]
            assert len(texts) == 1, (kind, len(texts))
            assert texts[0] is getattr(tab, dict(
                complaint="txt_complaint", symptom="txt_sym",
                diagnosis="txt_diagnosis",
                procedure="txt_procedure")[kind]), kind
        # The four legacy note names alias the ONE visit-note widget.
        assert hasattr(tab, "txt_visit_note")
        for attr in ("txt_complaint_note", "txt_sym_note",
                     "txt_diagnosis_note", "txt_procedure_note"):
            assert getattr(tab, attr) is tab.txt_visit_note, attr
        # Save rows: the note lives in the notes row and the Save
        # button in its OWN row directly under it. Round 19 item 3
        # supersedes the round-18 sticky bar: both rows now live
        # in the fixed input block at the top of the right area,
        # under the one-row tables (no sticky_bar any more).
        assert tab.txt_visit_note.master is tab.visit_note_row
        assert tab.btn_save_visit.master is tab.save_row
        chain = []
        _w = tab.txt_visit_note.master
        while _w is not None:
            chain.append(_w); _w = _w.master
        assert tab.input_block in chain and tab.sections_grid not in chain
        assert not hasattr(tab, "sticky_bar")
        assert (tab.btn_save_visit.winfo_rooty()
                > tab.txt_visit_note.winfo_rooty())
        assert "visit_note" in tab.clipboard_fields
        for name in ("complaint_note", "symptom_note",
                     "diagnosis_note", "procedure_note"):
            assert name not in tab.clipboard_fields, name
    finally:
        root.destroy(); _cleanup_all(fid)
