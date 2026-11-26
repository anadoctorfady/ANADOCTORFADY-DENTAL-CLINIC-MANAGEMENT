"""Round 49 (Section F): ADMIN-ONLY date editing.
(a) Admin moves a session's date through the real edit save (entry
date box -> store.update_clinical -> edit.change_session_date):
dates change, updated_at bumped, History order follows, totals
identical. (b) Doctor/nurse via the guarded path: PermissionError,
nothing moves — also when a doctor force-enables the GUI box.
(c) Admin moves a STANDALONE payment's date: running balances
re-derive in the new order, totals unchanged; session-linked +
non-admin refused. (d) Invalid dates rejected on both paths.
(e) GUI: date entry ENABLED for admin, DISABLED for doctor; tooth
disabled for both. Helpers from test_r24_unified_table."""
import tkinter as tk
from datetime import datetime

from src.models import payments as _pay
from src.models import session_money as _sm
from src.models.database import get_connection
from src.models.finance import patient_totals
from src.models.history_money import session_rows
from src.ui import clinical_session_edit as _edit
from tests.test_r24_unified_table import (
    D1, _build, _cleanup, _patient, _patch_msgs, _save_session)

D0, D2, D3 = "2026-11-10", "2026-11-17", "2026-11-20"
OLD_TS = "2000-01-01T00:00:00"


def _seed_session(fid, date, author="doc_a", total=300, paid=50):
    """One complete fresh session (clinical rows + money), direct."""
    now = datetime.now().isoformat()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO complaints(patient_file,visit_date,complaint,symptoms,author,created_at) VALUES(?,?,?,?,?,?)", (fid, date, "Pain", "Sym", author, now))
    cur.execute("INSERT INTO diagnoses(patient_file,visit_date,tooth_number,diagnosis,author,created_at) VALUES(?,?,?,?,?,?)", (fid, date, "16", "Pulpitis", author, now))
    cur.execute("INSERT INTO procedures(patient_file,visit_date,tooth_number,procedure_done,author,created_at) VALUES(?,?,?,?,?,?)", (fid, date, "16", "Root canal", author, now))
    conn.commit(); conn.close()
    if total or paid:
        _sm.save_session_money(fid, date, "16", total, paid)


def _dates(fid, table):
    conn = get_connection()
    out = [r[0] for r in conn.execute(f"SELECT visit_date FROM {table} WHERE patient_file=? ORDER BY id", (fid,))]
    conn.close(); return out


def _fin_ts(fid, date):
    conn = get_connection()
    row = conn.execute("SELECT updated_at FROM financials WHERE patient_file=? AND visit_date=?", (fid, date)).fetchone()
    conn.close(); return row[0] if row else None


def _age_financials(fid):
    conn = get_connection(); conn.execute("UPDATE financials SET updated_at=? WHERE patient_file=?", (OLD_TS, fid))
    conn.commit(); conn.close()


def test_admin_edits_session_date_via_gui_save():
    fid = _patient("R49AdminDate")
    caps, restore = _patch_msgs()
    root, tab = _build(user="boss", role="admin", fid=fid)
    if tab is None:
        print("SKIP r49 admin date (no display)"); restore(); _cleanup(fid); return
    try:
        _save_session(tab, D1, "16", 300, 50)
        _save_session(tab, D2, "36", 400, 100)
        before = patient_totals(fid)
        assert before == {"total": 700.0, "paid": 150.0, "remaining": 550.0}
        _age_financials(fid)
        idx = [i for i, s in enumerate(tab._history_sessions) if s["date"] == D1][0]
        tab.tree_history.selection_set(tab.tree_history.get_children()[idx])
        assert _edit.start_edit(tab) is True
        assert str(tab.e_sess_date.cget("state")) == "normal"  # admin: editable
        tab.e_sess_date.delete(0, tk.END); tab.e_sess_date.insert(0, D3)
        tab.btn_save_visit.invoke()
        assert not caps["error"], caps["error"]
        rows = session_rows(fid)
        assert [r["date"] for r in rows] == [D3, D2]  # history follows new date
        assert (rows[0]["total"], rows[0]["paid"]) == (300.0, 50.0)
        assert _dates(fid, "diagnoses") == [D3, D2]
        assert _dates(fid, "procedures") == [D3, D2]
        assert _dates(fid, "complaints") == [D3, D2]
        assert sorted(_dates(fid, "financials")) == [D2, D3]  # money row re-inserted on replace
        assert _fin_ts(fid, D3) > OLD_TS  # updated_at bumped for sync
        assert patient_totals(fid) == before  # totals byte-identical
    finally:
        root.destroy(); restore(); _cleanup(fid)


def test_doctor_and_nurse_date_change_refused():
    fid = _patient("R49Refused")
    _seed_session(fid, D1)
    try:
        for role in ("doctor", "nurse"):
            try:
                _edit.change_session_date(fid, session_rows(fid)[0], D3, role)
                raise AssertionError(f"{role} date change was not refused")
            except PermissionError: pass
            assert session_rows(fid)[0]["date"] == D1
            assert _dates(fid, "financials") == [D1]
        session = session_rows(fid)[0]  # admin CAN use the same path
        assert _edit.change_session_date(fid, session, D3, "admin") is True
        assert session["date"] == D3 and session_rows(fid)[0]["date"] == D3
        assert patient_totals(fid) == {"total": 300.0, "paid": 50.0, "remaining": 250.0}
    finally:
        _cleanup(fid)


def test_doctor_force_enabled_gui_date_still_refused():
    fid = _patient("R49ForceGui")
    caps, restore = _patch_msgs()
    root, tab = _build(user="doc_a", role="doctor", fid=fid)
    if tab is None:
        print("SKIP r49 force gui (no display)"); restore(); _cleanup(fid); return
    try:
        _save_session(tab, D1, "16", 300, 50)  # authored by doc_a, fresh
        before = patient_totals(fid)
        tab.tree_history.selection_set(tab.tree_history.get_children()[0])
        assert _edit.start_edit(tab) is True
        assert str(tab.e_sess_date.cget("state")) == "disabled"
        tab.e_sess_date.config(state="normal")  # force the widget open
        tab.e_sess_date.delete(0, tk.END); tab.e_sess_date.insert(0, D3)
        tab.btn_save_visit.invoke()  # guard raises inside the save
        assert _dates(fid, "diagnoses") == [D1]  # nothing moved
        assert _dates(fid, "financials") == [D1]
        assert patient_totals(fid) == before
    finally:
        root.destroy(); restore(); _cleanup(fid)


def test_admin_edits_standalone_payment_date():
    fid = _patient("R49PayDate")
    try:
        sess_id = _sm.save_session_money(fid, D1, "16", 300, 50)
        _pay.save_standalone_payment(fid, 50, D0, doctor="doc_a", entered_by="doc_a")
        late_id = _pay.save_standalone_payment(fid, 100, D2, doctor="doc_a", entered_by="doc_a")
        before = patient_totals(fid)
        assert before == {"total": 300.0, "paid": 200.0, "remaining": 100.0}
        rows = _pay.patient_payments(fid)  # newest first
        assert [(r["visit_date"], r["balance_after"]) for r in rows] == [(D2, 100.0), (D1, 200.0), (D0, -50.0)]
        _age_financials(fid)
        # Move the D2 standalone payment BEFORE D0: balances re-derive.
        assert _pay.change_payment_date(fid, late_id, "2026-11-09", "admin") is True
        rows = _pay.patient_payments(fid)
        assert [(r["visit_date"], r["balance_after"]) for r in rows] == [(D1, 100.0), (D0, -150.0), ("2026-11-09", -100.0)]
        assert _fin_ts(fid, "2026-11-09") > OLD_TS
        assert patient_totals(fid) == before  # totals unchanged
        for role in ("doctor", "nurse"):  # non-admin refused
            try:
                _pay.change_payment_date(fid, late_id, D2, role)
                raise AssertionError(f"{role} payment date change not refused")
            except PermissionError: pass
        try:  # session-linked row refused: its date follows the session
            _pay.change_payment_date(fid, sess_id, D2, "admin")
            raise AssertionError("session-linked payment date was editable")
        except ValueError: pass
        assert _dates(fid, "financials") == [D1, D0, "2026-11-09"]
        assert patient_totals(fid) == before
    finally:
        _cleanup(fid)


def test_invalid_dates_rejected_both_paths():
    fid = _patient("R49BadDate")
    _seed_session(fid, D1)
    try:
        pid = _pay.save_standalone_payment(fid, 40, D1, doctor="doc_a", entered_by="doc_a")
        for bad in ("2026-13-40", "2026-1-05", "not-a-date", "", "2026-11-16 "):
            try:
                _edit.change_session_date(fid, session_rows(fid)[0], bad, "admin")
                raise AssertionError(f"session accepted bad date {bad!r}")
            except ValueError: pass
            try:
                _pay.change_payment_date(fid, pid, bad, "admin")
                raise AssertionError(f"payment accepted bad date {bad!r}")
            except ValueError: pass
        assert session_rows(fid)[0]["date"] == D1
        row = [r for r in _pay.patient_payments(fid) if r["id"] == pid][0]
        assert row["visit_date"] == D1
    finally:
        _cleanup(fid)


def test_gui_date_widget_enabled_admin_disabled_doctor():
    fid = _patient("R49Widget")
    _seed_session(fid, D1, author="doc_a")
    caps, restore = _patch_msgs()
    try:
        for user, role, want in (("boss", "admin", "normal"), ("doc_a", "doctor", "disabled")):
            root, tab = _build(user=user, role=role, fid=fid)
            if tab is None:
                print("SKIP r49 widget (no display)"); return
            try:
                tab.tree_history.selection_set(tab.tree_history.get_children()[0])
                assert _edit.start_edit(tab) is True
                assert str(tab.e_sess_date.cget("state")) == want, (role, tab.e_sess_date.cget("state"))
                assert str(tab.e_sess_tooth.cget("state")) == "disabled"  # tooth fixed for all
            finally:
                root.destroy()
    finally:
        restore(); _cleanup(fid)
