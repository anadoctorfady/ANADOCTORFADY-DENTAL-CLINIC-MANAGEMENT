"""i18n for shell chrome + login + dialogs (Job A1).

(1) GUI test under xvfb: language ar -> App shell chrome (tabs,
Logout, New Patient, list headings) and the login window are Arabic;
toggle back -> English again. Skips gracefully with no display.
(2) Static test: every t("...") key used by this job's own source
files exists in both EN and AR in src/config/strings.py.
"""
import re
from pathlib import Path

from src.config.strings import AR, EN, t
from src.models.database import get_setting, set_setting

MY_FILES = ["src/config/strings.py", "src/ui/shell.py", "src/ui/login.py",
            "src/utils/finance_gate.py", "src/ui/sync_now_ui.py",
            "src/ui/template_manager.py", "src/ui/add_drug.py",
            "src/ui/attendance_view.py", "src/ui/phrase_picker.py",
            "src/ui/clipboard_picker.py"]
ROOT = Path(__file__).resolve().parent.parent
_KEY_RE = re.compile(r"""\bt\(\s*["']([A-Za-z0-9_.]+)["']""")


def _display_available():
    try:
        import tkinter as tk
        r = tk.Tk(); r.withdraw(); r.destroy()
        return True
    except Exception:
        return False


def _texts(widget):
    """All Label/Button texts under `widget`, recursively."""
    import tkinter as tk
    out = []
    try:
        if widget.winfo_class() in ("Label", "Button"):
            out.append(str(widget.cget("text")))
    except Exception:
        pass
    for child in widget.winfo_children():
        out.extend(_texts(child))
    return out


def _app_tabs(app):
    for w in app.winfo_children():
        if w.winfo_class() == "Panedwindow":
            for child in w.winfo_children():
                for nb in child.winfo_children():
                    if nb.winfo_class() == "TNotebook":
                        return [nb.tab(i, "text") for i in range(nb.index("end"))]
    return []


def test_shell_ar_chrome_and_back():
    if not _display_available():
        return  # no display: skip GUI check
    import tkinter as tk
    from tkinter import messagebox
    from src.ui.shell import App
    orig = get_setting("language", "en") or "en"
    set_setting("language", "en")
    app = App()
    messagebox.showinfo = lambda *a, **k: None
    try:
        assert app.lang == "en"
        # Round 17: no Patients tab (form lives only in the modal dialog).
        assert any("Clinical" in x for x in _app_tabs(app)), _app_tabs(app)
        assert not any("Patients" in x for x in _app_tabs(app)), _app_tabs(app)
        assert any("Logout" in x for x in _texts(app))
        assert any("New Patient" in x for x in _texts(app))
        assert app.tree.heading("name", "text") == "Name"
        assert app.tree.heading("mobile", "text") == "Mobile"
        app._toggle_lang()
        assert app.lang == "ar"
        tabs = _app_tabs(app)
        assert not any("المرضى" in x for x in tabs), tabs  # round 17: no Patients tab
        assert any("السريري" in x for x in tabs), tabs
        assert any("المواعيد" in x for x in tabs), tabs
        assert any("المالية" in x for x in tabs), tabs
        assert any("الإعدادات" in x for x in tabs), tabs
        assert any("تسجيل الخروج" in x for x in _texts(app))
        assert any("مريض جديد" in x for x in _texts(app))
        assert app.tree.heading("name", "text") == "الاسم"
        assert app.tree.heading("mobile", "text") == "الجوال"
        app._toggle_lang()
        assert app.lang == "en"
        assert any("Clinical" in x for x in _app_tabs(app))
        assert any("Logout" in x for x in _texts(app))
    finally:
        set_setting("language", orig)
        try:
            app.destroy()
        except Exception:
            pass


def test_login_window_arabic_texts():
    if not _display_available():
        return  # no display: skip GUI check
    import tkinter as tk
    from src.ui.login import LoginWindow
    root = tk.Tk(); root.withdraw()
    try:
        win = LoginWindow(root, lang="ar")
        try:
            assert "تسجيل الدخول" in win.title()
            texts = _texts(win)
            assert "اسم المستخدم" in texts, texts
            assert "كلمة السر" in texts, texts
            assert "دخول" in texts, texts
        finally:
            try:
                win.destroy()
            except Exception:
                pass
        win_en = LoginWindow(root, lang="en")
        try:
            assert win_en.title().startswith("Login")
            texts = _texts(win_en)
            assert "Username" in texts and "Password" in texts
            assert "Sign In" in texts, texts
        finally:
            try:
                win_en.destroy()
            except Exception:
                pass
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def test_all_job_keys_exist_in_en_and_ar():
    """Every t("key") in this job's files must exist in EN and AR.

    Looked up in the merged strings plus the round-16 modules
    (strings_r16_*.py, not yet merged into strings.py)."""
    from src.config.strings import AR as _AR, EN as _EN
    import importlib
    en, ar = dict(_EN), dict(_AR)
    for _name in ("strings_r16_clinical", "strings_r16_patients",
                  "strings_r16_print", "strings_r16_rx",
                  "strings_r16_settings"):
        _mod = importlib.import_module(f"src.config.{_name}")
        en.update(_mod.EN)
        ar.update(_mod.AR)
    used = set()
    for rel in MY_FILES:
        src = (ROOT / rel).read_text(encoding="utf-8")
        used.update(_KEY_RE.findall(src))
    assert used, "no t() keys found -- regex or files wrong"
    missing_en = sorted(k for k in used if k not in en)
    missing_ar = sorted(k for k in used if k not in ar)
    assert not missing_en, f"keys missing from EN: {missing_en}"
    assert not missing_ar, f"keys missing from AR: {missing_ar}"
    for k in used:
        assert en[k], f"empty EN value for {k}"
        assert ar[k], f"empty AR value for {k}"


def test_en_texts_unchanged_and_arabic_present():
    """English mode keeps today's exact wording; Arabic differs."""
    assert t("shell.tab_patients", "en") == "  Patients  "
    assert t("shell.tab_patients", "ar") == "  المرضى  "
    assert t("login.signin", "en") == "Sign In"
    assert t("login.signin", "ar") == "دخول"
    assert t("shell.logout", "en") == "Logout"
    assert t("shell.logout", "ar") == "تسجيل الخروج"
    assert t("shell.new_patient", "en") == "＋ New Patient"
    assert t("no.such.key", "ar") == "no.such.key"  # fallback = key
    assert t("shell.logout") == "Logout"  # default lang is en


def test_finance_gate_prompt_texts_single_language():
    """Round 16: every language shows only its own words."""
    from src.utils.finance_gate import prompt_texts
    en, ar = prompt_texts("en"), prompt_texts("ar")
    assert en["unlock"] == "Unlock"
    assert ar["unlock"] == "فتح"
    assert "كلمة السر" in ar["prompt"]
    assert "password" in en["prompt"].lower()
    assert "كلمة السر" not in en["prompt"]


def test_sync_format_result_arabic():
    from src.ui.sync_now_ui import format_result
    res = {"offline": False, "login": True, "push": 3,
           "pull": {"patients": 1, "visits": 2, "financials": 0,
                    "employees": 0}, "errors": []}
    en = format_result(res, lang="en")
    assert "pushed 3" in en and "patients 1" in en and "Sync done" in en
    assert "تمت المزامنة" not in en, en
    ar = format_result(res, lang="ar")
    assert "تمت المزامنة" in ar and "3" in ar and "pushed" not in ar
    assert "بلا اتصال" in format_result({"offline": True}, lang="ar")
    assert "Offline" in format_result({"offline": True}, lang="en")
