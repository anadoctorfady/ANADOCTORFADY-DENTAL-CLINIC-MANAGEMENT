"""Shared helpers for the sync server (stdlib only): timestamps, row
mapping, and the last-write-wins upsert for patients/visits."""
import json
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def rows_dict(conn, sql, args, cols):
    return [dict(zip(cols, r)) for r in conn.execute(sql, args)]


def merge(row, data_idx, fields):
    """data_json (parsed) + stored columns; stored columns win only if absent."""
    try:
        data = json.loads(row[data_idx])
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {"value": data}
    out = dict(data)
    for k, i in fields.items():
        out.setdefault(k, row[i])
    return out


def upsert_sync(conn, item, user, is_patient):
    """Last-write-wins: overwrite only if incoming updated_at > stored."""
    table, key_col, key = ("patients_sync", "patient_file", item["patient_file"]) if is_patient else \
        ("visits_sync", "record_id", item["record_id"])
    updated = item.get("updated_at") or now_iso()
    center = item.get("center_id") or user["center_id"]
    dj = item.get("data_json") or item
    data_json = dj if isinstance(dj, str) else json.dumps(dj, ensure_ascii=False)
    row = conn.execute(f"SELECT updated_at FROM {table} WHERE {key_col}=?", (key,)).fetchone()
    if row and updated <= (row[0] or ""):
        return 0
    if is_patient:
        conn.execute("INSERT OR REPLACE INTO patients_sync(patient_file, center_id, data_json, updated_at, updated_by)"
                     " VALUES (?,?,?,?,?)", (key, center, data_json, updated, user["username"]))
    else:
        conn.execute("INSERT OR REPLACE INTO visits_sync(record_id, patient_file, center_id, kind, data_json, updated_at, updated_by)"
                     " VALUES (?,?,?,?,?,?,?)", (key, item.get("patient_file") or "", center, item.get("kind") or "", data_json, updated, user["username"]))
    return 1
