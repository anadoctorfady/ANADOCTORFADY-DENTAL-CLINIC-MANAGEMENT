"""Round 38, item 1: advance payments / patient CREDIT.

The owner's bug: round 24 capped every payment at the patient's
outstanding balance, so money offered in advance (or beyond the
balance) was REFUSED. Round 38 model: standalone payments
(kind='payment' rows, total 0) are never capped; the excess is
patient CREDIT = negative remaining = money the clinic owes the
patient, consumed naturally by later sessions.

Scenario pinned by the brief: pay 500 advance with no sessions ->
balance -500 (credit); a session total 300 -> -200; a session
total 400 more -> +200 owed. Plus: refusal paths that remain
(zero/negative standalone amount, session overpay), debtor filter
excludes credit patients, the credit alert fires (amber does not),
doctor income counts the advance, and a sync round-trip of a
standalone payment row."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.database import get_connection, init_db
from src.models.finance import patient_totals, debtor_files
from src.models import payments, session_money


def _patient(name):
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name) VALUES(?,?)",
                (name, name))
    fid = cur.lastrowid
    conn.commit(); conn.close()
    return fid


def _session(fid, total, paid=0.0, date="2026-11-21", tooth="16"):
    return session_money.save_session_money(
        fid, date, tooth, total, paid, currency="SYP", doctor="fady",
        entered_by="fady")


def test_credit_scenario_from_the_brief():
    fid = _patient("R38 Credit")
    assert patient_totals(fid)["remaining"] == 0.0
    # 1) 500 advance, no sessions at all -> credit -500.
    payments.save_standalone_payment(fid, 500, "2026-11-21",
                                     doctor="fady", entered_by="nurse1")
    tot = patient_totals(fid)
    assert tot["total"] == 0.0 and tot["paid"] == 500.0
    assert tot["remaining"] == -500.0, tot
    # 2) a session total 300 (paid 0 — the credit covers it) -> -200.
    _session(fid, 300)
    assert patient_totals(fid)["remaining"] == -200.0
    # 3) a session total 400 more -> +200 owed.
    _session(fid, 400, date="2026-11-22")
    assert patient_totals(fid)["remaining"] == 200.0


def test_session_paid_zero_allowed_against_credit():
    fid = _patient("R38 CreditCap")
    payments.save_standalone_payment(fid, 500, "2026-11-21",
                                     doctor="fady", entered_by="fady")
    # Raw cap is negative (credit) yet Paid 0 validates (round 38);
    # any positive session Paid is still refused (extra cash goes
    # through the payment entry, not a session row).
    ok, cap = session_money.validate(fid, 300, 0)
    assert ok and cap == -200.0, (ok, cap)
    ok, _cap = session_money.validate(fid, 300, 50)
    assert not ok


def test_refusals_that_remain():
    fid = _patient("R38 Refuse")
    for bad in (0, -5, float("nan")):
        try:
            payments.save_standalone_payment(fid, bad, "2026-11-21")
            raise AssertionError(f"amount {bad} accepted")
        except ValueError:
            pass
    # Session overpay beyond balance still refused (round 24 rule) —
    # the refusal lives in validate(), which the session save path
    # (clinical_session_store.validate_money) enforces before
    # save_session_money stores anything.
    ok, cap = session_money.validate(fid, 100, 150)
    assert not ok and cap == 100.0, (ok, cap)
    assert patient_totals(fid)["remaining"] == 0.0


def test_debtor_filter_excludes_credit_patients():
    fid = _patient("R38 NotDebtor")
    payments.save_standalone_payment(fid, 100, "2026-11-21",
                                     doctor="fady", entered_by="fady")
    assert fid not in debtor_files()  # a set of file numbers


def test_credit_alert_replaces_amber():
    from src.ui.patient_alerts import patient_alerts
    fid = _patient("R38 Alert")
    payments.save_standalone_payment(fid, 250, "2026-11-21",
                                     doctor="fady", entered_by="fady")
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE file_number=?", (fid,))
    row = dict(cur.fetchone()); conn.close()
    kinds = [k for k, _m in patient_alerts(row, "en")]
    assert kinds == ["credit"], kinds
    msgs = dict(patient_alerts(row, "ar"))
    assert "250" in msgs["credit"]


def test_doctor_income_counts_advance_payment():
    from src.models.finance import doctor_income
    fid = _patient("R38 Income")
    payments.save_standalone_payment(fid, 700, "2026-11-21",
                                     doctor="doc_r38", entered_by="nurse1")
    inc = doctor_income("doc_r38", "2026-11-01", "2026-11-30")
    assert inc["paid"] == 700.0 and inc["count"] == 1, inc


def test_payments_review_rows_and_balances():
    fid = _patient("R38 Review")
    payments.save_standalone_payment(fid, 500, "2026-11-20",
                                     doctor="fady", entered_by="nurse1",
                                     note="advance")
    _session(fid, 300, paid=100, date="2026-11-21")
    rows = payments.patient_payments(fid)  # newest first
    assert [r["row_kind"] for r in rows] == ["session", "payment"], rows
    assert rows[0]["balance_after"] == -300.0  # 300 total - 600 paid
    assert rows[1]["balance_after"] == -500.0
    assert rows[1]["note"] == "advance" and rows[1]["entered_by"] == "nurse1"


def test_credit_colour_contrast():
    from src.config.theme import credit_color
    from src.ui.patient_alerts import CREDIT_BG

    def lum(hx):
        hx = hx.lstrip("#")
        r, g, b = (int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

    def ratio(a, b):
        la, lb = lum(a), lum(b)
        return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

    # Surfaces the credit colour labels: finance section + panels.
    assert ratio(credit_color(False), "#E5DAC6") >= 4.5   # light fin bg
    assert ratio(credit_color(False), "#EDE4D3") >= 4.5   # light panel
    assert ratio(credit_color(True), "#92400E") >= 4.5    # dark fin bg
    assert ratio(credit_color(True), "#26211E") >= 4.5    # dark panel
    assert ratio("#FFFFFF", CREDIT_BG) >= 4.5             # strip text
    # Distinct from the debt red and the unpaid amber in both modes.
    for dark in (False, True):
        assert credit_color(dark) not in ("#DC2626", "#F59E0B")


def test_standalone_payment_sync_round_trip():
    """A row_kind='payment' row survives the REAL client sync path:
    queue -> split_financial_queue (push item) -> server merge
    semantics (data_json fields + stored columns) -> apply pull.
    The column is row_kind, NOT kind, because the payload's 'kind'
    key is the sync record kind and pull-apply drops it."""
    import json
    from src.models.finance_sync import (apply_financial_pull,
                                         split_financial_queue)
    fid = _patient("R38 Sync")
    rid = payments.save_standalone_payment(fid, 125, "2026-11-21",
                                           doctor="fady", entered_by="fady",
                                           note="advance sync")
    conn = get_connection()
    cur = conn.execute("SELECT * FROM sync_queue WHERE table_name='financials'"
                       " AND record_id=?", (f"financials:{rid}",))
    qrow = dict(cur.fetchone())
    fin, _emp = split_financial_queue([qrow], "main")
    assert len(fin) == 1 and fin[0]["kind"] == "payment"  # sync kind
    payload = fin[0]["data_json"]
    assert payload["row_kind"] == "payment" and payload["note"] == "advance sync"
    # What the receiving client sees after the server merge:
    item = dict(payload)
    for k, v in (("record_id", fin[0]["record_id"]), ("kind", "payment"),
                 ("doctor", "fady"), ("center_id", "main"),
                 ("updated_at", fin[0]["updated_at"]), ("updated_by", "fady")):
        item.setdefault(k, v)
    conn.execute("DELETE FROM financials WHERE id=?", (rid,)); conn.commit()
    counts = apply_financial_pull(conn, {"financials": [item], "employees": []})
    conn.commit()
    assert counts["financials"] == 1, counts
    row = conn.execute("SELECT row_kind, note, paid_amount FROM financials"
                       " WHERE id=?", (rid,)).fetchone()
    conn.close()
    assert row is not None and tuple(row) == ("payment", "advance sync", 125.0)
    assert patient_totals(fid)["remaining"] == -125.0
