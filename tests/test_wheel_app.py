"""Round 14 wheel audit: end-to-end wheel check in the real App.

Build order in App is PatientForm -> ClinicalTab -> SettingsTab, so
this is the exact configuration where the old bind_all bug left only
the settings handler alive. Runs against a backup-API copy of the
live DB (live md5 verified unchanged); the test itself only reads.
"""
import contextlib
import hashlib
import sqlite3
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import src.models.database as DBmod

LIVE_DB = Path.home() / ".config" / "ANADOCTORFADY" / "clinic.db"


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def _canvas_of(tab, widget):
    w = widget
    while w is not None:
        if isinstance(w, tk.Canvas) and w.cget("yscrollcommand"):
            return w
        w = w.master
    return None


def _down_up(root, widget, view):
    before = view()
    widget.event_generate("<MouseWheel>", delta=-120)
    root.update()
    assert view()[0] > before[0], f"MouseWheel down did not scroll {widget}"
    widget.event_generate("<Button-5>")
    root.update()
    assert view()[0] > before[0], "Button-5 did not scroll down"
    mid = view()
    widget.event_generate("<MouseWheel>", delta=120)
    root.update()
    assert view()[0] < mid[0], "MouseWheel up did not scroll back"
    widget.event_generate("<Button-4>")
    root.update()
    assert view()[0] < mid[0], "Button-4 did not scroll back"


@contextlib.contextmanager
def _isolated_db():
    """Backup-API copy of the live DB; live md5 verified unchanged."""
    live_md5 = hashlib.md5(LIVE_DB.read_bytes()).hexdigest()
    tmp = Path(tempfile.mkdtemp(prefix="wheel_app_")) / "iso.db"
    src = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    dst = sqlite3.connect(str(tmp))
    try:
        src.backup(dst)
    finally:
        dst.close(); src.close()
    old = DBmod.DB
    DBmod.DB = tmp
    try:
        yield
    finally:
        DBmod.DB = old
        tmp.unlink(missing_ok=True)
        assert hashlib.md5(LIVE_DB.read_bytes()).hexdigest() == live_md5


def test_full_app_wheel():
    """Patient tree, clinical page and settings page must ALL scroll
    with the wheel in one real App process."""
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_full_app_wheel (no display)")
        return
    root.deiconify()
    root.geometry("1380x900")
    root.update()
    with _isolated_db():
        from src.ui.shell import App
        app = App()
        try:
            app.deiconify()
            for w in list(app.winfo_children()):
                if "loginwindow" in str(w):
                    w.destroy()  # release the modal grab
            app.update()
            for i in range(120):
                app.tree.insert("", "end", values=(9000 + i, f"Wheel {i}", "000"))
            app.update()
            assert app.tree.yview()[1] < 1.0, "patient list not scrollable"
            _down_up(app, app.tree, app.tree.yview)
            nb = next(w for w in _walk(app) if isinstance(w, ttk.Notebook))
            nb.select(app.clinical)
            app.update()
            # Round 19: page canvas anchored by the history section
            # (input tables now live in a fixed, canvas-less block).
            canvas = _canvas_of(app.clinical, app.clinical.history_section)
            assert canvas.yview()[1] < 1.0, "clinical page not scrollable"
            s0 = app.settings._canvas.yview()
            _down_up(app, app.clinical.history_section, canvas.yview)
            assert app.settings._canvas.yview() == s0, "clinical wheel moved settings"
            nb.select(app.settings)
            app.update()
            _down_up(app, app.settings.body, app.settings._canvas.yview)
        finally:
            app.destroy()
