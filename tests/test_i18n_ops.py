"""i18n for ops area (Job A3): appointments, finance, salaries,
settings, users, about, sync guide.

(1) GUI test under xvfb: language ar -> App, open the Appointments,
Finances, Settings and About tabs (Users tab built standalone: it is
hidden for non-admins) and assert their key labels are Arabic; toggle
back -> English again. Skips gracefully with no display.
(2) Static test: every t("...") key used by this job's own source
files exists in both EN and AR in the merged strings (strings.py,
which merges strings_ops.py + strings_round12.py; round-12 keys live
only in strings_round12.py by design). Dynamic f-string keys like
t(f"fin.card_{key}") are expanded against EN).
"""
import re
from pathlib import Path

from src.config.strings import t
from src.config.strings import AR, EN  # merged EN/AR (ops + clinical + round12)
from src.models.database import get_setting, set_setting

MY_FILES = ["src/ui/appointments.py", "src/ui/calendar_grid.py",
            "src/ui/finance.py", "src/ui/finance_views.py",
            "src/ui/salaries_view.py", "src/ui/settings_ui.py",
            "src/ui/settings_account.py", "src/ui/settings_sync_guide.py",
            "src/ui/users_tab.py", "src/ui/about_tab.py",
            "src/config/strings_ops.py"]
ROOT = Path(__file__).resolve().parent.parent
_KEY_RE = re.compile(r"""\bt\(\s*["']([A-Za-z0-9_.]+)["']""")
_DYN_RE = re.compile(r"""\bt\(f["']([^"']*)\{[^}]*\}([^"']*)["']""")
_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


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
        if widget.winfo_class() in ("Label", "Button", "TButton", "Labelframe"):
            out.append(str(widget.cget("text")))
    except Exception:
        pass
    for child in widget.winfo_children():
        out.extend(_texts(child))
    return out


class _StubApp:
    lang = "ar"
    current_user = "fady"
    current_role = "admin"
    current_patient = None
    finance_gate = None


def _check_ar(app):
    """Key labels of each ops tab are Arabic with language ar."""
    texts_appt = _texts(app.appt)
    for h in ("ملف #", "المريض", "التاريخ", "الوقت", "السبب", "الحالة"):
        assert app.appt.tree.heading(
            {"ملف #": "file", "المريض": "name", "التاريخ": "date",
             "الوقت": "time", "السبب": "reason", "الحالة": "status"}[h],
            "text") == h, h
    assert app.appt.lb_days.get(0) == "الاثنين"
    assert _ARABIC_RE.search(app.appt.cal.lbl_month.cget("text")), \
        app.appt.cal.lbl_month.cget("text")
    assert "إضافة موعد" in texts_appt, texts_appt
    assert app.appt.lbl_selected.cget("text").startswith("المحدد:")
    texts_fin = _texts(app.fin)
    for s in ("إجمالي الدخل", "إجمالي المصروفات", "صافي الدخل",
              "من", "إلى", "احسب"):
        assert s in texts_fin, s
    assert any("المالية مقفلة" in x for x in texts_fin), texts_fin
    texts_set = _texts(app.settings)
    for s in ("الإعدادات", "مزامنة الأجهزة", "تغيير كلمة السر",
              "إعادة تسمية مستخدم", "حفظ إعدادات المزامنة",
              "تطبيق السمة والعملة"):
        assert any(s in x for x in texts_set), s
    texts_about = _texts(app.about)
    for s in ("إدارة عيادة الأسنان", "للتواصل واتساب فقط", "+963944234456"):
        assert any(s in x for x in texts_about), texts_about
    assert any("صدقة" in x for x in texts_about), texts_about


def _check_en(app):
    """Same labels back in English after toggling to en."""
    assert app.appt.tree.heading("name", "text") == "Patient"
    assert app.appt.tree.heading("status", "text") == "Status"
    assert app.appt.lb_days.get(0).startswith("Monday")
    texts_fin = _texts(app.fin)
    assert "Total Income" in texts_fin and "Net Income" in texts_fin
    assert "Finances locked" in " ".join(texts_fin)
    texts_set = _texts(app.settings)
    assert any("Settings" in x for x in texts_set)
    assert "Save sync settings" in texts_set
    texts_about = _texts(app.about)
    assert "Dental Clinic Management" in texts_about


def test_ops_ar_tabs_and_back():
    if not _display_available():
        return  # no display: skip GUI check
    import tkinter as tk
    from tkinter import ttk, messagebox
    from src.ui.shell import App
    orig = get_setting("language", "en") or "en"
    set_setting("language", "ar")
    app = App()
    messagebox.showinfo = lambda *a, **k: None
    try:
        assert app.lang == "ar"
        _check_ar(app)
        # Users tab is hidden for non-admins, so build it standalone
        # (notebook parent: refresh() hides it, widgets still exist).
        nb = ttk.Notebook(app)
        from src.ui.users_tab import UsersTab
        users = UsersTab(nb, _StubApp())
        texts_users = _texts(users)
        for s in ("المستخدمون", "إنشاء مستخدم جديد", "اسم المستخدم",
                  "كلمة السر", "الدور", "المركز", "إنشاء مستخدم",
                  "حذف المحدد"):
            assert any(s in x for x in texts_users), s
        app._toggle_lang()
        assert app.lang == "en"
        _check_en(app)
    finally:
        set_setting("language", orig)
        try:
            app.destroy()
        except Exception:
            pass


def _used_keys():
    used = set()
    for rel in MY_FILES:
        src = (ROOT / rel).read_text(encoding="utf-8")
        used.update(_KEY_RE.findall(src))
        for pre, suf in _DYN_RE.findall(src):
            pat = re.compile("^" + re.escape(pre) + ".*" + re.escape(suf) + "$")
            used.update(k for k in EN if pat.match(k))
    return used


def test_ops_keys_exist_in_en_and_ar():
    """Every t("key") in this job's files must exist in EN and AR.

    Looked up in the merged strings plus the round-16 modules
    (strings_r16_*.py, not yet merged into strings.py)."""
    import importlib
    en, ar = dict(EN), dict(AR)
    for _name in ("strings_r16_clinical", "strings_r16_patients",
                  "strings_r16_print", "strings_r16_rx",
                  "strings_r16_settings"):
        _mod = importlib.import_module(f"src.config.{_name}")
        en.update(_mod.EN)
        ar.update(_mod.AR)
    used = _used_keys()
    assert used, "no t() keys found -- regex or files wrong"
    assert len(used) > 100, f"only {len(used)} keys found, expected 150+"
    missing_en = sorted(k for k in used if k not in en)
    missing_ar = sorted(k for k in used if k not in ar)
    assert not missing_en, f"keys missing from EN: {missing_en}"
    assert not missing_ar, f"keys missing from AR: {missing_ar}"
    for k in used:
        assert en[k], f"empty EN value for {k}"
        assert ar[k], f"empty AR value for {k}"
        assert t(k, "en") == en[k], f"t() en mismatch for {k}"
        assert t(k, "ar") == ar[k], f"t() ar mismatch for {k}"


def test_ops_en_texts_single_language_and_arabic_present():
    """Round 16: English mode is single-language; Arabic differs."""
    assert t("appt.title", "en") == "📅 Appointments"
    assert t("appt.title", "ar") == "📅 المواعيد"
    assert t("fin.card_net", "en") == "Net Income"
    assert t("fin.card_net", "ar") == "صافي الدخل"
    assert t("fin.tab_expenses", "en") == " Expenses "
    assert t("fin.tab_expenses", "ar") == " المصروفات "
    assert t("settings.apply", "en") == "Apply Theme & Currency"
    assert t("settings.apply", "ar") == "تطبيق السمة والعملة"
    assert t("users.create_btn", "en") == "Create User"
    assert t("users.create_btn", "ar") == "إنشاء مستخدم"
    assert t("about.contact", "en") == "Contact via WhatsApp only"
    assert t("about.contact", "ar") == "للتواصل واتساب فقط"
    assert t("sync.guide_close", "en") == "Close"
    assert t("sync.guide_close", "ar") == "إغلاق"
    assert t("no.such.key", "ar") == "no.such.key"  # fallback = key
