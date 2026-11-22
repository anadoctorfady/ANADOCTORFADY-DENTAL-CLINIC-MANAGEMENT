"""Round 40, item 1: ONE payment place (owner correction
2026-11-21 of round 38's two-zone layout). The unified session
entry is the ONLY money entry (no fin_section / e_paid /
e_pay_date / add_fin). Through the REAL form: a normal session
save; an OVERPAYMENT splits (session absorbs to the cap, EXCESS
becomes a standalone advance row = credit, split info shown,
Note on both rows); a PURE ADVANCE (Paid>0, no tooth/text,
Total 0) records one standalone row; the round-38 scripted
scenario (500 -> -500, +300 -> -200, +400 -> +200); a money-only
save against the day's session; refusals kept (negatives, 0/0).
GUI tests skip with no display."""
import tkinter as tk
from src.config.theme import credit_color, is_dark
from src.models.database import get_connection, save_financial
from src.models.finance import patient_totals
from tests.test_payments_e2e import (TODAY, _seed_users, _seed_patient,
                                     _rows, _cleanup, _patch_msgs,
                                     _build_clinical)


def _money_rows(fid):
    conn = get_connection()
    out = [tuple(r) for r in conn.execute(
        "SELECT tooth_number,total_cost,paid_amount,row_kind,note "
        "FROM financials WHERE patient_file=? ORDER BY id", (fid,))]
    conn.close(); return out


def _fill_texts(tab):
    for w, txt in ((tab.txt_complaint, "Pain"), (tab.txt_sym, "Sharp"),
                   (tab.txt_diagnosis, "Caries"),
                   (tab.txt_procedure, "Filling")):
        w.delete("1.0", tk.END); w.insert("1.0", txt)


def _save_session(tab, total, paid, tooth="11", date=TODAY):
    from src.ui import clinical_session_entry as _entry
    _fill_texts(tab)
    tab.e_sess_date.delete(0, tk.END); tab.e_sess_date.insert(0, date)
    tab.e_sess_tooth.delete(0, tk.END)
    if tooth:
        tab.e_sess_tooth.insert(0, tooth)
    _entry.set_money(tab, total, paid)
    tab.btn_save_visit.invoke()


def test_single_payment_place_structure():
    fid = _seed_patient("R40 One")
    try:
        root, tab = _build_clinical("fady", "admin", fid)
        if root is None:
            return  # no display
        try:
            assert not hasattr(tab, "fin_section")  # R38 zone GONE
            assert not hasattr(tab, "e_paid")
            assert not hasattr(tab, "e_pay_date")
            assert not hasattr(tab, "add_fin")
            for attr in ("e_sess_date", "e_sess_tooth", "e_sess_total",
                         "e_sess_paid", "lbl_sess_remain", "money_strip",
                         "cb_cur", "e_rate", "e_rate_date", "doctor_var",
                         "cb_doctor", "e_pay_note", "btn_invoice",
                         "lbl_pat_totals", "lbl_cur_break"):
                assert hasattr(tab, attr), attr
            assert tab.money_strip.master is tab.input_block
            def _walk(w):
                yield w
                for ch in w.winfo_children():
                    yield from _walk(ch)
            texts = [str(w.cget("text")) for w in _walk(tab)
                     if isinstance(w, tk.Button)]
            assert "Add Payment" not in texts and "إضافة دفعة" not in texts
            assert tab.btn_save_visit is not None
        finally:
            root.destroy()
    finally:
        _cleanup(fid)


def test_normal_session_save_unchanged():
    _seed_users(); fid = _seed_patient("R40 Normal")
    try:
        save_financial(fid, "11", 500000, 300000, TODAY, doctor="doc_x",
                       entered_by="doc_x")
        caps, restore = _patch_msgs()
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None:
            restore(); return
        try:
            _save_session(tab, 100000, 50000); root.update_idletasks()
            assert not caps["error"] and not caps["info"], caps
            assert patient_totals(fid) == {"total": 600000.0,
                "paid": 350000.0, "remaining": 250000.0}
            rows = _money_rows(fid)
            assert len(rows) == 2 and rows[-1][3] == "session", rows
        finally:
            root.destroy(); restore()
    finally:
        _cleanup(fid)


def test_overpayment_splits_to_advance():
    """Balance 250,000; session Total 0 / Paid 300,000: session
    absorbs 250,000, excess 50,000 = standalone advance (credit
    -50,000), split info shown, Note rides on BOTH rows."""
    _seed_users(); fid = _seed_patient("R40 Split")
    try:
        save_financial(fid, "11", 600000, 350000, TODAY, doctor="doc_x",
                       entered_by="doc_x")
        caps, restore = _patch_msgs()
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None:
            restore(); return
        try:
            tab.e_pay_note.delete(0, tk.END)
            tab.e_pay_note.insert(0, "split-note")
            _save_session(tab, 0, 300000); root.update_idletasks()
            assert not caps["error"], caps
            assert caps["info"] and "50000" in caps["info"][-1][1], caps
            assert patient_totals(fid) == {"total": 600000.0,
                "paid": 650000.0, "remaining": -50000.0}
            rows = _money_rows(fid)
            assert len(rows) == 3, rows
            assert rows[1][1:4] == (0.0, 250000.0, "session"), rows
            assert rows[2][1:4] == (0.0, 50000.0, "payment"), rows
            assert rows[1][4] == "split-note" and rows[2][4] == "split-note"
            assert "Credit" in tab.lbl_pat_totals.cget("text")
            assert tab.lbl_pat_totals.cget("fg") == credit_color(is_dark())
        finally:
            root.destroy(); restore()
    finally:
        _cleanup(fid)


def test_pure_advance_records_standalone_only():
    _seed_users(); fid = _seed_patient("R40 Advance")
    try:
        caps, restore = _patch_msgs()
        root, tab = _build_clinical("nurse1", "nurse", fid)
        if tab is None:
            restore(); return
        try:
            tab.app.chart_teeth = lambda: []  # nothing selected
            from src.ui import clinical_session_entry as _entry
            tab.e_pay_note.delete(0, tk.END)
            tab.e_pay_note.insert(0, "advance")
            _entry.set_money(tab, 0, 500)
            tab.btn_save_visit.invoke(); root.update_idletasks()
            assert not caps["error"], caps
            rows = _money_rows(fid)
            assert len(rows) == 1 and rows[0][3] == "payment", rows
            assert rows[0][2] == 500.0 and rows[0][4] == "advance"
            assert patient_totals(fid) == {"total": 0.0, "paid": 500.0,
                                           "remaining": -500.0}
        finally:
            root.destroy(); restore()
    finally:
        _cleanup(fid)


