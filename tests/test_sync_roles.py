"""Phase 4: roles, attendance, sync client vs the real server, payment roles."""
import os, sqlite3, sys, tempfile, threading
from datetime import datetime
from pathlib import Path
from src.models import permissions as P
from src.models.attendance import (ensure_tables as att_tables,
    record_attendance, list_attendance, unsynced_attendance, mark_synced)
from src.models.sync import (ensure_tables as sync_tables, queue_change,
    pending_changes, SyncClient, sync_now)
from src.models.finance import update_payment_checked
def _mem():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn
def _clinic_tables(conn):
    conn.execute("CREATE TABLE patients(file_number INTEGER PRIMARY KEY,"
                 " full_name TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE complaints(id INTEGER PRIMARY KEY,"
                 " patient_file INT, visit_date TEXT, complaint TEXT,"
                 " symptoms TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE financials(id INTEGER PRIMARY KEY,"
                 " patient_file INT, total_cost REAL, paid_amount REAL,"
                 " remaining REAL, total_syp REAL, paid_syp REAL, remaining_syp REAL)")
    conn.commit()
def test_role_matrix():
    assert P.can_edit_payments("admin") and not P.can_edit_payments("doctor")
    assert not P.can_edit_payments("nurse")
    assert P.can_edit_clinical("admin") and P.can_edit_clinical("doctor")
    assert not P.can_edit_clinical("nurse")
    assert P.can_view_patients("admin") and P.can_view_patients("doctor")
    assert P.can_view_patients("nurse")
    assert P.can_manage_users("admin") and not P.can_manage_users("doctor")
    assert not P.can_manage_users("nurse")
    assert P.can_delete_records("admin") and not P.can_delete_records("doctor")
    assert P.can_register_attendance("nurse") and P.can_register_attendance("doctor")
    assert P.can_view_attendance("admin") and not P.can_view_attendance("doctor")
    assert P.can_view_attendance("nurse") is False
    assert P.ROLE_LABELS["admin"] == ("Admin", "مدير")
    assert P.role_label("nurse", "ar") == "ممرضة / ممرض"
def test_attendance_roundtrip():
    conn = _mem(); att_tables(conn)
    today = datetime.now().strftime("%Y-%m-%d")
    i1 = record_attendance(conn, "nurse1", "in", "dev-A")
    i2 = record_attendance(conn, "nurse1", "out", "dev-A")
    assert i1 and i2 and i1 != i2
    rows = list_attendance(conn)
    assert len(rows) == 2 and rows[0]["action"] == "out"  # newest first
    assert [r["username"] for r in list_attendance(conn, username="nurse1")] == ["nurse1", "nurse1"]
    assert len(list_attendance(conn, date=today)) == 2
    assert list_attendance(conn, date="2000-01-01") == []
    assert list_attendance(conn, username="nobody") == []
    # Exact timestamps preserved: a manually inserted row round-trips verbatim.
    conn.execute("INSERT INTO attendance_log(username,action,ts,device_id,synced)"
                 " VALUES(?,?,?,?,0)", ("doc1", "in", "2026-11-07T08:30:00", "dev-B"))
    conn.commit()
    got = [r for r in list_attendance(conn, username="doc1") if r["ts"] == "2026-11-07T08:30:00"]
    assert len(got) == 1 and got[0]["device_id"] == "dev-B"
    assert len(unsynced_attendance(conn)) == 3
    assert mark_synced(conn, [i1]) == 1
    assert len(unsynced_attendance(conn)) == 2
    try:
        record_attendance(conn, "x", "maybe", "")
        raise AssertionError("bad action should raise")
    except ValueError:
        pass
    conn.close()
def test_sync_against_real_server():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "server"))
    import sync_server
    from http.server import ThreadingHTTPServer
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close(); db_path = tmp.name
    sync_server.DB_PATH = Path(db_path)
    sync_server.init_db(Path(db_path))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), sync_server.Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
    try:
        url = f"http://127.0.0.1:{port}"
        now = datetime.now().isoformat(timespec="seconds")
        c1 = _mem(); _clinic_tables(c1); sync_tables(c1)
        queue_change(c1, "patients", "9001", {"patient_file": "9001",
            "full_name": "Sync Test Patient", "updated_at": now})
        queue_change(c1, "complaints", "complaints:1", {"patient_file": "9001",
            "complaint": "toothache", "symptoms": "pain",
            "visit_date": "2026-11-07", "updated_at": now})
        cl1 = SyncClient(url)
        ok, info = cl1.login("fady", "1234")
        assert ok, info
        assert info["role"] == "admin" and info["center_id"] == "main"
        ok, applied = cl1.push(c1, "main")
        assert ok and applied >= 2, (ok, applied)
        assert pending_changes(c1) == []  # queue marked synced
        # Second device / DB pulls the records.
        c2 = _mem(); _clinic_tables(c2); sync_tables(c2)
        cl2 = SyncClient(url)
        ok, _ = cl2.login("fady", "1234")
        assert ok
        ok, counts = cl2.pull(c2, "main", "")
        assert ok and counts["patients"] >= 1 and counts["visits"] >= 1, counts
        row = c2.execute("SELECT * FROM patients WHERE file_number=9001").fetchone()
        assert row and row["full_name"] == "Sync Test Patient"
        v = c2.execute("SELECT * FROM complaints WHERE id=1").fetchone()
        assert v and v["complaint"] == "toothache" and v["patient_file"] == 9001
        # Pull again: last-write-wins, no duplicates.
        ok, counts = cl2.pull(c2, "main", "")
        assert ok and counts["patients"] == 0 and counts["visits"] == 0, counts
        assert c2.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 1
        # Wrong password fails gracefully (no raise).
        ok, err = SyncClient(url).login("fady", "wrong")
        assert not ok and err
        # Offline: bad URL / stopped server -> offline dict, no raise.
        assert SyncClient("http://127.0.0.1:1").login("fady", "1234")[0] is False
        assert sync_now(c2, "", "fady", "1234", "main")["offline"] is True
        assert sync_now(c2, "http://127.0.0.1:1", "fady", "1234", "main")["offline"] is True
        c1.close(); c2.close()
    finally:
        srv.shutdown(); srv.server_close()
        os.unlink(db_path)
def test_payment_role():
    conn = _mem(); _clinic_tables(conn)
    conn.execute("INSERT INTO financials(id,patient_file,total_cost,paid_amount,"
                 "remaining) VALUES(1,9001,100,40,60)")
    conn.commit()
    assert update_payment_checked(conn, 1, total=120, paid=50, role="doctor") is False
    assert update_payment_checked(conn, 1, total=120, paid=50, role="nurse") is False
    assert update_payment_checked(conn, 1, total=120, paid=50, role=None) is False
    row = conn.execute("SELECT total_cost, paid_amount FROM financials WHERE id=1").fetchone()
    assert row["total_cost"] == 100 and row["paid_amount"] == 40  # unchanged
    assert update_payment_checked(conn, 1, total=120, paid=50, role="admin") is True
    row = conn.execute("SELECT total_cost, paid_amount, remaining FROM financials WHERE id=1").fetchone()
    assert (row["total_cost"], row["paid_amount"], row["remaining"]) == (120, 50, 70)
    assert update_payment_checked(conn, 999, total=1, role="admin") is False
    conn.close()
