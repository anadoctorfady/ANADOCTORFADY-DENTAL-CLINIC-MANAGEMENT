"""Clipdiary-like clipboard history, persisted in SQLite (max 30).
External Clipdiary also works: it puts text on the system clipboard,
and the UI polls it (see phrase_picker.poll_clipboard). <100 lines.
Phase 2: newest-first history list, multi_paste() (one item per line),
and copy_row_text() for the clinical tables' "Copy row" buttons."""
from datetime import datetime
from src.models.database import get_connection
from src.models.phrases import ensure_tables
MAX_CLIPS = 30
HISTORY_LIMIT = 20  # picker / list default: newest 20
def _now():
    return datetime.now().isoformat(timespec="seconds")
def add_clip(text):
    """Add text; ignore empty / duplicate of the most recent clip."""
    text = (text or "").strip()
    if len(text) < 2:
        return None
    ensure_tables()
    conn = get_connection(); c = conn.cursor()
    last = c.execute("SELECT text FROM clipboard_history ORDER BY id DESC LIMIT 1").fetchone()
    if last and last["text"] == text:
        conn.close(); return None
    c.execute("INSERT INTO clipboard_history(text,copied_at) VALUES(?,?)", (text, _now()))
    c.execute("DELETE FROM clipboard_history WHERE id NOT IN (SELECT id FROM clipboard_history ORDER BY id DESC LIMIT ?)", (MAX_CLIPS,))
    conn.commit(); conn.close(); return True
def list_clips(limit=20):
    ensure_tables()
    conn = get_connection(); c = conn.cursor()
    c.execute("SELECT * FROM clipboard_history ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]; conn.close(); return rows
def get_history(limit=HISTORY_LIMIT):
    """Newest-first list of history texts (strings, not row dicts)."""
    return [r["text"] for r in list_clips(limit)]
def multi_paste(items):
    """Join selected items into one string, one item per line, in the
    order given (the picker's selection order). Empty items dropped."""
    return "\n".join(str(i).strip() for i in (items or []) if str(i).strip())
def multi_paste_all(limit=HISTORY_LIMIT):
    """Paste-all: every history item, newest first, one per line."""
    return multi_paste(get_history(limit))
def copy_row_text(text):
    """Copy a table row's text into history. Dedupes (an existing copy
    of the same text is moved to the top) and caps at MAX_CLIPS."""
    text = (text or "").strip()
    if len(text) < 2:
        return None
    ensure_tables()
    conn = get_connection(); c = conn.cursor()
    c.execute("DELETE FROM clipboard_history WHERE text=?", (text,))
    conn.commit(); conn.close()
    return add_clip(text)
def clear_clips():
    ensure_tables()
    conn = get_connection(); c = conn.cursor(); c.execute("DELETE FROM clipboard_history"); conn.commit(); conn.close()
