"""Item D: per-user last-login list on the login window (this device).
Isolation: every test runs against a TEMPORARY database (DB path patched
in src.models.database, then restored). Live clinic.db never touched.
GUI tests need DISPLAY=:98 (Xvfb)."""
import contextlib
import tempfile
import tkinter as tk
from pathlib import Path
from unittest import mock

import src.models.database as DBmod
import src.ui.login as login_mod
from src.models.database import get_connection, init_db
from src.ui.login import LoginWindow
from src.utils.auth import get_all_last_logins, get_last_login, hash_pw

TMP = Path(tempfile.mkdtemp(prefix="lastlogin_list_test_"))


@contextlib.contextmanager
def isolated_db():
    db_path = TMP / "iso_clinic.db"
    for suf in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suf)
        if p.exists(): p.unlink()
    old_db = DBmod.DB
    DBmod.DB = db_path
    try:
        init_db()
        yield db_path
    finally:
        DBmod.DB = old_db


def _add_user(username, last_login=None):
    conn = get_connection()
    conn.execute("INSERT INTO users(username, password_hash, role, last_login) VALUES(?,?,?,?)",
                 (username, hash_pw("1234"), "doctor", last_login))
    conn.commit(); conn.close()


def _set_last_login(username, when):
    conn = get_connection()
    conn.execute("UPDATE users SET last_login=? WHERE username=?", (when, username))
    conn.commit(); conn.close()


def _label_texts(win):
    """All Label texts under `win` (walk the widget tree)."""
    out, stack = [], list(win.winfo_children())
    while stack:
        w = stack.pop(); stack.extend(w.winfo_children())
        if w.winfo_class() == "Label": out.append(w.cget("text"))
    return out


def test_get_all_last_logins_ordered():
    with isolated_db():
        _set_last_login("fady", "2026-11-08T09:30:00")
        _add_user("nurse1", "2026-11-09T08:00:00"); _add_user("doc2", "2026-11-09T10:15:00")
        _add_user("never1", None)  # never logged in on this device
        rows = get_all_last_logins()
        assert [u for u, _ in rows] == ["doc2", "nurse1", "fady"] and rows[0][1] == "2026-11-09T10:15:00"
        assert "never1" not in [u for u, _ in rows]


def test_get_all_last_logins_empty():
    with isolated_db():
        # fresh DB: fady exists but never logged in -> empty list
        assert get_all_last_logins() == [] and get_last_login("ghost") is None


def test_login_window_shows_list_en():
    with isolated_db():
        _set_last_login("fady", "2026-11-08T09:30:00")
        _add_user("nurse1", "2026-11-09T08:00:00")
        root = tk.Tk()
        try:
            win = LoginWindow(root, lang="en")
            try:
                texts = _label_texts(win)
                assert "Last login on this device" in texts
                assert "fady — 2026-11-08 09:30" in texts and "nurse1 — 2026-11-09 08:00" in texts
            finally:
                win.destroy()
        finally:
            root.destroy()


def test_login_window_shows_list_ar():
    with isolated_db():
        _set_last_login("fady", "2026-11-08T09:30:00")
        _add_user("nurse1", "2026-11-09T08:00:00")
        root = tk.Tk()
        try:
            win = LoginWindow(root, lang="ar")
            try:
                texts = _label_texts(win)
                assert "آخر تسجيل دخول على هذا الجهاز" in texts
                assert "fady — 2026-11-08 09:30" in texts and "nurse1 — 2026-11-09 08:00" in texts
            finally:
                win.destroy()
        finally:
            root.destroy()


def test_login_window_empty_list():
    with isolated_db():
        root = tk.Tk()
        try:
            win = LoginWindow(root, lang="en")
            try:
                assert "No logins yet on this device" in _label_texts(win)
            finally:
                win.destroy()
            win = LoginWindow(root, lang="ar")
            try:
                assert "لا توجد عمليات تسجيل دخول بعد على هذا الجهاز" in _label_texts(win)
            finally:
                win.destroy()
        finally:
            root.destroy()


def test_list_shows_all_rows():
    """Round 13 item 3: the 6-row cap is REMOVED — all users who ever
    logged in on this device are shown, most recent first, no '+N more'."""
    with isolated_db():
        for i in range(8): _add_user(f"user{i}", f"2026-11-09T0{i}:00:00")
        root = tk.Tk()
        try:
            win = LoginWindow(root, lang="en")
            try:
                texts = _label_texts(win)
                shown = [x for x in texts if x.startswith("user")]
                assert len(shown) == 8, shown
                assert "user7 — 2026-11-09 07:00" in texts and "user0 — 2026-11-09 00:00" in texts
                assert not [x for x in texts if x.startswith("+") and "more" in x]
            finally:
                win.destroy()
        finally:
            root.destroy()


def test_list_is_scrollable():
    """Round 13 item 3: with more rows than fit, the list is a Canvas +
    Scrollbar whose scrollregion is taller than the canvas, and it
    scrolls to the bottom showing all 12 rows."""
    with isolated_db():
        for i in range(12): _add_user(f"user{i:02d}", f"2026-11-09T{i:02d}:00:00")
        root = tk.Tk()
        try:
            win = LoginWindow(root, lang="en")
            try:
                win.update_idletasks(); win.update()
                allw, stack = [], list(win.winfo_children())
                while stack:
                    w = stack.pop(); allw.append(w); stack.extend(w.winfo_children())
                cvs = [w for w in allw if isinstance(w, tk.Canvas)]
                assert cvs, "no Canvas in login window"
                assert [w for w in allw if isinstance(w, tk.Scrollbar)], "no Scrollbar"
                _, _, _, y1 = cvs[0].bbox("all")
                assert y1 > cvs[0].winfo_height(), "scrollregion not taller than canvas"
                cvs[0].yview_moveto(1.0); win.update()
                assert cvs[0].yview()[0] > 0, "canvas did not scroll to bottom"
                assert len([x for x in _label_texts(win) if x.startswith("user")]) == 12
            finally:
                win.destroy()
        finally:
            root.destroy()


def test_list_refreshes_after_login():
    with isolated_db():
        _set_last_login("fady", "2026-11-08T09:30:00")
        root = tk.Tk()
        try:
            with mock.patch.object(login_mod.messagebox, "showinfo") as info:
                win = LoginWindow(root, lang="en")
                win.e_user.delete(0, tk.END)
                win.e_user.insert(0, "fady")
                win.e_pass.delete(0, tk.END)
                win.e_pass.insert(0, "1234")
                win.do_login()
                assert win.result is True
                # Round 17 item 2: the post-login modal is REMOVED --
                # last-login info lives only in the login window list.
                assert info.call_count == 0
            # next login window reads the fresh value from the DB
            new_when = get_last_login("fady")
            assert new_when != "2026-11-08T09:30:00"
            win2 = LoginWindow(root, lang="en")
            try:
                texts = _label_texts(win2)
                assert f"fady — {new_when.replace('T', ' ')[:16]}" in texts
                assert "fady — 2026-11-08 09:30" not in texts
            finally:
                win2.destroy()
        finally:
            root.destroy()
