"""Finance permissions (owner rules, 2026-11-07): admin full, doctor
own-income only, nurse no finance view - but the nurse MAY record
payments, credited to the TREATING doctor, never to who typed it."""
from datetime import date, timedelta
from src.models.database import init_db, get_connection, save_financial
from src.models.finance import doctor_income, net_income
from src.models.permissions import finance_scope, can_add_payment
from src.utils.auth import list_doctors
from src.utils.finance_gate import FinanceGate


def _setup():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO patients(first_name,father_name,grand_name,last_name,"
                    "full_name,birth_date_greg,nationality) VALUES(?,?,?,?,?,?,?)",
                    ("Fin", "Perm", "Grand", "Patient", "Fin Perm Grand Patient",
                     "1990-01-01", "Syrian"))
        fid = cur.lastrowid
        for u, r in (("doc_x", "doctor"), ("doc_y", "doctor"), ("nurse1", "nurse")):
            # local users table has no center_id (server-side only)
            cur.execute("INSERT OR IGNORE INTO users(username,password_hash,role) VALUES(?,?,?)",
                        (u, "x", r))
        conn.commit()
    finally:
        conn.close()
    return fid


def _teardown(fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    cur.execute("DELETE FROM users WHERE username IN ('doc_x','doc_y','nurse1')")
    conn.commit(); conn.close()


def test_nurse_enters_payment_credited_to_treating_doctor():
    """Nurse collects the money: income goes to doctor X, not the nurse,
    not doctor Y. Nurse may add, but has NO finance view."""
    fid = _setup()
    try:
        assert can_add_payment("nurse", "doc_x", "nurse1") is True
        assert finance_scope("nurse") == "none"
        save_financial(fid, "11", 100000, 100000, date.today().isoformat(),
                       doctor="doc_x", entered_by="nurse1")
        assert doctor_income("doc_x")["paid"] == 100000.0
        assert doctor_income("doc_y")["paid"] == 0.0
        assert doctor_income("nurse1")["paid"] == 0.0  # nurse has no income
    finally:
        _teardown(fid)


def test_doctor_own_only_and_admin_anyone():
    fid = _setup()
    try:
        assert can_add_payment("doctor", "doc_x", "doc_x") is True
        assert can_add_payment("doctor", "doc_y", "doc_x") is False
        assert can_add_payment("admin", "doc_y", "fady") is True
        assert finance_scope("doctor") == "own"
        assert finance_scope("admin") == "full"
        save_financial(fid, "11", 50000, 50000, date.today().isoformat(),
                       doctor="doc_x", entered_by="doc_x")
        assert doctor_income("doc_x")["paid"] == 50000.0
        assert doctor_income("doc_y")["paid"] == 0.0
    finally:
        _teardown(fid)


def test_null_doctor_old_record_admin_only():
    """Old rows with no doctor: excluded from every doctor's income,
    still included in the admin's center totals."""
    fid = _setup()
    try:
        before = net_income()["total_income"]
        save_financial(fid, "11", 70000, 70000, date.today().isoformat())
        assert doctor_income("doc_x")["paid"] == 0.0
        assert doctor_income("doc_y")["paid"] == 0.0
        assert net_income()["total_income"] >= before + 70000.0
    finally:
        _teardown(fid)


def test_doctor_income_day_month_period():
    fid = _setup()
    try:
        today = date.today()
        first = today.replace(day=1)
        last_month = (first - timedelta(days=1)).isoformat()
        save_financial(fid, "11", 10000, 10000, today.isoformat(), doctor="doc_x", entered_by="doc_x")
        save_financial(fid, "12", 20000, 20000, first.isoformat(), doctor="doc_x", entered_by="doc_x")
        save_financial(fid, "13", 99999, 99999, last_month, doctor="doc_x", entered_by="doc_x")
        assert doctor_income("doc_x", today.isoformat(), today.isoformat())["paid"] == 10000.0
        assert doctor_income("doc_x", first.isoformat(), today.isoformat())["paid"] == 30000.0
        assert doctor_income("doc_x")["paid"] == 129999.0
    finally:
        _teardown(fid)


def test_list_doctors_excludes_nurse():
    fid = _setup()
    try:
        docs = list_doctors()
        assert "doc_x" in docs and "doc_y" in docs and "fady" in docs
        assert "nurse1" not in docs
    finally:
        _teardown(fid)


def test_gate_still_locks_and_relocks():
    g = FinanceGate(verify_fn=lambda u, p: (u, p) == ("fady", "1234"))
    assert g.is_unlocked is False
    assert g.try_unlock("fady", "1234") is True
    g.lock()
    assert g.is_unlocked is False
