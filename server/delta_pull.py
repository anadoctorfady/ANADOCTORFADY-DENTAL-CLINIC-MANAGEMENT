"""Round 39: delta (incremental) pull for GET /sync/pull.

Protocol: a client that sends `server_id` and/or `seq_<table>`
query params gets this path; a client that sends neither gets the
legacy timestamp-filtered pull in sync_server.py, byte-for-byte as
before. Each table's rows are filtered by the server-assigned `seq`
(see sync_helpers): the client stores the highest seq it has been
served per table (its watermark) and asks for `seq > watermark`.

Safety properties:
- Watermarks are per (server, center, table) on the client and the
  response carries this server's `server_id`: a client talking to a
  new/replaced server DB (different id) is served a FULL pull, so
  stored watermarks from another server can never starve it.
- `watermarks[table]` in the response is the max seq SERVED for
  that table (after center scoping and, for financials, the finance
  role filter), or null when nothing was served — the client then
  keeps its previous watermark, so rows a role cannot see never
  advance its watermark past data it might later become able to
  see, and an idle table costs one indexed range check.
- Apply on the client is the same idempotent last-write-wins
  upsert as the legacy pull, so any re-delivery is harmless.
- updated_at / last-write-wins semantics are untouched: seq only
  decides WHICH rows are offered, never which version wins.
"""
from finance_sync import _visible
from sync_helpers import ensure_seq, merge, server_id

TABLES = ("patients", "visits", "financials", "employees", "referrals")


def _seq_param(q, key, full):
    """Client watermark for one table; 0 in full mode / on garbage."""
    if full:
        return 0
    try:
        return max(0, int(q.get(f"seq_{key}", ["0"])[0] or 0))
    except (TypeError, ValueError):
        return 0


def _max_seq(rows, idx):
    vals = [r[idx] for r in rows if r[idx] is not None]
    return max(vals) if vals else None


def _patients(conn, user, q, full):
    center = q.get("center_id", [user["center_id"]])[0]
    rows = conn.execute(
        "SELECT patient_file, center_id, data_json, updated_at,"
        " updated_by, seq FROM patients_sync WHERE center_id=?"
        " AND seq>? ORDER BY seq",
        (center, _seq_param(q, "patients", full))).fetchall()
    items = [merge(r, 2, {"patient_file": 0, "center_id": 1,
                          "updated_at": 3, "updated_by": 4})
             for r in rows]
    return items, _max_seq(rows, 5)


def _visits(conn, user, q, full):
    center = q.get("center_id", [user["center_id"]])[0]
    rows = conn.execute(
        "SELECT record_id, patient_file, center_id, kind, data_json,"
        " updated_at, updated_by, seq FROM visits_sync"
        " WHERE center_id=? AND seq>? ORDER BY seq",
        (center, _seq_param(q, "visits", full))).fetchall()
    items = [merge(r, 4, {"record_id": 0, "patient_file": 1,
                          "center_id": 2, "kind": 3, "updated_at": 5,
                          "updated_by": 6}) for r in rows]
    return items, _max_seq(rows, 7)


def _financials(conn, user, q, full):
    """Same role filter as the legacy pull (nurse: nothing; doctor:
    own rows only; admin: all). Watermark = max seq SERVED."""
    if (user or {}).get("role") == "nurse":
        return [], None
    rows = conn.execute(
        "SELECT record_id, center_id, kind, doctor, data_json,"
        " updated_at, updated_by, seq FROM financials_sync"
        " WHERE seq>? ORDER BY seq",
        (_seq_param(q, "financials", full),)).fetchall()
    served = []
    for r in rows:
        item = merge(r, 4, {"record_id": 0, "center_id": 1, "kind": 2,
                            "doctor": 3, "updated_at": 5,
                            "updated_by": 6})
        if _visible(user, item):
            served.append((item, r[7]))
    return [i for i, _ in served], _max_seq(served, 1)


def _employees(conn, user, q, full):
    if (user or {}).get("role") != "admin":
        return [], None
    rows = conn.execute(
        "SELECT record_id, center_id, data_json, updated_at,"
        " updated_by, seq FROM employees_sync WHERE seq>?"
        " ORDER BY seq",
        (_seq_param(q, "employees", full),)).fetchall()
    items = [merge(r, 2, {"record_id": 0, "center_id": 1,
                          "updated_at": 3, "updated_by": 4})
             for r in rows]
    return items, _max_seq(rows, 5)


def _referrals(conn, user, q, full):
    center = q.get("center_id", [user["center_id"]])[0]
    rows = conn.execute(
        "SELECT record_id, patient_file, center_id, data_json,"
        " updated_at, updated_by, seq FROM referrals_sync"
        " WHERE center_id=? AND seq>? ORDER BY seq",
        (center, _seq_param(q, "referrals", full))).fetchall()
    items = [merge(r, 3, {"record_id": 0, "patient_file": 1,
                          "center_id": 2, "updated_at": 4,
                          "updated_by": 5}) for r in rows]
    return items, _max_seq(rows, 6)


_BUILDERS = {"patients": _patients, "visits": _visits,
             "financials": _financials, "employees": _employees,
             "referrals": _referrals}


def delta_pull(conn, user, q):
    """Full /sync/pull response dict for a delta-mode request."""
    ensure_seq(conn)
    sid = server_id(conn)
    full = (q.get("server_id", [""])[0] or "") != sid
    out = {"server_id": sid, "watermarks": {}}
    for key in TABLES:
        items, mark = _BUILDERS[key](conn, user, q, full)
        out[key] = items
        out["watermarks"][key] = mark
    return out
