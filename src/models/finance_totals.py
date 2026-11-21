"""Flexible finance totals (Round 12, Job 9a): the admin/doctor chooses
which cost components the displayed totals include — lab costs,
salaries, expenses — each independently toggleable, so lab alone,
lab+salaries, or everything can be seen without opening each tab.

Income and debts are always shown (they are not cost components).
Net = income - included expenses - included salaries - included lab.
Salary payments count as center expenses (owner rule), split out here
so the caller can show them separately. Role rules live in the UI:
a doctor's view never receives center components at all.
"""
from src.models.database import get_connection, init_db
from src.models.currency import latest_rate, default_currency


def _norm(code, base):
    """A stored currency value -> its code (NULL/blank = base)."""
    code = (code or "").strip().upper()
    return code or base


def normalize_tooth_key(raw):
    """Canonical financials bucket key for a tooth selection (R23):
    the comma-joined SORTED tooth numbers ('16', '16,36'); '' for an
    empty/blank selection. Rows were saved as ','.join of the chart
    selection (already sorted), so normalizing both sides makes
    '36,16' / '16, 36' the same bucket as '16,36'."""
    parts = [p.strip() for p in str(raw or "").split(",")]
    return ",".join(sorted(p for p in parts if p))


def patient_tooth_totals(patient_file, tooth):
    """Cumulative Total / Paid / Remaining for ONE patient + ONE tooth
    bucket, in the base currency (same *_syp columns and fallbacks as
    finance.patient_totals). Rows whose tooth_number normalizes to
    the same key sum together; tooth '' sums ONLY the general rows
    (empty/NULL tooth) -- the general bucket. finance.patient_totals()
    remains the sum over ALL buckets."""
    init_db()
    key = normalize_tooth_key(tooth)
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""SELECT tooth_number, total_cost, paid_amount, remaining,
        total_syp, paid_syp, remaining_syp, currency, exchange_rate
        FROM financials WHERE patient_file=?""", (patient_file,))
    cols = ("tooth_number", "total_cost", "paid_amount", "remaining",
            "total_syp", "paid_syp", "remaining_syp", "currency",
            "exchange_rate")
    tot = paid = rem = 0.0
    for raw in cur.fetchall():
        row = dict(zip(cols, raw))
        if normalize_tooth_key(row["tooth_number"]) == key:
            t_, p_, r_ = converted_amounts(row)
            tot += t_; paid += p_; rem += r_
    conn.close()
    return {"total": tot, "paid": paid, "remaining": rem}


def flexible_totals(start=None, end=None, include_lab=True,
                    include_salaries=True, include_expenses=True):
    """Admin (full-scope) totals with the chosen components included.
    Excluded components report 0.0; `included` names what is in."""
    init_db()
    base = default_currency()
    conn = get_connection(); cur = conn.cursor()

    def q(sql, args=()):
        cur.execute(sql, args)
        return float(cur.fetchone()[0] or 0)

    def rng(col):
        return (f" WHERE {col} BETWEEN ? AND ?", [start, end]) if start and end else ("", [])

    w, a = rng("visit_date")
    # R23 item 6: currency-aware conversion (conv_sql) -- a foreign
    # row with no saved rate no longer folds raw into base totals.
    inc = q("SELECT COALESCE(SUM(" + conv_sql("paid_syp", "paid_amount") + "),0) FROM financials" + w, [base, base] + a)
    debt = q("SELECT COALESCE(SUM(" + conv_sql("remaining_syp", "remaining") + "),0) FROM financials" + w, [base, base] + a)
    w, a = rng("date")
    exp = q("SELECT COALESCE(SUM(amount),0) FROM expenses" + w, a)
    lab = q("SELECT COALESCE(SUM(cost),0) FROM lab_costs" + w, a)
    w, a = rng("payment_date")
    sal = q("SELECT COALESCE(SUM(amount),0) FROM salary_payments" + w, a)
    conn.close()
    exp = exp if include_expenses else 0.0
    sal = sal if include_salaries else 0.0
    lab = lab if include_lab else 0.0
    included = tuple(n for n, on in (("lab", include_lab),
                                     ("salaries", include_salaries),
                                     ("expenses", include_expenses)) if on)
    net = inc - exp - sal - lab
    if base == "USD":
        rate, inc_usd, net_usd = 1.0, inc, net
    else:
        rate = latest_rate("USD", base)
        inc_usd = (inc / rate) if rate else None
        net_usd = (net / rate) if rate else None
    return {"total_income": inc, "total_expenses": exp + sal,
            "expenses_only": exp, "salaries": sal, "total_lab": lab,
            "total_debts": debt, "net_income": net,
            "net_if_debts_collected": net + debt,
            "total_income_usd": inc_usd, "net_usd": net_usd,
            "rate": rate, "base_currency": base, "included": included}


def conv_sql(syp_col, raw_col, prefix=""):
    """SQL expression (R23 item 6): a financial row's amount in the
    BASE currency, currency-aware. Base-currency rows use the stored
    *_syp value (raw fallback, as before). FOREIGN rows count ONLY
    when a conversion was actually stored (exchange_rate present:
    *_syp, else raw x rate) -- a foreign row with NO rate contributes
    0 here and is surfaced RAW by unconverted_totals(), never folded
    into base totals at its raw face value. Bind [base, base]."""
    p = prefix
    return (f"CASE WHEN COALESCE(NULLIF(TRIM({p}currency),''),?) = ? "
            f"THEN COALESCE({p}{syp_col},{p}{raw_col}) "
            f"WHEN {p}exchange_rate IS NOT NULL "
            f"THEN COALESCE({p}{syp_col},{p}{raw_col}*{p}exchange_rate) "
            f"ELSE 0 END")


def converted_amounts(row, base=None):
    """Python twin of conv_sql() for one row dict: (total, paid,
    remaining) in base currency; foreign + no rate -> (0, 0, 0)."""
    base = base or default_currency()
    cur = _norm(row.get("currency"), base)
    rate = row.get("exchange_rate")

    def one(syp, raw):
        raw = float(raw or 0)
        if cur == base:
            return float(syp) if syp is not None else raw
        if rate is None:
            return 0.0
        return float(syp) if syp is not None else raw * float(rate)
    return (one(row.get("total_syp"), row.get("total_cost")),
            one(row.get("paid_syp"), row.get("paid_amount")),
            one(row.get("remaining_syp"), row.get("remaining")))


def group_raw_amounts(rows):
    """Group financial row dicts by their OWN currency (R23 item 6):
    [{currency, total, paid, remaining}] RAW sums, sorted by code.
    Used by the invoice + patient report so a document is issued in
    the currency(s) the patient actually paid in -- never converted
    and never summed across currencies."""
    base = default_currency()
    groups = {}
    for r in rows or []:
        cur = _norm(r.get("currency"), base)
        g = groups.setdefault(cur, {"currency": cur, "total": 0.0,
                                    "paid": 0.0, "remaining": 0.0})
        tot = float(r.get("total_cost") or 0)
        paid = float(r.get("paid_amount") or 0)
        rem = r.get("remaining")
        g["total"] += tot; g["paid"] += paid
        g["remaining"] += float(rem) if rem is not None else tot - paid
    return [groups[k] for k in sorted(groups)]


def unconverted_totals(start=None, end=None):
    """RAW totals of foreign-currency rows that carry NO saved rate
    (exchange_rate IS NULL): excluded from every converted/base total
    (conv_sql), listed here per currency so they are visible as raw
    amounts instead of being silently dropped or folded into base."""
    init_db()
    base = default_currency()
    conn = get_connection(); cur = conn.cursor()
    w = " AND visit_date BETWEEN ? AND ?" if start and end else ""
    a = [start, end] if start and end else []
    cur.execute("""SELECT COALESCE(NULLIF(TRIM(currency),''),?) AS cur,
        COALESCE(SUM(total_cost),0), COALESCE(SUM(paid_amount),0),
        COALESCE(SUM(remaining),0) FROM financials
        WHERE exchange_rate IS NULL
        AND COALESCE(NULLIF(TRIM(currency),''),?) != ?""" + w +
        " GROUP BY cur ORDER BY cur", [base, base, base] + a)
    rows = [{"currency": r[0], "total": float(r[1]), "paid": float(r[2]),
             "remaining": float(r[3])} for r in cur.fetchall()]
    conn.close()
    return rows

