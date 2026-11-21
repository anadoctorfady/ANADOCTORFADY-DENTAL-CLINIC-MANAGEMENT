"""Username rule: own-name login; only admin may rename a username."""
import json, os, sys, tempfile, threading, urllib.request, urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path
from src.models.database import init_db, get_connection
from src.utils.auth import rename_user, valid_username, verify, hash_pw
def _start():
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "server"))
    import sync_server
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    sync_server.DB_PATH = Path(tmp.name); sync_server.init_db(Path(tmp.name))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), sync_server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}", srv, tmp.name
def _req(url, method, path, body=None, token=None):
    h = {"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})}
    req = urllib.request.Request(url + path, data=json.dumps(body or {}).encode(), method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=5) as r: return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read().decode() or "{}")
def _login(url, u, p):
    st, r = _req(url, "POST", "/auth/login", {"username": u, "password": p})
    assert st == 200, r
    return r["token"]
def test_local_rename():
    init_db()
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE username IN ('doc1','doc2')")
    conn.execute("INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,datetime('now'))", ("doc1", hash_pw("docpass"), "doctor"))
    conn.commit(); conn.close()
    assert rename_user("doc1", "doctor", "doc1", "doc2")[0] is False
    assert verify("doc1", "docpass") is True
    assert rename_user("fady", "admin", "doc1", "doc2")[0] is True
    assert verify("doc2", "docpass") is True and verify("doc1", "docpass") is False
    assert rename_user("fady", "admin", "doc2", "fady")[0] is False
    assert rename_user("fady", "admin", "doc2", "a b")[0] is False
    assert valid_username("ab") is False and valid_username("ok_name-1") is True
def test_server_rename():
    url, srv, db = _start()
    try:
        admin = _login(url, "fady", "1234")
        st, r = _req(url, "POST", "/users", {"username": "doc1", "password": "docpass", "role": "doctor"}, admin); assert st == 201, r
        doc = _login(url, "doc1", "docpass")
        st, r = _req(url, "POST", "/users/doc1/rename", {"new_username": "docX"}, doc); assert st == 403, r
        assert _login(url, "doc1", "docpass")
        st, r = _req(url, "POST", "/users/fady/rename", {"new_username": "root"}, doc); assert st == 403, r
        st, r = _req(url, "POST", "/users/doc1/rename", {"new_username": "doc2"}, admin); assert st == 200, r
        assert _req(url, "POST", "/auth/login", {"username": "doc1", "password": "docpass"})[0] == 401
        assert _login(url, "doc2", "docpass")
        st, r = _req(url, "POST", "/users/doc2/rename", {"new_username": "fady"}, admin); assert st == 409, r
        st, r = _req(url, "POST", "/users/nobody/rename", {"new_username": "x1y"}, admin); assert st == 404, r
        for bad in ("", "ab", "a b"):
            st, r = _req(url, "POST", "/users/doc2/rename", {"new_username": bad}, admin); assert st == 400, (bad, r)
        assert _login(url, "doc2", "docpass")
    finally:
        srv.shutdown(); srv.server_close(); os.unlink(db)
