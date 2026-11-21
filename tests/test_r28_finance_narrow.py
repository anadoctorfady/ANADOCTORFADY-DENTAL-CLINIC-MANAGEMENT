"""Round 28 item 2: the Clinical-tab finance section is WIDTH-
capped (FIN_CAP_W) instead of stretching the full content width,
in EN and AR (RTL), and the payments list (tree_fin) is BOUNDED
(6 visible rows) with a working vertical scrollbar so a long
payment history scrolls inside the section. GUI tests skip
without a display."""
import tkinter as tk
from src.models.database import (get_connection, init_db,
                                 save_financial)
from src.ui.clinical import ClinicalTab
from src.ui.clinical_finance import FIN_CAP_W

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

def test_finance_width_capped_en():
    fid = _mk(); root, tab = _tab(fid, "en")
    if tab is None: _cleanup(fid); print("SKIP r28 fin width"); return
    try:
        root.update_idletasks()
        w = tab.fin_frame.winfo_width()
        cw = tab.main_canvas.winfo_width()
        assert 0 < w <= FIN_CAP_W + 2, (w, FIN_CAP_W)
        assert w < 0.6 * cw, (w, cw)  # clearly narrower than content
        # controls still fully present and usable at the cap
        for attr in ("e_pay_date", "e_paid", "e_pay_note", "cb_cur",
                     "cb_doctor", "btn_invoice"):  # R38 payment entry (was: e_total/e_fin_tooth)
            assert getattr(tab, attr, None) is not None, attr
    finally:
        root.destroy(); _cleanup(fid)

def test_finance_width_capped_ar_rtl():
    fid = _mk(); root, tab = _tab(fid, "ar")
    if tab is None: _cleanup(fid); print("SKIP r28 fin width ar"); return
    try:
        root.update_idletasks()
        w = tab.fin_frame.winfo_width()
        cw = tab.main_canvas.winfo_width()
        assert 0 < w <= FIN_CAP_W + 2, (w, FIN_CAP_W)
        assert w < 0.6 * cw, (w, cw)
        # RTL: the capped section anchors to the RIGHT edge, i.e. it
        # is NOT flush with the canvas's left edge.
        dx = tab.fin_frame.winfo_rootx() - tab.main_canvas.winfo_rootx()
        assert dx > 100, dx
        assert getattr(tab, "e_paid", None) is not None  # R38 payment entry built
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
