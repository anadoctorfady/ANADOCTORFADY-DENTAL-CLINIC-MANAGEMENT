"""Flexible finance totals (Round 12, Job 9a): toggles for lab costs,
salaries and expenses choose which components the displayed totals
include, without opening each tab. Model tests use before/after
deltas (the isolated DB copy already holds live rows). Covers the
admin-only expense/lab edit+delete model helpers. GUI tests live in
tests/test_finance_totals_gui.py."""
from datetime import date, datetime, timedelta
from src.models.database import init_db, get_connection, save_financial
from src.models.finance_totals import flexible_totals
from src.models.finance_records import (may_change_record, delete_expense,
                                        delete_lab_cost, update_expense_amount,
                                        update_lab_cost)

TODAY = date.today().isoformat()
LAST_MONTH = (date.today().replace(day=1) - timedelta(days=1)).isoformat()


def _setup():
    """Seed one income row (paid 100000), one expense (40000), one lab
    cost (10000) and one salary payment (20000), all dated today.
    Returns the row ids for teardown."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name) VALUES(?,?)",
                ("Tot", "Tot Totals"))
    fid = cur.lastrowid
    cur.execute("INSERT INTO expenses(date,category,description,amount,created_at)"
                " VALUES(?,?,?,?,?)", (TODAY, "Materials", "tot-exp", 40000, datetime.now().isoformat()))
    exp_id = cur.lastrowid
    cur.execute("INSERT INTO lab_costs(date,lab_name,description,cost,created_at)"
                " VALUES(?,?,?,?,?)", (TODAY, "Lab", "tot-lab", 10000, datetime.now().isoformat()))
    lab_id = cur.lastrowid
    cur.execute("INSERT INTO salary_payments(employee_id,month,amount,payment_date)"
                " VALUES(NULL,?,?,?)", (TODAY[:7], 20000, TODAY))
    sal_id = cur.lastrowid
    conn.commit(); conn.close()
    save_financial(fid, "11", 100000, 100000, TODAY, doctor="fady", entered_by="fady")
    return fid, exp_id, lab_id, sal_id


def _teardown(fid, exp_id, lab_id, sal_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    cur.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
    cur.execute("DELETE FROM lab_costs WHERE id=?", (lab_id,))
    cur.execute("DELETE FROM salary_payments WHERE id=?", (sal_id,))
    conn.commit(); conn.close()


def test_toggle_combinations_produce_right_totals():
    """Every toggle combination: included components count, excluded
    ones report 0, net = income - included only."""
    before = flexible_totals(TODAY, TODAY)
    fid, exp_id, lab_id, sal_id = _setup()
    try:
        all_on = flexible_totals(TODAY, TODAY)
        assert all_on["total_income"] == before["total_income"] + 100000.0
        assert all_on["total_expenses"] == before["total_expenses"] + 60000.0
        assert all_on["expenses_only"] == before["expenses_only"] + 40000.0
        assert all_on["salaries"] == before["salaries"] + 20000.0
        assert all_on["total_lab"] == before["total_lab"] + 10000.0
        assert all_on["net_income"] == before["net_income"] + 100000.0 - 70000.0
        assert set(all_on["included"]) == {"lab", "salaries", "expenses"}
        lab_only = flexible_totals(TODAY, TODAY, include_lab=True,
                                   include_salaries=False, include_expenses=False)
        assert lab_only["total_lab"] == before["total_lab"] + 10000.0
        assert lab_only["total_expenses"] == 0.0
        assert lab_only["salaries"] == 0.0
        assert lab_only["net_income"] == before["total_income"] + 100000.0 - (before["total_lab"] + 10000.0)
        assert lab_only["included"] == ("lab",)
        lab_sal = flexible_totals(TODAY, TODAY, include_lab=True,
                                  include_salaries=True, include_expenses=False)
        assert lab_sal["total_expenses"] == before["salaries"] + 20000.0
        assert lab_sal["expenses_only"] == 0.0
        assert lab_sal["total_lab"] == before["total_lab"] + 10000.0
        assert set(lab_sal["included"]) == {"lab", "salaries"}
        none = flexible_totals(TODAY, TODAY, include_lab=False,
                               include_salaries=False, include_expenses=False)
        assert none["total_expenses"] == 0.0 and none["total_lab"] == 0.0
        assert none["net_income"] == before["total_income"] + 100000.0
        assert none["included"] == ()
    finally:
        _teardown(fid, exp_id, lab_id, sal_id)


def test_totals_respect_date_range():
    """A row dated outside the chosen period does not move that
    period's totals, but does move its own period's totals."""
    fid, exp_id, lab_id, sal_id = _setup()
    try:
        before_today = flexible_totals(TODAY, TODAY)
        before_old = flexible_totals(LAST_MONTH, LAST_MONTH)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO expenses(date,category,description,amount,created_at)"
                    " VALUES(?,?,?,?,?)", (LAST_MONTH, "Materials", "old-exp", 99999, datetime.now().isoformat()))
        old_id = cur.lastrowid
        conn.commit(); conn.close()
        try:
            assert flexible_totals(TODAY, TODAY)["expenses_only"] == before_today["expenses_only"]
            assert flexible_totals(LAST_MONTH, LAST_MONTH)["expenses_only"] == before_old["expenses_only"] + 99999.0
        finally:
            conn = get_connection()
            conn.execute("DELETE FROM expenses WHERE id=?", (old_id,))
            conn.commit(); conn.close()
    finally:
        _teardown(fid, exp_id, lab_id, sal_id)


def test_admin_only_expense_lab_model():
    """Finance records are ADMIN-ONLY regardless of age (coordinator
    ruling 2026-11-09): a doctor is refused even on a fresh row, a
    nurse is refused, the admin may change any row, any age."""
    fid, exp_id, lab_id, sal_id = _setup()
    try:
        now = datetime.now().isoformat()
        assert may_change_record("admin", now) is True
        assert may_change_record("doctor", now, "doc_x") is False
        assert may_change_record("nurse", now, "nurse1") is False
        old = (datetime.now() - timedelta(hours=25)).isoformat()
        assert may_change_record("doctor", old, "doc_x") is False
        assert may_change_record("admin", old) is True
        assert may_change_record("admin", None) is True  # admin, any age
        assert may_change_record("doctor", None, "doc_x") is False
        # Update + delete flow: admin succeeds, doctor refused.
        assert update_lab_cost(lab_id, 12000, "admin") is True
        conn = get_connection()
        assert conn.execute("SELECT cost FROM lab_costs WHERE id=?", (lab_id,)).fetchone()[0] == 12000.0
        conn.close()
        assert update_lab_cost(lab_id, -5, "admin") is False  # negative refused
        assert update_expense_amount(exp_id, 41000, "nurse", "nurse1") is False
        assert update_expense_amount(exp_id, 41000, "doctor", "doc_x") is False
        assert delete_lab_cost(lab_id, "doctor", "doc_x") is False
        assert delete_lab_cost(lab_id, "admin") is True
        assert delete_expense(exp_id, "doctor", "doc_x") is False
        assert delete_expense(exp_id, "admin") is True
    finally:
        _teardown(fid, exp_id, lab_id, sal_id)

