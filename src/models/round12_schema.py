"""Round 12 schema additions (2026-11-09). Kept in its own module so
database.py stays at its 200-line limit. Called from init_db().

- created_at on complaints / diagnoses / procedures / financials /
  lab_costs: the 24-hour edit rule needs a creation timestamp per
  record. Old rows keep NULL created_at; callers fall back to the
  record's visit_date / date when it is NULL.
- user_grants(username, perm): per-user EXTRA permissions beyond the
  role default. Grants only add, never remove. Enforced in
  permissions.py; managed from the admin-only Users tab tree.
- users.last_login: last successful login on THIS device (local only).
  Cross-device login/logout stays in the attendance records.
"""
import sqlite3


def ensure_round12_schema(cur):
    """Run inside init_db(); `cur` is the open cursor. Idempotent."""
    for table in ("complaints", "diagnoses", "procedures",
                  "financials", "lab_costs"):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN created_at TEXT")
        except sqlite3.OperationalError:
            pass  # already exists
    cur.execute("""CREATE TABLE IF NOT EXISTS user_grants(
        username TEXT, perm TEXT, PRIMARY KEY(username, perm))""")
    try:
        cur.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
    except sqlite3.OperationalError:
        pass  # already exists
    # Round 12, Jobs 3a+3c (Agent A): per-field notes + author on the
    # clinical tables. complaints gets a second notes column because
    # symptoms share its row (no separate symptoms table).
    for table, cols in (
            ("complaints", ("notes TEXT", "symptoms_notes TEXT", "author TEXT")),
            ("diagnoses", ("notes TEXT", "author TEXT")),
            ("procedures", ("notes TEXT", "author TEXT"))):
        for col in cols:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass  # already exists
    # Round 38: financials.row_kind marks a STANDALONE payment row
    # ('payment': total 0, paid = amount, no session/tooth link --
    # this is how advance payments / patient credit are stored)
    # apart from session money rows ('session', the default, which
    # every pre-round-38 row gets). financials.note is the payment
    # entry's optional note. Both ride inside the sync data_json
    # payload automatically (the server stores blobs; the client
    # pull keeps only columns the local table has). Named row_kind,
    # NOT kind: the sync payload already uses 'kind' for the SYNC
    # record kind (finance_sync.FIN_KINDS) and the pull-apply path
    # drops that key, so a 'kind' column would never survive sync.
    for col in ("row_kind TEXT DEFAULT 'session'", "note TEXT DEFAULT ''"):
        try:
            cur.execute(f"ALTER TABLE financials ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass  # already exists
