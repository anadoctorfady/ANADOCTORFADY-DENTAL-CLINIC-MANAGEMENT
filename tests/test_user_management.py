"""User management (2026-11-07): admin-only creation, local + server.
New users log in with their own name + password immediately."""
import os, sqlite3, sys, tempfile, threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from src.models.database import init_db, get_connection
from src.models.sync import SyncClient
from src.utils import auth
from src.utils.auth import (create_user, delete_user, hash_pw, list_users,
                            set_current_user, verify)
USERS = ("um_doc1", "um_nurse1", "um_admin2")
def _clean():
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE username IN (?,?,?)", USERS)
    conn.commit(); conn.close()
def _setup():
    init_db(); _clean()
    conn = get_connection()
    conn.execute("INSERT INTO users(username,password_hash,role,created_at)"
                 " VALUES(?,?,?,datetime('now'))", ("um_admin2", hash_pw("adminpw"), "admin"))
    conn.commit(); conn.close()
def test_admin_creates_and_new_user_logs_in():
    """Local creation works with no server; role stored; login immediate."""
    _setup()
    try:
        ok, msg = create_user("admin", "um_doc1", "docpass1", "doctor")
        assert ok, msg
        ok, msg = create_user("admin", "um_nurse1", "nursepass", "nurse")
        assert ok, msg
        assert verify("um_doc1", "docpass1") is True
        assert verify("um_nurse1", "nursepass") is True
        assert verify("um_doc1", "wrong") is False
        roles = dict(list_users())
        assert roles.get("um_doc1") == "doctor" and roles.get("um_nurse1") == "nurse"
        assert roles.get("um_admin2") == "admin"
    finally:
        _clean()
def test_non_admin_cannot_create():
    _setup()
    try:
        for role in ("doctor", "nurse", None):
            ok, msg = create_user(role, "um_doc1", "docpass1", "doctor")
            assert ok is False and "admin" in msg.lower()
        assert verify("um_doc1", "docpass1") is False
        assert "um_doc1" not in dict(list_users())
    finally:
        _clean()
def test_duplicate_name_refused():
    _setup()
    try:
        assert create_user("admin", "um_doc1", "docpass1", "doctor")[0] is True
        ok, msg = create_user("admin", "um_doc1", "otherpass", "nurse")
        assert ok is False and "exists" in msg.lower()
        assert verify("um_doc1", "docpass1") is True  # original kept
    finally:
        _clean()
def test_password_min_length_and_username_rules():
    _setup()
    try:
        assert create_user("admin", "um_doc1", "abc", "doctor")[0] is False
        assert create_user("admin", "um_doc1", "abcd", "doctor")[0] is True
        for bad in ("ab", "a b", "a/b", "", "x" * 33):
            assert create_user("admin", bad, "validpass", "doctor")[0] is False, bad
        assert create_user("admin", "um_doc1", "validpass", "superuser")[0] is False
    finally:
        _clean()
def test_delete_last_admin_refused():
    """Guard logic on an isolated DB (never touches the real fady admin):
    one admin -> delete refused; two admins -> delete allowed."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    conn = sqlite3.connect(tmp.name); conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT,"
                 " username TEXT UNIQUE, password_hash TEXT, role TEXT,"
                 " created_at TEXT)")
    conn.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                 ("solo", hash_pw("pw12"), "admin"))
    conn.commit()
    real = auth.get_connection
    def _tmp_conn():
        c = sqlite3.connect(tmp.name); c.row_factory = sqlite3.Row; return c
    auth.get_connection = _tmp_conn  # fresh conn per call: auth closes it
    try:
        ok, msg = delete_user("admin", "solo")
        assert ok is False and "last admin" in msg.lower()
        assert delete_user("doctor", "solo")[0] is False  # non-admin refused
        assert delete_user("admin", "ghost")[0] is False  # not found
        conn.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                     ("second", hash_pw("pw12"), "admin"))
        conn.commit()
        assert delete_user("admin", "solo")[0] is True
        assert delete_user("admin", "solo")[0] is False  # already gone
    finally:
        auth.get_connection = real; conn.close(); os.unlink(tmp.name)
def _start_server():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "server"))
    import sync_server
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    sync_server.DB_PATH = Path(tmp.name); sync_server.init_db(Path(tmp.name))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), sync_server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}", srv, tmp.name
def test_server_create_user():
    """POST /users (existing endpoint, admin-only): 201, 409 duplicate,
    403 non-admin, new user logs in, list shows them, last-admin delete
    refused (400)."""
    url, srv, db = _start_server()
    try:
        admin = SyncClient(url)
        ok, info = admin.login("fady", "1234"); assert ok, info
        ok, err = admin.create_user("um_doc1", "docpass1", "doctor", "main")
        assert ok, err
        ok, err = admin.create_user("um_doc1", "other", "doctor", "main")
        assert ok is False and err and "exists" in err.lower(), err
        doc = SyncClient(url)
        ok, info = doc.login("um_doc1", "docpass1")
        assert ok and info["role"] == "doctor", info
        ok, err = doc.create_user("um_doc2", "pass1234", "doctor", "main")
        assert ok is False, "non-admin must not create users"
        ok, users = admin.list_users()
        assert ok and any(u["username"] == "um_doc1" and u["role"] == "doctor"
                          and u["center_id"] == "main" for u in users), users
        ok, err = doc.list_users()
        assert ok is False  # GET /users is admin-only
        ok, err = admin.delete_user("fady")
        assert ok is False, "last admin must never be deleted"
        ok, err = admin.delete_user("um_doc1")
        assert ok, err
        assert SyncClient(url).login("um_doc1", "docpass1")[0] is False
    finally:
        srv.shutdown(); srv.server_close(); os.unlink(db)
def test_users_tab_hidden_for_non_admin():
    """Tab shows for admin, hides for doctor/nurse. Skipped with no
    display (headless CI); exercised under xvfb-run."""
    try:
        import tkinter as tk
        from tkinter import ttk
        root = tk.Tk(); root.withdraw()
    except Exception:
        return  # no display: skip GUI check
    try:
        from src.ui.users_tab import UsersTab
        _setup()
        nb = ttk.Notebook(root); nb.pack()
        tab = UsersTab(nb, app=None)
        nb.add(tab, text="  Users  ")
        set_current_user("fady")  # admin (from DB role)
        tab.refresh()
        assert nb.tab(tab, "state") == "normal"
        assert any(v[0] == "fady" for v in
                   [tab.tree.item(i, "values") for i in tab.tree.get_children()])
        set_current_user("um_doc1")  # unknown user -> "doctor" fallback role
        tab.refresh()
        assert nb.tab(tab, "state") == "hidden"
        set_current_user("fady")
        tab.refresh()
        assert nb.tab(tab, "state") == "normal"
    finally:
        _clean()
        try: root.destroy()
        except Exception: pass
