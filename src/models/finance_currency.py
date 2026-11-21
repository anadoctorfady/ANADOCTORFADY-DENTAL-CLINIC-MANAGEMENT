"""Per-currency finance (Round 19, Job R19-E): RAW totals per
currency, NO conversion, so SYP and USD accounts never mix.

Which tables carry a currency column (checked against the schema
in database.py / round12_schema.py and the live DB):
- financials: YES -- `currency` (default 'SYP'); the raw amounts are
  total_cost / paid_amount / remaining, while total_syp / paid_syp /
  remaining_syp hold the CONVERTED base amounts used by the old
  (All-currencies) views, which are untouched.
- expenses: NO currency column -- every row is in the base currency.
- lab_costs: NO currency column -- every row is in the base currency.
- salary_payments: NO currency column -- base currency.
So expenses / lab / salaries contribute ONLY to the base currency's
raw totals. The column check is done live via PRAGMA, so if a
currency column is ever added to one of those tables its values are
picked up automatically.

All-currencies behaviour is NOT reimplemented here: the Finance tab
keeps calling flexible_totals() / doctor_income() exactly as before
for the "All" selection. This module only serves ONE currency.
"""
from src.models.database import get_connection, init_db
from src.models.currency import default_currency
from src.models.finance_totals import (conv_sql, converted_amounts,
                                       group_raw_amounts, unconverted_totals)  # R23: shared conversion helpers live in finance_totals

# (table, amount column, date column) for the non-financials tables.
_OTHER = (("expenses", "amount", "date"),
          ("lab_costs", "cost", "date"),
          ("salary_payments", "amount", "payment_date"))


def _norm(code, base):
    """A stored currency value -> its code (NULL/blank = base)."""
    code = (code or "").strip().upper()
    return code or base


def _has_currency_col(cur, table):
    return "currency" in [r[1] for r in cur.execute(f"PRAGMA table_info({table})")]


def currencies_present():
    """Sorted currency codes actually present across finance
    records: every distinct financials.currency, plus the base
    currency when expenses / lab_costs / salary_payments hold rows
    (they carry no currency column, so their rows ARE base rows).
    Derived from the records only -- no settings list."""
    init_db()
    base = default_currency()
    conn = get_connection(); cur = conn.cursor()
    out = set()
    for (code,) in cur.execute(
            "SELECT DISTINCT currency FROM financials"):
        out.add(_norm(code, base))
    for table, _amt, _date in _OTHER:
        if _has_currency_col(cur, table):
            for (code,) in cur.execute(
                    f"SELECT DISTINCT currency FROM {table}"):
                out.add(_norm(code, base))
        elif cur.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone():
            out.add(base)
    conn.close()
    return sorted(out)


def _rng(col, start, end):
    return (f" AND {col} BETWEEN ? AND ?", [start, end]) if start and end else ("", [])


def _other_sum(cur, table, amt, date_col, currency, base, start, end):
    """Raw sum of one non-financials table for ONE currency."""
    w, a = _rng(date_col, start, end)
    if _has_currency_col(cur, table):
        cur.execute(f"SELECT COALESCE(SUM({amt}),0) FROM {table} "
                    f"WHERE COALESCE(NULLIF(TRIM(currency),''),?) = ?" + w,
                    [base, currency] + a)
    else:
        if currency != base:
            return 0.0
        cur.execute(f"SELECT COALESCE(SUM({amt}),0) FROM {table} WHERE 1=1" + w, a)
    return float(cur.fetchone()[0] or 0)


def totals_for_currency(currency, start=None, end=None, include_lab=True,
                        include_salaries=True, include_expenses=True):
    """RAW totals for ONE currency (no conversion, ever).

    Income/debts come from financials rows in that currency using
    the ORIGINAL total_cost / paid_amount / remaining columns.
    Expenses / lab / salaries count only when `currency` is the
    base currency (they have no currency column), and only when the
    matching include flag is on -- same toggle semantics and same
    result keys as finance_totals.flexible_totals()."""
    init_db()
    base = default_currency()
    currency = _norm(currency, base)
    conn = get_connection(); cur = conn.cursor()

    def q(sql, args=()):
        cur.execute(sql, args)
        return float(cur.fetchone()[0] or 0)

    w, a = _rng("visit_date", start, end)
    match = "COALESCE(NULLIF(TRIM(currency),''),?) = ?"
    tot = q(f"SELECT COALESCE(SUM(total_cost),0) FROM financials WHERE {match}" + w,
            [base, currency] + a)
    inc = q(f"SELECT COALESCE(SUM(paid_amount),0) FROM financials WHERE {match}" + w,
            [base, currency] + a)
    debt = q(f"SELECT COALESCE(SUM(remaining),0) FROM financials WHERE {match}" + w,
             [base, currency] + a)
    exp = _other_sum(cur, "expenses", "amount", "date", currency, base, start, end)
    lab = _other_sum(cur, "lab_costs", "cost", "date", currency, base, start, end)
    sal = _other_sum(cur, "salary_payments", "amount", "payment_date",
                     currency, base, start, end)
    conn.close()
    exp = exp if include_expenses else 0.0
    sal = sal if include_salaries else 0.0
    lab = lab if include_lab else 0.0
    included = tuple(n for n, on in (("lab", include_lab),
                                     ("salaries", include_salaries),
                                     ("expenses", include_expenses)) if on)
    return {"currency": currency, "total": tot, "total_income": inc,
            "total_expenses": exp + sal, "expenses_only": exp,
            "salaries": sal, "total_lab": lab, "total_debts": debt,
            "net_income": inc - exp - sal - lab,
            "net_if_debts_collected": inc - exp - sal - lab + debt,
            "base_currency": base, "included": included}


def doctor_income_currency(username, currency, start=None, end=None):
    """One doctor's OWN income in ONE currency, RAW (original
    paid_amount etc., no conversion). Same shape and same doctor
    attribution rule as finance.doctor_income(): rows whose
    treating doctor is `username`; NULL-doctor rows are excluded."""
    init_db()
    base = default_currency()
    currency = _norm(currency, base)
    conn = get_connection(); cur = conn.cursor()
    sql = ("SELECT COALESCE(SUM(total_cost),0), COALESCE(SUM(paid_amount),0), "
           "COALESCE(SUM(remaining),0), COUNT(*) FROM financials "
           "WHERE doctor=? AND COALESCE(NULLIF(TRIM(currency),''),?) = ?")
    args = [username or "", base, currency]
    if start and end:
        sql += " AND visit_date BETWEEN ? AND ?"; args += [start, end]
    cur.execute(sql, args)
    tot, paid, rem, cnt = cur.fetchone(); conn.close()
    return {"total": float(tot), "paid": float(paid),
            "remaining": float(rem), "count": int(cnt),
            "currency": currency}


def patient_totals_by_currency(patient_file):
    """Per-currency RAW totals for ONE patient: a list of
    {currency, total, paid, remaining} (original columns, no
    conversion), one entry per currency the patient actually has
    financial rows in, ordered by currency code. Empty list when
    the patient has no financial rows at all."""
    init_db()
    base = default_currency()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""SELECT COALESCE(NULLIF(TRIM(currency),''),?) AS cur,
        COALESCE(SUM(total_cost),0), COALESCE(SUM(paid_amount),0),
        COALESCE(SUM(remaining),0) FROM financials
        WHERE patient_file=? GROUP BY cur ORDER BY cur""",
                (base, patient_file))
    rows = [{"currency": r[0], "total": float(r[1]), "paid": float(r[2]),
             "remaining": float(r[3])} for r in cur.fetchall()]
    conn.close()
    return rows
