"""Salaries: no-login employees, monthly paid/remaining, salary payments
as center expenses, admin-only access. Login never consults the
employees table (users table only) - proven against the real server."""
import os, sqlite3, sys, tempfile, threading
from pathlib import Path
from src.models.database import get_connection, init_db
from src.models.finance import per_center_totals
from src.models.permissions import can_manage_salaries
from src.models import salaries as S
from src.models.sync import SyncClient


def _mem():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_employee_without_login_and_month_status():
    conn = _mem(); S.ensure_tables(conn)
    eid = S.add_employee(conn, "admin", "Ghost Nurse", "nurse", 500000, "main")
    st = S.employee_month_status(conn, "admin", eid, "2026-11")
    assert (st["monthly_salary"], st["paid"], st["remaining"]) == (500000, 0, 500000)
    S.record_salary_payment(conn, "admin", eid, "2026-11", 200000, "2026-11-05", "fady")
    st = S.employee_month_status(conn, "admin", eid, "2026-11")
    assert (st["paid"], st["remaining"]) == (200000, 300000)
    S.record_salary_payment(conn, "admin", eid, "2026-11", 100000, "2026-11-20", "fady")
    st = S.employee_month_status(conn, "admin", eid, "2026-11")
    assert (st["paid"], st["remaining"]) == (300000, 200000)
    st2 = S.employee_month_status(conn, "admin", eid, "2026-10")
    assert (st2["paid"], st2["remaining"]) == (0, 500000)
    conn.close()


def test_month_summary_lists_all_employees():
    conn = _mem(); S.ensure_tables(conn)
    e1 = S.add_employee(conn, "admin", "A One", "doctor", 100000, "main")
    e2 = S.add_employee(conn, "admin", "B Two", "nurse", 200000, "main")
    S.record_salary_payment(conn, "admin", e1, "2026-11", 40000, "2026-11-03", "fady")
    rows = {r["employee_id"]: r for r in S.month_summary(conn, "admin", "2026-11")}
    assert (rows[e1]["paid"], rows[e1]["remaining"]) == (40000, 60000)
    assert (rows[e2]["paid"], rows[e2]["remaining"]) == (0, 200000)
    conn.close()


def test_set_monthly_salary_updates_remaining():
    conn = _mem(); S.ensure_tables(conn)
    eid = S.add_employee(conn, "admin", "Up", "doctor", 100000, "main")
    S.set_monthly_salary(conn, "admin", eid, 200000)
    st = S.employee_month_status(conn, "admin", eid, "2026-11")
    assert (st["monthly_salary"], st["remaining"]) == (200000, 200000)
    conn.close()


def test_bad_month_and_inactive_employee_rejected():
    conn = _mem(); S.ensure_tables(conn)
    eid = S.add_employee(conn, "admin", "Temp", "other", 100000, "main")
    for bad in ("2026-1", "11-2026", "", None):
        try:
            S.record_salary_payment(conn, "admin", eid, bad, 100, "2026-11-01", "fady")
            raise AssertionError(f"month {bad!r} should be rejected")
        except ValueError:
            pass
    S.set_employee_active(conn, "admin", eid, False)
    try:
        S.record_salary_payment(conn, "admin", eid, "2026-11", 100, "2026-11-01", "fady")
        raise AssertionError("inactive employee should be rejected")
    except ValueError:
        pass
    conn.close()


def test_non_admin_cannot_use_salary_functions():
    conn = _mem(); S.ensure_tables(conn)
    assert can_manage_salaries("admin") is True
    assert can_manage_salaries("doctor") is False
    assert can_manage_salaries("nurse") is False
    for role in ("doctor", "nurse", None):
        for fn in (lambda: S.add_employee(conn, role, "X", "other", 100, "main"),
                   lambda: S.list_employees(conn, role),
                   lambda: S.record_salary_payment(conn, role, 1, "2026-11", 100, "2026-11-01", "x"),
                   lambda: S.month_summary(conn, role, "2026-11"),
                   lambda: S.employee_month_status(conn, role, 1, "2026-11"),
                   lambda: S.set_monthly_salary(conn, role, 1, 100),
                   lambda: S.set_employee_active(conn, role, 1, False)):
            try:
                fn()
                raise AssertionError(f"role {role!r} should be refused")
            except PermissionError:
                pass
    conn.close()


def test_salary_payment_counts_as_center_expense():
    """A salary payment appears in the admin per-center breakdown as an
    expense of the employee's center (real DB, cleaned up after)."""
    init_db()
    conn = get_connection()
    eid = pay_id = None
    try:
        eid = S.add_employee(conn, "admin", "Sal Test Nurse", "nurse", 400000, "tst-sal")
        before = {r["center_id"]: r for r in per_center_totals()}
        pay_id = S.record_salary_payment(conn, "admin", eid, "2026-11", 150000, "2026-11-05", "fady")
        after = {r["center_id"]: r for r in per_center_totals()}
        assert after["tst-sal"]["salaries"] == 150000
        assert after["tst-sal"]["expenses"] == before.get("tst-sal", {}).get("expenses", 0) + 150000
    finally:
        cur = conn.cursor()
        cur.execute("DELETE FROM salary_payments WHERE employee_id=?", (eid,))
        cur.execute("DELETE FROM employees WHERE id=?", (eid,))
        cur.execute("DELETE FROM sync_queue WHERE record_id IN (?, ?)",
                    (f"employees:{eid}", f"salary_payments:{pay_id}"))
        conn.commit(); conn.close()


def test_per_center_range_includes_salaries():
    """Regression (2026-11-07): the UI always passes a date range to
    per_center_totals; salary_payments has payment_date, not date, so the
    ranged query used to fail silently and report salaries 0.00."""
    init_db()
    conn = get_connection()
    eid = pay_id = None
    try:
        eid = S.add_employee(conn, "admin", "Range Test", "nurse", 400000, "tst-sal-r")
        pay_id = S.record_salary_payment(conn, "admin", eid, "2026-11", 150000, "2026-11-05", "fady")
        conn.commit()
        rows = {r["center_id"]: r for r in per_center_totals("2026-11-01", "2026-11-30")}
        assert rows["tst-sal-r"]["salaries"] == 150000, rows["tst-sal-r"]
        assert rows["tst-sal-r"]["expenses"] == 150000
        assert rows["tst-sal-r"]["net"] == -150000
    finally:
        cur = conn.cursor()
        cur.execute("DELETE FROM salary_payments WHERE employee_id=?", (eid,))
        cur.execute("DELETE FROM employees WHERE id=?", (eid,))
        cur.execute("DELETE FROM sync_queue WHERE record_id IN (?, ?)",
                    (f"employees:{eid}", f"salary_payments:{pay_id}"))
        conn.commit(); conn.close()


def test_no_login_employee_cannot_authenticate():
    """An employee row - with or without a linked username - can NEVER
    log in: server login consults ONLY the users table."""
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "server"))
    import sync_server
    from http.server import ThreadingHTTPServer
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    sync_server.DB_PATH = Path(tmp.name)
    sync_server.init_db(Path(tmp.name))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), sync_server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}"
        conn = _mem(); S.ensure_tables(conn)
        S.add_employee(conn, "admin", "Ghost Nurse", "nurse", 500000, "main")
        S.add_employee(conn, "admin", "Ghost Doc", "doctor", 600000, "main",
                       linked_username="ghostdoc")
        conn.close()
        assert SyncClient(url).login("Ghost Nurse", "anything")[0] is False
        assert SyncClient(url).login("ghostdoc", "anything")[0] is False
        assert SyncClient(url).login("fady", "1234")[0] is True  # real user still works
    finally:
        srv.shutdown(); srv.server_close()
        os.unlink(tmp.name)
