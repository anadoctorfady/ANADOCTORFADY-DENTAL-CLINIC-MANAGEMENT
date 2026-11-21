"""Job 3d (round 12): clinical history Edit/Delete + notes persistence.

Split out of test_clinical_save_gate.py (200-line limit). Shares its
helpers via import. ROUND-24 SUPERSESSION (items 2+6): the History
tab's per-table Edit/Delete buttons (clinical_edit + tree_diag) are
REMOVED -- editing lives on the UNIFIED session table
(clinical_session_edit / clinical_session_delete): Edit loads the
session into the entry (date + tooth fixed), Delete removes the
whole session via session_money.delete_session_rows. The 24h rule
(edit_rules.check_record), the reason label (now tab.sess_status),
the delete confirmation and created_at preservation are asserted
in equivalent form below. Covers:
  - notes saved with a visit persist across a patient reload;
  - unified Edit/Delete buttons gated by the 24h rule;
  - delete removes the whole session; edit keeps created_at.

GUI tests skip gracefully when no display is available; run with
DISPLAY=:105 under Xvfb. Seeded rows are cleaned up.
"""
import tkinter as tk
from datetime import datetime, timedelta
from unittest import mock

from src.models.database import get_connection
from src.models.edit_rules import block_reason
from src.ui import clinical_session_delete as _sess_del
from src.ui import clinical_session_edit as _sess_edit
from src.ui import clinical_tables
from tests.test_clinical_save_gate import (
    _build_tab, _cleanup, _count, _fill, _seed_patient, _stub_app)


def test_notes_persist_across_reload():
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_notes_persist_across_reload (no display)")
        return
    try:
        _fill(tab)
        # Round 17: the ONE visit note is stored on every saved row.
        # R24: clinical_tables.add routes to the unified session save.
        tab.txt_visit_note.insert("1.0", "keep this note")
        clinical_tables.add(tab, "complaint")
        clinical_tables.add(tab, "diagnosis")
        # Reload the patient (as the app does on select): the saved
        # note must still be in the DB afterwards.
        tab.app.current_patient = {"file_number": fid}
        tab.load(fid)
        conn = get_connection(); cur = conn.cursor()
        row = cur.execute("SELECT notes FROM diagnoses WHERE patient_file=?",
                          (fid,)).fetchone()
        conn.close()
        assert row["notes"] == "keep this note"
    finally:
        root.destroy()
        _cleanup(fid)


def _seed_session(fid, date, author, created_at, tooth="11"):
    """One full session (complaints + diagnoses + procedures)."""
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO complaints(patient_file,visit_date,complaint,"
                "symptoms,notes,author,created_at) VALUES(?,?,?,?,?,?,?)",
                (fid, date, "Pain", "Sharp", "", author, created_at))
    cur.execute("INSERT INTO diagnoses(patient_file,visit_date,tooth_number,"
                "diagnosis,author,created_at) VALUES(?,?,?,?,?,?)",
                (fid, date, tooth, "Pulpitis", author, created_at))
    cur.execute("INSERT INTO procedures(patient_file,visit_date,tooth_number,"
                "procedure_done,author,created_at) VALUES(?,?,?,?,?,?)",
                (fid, date, tooth, "Filling", author, created_at))
    conn.commit(); conn.close()


def _session_iid(tab, date):
    from src.ui.clinical_history import history_columns
    di = history_columns(tab.lang).index("date")
    for iid in tab.tree_history.get_children():
        if tab.tree_history.item(iid, "values")[di] == date:
            return iid
    raise AssertionError(f"no session row for {date}")


def test_history_edit_delete_buttons_24h_rule():
    fid = _seed_patient()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    old_day = (now - timedelta(days=2)).strftime("%Y-%m-%d")
    _seed_session(fid, today, "dr_fady", now.isoformat())
    _seed_session(fid, old_day, "other_doc",
                  (now - timedelta(days=2)).isoformat())
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_history_edit_delete_buttons_24h_rule (no display)")
        return
    try:
        tab.current_role = "doctor"
        tab.current_user = "dr_fady"
        tab.app.current_patient = {"file_number": fid}
        tab.load(fid)
        root.update()
        # Fresh session, own author, doctor: editable.
        tab.tree_history.selection_set(_session_iid(tab, today))
        _sess_edit.sync_edit_buttons(tab)
        assert str(tab.btn_sess_edit.cget("state")) == "normal"
        assert str(tab.btn_sess_delete.cget("state")) == "normal"
        assert tab.sess_status.cget("text") == ""
        # Old session, other author, >24h: not editable, reason shown.
        tab.tree_history.selection_set(_session_iid(tab, old_day))
        _sess_edit.sync_edit_buttons(tab)
        assert str(tab.btn_sess_edit.cget("state")) == "disabled"
        assert str(tab.btn_sess_delete.cget("state")) == "disabled"
        assert tab.sess_status.cget("text") == block_reason("en"), \
            tab.sess_status.cget("text")
        # Admin may always edit, even the old session.
        tab.current_role = "admin"
        _sess_edit.sync_edit_buttons(tab)
        assert str(tab.btn_sess_edit.cget("state")) == "normal"
        assert str(tab.btn_sess_delete.cget("state")) == "normal"
    finally:
        root.destroy()
        _cleanup(fid)


def test_delete_session_removes_all_rows():
    fid = _seed_patient()
    now = datetime.now()
    _seed_session(fid, now.strftime("%Y-%m-%d"), "dr_fady", now.isoformat())
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_delete_session_removes_all_rows (no display)")
        return
    try:
        tab.app.current_patient = {"file_number": fid}
        tab.load(fid)
        tab.tree_history.selection_set(
            _session_iid(tab, now.strftime("%Y-%m-%d")))
        with mock.patch("tkinter.messagebox.askyesno", return_value=True):
            assert _sess_del.delete_selected(tab) is True
        assert _count("diagnoses", fid) == 0
        assert _count("procedures", fid) == 0
        assert _count("complaints", fid) == 0
    finally:
        root.destroy()
        _cleanup(fid)


def test_edit_session_keeps_created_at():
    fid = _seed_patient()
    created = datetime.now().isoformat()
    _seed_session(fid, datetime.now().strftime("%Y-%m-%d"),
                  "dr_fady", created)
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_edit_session_keeps_created_at (no display)")
        return
    try:
        tab.app.current_patient = {"file_number": fid}
        tab.load(fid)
        tab.tree_history.selection_set(
            _session_iid(tab, datetime.now().strftime("%Y-%m-%d")))
        assert _sess_edit.start_edit(tab) is True
        tab.txt_diagnosis.delete("1.0", tk.END)
        tab.txt_diagnosis.insert("1.0", "Irreversible pulpitis")
        clinical_tables.add(tab)  # routes to the session edit save
        conn = get_connection(); cur = conn.cursor()
        row = cur.execute("SELECT * FROM diagnoses WHERE patient_file=?",
                          (fid,)).fetchone()
        conn.close()
        assert row["diagnosis"] == "Irreversible pulpitis", dict(row)
        assert row["created_at"] == created, dict(row)
    finally:
        root.destroy()
        _cleanup(fid)
