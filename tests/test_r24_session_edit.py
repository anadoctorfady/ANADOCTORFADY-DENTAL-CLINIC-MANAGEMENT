"""Round 24 (items 2+6): unified session EDIT / DELETE permission
matrix. Edit loads the session into the entry (date + tooth fixed);
money edits/deletes additionally require finance.edit_amounts --
without it the money boxes are locked and a money-bearing session
cannot be deleted; clinical edits follow edit_rules.check_record
(admin always; author doctor <= 24h; nurse never). Helpers are
shared from tests/test_r24_unified_table.py. Isolated DB."""
from datetime import datetime, timedelta

import tkinter as tk

from src.models.database import get_connection
from src.models.finance import patient_totals
from src.models.history_money import session_rows
from src.models.permissions import grant_perm, revoke_perm
from src.ui import clinical_session_delete as _del
from src.ui import clinical_session_edit as _edit
from src.ui import clinical_session_entry as _entry
from tests.test_r24_unified_table import (
    D1, _build, _cleanup, _count, _patient, _patch_msgs, _save_session)


def _seed_old_session(fid, author="doc_b", days_ago=2):
    """A complete session created `days_ago` by `author`, with money."""
    from src.models import session_money as sm
    date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    created = (datetime.now() - timedelta(days=days_ago)).isoformat()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO complaints(patient_file,visit_date,complaint,symptoms,author,created_at) VALUES(?,?,?,?,?,?)",
                (fid, date, "Old pain", "Old sym", author, created))
    cur.execute("INSERT INTO diagnoses(patient_file,visit_date,tooth_number,diagnosis,author,created_at) VALUES(?,?,?,?,?,?)",
                (fid, date, "16", "Old diag", author, created))
    cur.execute("INSERT INTO procedures(patient_file,visit_date,tooth_number,procedure_done,author,created_at) VALUES(?,?,?,?,?,?)",
                (fid, date, "16", "Old proc", author, created))
    conn.commit(); conn.close()
    sm.save_session_money(fid, date, "16", 300, 50)
    return date


def test_edit_admin_updates_text_money_keeps_created_at():
    fid = _patient("R24EditAdmin")
    caps, restore = _patch_msgs()
    root, tab = _build(user="boss", role="admin", fid=fid)
    if tab is None:
        print("SKIP edit admin (no display)"); restore(); _cleanup(fid); return
    try:
        _save_session(tab, D1, "16", 300, 50)
        conn = get_connection()
        created = conn.execute("SELECT created_at FROM diagnoses WHERE patient_file=?", (fid,)).fetchone()[0]
        conn.close()
        iid = tab.tree_history.get_children()[0]
        tab.tree_history.selection_set(iid)
        assert _edit.start_edit(tab) is True
        assert tab.txt_diagnosis.get("1.0", tk.END).strip() == "Pulpitis"
        assert (tab.e_sess_total.get(), tab.e_sess_paid.get()) == ("300", "50")
        assert str(tab.e_sess_date.cget("state")) == "disabled"  # identity fixed
        assert str(tab.e_sess_tooth.cget("state")) == "disabled"
        _entry.set_entry_text(tab, "txt_diagnosis", "Irreversible pulpitis")
        _entry.set_money(tab, 350, 100)
        tab.btn_save_visit.invoke()
        assert not caps["error"], caps["error"]
        conn = get_connection()
        row = conn.execute("SELECT diagnosis, created_at FROM diagnoses WHERE patient_file=?", (fid,)).fetchone()
        conn.close()
        assert row[0] == "Irreversible pulpitis" and row[1] == created
        assert patient_totals(fid) == {"total": 350.0, "paid": 100.0, "remaining": 250.0}
        assert _count("financials", fid) == 1  # replaced, not appended
        assert tab._editing_session is None  # edit mode exited
    finally:
        root.destroy(); restore(); _cleanup(fid)


def test_edit_doctor_without_finance_grant_money_locked():
    fid = _patient("R24Locked")
    caps, restore = _patch_msgs()
    root, tab = _build(user="doc_a", role="doctor", fid=fid)
    if tab is None:
        print("SKIP locked edit (no display)"); restore(); _cleanup(fid); return
    try:
        _save_session(tab, D1, "16", 300, 50)  # authored by doc_a, fresh
        iid = tab.tree_history.get_children()[0]
        tab.tree_history.selection_set(iid)
        _edit.sync_edit_buttons(tab)
        assert str(tab.btn_sess_edit.cget("state")) == "normal"
        assert str(tab.btn_sess_delete.cget("state")) == "disabled"  # money, no grant
        assert _edit.start_edit(tab) is True
        assert str(tab.e_sess_total.cget("state")) == "disabled"  # money LOCKED
        assert str(tab.e_sess_paid.cget("state")) == "disabled"
        assert "🔒" in tab.lbl_money_lock.cget("text")
        _entry.set_entry_text(tab, "txt_diagnosis", "Edited by author")
        tab.btn_save_visit.invoke()  # clinical-only save
        conn = get_connection()
        diag = conn.execute("SELECT diagnosis FROM diagnoses WHERE patient_file=?", (fid,)).fetchone()[0]
        conn.close()
        assert diag == "Edited by author"
        assert patient_totals(fid) == {"total": 300.0, "paid": 50.0, "remaining": 250.0}  # money untouched
        # Delete of the money session is refused with the explanation.
        tab.load(fid); root.update_idletasks()
        iid = tab.tree_history.get_children()[0]
        tab.tree_history.selection_set(iid)
        assert _del.delete_selected(tab) is False
        assert caps["error"], "money-delete refusal showed no explanation"
        assert "finance" in caps["error"][-1][1].lower(), caps["error"][-1]
        assert _count("diagnoses", fid) == 1 and _count("financials", fid) == 1
        # With the grant, the same doctor CAN delete it.
        grant_perm("doc_a", "finance.edit_amounts")
        try:
            assert _edit.can_edit_money(tab) is True
            assert _del.delete_selected(tab) is True
            assert _count("diagnoses", fid) == 0 and _count("financials", fid) == 0
            assert patient_totals(fid)["total"] == 0.0
        finally:
            revoke_perm("doc_a", "finance.edit_amounts")
    finally:
        root.destroy(); restore(); _cleanup(fid)


def test_edit_delete_blocked_old_other_author_and_nurse():
    fid = _patient("R24Old")
    _seed_old_session(fid)  # doc_b, 2 days ago, with money
    caps, restore = _patch_msgs()
    try:
        for user, role in (("doc_a", "doctor"), ("nurse1", "nurse")):
            root, tab = _build(user=user, role=role, fid=fid)
            if tab is None:
                print("SKIP old/nurse (no display)"); return
            try:
                session = session_rows(fid)[0]
                ok, reason = _edit.session_editable(tab, session)
                assert ok is False and reason, (user, ok)
                iid = tab.tree_history.get_children()[0]
                tab.tree_history.selection_set(iid)
                _edit.sync_edit_buttons(tab)
                assert str(tab.btn_sess_edit.cget("state")) == "disabled"
                assert tab.sess_status.cget("text") == reason
                assert _edit.start_edit(tab) is False
                assert _del.delete_selected(tab) is False
                assert _count("diagnoses", fid) == 1  # nothing touched
            finally:
                root.destroy()
        # Admin CAN edit + delete the same old session.
        root, tab = _build(user="boss", role="admin", fid=fid)
        try:
            session = session_rows(fid)[0]
            assert _edit.session_editable(tab, session)[0] is True
            iid = tab.tree_history.get_children()[0]
            tab.tree_history.selection_set(iid)
            assert _del.delete_selected(tab) is True
            assert session_rows(fid) == [] and patient_totals(fid)["total"] == 0.0
        finally:
            root.destroy()
    finally:
        restore(); _cleanup(fid)
