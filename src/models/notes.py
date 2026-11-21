"""Patient notes: optional free-text notes per patient.
Only the author or an admin may edit/delete a note (enforced here).
All functions take an open sqlite3 connection (never closed here);
fetch_notes(patient_id) is the convenience wrapper that opens its own.
<120 lines."""
import sqlite3
from datetime import datetime
from src.models.database import get_connection
def _now():
    return datetime.now().isoformat(timespec="seconds")
def _today():
    return datetime.now().strftime("%Y-%m-%d")
def ensure_tables(conn):
    conn.row_factory = sqlite3.Row
    conn.cursor().execute("""CREATE TABLE IF NOT EXISTS patient_notes(
        id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INT,
        visit_date TEXT, author TEXT, note TEXT, updated_at TEXT)""")
    conn.commit()
def add_note(conn, patient_id, author, note):
    """Insert a note. Returns id, or None if the text is empty."""
    note = (note or "").strip()
    if not note or not patient_id:
        return None
    ensure_tables(conn)
    c = conn.cursor()
    c.execute("INSERT INTO patient_notes(patient_id,visit_date,author,note,updated_at) VALUES(?,?,?,?,?)",
              (patient_id, _today(), author or "", note, _now()))
    conn.commit()
    return c.lastrowid
def _get(conn, note_id):
    ensure_tables(conn)
    r = conn.cursor().execute("SELECT * FROM patient_notes WHERE id=?", (note_id,)).fetchone()
    return dict(r) if r else None
def _allowed(row, current_user, role, can_edit=None):
    if can_edit is not None:
        return bool(can_edit)
    return bool(row) and (role == "admin" or row.get("author") == current_user)
def update_note(conn, note_id, current_user, note, role="user", can_edit=None):
    """Edit a note. Only author or admin (or can_edit=True from caller).
    Returns True on success, False if not found / not allowed / empty."""
    note = (note or "").strip()
    row = _get(conn, note_id)
    if not row or not note or not _allowed(row, current_user, role, can_edit):
        return False
    conn.cursor().execute("UPDATE patient_notes SET note=?, updated_at=? WHERE id=?",
                          (note, _now(), note_id))
    conn.commit()
    return True
def delete_note(conn, note_id, current_user, role="user", can_edit=None):
    """Delete a note. Same author-or-admin rule as update_note."""
    row = _get(conn, note_id)
    if not row or not _allowed(row, current_user, role, can_edit):
        return False
    conn.cursor().execute("DELETE FROM patient_notes WHERE id=?", (note_id,))
    conn.commit()
    return True
def list_notes(conn, patient_id):
    """[dict] newest first for one patient."""
    ensure_tables(conn)
    rows = conn.cursor().execute(
        "SELECT * FROM patient_notes WHERE patient_id=? ORDER BY visit_date DESC, id DESC",
        (patient_id,)).fetchall()
    return [dict(r) for r in rows]
def fetch_notes(patient_id):
    """list_notes() with its own connection (used by the PDF builder)."""
    conn = get_connection()
    try:
        return list_notes(conn, patient_id)
    finally:
        conn.close()
