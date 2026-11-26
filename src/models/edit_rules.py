"""24-hour edit rule (2026-11-09, owner rule).

A saved record (visit / procedure / payment) may be edited or deleted
within 24 hours of creation by its author doctor OR the admin. After
24 hours ONLY the admin may edit or delete it.

`created_at` is an ISO timestamp. When it is missing (old rows) the
caller should pass the record's visit_date / date as a fallback; when
even that is missing the record is treated as old (admin only).

Legacy rows have no author column: within 24h any doctor may edit
them (author unknown, almost certainly their own recent visit);
after 24h admin only. Rows WITH an author are strict: author or admin.
"""
from datetime import datetime

RULE_HOURS = 24


def _parse(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts)[:19])
    except ValueError:
        return None


def record_age_hours(created_at, now=None):
    """Hours since creation, or None when the timestamp is unknown."""
    made = _parse(created_at)
    if made is None:
        return None
    now = now or datetime.now()
    return (now - made).total_seconds() / 3600.0


def can_edit(role, author, created_at, username=None, now=None):
    """True when `role`/`username` may edit/delete a record created at
    `created_at` by `author`. Admin: always. Author doctor: within
    24h. Legacy row (author None): any doctor within 24h."""
    if role == "admin":
        return True
    if role != "doctor":
        return False
    age = record_age_hours(created_at, now)
    if age is None or age > RULE_HOURS:
        return False
    if author is None:
        return True  # legacy row, author unknown
    return bool(username) and username == author


can_delete = can_edit


def block_reason(lang=None):
    """Single-language explanation shown when editing is refused
    (round 17: lang=None resolves to the app language setting)."""
    if lang not in ("en", "ar"):
        try:
            from src.models.database import get_setting
            lang = "ar" if (get_setting("language", "en") or "en") == "ar" else "en"
        except Exception:
            lang = "en"
    if lang == "ar":
        return "لا يمكن التعديل بعد 24 ساعة إلا من قبل المدير"
    return "Editing is allowed only by the admin after 24 hours"


# ---- Model-level enforcement (Job 5, 2026-11-09) -----------------------
# Tables covered by the 24h rule + their fallback date column (used
# when created_at is NULL, e.g. rows saved before this round).
_TABLE_DATES = {"complaints": "visit_date", "diagnoses": "visit_date",
                "procedures": "visit_date", "financials": "visit_date",
                "expenses": "date", "lab_costs": "date"}
# Author column per table. Clinical tables have no author column yet
# (Agent A adds it at insert time); financials carry the treating
# doctor. Expenses / lab costs are admin-only operations, so they
# report author "" (never a doctor) instead of None (legacy = any
# doctor within 24h).
_TABLE_AUTHORS = {"complaints": "author", "diagnoses": "author",
                  "procedures": "author", "financials": "doctor",
                  "expenses": None, "lab_costs": None}


def fetch_record_meta(conn, table, row_id):
    """(author, created_at, fallback_date) for one row, or None when
    the row does not exist. Column-safe: author / created_at are
    probed via PRAGMA, so this works before the author column exists
    and on tables without created_at."""
    if table not in _TABLE_DATES:
        raise ValueError(f"24h rule does not cover table {table!r}")
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    author_col = _TABLE_AUTHORS[table]
    author = None
    if table in ("expenses", "lab_costs"):
        author = ""  # admin-only operations, no author recorded
    elif author_col in cols:
        row = conn.execute(f"SELECT {author_col} FROM {table} WHERE id=?",
                           (row_id,)).fetchone()
        author = row[0] if row else None
    date_col = _TABLE_DATES[table]
    if "created_at" in cols:
        row = conn.execute(
            f"SELECT created_at, {date_col} FROM {table} WHERE id=?",
            (row_id,)).fetchone()
        if row is None:
            return None
        return (author, row[0], row[1])
    row = conn.execute(f"SELECT {date_col} FROM {table} WHERE id=?",
                       (row_id,)).fetchone()
    if row is None:
        return None
    return (author, None, row[0])


def check_record(role, username, author, created_at, fallback_date=None,
                 now=None, lang=None):
    """(allowed, reason_or_None) for one record. When created_at is
    NULL the record's visit_date/date is used as the creation time;
    when both are missing the record counts as old (admin only)."""
    effective = created_at or fallback_date
    if can_edit(role, author, effective, username, now):
        return True, None
    return False, block_reason(lang)


def authorize_edit(conn, table, row_id, role, username, lang=None, now=None):
    """Fetch + check one record. Returns its meta dict when editing is
    allowed; raises LookupError when the row is missing and
    PermissionError(block_reason) when the 24h rule refuses it. UI and
    model update paths gate on this before touching the row."""
    meta = fetch_record_meta(conn, table, row_id)
    if meta is None:
        raise LookupError(f"{table} row {row_id} not found")
    author, created_at, fallback = meta
    ok, reason = check_record(role, username, author, created_at,
                              fallback, now, lang)
    if not ok:
        raise PermissionError(reason)
    return {"author": author, "created_at": created_at,
            "fallback_date": fallback}


# ---- Round 49 (Section F): DATE editing is ADMIN-ONLY -------------
# Layered ON TOP of the 24h rule above: a doctor who may edit a
# record's content within 24h still may NOT move it to another date.
def can_edit_date(role):
    """True only for the admin role."""
    return role == "admin"


def valid_date(value):
    """True iff `value` is a real calendar date in strict
    YYYY-MM-DD form (zero-padded, nothing before/after)."""
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except (ValueError, TypeError):
        return False
    return parsed.strftime("%Y-%m-%d") == value


def delete_record_checked(conn, table, row_id, role, username, lang=None,
                          now=None):
    """Delete one record after the 24h check. Returns True on success,
    False when refused or the row is missing (same False convention as
    finance.update_payment_checked)."""
    try:
        authorize_edit(conn, table, row_id, role, username, lang, now)
    except (LookupError, PermissionError):
        return False
    conn.execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
    conn.commit()
    return True
