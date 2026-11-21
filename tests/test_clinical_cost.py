"""Clinical cost totals: patient_totals() sums a patient's financial
rows (screenshot issue 5 — the clinical Cost section showed 0/0 for a
patient with a 500,000 / 300,000 record because nothing ever loaded
the rows into the Total/Paid boxes).
ROUND-24 SUPERSESSION: the boxes no longer show cumulative totals;
add_fin() saves the ENTERED amounts as one payment under
session_money semantics. The income / net assertions keep their
pre-R24 endpoints.
ROUND-38 SUPERSESSION: add_fin() is the standalone PAYMENT entry
(owner's restructure + advance payments): it records ONE payment
(amount only — no Total box), NEVER capped; paying beyond the
balance is patient CREDIT (negative remaining), not a refusal.
The session-entry cap refusal lives in session_money.validate /
test_r24_session_money. Income / net endpoints unchanged."""
from src.models.database import init_db, get_connection, save_financial
from src.models.finance import patient_totals, doctor_income, net_income
from src.models.currency import default_currency
from src.ui import clinical_finance as _fin
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
class _Entry:
    def __init__(self, v=""):
        self._v = str(v)
    def get(self):
        return self._v
    def delete(self, _a, _b=None):
        self._v = ""
    def insert(self, _i, v):
        self._v = str(v)
class _Var:
    def __init__(self, v=""):
        self._v = v
    def get(self):
        return self._v
class _FakeApp:
    def __init__(self, fid):
        self.current_patient = {"file_number": fid}
    def chart_teeth(self):
        return []
    def refresh_clinical(self):
        pass
class _FakeTab:
    """Headless stand-in for ClinicalTab: only what add_fin() touches
    (R38 payment entry: amount / date / note / rate widgets)."""
    def __init__(self, fid, paid, cur=None, rate=""):
        self.app = _FakeApp(fid)
        self.current_user = "fady"
        self.current_role = "admin"
        self.doctor_var = _Var("fady")
        self.e_paid = _Entry(paid)
        self.e_pay_date = _Entry("2026-11-08")
        self.e_pay_note = _Entry("")
        self.e_rate = _Entry(rate)
        self.e_rate_date = _Entry("2026-11-08")
        self.base_cur = default_currency()
        self._cur = cur or self.base_cur
    def _need(self):
        return True
    def cur_code(self):
        return self._cur
    def calc(self, _e=None):
        pass
def _run_add_fin(tab, errors):
    orig = _fin.messagebox.showerror
    _fin.messagebox.showerror = lambda *a, **k: errors.append(a)
    try:
        _fin.add_fin(tab)
    finally:
        _fin.messagebox.showerror = orig
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
def test_add_fin_records_standalone_payments():
    """ROUND-38: each Add Payment saves ONE standalone payment of
    exactly the entered amount; doctor income and center net grow
    by the payment only. Paying BEYOND the balance is accepted and
    becomes patient credit (the R24 over-cap refusal is superseded
    by the owner's advance-payment requirement)."""
    fid = _seed_patient()
    errors = []
    try:
        save_financial(fid, "11", 500000, 300000, "2026-11-07",
                       doctor="fady", entered_by="fady")
        assert patient_totals(fid) == {"total": 500000.0, "paid": 300000.0, "remaining": 200000.0}
        inc_before = doctor_income("fady")["paid"]
        net_before = net_income()["total_income"]
        _run_add_fin(_FakeTab(fid, "50000"), errors)
        assert not errors, errors
        assert patient_totals(fid) == {"total": 500000.0, "paid": 350000.0, "remaining": 150000.0}
        assert _close(doctor_income("fady")["paid"] - inc_before, 50000), "doctor income inflated"
        assert _close(net_income()["total_income"] - net_before, 50000), "center net inflated"
        # Beyond the balance: accepted as CREDIT (remaining < 0).
        _run_add_fin(_FakeTab(fid, "300000"), errors)
        assert not errors, errors
        assert patient_totals(fid) == {"total": 500000.0, "paid": 650000.0, "remaining": -150000.0}
        inc_before = doctor_income("fady")["paid"]
        _run_add_fin(_FakeTab(fid, "350000"), errors)
        assert patient_totals(fid) == {"total": 500000.0, "paid": 1000000.0, "remaining": -500000.0}
        assert _close(doctor_income("fady")["paid"] - inc_before, 350000), "doctor income inflated"
    finally:
        _cleanup(fid)
def test_add_fin_standalone_in_foreign_currency():
    """ROUND-38: foreign-currency standalone payments convert at
    the entered rate (USD @ 15,000 SYP): USD 20 -> base paid
    300,000; USD 10 -> 450,000; a further USD 40 with no balance
    at all is an advance payment (credit), also accepted."""
    if default_currency() == "USD":
        print("SKIP foreign-currency payment test (base is USD)")
        return
    fid = _seed_patient()
    errors = []
    try:
        _run_add_fin(_FakeTab(fid, "20", cur="USD", rate="15000"), errors)
        assert not errors, errors
        t = patient_totals(fid)
        assert _close(t["total"], 0) and _close(t["paid"], 300000) and _close(t["remaining"], -300000), t
        _run_add_fin(_FakeTab(fid, "10", cur="USD", rate="15000"), errors)
        t = patient_totals(fid)
        assert _close(t["paid"], 450000) and _close(t["remaining"], -450000), t
        _run_add_fin(_FakeTab(fid, "40", cur="USD", rate="15000"), errors)
        assert not errors, errors
        t = patient_totals(fid)
        assert _close(t["paid"], 1050000) and _close(t["remaining"], -1050000), t
    finally:
        _cleanup(fid)
