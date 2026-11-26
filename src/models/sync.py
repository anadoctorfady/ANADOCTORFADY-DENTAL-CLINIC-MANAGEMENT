"""Sync client (Phase 4). Offline-first: queue, push when online, pull
last-write-wins on updated_at. Never raises on network failure.
Records keep author + center_id; patients shared, finance role-filtered
server-side (admin all centers / doctor own income / nurse none)."""
import json, threading, urllib.request, urllib.error
from datetime import datetime
from urllib.parse import urlencode
from src.models.sync_apply import VT, _apply_visit, _upsert  # noqa: F401
from src.models.finance_sync import (apply_financial_pull,
                                     ensure_finance_columns, split_financial_queue)
def _now(): return datetime.now().isoformat(timespec="seconds")
def ensure_tables(conn):
    conn.cursor().execute("""CREATE TABLE IF NOT EXISTS sync_queue(
        id INTEGER PRIMARY KEY AUTOINCREMENT, table_name TEXT, record_id TEXT,
        payload_json TEXT, updated_at TEXT, synced INT DEFAULT 0,
        UNIQUE(table_name, record_id))""")
    for t in ("complaints", "diagnoses", "procedures", "patient_notes", "patients"):
        try: conn.cursor().execute(f"ALTER TABLE {t} ADD COLUMN updated_at TEXT")
        except Exception: pass  # already exists / table not created yet
    ensure_finance_columns(conn)
    conn.commit()
def queue_change(conn, table_name, record_id, payload_dict):
    """Queue one local change for push (payload carries patient_file).

    R49 defensive filter: settings rows NEVER sync - above all the
    wa_* keys (reminder token / phone-number id are per-device
    credentials). No caller queues settings today; this guard keeps
    it that way even if one ever tries."""
    if table_name == "settings" or str(record_id or "").startswith("wa_"):
        return
    ensure_tables(conn); p = dict(payload_dict or {})
    if any(str(k).startswith("wa_") for k in p):
        return
    conn.cursor().execute("INSERT OR REPLACE INTO sync_queue(table_name,record_id,"
        "payload_json,updated_at,synced) VALUES(?,?,?,?,0)", (table_name,
        str(record_id), json.dumps(p, ensure_ascii=False), p.get("updated_at") or _now()))
    conn.commit()
def pending_changes(conn):
    ensure_tables(conn)
    return [dict(r) for r in conn.cursor().execute("SELECT * FROM sync_queue WHERE synced=0 ORDER BY id").fetchall()]
def mark_synced(conn, ids):
    ids = list(ids)
    if not ids: return 0
    c = conn.cursor(); c.executemany("UPDATE sync_queue SET synced=1 WHERE id=?", [(i,) for i in ids])
    conn.commit(); return c.rowcount
class SyncClient:
    """Thin urllib client for server/sync_server.py. 5s timeout,
    except pulls (300s): a first full sync is one huge response —
    the R39 load test measured the server needing ~a minute just
    to generate the 200k-patient payload, so the old 5s cap made
    an initial sync at that scale impossible, delta or not."""
    def __init__(self, server_url, token=None):
        self.server_url = (server_url or "").rstrip("/"); self.token = token
    def _req(self, method, path, body=None, timeout=5):
        if not self.server_url: return None, "network: no server URL"
        data = json.dumps(body).encode() if body is not None else None
        h = {"Content-Type": "application/json"}
        if self.token: h["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(self.server_url + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            try: return e.code, json.loads(e.read().decode("utf-8") or "{}")
            except Exception: return e.code, {"error": f"http {e.code}"}
        except Exception as e: return None, f"network: {e}"  # URLError/timeout/offline
    def login(self, username, password):
        """-> (True, {token, username, role, center_id}) or (False, error)."""
        st, res = self._req("POST", "/auth/login", {"username": username, "password": password})
        if st == 200 and isinstance(res, dict) and res.get("ok"):
            self.token = res["token"]
            return True, {"token": res["token"], "username": res.get("username"), "role": res.get("role"), "center_id": res.get("center_id")}
        return False, (res.get("error") if isinstance(res, dict) else str(res)) or f"http {st}"
    def change_password(self, old_password, new_password):
        """POST /auth/change-password (self only). -> (ok, error|None)."""
        if not self.token: return False, "not logged in"
        st, res = self._req("POST", "/auth/change-password", {"old_password": old_password, "new_password": new_password})
        if st == 200 and isinstance(res, dict) and res.get("ok"): return True, None
        return False, (res.get("error") if isinstance(res, dict) else str(res)) or f"http {st}"
    def rename_user(self, old_username, new_username):
        """POST /users/<old>/rename (admin only). -> (ok, error|None)."""
        if not self.token: return False, "not logged in"
        st, res = self._req("POST", f"/users/{old_username}/rename", {"new_username": new_username})
        if st == 200 and isinstance(res, dict) and res.get("ok"): return True, None
        return False, (res.get("error") if isinstance(res, dict) else str(res)) or f"http {st}"
    def create_user(self, username, password, role, center_id):
        """POST /users (admin only; 201 created, 409 name taken).
        -> (ok, error|None)."""
        if not self.token: return False, "not logged in"
        st, res = self._req("POST", "/users", {"username": username, "password": password,
                                               "role": role, "center_id": center_id})
        if st in (200, 201) and isinstance(res, dict) and res.get("ok"): return True, None
        return False, (res.get("error") if isinstance(res, dict) else str(res)) or f"http {st}"
    def list_users(self):
        """GET /users (admin only). -> (ok, users|error)."""
        if not self.token: return False, "not logged in"
        st, res = self._req("GET", "/users")
        if st == 200 and isinstance(res, dict): return True, res.get("users") or []
        return False, (res.get("error") if isinstance(res, dict) else str(res)) or f"http {st}"
    def delete_user(self, username):
        """DELETE /users/<name> (admin only; server refuses last admin).
        -> (ok, error|None)."""
        if not self.token: return False, "not logged in"
        st, res = self._req("DELETE", f"/users/{username}")
        if st == 200 and isinstance(res, dict) and res.get("ok"): return True, None
        return False, (res.get("error") if isinstance(res, dict) else str(res)) or f"http {st}"
    def push(self, conn, center_id):
        """Push pending queue + unsynced attendance. -> (ok, applied|error)."""
        if not self.token: return False, "not logged in"
        from src.models.referrals import queue_all_referrals as _qr, split_referral_queue as _sr
        try: _qr(conn)  # R23: backfill referrals created before they were queued
        except Exception: pass
        patients, visits, pend = [], [], pending_changes(conn)
        for row in pend:
            try: p = json.loads(row["payload_json"])
            except Exception: continue
            p.setdefault("center_id", center_id); p.setdefault("updated_at", row["updated_at"])
            if row["table_name"] == "patients":
                p.setdefault("patient_file", str(row["record_id"])); patients.append(p)
            elif row["table_name"] in VT:
                visits.append({"record_id": str(row["record_id"]),
                    "patient_file": str(p.get("patient_file") or ""), "kind": row["table_name"],
                    "center_id": center_id, "updated_at": row["updated_at"], "data_json": p})
        fin, emp = split_financial_queue(pend, center_id); refs = _sr(pend, center_id)
        applied = 0
        if patients or visits or fin or emp or refs:
            st, res = self._req("POST", "/sync/push", {"patients": patients, "visits": visits, "financials": fin, "employees": emp, "referrals": refs})
            if st != 200 or not (isinstance(res, dict) and res.get("ok")):
                return False, (res.get("error") if isinstance(res, dict) else str(res)) or f"http {st}"
            applied = res.get("applied", 0); mark_synced(conn, [r["id"] for r in pend])
        from src.models.attendance import unsynced_attendance, mark_synced as _ms
        sent = []
        for row in unsynced_attendance(conn):
            st, res = self._req("POST", "/attendance", {"action": row["action"], "device_id": row.get("device_id") or ""})
            if st == 200 and isinstance(res, dict) and res.get("ok"):
                sent.append(row["id"]); applied += 1
            else: break  # first failure stops; rest stays unsynced
        _ms(conn, sent); return True, applied
    def pull(self, conn, center_id, since=""):
        """GET /sync/pull, apply into real local tables. -> (ok, counts|error).

        R39: the default (since="") is a DELTA pull — the stored
        per-table seq watermarks (models/sync_state) go out with the
        request and an R39 server answers only rows changed since.
        A fresh client (no watermarks / unknown server_id) is served
        a full pull, exactly as before. An explicit non-empty since
        keeps the legacy timestamp-filtered pull. A pre-R39 server
        ignores the extra params, answers a full pull and returns no
        watermarks, so nothing is stored and pulls stay full."""
        if not self.token: return False, "not logged in"
        params = {"since": since or "", "center_id": center_id}
        delta = not since
        if delta:
            from src.models.sync_state import request_params
            params.update(request_params(conn, self.server_url, center_id))
        st, res = self._req("GET", "/sync/pull?" + urlencode(params),
                            timeout=300)
        if st != 200 or not isinstance(res, dict):
            return False, (res.get("error") if isinstance(res, dict) else str(res)) or f"http {st}"
        from src.models.referrals import apply_referral_pull as _apply_ref
        counts = {"patients": 0, "visits": 0, "financials": 0, "employees": 0, "referrals": 0}
        for item in res.get("patients") or []:
            try: counts["patients"] += _upsert(conn, "patients", "file_number", int(item["patient_file"]), item, item.get("updated_at"))
            except Exception: continue  # skip one bad record, never crash pull
        for item in res.get("visits") or []:
            try: counts["visits"] += _apply_visit(conn, item)
            except Exception: continue
        counts.update(apply_financial_pull(conn, res)); counts["referrals"] = _apply_ref(conn, res)
        conn.commit()
        if delta:
            from src.models.sync_state import absorb_response
            absorb_response(conn, self.server_url, center_id, res)
        return True, counts
def sync_now(conn, server_url, username, password, center_id, since=""):
    """Login + push + pull. -> dict summary; offline-safe, never raises."""
    if not (server_url or "").strip():
        return {"offline": True, "login": False, "push": None, "pull": None, "errors": ["no server URL"]}
    try:
        client = SyncClient(server_url); ok, info = client.login(username, password)
        if not ok:
            if isinstance(info, str) and info.startswith("network:"):
                return {"offline": True, "login": False, "push": None, "pull": None, "errors": [info]}
            return {"offline": False, "login": False, "push": None, "pull": None, "errors": [str(info)]}
        pok, applied = client.push(conn, center_id); qok, counts = client.pull(conn, center_id, since)
        errs = ([f"push: {applied}"] if not pok else []) + ([f"pull: {counts}"] if not qok else [])
        return {"offline": False, "login": True, "role": info.get("role"), "center_id": info.get("center_id"), "push": applied if pok else None, "pull": counts if qok else None, "errors": errs}
    except Exception as e:
        return {"offline": True, "login": False, "push": None, "pull": None, "errors": [str(e)]}
def sync_in_background(server_url, username, password, center_id):
    """Daemon thread: own DB connection, runs sync_now. Returns Thread."""
    def _run():
        try:
            from src.models.database import get_connection
            conn = get_connection()
            try: sync_now(conn, server_url, username, password, center_id)
            finally: conn.close()
        except Exception: pass
    t = threading.Thread(target=_run, daemon=True); t.start(); return t
