"""Round 32: patient search norms -- single source of truth.

Pure helpers (norm_name / phone_digits / normalize_phone /
phones_match) MOVED here from patients.py (patients re-exports them)
plus the stored normalized columns that let search_patients() and
find_duplicate() run as indexed SQL instead of fetchall+filter:

  norm_full / norm_first / norm_father / norm_grand / norm_family
      = norm_name() of full / first / father / grand / last name.
  For mobile1 / mobile2 / emergency_phone (suffixes p1 / p2 / pe):
      sig_* = normalize_phone(value)  (significant digits)
      dig_* = phone_digits(value)     (all digits, prefixes kept)
      rev_* = sig_* reversed          (ends-with via LIKE prefix)

ensure_patient_norms() is idempotent: it adds any missing norm
column, creates the indexes, and backfills ONLY rows whose
norm_full IS NULL (so already-migrated DBs stay cheap). It also
creates patient_file indexes on the child tables used when a
patient file is opened. refresh_norms() recomputes one row.
This module must NOT import patients.py (no circularity).
"""

def norm_name(s):
    """Name key for duplicate matching: strip + casefold."""
    return (s or "").strip().casefold()


# Arabic-Indic + Extended Arabic-Indic digits -> ASCII.
_PHONE_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
                              "01234567890123456789")


def phone_digits(s):
    """Digits of a phone string only (spaces, +, dashes dropped)."""
    return "".join(ch for ch in (s or "").translate(_PHONE_DIGITS)
                   if ch.isdigit())


def normalize_phone(s):
    """Significant digits: phone_digits() minus a leading
    country-code prefix (00-form or bare form, when more digits
    follow) and one trunk 0."""
    d = phone_digits(s)
    if d.startswith("00963") and len(d) > 12:
        d = d[5:]
    elif d.startswith("963") and len(d) > 9:
        d = d[3:]
    return d[1:] if d.startswith("0") else d


def phones_match(query, stored):
    """Phone match: with >=7 significant digits the normalized
    query must be a suffix of the normalized stored number (or vice
    versa); shorter queries fall back to a digit substring match."""
    qd, sd = phone_digits(query), phone_digits(stored)
    if not qd or not sd:
        return False
    qn, sn = normalize_phone(query), normalize_phone(stored)
    if len(qn) >= 7:
        return qn == sn or sn.endswith(qn) or qn.endswith(sn)
    return qn in sn or qd in sd


_NAME_NORMS = (("norm_full", "full_name"), ("norm_first", "first_name"),
               ("norm_father", "father_name"), ("norm_grand", "grand_name"),
               ("norm_family", "last_name"))
_PHONE_NORMS = (("p1", "mobile1"), ("p2", "mobile2"),
                ("pe", "emergency_phone"))
# Norm column -> source column it is derived from.
NORM_SOURCE = dict(_NAME_NORMS)
for _sfx, _src in _PHONE_NORMS:
    for _kind in ("sig", "dig", "rev"):
        NORM_SOURCE[f"{_kind}_{_sfx}"] = _src
NORM_COLUMNS = tuple(NORM_SOURCE)
_SOURCE_COLUMNS = ("full_name", "first_name", "father_name", "grand_name",
                   "last_name", "mobile1", "mobile2", "emergency_phone")
_CHILD_TABLES = ("complaints", "diagnoses", "procedures", "financials",
                 "prescriptions", "xrays", "appointments")


def _get(row, key):
    if row is None:
        return None
    try:
        return row.get(key)
    except AttributeError:
        try:
            return row[key]
        except Exception:
            return None


def compute_norms(row):
    """All norm columns for a mapping holding the source columns."""
    out = {norm: norm_name(_get(row, src)) for norm, src in _NAME_NORMS}
    for sfx, src in _PHONE_NORMS:
        value = _get(row, src)
        sig = normalize_phone(value)
        out[f"sig_{sfx}"] = sig
        out[f"dig_{sfx}"] = phone_digits(value)
        out[f"rev_{sfx}"] = sig[::-1]
    return out


def _table_exists(cur, name):
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table'"
                       " AND name=?", (name,)).fetchone() is not None


def _columns(cur, table):
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})")}


def refresh_norms(conn, file_number):
    """Recompute one patient's norm columns on `conn` (no commit).
    No-op (False) when the row or the norm columns do not exist --
    e.g. a minimal sync-test table -- so callers never crash."""
    cur = conn.cursor()
    if not _table_exists(cur, "patients"):
        return False
    cols = _columns(cur, "patients")
    if not set(NORM_COLUMNS) <= cols or \
            not set(_SOURCE_COLUMNS) <= cols:
        return False
    row = cur.execute("SELECT " + ", ".join(_SOURCE_COLUMNS) +
                      " FROM patients WHERE file_number=?",
                      (file_number,)).fetchone()
    if row is None:
        return False
    norms = compute_norms(dict(zip(_SOURCE_COLUMNS, row)))
    cur.execute("UPDATE patients SET " +
                ", ".join(f"{c}=?" for c in NORM_COLUMNS) +
                " WHERE file_number=?",
                [norms[c] for c in NORM_COLUMNS] + [file_number])
    return True


def ensure_patient_norms(conn):
    """Add norm columns + indexes (idempotent) and backfill rows
    whose norm_full IS NULL; also index child patient_file columns."""
    cur = conn.cursor()
    if not _table_exists(cur, "patients"):
        return
    cols = _columns(cur, "patients")
    for col in NORM_COLUMNS:
        if col not in cols:
            cur.execute(f"ALTER TABLE patients ADD COLUMN {col} TEXT")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pat_norm_full"
                " ON patients(norm_full)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pat_norm_names"
                " ON patients(norm_first, norm_father, norm_family)")
    for sfx, _src in _PHONE_NORMS:
        for kind in ("sig", "dig", "rev"):
            col = f"{kind}_{sfx}"
            cur.execute(f"CREATE INDEX IF NOT EXISTS idx_pat_{col}"
                        f" ON patients({col})")
    for table in _CHILD_TABLES:
        if _table_exists(cur, table) and \
                "patient_file" in _columns(cur, table):
            cur.execute(f"CREATE INDEX IF NOT EXISTS"
                        f" idx_{table}_patient_file"
                        f" ON {table}(patient_file)")
    rows = cur.execute("SELECT file_number, " +
                       ", ".join(_SOURCE_COLUMNS) +
                       " FROM patients WHERE norm_full IS NULL").fetchall()
    if rows:
        keys = ("file_number",) + _SOURCE_COLUMNS
        updates = []
        for r in rows:
            norms = compute_norms(dict(zip(keys, r)))
            updates.append([norms[c] for c in NORM_COLUMNS] + [r[0]])
        cur.executemany("UPDATE patients SET " +
                        ", ".join(f"{c}=?" for c in NORM_COLUMNS) +
                        " WHERE file_number=?", updates)
    conn.commit()
