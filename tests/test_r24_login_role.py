"""Round 24 integration regression: the logged-in role must reach
the Clinical tab.

BUG (found by the round-24 gallery shoot, pre-existing wiring):
App.__init__ builds the whole main UI BEFORE login, while
app.current_role is still the default "doctor"; ClinicalTab
snapshots app.current_role/current_user at construction, and
_on_login never propagated the real role into the built tab. In a
fresh session an ADMIN was therefore treated as "doctor" by every
clinical check reading tab.current_role (round-12 history edit had
the same latent staleness; round-24 session Edit / money lock made
it visible: admin + >24h session -> "Editing is allowed only by
the admin after 24 hours" with Edit disabled). A language/theme
rebuild masked it (tabs rebuilt with the then-correct role).

Fix: App._on_login propagates (user, role) into self.clinical.
These tests drive the REAL App + REAL login window; they fail on
the pre-fix code (clinical.current_role stays "doctor").
"""
import tkinter as tk
from datetime import datetime, timedelta
from unittest import mock

from src.models.database import get_connection, init_db
from src.utils.auth import hash_pw
from tests.test_r18_info_panel_visible import _wait_login
import src.ui.login as login_mod


def _reset_pw(user):
    init_db(); conn = get_connection()
    conn.execute("UPDATE users SET password_hash=? WHERE username=?",
                 (hash_pw("1234"), user))
    conn.commit(); conn.close()


def _login(app, user):
    login = _wait_login(app)
    with mock.patch.object(login_mod.messagebox, "showinfo"):
        login.e_user.delete(0, tk.END); login.e_user.insert(0, user)
        login.e_pass.delete(0, tk.END); login.e_pass.insert(0, "1234")
        login.do_login()
    app.update()


def _seed_old_session(fid, author, days=3):
    when = datetime.now() - timedelta(days=days)
    d = when.date().isoformat(); ts = when.isoformat(timespec="seconds")
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO complaints(patient_file,visit_date,complaint,"
                "symptoms,author,created_at) VALUES(?,?,?,?,?,?)",
                (fid, d, "Pain", "Ache", author, ts))
    cur.execute("INSERT INTO diagnoses(patient_file,visit_date,tooth_number,"
                "diagnosis,author,created_at) VALUES(?,?,?,?,?,?)",
                (fid, d, "16", "Pulpitis", author, ts))
    cur.execute("INSERT INTO procedures(patient_file,visit_date,tooth_number,"
                "procedure_done,author,created_at) VALUES(?,?,?,?,?,?)",
                (fid, d, "16", "Filling", author, ts))
    conn.commit(); conn.close()
    return d


def _seed_patient(name):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name,birth_date_greg,"
                "nationality) VALUES(?,?,?,?)", (name, name, "1990-01-01", "Syrian"))
    fid = cur.lastrowid; conn.commit(); conn.close()
    return fid


def _cleanup(fid):
    conn = get_connection(); cur = conn.cursor()
    for tbl in ("complaints", "diagnoses", "procedures"):
        cur.execute(f"DELETE FROM {tbl} WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()


def _app(user):
    from src.ui.shell import App
    _reset_pw(user)
    app = App(); _login(app, user)
    return app


def test_admin_role_reaches_clinical_tab():
    app = _app("fady")
    try:
        assert app.current_role == "admin", app.current_role
        assert app.clinical.current_user == "fady"
        assert app.clinical.current_role == "admin", \
            f"clinical tab role is {app.clinical.current_role!r}, expected 'admin'"
    finally:
        app.destroy()


def test_doctor_role_reaches_clinical_tab():
    app = _app("doc2")
    try:
        assert app.current_role == "doctor", app.current_role
        assert app.clinical.current_user == "doc2"
        assert app.clinical.current_role == "doctor"
    finally:
        app.destroy()


def test_admin_can_edit_old_session_after_real_login():
    from src.models.history_money import session_rows
    from src.ui.clinical_session_edit import session_editable, sync_edit_buttons
    fid = _seed_patient("R24 Role Regression")
    _seed_old_session(fid, author="doc2", days=3)
    app = _app("fady")
    try:
        app.select_patient(fid); app.update()
        rows = session_rows(fid)
        assert rows, "seeded session missing"
        ok, reason = session_editable(app.clinical, rows[0])
        assert ok, f"admin refused a 3-day-old session: {reason}"
        kids = app.clinical.tree_history.get_children()
        assert kids
        app.clinical.tree_history.selection_set(kids[0]); app.update()
        sync_edit_buttons(app.clinical)
        assert str(app.clinical.btn_sess_edit["state"]) == "normal"
    finally:
        app.destroy(); _cleanup(fid)


def test_doctor_cannot_edit_old_foreign_session_after_real_login():
    from src.models.history_money import session_rows
    from src.ui.clinical_session_edit import session_editable
    fid = _seed_patient("R24 Role Regression Two")
    _seed_old_session(fid, author="fady", days=3)
    app = _app("doc2")
    try:
        app.select_patient(fid); app.update()
        rows = session_rows(fid)
        assert rows
        ok, reason = session_editable(app.clinical, rows[0])
        assert not ok and reason, "non-author doctor must be refused after 24h"
    finally:
        app.destroy(); _cleanup(fid)
