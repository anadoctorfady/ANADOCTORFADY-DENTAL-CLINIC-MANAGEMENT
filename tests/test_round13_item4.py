"""Round 13, item 4: the four cosmetic leftovers from round 12.
(a) Quick-book row fits at 1380px and at the 1200px minimum, EN+AR.
(b) Template-manager bottom row fits the 640px dialog (R21: the
buttons row incl. "Restore built-in templates"). (c) "Manage
templates" button fully visible in AR clinical. (d) Long patient
name fully shown in the shell info panel (R20). GUI skips w/o display."""
import time
import tkinter as tk
from tkinter import ttk

LONG_NAME = "Ahmed Mohammed Ali Hassan"
VERY_LONG_NAME = "Ahmed Mohammed Ali Hassan Al-Dadoush Al-Sayed Al-Hashimi"

def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)

def _tk():
    try:
        return tk.Tk()
    except Exception:
        return None

def _app():
    """Logged-in App at the default 1380x820, or None (no display)."""
    try:
        from src.ui.shell import App
        app = App()
    except Exception:
        return None
    app.update()
    time.sleep(0.6)  # login window appears after 100ms
    app.update()
    login = next((w for w in app.winfo_children()
                  if isinstance(w, tk.Toplevel) and hasattr(w, "e_user")), None)
    if login is not None:
        login.destroy()
    app._on_login("fady")
    app.update()
    return app

def _main_nb(app):
    # Round 17: the main notebook has 6 tabs (Patients tab removed);
    # identify it as the notebook holding the Clinical tab.
    for w in _walk(app):
        if isinstance(w, ttk.Notebook) and str(app.clinical) in w.tabs():
            return w
    raise RuntimeError("main notebook not found")

def _select(app, idx):
    _main_nb(app).select(idx)
    app.update_idletasks()
    app.update()

def _set_lang(app, lang):
    from src.models.database import set_setting
    app.lang = lang
    set_setting("language", lang)
    app._rebuild()
    app.update()
    app._on_login("fady")
    app.update()

def _right(w, app):
    return w.winfo_rootx() - app.winfo_rootx() + w.winfo_width()

def _check_quickbook(app, width):
    """(a) button + patient label inside the window, enabled."""
    tab = app.appt
    btn = tab.btn_quickbook
    assert btn.winfo_width() >= 100, f"quick-book squeezed: {btn.winfo_width()}px"
    assert _right(btn, app) <= width - 8, f"quick-book off-screen: right={_right(btn, app)} win={width}"
    assert _right(tab.lbl_qb_patient, app) <= width - 8
    assert tab.lbl_qb_patient.winfo_width() >= 200, f"patient label squeezed: {tab.lbl_qb_patient.winfo_width()}px"
    assert str(btn.cget("state")) in ("normal", "active"), "quick-book disabled with a patient selected"  # R28: Tk reports hover as "active" -- also enabled; the old == "normal" assert failed on X-pointer position alone (fails identically on the round-27 tree).

def test_quickbook_button_visible_1380_en():
    app = _app()
    if app is None:
        print("SKIP test_quickbook_button_visible_1380_en (no display)")
        return
    try:
        app.select_patient(1)
        app.update()
        _select(app, 1)  # Appointments (round 17 tab order: Clinical=0, Appointments=1)
        _check_quickbook(app, 1380)
    finally:
        app.destroy()

def test_quickbook_button_visible_1200_ar():
    app = _app()
    if app is None:
        print("SKIP test_quickbook_button_visible_1200_ar (no display)")
        return
    try:
        app.geometry("1200x800")
        app.update()
        _set_lang(app, "ar")
        app.select_patient(1)
        app.update()
        _select(app, 1)  # Appointments (round 17 tab order)
        _check_quickbook(app, 1200)
    finally:
        _restore_lang_en()
        app.destroy()

def test_template_manager_bottom_row_visible():
    # Round 21: no "Show hidden" checkbutton any more; the buttons
    # row (widest: "Restore built-in templates") must fit 640x560.
    root = _tk()
    if root is None:
        print("SKIP test_template_manager_bottom_row_visible (no display)")
        return
    root.withdraw()
    try:
        from src.ui.template_manager import open_template_manager
        win = open_template_manager(root, "fady", lang="en")
        root.update_idletasks()
        root.update()
        assert win.winfo_reqwidth() <= 640 and win.winfo_reqheight() <= 560, "dialog wants more than 640x560"
        assert not [w for w in _walk(win) if w.winfo_class() == "TCheckbutton"]
        btn = next(w for w in _walk(win) if _has_text(w, "Restore built-in"))
        assert btn.winfo_width() >= btn.winfo_reqwidth(), f"Restore-built-ins clipped: {btn.winfo_width()}px < req {btn.winfo_reqwidth()}px"
        assert btn.winfo_rootx() - win.winfo_rootx() + btn.winfo_width() <= win.winfo_width(), "Restore-built-ins past dialog edge"
        assert btn.winfo_y() + btn.winfo_height() <= win.winfo_height(), "Restore-built-ins past dialog bottom"
        win.destroy()
    finally:
        root.destroy()

def test_manage_templates_button_visible_ar():
    app = _app()
    if app is None:
        print("SKIP test_manage_templates_button_visible_ar (no display)")
        return
    try:
        _set_lang(app, "ar")
        app.select_patient(1)
        app.update()
        _select(app, 0)  # Clinical (round 17 tab order)
        btn = next((w for w in _walk(app.clinical) if _has_text(w, "إدارة القوالب")), None)
        assert btn is not None, "Manage-templates button not found (AR)"
        assert btn.winfo_width() >= btn.winfo_reqwidth(), f"Manage-templates squeezed: {btn.winfo_width()}px < req {btn.winfo_reqwidth()}px"
        assert _right(btn, app) <= 1380 - 24, f"Manage-templates flush at right edge: {_right(btn, app)}"
    finally:
        _restore_lang_en()
        app.destroy()

def _restore_lang_en():  # AR tests must not leave language=ar behind.
    from src.models.database import set_setting
    set_setting("language", "en")

def _has_text(w, needle):
    try: return needle in str(w.cget("text"))
    except Exception: return False

def test_long_patient_name_single_line():
    app = _app()
    if app is None:
        print("SKIP test_long_patient_name_single_line (no display)")
        return
    try:
        app.select_patient(1)  # Ahmed Mohammed Ali Hassan
        app.update()
        # Round 20: the name's single home = the shell panel body.
        body = app.info_panel.info_text()  # R21: per-line labels; info_text() joins them
        assert LONG_NAME in body, body
        assert app.info_panel.winfo_ismapped()
        assert not hasattr(app.clinical, "lbl_pat_name")
    finally:
        app.destroy()

def test_very_long_name_no_clinical_header():
    """Round 20: the ellipsising clinical name header this test
    used to pin was REMOVED (owner: it duplicated the shell's
    far-left info panel, whose body wraps instead of truncating).
    A very long name must build + refresh cleanly on a headerless tab."""
    root = _tk()
    if root is None:
        print("SKIP test_very_long_name_no_clinical_header (no display)")
        return
    root.geometry("1380x900")
    root.deiconify()
    try:
        from src.ui.clinical import ClinicalTab
        from tests.test_clinical_redesign import _stub_app
        app = _stub_app()
        app.current_patient = {"full_name": VERY_LONG_NAME, "file_number": 1,
                               "mobile1": "0944000111", "birth_date_greg": "1990-05-15"}
        tab = ClinicalTab(root, app)
        tab.pack()
        root.update_idletasks()
        tab._refresh_patient_panel()  # must not raise without a header
        assert not hasattr(tab, "lbl_pat_name")
        # R24: panels/_panels_fid REMOVED; the header must exist.
        assert tab.header_panel is not None
        assert not hasattr(tab, "_panels_fid")
    finally:
        root.destroy()
