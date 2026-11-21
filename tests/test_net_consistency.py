"""Net consistency (owner rule, 2026-11-07): total_expenses must include
salary payments everywhere - the top "Total Expenses" card (net_income)
and the per-center breakdown (per_center_totals) must agree, and the
net must be identical. Salaries use payment_date, expenses use date."""
from src.models.database import init_db, get_connection
from src.models.finance import net_income, per_center_totals
from src.models import salaries as S

START, END = "2026-11-01", "2026-11-30"
MARK = "NET-CONSISTENCY-TEST"
EXP_IN, SAL_IN, SAL_OUT = 100000.0, 200000.0, 50000.0


def _seed():
    """One expense + one salary inside the range, one salary outside it.
    Returns (employee_id, expense_id, [salary_payment_ids])."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO expenses(date,category,description,amount,center_id) "
                "VALUES(?,?,?,?,?)", ("2026-11-05", "test", MARK, EXP_IN, "main"))
    exp_id = cur.lastrowid
    conn.commit()
    eid = S.add_employee(conn, "admin", MARK, "nurse", 500000, "main")
    S.record_salary_payment(conn, "admin", eid, "2026-11", SAL_IN,
                            "2026-11-05", "fady")
    S.record_salary_payment(conn, "admin", eid, "2026-10", SAL_OUT,
                            "2026-10-01", "fady")
    conn.commit()
    ids = [r[0] for r in cur.execute(
        "SELECT id FROM salary_payments WHERE employee_id=?", (eid,))]
    conn.close()
    return eid, exp_id, ids


def _cleanup(eid, exp_id, sal_ids):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
    cur.execute("DELETE FROM salary_payments WHERE employee_id=?", (eid,))
    cur.execute("DELETE FROM employees WHERE id=?", (eid,))
    for t, rid in [("expenses", exp_id), ("employees", eid)] + \
            [("salary_payments", i) for i in sal_ids]:
        # queue_synced_row stores record_id as "table:id"
        cur.execute("DELETE FROM sync_queue WHERE table_name=? AND record_id IN (?,?)",
                    (t, str(rid), f"{t}:{rid}"))
    conn.commit(); conn.close()


def test_expenses_include_salaries_in_range():
    before = net_income(START, END)
    eid, exp_id, sal_ids = _seed()
    try:
        res = net_income(START, END)
        assert res["total_expenses"] == before["total_expenses"] + EXP_IN + SAL_IN
        # Out-of-range salary (Oct) must NOT leak into the Nov range.
        assert res["total_expenses"] != before["total_expenses"] + EXP_IN + SAL_IN + SAL_OUT
        assert res["net_income"] == before["net_income"] - EXP_IN - SAL_IN
    finally:
        _cleanup(eid, exp_id, sal_ids)


def test_per_center_sum_matches_net():
    eid, exp_id, sal_ids = _seed()
    try:
        res = net_income(START, END)
        centers = per_center_totals(START, END)
        assert sum(c["expenses"] for c in centers) == res["total_expenses"]
        assert sum(c["net"] for c in centers) == res["net_income"]
        assert sum(c["income"] for c in centers) == res["total_income"]
        assert sum(c["lab"] for c in centers) == res["total_lab"]
        assert sum(c["debts"] for c in centers) == res["total_debts"]
    finally:
        _cleanup(eid, exp_id, sal_ids)


def test_result_keys_unchanged():
    res = net_income(START, END)
    assert set(res) == {"total_income", "total_expenses", "total_lab",
                        "total_debts", "net_income", "net_if_debts_collected",
                        "total_income_usd", "net_usd", "rate", "base_currency"}
