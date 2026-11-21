"""Settings horizontal overflow (shot 13ar, 2026-11-08). <200 lines.

In Arabic the Settings body needed 1103px but its canvas viewport is
only 962px at 1380x820, so the Bilingual PDF button was truncated
(106 of 152px wide) and the red Rename User button stuck out 111px
past the viewport. Both rows were reflowed (top buttons 2x2, Rename
button on its own row); assert in AR and EN that the body fits the
viewport and EVERY Settings button is fully inside it at its full
requested width. GUI test: skips gracefully with no display."""
import time
import tkinter as tk

from src.config.strings import t
from src.models.database import get_setting, init_db, set_setting
from src.utils.auth import create_user


def test_settings_no_horizontal_overflow_ar_and_en():
    orig = get_setting("language", "en") or "en"
    for lang in ("ar", "en"):
        set_setting("language", lang)
        try:
            from src.ui.shell import App
            init_db()
            try:
                create_user("admin", "fady", "1234", "admin")
            except Exception:
                pass
            app = App()
        except Exception:
            set_setting("language", orig)
            return  # no display: skip GUI check
        try:
            time.sleep(0.5); app.update()
            app._on_login("fady"); app.update()
            app.notebook.select(app.settings)  # round 17: no app.form / Patients tab any more
            time.sleep(0.5); app.update(); app.update_idletasks()
            st = app.settings
            assert st.body.winfo_reqwidth() <= st._canvas.winfo_width(), \
                (lang, st.body.winfo_reqwidth(), st._canvas.winfo_width())
            view_right = st._canvas.winfo_rootx() + st._canvas.winfo_width()
            btns = []

            def _walk(w):
                if isinstance(w, tk.Button):
                    btns.append(w)
                for ch in w.winfo_children():
                    _walk(ch)
            _walk(st.body)
            assert btns, f"{lang}: no Settings buttons found"
            for b in btns:
                txt = str(b.cget("text") or "")
                assert b.winfo_width() == b.winfo_reqwidth(), \
                    (lang, txt, b.winfo_width(), b.winfo_reqwidth())
                assert b.winfo_rootx() + b.winfo_width() <= view_right, \
                    (lang, txt, b.winfo_rootx() + b.winfo_width() - view_right)
            for key in ("settings.bilingual_pdf", "settings.rename_btn"):
                assert any(t(key, lang) == str(b.cget("text") or "")
                           for b in btns), (lang, key)
        finally:
            try:
                app.destroy()
            except Exception:
                pass
    set_setting("language", orig)
