"""ANADOCTORFADY sync server - multi-device online sync (stdlib only).
SQLite DB next to this file (default server/clinic_sync.db). Offline-first,
last-write-wins on updated_at. Run:
  python server/sync_server.py [--port 8001] [--db server/clinic_sync.db]
Default admin fady / 1234 (admin, center 'main') - change its password
via POST /auth/change-password or delete it after creating a new admin.
"""
import argparse, json, secrets, sqlite3
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from auth import (create_default_admin, hash_password, verify_password,
                  change_user_password, delete_user, rename_user)
from sync_helpers import ensure_seq, merge, now_iso, rows_dict, upsert_sync
from delta_pull import delta_pull
from finance_sync import (init_tables as init_fin_tables, pull_financials,
                          pull_employees, push_financials, push_employees,
                          init_referral_tables, pull_referrals, push_referrals)
MAX_BODY = 5 * 1024 * 1024
TOKEN_TTL = timedelta(hours=24)
TOKENS = {}  # token -> {username, role, center_id, expires}
DB_PATH = Path(__file__).resolve().parent / "clinic_sync.db"
def init_db(p):
    c = sqlite3.connect(str(p))
    c.executescript("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,
      username TEXT UNIQUE, password_hash TEXT, salt TEXT, role TEXT,
      center_id TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS patients_sync(id INTEGER PRIMARY KEY,
      patient_file TEXT UNIQUE, center_id TEXT, data_json TEXT,
      updated_at TEXT, updated_by TEXT);
    CREATE TABLE IF NOT EXISTS visits_sync(id INTEGER PRIMARY KEY,
      record_id TEXT UNIQUE, patient_file TEXT, center_id TEXT, kind TEXT,
      data_json TEXT, updated_at TEXT, updated_by TEXT);
    CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY,
      username TEXT, center_id TEXT, action TEXT, ts TEXT, device_id TEXT);""")
    init_fin_tables(c); init_referral_tables(c); ensure_seq(c)
    created = create_default_admin(c); c.close(); return created
def db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout=5000")  # R39: seq counters serialize writers
    return conn
def issue_token(u):
    t = secrets.token_hex(32)
    TOKENS[t] = {"username": u["username"], "role": u["role"],
                 "center_id": u["center_id"],
                 "expires": datetime.now(timezone.utc) + TOKEN_TTL}
    return t
def check_token(t):
    info = TOKENS.get(t or "")
    if not info or info["expires"] < datetime.now(timezone.utc):
        TOKENS.pop(t or "", None); return None
    return info
class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY: return None
        try: data = json.loads((self.rfile.read(length) if length else b"{}").decode("utf-8"))
        except Exception: return False
        return data if isinstance(data, dict) else False
    def _auth(self):
        a = self.headers.get("Authorization") or ""
        user = check_token(a[7:] if a.startswith("Bearer ") else "")
        if not user: self._json(401, {"ok": False, "error": "unauthorized / غير مصرح"})
        return user
    def _admin(self, user):
        if user and user["role"] == "admin": return True
        self._json(403, {"ok": False, "error": "admin only / للمدراء فقط"}); return False
    def do_GET(self):
        parsed = urlparse(self.path); path, q = parsed.path, parse_qs(parsed.query)
        if path == "/health": return self._json(200, {"ok": True})
        user = self._auth()
        if not user: return
        conn = db()
        if path == "/sync/pull":
            if "server_id" in q or any(k.startswith("seq_") for k in q):
                res = delta_pull(conn, user, q)  # R39 delta mode
                conn.close(); return self._json(200, res)
            since = q.get("since", [""])[0]; center = q.get("center_id", [user["center_id"]])[0]
            p = [merge(r, 2, {"patient_file": 0, "center_id": 1, "updated_at": 3, "updated_by": 4})
                 for r in conn.execute("SELECT patient_file, center_id, data_json, updated_at,"
                 " updated_by FROM patients_sync WHERE center_id=? AND updated_at>? ORDER BY updated_at", (center, since))]
            v = [merge(r, 4, {"record_id": 0, "patient_file": 1, "center_id": 2, "kind": 3, "updated_at": 5, "updated_by": 6})
                 for r in conn.execute("SELECT record_id, patient_file, center_id, kind, data_json,"
                 " updated_at, updated_by FROM visits_sync WHERE center_id=? AND updated_at>? ORDER BY updated_at", (center, since))]
            f = pull_financials(conn, user, since); e = pull_employees(conn, user, since)
            r = pull_referrals(conn, user, since, center)
            conn.close(); return self._json(200, {"patients": p, "visits": v, "financials": f, "employees": e, "referrals": r})
        if path == "/attendance":
            if not self._admin(user): conn.close(); return
            center, date = q.get("center_id", [""])[0], q.get("date", [""])[0]
            out = rows_dict(conn, "SELECT username, center_id, action, ts, device_id FROM attendance"
                " WHERE (?='' OR center_id=?) AND (?='' OR substr(ts,1,10)=?) ORDER BY ts",
                (center, center, date, date), ("username", "center_id", "action", "ts", "device_id"))
            conn.close(); return self._json(200, {"entries": out})
        if path == "/users":
            if not self._admin(user): conn.close(); return
            out = rows_dict(conn, "SELECT id, username, role, center_id, created_at FROM users ORDER BY username",
                (), ("id", "username", "role", "center_id", "created_at"))
            conn.close(); return self._json(200, {"users": out})
        conn.close(); self._json(404, {"ok": False, "error": "not found"})
    def do_POST(self):
        path = urlparse(self.path).path; data = self._body()
        if data is None: return self._json(413, {"ok": False, "error": "body too large"})
        if data is False: return self._json(400, {"ok": False, "error": "bad json"})
        if path == "/auth/login": return self._login(data)
        user = self._auth()
        if not user: return
        if path == "/auth/change-password": return self._change_password(data, user)
        if path.startswith("/users/") and path.endswith("/rename"): return self._rename_user(path, data, user)
        if path == "/sync/push": return self._push(data, user)
        if path == "/attendance": return self._attendance(data, user)
        if path == "/users": return self._create_user(data, user)
        self._json(404, {"ok": False, "error": "not found"})
    def do_DELETE(self):
        user = self._auth()
        if not user: return
        path = urlparse(self.path).path
        if path.startswith("/users/") and self._admin(user):
            target = path[len("/users/"):]
            conn = db(); ok, err = delete_user(conn, target); conn.close()
            if not ok:
                return self._json(404 if "not found" in err else 400, {"ok": False, "error": err})
            return self._json(200, {"ok": True, "username": target})
        self._json(404, {"ok": False, "error": "not found"})
    def _rename_user(self, path, data, user):
        if not self._admin(user): return
        old = path[len("/users/"):-len("/rename")]
        conn = db(); st, err = rename_user(conn, user, old, data.get("new_username")); conn.close()
        if st != 200: return self._json(st, {"ok": False, "error": err})
        self._json(200, {"ok": True, "username": data.get("new_username")})
    def _change_password(self, data, user):
        conn = db(); target = data.get("username") or user["username"]
        st, err = change_user_password(conn, user, target, data.get("old_password"), data.get("new_password"))
        conn.close()
        if st != 200: return self._json(st, {"ok": False, "error": err})
        self._json(200, {"ok": True})
    def _login(self, data):
        conn = db()
        row = conn.execute("SELECT username, password_hash, salt, role, center_id FROM users WHERE username=?", (data.get("username") or "",)).fetchone(); conn.close()
        if not row or not verify_password(data.get("password") or "", row[2], row[1]):
            return self._json(401, {"ok": False, "error": "wrong username or password / اسم أو كلمة مرور خاطئة"})
        u = {"username": row[0], "role": row[3], "center_id": row[4]}
        self._json(200, {"ok": True, "token": issue_token(u), **u})
    def _push(self, data, user):
        conn = db(); applied = 0
        st, res = push_financials(conn, data.get("financials") or [], user)
        if st != 200: conn.close(); return self._json(st, {"ok": False, "error": res})
        applied += res
        st, res = push_employees(conn, data.get("employees") or [], user)
        if st != 200: conn.close(); return self._json(st, {"ok": False, "error": res})
        applied += res
        st, res = push_referrals(conn, data.get("referrals") or [], user)
        if st != 200: conn.close(); return self._json(st, {"ok": False, "error": res})
        applied += res
        for item in data.get("patients") or []:
            if isinstance(item, dict) and item.get("patient_file"): applied += upsert_sync(conn, item, user, True)
        for item in data.get("visits") or []:
            if isinstance(item, dict) and item.get("record_id"): applied += upsert_sync(conn, item, user, False)
        conn.commit(); conn.close(); return self._json(200, {"ok": True, "applied": applied})
    def _attendance(self, data, user):
        if data.get("action") not in ("in", "out"): return self._json(400, {"ok": False, "error": "action must be 'in' or 'out'"})
        ts = now_iso(); conn = db()
        conn.execute("INSERT INTO attendance(username, center_id, action, ts, device_id) VALUES (?,?,?,?,?)",
                     (user["username"], user["center_id"], data["action"], ts, data.get("device_id") or ""))
        conn.commit(); conn.close(); return self._json(200, {"ok": True, "ts": ts})
    def _create_user(self, data, user):
        if not self._admin(user): return
        if not data.get("username") or not data.get("password"):
            return self._json(400, {"ok": False, "error": "username and password required"})
        pw, salt = hash_password(data["password"]); conn = db()
        try:
            conn.execute("INSERT INTO users(username, password_hash, salt, role, center_id, created_at) VALUES (?,?,?,?,?, datetime('now'))", (data["username"], pw, salt, data.get("role") or "user", data.get("center_id") or user["center_id"]))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close(); return self._json(409, {"ok": False, "error": "username already exists"})
        conn.close()
        self._json(201, {"ok": True, "username": data["username"], "role": data.get("role") or "user",
                         "center_id": data.get("center_id") or user["center_id"]})
    def log_message(self, *a): pass
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ANADOCTORFADY sync server")
    ap.add_argument("--port", type=int, default=8001); ap.add_argument("--db", default=None)
    args = ap.parse_args()
    if args.db: DB_PATH = Path(args.db)
    created = init_db(DB_PATH)
    print(f"Sync server on http://localhost:{args.port}  (db: {DB_PATH})", flush=True)
    print("Default admin: fady / 1234 (admin, center 'main')" + (" - just created" if created else " - already exists") + "\nFirst hosting: create a new admin, verify its login, then change fady's password (POST /auth/change-password) or delete fady (DELETE /users/fady). Do NOT open the port to the internet before that.", flush=True)
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()
