"""Standalone payments + patient credit (Round 38, item 1).

A standalone payment is a financials row with row_kind='payment',
total_cost 0, paid_amount = the amount received, tooth_number ''
and NO session link. It is how a patient pays toward an existing
balance on a day with no session — and how a patient pays IN
ADVANCE: round 24's session_money.validate capped every payment
at the outstanding balance, so money offered beyond it (or with
no balance at all) was REFUSED. A standalone payment is never
capped: the excess is patient CREDIT.

Balance math (unchanged source of truth, models.finance.
patient_totals): remaining = SUM(totals) - SUM(paids) over ALL the
patient's financial rows, session and payment rows alike. A
negative remaining IS the credit — money the clinic owes the
patient — and later sessions consume it through the same sums
(session_money.validate allows Paid 0 against a negative cap).
Sync: the row is queued by _insert_money like any financial row;
row_kind/note ride inside the payload's data_json (the server stores
blobs; client pull keeps the columns the local table has)."""
from src.models.database import get_connection, init_db
from src.models.finance_totals import converted_amounts
from src.models.session_money import _insert_money


def save_standalone_payment(fid, amount, visit_date, currency="SYP",
                            rate=None, rate_date=None, base=None,
                            doctor=None, entered_by=None, note=""):
    """Record ONE standalone payment; return the new row id.

    ValueError when the amount is not a positive finite number
    (zero/negative payments stay refused — only the round-24 CAP
    on legitimate payments is gone) or when a foreign currency has
    no rate (_insert_money)."""
    amount = float(amount)
    if amount != amount or amount in (float("inf"), float("-inf")) \
            or amount <= 0:
        raise ValueError("payment amount must be a positive number")
    init_db()
    conn = get_connection()
    try:
        rid = _insert_money(conn, fid, visit_date, "", 0.0, amount,
                            currency, rate, rate_date, base, doctor,
                            entered_by, row_kind="payment",
                            note=(note or "").strip())
        conn.commit()
        return rid
    finally:
        conn.close()


def patient_payments(fid):
    """The payments-review rows for one patient, NEWEST first.

    One entry per financial row whose converted Paid is non-zero
    (session rows included — their Paid is a payment; totals-only
    rows are charges, visible in the unified table, and appear
    here only through the balances they shift). Each entry is the
    stored row dict plus:
      amount_base / balance_after — base-currency floats from
        converted_amounts; balance_after is the patient balance
        (SUM totals - SUM paids over every row) immediately after
        this row, computed chronologically (visit_date, id).
      row_kind — 'payment' (standalone) or 'session'.
    [] for a null file / no payments."""
    if not fid:
        return []
    init_db()
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM financials WHERE patient_file=?"
                    " ORDER BY visit_date, id", (fid,))
        rows = [dict(r) for r in cur.fetchall()]
    except Exception:
        rows = []
    conn.close()
    balance = 0.0
    out = []
    for r in rows:
        tot, paid, _rem = converted_amounts(r)
        balance += tot - paid
        if paid == 0:
            continue
        r["row_kind"] = (r.get("row_kind") or "session")
        r["amount_base"] = paid
        r["balance_after"] = balance
        out.append(r)
    out.reverse()
    return out
