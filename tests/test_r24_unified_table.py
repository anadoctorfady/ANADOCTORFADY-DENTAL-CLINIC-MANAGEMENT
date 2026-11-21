"""Round 24 (items 2 + 6 + 3): the UNIFIED clinical table through
the REAL ClinicalTab entry widgets + Save session button.
Item-3 acceptance (owner scenario): day 1 work 300 paid 50; day 2
NEW work 400, patient pays 500 (settling earlier debt) -- must
SAVE; patient totals end exactly 700 / 550 / 150. Exercised for a
different-tooth and a same-tooth day 2, plus the genuine-
overpayment refusal (EN + AR, cap stated, nothing saved).
Also: the all-four save gate on the entry date, the money-only
save (clinical already saved for the date) and live Remaining.
The Edit/Delete permission matrix lives in
tests/test_r24_session_edit.py. GUI skips with no display;
DB is the isolated gate copy."""
import tkinter as tk
import tkinter.messagebox as _mb

from src.models.database import get_connection, init_db
from src.models.finance import patient_totals
from src.models.history_money import session_rows
from src.ui import clinical_session_entry as _entry
from src.ui.clinical import ClinicalTab

D1, D2 = "2026-11-16", "2026-11-17"


class _App:
    def __init__(self, user, role, fid=None, lang="en"):
        self.current_user = user; self.current_role = role; self.lang = lang
        self.current_patient = ({"file_number": fid, "full_name": "R24 Test"}
                                if fid else None)
    def chart_teeth(self):
        return []
    def refresh_clinical(self):
        pass


def _patient(name="R24Uni"):
    init_db(); conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name) VALUES(?,?)", (name, name))
    fid = cur.lastrowid; conn.commit(); conn.close(); return fid

def _seed_users():
    init_db(); conn = get_connection(); cur = conn.cursor()
    for u, r in (("doc_a", "doctor"), ("doc_b", "doctor"), ("boss", "admin"), ("nurse1", "nurse")):
        cur.execute("INSERT OR IGNORE INTO users(username,password_hash,role) VALUES(?,?,?)", (u, "x", r))
    conn.commit(); conn.close()


def _cleanup(fid):
    conn = get_connection(); cur = conn.cursor()
    for tbl in ("complaints", "diagnoses", "procedures", "financials"):
        cur.execute(f"DELETE FROM {tbl} WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    cur.execute("DELETE FROM user_grants WHERE username IN ('doc_a','doc_b')")
    cur.execute("DELETE FROM users WHERE username IN ('doc_a','doc_b','boss','nurse1')")
    conn.commit(); conn.close()


def _count(table, fid):
    conn = get_connection()
    n = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE patient_file=?", (fid,)).fetchone()[0]
    conn.close(); return n  # noqa: E501


def _patch_msgs():
    caps = {"error": [], "info": [], "warn": []}
    orig = (_mb.showerror, _mb.showinfo, _mb.showwarning, _mb.askyesno)
    _mb.showerror = lambda *a, **k: caps["error"].append(a)
    _mb.showinfo = lambda *a, **k: caps["info"].append(a)
    _mb.showwarning = lambda *a, **k: caps["warn"].append(a)
    _mb.askyesno = lambda *a, **k: True
    def restore():
        _mb.showerror, _mb.showinfo, _mb.showwarning, _mb.askyesno = orig
    return caps, restore


def _build(user="doc_a", role="doctor", fid=None, lang="en"):
    _seed_users()
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.withdraw()
    tab = ClinicalTab(root, _App(user, role, fid, lang),
                      current_user=user, current_role=role)
    tab.pack(); root.update_idletasks()
    if fid:
        tab.load(fid); root.update_idletasks()
    return root, tab


def _fill(tab, complaint="Toothache", symptom="Pain", diagnosis="Pulpitis",
          procedure="Root canal"):
    for w, v in ((tab.txt_complaint, complaint), (tab.txt_sym, symptom),
                 (tab.txt_diagnosis, diagnosis), (tab.txt_procedure, procedure)):
        w.delete("1.0", tk.END); w.insert("1.0", v)


def _set_entry(tab, date, tooth, total, paid):
    for w, v in ((tab.e_sess_date, date), (tab.e_sess_tooth, tooth)):
        w.delete(0, tk.END); w.insert(0, v)
    _entry.set_money(tab, total, paid)


def _save_session(tab, date, tooth, total, paid, **kw):
    _fill(tab, **kw)
    _set_entry(tab, date, tooth, total, paid)
    tab.btn_save_visit.invoke()


def test_item3_day2_settles_debt_different_tooth():
    fid = _patient("R24DiffTooth")
    caps, restore = _patch_msgs()
    root, tab = _build(fid=fid)
    if tab is None:
        print("SKIP item3 diff-tooth (no display)"); restore(); _cleanup(fid); return
    try:
        _save_session(tab, D1, "16", 300, 50)
        assert patient_totals(fid) == {"total": 300.0, "paid": 50.0, "remaining": 250.0}
        _save_session(tab, D2, "36", 400, 500)  # pays 500: settles day-1 debt
        assert not caps["error"], caps["error"]
        assert patient_totals(fid) == {"total": 700.0, "paid": 550.0, "remaining": 150.0}, patient_totals(fid)
        rows = {r["date"]: r for r in session_rows(fid)}
        assert (rows[D2]["total"], rows[D2]["paid"]) == (400.0, 500.0)
        # Unified tree: 2 rows; day-2 Remaining DISPLAY clamps to 0.
        assert len(tab.tree_history.get_children()) == 2
        cell = {tab.tree_history.set(i, "date"): tab.tree_history.set(i, "remain")
                for i in tab.tree_history.get_children()}
        assert float(cell[D2]) == 0.0 and float(cell[D1]) == 250.0, cell
    finally:
        root.destroy(); restore(); _cleanup(fid)


def test_item3_day2_settles_debt_same_tooth():
    fid = _patient("R24SameTooth")
    caps, restore = _patch_msgs()
    root, tab = _build(fid=fid)
    if tab is None:
        print("SKIP item3 same-tooth (no display)"); restore(); _cleanup(fid); return
    try:
        _save_session(tab, D1, "16", 300, 50)
        _save_session(tab, D2, "16", 400, 500)  # same tooth, +400 work, pays 500
        assert not caps["error"], caps["error"]
        assert patient_totals(fid) == {"total": 700.0, "paid": 550.0, "remaining": 150.0}, patient_totals(fid)
        assert len(session_rows(fid)) == 2  # two sessions, one per date
    finally:
        root.destroy(); restore(); _cleanup(fid)


def test_item3_genuine_overpayment_refused_bilingual():
    for lang, needle in (("en", "maximum"), ("ar", "الحد الأقصى")):
        fid = _patient("R24Over" + lang)
        caps, restore = _patch_msgs()
        root, tab = _build(fid=fid, lang=lang)
        if tab is None:
            print("SKIP overpayment (no display)"); restore(); _cleanup(fid); return
        try:
            _fill(tab)
            _set_entry(tab, D1, "16", 400, 401)  # cap is exactly 400
            tab.btn_save_visit.invoke()
            assert caps["error"], f"no refusal in {lang}"
            msg = caps["error"][-1][1]
            assert needle in msg and "400" in msg, (lang, msg)
            # Nothing saved: no clinical rows, no money, no totals.
            assert _count("complaints", fid) == _count("financials", fid) == 0
            assert patient_totals(fid)["total"] == 0.0
        finally:
            root.destroy(); restore(); _cleanup(fid)


def test_save_gate_and_money_only_save():
    fid = _patient("R24Gate")
    caps, restore = _patch_msgs()
    root, tab = _build(fid=fid)
    if tab is None:
        print("SKIP gate/money-only (no display)"); restore(); _cleanup(fid); return
    try:
        # Gate: only complaint filled -> blocked, missing named.
        _fill(tab, complaint="Toothache", symptom="", diagnosis="", procedure="")
        _set_entry(tab, D1, "16", 300, 50)
        tab.btn_save_visit.invoke()
        assert caps["error"], "gate did not block"
        msg = caps["error"][-1][1]
        for name in ("Symptoms", "Diagnosis", "Procedure"):
            assert name in msg, msg
        assert _count("complaints", fid) == 0
        # Full save, then a MONEY-ONLY save for the same date.
        _save_session(tab, D1, "16", 300, 50)
        assert patient_totals(fid)["paid"] == 50.0
        _set_entry(tab, D1, "16", 0, 100)  # fields are empty post-save
        tab.btn_save_visit.invoke()
        assert patient_totals(fid) == {"total": 300.0, "paid": 150.0, "remaining": 150.0}
        assert _count("complaints", fid) == 1 and _count("diagnoses", fid) == 1
        assert _count("financials", fid) == 2
        # Live Remaining: max(Total - Paid, 0) while typing.
        _entry.set_money(tab, 300, 500)
        assert tab.lbl_sess_remain.cget("text") == "0.00"
        _entry.set_money(tab, 300, 50)
        assert tab.lbl_sess_remain.cget("text") == "250.00"
    finally:
        root.destroy(); restore(); _cleanup(fid)
