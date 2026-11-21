"""Round 23 (item 2): History shows per-session Total / Paid /
Remaining; the Recent Payments panel is removed. Money rule
(history_money.py): patient + visit_date + tooth SET must match
exactly; same-session rows are summed; a multi-tooth row shows
in full only on the exact-set session (never split/duplicated);
no matching row -> blank money cells (None in the data layer).
Covers seeded totals in the unified tree, the no-financial-rows
and no-patient paths, and the migrated payment-detail dialog.
ROUND-24 SUPERSESSION (items 2+6): the diag/proc trees and the
Therapeutic Procedures panel this file once asserted on are
removed; their content lives in the unified tree's columns.
GUI skips w/o display."""
import tkinter as tk
from unittest import mock

from src.models.database import get_connection, init_db
from src.models.history_money import session_money, session_rows
from src.ui import clinical_history as _hist
from src.ui.clinical import ClinicalTab
from src.ui.clinical_panels import MAIN_PANELS
from tests.test_clinical_save_gate import _stub_app

DATE = "2026-11-10"

def _seed_patient():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name) VALUES(?,?)",
                ("R23", "R23 History Money"))
    fid = cur.lastrowid; conn.commit(); conn.close()
    return fid

def _seed_visit(fid, tooth="16", date=DATE, with_money=True):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO complaints(patient_file,visit_date,complaint,"
                "symptoms) VALUES(?,?,?,?)",
                (fid, date, "Toothache", "Pain on chewing"))
    cur.execute("INSERT INTO diagnoses(patient_file,visit_date,tooth_number,"
                "diagnosis) VALUES(?,?,?,?)", (fid, date, tooth, "Pulpitis"))
    cur.execute("INSERT INTO procedures(patient_file,visit_date,tooth_number,"
                "procedure_done) VALUES(?,?,?,?)",
                (fid, date, tooth, "Root canal"))
    if with_money:  # two partial rows, same patient+date+tooth: summed
        for total, paid in ((50000.0, 30000.0), (30000.0, 10000.0)):
            cur.execute("INSERT INTO financials(patient_file,tooth_number,total_cost,paid_amount,remaining,visit_date,total_syp,paid_syp,remaining_syp) VALUES(?,?,?,?,?,?,?,?,?)",
                        (fid, tooth, total, paid, total - paid, date, total, paid, total - paid))
    conn.commit(); conn.close()

def _cleanup(fid):
    try:
        conn = get_connection(); cur = conn.cursor()
        for tbl in ("complaints", "diagnoses", "procedures", "financials"):
            cur.execute(f"DELETE FROM {tbl} WHERE patient_file=?", (fid,))
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
        conn.commit(); conn.close()
    except Exception:
        pass

def test_session_money_model():
    fid = _seed_patient()
    try:
        _seed_visit(fid)
        m = session_money(fid, DATE, "16")
        assert m == {"total": 80000.0, "paid": 40000.0, "remaining": 40000.0}, m
        assert session_money(fid, DATE, "11") is None  # wrong tooth
        assert session_money(fid, "2026-01-01", "16") is None  # wrong date
        rows = session_rows(fid)
        assert len(rows) == 1, rows
        r = rows[0]
        assert (r["complaint"], r["symptom"]) == ("Toothache", "Pain on chewing")
        assert (r["diagnosis"], r["procedure"]) == ("Pulpitis", "Root canal")
        assert (r["total"], r["paid"], r["remaining"]) == \
            (80000.0, 40000.0, 40000.0)
        assert session_rows(None) == [] and session_money(None, DATE, "16") is None
    finally:
        _cleanup(fid)

def test_session_money_multi_tooth_attribution():
    fid = _seed_patient()
    try:
        _seed_visit(fid, tooth="16,11", with_money=False)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO financials(patient_file,tooth_number,total_cost,paid_amount,remaining,visit_date,total_syp,paid_syp,remaining_syp) VALUES(?,?,?,?,?,?,?,?,?)",
                    (fid, "11,16", 90000.0, 90000.0, 0.0, DATE, 90000.0, 90000.0, 0.0))
        conn.commit(); conn.close()
        # Exact set matches in any stored order; the full amount
        # lands on the multi-tooth session only -- a single-tooth
        # lookup gets NOTHING (no splitting / double counting).
        assert session_money(fid, DATE, "16,11")["total"] == 90000.0
        assert session_money(fid, DATE, "16") is None
        assert session_money(fid, DATE, "11") is None
        assert session_rows(fid)[0]["total"] == 90000.0
    finally:
        _cleanup(fid)

def _build(lang="en", patient=None):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.geometry("1380x1000")
    tab = ClinicalTab(root, _stub_app(patient, lang=lang))
    tab.pack(fill="both", expand=True)
    root.update_idletasks(); root.update()
    return root, tab

def _cell(tab, tree, col):
    kids = tree.get_children()
    assert len(kids) == 1, kids
    return tree.set(kids[0], col)

def test_history_gui_money_and_panels():
    fid = _seed_patient()
    try:
        _seed_visit(fid)
        patient = {"file_number": fid, "full_name": "R23 History Money"}
        root, tab = _build("en", patient)
        if tab is None:
            print("SKIP r23 history GUI (no display)"); return
        try:
            tab.load(fid); root.update()
            # Unified History: the session row carries the money.
            for col, want in (("total", 80000.0), ("paid", 40000.0),
                              ("remain", 40000.0)):
                assert float(_cell(tab, tab.tree_history, col)) == want, col
            assert _cell(tab, tab.tree_history, "complaint") == "Toothache"
            assert _cell(tab, tab.tree_history, "procedure") == "Root canal"
            # ROUND-24 SUPERSESSION (items 2+6): the diag/proc trees
            # are REMOVED (their money lived in the unified tree,
            # asserted above) and the Therapeutic Procedures panel
            # is REMOVED too -- MAIN_PANELS is empty, no panel attrs
            # are built, and the procedure text is the unified
            # tree's procedure column (asserted above).
            assert not hasattr(tab, "tree_diag")
            assert not hasattr(tab, "tree_proc")
            assert MAIN_PANELS == ()
            assert not hasattr(tab, "panel_frames")
            assert not hasattr(tab, "panel_texts")
            # Zebra striping kept on History.
            iid = tab.tree_history.get_children()[0]
            assert "zebra0" in tab.tree_history.item(iid, "tags")
            # Migrated behaviour: payment detail for the money row.
            tab.tree_history.selection_set(iid)
            with mock.patch.object(_hist.messagebox, "showinfo") as info:
                assert _hist.show_history_payment_detail(tab) is True
            assert "Payment details" in info.call_args[0][0]
            assert "80000" in info.call_args[0][1]
        finally:
            root.destroy()
    finally:
        _cleanup(fid)

def test_history_gui_no_financial_rows_and_no_patient():
    fid = _seed_patient()
    try:
        _seed_visit(fid, with_money=False)  # clinical rows, NO money
        patient = {"file_number": fid, "full_name": "R23 No Money"}
        root, tab = _build("en", patient)
        if tab is None:
            print("SKIP r23 no-money GUI (no display)"); return
        try:
            tab.load(fid); root.update()
            # Empty/null path: the session row exists, money blank.
            assert len(tab.tree_history.get_children()) == 1
            for col in ("total", "paid", "remain"):
                assert _cell(tab, tab.tree_history, col) == "", col
            assert tab._history_sessions[0]["total"] is None
            iid = tab.tree_history.get_children()[0]
            tab.tree_history.selection_set(iid)
            assert _hist.show_history_payment_detail(tab) is False
            # No patient (the shell clears current_patient, then
            # reloads): History empties. ROUND-24 SUPERSESSION: the
            # "procedures panel shows the no-patient text" assert is
            # replaced by the panel's absence (no panels are built).
            tab.app.current_patient = None
            tab.load(None); root.update()
            assert tab.tree_history.get_children() == ()
            assert tab._history_sessions == []
            assert not hasattr(tab, "panel_texts")
        finally:
            root.destroy()
        # Build with NO patient selected at all: no crash, empty.
        root, tab = _build("en", None)
        if tab is None:
            print("SKIP r23 no-patient build (no display)"); return
        try:
            assert tab.tree_history.get_children() == ()
            assert not hasattr(tab, "panel_frames")
        finally:
            root.destroy()
    finally:
        _cleanup(fid)
