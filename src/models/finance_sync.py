"""Client-side finance / salary / employee sync helpers. Split from
src/models/sync.py so it stays <200 lines. Server-side filtering lives
in server/finance_sync.py: admin sees all centers, doctor only their own
income, nurse nothing. (Lazy imports of sync.py avoid a cycle.)"""
import json
from datetime import datetime

FIN_KINDS = {"financials": "payment", "expenses": "expense", "lab_costs": "lab",
             "salary_payments": "salary", "employees": "employee"}
FIN_TABLES = {"payment": "financials", "expense": "expenses", "lab": "lab_costs", "salary": "salary_payments"}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def ensure_finance_columns(conn):
    """center_id + updated_at on finance tables (migration for old DBs)."""
    for t in ("financials", "expenses", "lab_costs", "salary_payments"):
        for col in ("updated_at TEXT", "center_id TEXT"):
            try:
                conn.cursor().execute(f"ALTER TABLE {t} ADD COLUMN {col}")
            except Exception:
                pass  # already exists / table not created yet


def queue_synced_row(conn, table, record_id):
    """Re-read one finance/salary/employee row and queue it for push.
    Payload carries kind, center_id, doctor, amounts, dates, updated_at."""
    from src.models.sync import queue_change
    row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (record_id,)).fetchone()
    if not row:
        return
    p = dict(row)
    p["kind"] = FIN_KINDS[table]
    p.setdefault("updated_at", _now())
    queue_change(conn, table, f"{table}:{record_id}", p)


def split_financial_queue(pend, center_id):
    """Build the financials + employees push payloads from pending rows.
    The server validates: a non-admin may push a payment for themselves,
    or a payment they recorded (entered_by) for a treating doctor/admin."""
    fin, emp = [], []
    for row in pend:
        if row["table_name"] not in FIN_KINDS:
            continue
        try:
            p = json.loads(row["payload_json"])
        except Exception:
            continue
        p.setdefault("center_id", center_id)
        p.setdefault("updated_at", row["updated_at"])
        item = {"record_id": str(row["record_id"]), "kind": FIN_KINDS[row["table_name"]],
                "doctor": p.get("doctor") or "", "patient_file": str(p.get("patient_file") or ""),
                "center_id": p.get("center_id") or center_id,
                "updated_at": row["updated_at"], "data_json": p}
        (emp if row["table_name"] == "employees" else fin).append(item)
    return fin, emp


def apply_financial_pull(conn, res):
    """Apply pulled financials + employees; returns counts dict."""
    from src.models.sync import _upsert
    counts = {"financials": 0, "employees": 0}
    for key, tbl in (("financials", None), ("employees", "employees")):
        for item in res.get(key) or []:
            try:
                counts[key] += _apply_record(conn, item, tbl or FIN_TABLES.get(item.get("kind") or ""), _upsert)
            except Exception:
                continue
    return counts


def _apply_record(conn, item, table, upsert):
    """Upsert one synced finance/salary/employee row, last-write-wins
    on updated_at. Unknown kind (table None) applies nothing."""
    rid = str(item.get("record_id") or "")
    if not table or not rid.split(":")[-1].isdigit():
        return 0
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if not cols:
        return 0
    data = {k: v for k, v in item.items() if k in cols and k not in ("record_id", "kind", "data_json")}
    if "updated_at" in cols:
        data["updated_at"] = item.get("updated_at") or _now()
    return upsert(conn, table, "id", int(rid.split(":")[-1]), data, item.get("updated_at"))
