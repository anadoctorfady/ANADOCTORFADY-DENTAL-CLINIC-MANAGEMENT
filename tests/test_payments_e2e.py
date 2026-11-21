"""Payments end to end (Round 12, Item A): the REAL ClinicalTab payment
form (not just the model) + the real FinanceTab role views, on the
isolated DB copy. Fresh users (doc_x/doc_y/nurse1) give exact baselines."""
from datetime import date
import tkinter as tk, tkinter.messagebox as _mb
from src.models.database import init_db, get_connection, save_financial
from src.models.finance import patient_totals, doctor_income, net_income
from src.models.permissions import finance_scope, can_add_payment
from src.ui.clinical import ClinicalTab
from src.ui.finance import FinanceTab
from src.utils.finance_gate import FinanceGate

TODAY = date.today().isoformat()
USERS = (("doc_x", "doctor"), ("doc_y", "doctor"), ("nurse1", "nurse"))

def _seed_users():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    for u, r in USERS: cur.execute("INSERT OR IGNORE INTO users(username,password_hash,role) VALUES(?,?,?)", (u, "x", r))
    conn.commit(); conn.close()

def _seed_patient(name):
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name) VALUES(?,?)", (name, name + " Pay"))
    fid = cur.lastrowid; conn.commit(); conn.close()
    return fid

def _rows(fid):
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) FROM financials WHERE patient_file=?",
                     (fid,)).fetchone()[0]
    conn.close(); return n

def _cleanup(fid=None, exp_id=None, lab_id=None, sal_id=None):
    conn = get_connection(); cur = conn.cursor()
    if fid:
        cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    for tbl, rid in (("expenses", exp_id), ("lab_costs", lab_id),
                     ("salary_payments", sal_id)):
        if rid: cur.execute(f"DELETE FROM {tbl} WHERE id=?", (rid,))
    cur.execute("DELETE FROM users WHERE username IN ('doc_x','doc_y','nurse1')")
    conn.commit(); conn.close()

def _patch_msgs():
    caps = {"error": [], "info": [], "warn": []}
    orig = (_mb.showerror, _mb.showinfo, _mb.showwarning)
    _mb.showerror = lambda *a, **k: caps["error"].append(a)
    _mb.showinfo = lambda *a, **k: caps["info"].append(a)
    _mb.showwarning = lambda *a, **k: caps["warn"].append(a)
    return caps, lambda: [setattr(_mb, n, f) for n, f in zip(("showerror", "showinfo", "showwarning"), orig)]

class _FakeApp:
    lang = "en"
    def __init__(self, user, role, fid=None, lang="en"):
        self.current_user = user; self.current_role = role; self.lang = lang
        self.current_patient = ({"file_number": fid, "full_name": "Pay", "mobile1": "",
                                 "birth_date_greg": "1990-01-01"} if fid else None)
    def chart_teeth(self):
        return ["11"]
    def refresh_clinical(self):
        pass

def _build_clinical(user, role, fid=None, lang="en"):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.withdraw()
    tab = ClinicalTab(root, _FakeApp(user, role, fid, lang))
    tab.pack(); root.update_idletasks()
    if fid: tab.load(fid); root.update_idletasks()
    return root, tab

def _set(tab, paid, doctor=None):
    """R38: payment entry = ONE standalone payment (amount + doctor)."""
    tab.e_paid.delete(0, tk.END); tab.e_paid.insert(0, str(paid))
    if doctor:
        tab.doctor_var.set(doctor)

def _build_finance(user):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.withdraw()
    app = _FakeApp("fady", "admin")
    app.finance_gate = FinanceGate(verify_fn=lambda u, p: True)
    tab = FinanceTab(tk.Frame(root), app)
    root.update_idletasks()
    tab.e_gate_user.delete(0, tk.END); tab.e_gate_user.insert(0, user)
    tab.e_gate_pass.delete(0, tk.END); tab.e_gate_pass.insert(0, "x")
    tab._try_unlock(); root.update_idletasks()
    return root, tab

def test_e2e_session_payment_via_unified_entry():
    """ROUND-24 SUPERSESSION of test_e2e_cumulative_via_real_form:
    the cumulative entry is gone (boxes start 0/0 -- asserted). A
    NEW session through the REAL unified entry (Total 100,000,
    Paid 50,000) reaches the same endpoints the delta flow did:
    totals 600,000/350,000 (NOT doubled), doctor +50,000, center
    +50,000, one new row."""
    _seed_users()
    fid = _seed_patient("E2E")
    try:
        save_financial(fid, "11", 500000, 300000, TODAY, doctor="doc_x",
                       entered_by="doc_x")
        assert patient_totals(fid) == {"total": 500000.0, "paid": 300000.0,
                                       "remaining": 200000.0}
        net_before = net_income()["total_income"]
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None:
            print("SKIP test_e2e_session_payment_via_unified_entry (no display)"); return
        try:
            assert tab.e_paid.get() == "0"  # R24: no cumulative prefill; R38: the payment entry's amount starts at 0
            assert tab.doctor_var.get() == "doc_x"  # defaults to visit doctor
            from src.ui import clinical_session_entry as _entry
            for w, txt in ((tab.txt_complaint, "Pain"), (tab.txt_sym, "Sharp"),
                           (tab.txt_diagnosis, "Caries"), (tab.txt_procedure, "Filling")):
                w.delete("1.0", tk.END); w.insert("1.0", txt)
            tab.e_sess_date.delete(0, tk.END); tab.e_sess_date.insert(0, TODAY)
            tab.e_sess_tooth.delete(0, tk.END); tab.e_sess_tooth.insert(0, "11")
            _entry.set_money(tab, 100000, 50000)
            tab.btn_save_visit.invoke(); root.update_idletasks()
            assert patient_totals(fid) == {"total": 600000.0, "paid": 350000.0,
                                           "remaining": 250000.0}, patient_totals(fid)
            assert _rows(fid) == 2, "exactly one new session row must be added"
            assert doctor_income("doc_x")["paid"] == 350000.0
            assert net_income()["total_income"] - net_before == 50000.0
        finally:
            root.destroy()
    finally:
        _cleanup(fid)

def test_nurse_payment_credited_to_doctor_via_form():
    """Nurse enters via the real form for doc_y: income goes to doc_y
    (+150,000), not the nurse, not doc_x; selector lists doctors/admins
    only. (R24: the clinical finance entry was rewired onto
    session_money -- one payment per entry, same crediting rule.)"""
    _seed_users()
    fid = _seed_patient("NursePay")
    try:
        save_financial(fid, "11", 500000, 300000, TODAY, doctor="doc_x",
                       entered_by="doc_x")
        root, tab = _build_clinical("nurse1", "nurse", fid)
        if tab is None:
            print("SKIP test_nurse_payment_credited_to_doctor_via_form (no display)"); return
        try:
            docs = list(tab.cb_doctor["values"])
            assert "nurse1" not in docs and "doc_x" in docs and "doc_y" in docs
            assert "fady" in docs and tab.doctor_var.get() in docs
            assert tab.doctor_var.get() != "nurse1"
            # R38: the payment entry records the PAYMENT only
            # (150,000 for doc_y); totals stay 500,000 total.
            _set(tab, 150000, "doc_y")
            tab.add_fin(); root.update_idletasks()
            assert patient_totals(fid) == {"total": 500000.0, "paid": 450000.0,
                                           "remaining": 50000.0}
            assert doctor_income("doc_y")["paid"] == 150000.0
            assert doctor_income("doc_x")["paid"] == 300000.0
            assert doctor_income("nurse1")["paid"] == 0.0
        finally:
            root.destroy()
    finally:
        _cleanup(fid)

def test_doctor_my_income_view_and_nurse_no_finance():
    """Real FinanceTab: doc_x unlock -> own-income view shows ONLY
    doc_x (100,000, not doc_y's 50,000); nurse unlock -> no finance view."""
    _seed_users()
    fid = _seed_patient("RoleView")
    try:
        save_financial(fid, "11", 100000, 100000, TODAY, doctor="doc_x",
                       entered_by="doc_x")
        save_financial(fid, "12", 50000, 50000, TODAY, doctor="doc_y",
                       entered_by="doc_y")
        assert can_add_payment("nurse", "doc_x", "nurse1") is True
        assert can_add_payment("doctor", "doc_y", "doc_x") is False
        assert finance_scope("nurse") == "none" and finance_scope("doctor") == "own"
        root, tab = _build_finance("doc_x")
        if tab is None:
            print("SKIP test_doctor_my_income_view_and_nurse_no_finance (no display)"); return
        try:
            assert tab._finance_scope() == "own"
            assert tab._doc_view.winfo_manager() == "place"
            assert tab._doc_paid.cget("text") == "100000.00", tab._doc_paid.cget("text")
            assert tab._doc_total.cget("text") == "100000.00"
        finally:
            root.destroy()
        root, tab = _build_finance("nurse1")
        try:
            assert tab._finance_scope() == "none"
            assert tab._nurse_view.winfo_manager() == "place"
            assert tab._doc_view.winfo_manager() == ""
        finally:
            root.destroy()
    finally:
        _cleanup(fid)
