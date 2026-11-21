"""Finance: income, expenses, lab, debts, net — all in BASE currency.
Base = default_currency setting (SYP by default, changeable). <200 lines."""
from datetime import datetime
from src.models.database import get_connection, get_setting, init_db
from src.models.currency import latest_rate, default_currency
from src.models.finance_totals import conv_sql  # R23: currency-aware base conversion
def update_payment_checked(conn, financial_id, total=None, paid=None, role=None):
    """Update a payment row only if the role may edit payments (admin
    only, see permissions.can_edit_payments). True on success."""
    from src.models.permissions import can_edit_payments
    if not can_edit_payments(role):
        return False
    cur = conn.cursor()
    row = cur.execute("SELECT total_cost, paid_amount, total_syp, paid_syp FROM financials WHERE id=?",
                      (financial_id,)).fetchone()
    if not row:
        return False
    total = float(total) if total is not None else row[0]
    paid = float(paid) if paid is not None else row[1]
    cur.execute("UPDATE financials SET total_cost=?, paid_amount=?, remaining=? WHERE id=?",
                (total, paid, total - paid, financial_id))
    try:  # keep base columns in step, scaling the stored conversion by the raw change (R23: never overwrite *_syp with a foreign row's RAW amounts).
        nts = (row[2] * total / row[0]) if row[2] is not None and row[0] else row[2]
        nps = (row[3] * paid / row[1]) if row[3] is not None and row[1] else row[3]
        nrs = (nts - nps) if nts is not None and nps is not None else None
        cur.execute("UPDATE financials SET total_syp=?, paid_syp=?, remaining_syp=? WHERE id=?",
                    (nts, nps, nrs, financial_id))
    except Exception:
        pass
    try:  # keep the row syncable: bump updated_at + queue the change
        cur.execute("UPDATE financials SET updated_at=? WHERE id=?",
                    (datetime.now().isoformat(), financial_id))
        from src.models.finance_sync import queue_synced_row
        queue_synced_row(conn, "financials", financial_id)
    except Exception:
        pass
    conn.commit()
    return True
def patient_totals(patient_file):
    """Cumulative Total / Paid / Remaining for one patient, in base currency (conv_sql: foreign rows count only with a stored rate)."""
    init_db()
    base = default_currency()
    conn = get_connection(); cur = conn.cursor()
    cur.execute(f"""SELECT COALESCE(SUM({conv_sql('total_syp','total_cost')}),0),
        COALESCE(SUM({conv_sql('paid_syp','paid_amount')}),0),
        COALESCE(SUM({conv_sql('remaining_syp','remaining')}),0)
        FROM financials WHERE patient_file=?""", (base, base, base, base, base, base, patient_file))
    tot, paid, rem = cur.fetchone(); conn.close()
    return {"total": float(tot), "paid": float(paid), "remaining": float(rem)}
def debtor_files():
    """R21 item 11: {file_number} whose remaining > 0, in ONE grouped query -- the same SUM patient_totals() reports, per patient."""
    base = default_currency()
    conn = get_connection(); cur = conn.cursor()
    cur.execute(f"SELECT patient_file FROM financials GROUP BY patient_file HAVING SUM({conv_sql('remaining_syp','remaining')}) > 0", (base, base))
    out = {r[0] for r in cur.fetchall()}; conn.close(); return out
def last_treating_doctor(patient_file):
    """Doctor of the patient's most recent payment row (highest id):
    the clinical tables carry no author, so the latest financials row
    IS the visit record. Rows with no doctor are skipped."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    row = cur.execute("""SELECT doctor FROM financials WHERE patient_file=?
        AND doctor IS NOT NULL AND TRIM(doctor) != ''
        ORDER BY id DESC LIMIT 1""", (patient_file,)).fetchone()
    conn.close()
    return row[0] if row else None
def doctor_income(username, start=None, end=None):
    """One doctor's OWN income only (base currency): rows whose treating
    doctor is `username`. NULL-doctor rows are EXCLUDED (admin-only, via
    net_income()). Used by the doctor's "My income" view."""
    init_db()
    base = default_currency()
    conn = get_connection(); cur = conn.cursor()
    sql = f"""SELECT COALESCE(SUM({conv_sql('total_syp','total_cost')}),0),
        COALESCE(SUM({conv_sql('paid_syp','paid_amount')}),0),
        COALESCE(SUM({conv_sql('remaining_syp','remaining')}),0),
        COUNT(*) FROM financials WHERE doctor=?"""
    args = [base, base, base, base, base, base, username or ""]
    if start and end:
        sql += " AND visit_date BETWEEN ? AND ?"; args += [start, end]
    cur.execute(sql, args)
    tot, paid, rem, cnt = cur.fetchone(); conn.close()
    return {"total": float(tot), "paid": float(paid), "remaining": float(rem),
            "count": int(cnt)}
def net_income(start=None, end=None):
    init_db()
    base = default_currency()
    conn = get_connection(); cur = conn.cursor()
    def q(sql, args=()):
        cur.execute(sql, args)
        return cur.fetchone()[0] or 0
    inc_sql = f"SELECT COALESCE(SUM({conv_sql('paid_syp','paid_amount')}),0) FROM financials"
    debt_sql = f"SELECT COALESCE(SUM({conv_sql('remaining_syp','remaining')}),0) FROM financials"
    if start and end:
        inc = q(inc_sql + " WHERE visit_date BETWEEN ? AND ?", (base, base, start, end))
        exp = q("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE date BETWEEN ? AND ?", (start, end))
        # Salaries are center expenses (owner rule): salary_payments has
        # payment_date, NOT date - same range, own column.
        sal = q("SELECT COALESCE(SUM(amount),0) FROM salary_payments WHERE payment_date BETWEEN ? AND ?", (start, end))
        lab = q("SELECT COALESCE(SUM(cost),0) FROM lab_costs WHERE date BETWEEN ? AND ?", (start, end))
        debt = q(debt_sql + " WHERE visit_date BETWEEN ? AND ?", (base, base, start, end))
    else:
        inc = q(inc_sql, (base, base)); exp = q("SELECT COALESCE(SUM(amount),0) FROM expenses")
        sal = q("SELECT COALESCE(SUM(amount),0) FROM salary_payments")
        lab = q("SELECT COALESCE(SUM(cost),0) FROM lab_costs"); debt = q(debt_sql, (base, base))
    exp = exp + sal  # total_expenses = expenses + salary payments, everywhere
    conn.close()
    net = inc - exp - lab
    # USD equivalent: if base is USD, 1:1; else divide by USD->base rate
    if base == "USD":
        rate, inc_usd, net_usd = 1.0, inc, net
    else:
        rate = latest_rate("USD", base)
        inc_usd = (inc / rate) if rate else None
        net_usd = (net / rate) if rate else None
    return {"total_income": inc, "total_expenses": exp, "total_lab": lab,
            "total_debts": debt, "net_income": net,
            "net_if_debts_collected": net + debt,
            "total_income_usd": inc_usd, "net_usd": net_usd,
            "rate": rate, "base_currency": base}
def add_expense(date, category, description, amount, center_id=None):
    """Insert an expense (admin only - caller/UI) with center_id + updated_at, queued for sync. Returns the row id."""
    from src.models.finance_sync import queue_synced_row
    init_db()
    conn = get_connection()
    cid = center_id or get_setting("sync_center_id", "main") or "main"
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute("INSERT INTO expenses(date,category,description,amount,created_at,center_id,updated_at) VALUES(?,?,?,?,?,?,?)",
                (date, category, description, float(amount), now, cid, now))
    rid = cur.lastrowid
    queue_synced_row(conn, "expenses", rid)
    conn.commit(); conn.close()
    return rid
def add_lab_cost(date, lab_name, patient_file, description, cost, center_id=None):
    """Insert a lab cost (admin only - caller/UI) with center_id + updated_at, queued for sync. Returns the row id."""
    from src.models.finance_sync import queue_synced_row
    init_db()
    conn = get_connection()
    cid = center_id or get_setting("sync_center_id", "main") or "main"
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute("INSERT INTO lab_costs(date,lab_name,patient_file,description,cost,center_id,updated_at) VALUES(?,?,?,?,?,?,?)",
                (date, lab_name, patient_file, description, float(cost), cid, now))
    rid = cur.lastrowid
    queue_synced_row(conn, "lab_costs", rid)
    conn.commit(); conn.close()
    return rid
def per_center_totals(start=None, end=None):
    """Admin-only per-center breakdown: income, expenses (incl. salaries),
    lab, debts, net. NULL center_id counts under this device's center."""
    init_db()
    base = default_currency()
    dev = get_setting("sync_center_id", "main") or "main"
    conn = get_connection(); cur = conn.cursor()
    centers = set()
    for t in ("financials", "expenses", "lab_costs", "salary_payments"):
        try:
            centers |= {r[0] or dev for r in cur.execute(f"SELECT DISTINCT COALESCE(center_id, ?) FROM {t}", (dev,))}
        except Exception:
            pass
    out = []
    for c in sorted(centers):
        def q(sql, args=()):
            cur.execute(sql, args)
            return float(cur.fetchone()[0] or 0)
        def rng(col):
            return (f" AND {col} BETWEEN ? AND ?", [start, end]) if start and end else ("", [])
        w, a = rng("visit_date")
        inc = q(f"SELECT COALESCE(SUM({conv_sql('paid_syp','paid_amount')}),0) FROM financials WHERE COALESCE(center_id,?)=?" + w, [base, base, dev, c] + a)
        debt = q(f"SELECT COALESCE(SUM({conv_sql('remaining_syp','remaining')}),0) FROM financials WHERE COALESCE(center_id,?)=?" + w, [base, base, dev, c] + a)
        w, a = rng("date")
        exp = q("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE COALESCE(center_id,?)=?" + w, [dev, c] + a)
        lab = q("SELECT COALESCE(SUM(cost),0) FROM lab_costs WHERE COALESCE(center_id,?)=?" + w, [dev, c] + a)
        # salary_payments has payment_date, NOT date (rng("date") raised, swallowed -> salaries 0).
        w_sal, a_sal = rng("payment_date")
        try:
            sal = q("SELECT COALESCE(SUM(amount),0) FROM salary_payments WHERE COALESCE(center_id,?)=?" + w_sal, [dev, c] + a_sal)
        except Exception:
            sal = 0.0
        out.append({"center_id": c, "income": inc, "expenses": exp + sal, "salaries": sal,
                    "lab": lab, "debts": debt, "net": inc - exp - sal - lab})
    conn.close()
    return out
def debts_list():
    base = default_currency()
    conn = get_connection(); cur = conn.cursor()
    cur.execute(f"""SELECT p.file_number, p.full_name,
        COALESCE(SUM({conv_sql('total_syp','total_cost','f.')}),0) total,
        COALESCE(SUM({conv_sql('paid_syp','paid_amount','f.')}),0) paid,
        COALESCE(SUM({conv_sql('remaining_syp','remaining','f.')}),0) remain
        FROM patients p LEFT JOIN financials f ON p.file_number=f.patient_file
        GROUP BY p.file_number HAVING remain>0 ORDER BY remain DESC""",
        (base, base, base, base, base, base))
    rows = [dict(r) for r in cur.fetchall()]; conn.close()
    return rows
