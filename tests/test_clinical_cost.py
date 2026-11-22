"""Clinical cost totals: patient_totals() sums a patient's financial
rows (screenshot issue 5 — the clinical Cost section showed 0/0 for a
patient with a 500,000 / 300,000 record because nothing ever loaded
the rows into the Total/Paid boxes).
ROUND-24 SUPERSESSION: the boxes no longer show cumulative totals.
ROUND-38 SUPERSESSION: standalone payments (advance = credit) via
models.payments.save_standalone_payment, NEVER capped.
ROUND-40 RE-PIN (owner correction 2026-11-21): the headless
_FakeTab drove clinical_finance.add_fin, which is DELETED with
the round-38 payment-entry zone (ONE payment place now). These
tests call save_standalone_payment directly — the exact model
entry the R38 form used and the R40 form still uses for advances
and overpayment excess (real-form coverage: test_r40_*). The
income / net / conversion endpoints are unchanged."""
from src.models.database import init_db, get_connection, save_financial
from src.models.finance import patient_totals, doctor_income, net_income
from src.models.currency import default_currency
from src.models import payments as _pay


def _seed_patient():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,father_name,grand_name,last_name,full_name,birth_date_greg,nationality) VALUES(?,?,?,?,?,?,?)",
                ("Cost", "Test", "Grand", "Patient", "Cost Test Grand Patient", "1990-01-01", "Syrian"))
    fid = cur.lastrowid; conn.commit(); conn.close()
    return fid


def _cleanup(fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()


def _close(a, b, tol=1.0):
    return abs(a - b) <= tol


def test_patient_totals_seed():
    fid = _seed_patient()
    try:
        assert patient_totals(fid) == {"total": 0.0, "paid": 0.0, "remaining": 0.0}
        save_financial(fid, "11", 500000, 300000, "2026-11-07")
        assert patient_totals(fid) == {"total": 500000.0, "paid": 300000.0, "remaining": 200000.0}
        save_financial(fid, "12", 100000, 50000, "2026-11-07")
        assert patient_totals(fid) == {"total": 600000.0, "paid": 350000.0, "remaining": 250000.0}
    finally:
        _cleanup(fid)


def test_standalone_payments_recorded():
    """Each standalone payment saves exactly the entered amount;
    doctor income and center net grow by the payment only. Paying
    BEYOND the balance is accepted and becomes patient credit."""
    fid = _seed_patient()
    try:
        save_financial(fid, "11", 500000, 300000, "2026-11-07",
                       doctor="fady", entered_by="fady")
        assert patient_totals(fid) == {"total": 500000.0, "paid": 300000.0, "remaining": 200000.0}
        inc_before = doctor_income("fady")["paid"]
        net_before = net_income()["total_income"]
        _pay.save_standalone_payment(fid, 50000, "2026-11-08",
                                     doctor="fady", entered_by="fady")
        assert patient_totals(fid) == {"total": 500000.0, "paid": 350000.0, "remaining": 150000.0}
        assert _close(doctor_income("fady")["paid"] - inc_before, 50000), "doctor income inflated"
        assert _close(net_income()["total_income"] - net_before, 50000), "center net inflated"
        # Beyond the balance: accepted as CREDIT (remaining < 0).
        _pay.save_standalone_payment(fid, 300000, "2026-11-08",
                                     doctor="fady", entered_by="fady")
        assert patient_totals(fid) == {"total": 500000.0, "paid": 650000.0, "remaining": -150000.0}
        inc_before = doctor_income("fady")["paid"]
        _pay.save_standalone_payment(fid, 350000, "2026-11-08",
                                     doctor="fady", entered_by="fady")
        assert patient_totals(fid) == {"total": 500000.0, "paid": 1000000.0, "remaining": -500000.0}
        assert _close(doctor_income("fady")["paid"] - inc_before, 350000), "doctor income inflated"
    finally:
        _cleanup(fid)


def test_standalone_payment_in_foreign_currency():
    """Foreign-currency standalone payments convert at the entered
    rate (USD @ 15,000 SYP): USD 20 -> base paid 300,000; USD 10
    -> 450,000; a further USD 40 with no balance at all is an
    advance payment (credit), also accepted."""
    if default_currency() == "USD":
        print("SKIP foreign-currency payment test (base is USD)")
        return
    fid = _seed_patient()
    base = default_currency()
    try:
        _pay.save_standalone_payment(fid, 20, "2026-11-08", currency="USD",
                                     rate=15000, rate_date="2026-11-08",
                                     base=base, doctor="fady", entered_by="fady")
        t = patient_totals(fid)
        assert _close(t["total"], 0) and _close(t["paid"], 300000) and _close(t["remaining"], -300000), t
        _pay.save_standalone_payment(fid, 10, "2026-11-08", currency="USD",
                                     rate=15000, rate_date="2026-11-08",
                                     base=base, doctor="fady", entered_by="fady")
        t = patient_totals(fid)
        assert _close(t["paid"], 450000) and _close(t["remaining"], -450000), t
        _pay.save_standalone_payment(fid, 40, "2026-11-08", currency="USD",
                                     rate=15000, rate_date="2026-11-08",
                                     base=base, doctor="fady", entered_by="fady")
        t = patient_totals(fid)
        assert _close(t["paid"], 1050000) and _close(t["remaining"], -1050000), t
    finally:
        _cleanup(fid)
