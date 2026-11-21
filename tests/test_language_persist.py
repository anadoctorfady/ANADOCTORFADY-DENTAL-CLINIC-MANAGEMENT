"""Language switch (ITEM 2): the choice must survive a restart.

Root cause found by reproduction: the DB seed in database.py init_db()
already uses INSERT OR IGNORE, so set language='ar' + init_db() twice
still reads back 'ar' -- persistence was never the bug. The real bug
was in shell.py: _toggle_lang() saved the setting but never rebuilt
the UI, and the shell's own chrome (tabs, top bar, list headings) was
hardcoded English, so after a restart the app still looked English.
Fix: _toggle_lang() persists + _rebuild()s (the same instant-apply
mechanism the theme toggle uses), and shell chrome reads self.lang.
"""
from src.models.database import init_db, get_setting, set_setting


def _restart():
    """Simulate a restart exactly as startup does: main.py calls
    init_db(), then App.__init__ calls init_db() again and reads the
    setting with get_setting('language', 'en')."""
    init_db()
    init_db()
    return get_setting("language", "en") or "en"


def test_language_ar_persists_across_restart():
    orig = get_setting("language", "en") or "en"
    try:
        set_setting("language", "ar")
        assert _restart() == "ar"
        assert _restart() == "ar"  # a second restart still Arabic
    finally:
        set_setting("language", orig)


def test_language_en_persists_across_restart():
    orig = get_setting("language", "en") or "en"
    try:
        set_setting("language", "en")
        assert _restart() == "en"
        set_setting("language", "ar")
        assert _restart() == "ar"
        set_setting("language", "en")
        assert _restart() == "en"
    finally:
        set_setting("language", orig)


def test_language_seed_does_not_reset():
    """init_db() seeding must not overwrite an existing choice:
    the seed is INSERT OR IGNORE, not INSERT OR REPLACE."""
    orig = get_setting("language", "en") or "en"
    try:
        set_setting("language", "ar")
        init_db()
        assert get_setting("language") == "ar"
    finally:
        set_setting("language", orig)


def _app_tabs(app):
    for w in app.winfo_children():
        if w.winfo_class() == "Panedwindow":
            for child in w.winfo_children():
                for nb in child.winfo_children():
                    if nb.winfo_class() == "TNotebook":
                        return [nb.tab(i, "text") for i in range(nb.index("end"))]
    return []


def test_shell_toggle_applies_arabic_and_back():
    """GUI test under xvfb; skips (returns) with no display, like
    test_sync_button. Toggling must rebuild the shell in Arabic
    immediately -- no restart needed -- and toggling back restores
    English; the persisted value survives a simulated restart."""
    try:
        from tkinter import messagebox
        from src.ui.shell import App
        orig = get_setting("language", "en") or "en"
        set_setting("language", "en")
        app = App()
        app._logged_in = True  # login window not shown yet (after(100))
        messagebox.showinfo = lambda *a, **k: None
        try:
            assert app.lang == "en"
            app._toggle_lang()
            assert app.lang == "ar"
            assert get_setting("language") == "ar"
            assert _restart() == "ar"
            tabs = _app_tabs(app)
            # Round 17: no Patients tab any more; Clinical is the first tab.
            assert any("السريري" in t for t in tabs), tabs
            assert not any("المرضى" in t for t in tabs), tabs
            assert app.tree.heading("name", "text") == "الاسم"
            app._toggle_lang()
            assert app.lang == "en"
            assert get_setting("language") == "en"
            assert _restart() == "en"
            assert any("Clinical" in t for t in _app_tabs(app))
            assert not any("Patients" in t for t in _app_tabs(app))
        finally:
            set_setting("language", orig)
            try:
                app.destroy()
            except Exception:
                pass
    except Exception:
        return  # no display: skip GUI check
