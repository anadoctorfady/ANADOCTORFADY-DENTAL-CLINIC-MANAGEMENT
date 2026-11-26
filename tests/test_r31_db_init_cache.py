"""Round 31 (item 2 follow-up): init_db() memoization in database.py.

Profile on the 500-patient seed showed init_db() (~52ms) ran ~42x per
toggle, and its unconditional UPDATE users SET role='admin' rewrote
the fady row on EVERY run, changing the DB file fingerprint, which
invalidated the settings cache so the next get_setting() paid a full
_load_settings() (~19 reloads per toggle). Fix: the full init body
runs ONCE per DB file identity (resolved path + mtime_ns + size, the
settings-cache fingerprint); any write/replace/delete changes the
fingerprint and the next call re-runs the full body; a missing file
always runs it. The users UPDATE is additionally guarded to fire
only when the role actually differs. First-init semantics are
unchanged: fresh and legacy DBs get every table/column/index,
the default admin and the default settings, in the same order.
Isolation: DB path patched to temp files (live DB never touched),
module cache state saved/restored around every test.
"""
import contextlib, hashlib, os, sqlite3, tempfile, time
from pathlib import Path

import src.models.database as DBmod
from src.models.database import get_connection, get_setting, init_db

_TMP = Path(tempfile.mkdtemp(prefix="r31_dbinit_"))
TABLES = {"users", "settings", "patients", "prescriptions",
          "prescription_items", "financials", "appointments",
          "patient_notes", "specialty_templates", "custom_specialties",
          "attendance_log", "sync_queue", "employees",
          "salary_payments", "referrals", "exchange_rates",
          "user_grants", "clipboard_history", "teeth_records"}


@contextlib.contextmanager
def _patched(path):
    old_db = DBmod.DB
    saved = (DBmod._INIT_KEY, DBmod._SETTINGS_CACHE, DBmod._SETTINGS_FP)
    DBmod.DB = Path(path)
    DBmod._INIT_KEY = None
    DBmod._SETTINGS_CACHE = None; DBmod._SETTINGS_FP = None
    try:
        yield Path(path)
    finally:
        DBmod.DB = old_db
        (DBmod._INIT_KEY, DBmod._SETTINGS_CACHE,
         DBmod._SETTINGS_FP) = saved


def _tables():
    conn = get_connection()
    try:
        return {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


def _admin_role():
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT role FROM users WHERE username='fady'").fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _snap(path):
    s = path.stat()
    return (s.st_mtime_ns, s.st_size,
            hashlib.md5(path.read_bytes()).hexdigest())


def test_fresh_init_creates_full_schema_and_defaults():
    with _patched(_TMP / "fresh" / "clinic.db") as db:
        db.parent.mkdir(parents=True, exist_ok=True)
        assert init_db() == db
        assert TABLES <= _tables(), TABLES - _tables()
        assert _admin_role() == "admin"
        conn = get_connection()
        try:
            keys = {r[0] for r in conn.execute("SELECT key FROM settings")}
        finally:
            conn.close()
        assert {"clinic_name", "language", "theme_mode",
                "default_currency", "telegram", "centre_phone"} <= keys
        # Two-pass completion in ONE call: the phase-4 sync ensure runs
        # before complaints/financials/expenses/lab_costs are created,
        # so old code only added their sync/finance columns on the
        # SECOND init_db() call. init_db now re-runs that ensure at the
        # end of the same call; the columns must exist after one call.
        conn = get_connection()
        try:
            cols = {t: {r[1] for r in conn.execute(f"PRAGMA table_info({t})")}
                    for t in ("complaints", "diagnoses", "procedures",
                              "financials", "expenses", "lab_costs")}
        finally:
            conn.close()
        for t in ("complaints", "diagnoses", "procedures"):
            assert "updated_at" in cols[t], (t, cols[t])
        for t in ("financials", "expenses", "lab_costs"):
            assert {"center_id", "updated_at"} <= cols[t], (t, cols[t])


def test_second_init_is_a_noop():
    with _patched(_TMP / "noop" / "clinic.db") as db:
        db.parent.mkdir(parents=True, exist_ok=True)
        init_db()
        before = _snap(db)
        t0 = time.perf_counter(); init_db(); dt = time.perf_counter() - t0
        assert dt < 0.005, f"second init_db took {dt*1000:.2f}ms"
        assert _snap(db) == before, "second init_db touched the DB file"
        init_db(); assert _snap(db) == before


def test_reinit_after_delete_recreates_schema():
    with _patched(_TMP / "gone" / "clinic.db") as db:
        db.parent.mkdir(parents=True, exist_ok=True)
        init_db(); assert _admin_role() == "admin"
        for suf in ("", "-wal", "-shm"):
            p = Path(str(db) + suf)
            if p.exists(): p.unlink()
        init_db()
        assert TABLES <= _tables(), TABLES - _tables()
        assert _admin_role() == "admin"


def test_different_db_path_gets_full_init():
    with _patched(_TMP / "one" / "clinic.db") as db1:
        db1.parent.mkdir(parents=True, exist_ok=True)
        init_db(); assert _admin_role() == "admin"
        with _patched(_TMP / "two" / "clinic.db") as db2:
            db2.parent.mkdir(parents=True, exist_ok=True)
            init_db()
            assert TABLES <= _tables(), TABLES - _tables()
            assert _admin_role() == "admin"
        # Back to the first DB: still intact and usable.
        init_db(); assert _admin_role() == "admin"


def test_users_update_guard_restores_admin_only_when_wrong():
    with _patched(_TMP / "guard" / "clinic.db") as db:
        db.parent.mkdir(parents=True, exist_ok=True)
        init_db()
        conn = get_connection()
        conn.execute("UPDATE users SET role='doctor' WHERE username='fady'")
        conn.commit(); conn.close()  # external write: fingerprint changes
        init_db()  # full re-init must restore the admin role
        assert _admin_role() == "admin"
        # ...and the memo re-arms: the next call is a no-op again.
        before = _snap(db); init_db(); assert _snap(db) == before


def test_settings_cache_not_reloaded_by_repeated_init():
    with _patched(_TMP / "storm" / "clinic.db") as db:
        db.parent.mkdir(parents=True, exist_ok=True)
        init_db(); get_setting("language", "en")  # prime the cache
        orig = DBmod._load_settings; calls = []
        def counting():
            calls.append(1); orig()
        DBmod._load_settings = counting
        try:
            for _ in range(20):
                init_db(); get_setting("language", "en")
        finally:
            DBmod._load_settings = orig
        assert len(calls) == 0, f"_load_settings ran {len(calls)}x in 20 rounds"


def test_legacy_db_is_upgraded_on_first_init():
    db = _TMP / "legacy" / "clinic.db"; db.parent.mkdir(parents=True)
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT,"
                 " username TEXT UNIQUE, password_hash TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE exchange_rates(date TEXT PRIMARY KEY,"
                 " rate REAL, source TEXT)")
    conn.execute("INSERT INTO exchange_rates VALUES('2026-01-01',13000,'manual')")
    conn.commit(); conn.close()
    with _patched(db):
        init_db()
        conn = get_connection()
        try:
            ucols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
            ecols = {r[1] for r in conn.execute(
                "PRAGMA table_info(exchange_rates)")}
            rate = conn.execute("SELECT from_currency, to_currency, rate"
                                " FROM exchange_rates").fetchone()
        finally:
            conn.close()
        assert {"role", "last_login"} <= ucols
        assert {"from_currency", "to_currency"} <= ecols
        assert tuple(rate) == ("USD", "SYP", 13000.0)
        assert TABLES <= _tables()
        assert _admin_role() == "admin"
