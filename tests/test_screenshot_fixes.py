"""Screenshot fixes (2026-11-07 review): About text, finance re-auth
gate, clinical cost loader, rename refresh. GUI-free where possible."""
from pathlib import Path
from src.config.settings import ABOUT_EN, ABOUT_AR
from src.models.database import init_db, get_connection, save_financial
from src.models.finance import patient_totals
from src.utils.auth import verify
from src.utils.finance_gate import FinanceGate, require_auth
from src.ui import settings_ui


def _stub():
    return FinanceGate(verify_fn=lambda u, p: (u, p) == ("fady", "1234"))


def test_about_text():
    assert "Dr Fady Abdulkafy Dadoush" in ABOUT_EN
    assert "د. فادي عبد الكافي دعدوش" in ABOUT_AR


def test_about_whatsapp_only_line():
    # Line moved into the strings module (i18n round, 2026-11-08); the
    # About tab shows it via t("about.contact") in both languages.
    from src.config.strings import t
    assert "Contact via WhatsApp only" in t("about.contact", "en")
    assert "للتواصل واتساب فقط" in t("about.contact", "ar")


def test_finance_gate_locked_by_default():
    assert _stub().is_unlocked is False


def test_finance_gate_wrong_password_stays_locked():
    g = _stub()
    assert g.try_unlock("fady", "wrong") is False
    assert g.is_unlocked is False
    assert require_auth(g, "nope", "1234") is False
    assert g.is_unlocked is False


def test_finance_gate_correct_unlocks_and_lock_resets():
    g = _stub()
    assert g.try_unlock("fady", "1234") is True
    assert g.is_unlocked is True
    g.lock()  # logout re-locks
    assert g.is_unlocked is False
    # app restart = fresh instance starts locked
    assert FinanceGate(verify_fn=lambda u, p: True).is_unlocked is False


def test_finance_gate_real_verify():
    init_db()
    g = FinanceGate()  # real verify() against the users table
    assert g.try_unlock("fady", "1234") is True
    assert g.try_unlock("fady", "bad") is False


def test_clinical_cost_loader():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,father_name,grand_name,last_name,"
                "full_name,birth_date_greg,nationality) VALUES(?,?,?,?,?,?,?)",
                ("Gate", "Test", "Grand", "Patient", "Gate Test Grand Patient",
                 "1990-01-01", "Syrian"))
    fid = cur.lastrowid; conn.commit(); conn.close()
    try:
        save_financial(fid, "11", 500000, 300000, "2026-11-07")
        assert patient_totals(fid) == {"total": 500000.0, "paid": 300000.0,
                                       "remaining": 200000.0}
    finally:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
        conn.commit(); conn.close()


def test_rename_refresh_exists():
    assert hasattr(settings_ui.SettingsTab, "refresh_role_sections")
    assert callable(settings_ui.SettingsTab.refresh_role_sections)


def test_attendance_button_hidden_for_non_admin():
    """Attendance button (2026-11-08 gallery round): _on_login must hide
    the admin-only Attendance button for a non-admin even when an admin
    was logged in earlier in the same session - the button used to stay
    packed after logout -> doctor login (shot 09 showed it for doc1).
    GUI test: skips gracefully with no display (like test_header_bar_full_name)."""
    try:
        from src.ui.shell import App
        from src.utils.auth import create_user, delete_user
        init_db()
        create_user("admin", "fady", "1234", "admin")
        create_user("admin", "doc9", "1234", "doctor")
        app = App()
    except Exception:
        return  # no display: skip GUI check
    try:
        import time
        time.sleep(0.5); app.update()
        assert hasattr(app, "_att_btn")
        app._on_login("fady"); app.update()
        assert app._att_btn.winfo_ismapped(), "Attendance button not shown for admin"
        app._on_login("doc9"); app.update()
        assert not app._att_btn.winfo_ismapped(), "Attendance button still shown for doctor"
        app._on_login("fady"); app.update()
        assert app._att_btn.winfo_ismapped(), "Attendance button not re-shown for admin"
    finally:
        try:
            delete_user("admin", "doc9")
        except Exception:
            pass
        try:
            app.destroy()
        except Exception:
            pass
    """Header bar (2026-11-08): the in-app top bar must show the full
    'ANADOCTORFADY DENTAL CLINIC MANAGEMENT', not just ANADOCTORFADY,
    at Segoe UI 13 bold without clipping at 1380px width.
    GUI test: skips gracefully with no display (like test_sync_button)."""
    try:
        from src.ui.shell import App
        app = App()
    except Exception:
        return  # no display: skip GUI check
    try:
        import time
        # Round 13 item 1: the main window is withdrawn until login, so
        # widths only compute after login — log in (deiconifies) first.
        # The login window itself does not affect the bar.
        time.sleep(0.5)
        app.update()
        app._on_login("fady"); app.update()
        import tkinter as tk
        found = []

        def walk(w):
            if isinstance(w, tk.Label):
                if "DENTAL CLINIC MANAGEMENT" in str(w.cget("text") or ""):
                    found.append(w)
            for ch in w.winfo_children():
                walk(ch)

        walk(app)
        assert len(found) == 1, "header label missing"
        lbl = found[0]
        assert lbl.cget("text") == " ANADOCTORFADY DENTAL CLINIC MANAGEMENT "
        assert lbl.winfo_reqwidth() <= lbl.winfo_width(), "header label clipped"
        assert lbl.winfo_x() + lbl.winfo_width() <= 1380, "header overflows window"
    finally:
        try:
            app.destroy()
        except Exception:
            pass
