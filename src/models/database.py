"""SQLite core: users, settings, patients, clinical. <190 lines."""
import sqlite3, hashlib, json, os, shutil
from datetime import datetime
from pathlib import Path
from src.config.settings import DB, BACKUPS, REPORTS, XRAYS
def get_connection():
    conn = sqlite3.connect(str(DB), check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-64000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn
# init_db memo (R31): full body runs ONCE per DB file identity (resolved
# path + settings-cache fingerprint: mtime_ns + size). Any write/replace/
# delete changes it, so the next call re-runs; a missing file always runs.
_INIT_KEY = None
def _cur_key():
    fp = _settings_fp(); return None if fp is None else (os.path.realpath(str(DB)), fp)
def init_db():
    global _INIT_KEY; _k = _cur_key()
    if _k is not None and _k == _INIT_KEY: return DB
    conn = get_connection(); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE,
        password_hash TEXT, role TEXT DEFAULT 'admin', created_at TEXT)""")
    c.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS patients(file_number INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT, father_name TEXT, grand_name TEXT, last_name TEXT, full_name TEXT, birth_date_greg TEXT, birth_date_hijri TEXT, age_years INT, age_months INT, age_days INT, age_total_days INT, age_hijri_years INT, age_hijri_months INT, age_hijri_days INT, mobile1 TEXT, mobile2 TEXT, emergency_phone TEXT, address TEXT, nationality TEXT DEFAULT 'سورية', created_at TEXT, updated_at TEXT)")
    for idx, col in [("fullname", "full_name"), ("m1", "mobile1"), ("m2", "mobile2"), ("em", "emergency_phone")]:
        c.execute(f"CREATE INDEX IF NOT EXISTS idx_p_{idx} ON patients({col})")
    for col in ("current_medications TEXT DEFAULT ''", "allergies TEXT DEFAULT ''", "diseases TEXT DEFAULT ''", "deleted INTEGER DEFAULT 0"):
        try:
            c.execute(f"ALTER TABLE patients ADD COLUMN {col}")
        except Exception:
            pass
    c.execute("""CREATE TABLE IF NOT EXISTS prescriptions(
        id INTEGER PRIMARY KEY AUTOINCREMENT, patient_file INT,
        date TEXT, doctor TEXT, notes TEXT, acknowledged_warnings TEXT,
        FOREIGN KEY(patient_file) REFERENCES patients(file_number) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS prescription_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT, prescription_id INT,
        generic TEXT, brand TEXT, dose TEXT, frequency TEXT,
        duration_days TEXT, instructions TEXT,
        FOREIGN KEY(prescription_id) REFERENCES prescriptions(id) ON DELETE CASCADE)""")
    c.execute("CREATE TABLE IF NOT EXISTS reusable_phrases(id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, text TEXT, usage_count INT DEFAULT 1, last_used TEXT, is_favorite INT DEFAULT 0, UNIQUE(category,text))")
    c.execute("CREATE INDEX IF NOT EXISTS idx_phr_cat ON reusable_phrases(category, usage_count DESC)")
    try:
        c.execute("ALTER TABLE reusable_phrases ADD COLUMN specialty TEXT DEFAULT 'general'")
    except Exception:
        pass  # already exists
    # Phase 1: patient notes + specialty templates (new modules, lazy import)
    from src.models.notes import ensure_tables as _ensure_notes; from src.models.patient_norms import ensure_patient_norms as _ensure_pn
    from src.models.specialty_templates import ensure_tables as _ensure_tpl
    _ensure_notes(conn); _ensure_tpl(conn); _ensure_pn(conn)
    # Phase 4: attendance + sync queue (own modules, lazy import)
    from src.models.attendance import ensure_tables as _ea
    from src.models.sync import ensure_tables as _es
    from src.models.salaries import ensure_tables as _ens; from src.models.referrals import ensure_tables as _enr
    _ea(conn); _es(conn); _ens(conn); _enr(conn)
    c.execute("CREATE TABLE IF NOT EXISTS clipboard_history(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, copied_at TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS teeth_records(
        id INTEGER PRIMARY KEY AUTOINCREMENT, patient_file INT,
        tooth_number TEXT, tooth_type TEXT, jaw TEXT, created_at TEXT,
        FOREIGN KEY(patient_file) REFERENCES patients(file_number) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS complaints(
        id INTEGER PRIMARY KEY AUTOINCREMENT, patient_file INT,
        visit_date TEXT, complaint TEXT, symptoms TEXT,
        FOREIGN KEY(patient_file) REFERENCES patients(file_number) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS diagnoses(
        id INTEGER PRIMARY KEY AUTOINCREMENT, patient_file INT,
        visit_date TEXT, tooth_number TEXT, diagnosis TEXT,
        FOREIGN KEY(patient_file) REFERENCES patients(file_number) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS procedures(
        id INTEGER PRIMARY KEY AUTOINCREMENT, patient_file INT,
        visit_date TEXT, tooth_number TEXT, procedure_done TEXT,
        FOREIGN KEY(patient_file) REFERENCES patients(file_number) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS financials(
        id INTEGER PRIMARY KEY AUTOINCREMENT, patient_file INT,
        tooth_number TEXT, total_cost REAL DEFAULT 0, paid_amount REAL DEFAULT 0,
        remaining REAL DEFAULT 0, visit_date TEXT,
        FOREIGN KEY(patient_file) REFERENCES patients(file_number) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS xrays(
        id INTEGER PRIMARY KEY AUTOINCREMENT, patient_file INT,
        file_path TEXT, description TEXT, upload_date TEXT,
        FOREIGN KEY(patient_file) REFERENCES patients(file_number) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT, patient_file INT,
        appointment_date TEXT, appointment_time TEXT, reason TEXT,
        status TEXT DEFAULT 'قادم', created_at TEXT,
        FOREIGN KEY(patient_file) REFERENCES patients(file_number) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, category TEXT,
        description TEXT, amount REAL, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS lab_costs(
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, lab_name TEXT,
        patient_file INT, tooth_number TEXT, description TEXT, cost REAL)""")
    _ex = ("(date TEXT, from_currency TEXT DEFAULT 'USD', to_currency TEXT DEFAULT 'SYP', rate REAL, source TEXT DEFAULT 'manual', PRIMARY KEY(date, from_currency, to_currency))")
    c.execute("PRAGMA table_info(exchange_rates)")
    _cols = [r[1] for r in c.fetchall()]
    if _cols and "from_currency" not in _cols:
        c.execute("ALTER TABLE exchange_rates RENAME TO exchange_rates_old")
        c.execute("CREATE TABLE exchange_rates" + _ex)
        c.execute("INSERT OR IGNORE INTO exchange_rates(date,from_currency,to_currency,rate,source) SELECT date,'USD','SYP',rate,source FROM exchange_rates_old")
        c.execute("DROP TABLE exchange_rates_old")
    else:
        c.execute("CREATE TABLE IF NOT EXISTS exchange_rates" + _ex)
    for col, ddl in [("currency", "TEXT DEFAULT 'SYP'"), ("exchange_rate", "REAL"), ("rate_date", "TEXT"), ("total_syp", "REAL"), ("paid_syp", "REAL"), ("remaining_syp", "REAL"), ("doctor", "TEXT"), ("entered_by", "TEXT")]:
        try:
            c.execute(f"ALTER TABLE financials ADD COLUMN {col} {ddl}")
        except Exception:
            pass  # already exists
    c.execute("UPDATE financials SET total_syp=COALESCE(total_syp,total_cost), paid_syp=COALESCE(paid_syp,paid_amount), remaining_syp=COALESCE(remaining_syp,remaining) WHERE total_syp IS NULL")
    _es(conn)  # 2nd pass: sync/finance columns for tables created after phase 4 (old code: next init_db call)
    from src.models.round12_schema import ensure_round12_schema
    ensure_round12_schema(c); _ensure_pn(conn)  # R32 2nd pass: child tables exist now, so their patient_file indexes are created too
    now = datetime.now().isoformat()
    h = hashlib.sha256(b"1234").hexdigest()
    try: c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'doctor'")
    except Exception: pass  # already exists
    c.execute("UPDATE users SET role='admin' WHERE username='fady' AND (role IS NULL OR role<>'admin')")
    c.execute("INSERT OR IGNORE INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)", ("fady", h, "admin", now))
    for k, v in [("clinic_name", ""), ("language", "en"), ("theme_mode", "light"), ("default_currency", "SYP"), ("whatsapp", "+963944234456")]:
        c.execute("INSERT OR IGNORE INTO settings VALUES(?,?)", (k, v))
    conn.commit(); conn.close(); _INIT_KEY = _cur_key()
    return DB
# Settings cache (toggle speed): read once into memory; reloaded only
# when the DB file changes (mtime+size) or set_setting() writes a value.
_SETTINGS_CACHE = None; _SETTINGS_FP = None
def _settings_fp():
    try: s = DB.stat(); return (s.st_mtime_ns, s.st_size)
    except OSError: return None
def _load_settings():
    global _SETTINGS_CACHE, _SETTINGS_FP
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT key, value FROM settings")
    _SETTINGS_CACHE = {r[0]: r[1] for r in cur.fetchall()}; conn.close()
    _SETTINGS_FP = _settings_fp()
def get_setting(k, default=None):
    if _SETTINGS_CACHE is None or _settings_fp() != _SETTINGS_FP: _load_settings()
    return _SETTINGS_CACHE.get(k, default)
def set_setting(k, v):
    global _SETTINGS_CACHE, _SETTINGS_FP
    if _SETTINGS_CACHE is None or _settings_fp() != _SETTINGS_FP: _load_settings()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (k, str(v)))
    conn.commit(); conn.close()
    _SETTINGS_CACHE[k] = str(v); _SETTINGS_FP = _settings_fp()
def backup_db(custom=None):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = Path(custom) if custom else BACKUPS / f"backup_{ts}.db"
    dest.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(); conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    conn.close(); shutil.copy2(DB, dest)
    conn = get_connection()
    with open(dest.with_suffix(".sql"), "w", encoding="utf-8") as f:
        for line in conn.iterdump():
            f.write(line + "\n")
    conn.close(); return str(dest)
def restore_db(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    if p.suffix == ".db":
        shutil.copy2(p, DB); DB.touch()  # fresh mtime: init memo must re-run
    elif p.suffix == ".sql":
        if DB.exists():
            DB.unlink()
        conn = sqlite3.connect(str(DB))
        conn.executescript(p.read_text(encoding="utf-8")); conn.close()
    else:
        raise ValueError("Unsupported format")
    init_db(); return True
def save_financial(patient_file, tooth, total, paid, visit_date,
                   currency="SYP", rate=None, rate_date=None, base_currency=None,
                   doctor=None, entered_by=None, center_id=None):
    """Store payment in original currency + converted base amounts
    (total_syp/paid_syp/remaining_syp). doctor = treating doctor whose
    income this is; entered_by = who typed it (audit). Queued for sync."""
    from src.models.currency import default_currency
    base_currency = base_currency or default_currency()
    init_db()
    if currency == base_currency:
        rate, total_syp, paid_syp = 1.0, float(total), float(paid)
    else:
        if not rate:
            raise ValueError(f"{currency} rate required (base {base_currency})")
        total_syp, paid_syp = float(total) * float(rate), float(paid) * float(rate)
    conn = get_connection(); cur = conn.cursor()
    _cid = cur.execute("SELECT value FROM settings WHERE key='sync_center_id'").fetchone()
    center_id = center_id or (_cid[0] if _cid else "main")
    cur.execute("""INSERT INTO financials(patient_file,tooth_number,total_cost,
        paid_amount,remaining,visit_date,currency,exchange_rate,rate_date,
        total_syp,paid_syp,remaining_syp,doctor,entered_by,center_id,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (patient_file, tooth, total, paid, float(total) - float(paid), visit_date, currency, rate, rate_date,
         total_syp, paid_syp, total_syp - paid_syp, doctor, entered_by, center_id, datetime.now().isoformat()))
    from src.models.finance_sync import queue_synced_row
    queue_synced_row(conn, "financials", cur.lastrowid)
    conn.commit(); conn.close()
    return total_syp, paid_syp
