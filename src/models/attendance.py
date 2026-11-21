"""Attendance log (Phase 4). Local-first: records are written offline
at login/logout and synced later by the sync client (synced flag).
Table: attendance_log(id, username, action, ts, device_id, synced)."""
import sqlite3
from datetime import datetime
def _now():
    return datetime.now().isoformat(timespec="seconds")
def ensure_tables(conn):
    conn.row_factory = sqlite3.Row
    conn.cursor().execute("""CREATE TABLE IF NOT EXISTS attendance_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, action TEXT,
        ts TEXT, device_id TEXT DEFAULT '', synced INT DEFAULT 0)""")
    conn.commit()
def record_attendance(conn, username, action, device_id=""):
    """Log 'in' or 'out' with local time. Returns row id. Never crashes
    the caller on bad input: raises ValueError only for bad action."""
    if action not in ("in", "out"):
        raise ValueError("action must be 'in' or 'out'")
    ensure_tables(conn)
    c = conn.cursor()
    c.execute("INSERT INTO attendance_log(username,action,ts,device_id,synced)"
              " VALUES(?,?,?,?,0)", (username or "", action, _now(), device_id or ""))
    conn.commit()
    return c.lastrowid
def record_for_user(username, action):
    """One-line clock in/out: own connection + device id. Never raises,
    so login/logout can call it without guarding the UI flow."""
    try:
        from src.models.database import get_connection
        from src.models.telemetry import get_or_create_install_id
        try: dev = get_or_create_install_id()
        except Exception: dev = "local"
        conn = get_connection()
        try: return record_attendance(conn, username, action, dev)
        finally: conn.close()
    except Exception:
        return None
def list_attendance(conn, username=None, date=None):
    """[dict] newest first. date = 'YYYY-MM-DD' matches ts prefix."""
    ensure_tables(conn)
    sql = "SELECT * FROM attendance_log WHERE 1=1"
    args = []
    if username:
        sql += " AND username=?"; args.append(username)
    if date:
        sql += " AND substr(ts,1,10)=?"; args.append(date)
    sql += " ORDER BY ts DESC, id DESC"
    rows = conn.cursor().execute(sql, args).fetchall()
    return [dict(r) for r in rows]
def unsynced_attendance(conn):
    """[dict] rows with synced=0, oldest first (for push)."""
    ensure_tables(conn)
    rows = conn.cursor().execute(
        "SELECT * FROM attendance_log WHERE synced=0 ORDER BY id").fetchall()
    return [dict(r) for r in rows]
def mark_synced(conn, ids):
    """Mark attendance rows synced. ids = iterable of row ids."""
    ids = list(ids)
    if not ids:
        return 0
    ensure_tables(conn)
    c = conn.cursor()
    c.executemany("UPDATE attendance_log SET synced=1 WHERE id=?",
                  [(i,) for i in ids])
    conn.commit()
    return c.rowcount
