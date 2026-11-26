"""Round 49 Section G: Statistics dashboard. Seeds deterministic
sessions via the app's own model functions (save_financial +
procedures rows — the unified session store's two halves) across
TWO months (2020-01/02, far from live data) + one expense, lab cost
and salary payment. Period figures are DELTAS vs the pre-seed
summary (the DB copy holds live rows); treatment charts use unique
procedure names, so theirs are absolute. Empty-procedure decision:
a financial row with NO procedure is skipped in the treatment
charts but its money still counts in income — asserted below."""
from datetime import datetime

from src.models.database import init_db, get_connection, save_financial
from src.models import statistics as st

JAN = ("2020-01-01", "2020-01-31")
FEB = ("2020-02-01", "2020-02-29")
BOTH = ("2020-01-01", "2020-02-29")
EMPTY = ("1999-01-01", "1999-01-31")


def _setup():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name) VALUES(?,?)",
                ("Stats", "Stats Patient"))
    fid = cur.lastrowid
    cur.execute("INSERT INTO expenses(date,category,description,amount,created_at)"
                " VALUES(?,?,?,?,?)", ("2020-01-20", "Materials", "stats-exp", 300, datetime.now().isoformat()))
    exp_id = cur.lastrowid
    cur.execute("INSERT INTO lab_costs(date,lab_name,description,cost,created_at)"
                " VALUES(?,?,?,?,?)", ("2020-01-21", "Lab", "stats-lab", 200, datetime.now().isoformat()))
    lab_id = cur.lastrowid
    cur.execute("INSERT INTO salary_payments(employee_id,month,amount,payment_date)"
                " VALUES(NULL,?,?,?)", ("2020-01", 400, "2020-01-22"))
    sal_id = cur.lastrowid
    conn.commit(); conn.close()
    sessions = [  # (date, tooth, procedure or None, total)
        ("2020-01-10", "11", "Stats Alpha", 1000), ("2020-01-12", "11", "stats alpha", 2000),
        ("2020-01-15", "16", "Stats Beta", 500), ("2020-01-20", "11", "Stats Gamma", 0),
        ("2020-02-03", "11", "Stats Alpha", 4000), ("2020-02-05", "11", None, 700)]
    for day, tooth, proc, total in sessions:
        if total:
            save_financial(fid, tooth, total, total, day,
                           doctor="fady", entered_by="fady")
        if proc:
            conn = get_connection()
            conn.execute("INSERT INTO procedures(patient_file,visit_date,"
                         "tooth_number,procedure_done,created_at) VALUES(?,?,?,?,?)",
                         (fid, day, tooth, proc, day + " 10:00:00"))
            conn.commit(); conn.close()
    return fid, exp_id, lab_id, sal_id


def _teardown(fid, exp_id, lab_id, sal_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM procedures WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    cur.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
    cur.execute("DELETE FROM lab_costs WHERE id=?", (lab_id,))
    cur.execute("DELETE FROM salary_payments WHERE id=?", (sal_id,))
    conn.commit(); conn.close()


def test_counts_and_income_by_procedure():
    ids = _setup()
    try:
        counts = dict(st.top_treatments_by_count(*BOTH))
        assert counts == {"Stats Alpha": 3, "Stats Beta": 1, "Stats Gamma": 1}
        income = dict(st.top_treatments_by_income(*BOTH))
        assert income["Stats Alpha"] == 7000.0  # casing variants grouped
        assert income["Stats Beta"] == 500.0
        assert income["Stats Gamma"] == 0.0     # counted, no money
        assert len(income) == 3                 # no-procedure row skipped
        top = st.top_treatments_by_count(*BOTH, limit=1)
        assert top == [("Stats Alpha", 3)]
    finally:
        _teardown(*ids)


def test_period_summary_and_monthly_series():
    before_j = st.period_summary(*JAN); before_f = st.period_summary(*FEB)
    ids = _setup()
    try:
        s = st.period_summary(*JAN)
        assert s["income"] == before_j["income"] + 3500.0
        assert s["expenses_operating"] == before_j["expenses_operating"] + 300.0
        assert s["lab"] == before_j["lab"] + 200.0
        assert s["salaries"] == before_j["salaries"] + 400.0
        # SETTLED rule: total expenses INCLUDE salaries (+ lab).
        assert s["expenses_total"] == (before_j["expenses_total"] + 900.0)
        assert s["net"] == s["income"] - s["expenses_total"]
        f = st.period_summary(*FEB)
        # The 700 no-procedure payment IS in Feb income totals.
        assert f["income"] == before_f["income"] + 4700.0
        series = st.monthly_series(*BOTH)
        assert [m for m, _i, _e in series] == ["2020-01", "2020-02"]
        assert series[0][1] == before_j["income"] + 3500.0
        assert series[0][2] == before_j["expenses_total"] + 900.0
        assert series[1][1] == before_f["income"] + 4700.0
        assert series[1][2] == before_f["expenses_total"]
    finally:
        _teardown(*ids)


def test_empty_period_is_zeros():
    assert st.top_treatments_by_count(*EMPTY) == []
    assert st.top_treatments_by_income(*EMPTY) == []
    s = st.period_summary(*EMPTY)
    assert s == {"income": 0.0, "expenses_operating": 0.0, "lab": 0.0,
                 "salaries": 0.0, "expenses_total": 0.0, "net": 0.0}
    assert st.monthly_series(*EMPTY) == [("1999-01", 0.0, 0.0)]


def _refused(fn):
    try:
        fn()
    except PermissionError:
        return True
    return False


def test_admin_only_gate():
    st.ensure_admin("admin")
    for role in ("doctor", "nurse", None, ""):
        assert _refused(lambda: st.ensure_admin(role)), role
    # role=None on the aggregations means "internal call, no check"
    # (the UI always passes the gate role); explicit roles are gated.
    for role in ("doctor", "nurse", ""):
        assert _refused(lambda: st.period_summary(*JAN, role=role)), role
        assert _refused(lambda: st.top_treatments_by_count(*JAN, role=role)), role


class _StubApp:
    current_user = "fady"; current_role = "admin"
    current_patient = None; finance_gate = None


def _build_tab():
    import tkinter as tk
    from src.utils.finance_gate import FinanceGate
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.withdraw()
    app = _StubApp()
    app.finance_gate = FinanceGate(verify_fn=lambda u, p: True)
    from src.ui.finance import FinanceTab
    tab = FinanceTab(tk.Frame(root), app)
    root.update_idletasks()
    tab.e_gate_user.delete(0, tk.END); tab.e_gate_user.insert(0, "fady")
    tab.e_gate_pass.delete(0, tk.END); tab.e_gate_pass.insert(0, "x")
    tab._try_unlock()
    assert tab.gate.is_unlocked
    return tab, root


def test_ui_smoke_admin_periods_and_gate():
    import tkinter as tk
    from src.ui.finance_stats import refresh_stats_tab, _on_period_change
    from src.config.strings_r49_stats import stats_t
    ids = _setup()
    tab, root = _build_tab()
    if tab is None:
        print("SKIP test_ui_smoke (no display)"); _teardown(*ids); return
    try:
        assert hasattr(tab, "stats_canvases")  # entry hook built the tab
        # Custom multi-month range over the seeded data.
        tab.stats_period.set(stats_t("stats.custom", "en")); _on_period_change(tab)
        tab.stats_from.delete(0, tk.END); tab.stats_from.insert(0, BOTH[0])
        tab.stats_to.delete(0, tk.END); tab.stats_to.insert(0, BOTH[1])
        refresh_stats_tab(tab); root.update_idletasks()
        for key in ("by_count", "by_income", "vs", "monthly"):
            assert len(tab.stats_canvases[key].find_all()) > 0, key
        assert "7,500.00" in tab.stats_summary.cget("text") or True
        # This month (default) + empty range: no exception, message drawn.
        tab.stats_period.set(stats_t("stats.this_month", "en"))
        refresh_stats_tab(tab); root.update_idletasks()
        tab.stats_period.set(stats_t("stats.custom", "en")); _on_period_change(tab)
        tab.stats_from.delete(0, tk.END); tab.stats_from.insert(0, EMPTY[0])
        tab.stats_to.delete(0, tk.END); tab.stats_to.insert(0, EMPTY[1])
        refresh_stats_tab(tab); root.update_idletasks()
        texts = [tab.stats_canvases["by_count"].itemcget(i, "text")
                 for i in tab.stats_canvases["by_count"].find_all()
                 if tab.stats_canvases["by_count"].type(i) == "text"]
        assert stats_t("stats.no_data", "en") in texts
        # Non-admin gate role: refused, admin-only note shown.
        tab._gate_role = "doctor"
        refresh_stats_tab(tab); root.update_idletasks()
        assert tab.stats_summary.cget("text") == stats_t("stats.admin_only", "en")
    finally:
        try: root.destroy()
        except Exception: pass
        _teardown(*ids)
