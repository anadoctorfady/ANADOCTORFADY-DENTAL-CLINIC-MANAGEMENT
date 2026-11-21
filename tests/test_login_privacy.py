"""Round 13 item 1 (PRIVACY): no patient data is ever visible before login.

Regression test for the confirmed leak: App.__init__ used to build the
full main window and load_patients() and only then show the login
window, with NO withdraw() — the main window with real patient names
sat visible behind the login dialog. Fixed by withdraw() at startup,
deiconify() on successful login, withdraw() again on logout.

Isolation (test-gate skill): the LIVE clinic.db is copied to a temp
file, every call in this test runs against that copy, the temp copy is
deleted afterwards, and the live file's md5 is verified unchanged.
GUI tests need DISPLAY=:98 (Xvfb).
"""
import contextlib
import hashlib
import sqlite3
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest import mock

import src.models.database as DBmod
import src.ui.login as login_mod
from src.models.database import get_connection, init_db
from src.ui.shell import App
from src.utils.auth import hash_pw

LIVE_DB = Path.home() / ".config" / "ANADOCTORFADY" / "clinic.db"
TMP = Path(tempfile.mkdtemp(prefix="login_privacy_test_"))


def _md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


@contextlib.contextmanager
def isolated_live_copy():
    """Copy the live DB to temp, point the app at it, verify + delete."""
    live_md5 = _md5(LIVE_DB)
    db_path = TMP / "iso_clinic.db"
    for suf in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suf)
        if p.exists():
            p.unlink()
    # Consistent snapshot via the sqlite3 backup API (NOT a raw file
    # copy): another agent/process may be writing the live DB in WAL
    # mode concurrently, and a raw copy can miss -wal content and
    # produce a stale/partial DB that flips this test between runs.
    _src = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    _dst = sqlite3.connect(str(db_path))
    try:
        _src.backup(_dst)
    finally:
        _dst.close(); _src.close()
    old_db = DBmod.DB
    DBmod.DB = db_path
    try:
        init_db()
        # Deterministic login + a patient with NULL/empty fields so the
        # pre-login tree load exercises the null path too.
        conn = get_connection()
        conn.execute("UPDATE users SET password_hash=? WHERE username='fady'",
                     (hash_pw("1234"),))
        conn.execute("INSERT INTO patients(full_name, mobile1) "
                     "VALUES('Privacy Probe Patient', NULL)")
        conn.commit()
        conn.close()
        yield db_path
    finally:
        DBmod.DB = old_db
        for suf in ("", "-wal", "-shm"):
            p = Path(str(db_path) + suf)
            if p.exists():
                p.unlink()
        assert _md5(LIVE_DB) == live_md5, "LIVE clinic.db was modified!"


def _find_login(app):
    for w in app.winfo_children():
        if isinstance(w, tk.Toplevel) and hasattr(w, "e_user"):
            return w
    return None


def _wait_login(app, timeout=3.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.update()
        win = _find_login(app)
        if win is not None:
            return win
        time.sleep(0.05)
    raise AssertionError("login window did not appear")


def test_root_withdrawn_before_login():
    """Before login: root is withdrawn (not viewable) even though the
    app is built; ONLY the login window is viewable. (Round 16: the
    patient list is search-only, so the tree holds NO rows yet -- the
    seeded patient is in the DB, not in the tree.)"""
    with isolated_live_copy():
        app = App()
        try:
            # Withdrawn immediately at construction — no update/mainloop
            # needed, so there is no flash of the main window either.
            assert app.state() == "withdrawn", app.state()
            assert app.winfo_viewable() == 0
            # Search-only list (round 16): nothing is loaded behind
            # the curtain any more; the tree stays empty until a
            # search runs, yet nothing renders.
            assert len(app.tree.get_children()) == 0
            login = _wait_login(app)
            assert login.winfo_viewable() == 1
            assert login.winfo_ismapped() == 1
            # The login window is the only mapped top-level window.
            assert app.state() == "withdrawn"
            assert app.winfo_viewable() == 0
        finally:
            app.destroy()


def test_login_shows_main_logout_hides_again():
    """Full cycle: login -> main window visible; select a patient ->
    logout -> main window withdrawn again and login window shown."""
    with isolated_live_copy():
        app = App()
        try:
            login = _wait_login(app)
            assert app.state() == "withdrawn"
            with mock.patch.object(login_mod.messagebox, "showinfo"):
                login.e_user.delete(0, tk.END)
                login.e_user.insert(0, "fady")
                login.e_pass.delete(0, tk.END)
                login.e_pass.insert(0, "1234")
                login.do_login()
            app.update()
            assert login.winfo_exists() == 0
            assert app.state() == "normal", app.state()
            assert app.winfo_viewable() == 1
            # Exercise the logged-in state WITH a record selected, then
            # log out from that state (the selected-patient logout path).
            # Round 16: the list is search-only, so run a query first.
            app.search_var.set("Privacy")
            app.update()
            kids = app.tree.get_children()
            assert kids, "patient tree empty after login + search"
            app.tree.selection_set(kids[0])
            app.on_select()
            assert app.current_patient is not None
            app._logout()
            app.update()
            time.sleep(0.2)
            app.update()
            assert app.state() == "withdrawn", app.state()
            assert app.winfo_viewable() == 0
            login2 = _find_login(app)
            assert login2 is not None, "no login window after logout"
            assert login2.winfo_viewable() == 1
            # Re-login from the second login window restores the app.
            with mock.patch.object(login_mod.messagebox, "showinfo"):
                login2.e_user.delete(0, tk.END)
                login2.e_user.insert(0, "fady")
                login2.e_pass.delete(0, tk.END)
                login2.e_pass.insert(0, "1234")
                login2.do_login()
            app.update()
            assert app.state() == "normal", app.state()
            assert app.winfo_viewable() == 1
        finally:
            app.destroy()
