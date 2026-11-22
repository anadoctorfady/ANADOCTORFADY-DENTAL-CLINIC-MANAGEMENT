"""Round 39: delta sync — server identity + role-filter watermarks.

(1) Server replaced: a client whose stored watermarks belong to a
DIFFERENT server database (server_id mismatch) must get a full
pull, never a starved delta. Simulated by swapping the server DB
under the same URL/port.
(2) Financials watermark semantics for a doctor: the watermark is
the max seq SERVED to that user (after the finance role filter),
so other doctors' payments never advance it, a pull with nothing
new for the doctor returns zero financial rows, and the doctor's
next own payment still arrives.
(3) Regression (state found by the R39 load bench): sync rows
loaded into the server DB while its seq counters sat at 0 (bulk
load / pre-R39 restore) must not leave the counter below the
table's max seq — new writes would get seqs under every client's
watermark and delta pulls would starve."""
import gc, os, sqlite3, sys, tempfile, threading
from pathlib import Path
from urllib.parse import urlencode
from src.models.sync import (ensure_tables as sync_tables, queue_change,
                             SyncClient)
from src.models.sync_state import load_state, request_params

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


def _start_server(db_name, users=(), port=0):
    # GC guard: see test_r39_delta_sync._gc_guard_on (a server
    # thread must never finalize a stale PIL PhotoImage).
    gc.collect(); gc.disable()
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "server"))
    import sync_server
    from auth import hash_password
    from http.server import ThreadingHTTPServer
    sync_server.DB_PATH = Path(db_name); sync_server.init_db(Path(db_name))
    if users:
        conn = sqlite3.connect(db_name)
        for u, pw, role in users:
            h, s = hash_password(pw)
            conn.execute("INSERT INTO users(username,password_hash,salt,role,center_id,created_at) VALUES(?,?,?,?,?,datetime('now'))", (u, h, s, role, "main"))
        conn.commit(); conn.close()
    srv = ThreadingHTTPServer(("127.0.0.1", port), sync_server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _client(url, username="fady", password="1234"):
    cl = SyncClient(url)
    assert cl.login(username, password)[0]
    return cl


def _pay(fid, amount, doctor, ts):
    return {"patient_file": fid, "tooth_number": "", "total_cost": amount, "paid_amount": amount, "remaining": 0,
            "visit_date": "2026-11-21", "currency": "SYP", "total_syp": amount, "paid_syp": amount, "remaining_syp": 0,
            "doctor": doctor, "entered_by": "fady", "center_id": "main", "updated_at": ts}


def test_server_replaced_triggers_full_pull():
    tmp1 = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp1.close(); tmp2 = tempfile.NamedTemporaryFile(suffix=".db",
                                                      delete=False)
    tmp2.close()
    srv1 = _start_server(tmp1.name)
    port = srv1.server_address[1]
    url = f"http://127.0.0.1:{port}"
    try:
        a = _mem(); _clinic_tables(a); sync_tables(a)
        queue_change(a, "patients", "9101", {"patient_file": "9101", "full_name": "Server One", "deleted": 0, "updated_at": T1})
        assert _client(url).push(a, "main")[0]
        b = _mem(); _clinic_tables(b); sync_tables(b)
        clb = _client(url)
        ok, counts = clb.pull(b, "main", "")
        assert ok and counts["patients"] == 1, counts
        sid1, marks1 = load_state(b, url, "main")
        assert sid1 and marks1["patients"] == 1
        srv1.shutdown(); srv1.server_close()
        # New server DB (new server_id) under the SAME url/port.
        srv2 = _start_server(tmp2.name, port=port)
        try:
            a2 = _mem(); _clinic_tables(a2); sync_tables(a2)
            queue_change(a2, "patients", "9202", {"patient_file": "9202", "full_name": "Server Two", "deleted": 0, "updated_at": T1})
            cl2 = SyncClient(url); assert cl2.login("fady", "1234")[0]
            assert cl2.push(a2, "main")[0]
            ok, counts = clb.pull(b, "main", "")
            assert ok and counts["patients"] == 1, counts
            names = {r[0] for r in b.execute(
                "SELECT full_name FROM patients").fetchall()}
            assert names == {"Server One", "Server Two"}, names
            sid2, marks2 = load_state(b, url, "main")
            assert sid2 and sid2 != sid1 and marks2["patients"] == 1
            a2.close()
        finally:
            srv2.shutdown(); srv2.server_close(); gc.enable()
        a.close(); b.close()
    finally:
        os.unlink(tmp1.name); os.unlink(tmp2.name)


def test_doctor_financials_watermark_served_only():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    srv = _start_server(tmp.name, users=(("doc_a", "pw_a", "doctor"),
                                         ("doc_b", "pw_b", "doctor")))
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        a = _mem(); _clinic_tables(a); sync_tables(a)
        cla = _client(url)
        queue_change(a, "financials", "financials:1", _pay(9001, 100, "doc_a", T1))
        queue_change(a, "financials", "financials:2", _pay(9002, 200, "doc_b", T1))
        assert cla.push(a, "main") == (True, 2)
        d = _mem(); _clinic_tables(d); sync_tables(d)
        cld = _client(url, "doc_a", "pw_a")
        ok, counts = cld.pull(d, "main", "")
        assert ok and counts["financials"] == 1, counts
        _sid, marks = load_state(d, url, "main")
        assert marks["financials"] == 1, marks  # doc_b's seq=2 NOT served
        queue_change(a, "financials", "financials:3",
                     _pay(9003, 300, "doc_b", T2))
        assert cla.push(a, "main") == (True, 1)
        params = {"since": "", "center_id": "main"}
        params.update(request_params(d, url, "main"))
        st, res = cld._req("GET", "/sync/pull?" + urlencode(params))
        assert st == 200 and res["financials"] == [], res["financials"]
        ok, counts = cld.pull(d, "main", "")
        assert ok and counts["financials"] == 0, counts
        queue_change(a, "financials", "financials:4",
                     _pay(9004, 400, "doc_a", T2))
        assert cla.push(a, "main") == (True, 1)
        ok, counts = cld.pull(d, "main", "")
        assert ok and counts["financials"] == 1, counts
        ids = [r[0] for r in d.execute("SELECT id FROM financials ORDER BY id").fetchall()]
        assert ids == [1, 4], ids  # only doc_a's payments, ever
        _sid, marks = load_state(d, url, "main")
        assert marks["financials"] == 4, marks
        a.close(); d.close()
    finally:
        srv.shutdown(); srv.server_close(); os.unlink(tmp.name); gc.enable()


def test_counter_never_below_max_seq_after_bulk_load():
    """Regression for the load-bench state: rows bulk-loaded into
    patients_sync (no seq) while the counters sat at 0. After a
    server restart (init_db -> ensure_seq) the counter must sit at
    the max seq, so the next push gets a seq ABOVE it."""
    import json as _json
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    srv = _start_server(tmp.name)
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        raw = sqlite3.connect(tmp.name)
        for fid in (7001, 7002, 7003):
            raw.execute("INSERT INTO patients_sync(patient_file, center_id, data_json, updated_at, updated_by) VALUES(?,?,?,?,?)",
                        (str(fid), "main", _json.dumps(
                            {"patient_file": str(fid),
                             "full_name": f"Bulk {fid}", "deleted": 0}),
                         T1, "fady"))
        raw.commit(); raw.close()
        root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(root / "server"))
        import sync_server
        sync_server.init_db(Path(tmp.name))  # restart: ensure_seq runs
        b = _mem(); _clinic_tables(b); sync_tables(b)
        clb = _client(url)
        ok, counts = clb.pull(b, "main", "")
        assert ok and counts["patients"] == 3, counts
        a = _mem(); _clinic_tables(a); sync_tables(a)
        queue_change(a, "patients", "7004", {"patient_file": "7004", "full_name": "After Bulk", "deleted": 0, "updated_at": T2})
        assert _client(url).push(a, "main") == (True, 1)
        ok, counts = clb.pull(b, "main", "")
        assert ok and counts["patients"] == 1, counts  # not starved
        assert b.execute("SELECT COUNT(*) FROM patients WHERE file_number=7004").fetchone()[0] == 1
        a.close(); b.close()
    finally:
        srv.shutdown(); srv.server_close(); os.unlink(tmp.name); gc.enable()
