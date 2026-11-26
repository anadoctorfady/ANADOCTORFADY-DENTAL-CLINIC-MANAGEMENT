"""Round 53, Section B: every main-area page fits the window width
in Arabic at 1920x1080, and the Appointments table stays reachable.
Root causes (measured at 1920x1080, AR): Clinical -- the four entry
Text widgets used tk.Text's 80-char default (~888px each), so the
grid requested 3736px and each scrollbar sat ~500px past its panel
(fixed by width=1; pack expand still fills the panel). Appointments
-- the page had no scroll path, so a tall mid section squeezed the
table to zero height (fixed by the scroll-page scaffold + calendar
day rows non-stretching, weight=0). Pinned at tk scaling 1.0 and
2.0, AR (EN as control for width).
"""
import time
import tkinter as tk
from tkinter import messagebox

from src.models.database import get_setting, set_setting
from src.ui import rounded as _rounded
from src.ui.clinical_tables import FIELD_ATTRS

TABS = ("clinical", "appt", "fin", "settings", "users", "about")


def _display_available():
    try:
        r = tk.Tk(); r.withdraw(); r.destroy()
        return True
    except Exception:
        return False


def _make_app(lang="ar", scaling=None):
    from src.ui.shell import App
    orig = get_setting("language", "en") or "en"
    set_setting("language", lang)
    messagebox.showinfo = lambda *a, **k: None
    messagebox.showerror = lambda *a, **k: None
    app = App()
    login = [w for w in app.winfo_children()
             if isinstance(w, tk.Toplevel) and hasattr(w, "e_user")][0]
    login.do_login()
    app.update()
    if scaling is not None:
        app.tk.call("tk", "scaling", scaling)
        _rounded._MEASURE_CACHE.clear()
        if hasattr(app, "_r51_font_cache"):
            delattr(app, "_r51_font_cache")
        app._rebuild()
    app.geometry("1920x1080+0+0")
    app.update(); time.sleep(0.2); app.update()
    return app, orig


def _close(app, orig):
    set_setting("language", orig)
    _rounded._MEASURE_CACHE.clear()
    try:
        app.destroy()
    except Exception:
        pass


def _select_patient(app):
    kids = app.tree.get_children()
    if kids: app.tree.selection_set(kids[0]); app.on_select(); app.update()


def _extreme(widget, bottom=False):
    worst, who = 0, None
    stack = [widget]
    while stack:
        w = stack.pop()
        try:
            v = (w.winfo_rooty() + w.winfo_height()) if bottom else (
                w.winfo_rootx() + w.winfo_width())
        except Exception:
            continue
        if v > worst:
            worst, who = v, str(w)
        stack.extend(w.winfo_children())
    return worst, who


def test_r53_main_pages_fit_width_ar():
    if not _display_available():
        return
    for scaling in (None, 2.0):
        app, orig = _make_app("ar", scaling)
        try:
            _select_patient(app)
            win_right = app.winfo_rootx() + app.winfo_width()
            for name in TABS:
                widget = getattr(app, name)
                app.notebook.select(widget)
                app.update(); time.sleep(0.15); app.update()
                worst, who = _extreme(widget)
                assert worst <= win_right, (scaling, name, worst, win_right, who)
        finally:
            _close(app, orig)


def test_r53_main_pages_fit_width_en():
    if not _display_available():
        return
    app, orig = _make_app("en", 2.0)
    try:
        _select_patient(app)
        win_right = app.winfo_rootx() + app.winfo_width()
        for name in TABS:
            widget = getattr(app, name)
            app.notebook.select(widget)
            app.update(); time.sleep(0.15); app.update()
            worst, who = _extreme(widget)
            assert worst <= win_right, ("en", name, worst, win_right, who)
    finally:
        _close(app, orig)


def test_r53_clinical_entry_fields_fit_panels():
    """The four entry fields request a sane width (was 3736px for the
    grid) and each field's scrollbar sits inside its own panel."""
    if not _display_available():
        return
    app, orig = _make_app("ar", 2.0)
    try:
        _select_patient(app)
        app.notebook.select(app.clinical)
        app.update(); time.sleep(0.2); app.update()
        tab = app.clinical
        assert tab.sections_grid.winfo_reqwidth() <= 1600, (
            tab.sections_grid.winfo_reqwidth())
        for kind, attr in FIELD_ATTRS.items():
            field = getattr(tab, attr)
            assert field.winfo_reqwidth() <= 400, (kind, field.winfo_reqwidth())
            frame = tab.table_frames[kind]
            panel_right = frame.winfo_rootx() + frame.winfo_width()
            bars = [c for c in field.master.winfo_children() if c.winfo_class() == "TScrollbar"]
            assert bars, (kind, "no scrollbar beside the field")
            sb = bars[0]
            assert sb.winfo_rootx() + sb.winfo_width() <= panel_right, (
                kind, sb.winfo_rootx() + sb.winfo_width(), panel_right)
    finally:
        _close(app, orig)


def test_r53_appointments_table_reachable_ar():
    """Acceptance: at 1920x1080 in Arabic, the appointments table is
    reachable -- the page scrolls to it at any scaling."""
    if not _display_available():
        return
    for scaling in (None, 2.0):
        app, orig = _make_app("ar", scaling)
        try:
            _select_patient(app)
            tab = app.appt
            app.notebook.select(tab)
            app.update(); time.sleep(0.2); app.update()
            cv = tab._scroll_page
            region = cv.cget("scrollregion")
            assert region, "appointments page has no scroll region"
            y1 = float(str(region).split()[3])
            tree = tab.tree
            tree_bottom = tree.winfo_rooty() + tree.winfo_height()
            assert y1 >= tree_bottom - cv.winfo_rooty(), (
                scaling, region, tree_bottom - cv.winfo_rooty())
            cv.yview_moveto(1.0); app.update()
            win_bottom = app.winfo_rooty() + app.winfo_height()
            assert tree.winfo_rooty() + tree.winfo_height() <= win_bottom, (
                scaling, tree.winfo_rooty() + tree.winfo_height(), win_bottom)
            assert tree.winfo_rooty() < win_bottom, "table header not visible"
        finally:
            _close(app, orig)


def test_r53_finance_bottom_reachable_ar():
    """Finance content that runs past the fold must have a scroll
    path whose region covers it (the Statistics page)."""
    if not _display_available():
        return
    app, orig = _make_app("ar", 2.0)
    try:
        tab = app.fin
        app.notebook.select(tab)
        app.update(); time.sleep(0.2); app.update()
        win_bottom = app.winfo_rooty() + app.winfo_height()
        worst, who = _extreme(tab, bottom=True)
        if worst <= win_bottom:
            return
        covered, stack = False, [tab]
        while stack:
            w = stack.pop()
            if w.winfo_class() == "Canvas":
                try:
                    region = w.cget("scrollregion")
                    if region and w.winfo_rooty() + float(str(region).split()[3]) >= worst:
                        covered = True
                except Exception:
                    pass
            stack.extend(w.winfo_children())
        assert covered, (worst, win_bottom, who)
    finally:
        _close(app, orig)
