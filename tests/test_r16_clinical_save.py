"""Round 16 item 9: ONE save button + the "text required" bug fix.

The bug (reproduced on round-15 code before the fix -- see the
report): fill all four fields, save the complaint (which clears the
complaint + symptoms boxes), type NEW text into the Symptoms box and
click that table's Add button. The gate passed (a complaints row was
saved today) but add(tab, "complaint") read ONLY txt_complaint --
empty -- and reported "Text required!" although text had been
entered. The symptom table's Add button was wired to kind
"complaint", so the handler read a different widget than the one
the user typed in. save_all() reads each field from its own widget,
so the symptoms-only save now succeeds.
"""
import tkinter as tk
from unittest import mock

from src.ui import clinical_tables
from tests.test_clinical_save_gate import (
    _build_tab, _cleanup, _count, _fill, _seed_patient)


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def test_r16_single_save_button_saves_all_four():
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_r16_single_save_button_saves_all_four (no display)")
        return
    try:
        assert hasattr(tab, "btn_save_visit"), "no single Save button"
        # R24: the button is the unified "Save session" action.
        assert tab.btn_save_visit.cget("text") == "Save session"
        _fill(tab)
        # Round 17: ONE visit note, written to every notes column.
        tab.txt_visit_note.insert("1.0", "visit note")
        with mock.patch.object(clinical_tables.messagebox, "showerror") as err:
            tab.btn_save_visit.invoke()
        assert not err.called, f"save-all should succeed, got: {err.call_args}"
        assert _count("complaints", fid) == 1
        assert _count("diagnoses", fid) == 1
        assert _count("procedures", fid) == 1
        from src.models.database import get_connection
        conn = get_connection(); cur = conn.cursor()
        row = cur.execute("SELECT * FROM complaints WHERE patient_file=?",
                          (fid,)).fetchone()
        assert row["complaint"] == "Toothache" and row["symptoms"] == "Pain on chewing"
        assert row["notes"] == "visit note"
        assert row["symptoms_notes"] == "visit note"
        assert row["author"] == "dr_fady" and row["created_at"]
        row = cur.execute("SELECT * FROM diagnoses WHERE patient_file=?",
                          (fid,)).fetchone()
        assert row["diagnosis"] == "Pulpitis" and row["notes"] == "visit note"
        row = cur.execute("SELECT * FROM procedures WHERE patient_file=?",
                          (fid,)).fetchone()
        assert row["procedure_done"] == "Root canal" and row["notes"] == "visit note"
        conn.close()
        # Saved fields are cleared for the next visit.
        for attr in ("txt_complaint", "txt_sym", "txt_diagnosis", "txt_procedure"):
            assert getattr(tab, attr).get("1.0", tk.END).strip() == "", attr
    finally:
        root.destroy()
        _cleanup(fid)


def test_r16_save_blocked_names_missing_fields():
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_r16_save_blocked_names_missing_fields (no display)")
        return
    try:
        _fill(tab, complaint="Toothache", symptom="", diagnosis="", procedure="")
        with mock.patch.object(clinical_tables.messagebox, "showerror") as err:
            tab.btn_save_visit.invoke()
        assert err.called, "blocked save showed no error"
        msg = err.call_args[0][1]
        for name in ("Symptoms", "Diagnosis", "Procedure"):
            assert name in msg, f"missing field not named: {name} in {msg!r}"
        assert _count("complaints", fid) == 0
        assert _count("diagnoses", fid) == 0
        assert _count("procedures", fid) == 0
    finally:
        root.destroy()
        _cleanup(fid)


def test_r16_symptoms_only_second_save_no_text_required():
    """The bug scenario: after a first save cleared the boxes, text
    typed ONLY in the Symptoms box must save -- not "Text required!"."""
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_r16_symptoms_only_second_save (no display)")
        return
    try:
        _fill(tab)
        with mock.patch.object(clinical_tables.messagebox, "showerror") as err:
            clinical_tables.add(tab, "complaint")
        assert not err.called
        assert _count("complaints", fid) == 1
        # Doctor types new symptoms text and saves via the old
        # symptom-table path (add(tab, "complaint")).
        tab.txt_sym.delete("1.0", tk.END)
        tab.txt_sym.insert("1.0", "Swelling since yesterday")
        with mock.patch.object(clinical_tables.messagebox, "showerror") as err:
            clinical_tables.add(tab, "complaint")
        assert not err.called, f"bug is back: {err.call_args}"
        assert _count("complaints", fid) == 2
        from src.models.database import get_connection
        conn = get_connection(); cur = conn.cursor()
        rows = cur.execute("SELECT symptoms FROM complaints WHERE patient_file=? "
                           "ORDER BY id", (fid,)).fetchall()
        conn.close()
        assert rows[1]["symptoms"] == "Swelling since yesterday", [dict(r) for r in rows]
    finally:
        root.destroy()
        _cleanup(fid)


def test_r16_no_per_table_add_buttons_tables_shorter():
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_r16_no_per_table_add_buttons (no display)")
        return
    try:
        root.update_idletasks()
        for w in _walk(tab):
            if isinstance(w, tk.Button):
                txt = str(w.cget("text"))
                assert "Add Complaint" not in txt and "Add Diagnosis" not in txt \
                    and "Add Procedure" not in txt, txt
        # 2x2 grid kept, but each table is SHORTER than round 15 (182px
        # baseline, measured the same way before the change: the Add
        # button row is gone and paddings are tighter).
        for kind, frm in tab.table_frames.items():
            assert frm.winfo_height() < 182, (kind, frm.winfo_height())
        assert set(tab.table_frames) == {"complaint", "symptom", "diagnosis", "procedure"}
    finally:
        root.destroy()
        _cleanup(fid)
