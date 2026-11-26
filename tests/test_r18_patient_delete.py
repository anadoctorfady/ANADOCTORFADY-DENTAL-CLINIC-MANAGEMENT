"""Round 18 worker W2: soft Delete (model + admin-only role gate).

soft_delete_patient() sets deleted=1 only -- the patient vanishes
from search / list / fetch / duplicate-check, but financials,
procedures and prescriptions rows stay in the DB and the freed
name no longer blocks re-registration. PatientInfoPanel disables
Delete for doctor/nurse, its handler refuses them even when
called directly, and admin deletes only after confirming in a
dialog that NAMES the patient. Helpers are shared with
tests.test_r18_patient_edit_delete. GUI parts skip with no
display; run with DISPLAY=:98 under Xvfb.
"""
import tkinter as tk

from src.models.database import get_connection, init_db
from src.models.patients import (fetch_list_row, fetch_patient,
                                 find_duplicate, search_patients,
                                 soft_delete_patient)
from tests.test_r18_patient_edit_delete import (_StubApp, _count,
                                                _patch_msgs, _row)
from tests.test_r18_search_phone import _cleanup, _ids, _seed


def test_soft_delete_hides_but_preserves():
    """Deleted patient gone from search/list/fetch/duplicate, still
    in the DB, linked rows untouched, freed name re-registerable."""
    init_db()
    fid = _seed("R18Del", "R18Dad", "R18Gpa", "R18Fam", m1="0791234567")
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO financials(patient_file, total_cost, "
                "paid_amount, remaining, visit_date) "
                "VALUES(?, 100, 40, 60, '2026-11-14')", (fid,))
    cur.execute("INSERT INTO procedures(patient_file, visit_date, "
                "procedure_done) VALUES(?, '2026-11-14', 'Filling')", (fid,))
    cur.execute("INSERT INTO prescriptions(patient_file, date, doctor) "
                "VALUES(?, '2026-11-14', 'fady')", (fid,))
    conn.commit(); conn.close()
    new_fid = None
    try:
        assert find_duplicate("R18Del", "R18Dad", "R18Fam") == fid
        assert soft_delete_patient(fid) is True
        assert soft_delete_patient(fid) is False  # already deleted
        row = _row(fid)
        assert row is not None and row["deleted"] == 1, row
        assert _count("financials", fid) == 1
        assert _count("procedures", fid) == 1
        assert _count("prescriptions", fid) == 1
        assert search_patients(first="R18Del") == []
        # (Phone/q by fid: the gate DB may hold other patients
        # sharing a number, e.g. the clinic's own.)
        assert fid not in _ids(search_patients(phone="+962791234567"))
        assert fid not in _ids(search_patients(q="0791234567"))
        assert search_patients(current_file=fid) == []
        assert fetch_list_row(fid) is None
        assert fetch_patient(fid) is None
        assert find_duplicate("R18Del", "R18Dad", "R18Fam") is None
        new_fid = _seed("R18Del", "R18Dad", "R18Gpa", "R18Fam", m1="0791200099")
        assert new_fid != fid and fetch_patient(new_fid) is not None
    finally:
        conn = get_connection(); cur = conn.cursor()
        for t in ("financials", "procedures", "prescriptions"):
            cur.execute(f"DELETE FROM {t} WHERE patient_file=?", (fid,))
        conn.commit(); conn.close()
        _cleanup(*[f for f in (fid, new_fid) if f])


def test_delete_role_gate_panel():
    """Doctor + nurse: Delete button DISABLED and handler refuses
    (patient untouched). Admin: enabled, naming confirmation,
    confirmed delete hides the patient and clears the open file."""
    init_db()
    fid = _seed("R18Gate", "R18Dad", "R18Gpa", "R18Fam", m1="0791200055")
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        _cleanup(fid); print("SKIP delete_role_gate (no display)"); return
    from src.ui.patient_info import PatientInfoPanel
    row = fetch_patient(fid); caps, restore = _patch_msgs(ask=True)
    try:
        for role in ("doctor", "nurse"):
            app = _StubApp(role=role); app.current_patient = row
            panel = PatientInfoPanel(root, app); panel.pack()
            panel.refresh(row); root.update_idletasks()
            assert str(panel.delete_btn["state"]) == "disabled", role
            assert str(panel.edit_btn["state"]) == "normal", role
            assert "R18Gate" in panel.info_text()  # R21: lines are per-line labels now; info_text() joins them
            panel._delete()  # direct call: handler must refuse
            assert caps["warn"], f"no admin-only warning for {role}"
            assert fetch_patient(fid) is not None, role
            panel.destroy()
        app = _StubApp(role="admin"); app.current_patient = row
        panel = PatientInfoPanel(root, app); panel.pack()
        panel.refresh(row); root.update_idletasks()
        assert str(panel.delete_btn["state"]) == "normal"
        caps["ask_answer"] = False
        panel._delete()  # confirmation declined: nothing happens
        assert caps["ask"] and "R18Gate" in caps["ask"][-1][1]
        assert fetch_patient(fid) is not None
        caps["ask_answer"] = True
        panel._delete()  # confirmed: soft-deleted + cleared
        assert fetch_patient(fid) is None
        assert _row(fid)["deleted"] == 1
        assert app.current_patient is None and panel._fid is None
        assert str(panel.delete_btn["state"]) == "disabled"
        panel.destroy()
    finally:
        restore(); root.destroy(); _cleanup(fid)
