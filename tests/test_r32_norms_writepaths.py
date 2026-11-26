"""Round 32: norm columns stay correct on every write path.

(a) save_patient_record create + edit refreshes norms on the same
connection (search / duplicate see the new values immediately);
(b) sync _upsert never trusts synced norm values -- a payload with
no norm keys, and one with BOGUS norm keys, both end up with the
locally computed norms; (c) migration: a patients table WITHOUT
norm columns is upgraded by init_db (columns + indexes + backfill),
search/duplicate work, and a forced second full init is a no-op.
"""
import contextlib, sqlite3, tempfile
from pathlib import Path

import src.models.database as DBmod
from src.models.database import get_connection, init_db
from src.models.patient_norms import (NORM_COLUMNS, compute_norms,
                                      ensure_patient_norms)
from src.models.patients import (fetch_patient, find_duplicate,
                                 save_patient_record, search_patients)
from src.models.sync import _upsert

_TMP = Path(tempfile.mkdtemp(prefix="r32_norms_"))


def _cleanup(*fids):
    conn = get_connection()
    for fid in fids:
        conn.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()


def _norms(fid):
    conn = get_connection()
    row = conn.execute("SELECT " + ", ".join(NORM_COLUMNS) +
                       " FROM patients WHERE file_number=?",
                       (fid,)).fetchone()
    conn.close()
    return dict(zip(NORM_COLUMNS, row)) if row else None


def _ids(rows):
    return [r["file_number"] for r in rows]


def _data(first, father, last, mobile, grand="WpGrand"):
    return {"first_name": first, "father_name": father,
            "grand_name": grand, "last_name": last,
            "full_name": " ".join(p for p in (first, father, grand, last)
                                  if p),
            "mobile1": mobile, "mobile2": "", "emergency_phone": "",
            "birth_date_greg": "1990-05-15", "nationality": "Syrian"}


def test_save_create_and_edit_refresh_norms():
    init_db()
    fid = save_patient_record(_data("WpCreateR32", "WpDad", "WpFam",
                                    "0794111000"))
    try:
        assert _norms(fid) == compute_norms(fetch_patient(fid))
        assert _norms(fid)["sig_p1"] == "794111000"
        assert fid in _ids(search_patients(first="WpCreateR32"))
        assert fid in _ids(search_patients(phone="+962794111000"))
        assert find_duplicate("WpCreateR32", "WpDad", "WpFam") == fid
        save_patient_record(_data("WpEditedR32", "WpDad", "WpFam",
                                  "+962795666777"), current_file=fid)
        assert _norms(fid) == compute_norms(fetch_patient(fid))
        assert _norms(fid)["norm_first"] == "wpeditedr32"
        assert _norms(fid)["sig_p1"] == "962795666777"
        assert fid not in _ids(search_patients(first="WpCreateR32"))
        assert fid in _ids(search_patients(first="WpEditedR32"))
        assert fid in _ids(search_patients(phone="0795666777"))
        assert fid not in _ids(search_patients(phone="0794111000"))
        assert find_duplicate("WpEditedR32", "WpDad", "WpFam") == fid
        assert find_duplicate("WpCreateR32", "WpDad", "WpFam") is None
    finally:
        _cleanup(fid)


def test_sync_upsert_recomputes_norms():
    init_db(); conn = get_connection()
    f1, f2 = 940001, 940002
    base = {"first_name": "SyncR32", "father_name": "SyncDad",
            "grand_name": "SyncGrand", "last_name": "SyncFam",
            "full_name": "SyncR32 SyncDad SyncGrand SyncFam",
            "mobile1": "0794111222", "updated_at": "2026-01-01T00:00:00"}
    try:
        assert _upsert(conn, "patients", "file_number", f1, dict(base),
                       base["updated_at"]) == 1
        bogus = dict(base, first_name="SyncTwoR32", last_name="SyncFam2",
                     full_name="SyncTwoR32 SyncDad SyncGrand SyncFam2",
                     norm_first="BOGUS", norm_full="BOGUS", sig_p1="000",
                     rev_p1="x", updated_at="2026-01-01T00:00:00")
        assert _upsert(conn, "patients", "file_number", f2, bogus,
                       bogus["updated_at"]) == 1
        conn.commit(); conn.close()
        assert _norms(f1)["norm_first"] == "syncr32"
        assert _norms(f1)["sig_p1"] == "794111222"
        assert _norms(f2)["norm_first"] == "synctwor32"
        assert "BOGUS" not in _norms(f2).values()
        assert _norms(f2)["sig_p1"] == "794111222"
        assert f1 in _ids(search_patients(first="SyncR32"))
        assert f2 in _ids(search_patients(first="SyncTwoR32"))
        assert f2 not in _ids(search_patients(first="BOGUS"))
        assert find_duplicate("SyncTwoR32", "SyncDad", "SyncFam2") == f2
        conn = get_connection()
        upd = dict(base, mobile1="0795333444",
                   updated_at="2026-02-01T00:00:00")
        assert _upsert(conn, "patients", "file_number", f1, upd,
                       upd["updated_at"]) == 1
        conn.commit(); conn.close()
        assert _norms(f1)["sig_p1"] == "795333444"
        assert f1 in _ids(search_patients(phone="0795333444"))
        assert f1 not in _ids(search_patients(phone="0794111222"))
    finally:
        conn = get_connection(); conn.close(); _cleanup(f1, f2)


@contextlib.contextmanager
def _patched(path):
    old_db = DBmod.DB
    saved = (DBmod._INIT_KEY, DBmod._SETTINGS_CACHE, DBmod._SETTINGS_FP)
    DBmod.DB = Path(path); DBmod._INIT_KEY = None
    DBmod._SETTINGS_CACHE = None; DBmod._SETTINGS_FP = None
    try:
        yield Path(path)
    finally:
        DBmod.DB = old_db
        (DBmod._INIT_KEY, DBmod._SETTINGS_CACHE, DBmod._SETTINGS_FP) = saved


def test_migration_old_db_backfilled_and_idempotent():
    db = _TMP / "legacy" / "clinic.db"; db.parent.mkdir(parents=True)
    raw = sqlite3.connect(str(db))
    raw.execute("CREATE TABLE patients(file_number INTEGER PRIMARY KEY"
                " AUTOINCREMENT, first_name TEXT, father_name TEXT,"
                " grand_name TEXT, last_name TEXT, full_name TEXT,"
                " mobile1 TEXT, mobile2 TEXT, emergency_phone TEXT,"
                " deleted INTEGER DEFAULT 0)")
    raw.executemany("INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)", [
        (1, "Mig", "MigDad", "MigGrand", "MigFam",
         "Mig MigDad MigGrand MigFam", "0791234567", None, None, 0),
        (2, "MigDel", "MigDad", "MigGrand", "MigFam",
         "MigDel MigDad MigGrand MigFam", "0781112223", None, None, 1),
        (3, "MigAr", "MigDad", None, "MigFam", "MigAr MigDad MigFam",
         "٠٧٩١٢٣٤٥٦٧", None, None, None)])
    raw.commit(); raw.close()
    with _patched(db):
        init_db()
        conn = get_connection()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(patients)")}
        idx = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'")}
        norms = {r[0]: dict(zip(NORM_COLUMNS, r[1:])) for r in
                 conn.execute("SELECT file_number, " +
                              ", ".join(NORM_COLUMNS) + " FROM patients")}
        conn.close()
        assert set(NORM_COLUMNS) <= cols, set(NORM_COLUMNS) - cols
        assert {"idx_pat_norm_full", "idx_pat_norm_names",
                "idx_pat_sig_p1", "idx_pat_dig_p2", "idx_pat_rev_pe",
                "idx_complaints_patient_file",
                "idx_appointments_patient_file"} <= idx, idx
        assert norms[1]["norm_first"] == "mig"
        assert norms[1]["sig_p1"] == "791234567"
        assert norms[1]["rev_p1"] == "791234567"[::-1]
        assert norms[3]["sig_p1"] == "791234567"  # Arabic-Indic source
        assert 1 in _ids(search_patients(first="Mig"))
        assert 2 not in _ids(search_patients(first="MigDel"))
        assert find_duplicate("Mig", "MigDad", "MigFam") == 1
        assert find_duplicate("MigDel", "MigDad", "MigFam") is None
        DBmod._INIT_KEY = None  # force the full init body to re-run
        init_db()
        conn = get_connection()
        again = {r[0]: dict(zip(NORM_COLUMNS, r[1:])) for r in
                 conn.execute("SELECT file_number, " +
                              ", ".join(NORM_COLUMNS) + " FROM patients")}
        conn.close()
        assert again == norms, "second full init changed the norms"
        assert 1 in _ids(search_patients(phone="+962791234567"))
