"""ANADOCTORFADY sync server - finance, salaries, employees sync (stdlib only).
SERVER-SIDE ROLE FILTERING (owner rule): the server NEVER sends financials
to a non-admin. /sync/pull: admin gets ALL centers; doctor gets ONLY
records where doctor == their username (any center); nurse gets NOTHING.
Salary payments / expenses / lab costs carry no doctor, so no doctor ever
sees them. Employees sync admin-only. Push: a non-admin may push a payment
only when doctor is an existing doctor/admin username in the users table
AND either doctor == themselves (own payment) or entered_by == themselves
(a nurse/doctor recording a payment for the treating doctor); a nurse
cannot credit a payment to herself, and payments with an empty or unknown
doctor are refused (403). Expenses / lab / salary / employee records are
admin-only (403 otherwise). Last-write-wins on updated_at, as elsewhere."""
import json
from sync_helpers import merge, next_seq, now_iso

ADMIN_ONLY_KINDS = {"expense", "lab", "salary"}


def init_tables(conn):
    conn.executescript("""CREATE TABLE IF NOT EXISTS financials_sync(id INTEGER PRIMARY KEY,
      record_id TEXT UNIQUE, center_id TEXT, kind TEXT, doctor TEXT,
      data_json TEXT, updated_at TEXT, updated_by TEXT);
    CREATE TABLE IF NOT EXISTS employees_sync(id INTEGER PRIMARY KEY,
      record_id TEXT UNIQUE, center_id TEXT, data_json TEXT,
      updated_at TEXT, updated_by TEXT);""")
    conn.commit()


def _visible(user, item):
    """Admin: everything. Doctor: only rows where doctor == own username.
    Nurse: nothing. Salary/expense/lab rows have no doctor -> invisible
    to every doctor."""
    role = (user or {}).get("role")
    if role == "admin":
        return True
    if role == "doctor":
        return (item.get("doctor") or "") == user.get("username")
    return False


def pull_financials(conn, user, since=""):
    """Role-filtered financials (all kinds, all centers for admin)."""
    if (user or {}).get("role") == "nurse":
        return []
    out = []
    for r in conn.execute("SELECT record_id, center_id, kind, doctor, data_json, updated_at, updated_by"
                          " FROM financials_sync WHERE updated_at>? ORDER BY updated_at", (since or "",)):
        item = merge(r, 4, {"record_id": 0, "center_id": 1, "kind": 2,
                            "doctor": 3, "updated_at": 5, "updated_by": 6})
        if _visible(user, item):
            out.append(item)
    return out


def pull_employees(conn, user, since=""):
    """Employees sync is admin-only; anyone else gets an empty list."""
    if (user or {}).get("role") != "admin":
        return []
    return [merge(r, 2, {"record_id": 0, "center_id": 1, "updated_at": 3, "updated_by": 4})
            for r in conn.execute("SELECT record_id, center_id, data_json, updated_at, updated_by"
                                  " FROM employees_sync WHERE updated_at>? ORDER BY updated_at", (since or "",))]


def _upsert_table(conn, table, item, user, extra_cols=(), extra_vals=()):
    """Generic last-write-wins upsert keyed on record_id."""
    updated = item.get("updated_at") or now_iso()
    center = item.get("center_id") or user["center_id"]
    dj = item.get("data_json") or item
    data_json = dj if isinstance(dj, str) else json.dumps(dj, ensure_ascii=False)
    key = item.get("record_id") or ""
    row = conn.execute(f"SELECT updated_at FROM {table} WHERE record_id=?", (key,)).fetchone()
    if row and updated <= (row[0] or ""):
        return 0
    seq = next_seq(conn, table)  # R39: server arrival order (delta pull)
    cols = ["record_id", "center_id"] + list(extra_cols) + ["data_json", "updated_at", "updated_by", "seq"]
    vals = [key, center] + list(extra_vals) + [data_json, updated, user["username"], seq]
    conn.execute(f"INSERT OR REPLACE INTO {table}({','.join(cols)}) VALUES({','.join('?' * len(cols))})", vals)
    return 1


def _entered_by(item):
    """Who recorded the payment: top-level field, else inside data_json
    (the client sends entered_by inside the payload dict)."""
    by = item.get("entered_by") or ""
    if not by:
        dj = item.get("data_json")
        if isinstance(dj, dict):
            by = dj.get("entered_by") or ""
    return by


def _is_doctor_or_admin(conn, username):
    """True iff username exists in the users table with role doctor/admin."""
    if not username:
        return False
    row = conn.execute("SELECT role FROM users WHERE username=?",
                       (username,)).fetchone()
    return bool(row) and row[0] in ("doctor", "admin")


def push_financials(conn, items, user):
    """(status, applied|error). A non-admin may push a payment ONLY when
    doctor is an existing doctor/admin username in the users table, AND
    either doctor == sender (own payment) or entered_by == sender (a
    nurse/doctor recording a payment for the treating doctor). So a nurse
    cannot credit a payment to herself, and payments with an empty or
    unknown doctor are refused; expenses / lab / salary are admin-only."""
    role = (user or {}).get("role")
    sender = (user or {}).get("username") or ""
    for item in items or []:
        if not isinstance(item, dict) or not item.get("record_id"):
            continue
        kind = item.get("kind") or ""
        if role == "admin":
            continue
        if kind in ADMIN_ONLY_KINDS:
            return 403, "finance push refused: admin only / للمدراء فقط"
        doctor = item.get("doctor") or ""
        if not _is_doctor_or_admin(conn, doctor):
            return 403, "finance push refused: only own payments or payments recorded for a treating doctor / المدفوعات الخاصة أو المسجلة للطبيب المعالج فقط"
        if doctor == sender or _entered_by(item) == sender:
            continue
        return 403, "finance push refused: only own payments or payments recorded for a treating doctor / المدفوعات الخاصة أو المسجلة للطبيب المعالج فقط"
    applied = 0
    for item in items or []:
        if isinstance(item, dict) and item.get("record_id"):
            applied += _upsert_table(conn, "financials_sync", item, user,
                                     ("kind", "doctor"), (item.get("kind") or "", item.get("doctor") or ""))
    return 200, applied


def push_employees(conn, items, user):
    """(status, applied|error). Employees sync is admin-only."""
    if items and (user or {}).get("role") != "admin":
        return 403, "employees sync is admin-only / الموظفون للمدير فقط"
    applied = 0
    for item in items or []:
        if isinstance(item, dict) and item.get("record_id"):
            applied += _upsert_table(conn, "employees_sync", item, user)
    return 200, applied


# --- Referrals (round 23, item 8) -------------------------------------
# A nurse's referral never synced before round 23: no client queue,
# no push key, no server table. Referrals are CLINICAL records, not
# finance: like patients/visits they are shared within the center --
# EVERY authenticated role may push (the nurse is the reporter in
# the owner's workflow) and every role may pull them (the receiving
# doctor must see them; the nurse sees her own sends). No finance
# role filtering applies. Last-write-wins on updated_at (the
# client sends created_at, referrals being immutable).

def init_referral_tables(conn):
    conn.executescript("""CREATE TABLE IF NOT EXISTS referrals_sync(
      id INTEGER PRIMARY KEY, record_id TEXT UNIQUE, patient_file TEXT,
      center_id TEXT, data_json TEXT, updated_at TEXT, updated_by TEXT);""")
    conn.commit()


def pull_referrals(conn, user, since="", center=None):
    """Referrals for all roles; scoped to `center` when given
    (the /sync/pull handler passes the requested center, matching
    patients/visits), otherwise every center."""
    init_referral_tables(conn)
    sql = ("SELECT record_id, patient_file, center_id, data_json,"
           " updated_at, updated_by FROM referrals_sync"
           " WHERE updated_at>?")
    args = [since or ""]
    if center:
        sql += " AND center_id=?"; args.append(center)
    sql += " ORDER BY updated_at"
    return [merge(r, 3, {"record_id": 0, "patient_file": 1,
                         "center_id": 2, "updated_at": 4,
                         "updated_by": 5})
            for r in conn.execute(sql, args)]


def push_referrals(conn, items, user):
    """(status, applied|error). Any authenticated role may push a
    referral (nurse included); an item needs record_id +
    patient_file, malformed items are skipped like elsewhere."""
    init_referral_tables(conn)
    applied = 0
    for item in items or []:
        if isinstance(item, dict) and item.get("record_id") \
                and str(item.get("patient_file") or ""):
            applied += _upsert_table(
                conn, "referrals_sync", item, user, ("patient_file",),
                (str(item.get("patient_file") or ""),))
    return 200, applied
