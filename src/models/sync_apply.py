"""Apply side of sync: last-write-wins upserts for pulled rows.

Moved verbatim out of models/sync.py in round 39 (that file was at
the 200-line cap and needed room for the delta-pull client code).
models/sync.py re-exports VT / _upsert / _apply_visit, so existing
imports (models.finance_sync, models.referrals, tests) are
unchanged."""
from datetime import datetime

VT = {"complaints": "complaints", "diagnoses": "diagnoses",
      "procedures": "procedures", "notes": "patient_notes"}


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _upsert(conn, table, key_col, key, item, incoming_ts):
    """Insert/update one row, last-write-wins on updated_at. Returns 1/0."""
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if not cols: return 0
    data = {k: v for k, v in item.items() if k in cols and k != key_col}; data[key_col] = key
    if table == "patients":  # R32: never trust synced norm values
        from src.models.patient_norms import NORM_COLUMNS
        data = {k: v for k, v in data.items() if k not in NORM_COLUMNS}
    cur = conn.cursor(); has_ts = "updated_at" in cols
    sel = "updated_at" if has_ts else key_col
    row = cur.execute(f"SELECT {sel} FROM {table} WHERE {key_col}=?", (key,)).fetchone()
    if row and has_ts and (row[0] or "") >= (incoming_ts or ""): return 0
    ks = [k for k in data if k != key_col] if row else list(data)
    if row: cur.execute(f"UPDATE {table} SET {','.join(k + '=?' for k in ks)} WHERE {key_col}=?", [data[k] for k in ks] + [key])
    else: cur.execute(f"INSERT INTO {table}({','.join(ks)}) VALUES({','.join('?' * len(ks))})", [data[k] for k in ks])
    if table == "patients":  # R32: recompute norms locally after write
        from src.models.patient_norms import refresh_norms
        try: refresh_norms(conn, key)
        except Exception: pass
    return 1


def _apply_visit(conn, item):
    table = VT.get(item.get("kind") or ""); rid = str(item.get("record_id") or "")
    if not table or not rid.split(":")[-1].isdigit(): return 0
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    data = {k: v for k, v in item.items() if k in cols and k not in ("record_id", "kind", "center_id")}
    if "patient_file" in cols: data["patient_file"] = item.get("patient_file")
    elif "patient_id" in cols:
        try: data["patient_id"] = int(item.get("patient_file") or 0)
        except Exception: data["patient_id"] = 0
    if "author" in cols and item.get("updated_by"): data.setdefault("author", item["updated_by"])  # author preserved
    if "updated_at" in cols: data["updated_at"] = item.get("updated_at") or _now()
    return _upsert(conn, table, "id", int(rid.split(":")[-1]), data, item.get("updated_at"))
