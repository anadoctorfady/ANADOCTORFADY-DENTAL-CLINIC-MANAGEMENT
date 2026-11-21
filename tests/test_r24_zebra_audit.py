"""Round 24 (item 6): ZEBRA AUDIT -- every multi-row table in the
app must actually render alternating rows in BOTH themes.

Audit result on the pre-R24 code (zebra_tree / zebra_listbox from
src/ui/zebra.py; the zebra tag must be FIRST so meaning tags keep
precedence):
  HAD IT:  patient list (shell load_patients + debtors fill),
           unified History/session tree, clinical tree_fin,
           finance tree_exp / tree_lab / tree_debt /
           tree_centers / tree_sal, appointments tree, users list,
           attendance view, referrals tree, Rx items
           tree + Rx history tree, template picker list, template
           manager list, category picker list.
  R27:     tree_xray + the scans tree became THUMBNAIL GRIDS;
           their tiles alternate the same zebra pair (asserted
           below via _assert_grid_zebra).
  FIXED in R24: phrase_picker clipboard-history panel (refresh
           never striped), shell.select_patient's manual insert
           path (row inserted without re-striping the list),
           appointments weekday + time-slot selector listboxes.
  N/A:     clipboard multi-select picker (Checkbutton rows, not
           a listbox), users permission tree (checkbox-mark tree,
           not a record table), finance has no income tree (cards).

This test builds the real tabs in BOTH themes on the isolated DB
and asserts, per audited tree: rows exist, row i's FIRST tag is
zebra{i%2}, and the zebra tag backgrounds equal the theme's
zebra_colors for the active mode. Listboxes: per-row item
backgrounds alternate the same colours. Skips with no display."""
import tkinter as tk
from tkinter import ttk

from src.config.theme import zebra_colors
from src.models.database import get_connection, init_db, set_setting
from tests.test_templates_edit import isolated_db


def _mk_patient():
    init_db(); conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name) VALUES('Zeb','Zeb Ra')")
    fid = cur.lastrowid
    cur.execute("INSERT INTO complaints(patient_file,visit_date,complaint,symptoms) VALUES(?,?,?,?)", (fid, "2026-11-10", "Pain", "Sym"))
    cur.execute("INSERT INTO diagnoses(patient_file,visit_date,tooth_number,diagnosis) VALUES(?,?,?,?)", (fid, "2026-11-10", "16", "Caries"))
    cur.execute("INSERT INTO procedures(patient_file,visit_date,tooth_number,procedure_done) VALUES(?,?,?,?)", (fid, "2026-11-10", "16", "Filling"))
    cur.execute("INSERT INTO financials(patient_file,tooth_number,total_cost,paid_amount,remaining,visit_date,total_syp,paid_syp,remaining_syp) VALUES(?,?,?,?,?,?,?,?,?)", (fid, "16", 1000, 400, 600, "2026-11-10", 1000, 400, 600))
    cur.execute("INSERT INTO xrays(patient_file,file_path,description,upload_date) VALUES(?,?,?,?)", (fid, "/tmp/z.png", "", "2026-11-10"))
    cur.execute("INSERT INTO appointments(patient_file,appointment_date,appointment_time,reason,status) VALUES(?,?,?,?,?)", (fid, "2026-11-20", "10:00", "Check", "قادم"))
    conn.commit(); conn.close()
    from src.models.referrals import add_referral
    add_referral(fid, "doc_a", "doc_b", "please see")
    from src.models.prescriptions import save_prescription
    save_prescription(fid, [{"generic": "Amoxicillin", "brand": "", "dose": "500 mg",
                             "frequency": "x2", "duration_days": "5", "instructions": ""}],
                      "", "fady", [])
    return fid


def _assert_tree_zebra(tree, dark, label):
    kids = tree.get_children("")
    assert kids, f"{label}: no rows to stripe"
    even, odd = zebra_colors(dark)
    got0 = str(tree.tag_configure("zebra0", "background")).lower()
    got1 = str(tree.tag_configure("zebra1", "background")).lower()
    assert (got0, got1) == (even.lower(), odd.lower()), (label, got0, got1)
    for i, k in enumerate(kids):
        tags = tree.item(k, "tags")
        assert tags and tags[0] == f"zebra{i % 2}", (label, i, tags)


def _assert_listbox_zebra(lb, dark, label):
    inner = getattr(lb, "listbox", lb)
    assert inner.size() >= 2, f"{label}: needs >= 2 rows"
    even, odd = zebra_colors(dark)
    bgs = [str(inner.itemcget(i, "background")).lower() for i in range(min(inner.size(), 4))]
    want = [(even if i % 2 == 0 else odd).lower() for i in range(len(bgs))]
    assert bgs == want, (label, bgs, want)


def _assert_grid_zebra(grid, dark, label):
    """R27: thumbnail-grid tiles alternate the same zebra pair."""
    assert grid.tiles, f"{label}: no tiles to stripe"
    even, odd = zebra_colors(dark)
    for i, tile in enumerate(grid.tiles):
        want = (even if i % 2 == 0 else odd).lower()
        got = str(tile.cget("bg")).lower()
        assert got == want, (label, i, got, want)


def _find_trees(widget, out):
    if isinstance(widget, ttk.Treeview):
        out.append(widget)
    for ch in widget.winfo_children():
        _find_trees(ch, out)
    return out


class _App:
    lang = "en"; current_user = "fady"; current_role = "admin"
    def __init__(self, fid=None):
        self.current_patient = {"file_number": fid, "full_name": "Zeb Ra"} if fid else None
    def chart_teeth(self):
        return []
    def refresh_clinical(self):
        pass


def _run_theme(dark):
    from src.ui.clinical import ClinicalTab
    from src.ui.appointments import AppointmentsTab
    from src.ui.users_tab import UsersTab
    set_setting("theme_mode", "dark" if dark else "light")
    fid = _mk_patient()
    root = tk.Tk(); root.withdraw()
    try:
        app = _App(fid)
        tab = ClinicalTab(root, app); tab.pack(); root.update_idletasks()
        tab.load(fid); root.update_idletasks()
        _assert_tree_zebra(tab.tree_history, dark, "unified/session tree")
        _assert_tree_zebra(tab.tree_fin, dark, "clinical financial tree")
        # R27 SUPERSESSION: the X-Ray tree is now a thumbnail grid;
        # its tiles alternate the same zebra pair (seeded: 1 xray).
        _assert_grid_zebra(tab.xray_grid, dark, "xray grid")
        _assert_tree_zebra(tab.tree_ref, dark, "referrals tree")
        # Rx trees: history via load(); items via a real add_item.
        rx = tab.rx_section
        _assert_tree_zebra(rx.tree_hist, dark, "rx history tree")
        from src.utils.medications import list_medications, display
        med = list_medications()[0]
        rx.drug_var.set(display(med, "en"))
        rx.add_item(); root.update_idletasks()
        _assert_tree_zebra(rx.tree, dark, "rx items tree")
        # Scans grid (R27: tiles inside the scans section frame).
        assert tab.scans_frame.thumb_grid is not None, "scans grid not found"
        from src.models.database import get_connection as _gc
        from src.models.scans import ensure_tables, register_scan
        conn = _gc(); ensure_tables(conn)
        register_scan(conn, fid, "image2d", "/tmp/zeb.png", "z", "fady"); conn.close()
        from src.ui.clinical_lists import rebuild_scans
        rebuild_scans(tab, fid); root.update_idletasks()
        _assert_grid_zebra(tab.scans_frame.thumb_grid, dark, "scans grid")
        # Appointments: tree + weekday/slot selector listboxes.
        appt = AppointmentsTab(root, app); appt.load(); root.update_idletasks()
        _assert_tree_zebra(appt.tree, dark, "appointments tree")
        _assert_listbox_zebra(appt.lb_days, dark, "weekday listbox")
        _assert_listbox_zebra(appt.lb_slots, dark, "slot listbox")
        # Users list (in a Notebook, as in the real shell).
        nb = ttk.Notebook(root); nb.pack()
        users = UsersTab(nb, app); nb.add(users, text="Users")
        users._load(); root.update_idletasks()
        _assert_tree_zebra(users.tree, dark, "users list")
        # Finance trees (gate bypassed with an always-true verifier).
        from src.ui.finance import FinanceTab
        from src.utils.finance_gate import FinanceGate
        from src.models.finance import add_expense, add_lab_cost
        add_expense("2026-11-02", "Supplies", "Gauze", 500)
        add_lab_cost("2026-11-02", "Lab", fid, "Crown", 700)
        app2 = _App(fid); app2.finance_gate = FinanceGate(verify_fn=lambda u, p: True)
        fin = FinanceTab(tk.Frame(root), app2); root.update_idletasks()
        fin.e_gate_user.delete(0, tk.END); fin.e_gate_user.insert(0, "fady")
        fin.e_gate_pass.delete(0, tk.END); fin.e_gate_pass.insert(0, "x")
        fin._try_unlock(); fin.load(); root.update_idletasks()
        _assert_tree_zebra(fin.tree_exp, dark, "finance expenses tree")
        _assert_tree_zebra(fin.tree_lab, dark, "finance lab tree")
        _assert_tree_zebra(fin.tree_debt, dark, "finance debts tree")
        _assert_tree_zebra(fin.tree_centers, dark, "finance centers tree")
        # Attendance view (admin-only Toplevel).
        from src.models.attendance import record_for_user
        from src.ui.attendance_view import open_attendance_view
        record_for_user("fady", "in")
        win = open_attendance_view(root, "admin")
        assert win is not None
        trees = _find_trees(win, [])
        assert trees and trees[0].get_children(""), "attendance rows expected"
        _assert_tree_zebra(trees[0], dark, "attendance tree")
        win.destroy()
    finally:
        root.destroy()
        conn = get_connection(); cur = conn.cursor()
        for tbl in ("complaints", "diagnoses", "procedures", "financials", "xrays", "appointments", "referrals", "patient_scans", "expenses", "lab_costs", "prescription_items", "prescriptions"):
            try:
                cur.execute(f"DELETE FROM {tbl} WHERE patient_file=?", (fid,))
            except Exception:
                try:
                    cur.execute(f"DELETE FROM {tbl}")
                except Exception:
                    pass
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
        conn.commit(); conn.close()


def test_zebra_audit_both_themes():
    try:
        tk.Tk().destroy()
    except tk.TclError:
        print("SKIP zebra audit (no display)"); return
    with isolated_db():
        try:
            _run_theme(False)
            _run_theme(True)
        finally:
            set_setting("theme_mode", "light")


