"""Round 39: delta (incremental) sync — main flow. Before R39
every pull transferred the full dataset (the server filtered by a
`since` timestamp no client ever sent). R39 adds server-assigned
per-table `seq` values (arrival order, immune to client clock
skew), client watermarks per (server, center, table), and a
server_id handshake forcing a full pull against a replaced DB.
Covered against the REAL server (in-process, temp DB): fresh
client full pull + stored watermarks; exactly-3-changes delta
(patient edit, soft-delete, R38 standalone payment); zero-change
delta; a late row with an ANCIENT updated_at still arriving; the
legacy protocol unchanged (no watermarks without server_id/seq_*,
timestamp filter intact, client stores nothing from it)."""
import gc, os, sqlite3, sys, tempfile, threading
from pathlib import Path
from urllib.parse import urlencode
from src.models.sync import (ensure_tables as sync_tables, queue_change,
                             SyncClient)
from src.models.sync_state import (absorb_response, load_state,
                                   request_params)

T1 = "2026-11-21T10:00:00"
T2 = "2026-11-21T11:00:00"


def _mem():
    conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row
    return conn


def _clinic_tables(conn):
    conn.execute("CREATE TABLE patients(file_number INTEGER PRIMARY KEY,"
                 " full_name TEXT, deleted INT, updated_at TEXT)")
    conn.execute("CREATE TABLE complaints(id INTEGER PRIMARY KEY,"
                 " patient_file INT, visit_date TEXT, complaint TEXT,"
                 " symptoms TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE financials(id INTEGER PRIMARY KEY,"
                 " patient_file INT, tooth_number TEXT, total_cost REAL,"
                 " paid_amount REAL, remaining REAL, visit_date TEXT,"
                 " currency TEXT, total_syp REAL, paid_syp REAL,"
                 " remaining_syp REAL, doctor TEXT, entered_by TEXT,"
                 " row_kind TEXT, note TEXT, center_id TEXT,"
                 " updated_at TEXT)")
    conn.commit()


def _gc_guard_on():
    # Gate hazard (found R39 via watchdog stack): after ~100 GUI
    # files, a cyclic-GC pass on a SERVER thread can finalize a
    # stale PIL PhotoImage — its __del__ calls into Tk from the
    # wrong thread with no mainloop running and deadlocks the
    # request. Collect on the main thread; pause GC while serving.
    gc.collect(); gc.disable()


def _server():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "server"))
    import sync_server
    from http.server import ThreadingHTTPServer
    _gc_guard_on()
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    sync_server.DB_PATH = Path(tmp.name); sync_server.init_db(Path(tmp.name))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), sync_server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}", srv, tmp.name


def _stop(srv, db_path):
    srv.shutdown(); srv.server_close(); os.unlink(db_path); gc.enable()


def _client(url, conn):
    cl = SyncClient(url)
    assert cl.login("fady", "1234")[0]
    return cl


def _pay(fid, amount, ts, **kw):
    p = {"patient_file": fid, "tooth_number": "", "total_cost": amount,
         "paid_amount": amount, "remaining": 0, "visit_date": "2026-11-21",
         "currency": "SYP", "total_syp": amount, "paid_syp": amount,
         "remaining_syp": 0, "doctor": "fady", "entered_by": "fady",
         "center_id": "main", "updated_at": ts}
    p.update(kw); return p


def _raw_pull(cl, conn, url):
    params = {"since": "", "center_id": "main"}
    params.update(request_params(conn, url, "main"))
    st, res = cl._req("GET", "/sync/pull?" + urlencode(params))
    assert st == 200, res
    return res


def _seed_a(url):
    """Client A pushes the baseline dataset; returns its client."""
    a = _mem(); _clinic_tables(a); sync_tables(a)
    queue_change(a, "patients", "9001", {"patient_file": "9001",
        "full_name": "Delta One", "deleted": 0, "updated_at": T1})
    queue_change(a, "patients", "9002", {"patient_file": "9002",
        "full_name": "Delta Two", "deleted": 0, "updated_at": T1})
    queue_change(a, "complaints", "complaints:1", {"patient_file": "9001",
        "complaint": "ache", "symptoms": "pain",
        "visit_date": "2026-11-21", "updated_at": T1})
    queue_change(a, "financials", "financials:1", _pay(9001, 100, T1))
    cl = _client(url, a)
    ok, applied = cl.push(a, "main")
    assert ok and applied == 4, (ok, applied)
    return a, cl


def test_delta_full_then_incremental():
    url, srv, db_path = _server()
    try:
        a, cla = _seed_a(url)
        b = _mem(); _clinic_tables(b); sync_tables(b)
        clb = _client(url, b)
        ok, counts = clb.pull(b, "main", "")
        assert ok and counts["patients"] == 2 and counts["visits"] == 1 and counts["financials"] == 1, counts
        sid, marks = load_state(b, url, "main")
        assert sid and marks["patients"] == 2 and marks["visits"] == 1 and marks["financials"] == 1, (sid, marks)
        # Exactly 3 changes on A: edit, soft-delete, standalone payment.
        queue_change(a, "patients", "9001", {"patient_file": "9001", "full_name": "Delta One Edited", "deleted": 0, "updated_at": T2})
        queue_change(a, "patients", "9002", {"patient_file": "9002", "full_name": "Delta Two", "deleted": 1, "updated_at": T2})
        queue_change(a, "financials", "financials:2",
                     _pay(9001, 777, T2, row_kind="payment",
                          note="advance"))
        ok, applied = cla.push(a, "main")
        assert ok and applied == 3, (ok, applied)
        res = _raw_pull(clb, b, url)
        got_p = sorted(str(i["patient_file"]) for i in res["patients"])
        assert got_p == ["9001", "9002"], got_p  # exactly the changed
        assert res["visits"] == [] and res["employees"] == [] and res["referrals"] == []
        assert len(res["financials"]) == 1 and res["financials"][0]["row_kind"] == "payment", res
        ok, counts = clb.pull(b, "main", "")
        assert ok and counts["patients"] == 2 and counts["financials"] == 1, counts
        row = b.execute("SELECT full_name FROM patients"
                        " WHERE file_number=9001").fetchone()
        assert row["full_name"] == "Delta One Edited"
        row = b.execute("SELECT deleted FROM patients"
                        " WHERE file_number=9002").fetchone()
        assert row["deleted"] == 1  # soft delete propagated as update
        row = b.execute("SELECT row_kind, paid_amount FROM financials"
                        " WHERE id=2").fetchone()
        assert tuple(row) == ("payment", 777.0)
        # No-change pull: zero rows on the wire, zero applied.
        res = _raw_pull(clb, b, url)
        assert all(res[k] == [] for k in
                   ("patients", "visits", "financials", "employees", "referrals")), res
        ok, counts = clb.pull(b, "main", "")
        assert ok and all(v == 0 for v in counts.values()), counts
        a.close(); b.close()
    finally:
        _stop(srv, db_path)


def test_delta_late_row_with_old_timestamp_still_arrives():
    url, srv, db_path = _server()
    try:
        a, cla = _seed_a(url)
        b = _mem(); _clinic_tables(b); sync_tables(b)
        clb = _client(url, b)
        ok, _ = clb.pull(b, "main", "")
        assert ok
        # Pushed AFTER B's full pull but stamped 2020 (skewed clock):
        # a timestamp watermark would never deliver this row.
        queue_change(a, "patients", "9003", {"patient_file": "9003", "full_name": "Late Old", "deleted": 0, "updated_at": "2020-01-01T00:00:00"})
        ok, applied = cla.push(a, "main")
        assert ok and applied == 1, (ok, applied)
        res = _raw_pull(clb, b, url)
        assert [str(i["patient_file"]) for i in res["patients"]] == ["9003"]
        ok, counts = clb.pull(b, "main", "")
        assert ok and counts["patients"] == 1, counts
        assert b.execute("SELECT COUNT(*) FROM patients WHERE file_number=9003").fetchone()[0] == 1
        a.close(); b.close()
    finally:
        _stop(srv, db_path)


def test_legacy_pull_protocol_unchanged():
    url, srv, db_path = _server()
    try:
        _a, _cla = _seed_a(url)
        cl = _client(url, _mem())
        st, res = cl._req("GET", "/sync/pull?" + urlencode(
            {"since": "", "center_id": "main"}))
        assert st == 200 and "watermarks" not in res and "server_id" not in res, res.keys()
        assert len(res["patients"]) == 2  # legacy full pull
        st, res = cl._req("GET", "/sync/pull?" + urlencode(
            {"since": "2027-01-01T00:00:00", "center_id": "main"}))
        assert st == 200 and res["patients"] == []  # ts filter intact
        # Client stores nothing from a legacy-shaped response.
        c = _mem(); sync_tables(c)
        assert absorb_response(c, url, "main", {"patients": []}) is False
        sid, marks = load_state(c, url, "main")
        assert sid == "" and all(v == 0 for v in marks.values())
        _a.close(); c.close()
    finally:
        _stop(srv, db_path)
