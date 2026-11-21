"""Nurse finance push (FIX 1, 2026-11-07): a nurse records payments for
the TREATING doctor, so her push (doctor=X, entered_by=nurse) must be
accepted when X is a real doctor/admin. Uses the REAL sync server on a
temp DB (same harness as test_finance_sync)."""
import os, sqlite3, sys, tempfile, threading
from pathlib import Path
from src.models.sync import (ensure_tables as sync_tables, queue_change,
                             pending_changes, SyncClient)

NOW = "2026-11-07T10:00:00"


def _mem():
    conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row
    return conn


def _clinic_tables(conn):
    conn.execute("CREATE TABLE patients(file_number INTEGER PRIMARY KEY, full_name TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE financials(id INTEGER PRIMARY KEY, patient_file INT, tooth_number TEXT, total_cost REAL, paid_amount REAL, remaining REAL, visit_date TEXT, currency TEXT, exchange_rate REAL, rate_date TEXT, total_syp REAL, paid_syp REAL, remaining_syp REAL, doctor TEXT, entered_by TEXT, center_id TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE expenses(id INTEGER PRIMARY KEY, date TEXT, category TEXT, description TEXT, amount REAL, created_at TEXT, center_id TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE lab_costs(id INTEGER PRIMARY KEY, date TEXT, lab_name TEXT, patient_file INT, tooth_number TEXT, description TEXT, cost REAL, center_id TEXT, updated_at TEXT)")
    conn.commit()


def _pay(doctor, by, amount=5000, center="main"):
    return {"patient_file": 9001, "total_cost": amount, "paid_amount": amount, "remaining": 0,
            "visit_date": "2026-11-07", "total_syp": amount, "paid_syp": amount, "remaining_syp": 0,
            "doctor": doctor, "entered_by": by, "center_id": center, "updated_at": NOW}


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
    c = _mem(); _clinic_tables(c); sync_tables(c); return c


def _push_as(url, user, pw, table, rid, payload):
    c = _fresh_conn(); queue_change(c, table, rid, payload)
    cl = SyncClient(url); assert cl.login(user, pw)[0]
    res = cl.push(c, "main")
    pend = pending_changes(c); c.close()
    return res, pend


def _pull_as(url, username, password):
    c = _fresh_conn(); cl = SyncClient(url)
    assert cl.login(username, password)[0], username
    ok, counts = cl.pull(c, "main", "")
    assert ok, counts
    return c, counts


def test_nurse_push_for_treating_doctor():
    """Nurse pushes a payment for doctor X -> 200; admin + doctor X see
    it on pull; doctor Y does NOT; the queue row is marked synced."""
    url, srv, db_path = _server()
    try:
        res, pend = _push_as(url, "nurse1", "pw_n", "financials", "financials:1", _pay("doc_a", "nurse1", 7000))
        assert res[0] is True and res[1] == 1, res
        assert pend == [], "pushed record must leave the queue"
        c, counts = _pull_as(url, "fady", "1234")
        assert counts["financials"] == 1, counts
        assert tuple(c.execute("SELECT doctor, entered_by, paid_syp FROM financials").fetchone()) == ("doc_a", "nurse1", 7000.0)
        c.close()
        c, counts = _pull_as(url, "doc_a", "pw_a")
        assert counts["financials"] == 1, counts
        assert c.execute("SELECT doctor FROM financials").fetchone()[0] == "doc_a"
        c.close()
        c, counts = _pull_as(url, "doc_b", "pw_b")
        assert counts["financials"] == 0, counts
        assert c.execute("SELECT COUNT(*) FROM financials").fetchone()[0] == 0
        c.close()
    finally:
        _stop(srv, db_path)


def test_nurse_push_empty_doctor_refused():
    """Payment with an empty doctor is refused (403) and stays queued
    for retry - it is never dropped."""
    url, srv, db_path = _server()
    try:
        res, pend = _push_as(url, "nurse1", "pw_n", "financials", "financials:2", _pay("", "nurse1"))
        assert res[0] is False, res  # 403 from the server
        assert len(pend) == 1, "refused record must stay queued"
        c, counts = _pull_as(url, "fady", "1234")
        assert counts["financials"] == 0, counts
        c.close()
    finally:
        _stop(srv, db_path)


def test_nurse_push_unknown_doctor_refused():
    """Doctor value must be a real doctor/admin username in users."""
    url, srv, db_path = _server()
    try:
        res, pend = _push_as(url, "nurse1", "pw_n", "financials", "financials:3", _pay("ghost", "nurse1"))
        assert res[0] is False, res
        assert len(pend) == 1
        res, pend = _push_as(url, "nurse1", "pw_n", "financials", "financials:3", _pay("nurse1", "nurse1"))
        assert res[0] is False, res  # nurse cannot credit herself as doctor
        assert len(pend) == 1
    finally:
        _stop(srv, db_path)


def test_nurse_push_expense_refused():
    """Nurse pushing an expense is refused (403) and stays queued."""
    url, srv, db_path = _server()
    try:
        res, pend = _push_as(url, "nurse1", "pw_n", "expenses", "expenses:1",
                             {"date": "2026-11-07", "category": "Rent", "description": "rent",
                              "amount": 50000, "center_id": "main", "updated_at": NOW})
        assert res[0] is False, res
        assert len(pend) == 1
        c, counts = _pull_as(url, "fady", "1234")
        assert counts["financials"] == 0, counts
        c.close()
    finally:
        _stop(srv, db_path)


def test_doctor_push_for_other_doctor():
    """A doctor recording a payment for another treating doctor is
    allowed too (entered_by == sender, doctor is a real doctor)."""
    url, srv, db_path = _server()
    try:
        res, pend = _push_as(url, "doc_a", "pw_a", "financials", "financials:4", _pay("doc_b", "doc_a", 9000))
        assert res[0] is True and res[1] == 1, res
        assert pend == []
    finally:
        _stop(srv, db_path)
