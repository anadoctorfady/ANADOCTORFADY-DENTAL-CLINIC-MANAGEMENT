"""Payments form checks (Round 12, Item A, part 2): center net vs
flexible totals, negative-delta refusal (EN+AR), zero/empty payments,
USD conversion, no-patient safety, doctor-for-other-doctor refusal.
Helpers live in tests/test_payments_e2e.py. GUI tests skip with no display."""
import tkinter as tk
from src.config.strings import t
from src.models.database import get_connection, save_financial
from src.models.finance import (patient_totals, doctor_income, net_income,
                                per_center_totals, add_expense, add_lab_cost)
from src.models.finance_totals import flexible_totals
from src.utils.currencies import display_for_code
from tests.test_payments_e2e import (TODAY, _seed_users, _seed_patient,
                                     _rows, _cleanup, _patch_msgs,
                                     _build_clinical, _build_finance, _set)

def test_center_net_and_flexible_totals_agree():
    """Payment 100,000 + expense 40,000 + lab 10,000 + salary 20,000
    (all today): net = 100,000 - (40,000+20,000) - 10,000 = 30,000 in
    net_income, flexible_totals (all on) and the per-center breakdown."""
    _seed_users()
    fid = _seed_patient("NetCheck")
    exp_id = lab_id = sal_id = None
    try:
        before_net = net_income()
        before_flex = flexible_totals(TODAY, TODAY)
        before_centers = sum(c["net"] for c in per_center_totals(TODAY, TODAY))
        save_financial(fid, "11", 100000, 100000, TODAY, doctor="doc_x",
                       entered_by="doc_x")
        exp_id = add_expense(TODAY, "Materials", "e2e-exp", 40000)
        lab_id = add_lab_cost(TODAY, "Lab", fid, "e2e-lab", 10000)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO salary_payments(employee_id,month,amount,"
                    "payment_date) VALUES(NULL,?,?,?)", (TODAY[:7], 20000, TODAY))
        sal_id = cur.lastrowid; conn.commit(); conn.close()
        net = net_income()
        assert net["total_income"] - before_net["total_income"] == 100000.0
        assert net["total_expenses"] - before_net["total_expenses"] == 60000.0
        assert net["total_lab"] - before_net["total_lab"] == 10000.0
        assert net["net_income"] - before_net["net_income"] == 30000.0
        flex = flexible_totals(TODAY, TODAY)
        assert flex["net_income"] - before_flex["net_income"] == 30000.0
        assert flex["total_expenses"] - before_flex["total_expenses"] == 60000.0
        assert flex["total_lab"] - before_flex["total_lab"] == 10000.0
        assert flex["net_income"] - before_flex["net_income"] == net["net_income"] - before_net["net_income"]
        assert sum(c["net"] for c in per_center_totals(TODAY, TODAY)) - before_centers == 30000.0
    finally:
        _cleanup(fid, exp_id, lab_id, sal_id)

def test_session_overpayment_refused_bilingually():
    """ROUND-38 SUPERSESSION: the PAYMENT entry accepts overpayment
    (advance = credit, item 1; pinned in test_r38_*). The cap that
    remains is the SESSION entry's (round 24): session Paid beyond
    (balance + own Total) is refused bilingually, nothing saved."""
    _seed_users()
    fid = _seed_patient("NegDelta")
    try:
        save_financial(fid, "11", 600000, 350000, TODAY, doctor="doc_x",
                       entered_by="doc_x")
        caps, restore = _patch_msgs()
        try:
            for lang, needle in (("en", "maximum"), ("ar", "الحد الأقصى")):
                root, tab = _build_clinical("doc_x", "doctor", fid, lang)
                if tab is None:
                    print("SKIP test_session_overpayment_refused_bilingually (no display)"); return
                try:
                    from src.ui import clinical_session_entry as _entry
                    for w, txt in ((tab.txt_complaint, "Pain"), (tab.txt_sym, "Sharp"),
                                   (tab.txt_diagnosis, "Caries"), (tab.txt_procedure, "Filling")):
                        w.delete("1.0", tk.END); w.insert("1.0", txt)
                    tab.e_sess_date.delete(0, tk.END); tab.e_sess_date.insert(0, TODAY)
                    tab.e_sess_tooth.delete(0, tk.END); tab.e_sess_tooth.insert(0, "11")
                    _entry.set_money(tab, 0, 300000)  # balance is 250,000
                    tab.btn_save_visit.invoke(); root.update_idletasks()
                    assert caps["error"], f"no refusal in {lang}"
                    assert needle in caps["error"][-1][1], caps["error"][-1]
                    assert patient_totals(fid) == {"total": 600000.0, "paid": 350000.0,
                                                   "remaining": 250000.0}
                    assert _rows(fid) == 1
                finally:
                    root.destroy()
        finally:
            restore()
    finally:
        _cleanup(fid)

def test_zero_and_empty_save_nothing():
    """Zero-row bug fix: the payment Amount starts at 0 (not the
    cumulative), so Add Payment untouched saves NO row and says
    nothing changed; empty fields save nothing either."""
    assert "unchanged" in t("pay_no_change_msg", "en")
    assert "لم يتغيّر" in t("pay_no_change_msg", "ar")
    _seed_users()
    fid = _seed_patient("ZeroPay")
    fid2 = _seed_patient("EmptyPay")
    try:
        save_financial(fid, "11", 600000, 350000, TODAY, doctor="doc_x",
                       entered_by="doc_x")
        caps, restore = _patch_msgs()
        try:
            root, tab = _build_clinical("doc_x", "doctor", fid)
            if tab is None:
                print("SKIP test_zero_and_empty_save_nothing (no display)"); return
            try:
                # R24: the amount is NOT pre-filled with the cumulative.
                # R38: the payment entry has only the Amount box.
                assert tab.e_paid.get() == "0"
                tab.add_fin(); root.update_idletasks()
                assert _rows(fid) == 1, "an untouched 0 entry must not add a row"
                assert caps["info"] and "unchanged" in caps["info"][-1][1]
                assert patient_totals(fid) == {"total": 600000.0, "paid": 350000.0,
                                               "remaining": 250000.0}
            finally:
                root.destroy()
            root, tab = _build_clinical("doc_x", "doctor", fid2)
            try:
                tab.e_paid.delete(0, tk.END)
                tab.add_fin(); root.update_idletasks()
                assert _rows(fid2) == 0, "empty payment must not add a row"
                assert patient_totals(fid2) == {"total": 0.0, "paid": 0.0,
                                                "remaining": 0.0}
            finally:
                root.destroy()
        finally:
            restore()
    finally:
        _cleanup(fid); _cleanup(fid2)

def test_usd_payment_via_real_form():
    """Real form in USD @ 15,000. ROUND-38 SUPERSESSION: the form
    is the PAYMENT entry (payments only), so 20 then 10 USD pin
    standalone-payment conversion: paid 300,000 then 450,000 base,
    balances -300,000 / -450,000 (credit). Income endpoint same."""
    _seed_users()
    fid = _seed_patient("UsdPay")
    try:
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None:
            print("SKIP test_usd_payment_via_real_form (no display)"); return
        try:
            tab.cur_var.set(display_for_code("USD"))
            tab.e_rate.delete(0, tk.END); tab.e_rate.insert(0, "15000")
            _set(tab, 20, "doc_x")
            tab.add_fin(); root.update_idletasks()
            assert patient_totals(fid) == {"total": 0.0, "paid": 300000.0,
                                           "remaining": -300000.0}, patient_totals(fid)
            _set(tab, 10, "doc_x")
            tab.add_fin(); root.update_idletasks()
            assert patient_totals(fid) == {"total": 0.0, "paid": 450000.0,
                                           "remaining": -450000.0}, patient_totals(fid)
            assert doctor_income("doc_x")["paid"] == 450000.0
        finally:
            root.destroy()
    finally:
        _cleanup(fid)

def test_no_patient_no_crash():
    """Add Payment with no patient selected: warning only, no crash,
    no row written anywhere."""
    _seed_users()
    caps, restore = _patch_msgs()
    try:
        root, tab = _build_clinical("doc_x", "doctor", None)
        if tab is None:
            print("SKIP test_no_patient_no_crash (no display)"); return
        try:
            tab.add_fin(); root.update_idletasks()
            assert caps["warn"], "no-patient add must warn"
        finally:
            root.destroy()
    finally:
        restore(); _cleanup()

def test_doctor_cannot_pay_for_other_doctor():
    """Doctor's real form with the treating doctor set to another
    doctor: refused bilingually, totals and row count unchanged."""
    _seed_users()
    fid = _seed_patient("OtherDoc")
    try:
        save_financial(fid, "11", 500000, 300000, TODAY, doctor="doc_x",
                       entered_by="doc_x")
        caps, restore = _patch_msgs()
        try:
            root, tab = _build_clinical("doc_x", "doctor", fid)
            if tab is None:
                print("SKIP test_doctor_cannot_pay_for_other_doctor (no display)"); return
            try:
                _set(tab, 500000, "doc_y")
                tab.add_fin(); root.update_idletasks()
                assert caps["error"], "doctor paying for another doctor must be refused"
                assert "only" in caps["error"][-1][1].lower()
                assert patient_totals(fid) == {"total": 500000.0, "paid": 300000.0,
                                               "remaining": 200000.0}
                assert _rows(fid) == 1
                assert doctor_income("doc_y")["paid"] == 0.0
            finally:
                root.destroy()
        finally:
            restore()
    finally:
        _cleanup(fid)
