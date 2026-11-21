"""Alert strips: round 20 put them in the shell info panel;
round 22 moved them into the PINNED HEADER.

The owner (2026-11-15) had the clinical tab's patient name/info
header block removed -- it duplicated the shell's far-left Patient
info panel -- so round 20 moved the red allergy / current-meds
strip and the amber unpaid-balance strip into that shell panel.
Round 22 (owner redesign, 2026-11-16) superseded the location
again: the info panel itself moved into the clinical tab as the
PINNED HEADER (app.info_panel is tab.header_panel), and the
strips live in its Health block. This test drives the REAL App:
with a patient who has an allergy AND an unpaid balance selected,
BOTH strips are visible inside the header; with a clean patient
selected, NEITHER shows. It also pins that the tab carries the
header (not a loose strip of its own) and that the shell's left
column no longer contains any info panel.

Runs only against an isolated gate copy (ANADOCTORFADY_DATA_DIR
must be set); skips gracefully with no display. The gate copy's
fady password is reset to 1234 (throwaway copy only). Seeded rows
are cleaned up.
"""
import os
import time
import tkinter as tk
from unittest import mock


def _display_available():
    try:
        r = tk.Tk(); r.destroy(); return True
    except Exception:
        return False


def _seed(allergies="", total=0.0, paid=0.0):
    from src.models.database import get_connection, init_db
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,father_name,grand_name,"
                "last_name,full_name,birth_date_greg,allergies,"
                "current_medications) VALUES(?,?,?,?,?,?,?,?)",
                ("R20", "Father", "Grand", "Last",
                 "R20 Father Grand Last", "1990-05-15", allergies, ""))
    fid = cur.lastrowid
    if total:
        cur.execute("INSERT INTO financials(patient_file,total_cost,"
                    "paid_amount,remaining,visit_date) VALUES(?,?,?,?,?)",
                    (fid, total, paid, total - paid, "2026-11-09"))
    conn.commit(); conn.close()
    return fid


def _cleanup(*fids):
    from src.models.database import get_connection
    try:
        conn = get_connection(); cur = conn.cursor()
        for fid in fids:
            cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
            cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
        conn.commit(); conn.close()
    except Exception:
        pass


def _find_login(app):
    for w in app.winfo_children():
        if isinstance(w, tk.Toplevel) and hasattr(w, "e_user"):
            return w
    return None


def _login(app):
    import src.ui.login as login_mod
    deadline = time.time() + 5.0
    login = None
    while time.time() < deadline:
        app.update()
        login = _find_login(app)
        if login is not None:
            break
        time.sleep(0.05)
    assert login is not None, "login window did not appear"
    with mock.patch.object(login_mod.messagebox, "showinfo"):
        login.e_user.delete(0, tk.END); login.e_user.insert(0, "fady")
        login.e_pass.delete(0, tk.END); login.e_pass.insert(0, "1234")
        login.do_login()
    app.update()


def test_alert_strips_visible_in_pinned_header_for_alert_patient():
    if not os.environ.get("ANADOCTORFADY_DATA_DIR"):
        print("SKIP (not an isolated gate copy)"); return
    if not _display_available():
        print("SKIP (no display)"); return
    from src.models.database import get_connection
    from src.ui.shell import App
    from src.utils.auth import hash_pw
    conn = get_connection()
    conn.execute("UPDATE users SET password_hash=? WHERE username='fady'",
                 (hash_pw("1234"),))
    conn.commit(); conn.close()
    fid_alert = _seed(allergies="Penicillin", total=1000.0, paid=250.0)
    fid_clean = _seed()
    app = App()
    try:
        _login(app)
        # Round 22: the info panel IS the clinical tab's pinned
        # header now; the tab itself still carries no loose strip
        # or name labels (they live on tab.header_panel).
        assert app.info_panel is app.clinical.header_panel
        assert app.clinical.header_panel.master is app.clinical
        for attr in ("alert_strip", "lbl_pat_name", "lbl_pat_meta",
                     "clin_info_panel", "patient_header_frame",
                     "left_info_frame"):
            assert not hasattr(app.clinical, attr), attr
        # ... and the shell's left column holds no info panel.
        from src.ui.patient_info import PatientInfoPanel
        stack = [app.left_inner]
        while stack:
            w = stack.pop()
            assert not isinstance(w, PatientInfoPanel)
            stack.extend(w.winfo_children())
        # Allergy + unpaid balance: BOTH strips visible inside the
        # pinned header's Health block.
        app.select_patient(fid_alert)
        app.update()
        panel = app.info_panel
        strip = panel.alert_strip
        assert strip.winfo_ismapped() == 1, "alert strip not mapped"
        assert strip.winfo_manager() == "pack"
        assert strip.lbl_health.winfo_ismapped() == 1
        assert "Penicillin" in strip.lbl_health.cget("text")
        assert strip.lbl_balance.winfo_ismapped() == 1
        assert "750.00" in strip.lbl_balance.cget("text")
        chain = []
        w = strip
        while w is not None:
            chain.append(w); w = w.master
        assert panel in chain, "strip not inside the header panel"
        assert app.clinical in chain, "header not inside the clinical tab"
        top = panel.winfo_rooty(); bottom = top + panel.winfo_height()
        assert top <= strip.winfo_rooty() \
            and strip.winfo_rooty() + strip.winfo_height() <= bottom, \
            "strip must sit inside the pinned header"
        # Clean patient: NEITHER strip shows.
        app.select_patient(fid_clean)
        app.update()
        assert strip.winfo_manager() == "", "clean patient shows a strip"
        assert strip.winfo_ismapped() == 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass
        _cleanup(fid_alert, fid_clean)
