"""Password policy: self-change only; admin may change others; delete user."""
import json, os, sys, tempfile, threading, urllib.request, urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path
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
def test_self_change():
    url, srv, db = _start()
    try:
        t = _login(url, "fady", "1234")
        st, r = _req(url, "POST", "/auth/change-password", {"old_password": "1234", "new_password": "newpass"}, t); assert st == 200, r
        assert _req(url, "POST", "/auth/login", {"username": "fady", "password": "1234"})[0] == 401
        assert _login(url, "fady", "newpass")
        t2 = _login(url, "fady", "newpass")
        st, r = _req(url, "POST", "/auth/change-password", {"old_password": "wrong", "new_password": "x1234"}, t2); assert st == 401, r
        assert _login(url, "fady", "newpass")
        st, r = _req(url, "POST", "/auth/change-password", {"old_password": "newpass", "new_password": "abc"}, t2); assert st == 400, r
    finally:
        srv.shutdown(); srv.server_close(); os.unlink(db)
def test_admin_change_and_delete():
    url, srv, db = _start()
    try:
        admin = _login(url, "fady", "1234")
        st, r = _req(url, "POST", "/users", {"username": "doc1", "password": "docpass", "role": "doctor"}, admin); assert st == 201, r
        doc = _login(url, "doc1", "docpass")
        st, r = _req(url, "POST", "/auth/change-password", {"username": "fady", "new_password": "hacked"}, doc); assert st == 403, r
        st, r = _req(url, "POST", "/auth/change-password", {"username": "doc1", "new_password": "docnew"}, admin); assert st == 200, r
        assert _req(url, "POST", "/auth/login", {"username": "doc1", "password": "docpass"})[0] == 401
        assert _login(url, "doc1", "docnew")
        st, r = _req(url, "DELETE", "/users/doc1", token=admin); assert st == 200, r
        assert _req(url, "POST", "/auth/login", {"username": "doc1", "password": "docnew"})[0] == 401
        st, r = _req(url, "DELETE", "/users/nobody", token=admin); assert st == 404, r
        st, r = _req(url, "DELETE", "/users/fady", token=admin); assert st == 400, r
        assert _login(url, "fady", "1234")
    finally:
        srv.shutdown(); srv.server_close(); os.unlink(db)
