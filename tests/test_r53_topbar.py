"""Round 53, Section C: top-bar pills must not shrink under their text.

Root cause (owner's AR screenshot, reproduced here at tk scaling 2.0):
an Amiri 10pt pill needs a ~48px image, but the 48px bar with pady=8
allocates only 32px, and RoundedButton._on_resize re-rendered the
image at the allocated size -- the text then spilled past the pill
while the English pills (smaller text) looked fine. Fix: _on_resize
never renders below the measured content size, and the bar grows to
fit its tallest child (pill reqheight + 16, title linespace).
Pinned at tk scaling 1.0 and 2.0, EN and AR.
"""
import time
import tkinter as tk
from tkinter import messagebox

from src.models.database import get_setting, set_setting
from src.ui import rounded as _rounded


def _display_available():
    try:
        r = tk.Tk(); r.withdraw(); r.destroy()
        return True
    except Exception:
        return False


def _check_topbar(app):
    bar = app._topbar_frame
    pills = [c for c in bar.winfo_children()
             if c.winfo_class() == "Button" and c.winfo_ismapped()]
    assert pills, "no top-bar pills found"
    win_right = app.winfo_rootx() + app.winfo_width()
    need = max(c.winfo_reqheight() + (16 if c.winfo_class() == "Button" else 0)
               for c in bar.winfo_children())
    assert bar.winfo_height() >= need, (bar.winfo_height(), need)
    rects = []
    for p in pills:
        img = p._images["normal"]
        assert img.width() >= p._content_size[0], (p._text, img.width(), p._content_size)
        assert img.height() >= p._content_size[1], (p._text, img.height(), p._content_size)
        assert p.winfo_height() >= img.height(), (p._text, p.winfo_height(), img.height())
        assert p.winfo_rootx() + p.winfo_width() <= win_right, p._text
        rects.append((p.winfo_rootx(), p.winfo_rooty(),
                      p.winfo_rootx() + p.winfo_width(),
                      p.winfo_rooty() + p.winfo_height()))
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            a, b = rects[i], rects[j]
            assert not (a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]), (a, b)
    title = [c for c in bar.winfo_children()
             if c.winfo_class() == "Label" and "ANADOCTORFADY" in str(c.cget("text"))]
    assert title, "title label missing"
    assert bar.winfo_height() >= title[0].winfo_reqheight(), (
        bar.winfo_height(), title[0].winfo_reqheight())


def _login_app(lang, scaling=None):
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


def test_r53_topbar_pills_fit_ar():
    if not _display_available():
        return
    for scaling in (None, 2.0):
        app, orig = _login_app("ar", scaling)
        try:
            _check_topbar(app)
        finally:
            _close(app, orig)


def test_r53_topbar_pills_fit_en():
    if not _display_available():
        return
    app, orig = _login_app("en", 2.0)
    try:
        _check_topbar(app)
    finally:
        _close(app, orig)


def test_r53_pill_never_shrinks_below_text():
    """Unit pin for the _on_resize floor: a RoundedButton squeezed
    into a 10px-tall frame keeps its measured image size."""
    if not _display_available():
        return
    from src.ui import amiri as _amiri
    root = tk.Tk(); root.withdraw()
    try:
        fam = "Amiri" if _amiri.amiri_available(root) else "Segoe UI"
        text = "تسجيل الخروج" if fam == "Amiri" else "Logout now please"
        from src.ui.rounded import RoundedButton
        outer = tk.Frame(root, height=10); outer.pack(); outer.pack_propagate(False)
        b = RoundedButton(outer, text=text, font=(fam, 10))
        b.pack()
        root.update()
        assert b._images["normal"].height() >= b._content_size[1], (
            b._images["normal"].height(), b._content_size)
        assert b._images["normal"].width() >= b._content_size[0]
        outer.config(height=6); root.update()
        assert b._images["normal"].height() >= b._content_size[1], (
            "pill shrank under its text", b._images["normal"].height(),
            b._content_size)
    finally:
        try:
            root.destroy()
        except Exception:
            pass
