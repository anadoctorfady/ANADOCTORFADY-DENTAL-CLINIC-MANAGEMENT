"""Round 23 (item 8): referral SYNC. Before the fix referrals were
in NO sync layer: add_referral queued nothing, SyncClient.push had
no "referrals" key, the server had no referrals table / handler,
and pull never returned them -- a nurse's referral stayed on her
device and the doctor on another device never saw it.
Covered here, module-level + in-process server helpers (no real
network): (1) add_referral queues the row and split_referral_queue
builds the push payload (patient_file / author / center_id);
(2) queue_all_referrals backfills pre-fix rows; (3) the server
helpers push_referrals / pull_referrals accept a NURSE push,
apply last-write-wins, and return the referral to a doctor (and
to a nurse) scoped by center; (4) apply_referral_pull inserts it
into a fresh local DB idempotently; (5) a loopback end-to-end run
through the real server + SyncClient: nurse pushes, doctor pulls
and the referral lands in his referrals table / history data."""
import os, sqlite3, sys, tempfile, threading
from pathlib import Path

from src.models.database import get_connection, init_db
from src.models.referrals import (add_referral, apply_referral_pull,
                                  ensure_tables as ref_tables,
                                  queue_all_referrals,
                                  queue_referral, split_referral_queue)
from src.models.sync import (ensure_tables as sync_tables,
                             pending_changes, SyncClient)
from tests.test_r18_search_phone import _cleanup, _seed

NOW = "2026-11-17T08:00:00"
OLD = "2026-11-17T07:00:00"
NURSE = {"username": "nurse1", "role": "nurse", "center_id": "main"}
DOCTOR = {"username": "doc_a", "role": "doctor", "center_id": "main"}


def _mem():
    conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row
    return conn


def _item(rid=7, fid=9001, updated=NOW, center="main"):
    p = {"patient_id": fid, "patient_file": str(fid),
         "from_user": "nurse1", "author": "nurse1",
         "to_doctor": "doc_a", "note": "implant consult",
         "created_at": NOW, "updated_at": updated}
    return {"record_id": f"referrals:{rid}", "patient_file": str(fid),
            "center_id": center, "updated_at": updated, "data_json": p}


def _cleanup_refs(*fids):
    conn = get_connection(); cur = conn.cursor()
    for fid in fids:
        for (rid,) in cur.execute("SELECT id FROM referrals WHERE patient_id=?", (fid,)):
            cur.execute("DELETE FROM sync_queue WHERE table_name='referrals' AND record_id=?", (f"referrals:{rid}",))
        cur.execute("DELETE FROM referrals WHERE patient_id=?", (fid,))
    conn.commit(); conn.close(); _cleanup(*fids)


def _server_mod():
    root = Path(__file__).resolve().parent.parent
    if str(root / "server") not in sys.path:
        sys.path.insert(0, str(root / "server"))
    import finance_sync as fs
    return fs


def test_add_referral_queues_and_payload():
    init_db()
    fid = _seed("R23Sy", "R23Dad", "R23Gpa", "R23Fam")
    try:
        rid = add_referral(fid, "nurse1", "doc_a", "queued note")
        assert rid
        conn = get_connection()
        pend = pending_changes(conn); conn.close()
        mine = [p for p in pend if p["table_name"] == "referrals"
                and p["record_id"] == f"referrals:{rid}"]
        assert len(mine) == 1, "referral was not queued for sync"
        items = split_referral_queue(pend, "main")
        # Suite-isolation fix (coordinator, full-gate run 1): the
        # shared gate DB means other suites' referrals are pending
        # too -- scope the count to THIS test's row.
        mine_items = [i for i in items
                      if i["record_id"] == f"referrals:{rid}"]
        assert len(mine_items) == 1, items
        it = mine_items[0]
        assert it["record_id"] == f"referrals:{rid}"
        assert it["patient_file"] == str(fid)
        assert it["center_id"] == "main"
        d = it["data_json"]
        assert d["from_user"] == "nurse1" and d["author"] == "nurse1"
        assert d["to_doctor"] == "doc_a" and d["note"] == "queued note"
        assert d["patient_file"] == str(fid) and d["created_at"]
        assert it["updated_at"] == d["updated_at"] == d["created_at"]
    finally:
        _cleanup_refs(fid)


def test_backfill_queues_prefix_rows_once():
    init_db()
    fid = _seed("R23Back", "R23Dad", "R23Gpa", "R23Fam")
    try:
        conn = get_connection()  # direct insert = pre-R23 row, no queue
        cur = conn.cursor()
        cur.execute("INSERT INTO referrals(patient_id,from_user,"
                    "to_doctor,note,created_at) VALUES(?,?,?,?,?)",
                    (fid, "nurse1", "doc_a", "old row", NOW))
        rid = cur.lastrowid; conn.commit()
        assert queue_all_referrals(conn) >= 1
        pend = pending_changes(conn)
        items = split_referral_queue(pend, "main")
        assert any(i["record_id"] == f"referrals:{rid}"
                   and i["data_json"]["note"] == "old row"
                   for i in items), items
        assert queue_all_referrals(conn) == 0  # never re-queued
        conn.close()
    finally:
        _cleanup_refs(fid)


def test_server_helpers_nurse_push_doctor_pull_lww():
    fs = _server_mod()
    conn = _mem(); fs.init_referral_tables(conn)
    st, applied = fs.push_referrals(conn, [_item()], NURSE)
    assert (st, applied) == (200, 1)  # a nurse push is ACCEPTED
    st, applied = fs.push_referrals(conn, [_item(updated=OLD)], NURSE)
    assert (st, applied) == (200, 0)  # older copy loses (LWW)
    st, applied = fs.push_referrals(conn, [{"record_id": "referrals:9"}], NURSE)
    assert (st, applied) == (200, 0)  # no patient_file: skipped
    got = fs.pull_referrals(conn, DOCTOR, "", "main")
    assert len(got) == 1, got
    g = got[0]
    assert g["record_id"] == "referrals:7"
    assert g["patient_file"] == "9001" and g["center_id"] == "main"
    assert g["from_user"] == "nurse1" and g["author"] == "nurse1"
    assert g["to_doctor"] == "doc_a" and g["note"] == "implant consult"
    assert g["updated_by"] == "nurse1"
    assert len(fs.pull_referrals(conn, NURSE, "", "main")) == 1
    assert fs.pull_referrals(conn, DOCTOR, "", "branch2") == []
    assert fs.pull_referrals(conn, DOCTOR, "2027-01-01", "main") == []
    conn.close()


def test_client_apply_pull_idempotent():
    conn = _mem(); ref_tables(conn); sync_tables(conn)
    res = {"referrals": [_item()]}
    assert apply_referral_pull(conn, res) == 1
    row = conn.execute("SELECT * FROM referrals WHERE id=7").fetchone()
    assert row["patient_id"] == 9001 and row["from_user"] == "nurse1"
    assert row["to_doctor"] == "doc_a"
    assert row["note"] == "implant consult"
    assert row["created_at"] == NOW
    assert apply_referral_pull(conn, res) == 0  # no duplicate
    assert conn.execute("SELECT COUNT(*) FROM referrals").fetchone()[0] == 1
    assert apply_referral_pull(conn, {"referrals": [{"record_id": "x"}]}) == 0
    conn.close()


def test_loopback_nurse_push_doctor_pull():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "server"))
    import sync_server
    from auth import hash_password
    from http.server import ThreadingHTTPServer
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    sync_server.DB_PATH = Path(tmp.name); sync_server.init_db(Path(tmp.name))
    sc = sqlite3.connect(tmp.name)
    for u, pw, role in (("nurse1", "pw_n", "nurse"), ("doc_a", "pw_a", "doctor")):
        h, s = hash_password(pw)
        sc.execute("INSERT INTO users(username,password_hash,salt,role,center_id,created_at) VALUES(?,?,?,?,?,datetime('now'))", (u, h, s, role, "main"))
    sc.commit(); sc.close()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), sync_server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        c1 = _mem(); ref_tables(c1); sync_tables(c1)
        c1.execute("INSERT INTO referrals(id,patient_id,from_user,"
                   "to_doctor,note,created_at) VALUES(41,9001,'nurse1',"
                   "'doc_a','loopback referral',?)", (NOW,))
        c1.commit()
        assert queue_referral(c1, 41)
        cl = SyncClient(url); assert cl.login("nurse1", "pw_n")[0]
        ok, applied = cl.push(c1, "main")
        assert ok and applied >= 1, (ok, applied)
        assert pending_changes(c1) == []  # queue marked synced
        c1.close()
        c2 = _mem(); ref_tables(c2); sync_tables(c2)
        cl2 = SyncClient(url); assert cl2.login("doc_a", "pw_a")[0]
        ok, counts = cl2.pull(c2, "main", "")
        assert ok and counts["referrals"] == 1, counts
        row = c2.execute("SELECT * FROM referrals WHERE id=41").fetchone()
        assert row["patient_id"] == 9001 and row["from_user"] == "nurse1"
        assert row["to_doctor"] == "doc_a"
        assert row["note"] == "loopback referral"
        ok, counts = cl2.pull(c2, "main", "")
        assert ok and counts["referrals"] == 0, counts  # idempotent
        assert c2.execute("SELECT COUNT(*) FROM referrals").fetchone()[0] == 1
        c2.close()
    finally:
        srv.shutdown(); srv.server_close(); os.unlink(tmp.name)
