"""Patient model helpers: duplicates, search, save (round 16/18/32).

Round 32: search + duplicate detection run as indexed SQL over the
stored norm columns in patient_norms (norm_*/sig_*/dig_*/rev_*),
with EXACTLY the pre-round-32 match semantics:
- Duplicate: same first + father + family (strip + casefold) is
  refused even when birth date differs; find_duplicate() -> file no.
- Search-only list: NO criteria -> [] (or just the open patient);
  with criteria, name-part substrings or ANY phone + quick text.
- Phones (round 18): digits normalized (Arabic-Indic -> 0-9),
  a leading country-code prefix or trunk 0 stripped, >=7
  significant digits match by suffix ("0791234567" found by
  "+962791234567" -- fictional sample numbers only, round 46).
- Soft delete: deleted=1, NEVER a DELETE FROM; deleted patients
  never appear in search / fetch_list_row() / find_duplicate().
- save_patient_record() builds INSERT/UPDATE from the data dict,
  raises DuplicatePatientError, refreshes norms before commit.
Pure helpers live in patient_norms, re-exported here unchanged.
"""
from datetime import datetime
from src.models.database import get_connection, init_db
from src.models.patient_norms import (  # noqa: F401  (re-exported)
    _PHONE_DIGITS, norm_name, normalize_phone, phone_digits,
    phones_match, refresh_norms)

_PHONES = ("mobile1", "mobile2", "emergency_phone")
# (sig, dig, rev) norm-column triples, in _PHONES order.
_PHONE_COLS = (("sig_p1", "dig_p1", "rev_p1"),
               ("sig_p2", "dig_p2", "rev_p2"),
               ("sig_pe", "dig_pe", "rev_pe"))


class DuplicatePatientError(Exception):
    """A patient with the same three names already exists."""

    def __init__(self, file_number):
        super().__init__(f"duplicate patient file #{file_number}")
        self.file_number = file_number


def find_duplicate(first, father, last, exclude_file=None):
    """File number of a patient with the same first/father/family
    names (normalized), or None. exclude_file skips one file (the
    patient being edited); soft-deleted rows never count."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    sql = ("SELECT file_number FROM patients WHERE norm_first=?"
           " AND norm_father=? AND norm_family=?"
           " AND COALESCE(deleted,0)=0")
    params = [norm_name(first), norm_name(father), norm_name(last)]
    if exclude_file is not None:
        sql += " AND file_number<>?"
        params.append(exclude_file)
    cur.execute(sql + " ORDER BY file_number LIMIT 1", params)
    row = cur.fetchone(); conn.close()
    return row[0] if row else None


def _has_criteria(q, first, father, grand, family, phone):
    return any((v or "").strip()
               for v in (q, first, father, grand, family, phone))


def _escape_like(s):
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _phone_condition(query, params):
    """SQL fragment (params appended) matching ANY phone column,
    faithful to phones_match(query, stored) for one stored row."""
    qd = phone_digits(query)
    if not qd:
        return "(1=0)"
    qn = normalize_phone(query)
    per_col = []
    if len(qn) >= 7:
        suffixes = [qn[i:] for i in range(len(qn))]
        for sig, dig, rev in _PHONE_COLS:
            parts = [f"({dig}<>'' AND {sig}='')", f"{sig}=?",
                     f"{rev} LIKE ? ESCAPE '\\'",
                     f"{sig} IN ({','.join('?' * len(suffixes))})"]
            params.extend([qn, _escape_like(qn[::-1]) + "%"] + suffixes)
            per_col.append("(" + " OR ".join(parts) + ")")
    else:
        for sig, dig, _rev in _PHONE_COLS:
            per_col.append(f"({dig}<>'' AND (instr({sig},?)>0"
                           f" OR instr({dig},?)>0))")
            params.extend([qn, qd])
    return "(" + " OR ".join(per_col) + ")"


def search_patients(q=None, first=None, father=None, grand=None,
                    family=None, phone=None, current_file=None,
                    limit=500):
    """Patient-list rows ({file_number, full_name, mobile1}).

    No criteria -> [] when nothing is open, else [the open patient]
    only (with the full row dict the pre-round-32 code returned).
    With criteria every given field must match (name substring,
    case-insens; phones via phones_match())."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    if not _has_criteria(q, first, father, grand, family, phone):
        if current_file is None:
            conn.close(); return []
        cur.execute("SELECT file_number, full_name, first_name,"
                    " father_name, grand_name, last_name, mobile1,"
                    " mobile2, emergency_phone, deleted FROM patients"
                    " WHERE file_number=?"
                    " AND COALESCE(deleted,0)=0 LIMIT 1",
                    (current_file,))
        row = cur.fetchone(); conn.close()
        return [dict(row)] if row else []
    where = ["COALESCE(deleted,0)=0"]; params = []
    qn = norm_name(q)
    if qn:
        phone_params = []
        phone_sql = _phone_condition(q, phone_params)
        where.append("(instr(norm_full,?)>0"
                     " OR instr(CAST(file_number AS TEXT),?)>0 OR "
                     + phone_sql + ")")
        params.extend([qn, qn] + phone_params)
    for value, col in ((first, "norm_first"), (father, "norm_father"),
                       (grand, "norm_grand"), (family, "norm_family")):
        v = norm_name(value)
        if v:
            where.append(f"instr({col},?)>0"); params.append(v)
    if phone:
        where.append(_phone_condition(phone, params))
    cur.execute("SELECT file_number, full_name, mobile1 FROM patients"
                " WHERE " + " AND ".join(where) +
                " ORDER BY file_number DESC LIMIT ?", params + [limit])
    out = [{"file_number": r[0], "full_name": r[1], "mobile1": r[2] or ""}
           for r in cur.fetchall()]
    conn.close()
    return out


def fetch_list_row(fid):
    """One patient-list row ({file_number, full_name, mobile1}) by
    file number, or None (soft-deleted -> None, never selectable).
    Lets App.select_patient() work when the search-only list does
    not currently hold that patient."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT file_number, full_name, mobile1 FROM patients WHERE file_number=? AND COALESCE(deleted, 0)=0", (fid,))
    r = cur.fetchone(); conn.close()
    return dict(r) if r else None


def fetch_patient(fid):
    """Full patient row as a dict, or None when the file does not
    exist or is soft-deleted (round 18: edit / info read path)."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE file_number=? AND COALESCE(deleted, 0)=0", (fid,))
    r = cur.fetchone(); conn.close()
    return dict(r) if r else None


def soft_delete_patient(file_number):
    """Round 18 soft delete: set deleted=1 + stamp updated_at.
    NEVER a DELETE FROM -- the patient row and every treatments /
    financials / prescriptions / scans row stay in the DB; the
    patient is only hidden. True when a live patient was deleted."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("UPDATE patients SET deleted=1, updated_at=? WHERE file_number=? AND COALESCE(deleted, 0)=0",
                (datetime.now().isoformat(), file_number))
    done = cur.rowcount > 0
    conn.commit(); conn.close()
    return done


def save_patient_record(data, current_file=None):
    """Insert (new) or update (current_file) a patient row from a
    {column: value} dict; returns the file number. The duplicate
    check runs first and raises DuplicatePatientError."""
    dup = find_duplicate(data.get("first_name", ""), data.get("father_name", ""),
                         data.get("last_name", ""), exclude_file=current_file)
    if dup is not None:
        raise DuplicatePatientError(dup)
    now = datetime.now().isoformat()
    conn = get_connection(); cur = conn.cursor()
    cols = [k for k in data if k != "file_number"]
    if current_file:
        cur.execute("UPDATE patients SET " +
                    ", ".join(f"{c}=?" for c in cols) +
                    ", updated_at=? WHERE file_number=?",
                    [data[c] for c in cols] + [now, current_file])
        fid = current_file
    else:
        cur.execute("INSERT INTO patients(" + ", ".join(cols) +
                    ", created_at, updated_at) VALUES(" +
                    ", ".join("?" * (len(cols) + 2)) + ")",
                    [data[c] for c in cols] + [now, now])
        fid = cur.lastrowid
    refresh_norms(conn, fid)
    conn.commit(); conn.close()
    return fid
