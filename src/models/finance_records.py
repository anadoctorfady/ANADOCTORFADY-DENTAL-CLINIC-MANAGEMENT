"""Expense / lab-cost record changes (Round 12, Job 9): edit + delete
for the Finance tab. ADMIN-ONLY, regardless of age (coordinator
ruling 2026-11-09, Agent C is right): only admins can create
expenses/lab costs and doctors have no finance access at all, so
there is no "author doctor" for these rows — the 24h legacy grace
(author None + within 24h -> any doctor) lives ONLY in edit_rules
for clinical records (complaints/diagnoses/procedures). `created_at`
falls back to the record's date when NULL (old rows). Updates
re-queue the row for sync; deletes are local-only (the sync protocol
has no delete kind for expenses/lab costs — see report).
"""
from datetime import datetime
from src.models.database import get_connection, init_db


def may_change_record(role, created_at, username=None):
    """Admin-only: `created_at`/`username` are accepted (callers pass
    them) but play no part — a doctor is refused even within 24h."""
    return (role or "").strip().lower() == "admin"


def _row(table, row_id):
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table} WHERE id=?", (row_id,))
    r = cur.fetchone(); conn.close()
    return dict(r) if r else None


def get_expense(row_id):
    return _row("expenses", row_id)


def get_lab_cost(row_id):
    return _row("lab_costs", row_id)


def _created(row):
    """Creation timestamp, falling back to the record's date."""
    return (row or {}).get("created_at") or (row or {}).get("date")


def delete_expense(row_id, role, username=None):
    row = get_expense(row_id)
    if not row or not may_change_record(role, _created(row), username):
        return False
    conn = get_connection()
    conn.execute("DELETE FROM expenses WHERE id=?", (row_id,))
    conn.commit(); conn.close()
    return True


def delete_lab_cost(row_id, role, username=None):
    row = get_lab_cost(row_id)
    if not row or not may_change_record(role, _created(row), username):
        return False
    conn = get_connection()
    conn.execute("DELETE FROM lab_costs WHERE id=?", (row_id,))
    conn.commit(); conn.close()
    return True


def _update(table, row_id, col, amount, role, username=None):
    row = _row(table, row_id)
    if not row or not may_change_record(role, _created(row), username):
        return False
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return False
    if amount < 0:
        return False
    init_db()
    conn = get_connection()
    conn.execute(f"UPDATE {table} SET {col}=?, updated_at=? WHERE id=?",
                 (amount, datetime.now().isoformat(), row_id))
    try:
        from src.models.finance_sync import queue_synced_row
        queue_synced_row(conn, table, row_id)
    except Exception:
        pass
    conn.commit(); conn.close()
    return True


def update_expense_amount(row_id, amount, role, username=None):
    return _update("expenses", row_id, "amount", amount, role, username)


def update_lab_cost(row_id, cost, role, username=None):
    return _update("lab_costs", row_id, "cost", cost, role, username)
