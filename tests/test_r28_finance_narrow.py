"""Round 28 item 2: the Clinical-tab finance section is WIDTH-
capped (FIN_CAP_W) instead of stretching the full content width,
in EN and AR (RTL), and the payments list (tree_fin) is BOUNDED
(6 visible rows) with a working vertical scrollbar so a long
payment history scrolls inside the section. GUI tests skip
without a display.
ROUND-40 RE-PIN (owner correction 2026-11-21): the capped finance
section is REMOVED (ONE payment place) — the width-cap tests
become presence tests: no fin_section, and the money widgets live
inside the unified entry (the money strip in the input block).
The payments-list bound/scroll test is unchanged."""
import tkinter as tk
from src.models.database import (get_connection, init_db,
                                 save_financial)
from src.ui.clinical import ClinicalTab

def _mk():
    init_db(); conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name,birth_date_greg,nationality) VALUES(?,?,?,?)",
                ("R28", "R28 Narrow Patient", "1990-01-01", "Syrian"))
    fid = cur.lastrowid; conn.commit(); conn.close(); return fid

def _cleanup(fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()

def _root():
    try:
        root = tk.Tk(); root.deiconify()
        root.geometry("1380x950+0+0"); root.update(); return root
    except tk.TclError:
        return None

class _App:
    def __init__(self, patient, lang="en"):
        self.lang = lang; self.current_user = "fady"
        self.current_role = "admin"; self.current_patient = patient
    def chart_teeth(self): return []
    def refresh_clinical(self): pass

def _tab(fid, lang="en"):
    root = _root()
    if root is None: return None, None
    patient = {"file_number": fid, "full_name": "R28 Narrow Patient",
               "mobile1": "", "birth_date_greg": "1990-01-01",
               "current_medications": "", "allergies": ""}
    tab = ClinicalTab(root, _App(patient, lang))
    tab.pack(fill="both", expand=True); root.update_idletasks()
    tab.app.refresh_clinical = lambda: tab.load(fid)
    tab.load(fid); root.update_idletasks(); return root, tab

def test_money_strip_in_unified_entry_en():
    fid = _mk(); root, tab = _tab(fid, "en")
    if tab is None: _cleanup(fid); print("SKIP r28 fin width"); return
    try:
        root.update_idletasks()
        # R40: the capped section is gone; the money strip is a
        # direct child of the unified input block.
        assert not hasattr(tab, "fin_section")
        assert tab.money_strip.master is tab.input_block
        for attr in ("e_sess_date", "e_sess_paid", "e_pay_note", "cb_cur",
                     "cb_doctor", "btn_invoice"):
            assert getattr(tab, attr, None) is not None, attr
    finally:
        root.destroy(); _cleanup(fid)

def test_money_strip_in_unified_entry_ar():
    fid = _mk(); root, tab = _tab(fid, "ar")
    if tab is None: _cleanup(fid); print("SKIP r28 fin width ar"); return
    try:
        root.update_idletasks()
        assert not hasattr(tab, "fin_section")
        assert tab.money_strip.master is tab.input_block
        assert getattr(tab, "e_sess_paid", None) is not None  # R40 unified entry built
    finally:
        root.destroy(); _cleanup(fid)

def test_payments_list_bounded_and_scrolls():
    fid = _mk()
    for i in range(14):
        save_financial(fid, "11", 1000, 500, f"2026-11-{i + 1:02d}")
    root, tab = _tab(fid, "en")
    if tab is None: _cleanup(fid); print("SKIP r28 fin scroll"); return
    try:
        root.update_idletasks()
        tr = tab.tree_fin
        rows = tr.get_children()
        assert len(rows) == 14, len(rows)
        assert int(tr.cget("height")) == 6, tr.cget("height")
        sb = getattr(tr, "_v_scrollbar", None)
        assert sb is not None and sb.winfo_exists(), "no scrollbar"
        top = tr.yview()
        assert top[1] < 1.0, top  # not everything fits: it can scroll
        tr.yview_moveto(1.0); root.update_idletasks()
        assert tr.yview()[1] == 1.0, tr.yview()
        assert tr.bbox(rows[-1]), "last payment row not reachable"
        tr.yview_moveto(0.0); root.update_idletasks()
        assert tr.bbox(rows[0]), "first payment row not reachable"
    finally:
        root.destroy(); _cleanup(fid)
