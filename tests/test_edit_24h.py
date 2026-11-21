"""Job 5: 24-hour edit rule, model level (edit_rules.py). Isolation:
every DB test runs against a TEMPORARY database (DB path patched in
src.models.database for the test, then restored). Live clinic.db never touched.
"""
import contextlib
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import src.models.database as DBmod
from src.config.strings import t
from src.models.database import get_connection, init_db
from src.models.edit_rules import (authorize_edit, block_reason, can_edit,
                                   check_record, delete_record_checked,
                                   fetch_record_meta)

TMP = Path(tempfile.mkdtemp(prefix="edit24_test_"))
NOW = datetime.now()
RECENT = (NOW - timedelta(hours=1)).isoformat(timespec="seconds")
OLD = (NOW - timedelta(hours=25)).isoformat(timespec="seconds")
TODAY = NOW.strftime("%Y-%m-%d")
OLD_DATE = (NOW - timedelta(days=3)).strftime("%Y-%m-%d")


@contextlib.contextmanager
def isolated_db():
    db_path = TMP / "iso_clinic.db"
    for suf in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suf)
        if p.exists():
            p.unlink()
    old_db = DBmod.DB
    DBmod.DB = db_path
    try:
        init_db()
        yield db_path
    finally:
        DBmod.DB = old_db


def test_can_edit_matrix():
    # admin: always, any age, any author
    assert can_edit("admin", "doc_a", OLD, "doc_b") is True
    assert can_edit("admin", None, None, None) is True
    # author doctor: recent yes, old no
    assert can_edit("doctor", "doc_a", RECENT, "doc_a") is True
    assert can_edit("doctor", "doc_a", OLD, "doc_a") is False
    # other doctor: never for authored rows, even recent
    assert can_edit("doctor", "doc_a", RECENT, "doc_b") is False
    assert can_edit("doctor", "doc_a", OLD, "doc_b") is False
    # legacy row (author None): any doctor within 24h, admin only after
    assert can_edit("doctor", None, RECENT, "doc_b") is True
    assert can_edit("doctor", None, OLD, "doc_b") is False
    # nurse: never, even recent
    assert can_edit("nurse", "doc_a", RECENT, "nurse1") is False
    assert can_edit("nurse", None, RECENT, "nurse1") is False
    assert can_edit("doctor", "doc_a", None, "doc_a") is False
    assert can_edit("doctor", None, None, "doc_a") is False
    # boundary: 24h allowed, 24h+1s refused (truncate µs first: ISO
    # seconds precision would otherwise push the exact edge 1s over).
    now0 = NOW.replace(microsecond=0)
    edge = (now0 - timedelta(hours=24)).isoformat(timespec="seconds")
    assert can_edit("doctor", "doc_a", edge, "doc_a", now0) is True
    over = (now0 - timedelta(hours=24, seconds=1)).isoformat(timespec="seconds")
    assert can_edit("doctor", "doc_a", over, "doc_a", now0) is False


def test_check_record_fallback_date():
    # NULL created_at falls back to the record's visit_date/date.
    assert check_record("doctor", "doc_b", None, None, TODAY)[0] is True
    assert check_record("doctor", "doc_b", None, None, OLD_DATE)[0] is False
    assert check_record("doctor", "doc_a", "doc_a", None, None)[0] is False
    assert check_record("admin", "fady", "doc_a", None, None)[0] is True
    # authored row + recent fallback date: author only
    assert check_record("doctor", "doc_a", "doc_a", None, TODAY)[0] is True
    assert check_record("doctor", "doc_b", "doc_a", None, TODAY)[0] is False
    # refusal carries the bilingual reason
    ok, reason = check_record("doctor", "doc_b", "doc_a", OLD, None, None, "ar")
    assert ok is False and "24" in reason and "المدير" in reason


def test_block_reason_bilingual():
    assert block_reason("en") == t("edit24_blocked", "en")
    assert block_reason("ar") == t("edit24_blocked", "ar")
    assert block_reason("en") != block_reason("ar")


def test_fetch_record_meta_unknown_table():
    with isolated_db():
        conn = get_connection()
        try:
            try:
                fetch_record_meta(conn, "patients", 1)
            except ValueError:
                pass
            else:
                raise AssertionError("expected ValueError for uncovered table")
            assert fetch_record_meta(conn, "complaints", 9999) is None
        finally:
            conn.close()


def _seed_fin(conn):
    conn.execute("INSERT INTO patients(file_number, full_name) VALUES(1,'Test')")
    # (id, created_at, visit_date, doctor): recent / old / NULL+recent visit / NULL+old visit / NULL+NULL.
    rows = [(1, RECENT, TODAY, "doc_a"), (2, OLD, OLD_DATE, "doc_a"),
            (3, None, TODAY, "doc_a"), (4, None, OLD_DATE, "doc_a"),
            (5, None, None, "doc_a")]
    for rid, created, visit, doc in rows:
        conn.execute("INSERT INTO financials(id, patient_file, total_cost,"
                     " paid_amount, remaining, visit_date, doctor, created_at)"
                     " VALUES(?,?,?,?,?,?,?,?)",
                     (rid, 1, 100, 100, 0, visit, doc, created))
    conn.commit()


def test_authorize_edit_financials():
    with isolated_db():
        conn = get_connection()
        try:
            _seed_fin(conn)
            # recent authored row: author yes, other doctor no, nurse no
            assert authorize_edit(conn, "financials", 1, "doctor", "doc_a")["author"] == "doc_a"
            for role, user in (("doctor", "doc_b"), ("nurse", "nurse1")):
                try:
                    authorize_edit(conn, "financials", 1, role, user)
                except PermissionError:
                    pass
                else:
                    raise AssertionError(f"{role} should be refused on row 1")
            # old row: admin only, even the author
            try:
                authorize_edit(conn, "financials", 2, "doctor", "doc_a")
            except PermissionError:
                pass
            else:
                raise AssertionError("author should be refused on old row 2")
            assert authorize_edit(conn, "financials", 2, "admin", "fady") is not None
            # NULL created_at falls back to visit_date
            assert authorize_edit(conn, "financials", 3, "doctor", "doc_a") is not None
            try:
                authorize_edit(conn, "financials", 4, "doctor", "doc_a")
            except PermissionError:
                pass
            else:
                raise AssertionError("row 4 (old visit_date) should be refused")
            # NULL created_at + NULL visit_date = old
            try:
                authorize_edit(conn, "financials", 5, "doctor", "doc_a")
            except PermissionError:
                pass
            else:
                raise AssertionError("row 5 (no date at all) should be refused")
            # missing row
            try:
                authorize_edit(conn, "financials", 999, "admin", "fady")
            except LookupError:
                pass
            else:
                raise AssertionError("missing row should raise LookupError")
            # Arabic refusal message
            try:
                authorize_edit(conn, "financials", 2, "doctor", "doc_a", lang="ar")
            except PermissionError as e:
                assert "المدير" in str(e)
        finally:
            conn.close()


def test_delete_record_checked():
    with isolated_db():
        conn = get_connection()
        try:
            conn.execute("INSERT INTO patients(file_number, full_name) VALUES(1,'Test')")
            conn.execute("INSERT INTO complaints(id, patient_file, visit_date,"
                         " complaint, symptoms, created_at) VALUES(1,1,?, 'c','s',?)",
                         (TODAY, RECENT))
            conn.execute("INSERT INTO complaints(id, patient_file, visit_date,"
                         " complaint, symptoms, created_at) VALUES(2,1,?, 'c','s',?)",
                         (OLD_DATE, OLD))
            conn.execute("INSERT INTO expenses(id, date, category, description,"
                         " amount, created_at) VALUES(1,?, 'cat','d', 50,?)",
                         (TODAY, RECENT))
            conn.commit()
            # legacy clinical row, recent: any doctor may delete
            assert delete_record_checked(conn, "complaints", 1, "doctor", "doc_b") is True
            assert conn.execute("SELECT COUNT(*) c FROM complaints WHERE id=1").fetchone()["c"] == 0
            # old row: doctor refused (row stays), nurse refused, admin ok
            assert delete_record_checked(conn, "complaints", 2, "doctor", "doc_b") is False
            assert conn.execute("SELECT COUNT(*) c FROM complaints WHERE id=2").fetchone()["c"] == 1
            assert delete_record_checked(conn, "complaints", 2, "nurse", "nurse1") is False
            assert delete_record_checked(conn, "complaints", 2, "admin", "fady") is True
            # expenses are admin-only operations even when recent
            assert delete_record_checked(conn, "expenses", 1, "doctor", "doc_b") is False
            assert delete_record_checked(conn, "expenses", 1, "admin", "fady") is True
            # missing row -> False, never raises
            assert delete_record_checked(conn, "complaints", 999, "admin", "fady") is False
        finally:
            conn.close()
