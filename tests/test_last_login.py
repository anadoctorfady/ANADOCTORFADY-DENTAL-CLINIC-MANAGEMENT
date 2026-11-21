"""Job 6: last login on this device + attendance view verification.

Round 17 item 2 supersedes the round-12 modal behaviour: the
post-login "last login" messagebox is GONE. record_login() is still
called on every successful login (so users.last_login updates and
the per-user list on the login window stays populated), but NO
showinfo modal is shown during login, in any language.

Isolation: every test runs against a TEMPORARY database (DB path
patched in src.models.database for the test, then restored). The live
clinic.db is never touched. GUI tests need DISPLAY=:101 (Xvfb).
"""
import contextlib
import tempfile
import tkinter as tk
from pathlib import Path
from unittest import mock

import src.models.database as DBmod
import src.ui.attendance_view as av_mod
import src.ui.login as login_mod
from src.config.strings import t
from src.models.attendance import record_attendance
from src.models.database import get_connection, init_db
from src.ui.attendance_view import open_attendance_view
from src.ui.login import LoginWindow
from src.utils.auth import get_last_login, record_login, verify

TMP = Path(tempfile.mkdtemp(prefix="lastlogin_test_"))


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


def test_record_login_updates():
    with isolated_db():
        # first login ever on this device: no previous value
        assert get_last_login("fady") is None
        assert record_login("fady") is None
        first = get_last_login("fady")
        assert first and "T" in first
        # second login returns the previous timestamp and stores a new
        # one (same-second logins may store the identical second value)
        assert record_login("fady") == first
        assert get_last_login("fady") >= first
        # a FAILED login must not touch last_login
        assert verify("fady", "wrong") is False
        assert get_last_login("fady") is not None
        # unknown user: None, never raises
        assert get_last_login("ghost") is None
        assert record_login("ghost") is None


def _login_window(root, lang="en"):
    win = LoginWindow(root, lang=lang)
    win.e_user.delete(0, tk.END)
    win.e_user.insert(0, "fady")
    win.e_pass.delete(0, tk.END)
    win.e_pass.insert(0, "1234")
    return win


def test_login_window_shows_previous():
    # Name kept from round 12; round 17: previous login is NOT shown
    # in a modal any more — login succeeds silently, last_login updates.
    with isolated_db():
        conn = get_connection()
        conn.execute("UPDATE users SET last_login='2026-11-08T09:30:00' WHERE username='fady'")
        conn.commit(); conn.close()
        root = tk.Tk()
        try:
            with mock.patch.object(login_mod.messagebox, "showinfo") as info:
                win = _login_window(root)
                win.do_login()
                assert win.result is True
                assert info.call_count == 0, "post-login modal must be gone"
                assert win.winfo_exists() == 0  # window closed after login
            # the stored value is now the new login, not the old one
            assert get_last_login("fady") != "2026-11-08T09:30:00"
            assert get_last_login("fady") is not None
        finally:
            root.destroy()


def test_login_window_first_login():
    # Round 17: first login shows NO welcome modal either.
    with isolated_db():
        conn = get_connection()
        conn.execute("UPDATE users SET last_login=NULL WHERE username='fady'")
        conn.commit(); conn.close()
        root = tk.Tk()
        try:
            with mock.patch.object(login_mod.messagebox, "showinfo") as info:
                win = _login_window(root)
                win.do_login()
                assert win.result is True
                assert info.call_count == 0, "first-login modal must be gone"
            assert get_last_login("fady") is not None
        finally:
            root.destroy()


def test_login_window_arabic_message():
    # Name kept from round 12; round 17: Arabic login also shows NO modal.
    with isolated_db():
        conn = get_connection()
        conn.execute("UPDATE users SET last_login='2026-11-08T09:30:00' WHERE username='fady'")
        conn.commit(); conn.close()
        root = tk.Tk()
        try:
            with mock.patch.object(login_mod.messagebox, "showinfo") as info:
                win = _login_window(root, lang="ar")
                win.do_login()
                assert win.result is True
                assert info.call_count == 0, "Arabic post-login modal must be gone"
            assert get_last_login("fady") != "2026-11-08T09:30:00"
        finally:
            root.destroy()


def _tree_rows(win):
    """All Treeview widgets under `win`, as [values] rows."""
    out = []
    stack = list(win.winfo_children())
    while stack:
        w = stack.pop()
        stack.extend(w.winfo_children())
        if w.winfo_class() == "Treeview":
            out.extend(w.item(i)["values"] for i in w.get_children())
    return out


def test_attendance_view_device_and_admin():
    with isolated_db():
        conn = get_connection()
        record_attendance(conn, "fady", "in", "dev-123")
        record_attendance(conn, "nurse1", "out", "dev-999")
        conn.close()
        root = tk.Tk()
        try:
            # admin sees the view AND the device column
            win = open_attendance_view(root, "admin", lang="en")
            assert win is not None
            try:
                rows = _tree_rows(win)
                devices = [str(r[3]) for r in rows]
                assert "dev-123" in devices and "dev-999" in devices
                users = [str(r[0]) for r in rows]
                assert "fady" in users and "nurse1" in users
            finally:
                win.destroy()
            # non-admin: refused, no window, admin-only message shown
            with mock.patch.object(av_mod.messagebox, "showinfo") as info:
                assert open_attendance_view(root, "doctor", lang="en") is None
                assert open_attendance_view(root, "nurse", lang="en") is None
                assert info.call_count == 2
        finally:
            root.destroy()
