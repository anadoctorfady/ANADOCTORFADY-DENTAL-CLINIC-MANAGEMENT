"""Round 17 item 2: NO post-login "last login" modal.

Owner request: the messagebox.showinfo shown after every successful
login (previous-login / first-login-welcome) is removed entirely.
Last-login info remains ONLY inside the login box: record_login()
must still be called (so users.last_login updates) and the per-user
list on the login window (get_all_last_logins /
refresh_last_logins) must still be populated. Attendance
record_for_user(u, "in") is untouched (not asserted here beyond
login succeeding without error).

Isolation: TEMPORARY database (DB path patched, then restored).
Live clinic.db is never touched. GUI tests need DISPLAY=:98 (Xvfb).
"""
import contextlib
import tempfile
import tkinter as tk
from pathlib import Path
from unittest import mock

import src.models.database as DBmod
import src.ui.login as login_mod
from src.models.database import get_connection, init_db
from src.ui.login import LoginWindow
from src.utils.auth import get_all_last_logins, get_last_login

TMP = Path(tempfile.mkdtemp(prefix="r17_no_modal_"))


@contextlib.contextmanager
def isolated_db():
    db_path = TMP / "iso_clinic.db"
    for suf in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suf)
        if p.exists():
            p.unlink()
    old_db = DBmod.DB
    DBmod.DB = db_path
    try:
        init_db()
        yield db_path
    finally:
        DBmod.DB = old_db


def _set_last_login(username, when):
    conn = get_connection()
    conn.execute("UPDATE users SET last_login=? WHERE username=?",
                 (when, username))
    conn.commit(); conn.close()


def _do_login(root, lang="en"):
    win = LoginWindow(root, lang=lang)
    win.e_user.delete(0, tk.END); win.e_user.insert(0, "fady")
    win.e_pass.delete(0, tk.END); win.e_pass.insert(0, "1234")
    win.do_login()
    return win


def _label_texts(win):
    out, stack = [], list(win.winfo_children())
    while stack:
        w = stack.pop(); stack.extend(w.winfo_children())
        if w.winfo_class() == "Label":
            out.append(w.cget("text"))
    return out


def test_no_showinfo_on_login_with_previous():
    with isolated_db():
        _set_last_login("fady", "2026-11-08T09:30:00")
        root = tk.Tk()
        try:
            with mock.patch.object(login_mod.messagebox, "showinfo") as info:
                win = _do_login(root)
                assert win.result is True, "login should succeed"
                assert info.call_count == 0, (
                    f"showinfo must not be called during login, got {info.call_args_list}")
                assert win.winfo_exists() == 0
            # users.last_login was updated for the user
            new_when = get_last_login("fady")
            assert new_when is not None and new_when != "2026-11-08T09:30:00"
            # get_all_last_logins() still returns the row (login-window list)
            rows = get_all_last_logins()
            assert [u for u, _ in rows] == ["fady"] and rows[0][1] == new_when
            # ... and a fresh login window actually shows it in the list
            win2 = LoginWindow(root, lang="en")
            try:
                exp = f"fady — {new_when.replace('T', ' ')[:16]}"
                assert exp in _label_texts(win2)
            finally:
                win2.destroy()
        finally:
            root.destroy()


def test_no_showinfo_on_first_login():
    with isolated_db():
        _set_last_login("fady", None)
        assert get_last_login("fady") is None
        root = tk.Tk()
        try:
            with mock.patch.object(login_mod.messagebox, "showinfo") as info:
                win = _do_login(root)
                assert win.result is True
                assert info.call_count == 0, "first-login welcome modal must be gone"
            assert get_last_login("fady") is not None
            assert [u for u, _ in get_all_last_logins()] == ["fady"]
        finally:
            root.destroy()


def test_no_showinfo_on_login_arabic():
    with isolated_db():
        _set_last_login("fady", "2026-11-08T09:30:00")
        root = tk.Tk()
        try:
            with mock.patch.object(login_mod.messagebox, "showinfo") as info:
                win = _do_login(root, lang="ar")
                assert win.result is True
                assert info.call_count == 0
            assert get_last_login("fady") != "2026-11-08T09:30:00"
        finally:
            root.destroy()
