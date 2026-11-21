"""Item 9: restore .bak backups from other programs.

Valid .bak restore of a seeded DB, invalid-file refusal (DB untouched),
current DB auto-backed-up first, and .bak export.

Isolation: every test runs against a TEMPORARY database (the DB path
is patched in src.models.database + src.models.backup_validate for the
duration of the test, then restored). The live clinic.db is never
touched — other agents/screenshot runs share it concurrently, and a
restore test must not depend on, or disturb, its content.
"""
import contextlib
import shutil
import sqlite3
import tempfile
from pathlib import Path

import src.models.backup_validate as BV
import src.models.database as DBmod
from src.models.backup_validate import (
    export_backup, restore_backup_safe, validate_backup_file)
from src.models.database import get_connection, init_db

TMP = Path(tempfile.mkdtemp(prefix="bak_test_"))


@contextlib.contextmanager
def isolated_db():
    """Patch the DB path to a temp file for one test, then restore it."""
    db_path = TMP / "iso_clinic.db"
    for suf in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suf)
        if p.exists():
            p.unlink()
    old_db, old_bv, old_bk = DBmod.DB, BV.DB, DBmod.BACKUPS
    DBmod.DB, BV.DB, DBmod.BACKUPS = db_path, db_path, TMP / "backups"
    try:
        init_db()
        yield db_path
    finally:
        DBmod.DB, BV.DB, DBmod.BACKUPS = old_db, old_bv, old_bk


def _dump():
    """Logical content of the patients table. Raw DB bytes are NOT a
    stable comparison for a live WAL database: merely opening/closing
    it changes the file bytes, so compare content instead."""
    conn = get_connection()
    try:
        return sorted(r[0] for r in
                      conn.execute("SELECT full_name FROM patients"))
    finally:
        conn.close()


def _count_patients():
    conn = get_connection()
    try:
        return conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    finally:
        conn.close()


def _insert_patient(full_name):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO patients(first_name, full_name,"
                     " birth_date_greg, nationality) VALUES(?,?,?,?)",
                     (full_name.split()[0], full_name, "1990-01-01", "Syrian"))
        conn.commit()
    finally:
        conn.close()


def _checkpoint_and_copy(src, dest):
    """Copy a DB file only after checkpointing, so no WAL frames are
    left behind; the copy is then a standalone valid database."""
    conn = get_connection()
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    finally:
        conn.close()
    shutil.copy2(src, dest)
    chk = sqlite3.connect(str(dest))
    try:
        assert chk.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        chk.close()
    return dest


def _make_db(path, full_name):
    """Build a full-schema clinic DB file at `path` holding one patient.
    A seeded .bak must carry the REAL clinic schema (init_db creates
    indexes on patients.mobile1 etc.), not a minimal table."""
    old_db, old_bv = DBmod.DB, BV.DB
    DBmod.DB, BV.DB = Path(path), Path(path)
    try:
        init_db()
        _insert_patient(full_name)
    finally:
        DBmod.DB, BV.DB = old_db, old_bv
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    finally:
        conn.close()
    return Path(path)


def test_valid_bak_restore_of_seeded_db():
    with isolated_db() as db:
        _insert_patient("Original Patient")
        before_dump, before_count = _dump(), _count_patients()
        snap = _checkpoint_and_copy(db, TMP / "original_snapshot.bak")
        bak = _make_db(TMP / "seeded.bak", "BAK Restore Test Patient")
        ok, msg, auto = restore_backup_safe(bak)
        assert ok is True, msg
        assert auto and Path(auto).exists(), "current DB was not auto-backed-up"
        assert validate_backup_file(auto)[0] is True
        assert "BAK Restore Test Patient" in _dump(), "restored patient not visible"
        assert "Original Patient" not in _dump()
        ok2, msg2, _ = restore_backup_safe(snap)
        assert ok2 is True, msg2
        assert _count_patients() == before_count, "live DB not restored to original"
        assert _dump() == before_dump


def test_invalid_bak_refused_and_db_unchanged():
    with isolated_db():
        _insert_patient("Marker Patient")
        bad = TMP / "not_a_db.bak"
        bad.write_bytes(b"This is not a SQLite database at all, just text.")
        empty = TMP / "empty.bak"
        empty.write_bytes(b"")
        other = TMP / "other_app.bak"
        conn = sqlite3.connect(str(other))
        conn.execute("CREATE TABLE invoices(id INTEGER PRIMARY KEY, total REAL)")
        conn.commit(); conn.close()
        minimal = TMP / "minimal.bak"
        conn = sqlite3.connect(str(minimal))
        conn.execute("CREATE TABLE patients(file_number INTEGER PRIMARY KEY,"
                     " full_name TEXT)")
        conn.execute("INSERT INTO patients(full_name) VALUES('Minimal')")
        conn.commit(); conn.close()
        before_dump, before_count = _dump(), _count_patients()
        for p in (bad, empty, other, minimal):
            ok, msg, auto = restore_backup_safe(p)
            assert ok is False, f"{p.name} should be refused"
            assert auto is None, "no auto-backup should be taken for a refused file"
            assert "nothing was changed" in msg.lower() or "لم يتغير" in msg
        assert _dump() == before_dump, "DB content changed after refused restores"
        assert _count_patients() == before_count


def test_validate_accepts_db_and_sql_rejects_text():
    bak = _make_db(TMP / "valid2.bak", "Validate Patient")
    assert validate_backup_file(bak)[0] is True
    sql = TMP / "dump.sql"
    sql.write_text("CREATE TABLE patients(file_number INTEGER); INSERT INTO patients VALUES(1);",
                   encoding="utf-8")
    assert validate_backup_file(sql)[0] is True
    txt = TMP / "notes.sql"
    txt.write_text("hello, just notes", encoding="utf-8")
    assert validate_backup_file(txt)[0] is False
    assert validate_backup_file(TMP / "missing.bak")[0] is False


def test_export_bak_roundtrip():
    with isolated_db():
        _insert_patient("Export Patient")
        out = TMP / "exported.bak"
        got = export_backup(out)
        assert Path(got).exists() and Path(got).suffix == ".bak"
        assert validate_backup_file(got)[0] is True
        chk = sqlite3.connect(f"file:{got}?mode=ro", uri=True)
        try:
            assert chk.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            exp_names = sorted(r[0] for r in
                               chk.execute("SELECT full_name FROM patients"))
        finally:
            chk.close()
        assert exp_names == _dump(), "exported .bak does not hold the live patients"
