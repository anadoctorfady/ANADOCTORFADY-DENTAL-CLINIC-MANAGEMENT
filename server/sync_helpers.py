"""Shared helpers for the sync server (stdlib only): timestamps, row
mapping, and the last-write-wins upsert for patients/visits.

Round 39 adds the delta-sync sequence infrastructure: every sync
table carries a `seq` column assigned BY THE SERVER from a per-table
counter at upsert time (arrival order). Pull watermarks are seq
values, never client timestamps, so clock skew between clinic PCs
cannot make a client skip rows: a row pushed late with an old
updated_at still gets a fresh seq and is delivered to every client
on its next pull (last-write-wins on updated_at still decides
whether it overwrites, exactly as before)."""
import json
import uuid
from datetime import datetime, timezone

SEQ_TABLES = ("patients_sync", "visits_sync", "financials_sync",
              "employees_sync", "referrals_sync")


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


def _table_exists(conn, table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table'"
                        " AND name=?", (table,)).fetchone() is not None


def _ensure_one_seq(conn, table):
    """Add + backfill `seq` for one sync table and seed its counter.
    Idempotent; after the first run this is a PRAGMA + a counter
    lookup, so upsert paths may call it per write."""
    if not _table_exists(conn, table):
        return
    conn.execute("CREATE TABLE IF NOT EXISTS sync_seq_counters"
                 "(name TEXT PRIMARY KEY, next INTEGER NOT NULL DEFAULT 0)")
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    if "seq" not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN seq INTEGER")
    conn.execute(f"UPDATE {table} SET seq=id WHERE seq IS NULL")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_seq"
                 f" ON {table}(seq)")
    conn.execute("INSERT OR IGNORE INTO sync_seq_counters(name, next)"
                 f" SELECT ?, COALESCE(MAX(seq), 0) FROM {table}",
                 (table,))
    # The counter must never sit BELOW the table's max seq: rows can
    # exist above it when the counter was seeded while the table was
    # empty (server init) and rows arrived later by another path
    # (bulk load, a pre-R39 backup restore). A low counter hands out
    # seqs under every client's watermark and delta pulls starve —
    # the R39 load bench caught exactly this. Raise, never lower.
    conn.execute("UPDATE sync_seq_counters SET next=MAX(next,"
                 f" (SELECT COALESCE(MAX(seq), 0) FROM {table}))"
                 " WHERE name=?", (table,))


def ensure_seq(conn):
    """Seq columns/counters for every sync table + the server id.
    Called at server init and defensively from the pull handler."""
    conn.execute("CREATE TABLE IF NOT EXISTS sync_meta"
                 "(key TEXT PRIMARY KEY, value TEXT)")
    for t in SEQ_TABLES:
        _ensure_one_seq(conn, t)
    if not server_id(conn):
        conn.execute("INSERT OR IGNORE INTO sync_meta(key, value)"
                     " VALUES('server_id', ?)", (uuid.uuid4().hex,))


def server_id(conn):
    """Stable id of THIS server database (uuid, created by
    ensure_seq). A client whose stored server_id differs gets a
    full pull, so replacing/restoring the server DB self-heals
    instead of silently starving clients of rows."""
    try:
        row = conn.execute("SELECT value FROM sync_meta"
                           " WHERE key='server_id'").fetchone()
    except Exception:
        return ""
    return (row[0] or "") if row else ""


def next_seq(conn, table):
    """Next server-assigned sequence value for a sync table."""
    _ensure_one_seq(conn, table)
    conn.execute("UPDATE sync_seq_counters SET next=next+1 WHERE name=?",
                 (table,))
    return conn.execute("SELECT next FROM sync_seq_counters"
                        " WHERE name=?", (table,)).fetchone()[0]


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
    seq = next_seq(conn, table)
    if is_patient:
        conn.execute("INSERT OR REPLACE INTO patients_sync(patient_file, center_id, data_json, updated_at, updated_by, seq)"
                     " VALUES (?,?,?,?,?,?)", (key, center, data_json, updated, user["username"], seq))
    else:
        conn.execute("INSERT OR REPLACE INTO visits_sync(record_id, patient_file, center_id, kind, data_json, updated_at, updated_by, seq)"
                     " VALUES (?,?,?,?,?,?,?,?)", (key, item.get("patient_file") or "", center, item.get("kind") or "", data_json, updated, user["username"], seq))
    return 1
