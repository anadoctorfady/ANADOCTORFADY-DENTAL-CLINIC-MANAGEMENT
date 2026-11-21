"""Round 19 (R19-E): per-currency finance view.

Seeds financials in SYP + USD for one patient (USD rate 10000
SYP/USD, base SYP), plus an expense and a lab cost. NOTE on the
expense/lab rows: expenses and lab_costs carry NO currency column
(verified against the schema), so they are base-currency (SYP)
records by definition -- the tests assert they count in the SYP
raw totals and are EXCLUDED from the USD raw totals (accounts
must not mix). Assertions:

- totals_for_currency() returns EXACT raw sums per currency.
- The All view (flexible_totals / doctor_income, the pre-change
  functions) is unchanged for the same seed: converted totals.
- doctor_income_currency() filters by treating doctor + currency.
- currencies_present() derives from the records (USD appears
  only after the first USD record is seeded).
- patient_totals_by_currency() splits one patient per currency.
- GUI: the FinanceTab selector switches the cards All <-> USD raw.
"""
from datetime import date, datetime

from src.models.database import get_connection, init_db, save_financial
from src.models.finance import doctor_income
from src.models.finance_currency import (currencies_present,
                                         doctor_income_currency,
                                         patient_totals_by_currency,
                                         totals_for_currency)
from src.models.finance_totals import flexible_totals

TODAY = date.today().isoformat()
RATE = 10000.0  # SYP per 1 USD for the seeded USD row
DOC = "r19doc"
EXP_AMT, LAB_AMT = 40000.0, 10000.0


def _setup():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name) VALUES(?,?)",
                ("R19Cur", "R19Cur Currency"))
    fid = cur.lastrowid
    cur.execute("INSERT INTO expenses(date,category,description,amount,created_at)"
                " VALUES(?,?,?,?,?)", (TODAY, "Materials", "r19-exp", EXP_AMT,
                                       datetime.now().isoformat()))
    exp_id = cur.lastrowid
    cur.execute("INSERT INTO lab_costs(date,lab_name,description,cost,created_at)"
                " VALUES(?,?,?,?,?)", (TODAY, "Lab", "r19-lab", LAB_AMT,
                                       datetime.now().isoformat()))
    lab_id = cur.lastrowid
    conn.commit(); conn.close()
    # SYP: total 500000, paid 300000. USD: total 200, paid 50
    # (converted: total 2,000,000 SYP, paid 500,000 SYP).
    save_financial(fid, "11", 500000, 300000, TODAY, currency="SYP",
                   doctor=DOC, entered_by=DOC)
    save_financial(fid, "12", 200, 50, TODAY, currency="USD", rate=RATE,
                   rate_date=TODAY, doctor=DOC, entered_by=DOC)
    return fid, exp_id, lab_id


def _teardown(fid, exp_id, lab_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    cur.execute("DELETE FROM expenses WHERE id=?", (exp_id,))
    cur.execute("DELETE FROM lab_costs WHERE id=?", (lab_id,))
    conn.commit(); conn.close()


def test_currency_list_derives_from_records():
    before = currencies_present()
    assert "USD" not in before  # gate copy holds SYP rows only
    fid, e, l = _setup()
    try:
        after = currencies_present()
        assert "USD" in after and "SYP" in after
        assert after == sorted(after)
    finally:
        _teardown(fid, e, l)


def test_per_currency_raw_totals_exact():
    b_usd = totals_for_currency("USD", TODAY, TODAY)
    b_syp = totals_for_currency("SYP", TODAY, TODAY)
    fid, e, l = _setup()
    try:
        usd = totals_for_currency("USD", TODAY, TODAY)
        assert usd["total"] - b_usd["total"] == 200.0
        assert usd["total_income"] - b_usd["total_income"] == 50.0
        assert usd["total_debts"] - b_usd["total_debts"] == 150.0
        # No conversion and NO base-currency expense/lab leakage:
        assert usd["total_expenses"] - b_usd["total_expenses"] == 0.0
        assert usd["total_lab"] - b_usd["total_lab"] == 0.0
        assert usd["net_income"] - b_usd["net_income"] == 50.0
        assert usd["currency"] == "USD"
        syp = totals_for_currency("SYP", TODAY, TODAY)
        assert syp["total"] - b_syp["total"] == 500000.0
        assert syp["total_income"] - b_syp["total_income"] == 300000.0
        assert syp["total_debts"] - b_syp["total_debts"] == 200000.0
        assert syp["expenses_only"] - b_syp["expenses_only"] == EXP_AMT
        assert syp["total_lab"] - b_syp["total_lab"] == LAB_AMT
        assert syp["net_income"] - b_syp["net_income"] == \
            300000.0 - EXP_AMT - LAB_AMT
    finally:
        _teardown(fid, e, l)


def test_all_view_unchanged_converted():
    """All = the pre-change converted view: flexible_totals() on
    the same seed converts the USD row at its stored rate."""
    before = flexible_totals(TODAY, TODAY)
    fid, e, l = _setup()
    try:
        after = flexible_totals(TODAY, TODAY)
        assert after["total_income"] - before["total_income"] == \
            300000.0 + 50.0 * RATE
        assert after["total_debts"] - before["total_debts"] == \
            200000.0 + 150.0 * RATE
        assert after["expenses_only"] - before["expenses_only"] == EXP_AMT
        assert after["total_lab"] - before["total_lab"] == LAB_AMT
        assert after["net_income"] - before["net_income"] == \
            300000.0 + 50.0 * RATE - EXP_AMT - LAB_AMT
    finally:
        _teardown(fid, e, l)


def test_doctor_income_per_currency():
    fid, e, l = _setup()
    try:
        usd = doctor_income_currency(DOC, "USD", TODAY, TODAY)
        assert usd["total"] == 200.0 and usd["paid"] == 50.0
        assert usd["remaining"] == 150.0 and usd["count"] == 1
        syp = doctor_income_currency(DOC, "SYP", TODAY, TODAY)
        assert syp["total"] == 500000.0 and syp["paid"] == 300000.0
        assert syp["remaining"] == 200000.0 and syp["count"] == 1
        # All view for the same doctor stays converted (base sums):
        assert doctor_income(DOC, TODAY, TODAY)["paid"] == \
            300000.0 + 50.0 * RATE
        other = doctor_income_currency("nobody_r19", "USD", TODAY, TODAY)
        assert other["paid"] == 0.0 and other["count"] == 0
    finally:
        _teardown(fid, e, l)


def test_patient_totals_by_currency():
    fid, e, l = _setup()
    try:
        rows = patient_totals_by_currency(fid)
        assert [r["currency"] for r in rows] == ["SYP", "USD"]
        syp, usd = rows
        assert (syp["total"], syp["paid"], syp["remaining"]) == \
            (500000.0, 300000.0, 200000.0)
        assert (usd["total"], usd["paid"], usd["remaining"]) == \
            (200.0, 50.0, 150.0)
        assert patient_totals_by_currency(99999999) == []
    finally:
        _teardown(fid, e, l)


