"""Round 17 item 3 (+ item 1): chart state must follow EXACTLY the
open patient.

Regressions pinned here:
(a) clinical.load() only set the chart selection `if tr:` -- opening
    a patient with no teeth_records left the PREVIOUS patient's
    selection on the chart. Now load always sets it (empty if none).
(b) Nothing cleared ClinicalTab when the current patient became
    None (new-patient flow / logout): treated markers, draft fields,
    panels and the finance row all kept the previous patient. Now
    ClinicalTab.clear() resets every surface.
(c) Switching directly between two patients leaves markers ==
    exactly the newly opened patient's treated_teeth(), and unsaved
    drafts / Rx draft items of the previous patient never carry over.
Item 1: the (dialog-only) PatientForm contains NO dental chart.

GUI tests skip gracefully with no display; run with DISPLAY=:98.
Seeded rows are cleaned up."""
import tkinter as tk
from datetime import datetime

from src.models.database import get_connection, init_db
from tests.test_clinical_save_gate import _build_tab, _cleanup, _seed_patient


def _seed_procedure(fid, teeth="16"):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO procedures(patient_file,visit_date,tooth_number,"
                "procedure_done,author,created_at) VALUES(?,?,?,?,?,?)",
                (fid, datetime.now().strftime("%Y-%m-%d"), teeth,
                 "Root canal", "fady", datetime.now().isoformat()))
    conn.commit(); conn.close()


def _seed_teeth_record(fid, tooth="16"):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO teeth_records(patient_file,tooth_number,"
                "tooth_type,created_at) VALUES(?,?,?,?)",
                (fid, tooth, "دائم", datetime.now().isoformat()))
    conn.commit(); conn.close()


def _seed_financial(fid, total=1000, paid=400):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO financials(patient_file,tooth_number,total_cost,"
                "paid_amount,remaining,visit_date) VALUES(?,?,?,?,?,?)",
                (fid, "16", total, paid, total - paid,
                 datetime.now().strftime("%Y-%m-%d")))
    conn.commit(); conn.close()


def _cleanup_all(*fids):
    for fid in fids:
        try:
            conn = get_connection(); cur = conn.cursor()
            for tbl in ("procedures", "diagnoses", "teeth_records", "financials"):
                cur.execute(f"DELETE FROM {tbl} WHERE patient_file=?", (fid,))
            conn.commit(); conn.close()
        except Exception:
            pass
        _cleanup(fid)


def _switch(tab, fid, name):
    tab.app.current_patient = {"file_number": fid, "full_name": name}
    tab.load(fid)


def test_selection_cleared_when_next_patient_has_no_rows():
    """(a) A has a teeth_record for 16; B has none: after opening B
    the chart selection is [] (it used to stay ['16'])."""
    init_db()
    fid_a, fid_b = _seed_patient(), _seed_patient()
    _seed_teeth_record(fid_a, "16")
    root, tab = _build_tab(fid_a)
    if tab is None:
        _cleanup_all(fid_a, fid_b); print("SKIP (no display)"); return
    try:
        tab.load(fid_a); root.update()
        assert tab.chart.get_selection()[0] == ["16"], tab.chart.get_selection()
        _switch(tab, fid_b, "Patient B"); root.update()
        assert tab.chart.get_selection()[0] == [], tab.chart.get_selection()
        assert tab.e_sess_tooth.get() == "", tab.e_sess_tooth.get()  # R38: session tooth box (finance tooth box removed)
    finally:
        root.destroy(); _cleanup_all(fid_a, fid_b)


def test_switch_patients_markers_and_data_are_exactly_new_patients():
    """(c) A (treated 16, money owed, history) -> B (clean): treated,
    selection, drafts, finance row and history are B's alone."""
    init_db()
    fid_a, fid_b = _seed_patient(), _seed_patient()
    _seed_procedure(fid_a, "16"); _seed_financial(fid_a)
    root, tab = _build_tab(fid_a)
    if tab is None:
        _cleanup_all(fid_a, fid_b); print("SKIP (no display)"); return
    try:
        tab.load(fid_a); root.update()
        assert tab.chart.get_treated() == ["16"]
        # R24: the finance boxes no longer prefill the cumulative;
        # A's money (1000) shows on the patient-balance line.
        # R38: the payment entry's Amount box starts at 0.
        assert float(tab.e_paid.get()) == 0
        assert "1,000" in tab.lbl_pat_totals.cget("text")
        assert len(tab.tree_history.get_children()) == 1  # R24: unified tree
        tab.txt_complaint.insert("1.0", "A draft complaint")
        tab.txt_procedure.insert("1.0", "A draft procedure")
        _switch(tab, fid_b, "Patient B"); root.update()
        assert tab.chart.get_treated() == [], tab.chart.get_treated()
        assert tab.chart.get_selection()[0] == []
        assert tab.txt_complaint.get("1.0", tk.END).strip() == ""
        assert tab.txt_procedure.get("1.0", tk.END).strip() == ""
        assert float(tab.e_paid.get()) == 0  # R38 (was e_total+e_paid)
        assert tab.tree_history.get_children() == ()  # R24: unified tree
        # Round 20: the name header is gone (owner: it duplicated
        # the shell's far-left info panel). R24: the panels are
        # gone too; the patient-bound surface is the unified table
        # (sessions of the loaded patient only) + patient_id.
        assert tab._history_sessions == []  # B has no sessions
        assert tab.patient_id == fid_b
    finally:
        root.destroy(); _cleanup_all(fid_a, fid_b)


def test_clear_resets_every_surface():
    """(b) current_patient -> None + clear(): no treated markers, no
    selection, no draft fields, finance 0, no-patient panels,
    empty history + scans + Rx history."""
    init_db()
    fid_a = _seed_patient()
    _seed_procedure(fid_a, "16"); _seed_financial(fid_a)
    root, tab = _build_tab(fid_a)
    if tab is None:
        _cleanup_all(fid_a); print("SKIP (no display)"); return
    try:
        tab.load(fid_a); root.update()
        assert tab.chart.get_treated() == ["16"]
        tab.chart.set_selection(["16"], "دائم")
        tab.txt_complaint.insert("1.0", "stale")
        tab.txt_sym_note.insert("1.0", "stale note")
        tab.app.current_patient = None
        tab.clear(); root.update()
        assert tab.patient_id is None
        assert tab.chart.get_treated() == [], tab.chart.get_treated()
        assert tab.chart.get_selection()[0] == []
        for attr in ("txt_complaint", "txt_sym", "txt_diagnosis",
                     "txt_procedure", "txt_sym_note"):
            assert getattr(tab, attr).get("1.0", tk.END).strip() == "", attr
        assert float(tab.e_paid.get()) == 0  # R38: payment entry amount resets (no Total box anymore)
        assert tab.e_pay_note.get() == "" and tab.e_pay_date.get() == ""
        # Round 20: no name header to reset. R24: no panels;
        # the unified table must hold NO sessions after clear().
        assert tab._history_sessions == []
        assert tab.tree_history.get_children() == ()  # R24: unified tree
        assert tab.tree_fin.get_children() == ()
        assert tab.rx_section.tree_hist.get_children() == ()
        # R27 SUPERSESSION: the scans Treeview is now a ThumbGrid;
        # after clear() it must hold no tiles.
        from src.ui.thumb_grid import ThumbGrid
        scans_grids = [w for w in tab.scans_frame.winfo_children()
                       if isinstance(w, ThumbGrid)]
        assert scans_grids and scans_grids[0].tiles == []
    finally:
        root.destroy(); _cleanup_all(fid_a)


def test_patient_form_has_no_dental_chart():
    """Item 1: the entry form (dialog content) contains no chart."""
    init_db()
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_patient_form_has_no_dental_chart (no display)"); return
    root.withdraw()
    try:
        from src.ui.dental_chart import DentalChartFrame
        from src.ui.patient_form import PatientForm

        class Stub:
            lang = "en"; current_patient = None
            def print_pdf(self): pass
            def load_patients(self): pass
            def select_patient(self, fid): pass

        form = PatientForm(root, Stub()); form.pack(); root.update_idletasks()
        assert not hasattr(form, "chart"), "PatientForm still owns a chart"

        def _walk(w):
            yield w
            for ch in w.winfo_children():
                yield from _walk(ch)

        assert not any(isinstance(w, DentalChartFrame) for w in _walk(form))
    finally:
        root.destroy()
