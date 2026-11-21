"""Item 3: fixed per-user data location + one-time legacy migration.

Simulates on Linux with monkeypatched paths / a subprocess "run":
run from fake EXE location A, add a patient, close, "move" the EXE to
location B, run again - the patient is STILL there, because the data
location no longer depends on where the EXE sits. Also covers the
one-time migration of an old next-to-EXE database (verified copy first,
old copy kept as .migrated-*.bak, never deleted, never overwriting an
existing new database, invalid legacy databases refused).
Run directly: /tmp/venv_v2/bin/python -m pytest tests/test_data_location.py
or import the module and call each test_*() (as run_tests.py does).
"""
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from src.config.settings import _data_dir, _is_valid_sqlite, migrate_legacy_data

ROOT = Path(__file__).resolve().parent.parent
HELPER = (
    "import sys; sys.path.insert(0, {root!r})\n"
    "from src.models.database import init_db, get_connection\n"
    "from src.config.settings import DB\n"
    "init_db()\n"
    "conn = get_connection(); cur = conn.cursor()\n"
    "if sys.argv[1] == 'add':\n"
    "    cur.execute(\"INSERT INTO patients(first_name, full_name) \"\n"
    "                \"VALUES(?, ?)\", ('Migration', 'Migration Test Patient'))\n"
    "    conn.commit(); print('added', cur.lastrowid)\n"
    "else:\n"
    "    cur.execute('SELECT full_name FROM patients')\n"
    "    print('patients:', [r[0] for r in cur.fetchall()])\n"
    "conn.close(); print('DB:', DB)\n"
).format(root=str(ROOT))


def _run_from(exe_dir, data_dir, action):
    env = dict(os.environ)
    env["ANADOCTORFADY_DATA_DIR"] = str(data_dir)
    env["PYTHONPATH"] = str(ROOT)
    proc = subprocess.run(
        [sys.executable, "-c", HELPER, action],
        cwd=str(exe_dir), env=env, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]
    return proc.stdout


def _seed_db(path, patient):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE patients(file_number INTEGER PRIMARY KEY,"
                 " full_name TEXT)")
    conn.execute("INSERT INTO patients(full_name) VALUES(?)", (patient,))
    conn.commit(); conn.close()


def _names(path):
    conn = sqlite3.connect(f"file:{Path(path)}?mode=ro", uri=True)
    try:
        return [r[0] for r in conn.execute("SELECT full_name FROM patients")]
    finally:
        conn.close()


def test_data_location_independent_of_exe_location():
    tmp = Path(tempfile.mkdtemp(prefix="dataloc_"))
    data, exe_a, exe_b = tmp / "data", tmp / "A", tmp / "B"
    for d in (exe_a, exe_b):
        d.mkdir(parents=True)
        (d / "ANADOCTORFADY.exe").write_text("fake exe", encoding="utf-8")
    out_a = _run_from(exe_a, data, "add")
    assert "added" in out_a, out_a
    assert f"DB: {data / 'clinic.db'}" in out_a, out_a
    out_b = _run_from(exe_b, data, "list")
    assert "Migration Test Patient" in out_b, out_b
    assert f"DB: {data / 'clinic.db'}" in out_b, out_b
    assert (data / "clinic.db").exists()
    assert not (exe_a / "anadoctorfady" / "clinic.db").exists()
    assert not (exe_b / "anadoctorfady" / "clinic.db").exists()


def test_data_dir_fixed_location():
    saved = {k: os.environ.get(k) for k in
             ("ANADOCTORFADY_DATA_DIR", "APPDATA", "XDG_CONFIG_HOME")}
    try:
        os.environ["ANADOCTORFADY_DATA_DIR"] = "/tmp/override_dir"
        os.environ.pop("APPDATA", None)
        assert str(_data_dir()) == "/tmp/override_dir"
        os.environ.pop("ANADOCTORFADY_DATA_DIR", None)
        os.environ["APPDATA"] = "/tmp/appdata_dir"
        assert str(_data_dir()) == "/tmp/appdata_dir/ANADOCTORFADY"
        os.environ.pop("APPDATA", None)
        os.environ["XDG_CONFIG_HOME"] = "/tmp/xdg_dir"
        assert str(_data_dir()) == "/tmp/xdg_dir/ANADOCTORFADY"
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_migration_moves_old_db_and_keeps_backup():
    tmp = Path(tempfile.mkdtemp(prefix="migrate_"))
    legacy, new = tmp / "old_exe" / "anadoctorfady", tmp / "new_data"
    _seed_db(legacy / "clinic.db", "Legacy Patient")
    (legacy / "reports").mkdir(parents=True)
    (legacy / "reports" / "report1.txt").write_text("old report",
                                                    encoding="utf-8")
    res = migrate_legacy_data(str(legacy), str(new))
    assert res["migrated"] is True, res
    assert (new / "clinic.db").exists()
    assert "Legacy Patient" in _names(new / "clinic.db")
    assert not (legacy / "clinic.db").exists(), "old DB must be moved away"
    kept = list(legacy.glob("clinic.db.migrated-*.bak"))
    assert len(kept) == 1, "old copy kept as .bak, never deleted"
    assert "Legacy Patient" in _names(kept[0])
    assert (new / "reports" / "report1.txt").read_text() == "old report"
    _seed_db(legacy / "clinic.db", "Second Legacy Patient")
    res2 = migrate_legacy_data(str(legacy), str(new))
    assert res2["migrated"] is False and res2["reason"] == "new_db_exists", res2
    assert _names(new / "clinic.db") == ["Legacy Patient"]


def test_migration_never_overwrites_existing_new_db():
    tmp = Path(tempfile.mkdtemp(prefix="migrate_keep_"))
    legacy, new = tmp / "old" / "anadoctorfady", tmp / "new"
    _seed_db(legacy / "clinic.db", "Old Patient")
    _seed_db(new / "clinic.db", "Current Patient")
    res = migrate_legacy_data(str(legacy), str(new))
    assert res["migrated"] is False and res["reason"] == "new_db_exists", res
    assert _names(new / "clinic.db") == ["Current Patient"]
    assert _names(legacy / "clinic.db") == ["Old Patient"]


def test_migration_refuses_invalid_legacy_db():
    tmp = Path(tempfile.mkdtemp(prefix="migrate_bad_"))
    legacy, new = tmp / "old" / "anadoctorfady", tmp / "new"
    (legacy).mkdir(parents=True)
    (legacy / "clinic.db").write_bytes(b"This is not a SQLite database.")
    res = migrate_legacy_data(str(legacy), str(new))
    assert res["migrated"] is False and res["reason"] == "legacy_db_invalid", res
    assert not (new / "clinic.db").exists()


def test_migration_ignores_empty_placeholder_db():
    tmp = Path(tempfile.mkdtemp(prefix="migrate_empty_"))
    legacy, new = tmp / "old" / "anadoctorfady", tmp / "new"
    legacy.mkdir(parents=True)
    (legacy / "clinic.db").write_bytes(b"")  # stray 0-byte file, not a DB
    res = migrate_legacy_data(str(legacy), str(new))
    assert res["migrated"] is False and res["reason"] == "no_legacy_db", res
    assert not (new / "clinic.db").exists()


def test_is_valid_sqlite():
    tmp = Path(tempfile.mkdtemp(prefix="validsqlite_"))
    good = tmp / "good.db"
    _seed_db(good, "Someone")
    assert _is_valid_sqlite(good) is True
    bad = tmp / "bad.db"
    bad.write_bytes(b"not sqlite at all, just text........")
    assert _is_valid_sqlite(bad) is False
    empty = tmp / "empty.db"
    empty.write_bytes(b"")
    assert _is_valid_sqlite(empty) is False
    assert _is_valid_sqlite(tmp / "missing.db") is False
