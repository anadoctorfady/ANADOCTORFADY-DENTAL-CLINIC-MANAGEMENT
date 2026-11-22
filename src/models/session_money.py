"""Per-SESSION money for the unified clinical table (R24).

The R23 entry model stored per-TOOTH CUMULATIVE amounts and saved
only the increase over the bucket (clinical_finance.add_fin's
delta guard). That conflates a SESSION's amounts with the BUCKET's
cumulative: a session's Paid legitimately EXCEEDS its own Total
when it settles earlier debt (day 1: work 300, paid 50; day 2: new
work 400, patient pays 500), which the cumulative/delta model
cannot express -- it either refuses or silently rewrites the
bucket. The unified table therefore stores PER-SESSION amounts:
one financial row per session with exactly that session's Total /
Paid on its date + tooth. Validation is in BASE currency via
converted_amounts (foreign rows count only with a stored rate);
the stored row keeps the entry currency. <200 lines."""
from datetime import datetime
from src.models.database import get_connection, init_db
from src.models.finance_totals import converted_amounts
from src.models.currency import default_currency


def _rows(fid, exclude=()):
    """All financial row dicts of one patient minus `exclude` ids."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM financials WHERE patient_file=?", (fid,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return [r for r in rows if r.get("id") not in set(exclude or ())]


def outstanding(fid, exclude_financial_ids=()):
    """(total_sum, paid_sum) in BASE currency over the patient's
    financial rows EXCLUDING `exclude_financial_ids` (edit case)."""
    tot = paid = 0.0
    for r in _rows(fid, exclude_financial_ids):
        t_, p_, _rem = converted_amounts(r)
        tot += t_; paid += p_
    return (tot, paid)

def payment_cap(fid, new_total, exclude_financial_ids=()):
    """Maximum Paid for a session whose Total is `new_total`:
    (total_sum - paid_sum) + new_total over the OTHER rows -- a
    session may settle all earlier debt, never more than all owed.
    NOT clamped: with an overpayment/credit the raw cap is
    legitimately below new_total (even negative)."""
    total_sum, paid_sum = outstanding(fid, exclude_financial_ids)
    return (total_sum - paid_sum) + float(new_total)


def validate(fid, total, paid, exclude_financial_ids=()):
    """(ok, cap): ok iff total >= 0 and 0 <= paid <= cap + 1e-9. Round 38: with patient CREDIT (advance payments) the raw cap is
    legitimately negative -- the credit already covers the session,
    so Paid 0 must pass and the payable bound is max(cap, 0); extra
    cash goes through the standalone payment entry, never a session
    row. The RAW cap is still returned (display/tests rely on it)."""
    total = float(total); paid = float(paid)
    cap = payment_cap(fid, total, exclude_financial_ids)
    return (total >= 0 and 0.0 <= paid <= max(cap, 0.0) + 1e-9, cap)

def _insert_money(conn, fid, visit_date, tooth_key, total, paid,
                  currency, rate, rate_date, base, doctor, entered_by,
                  row_kind="session", note=""):
    """INSERT one financials row on `conn` + queue it for sync,
    EXACTLY as database.save_financial does (same columns, *_syp
    conversion, center_id from settings, updated_at now,
    queue_synced_row) but return cur.lastrowid -- save_financial
    returns only (total_syp, paid_syp), so the insert is mirrored
    here for the id. ValueError: foreign currency, no rate.
    Round 38: row_kind/note ride along ('payment' = standalone)."""
    base = base or default_currency()
    total = float(total); paid = float(paid)
    if currency == base:
        rate, total_syp, paid_syp = 1.0, total, paid
    else:
        if not rate:
            raise ValueError(f"{currency} rate required (base {base})")
        total_syp, paid_syp = total * float(rate), paid * float(rate)
    cur = conn.cursor()
    _cid = cur.execute("SELECT value FROM settings WHERE key='sync_center_id'").fetchone()
    center_id = _cid[0] if _cid else "main"
    cur.execute("""INSERT INTO financials(patient_file,tooth_number,total_cost,
        paid_amount,remaining,visit_date,currency,exchange_rate,rate_date,
        total_syp,paid_syp,remaining_syp,doctor,entered_by,center_id,updated_at,
        row_kind,note)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (fid, tooth_key, total, paid, total - paid, visit_date, currency, rate,
                 rate_date, total_syp, paid_syp, total_syp - paid_syp, doctor,
                 entered_by, center_id, datetime.now().isoformat(), row_kind, note))
    rid = cur.lastrowid
    from src.models.finance_sync import queue_synced_row
    queue_synced_row(conn, "financials", rid)
    return rid


def save_session_money(fid, visit_date, tooth_key, total, paid,
                       currency="SYP", rate=None, rate_date=None,
                       base=None, doctor=None, entered_by=None, note=""):
    """Save ONE session's money as its own financial row (tooth_key
    = normalised bucket string, "" = general); the new row id, or
    None when total == 0 and paid == 0. Caller validate()s first.
    Round 40: `note` (the entry's payment note) rides along."""
    if float(total) == 0 and float(paid) == 0:
        return None
    init_db()
    conn = get_connection()
    try:
        rid = _insert_money(conn, fid, visit_date, tooth_key, total, paid,
                            currency, rate, rate_date, base, doctor, entered_by, note=(note or "").strip())
        conn.commit(); return rid
    finally:
        conn.close()


def _delete_financials(conn, fid, ids):
    """Delete financial rows by id (patient-guarded) on `conn`;
    return the count. Sync: finance deletes are LOCAL-ONLY plain
    deletes (the protocol has no delete kind); stale PENDING
    sync_queue entries are removed so a push cannot resurrect the
    payment."""
    n = 0
    cur = conn.cursor()
    for rid in ids or ():
        cur.execute("DELETE FROM financials WHERE id=? AND patient_file=?", (rid, fid))
        n += cur.rowcount
        try:
            cur.execute("DELETE FROM sync_queue WHERE table_name='financials' AND record_id=?",
                        (f"financials:{rid}",))
        except Exception:
            pass  # no queue table / entry: the delete stands
    return n

def replace_session_money(fid, session, total, paid, currency="SYP",
                          rate=None, rate_date=None, base=None,
                          doctor=None, entered_by=None):
    """Replace a session's money: delete its financial_ids rows and
    insert ONE new row on the SESSION's date (session["date"]) with
    the session's tooth_raw, via save_session_money semantics.
    Return the new row id, or None when total == paid == 0 (old
    rows still deleted). A rate error rolls the deletes back."""
    init_db()
    conn = get_connection()
    try:
        _delete_financials(conn, fid, session.get("financial_ids") or ())
        if float(total) == 0 and float(paid) == 0:
            conn.commit(); return None
        tooth = session.get("tooth_raw", session.get("tooth", "")) or ""
        rid = _insert_money(conn, fid, session.get("date"), tooth, total, paid,
                            currency, rate, rate_date, base, doctor, entered_by)
        conn.commit(); return rid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_session_rows(fid, session):
    """Delete ONE session's rows in a single transaction; return
    {"complaints": n, "diagnoses": n, "procedures": n,
    "financials": n} (rows actually deleted).
    Complaints rule (the UI relies on this): complaints rows are
    VISIT-LEVEL -- one row carries the complaint/symptoms for every
    session of that date -- so session["complaints_id"] is deleted
    ONLY when (a) this session is the date's ONLY session (no
    diagnoses/procedures rows for this patient + date outside its
    own diagnosis_ids/procedure_ids), OR (b) the session is
    toothless in the complaints-only sense: NO diagnosis/procedure
    rows of its own. Other rows go by the session's own ids. Sync:
    clinical + finance deletes queue nothing today (plain deletes;
    finance deletes are local-only, see _delete_financials)."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    counts = {"complaints": 0, "diagnoses": 0, "procedures": 0, "financials": 0}
    try:
        date = session.get("date") or ""
        dids = list(session.get("diagnosis_ids") or ())
        pids = list(session.get("procedure_ids") or ())
        own = set(dids) | set(pids)
        others = 0
        for table in ("diagnoses", "procedures"):
            rows = cur.execute(f"SELECT id FROM {table} WHERE patient_file=? AND visit_date=?",
                               (fid, date)).fetchall()
            others += sum(1 for r in rows if r[0] not in own)
        for table, ids, key in (("diagnoses", dids, "diagnoses"),
                                ("procedures", pids, "procedures")):
            for rid in ids:
                cur.execute(f"DELETE FROM {table} WHERE id=? AND patient_file=?", (rid, fid))
                counts[key] += cur.rowcount
        counts["financials"] = _delete_financials(conn, fid, session.get("financial_ids") or ())
        cid = session.get("complaints_id")
        if cid and (others == 0 or (not dids and not pids)):
            cur.execute("DELETE FROM complaints WHERE id=? AND patient_file=?", (cid, fid))
            counts["complaints"] = cur.rowcount
        conn.commit()
        return counts
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
