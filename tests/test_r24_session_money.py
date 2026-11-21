"""Round 24: per-SESSION money (models/session_money.py) + the R24
session_rows keys (models/history_money.py). Model-level, isolated
DB. Owner acceptance: day 1 work 300 paid 50; day 2 NEW work 400,
patient pays 500 (settles debt) -- must SAVE, totals 700/550/150."""
from src.models.database import get_connection, init_db
from src.models.finance import patient_totals
from src.models.history_money import session_rows
from src.models import session_money as sm
D1, D2 = "2026-11-16", "2026-11-17"

def _patient(name):
    init_db(); conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name) VALUES(?,?)", (name, name))
    fid = cur.lastrowid; conn.commit(); conn.close(); return fid

def _cleanup(fid):
    conn = get_connection(); cur = conn.cursor()
    for tbl in ("complaints", "diagnoses", "procedures", "financials"):
        cur.execute(f"DELETE FROM {tbl} WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()

def _ins(table, **kw):
    conn = get_connection(); cur = conn.cursor()
    cur.execute(f"INSERT INTO {table}({','.join(kw)}) VALUES({','.join('?' * len(kw))})", tuple(kw.values()))
    rid = cur.lastrowid; conn.commit(); conn.close(); return rid

def _clinical(fid, date, tooth, author="doc_x", created=None, complaint="Pain"):
    """One complaints + diagnoses + procedures row set; returns ids."""
    created = created or (date + "T09:00:00")
    return {"complaints": _ins("complaints", patient_file=fid, visit_date=date, complaint=complaint, symptoms="Sym", author=author, created_at=created),
            "diagnoses": _ins("diagnoses", patient_file=fid, visit_date=date, tooth_number=tooth, diagnosis="Diag", author=author, created_at=created),
            "procedures": _ins("procedures", patient_file=fid, visit_date=date, tooth_number=tooth, procedure_done="Proc", author=author, created_at=created)}

def _diag_proc(fid, date, tooth):
    return (_ins("diagnoses", patient_file=fid, visit_date=date, tooth_number=tooth, diagnosis="Diag"), _ins("procedures", patient_file=fid, visit_date=date, tooth_number=tooth, procedure_done="Proc"))

def _by_date(fid):
    return {r["date"]: r for r in session_rows(fid)}

def _count(table, where, arg):
    conn = get_connection(); n = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", (arg,)).fetchone()[0]
    conn.close(); return n

def test_cap_and_validate_arithmetic():
    fid = _patient("R24Cap")
    try:
        # Fresh patient: cap == the session's own total, no more.
        assert sm.outstanding(fid) == (0.0, 0.0)
        assert sm.payment_cap(fid, 400) == 400.0
        assert sm.validate(fid, 400, 400) == (True, 400.0)
        assert sm.validate(fid, 400, 401)[0] is False
        assert sm.validate(fid, -1, 0)[0] is False
        assert sm.validate(fid, 100, -5)[0] is False
        # Day 1: 300/50 -> outstanding debt 250 -> cap(400) = 650.
        rid = sm.save_session_money(fid, D1, "16", 300, 50)
        assert isinstance(rid, int) and rid > 0
        assert sm.outstanding(fid) == (300.0, 50.0)
        assert sm.payment_cap(fid, 400) == 650.0
        assert sm.validate(fid, 400, 500) == (True, 650.0)
        assert sm.validate(fid, 400, 650)[0] is True
        assert sm.validate(fid, 400, 651)[0] is False
        # An unrated foreign row counts 0 (patient_totals rule).
        _ins("financials", patient_file=fid, tooth_number="16", total_cost=999, paid_amount=999, remaining=0, visit_date=D1, currency="USD")
        assert sm.outstanding(fid) == (300.0, 50.0)
        # Edit case: excluding the session's own row removes it.
        assert sm.outstanding(fid, (rid,)) == (0.0, 0.0)
        assert sm.payment_cap(fid, 350, (rid,)) == 350.0
        assert sm.validate(fid, 350, 350, (rid,))[0] is True
        assert sm.validate(fid, 350, 351, (rid,))[0] is False
        # 0/0 saves nothing and returns None.
        assert sm.save_session_money(fid, D2, "16", 0, 0) is None
        assert patient_totals(fid)["total"] == 300.0
    finally:
        _cleanup(fid)

def test_acceptance_owner_scenario_end_to_end():
    fid = _patient("R24Accept")
    try:
        _clinical(fid, D1, "16"); _clinical(fid, D2, "16")
        assert sm.save_session_money(fid, D1, "16", 300, 50)
        ok, cap = sm.validate(fid, 400, 500)
        assert ok and cap == 650.0, (ok, cap)
        assert sm.save_session_money(fid, D2, "16", 400, 500)
        assert patient_totals(fid) == {"total": 700.0, "paid": 550.0, "remaining": 150.0}, patient_totals(fid)
        rows = _by_date(fid)
        # Raw per-session sums (display clamping is the UI's job).
        assert (rows[D2]["total"], rows[D2]["paid"]) == (400.0, 500.0)
        assert rows[D2]["remaining"] == -100.0
        assert (rows[D1]["total"], rows[D1]["paid"]) == (300.0, 50.0)
        assert len(rows[D1]["financial_ids"]) == len(rows[D2]["financial_ids"]) == 1
    finally:
        _cleanup(fid)

def test_session_rows_new_keys():
    fid = _patient("R24Keys")
    try:
        ids = _clinical(fid, "2026-11-10", "16", author="doc_a",
                        created="2026-11-10T08:00:00", complaint="Old")
        c2 = _ins("complaints", patient_file=fid, visit_date="2026-11-10", complaint="New", symptoms="Sym2", author="doc_b", created_at="2026-11-10T09:00:00")
        d2 = _ins("diagnoses", patient_file=fid, visit_date="2026-11-10", tooth_number="16", diagnosis="Diag2", author="doc_c", created_at="2026-11-10T10:00:00")
        mid = sm.save_session_money(fid, "2026-11-10", "16", 100, 40)
        r = _by_date(fid)["2026-11-10"]
        assert r["complaints_id"] == c2  # LATEST complaints row
        assert r["complaint"] == "Old | New"
        assert r["diagnosis_ids"] == [ids["diagnoses"], d2]
        assert r["procedure_ids"] == [ids["procedures"]]
        assert r["financial_ids"] == [mid]
        assert r["meta"]["complaint"] == ("doc_b", "2026-11-10T09:00:00")
        assert r["meta"]["diagnosis"] == ("doc_c", "2026-11-10T10:00:00")
        assert r["meta"]["procedure"] == ("doc_a", "2026-11-10T08:00:00")
        assert r["tooth_raw"] == "16" and r["tooth"] == "16"
        assert r["money_currency"] == "SYP"
        # Mixed currencies in one session -> money_currency None.
        _clinical(fid, "2026-11-12", "36")
        sm.save_session_money(fid, "2026-11-12", "36", 50, 50)
        sm.save_session_money(fid, "2026-11-12", "36", 10, 10, currency="USD", rate=15000, rate_date="2026-11-12")
        rm = _by_date(fid)["2026-11-12"]
        assert rm["money_currency"] is None and len(rm["financial_ids"]) == 2
        assert rm["total"] == 50.0 + 150000.0
        # Foreign-only session -> that currency.
        _clinical(fid, "2026-11-13", "11")
        sm.save_session_money(fid, "2026-11-13", "11", 10, 5, currency="USD", rate=15000, rate_date="2026-11-13")
        assert _by_date(fid)["2026-11-13"]["money_currency"] == "USD"
        # Toothless complaints-only session.
        cid = _ins("complaints", patient_file=fid, visit_date="2026-11-11", complaint="Checkup", symptoms="", author="doc_a", created_at="2026-11-11T09:00:00")
        rt = _by_date(fid)["2026-11-11"]
        assert rt["tooth"] == "" and rt["tooth_raw"] == ""
        assert rt["complaints_id"] == cid and rt["complaint"] == "Checkup"
        assert rt["diagnosis_ids"] == [] and rt["procedure_ids"] == []
        assert rt["financial_ids"] == [] and rt["total"] is None
        assert rt["money_currency"] is None
        assert rt["meta"]["complaint"] == ("doc_a", "2026-11-11T09:00:00")
        assert rt["meta"]["diagnosis"] is None and rt["meta"]["procedure"] is None
    finally:
        _cleanup(fid)

def test_replace_session_money():
    fid = _patient("R24Replace")
    try:
        _clinical(fid, D1, "16")
        sm.save_session_money(fid, D1, "16", 300, 50)
        session = session_rows(fid)[0]
        old_ids = list(session["financial_ids"])
        new_id = sm.replace_session_money(fid, session, 350, 50, doctor="doc_x", entered_by="doc_x")
        assert new_id and new_id not in old_ids
        # Totals move by exactly +50 total, paid unchanged.
        assert patient_totals(fid) == {"total": 350.0, "paid": 50.0, "remaining": 300.0}
        after = session_rows(fid)[0]
        assert after["financial_ids"] == [new_id]
        assert (after["total"], after["paid"]) == (350.0, 50.0)
        conn = get_connection()
        row = conn.execute("SELECT visit_date,tooth_number FROM financials WHERE id=?", (new_id,)).fetchone(); conn.close()
        assert tuple(row) == (D1, "16")  # original date + tooth kept
        # Replace with 0/0: row deleted, nothing inserted.
        assert sm.replace_session_money(fid, after, 0, 0) is None
        assert patient_totals(fid)["total"] == 0.0
        assert session_rows(fid)[0]["financial_ids"] == []
    finally:
        _cleanup(fid)

def test_delete_session_rows_shared_complaints():
    fid = _patient("R24Delete")
    try:
        ids16 = _clinical(fid, D1, "16")
        _diag_proc(fid, D1, "36")
        sm.save_session_money(fid, D1, "16", 300, 50)
        sm.save_session_money(fid, D1, "36", 200, 200)
        rows = session_rows(fid)
        assert len(rows) == 2
        s16 = [r for r in rows if r["tooth_raw"] == "16"][0]
        assert s16["complaints_id"] == ids16["complaints"]
        # Delete ONE of two same-date sessions: complaints SURVIVES.
        counts = sm.delete_session_rows(fid, s16)
        assert counts == {"complaints": 0, "diagnoses": 1, "procedures": 1, "financials": 1}, counts
        assert _count("complaints", "id=?", ids16["complaints"]) == 1
        left = session_rows(fid)
        assert len(left) == 1 and left[0]["tooth_raw"] == "36"
        assert patient_totals(fid) == {"total": 200.0, "paid": 200.0, "remaining": 0.0}
        # Delete the LAST session of the date: complaints goes too.
        counts = sm.delete_session_rows(fid, left[0])
        assert counts == {"complaints": 1, "diagnoses": 1, "procedures": 1, "financials": 1}, counts
        assert session_rows(fid) == [] and patient_totals(fid)["total"] == 0.0
        # Toothless complaints-only session: delete removes it.
        _ins("complaints", patient_file=fid, visit_date=D2, complaint="Only", symptoms="")
        s = session_rows(fid)[0]
        assert s["tooth_raw"] == "" and s["diagnosis_ids"] == []
        counts = sm.delete_session_rows(fid, s)
        assert counts == {"complaints": 1, "diagnoses": 0, "procedures": 0, "financials": 0}, counts
        assert session_rows(fid) == []
    finally:
        _cleanup(fid)
