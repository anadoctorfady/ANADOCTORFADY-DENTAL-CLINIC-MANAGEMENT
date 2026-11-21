"""Finance sync: server-side role filtering, per-center aggregation,
last-write-wins, offline standalone. Uses the REAL sync server on a
temp DB (like test_sync_roles)."""
import os, sqlite3, sys, tempfile, threading
from datetime import date
from pathlib import Path
from src.models.database import get_connection, init_db, save_financial
from src.models.finance import net_income, per_center_totals
from src.models.salaries import ensure_tables as sal_tables
from src.models.sync import (ensure_tables as sync_tables, queue_change,
                             SyncClient, sync_now)

NOW = "2026-11-07T10:00:00"
OLD = "2026-11-07T09:00:00"


def _mem():
    conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row
    return conn


def _clinic_tables(conn):
    conn.execute("CREATE TABLE patients(file_number INTEGER PRIMARY KEY, full_name TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE financials(id INTEGER PRIMARY KEY, patient_file INT, tooth_number TEXT, total_cost REAL, paid_amount REAL, remaining REAL, visit_date TEXT, currency TEXT, exchange_rate REAL, rate_date TEXT, total_syp REAL, paid_syp REAL, remaining_syp REAL, doctor TEXT, entered_by TEXT, center_id TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE expenses(id INTEGER PRIMARY KEY, date TEXT, category TEXT, description TEXT, amount REAL, created_at TEXT, center_id TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE lab_costs(id INTEGER PRIMARY KEY, date TEXT, lab_name TEXT, patient_file INT, tooth_number TEXT, description TEXT, cost REAL, center_id TEXT, updated_at TEXT)")
    conn.commit()


def _pay(doctor, by, amount=5000, center="main", updated_at=NOW):
    """Payment payload: total == paid, no remainder."""
    return {"patient_file": 9001, "total_cost": amount, "paid_amount": amount, "remaining": 0,
            "visit_date": "2026-11-07", "total_syp": amount, "paid_syp": amount, "remaining_syp": 0,
            "doctor": doctor, "entered_by": by, "center_id": center, "updated_at": updated_at}


def _server():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "server"))
    import sync_server
    from auth import hash_password
    from http.server import ThreadingHTTPServer
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    sync_server.DB_PATH = Path(tmp.name); sync_server.init_db(Path(tmp.name))
    conn = sqlite3.connect(tmp.name)
    for u, pw, role, center in (("doc_a", "pw_a", "doctor", "main"), ("doc_b", "pw_b", "doctor", "branch2"), ("nurse1", "pw_n", "nurse", "main")):
        h, s = hash_password(pw); conn.execute("INSERT INTO users(username,password_hash,salt,role,center_id,created_at) VALUES(?,?,?,?,?,datetime('now'))", (u, h, s, role, center))
    conn.commit(); conn.close()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), sync_server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}", srv, tmp.name


def _stop(srv, db_path):
    srv.shutdown(); srv.server_close(); os.unlink(db_path)


def _fresh_conn():
    c = _mem(); _clinic_tables(c); sync_tables(c); sal_tables(c); return c


def _queue_admin_batch(c):
    """2 payments (2 doctors / 2 centers), 2 expenses, 1 lab, 1 salary, 1 employee."""
    queue_change(c, "financials", "financials:1", _pay("doc_a", "nurse1", 100000))
    queue_change(c, "financials", "financials:2", dict(_pay("doc_b", "fady", 80000), patient_file=9002, center_id="branch2"))
    queue_change(c, "expenses", "expenses:1", {"date": "2026-11-07", "category": "Rent", "description": "rent", "amount": 50000, "center_id": "main", "updated_at": NOW})
    queue_change(c, "expenses", "expenses:2", {"date": "2026-11-07", "category": "Rent", "description": "rent", "amount": 40000, "center_id": "branch2", "updated_at": NOW})
    queue_change(c, "lab_costs", "lab_costs:1", {"date": "2026-11-07", "lab_name": "Lab", "patient_file": 9001, "description": "crown", "cost": 30000, "center_id": "main", "updated_at": NOW})
    queue_change(c, "salary_payments", "salary_payments:1", {"employee_id": 1, "month": "2026-11", "amount": 400000, "payment_date": "2026-11-07", "entered_by": "fady", "center_id": "branch2", "updated_at": NOW})
    queue_change(c, "employees", "employees:1", {"name": "Ghost Nurse", "job_title": "nurse", "monthly_salary": 400000, "center_id": "branch2", "linked_username": None, "phone": "", "active": 1, "updated_at": NOW})


def _pull_as(url, username, password):
    c = _fresh_conn(); cl = SyncClient(url)
    assert cl.login(username, password)[0], username
    ok, counts = cl.pull(c, "main", "")
    assert ok, counts
    return c, counts


def test_server_pull_filtering():
    url, srv, db_path = _server()
    try:
        c1 = _fresh_conn(); _queue_admin_batch(c1)
        cl = SyncClient(url)
        assert cl.login("fady", "1234")[0] is True
        ok, applied = cl.push(c1, "main")
        assert ok and applied == 7, (ok, applied)
        c1.close()
        # Admin: ALL centers, everything.
        c2, counts = _pull_as(url, "fady", "1234")
        assert counts["financials"] == 6 and counts["employees"] == 1, counts
        assert c2.execute("SELECT COUNT(*) FROM financials").fetchone()[0] == 2
        assert c2.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 2
        assert c2.execute("SELECT COUNT(*) FROM lab_costs").fetchone()[0] == 1
        assert c2.execute("SELECT COUNT(*) FROM salary_payments").fetchone()[0] == 1
        assert c2.execute("SELECT name FROM employees").fetchone()[0] == "Ghost Nurse"
        c2.close()
        # Doctor A: ONLY their own payment (any center), nothing else.
        c3, counts = _pull_as(url, "doc_a", "pw_a")
        assert counts["financials"] == 1 and counts["employees"] == 0, counts
        rows = c3.execute("SELECT doctor FROM financials").fetchall()
        assert len(rows) == 1 and rows[0][0] == "doc_a"
        assert all(c3.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0 for t in ("expenses", "salary_payments", "employees"))
        c3.close()
        # Nurse: NO financial records at all, no employees.
        c4, counts = _pull_as(url, "nurse1", "pw_n")
        assert counts["financials"] == 0 and counts["employees"] == 0, counts
        assert all(c4.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0 for t in ("financials", "employees"))
        c4.close()
    finally:
        _stop(srv, db_path)


def test_push_rejection_for_non_admin():
    url, srv, db_path = _server()
    try:
        # NOTE (2026-11-07, new push rule): doctor-for-other-doctor and
        # nurse-for-treating-doctor payments are now LEGAL - see
        # tests/test_finance_sync_nurse.py. Only admin-only kinds refused.
        for user, pw, table, rid, payload in (
                ("doc_a", "pw_a", "salary_payments", "salary_payments:9", {"employee_id": 1, "month": "2026-11", "amount": 1000, "payment_date": "2026-11-07", "entered_by": "doc_a", "center_id": "main", "updated_at": NOW}),
                ("doc_a", "pw_a", "employees", "employees:9", {"name": "Sneaky", "job_title": "other", "monthly_salary": 1000, "center_id": "main", "active": 1, "updated_at": NOW})):
            c = _fresh_conn(); queue_change(c, table, rid, payload)
            cl = SyncClient(url); assert cl.login(user, pw)[0]
            assert cl.push(c, "main")[0] is False, (user, table)
            c.close()
        # Doctor pushing their OWN payment -> 200.
        c = _fresh_conn(); queue_change(c, "financials", "financials:9", _pay("doc_a", "doc_a"))
        cl = SyncClient(url); assert cl.login("doc_a", "pw_a")[0]
        ok, applied = cl.push(c, "main")
        assert ok and applied == 1, (ok, applied)
        c.close()
        # Server holds only the one legitimate payment.
        c2, counts = _pull_as(url, "fady", "1234")
        assert counts["financials"] == 1
        assert tuple(c2.execute("SELECT doctor, paid_syp FROM financials").fetchone()) == ("doc_a", 5000.0)
        c2.close()
    finally:
        _stop(srv, db_path)


def test_last_write_wins():
    url, srv, db_path = _server()
    try:
        cl = SyncClient(url); assert cl.login("fady", "1234")[0]
        c = _fresh_conn()
        queue_change(c, "financials", "financials:5", _pay("doc_a", "fady", 100))
        ok, applied = cl.push(c, "main")
        assert ok and applied == 1
        # Older update for the same record must NOT overwrite the newer one.
        queue_change(c, "financials", "financials:5", _pay("doc_a", "fady", 999, updated_at=OLD))
        ok, applied = cl.push(c, "main")
        assert ok and applied == 0, (ok, applied)
        c.close()
        c2, _ = _pull_as(url, "fady", "1234")
        assert c2.execute("SELECT paid_syp FROM financials WHERE id=5").fetchone()[0] == 100.0
        c2.close()
    finally:
        _stop(srv, db_path)


def test_per_center_aggregation_totals():
    """Admin per-center view: income / expenses / lab / debts / net per center."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name) VALUES(?,?)", ("Ctr", "Ctr Test"))
    fid = cur.lastrowid
    conn.commit()  # release the write lock: save_financial opens its own connection
    today = date.today().isoformat()
    try:
        save_financial(fid, "11", 100000, 100000, today, doctor="doc_a", entered_by="fady", center_id="tst-a")
        save_financial(fid, "11", 50000, 30000, today, doctor="doc_b", entered_by="fady", center_id="tst-b")
        cur.execute("INSERT INTO expenses(date,category,description,amount,center_id,updated_at) VALUES(?,?,?,?,?,?)", (today, "Rent", "r", 20000, "tst-a", today))
        cur.execute("INSERT INTO lab_costs(date,lab_name,patient_file,description,cost,center_id,updated_at) VALUES(?,?,?,?,?,?,?)", (today, "Lab", fid, "crown", 5000, "tst-a", today))
        conn.commit()
        rows = {r["center_id"]: r for r in per_center_totals()}
        a, b = rows["tst-a"], rows["tst-b"]
        assert (a["income"], a["expenses"], a["lab"], a["debts"], a["net"]) == (100000, 20000, 5000, 0, 75000)
        assert (b["income"], b["expenses"], b["lab"], b["debts"], b["net"]) == (30000, 0, 0, 20000, 30000)
    finally:
        for (i,) in cur.execute("SELECT id FROM financials WHERE patient_file=?", (fid,)):
            cur.execute("DELETE FROM sync_queue WHERE table_name='financials' AND record_id=?", (f"financials:{i}",))
        cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
        cur.execute("DELETE FROM expenses WHERE center_id IN ('tst-a','tst-b')")
        cur.execute("DELETE FROM lab_costs WHERE center_id IN ('tst-a','tst-b')")
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
        conn.commit(); conn.close()


def test_offline_standalone_still_works():
    """No server URL: sync reports offline, local finance still works."""
    c = _fresh_conn()
    res = sync_now(c, "", "fady", "1234", "main")
    assert res["offline"] is True
    assert sync_now(c, "http://127.0.0.1:1", "fady", "1234", "main")["offline"] is True
    assert isinstance(net_income(), dict)
    assert isinstance(per_center_totals(), list)
    c.close()
