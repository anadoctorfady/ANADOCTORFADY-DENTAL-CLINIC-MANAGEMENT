"""ANADOCTORFADY telemetry server - stdlib only, no Flask.

Privacy: POST /ping accepts ONLY {install_id, app_version, platform,
country} (country optional — pre-round-38 clients send just the first
three). Round 38: the client derives its country on-device and sends
it; the server prefers a valid client country and falls back to
deriving one from the request IP via a free lookup (if reachable).
Either way the IP is DISCARDED - never stored, never logged.
install_id is stored only as a sha256 hash. SQLite telemetry.db:
(date, country, hash).
Run: python server/telemetry_server.py  (port 8000, see server/README.md)
"""
import hashlib
import html
import json
import os
import sqlite3
import urllib.request
import uuid
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

DB = Path(__file__).resolve().parent / "telemetry.db"
TOKEN = os.environ.get("TELEMETRY_TOKEN", "change-me")
ALLOWED_KEYS = {"install_id", "app_version", "platform", "country"}
REQUIRED_KEYS = {"install_id", "app_version", "platform"}


def _valid_country(code):
    """'unknown' or an uppercase ISO alpha-2 code."""
    return code == "unknown" or (isinstance(code, str) and len(code) == 2
                                  and code.isalpha() and code == code.upper())


def validate_payload(data):
    """True only for the allowed fields (the 3 originals required,
    `country` optional since round 38), valid UUID + windows."""
    if not isinstance(data, dict) or not REQUIRED_KEYS <= set(data) \
            or not set(data) <= ALLOWED_KEYS:
        return False
    try:
        uuid.UUID(str(data["install_id"]))
    except Exception:
        return False
    if "country" in data and not _valid_country(data["country"]):
        return False
    return bool(data["app_version"]) and data["platform"] == "windows"


def country_for_ip(ip):
    """Derive country code from IP, then forget the IP. 'unknown' if the
    free lookup is unreachable or the IP is private/loopback."""
    if not ip or ip.startswith(("127.", "10.", "192.168.", "::1")) or \
            ip.startswith("172.16."):
        return "unknown"
    try:
        with urllib.request.urlopen(
                f"http://ip-api.com/json/{ip}?fields=countryCode",
                timeout=2) as r:
            code = json.loads(r.read()).get("countryCode") or ""
            return code if len(code) == 2 else "unknown"
    except Exception:
        return "unknown"


def init_db():
    conn = sqlite3.connect(str(DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS pings(
        date TEXT, country_code TEXT, install_hash TEXT,
        PRIMARY KEY(date, install_hash))""")
    conn.commit()
    return conn


def record_ping(install_id, country):
    h = hashlib.sha256(install_id.encode()).hexdigest()
    conn = init_db()
    conn.execute("INSERT OR IGNORE INTO pings VALUES(?,?,?)",
                 (str(date.today()), country, h))
    conn.commit()
    conn.close()


def stats():
    conn = init_db()
    total = conn.execute("SELECT COUNT(DISTINCT install_hash) FROM pings"
                         ).fetchone()[0]
    rows = conn.execute("SELECT country_code, COUNT(DISTINCT install_hash)"
                        " FROM pings GROUP BY country_code ORDER BY 2 DESC")
    by_country = {c: n for c, n in rows}
    since = str(date.today() - timedelta(days=30))
    last30 = conn.execute("SELECT COUNT(DISTINCT install_hash) FROM pings"
                          " WHERE date>=?", (since,)).fetchone()[0]
    conn.close()
    return {"total_users": total, "users_by_country": by_country,
            "last_30_days": last30}


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path != "/ping":
            return self._json(404, {"error": "not found"})
        try:
            data = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", 0)) or 0))
        except Exception:
            return self._json(400, {"error": "bad json"})
        if not validate_payload(data):
            return self._json(400, {"error": "only install_id, "
                                             "app_version, platform, country allowed"})
        # Round 38: a valid client-sent country wins; otherwise the
        # IP is used ONLY to derive the country, then discarded.
        country = data.get("country")
        if not _valid_country(country) or country == "unknown":
            country = country_for_ip(self.client_address[0])
        record_ping(data["install_id"], country)
        self._json(200, {"ok": True})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/stats":
            token = parse_qs(parsed.query).get("token", [""])[0]
            if token != TOKEN:
                return self._json(403, {"error": "bad token"})
            return self._json(200, stats())
        if parsed.path == "/":
            s = stats()
            rows = "".join(f"<tr><td>{html.escape(c)}</td><td>{n}</td></tr>"
                           for c, n in s["users_by_country"].items())
            body = (f"<html><body><h1>ANADOCTORFADY users: {s['total_users']}"
                    f"</h1><p>Last 30 days: {s['last_30_days']}</p>"
                    f"<table><tr><th>Country</th><th>Users</th></tr>{rows}"
                    "</table></body></html>").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._json(404, {"error": "not found"})

    def log_message(self, *a):
        pass  # never log IPs


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "8000"))
    print(f"Telemetry server on http://localhost:{port}  (db: {DB})")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
