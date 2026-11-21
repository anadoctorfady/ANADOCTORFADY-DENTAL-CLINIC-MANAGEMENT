"""Referrals (round 19, item 11): a patient referred to another
doctor -- an internal user (role doctor/admin) or an external
doctor typed by name. One row per referral: who referred
(from_user = the logged-in username), to whom (to_doctor = the
username or the external name, stored as ONE plain string so the
history display needs no join), the note (template / free text /
both) and created_at (ISO timestamp, defaults to now).

Schema follows the late-schema pattern of notes.py / salaries.py:
ensure_tables(conn) is idempotent (CREATE TABLE IF NOT EXISTS),
is wired into init_db() in database.py next to the other
late-schema ensures, and every public function self-ensures on
its own connection, so an existing DB gains the table on first
use even before any migration runs. <200 lines.

Round 23 (item 8): referrals now SYNC. A nurse's referral was
saved + shown locally but never left her device -- add_referral
queued nothing, the push payload had no referrals key, and the
server had no referrals table. Referrals are immutable (never
edited), so created_at doubles as the last-write-wins
updated_at; center_id rides in the sync payload (set at push
time, like visits). add_referral() queues the row;
queue_all_referrals() backfills rows created before round 23.
"""
import json
import sqlite3
from datetime import datetime

from src.models.database import get_connection


def _now():
    return datetime.now().isoformat(timespec="seconds")


def ensure_tables(conn):
    conn.row_factory = sqlite3.Row
    conn.cursor().execute("""CREATE TABLE IF NOT EXISTS referrals(
        id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INT,
        from_user TEXT, to_doctor TEXT, note TEXT, created_at TEXT)""")
    conn.commit()


def add_referral(patient_id, from_user, to_doctor, note):
    """Insert a referral for `patient_id`. Returns the new id, or
    None when patient_id / to_doctor is missing (a referral must
    name a doctor; the note may be empty at the model level --
    the dialog requires a doctor and lets the note be a template,
    free text, or both). created_at is stamped now."""
    to_doctor = (to_doctor or "").strip()
    if not patient_id or not to_doctor:
        return None
    conn = get_connection()
    try:
        ensure_tables(conn)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO referrals(patient_id, from_user, to_doctor,"
            " note, created_at) VALUES(?,?,?,?,?)",
            (patient_id, (from_user or "").strip(), to_doctor,
             (note or "").strip(), _now()))
        rid = cur.lastrowid
        try:
            queue_referral(conn, rid)  # R23: sync queue (see header)
        except Exception:
            pass  # referral saved; queueing retries via backfill
        conn.commit()
        return rid
    finally:
        conn.close()


def queue_referral(conn, referral_id):
    """Queue one referral row for sync push (payload: patient_file,
    author, to_doctor, note, created_at as updated_at)."""
    ensure_tables(conn)
    row = conn.execute("SELECT * FROM referrals WHERE id=?",
                       (referral_id,)).fetchone()
    if not row:
        return False
    r = dict(row)
    ts = r.get("created_at") or _now()
    from src.models.sync import queue_change
    queue_change(conn, "referrals", f"referrals:{r['id']}", {
        "patient_id": r.get("patient_id"),
        "patient_file": str(r.get("patient_id") or ""),
        "from_user": r.get("from_user") or "",
        "author": r.get("from_user") or "",
        "to_doctor": r.get("to_doctor") or "",
        "note": r.get("note") or "",
        "created_at": ts, "updated_at": ts})
    return True


def queue_all_referrals(conn):
    """Backfill: queue every referral that has NO sync_queue entry
    at all (rows created before round 23). Already-queued rows
    (synced or not) are left alone. Returns how many were queued."""
    from src.models.sync import ensure_tables as _sync_tables
    ensure_tables(conn); _sync_tables(conn)
    done = {r[0] for r in conn.execute(
        "SELECT record_id FROM sync_queue WHERE table_name='referrals'")}
    n = 0
    for r in conn.execute("SELECT id FROM referrals").fetchall():
        if f"referrals:{r[0]}" not in done and queue_referral(conn, r[0]):
            n += 1
    return n


def split_referral_queue(pend, center_id):
    """Push-payload items from pending sync_queue rows (the
    referrals analogue of finance_sync.split_financial_queue)."""
    out = []
    for row in pend:
        if row["table_name"] != "referrals":
            continue
        try:
            p = json.loads(row["payload_json"])
        except Exception:
            continue
        p.setdefault("center_id", center_id)
        p.setdefault("updated_at", row["updated_at"])
        out.append({"record_id": str(row["record_id"]),
                    "patient_file": str(p.get("patient_file")
                                         or p.get("patient_id") or ""),
                    "center_id": p.get("center_id") or center_id,
                    "updated_at": row["updated_at"], "data_json": p})
    return out


def apply_referral_pull(conn, res):
    """Apply pulled referrals into the local referrals table;
    returns the count inserted. Referrals are immutable, so a
    referral id that already exists locally is skipped (pulls
    are idempotent, no duplicates)."""
    n = 0
    for item in res.get("referrals") or []:
        try:
            n += _apply_pulled(conn, item)
        except Exception:
            continue  # skip one bad record, never crash pull
    return n


def _apply_pulled(conn, item):
    rid = str(item.get("record_id") or "")
    if not rid.split(":")[-1].isdigit():
        return 0
    local_id = int(rid.split(":")[-1])
    ensure_tables(conn)
    if conn.execute("SELECT 1 FROM referrals WHERE id=?",
                    (local_id,)).fetchone():
        return 0
    src = dict(item.get("data_json") or {}) \
        if isinstance(item.get("data_json"), dict) else {}
    src.update({k: v for k, v in item.items() if k != "data_json"})
    cols = {r[1] for r in conn.execute("PRAGMA table_info(referrals)")}
    data = {k: v for k, v in src.items() if k in cols and k != "id"}
    try:
        data["patient_id"] = int(src.get("patient_id")
                                 or src.get("patient_file") or 0)
    except Exception:
        return 0
    if not data.get("patient_id") or not (data.get("to_doctor") or ""):
        return 0
    data["created_at"] = src.get("created_at") \
        or src.get("updated_at") or _now()
    from src.models.sync import _upsert
    return _upsert(conn, "referrals", "id", local_id, data,
                   src.get("updated_at"))


def list_referrals(patient_id):
    """[dict] referrals for one patient, newest first."""
    if not patient_id:
        return []
    conn = get_connection()
    try:
        ensure_tables(conn)
        rows = conn.cursor().execute(
            "SELECT * FROM referrals WHERE patient_id=?"
            " ORDER BY created_at DESC, id DESC",
            (patient_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_referral(referral_id):
    """One referral dict by id, or None (round 24: printing)."""
    if not referral_id:
        return None
    conn = get_connection()
    try:
        ensure_tables(conn)
        row = conn.execute("SELECT * FROM referrals WHERE id=?",
                           (referral_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
