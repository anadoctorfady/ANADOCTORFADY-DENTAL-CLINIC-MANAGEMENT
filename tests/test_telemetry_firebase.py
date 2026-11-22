"""Firebase telemetry: same 4 fields (country added round 38,
owner-directed — it never reached Firebase before), PUT to
/installs/<id>.json every hour (round 40; was every 4h),
silent on offline/denied, server POST untouched, no hardcoded URL.
All network calls are mocked — the real Firebase is never touched.
The rules snippet in TELEMETRY.md is parsed + checked here, so the
doc the owner pastes and the code stay in agreement."""
import json, re, time, urllib.error
from pathlib import Path
from unittest.mock import patch
from src.models import telemetry as T
from src.models.database import get_connection, set_setting
ROOT = Path(__file__).resolve().parent.parent
# Dummy Firebase root (NOT the owner's real project): tests only prove
# the shape of the request, never a real write.
FAKE_FB = "https://example.firebaseio.com"
# Fragments of the owner's real Firebase URL: must not appear in src/.
FORBIDDEN = ("firebaseio.com", "anadoctorfady-default-rtdb")
class _Resp:
    def __init__(self, status=200): self.status = status
    def __enter__(self): return self
    def __exit__(self, *a): return False
def _clear(key):
    c = get_connection(); c.execute("DELETE FROM settings WHERE key=?", (key,))
    c.commit(); c.close()
def _reset():
    for k in ("telemetry_url", "firebase_url", "telemetry_last_sent",
              "telemetry_last_sent_firebase"): _clear(k)
    set_setting("telemetry_last_sent", "0")
    set_setting("telemetry_last_sent_firebase", "0")
def _capture(calls):
    def fake(req, timeout=None): calls.append(req); return _Resp(200)
    return fake
def _rules_from_docs():
    """The exact rules JSON the owner pastes (TELEMETRY.md block)."""
    text = (ROOT / "TELEMETRY.md").read_text(encoding="utf-8")
    m = re.search(r"<!-- BEGIN FIREBASE RULES.*?```json\n(.*?)```"
                  r".*?<!-- END FIREBASE RULES -->", text, re.S)
    assert m, "Firebase rules block missing from TELEMETRY.md"
    return json.loads(m.group(1))  # raises if the snippet is not valid JSON
def test_firebase_url_empty_by_default():
    _reset(); T.set_firebase_url("")
    assert T.get_firebase_url() == ""
    T.set_firebase_url("  " + FAKE_FB + "  ")
    assert T.get_firebase_url() == FAKE_FB
    T.set_firebase_url(""); assert T.get_firebase_url() == ""
def test_firebase_payload_exactly_four_keys():
    # Round 38: was ..._three_keys; country is the 4th field now.
    p = T.build_payload()
    assert set(p) == {"install_id", "app_version", "platform", "country"}
    assert p["platform"] == "windows" and "country" in p
def test_firebase_put_shape():
    _reset(); T.set_firebase_url(FAKE_FB + "/")  # trailing slash: no double-up
    calls = []
    with patch("urllib.request.urlopen", _capture(calls)):
        assert T.maybe_send_firebase() is True
    assert len(calls) == 1; req = calls[0]
    iid = T.get_or_create_install_id()
    assert req.get_method() == "PUT"
    assert req.full_url == FAKE_FB + "/installs/" + iid + ".json"
    assert "//installs/" not in req.full_url
    body = json.loads(req.data.decode())
    assert set(body) == {"install_id", "app_version", "platform", "country"}
    assert body["install_id"] == iid and body["app_version"] == T.APP_VERSION
    assert body["country"] == T.build_payload()["country"]
    assert float(T._last_sent_ts("telemetry_last_sent_firebase")) > 0
    _reset()
def test_no_firebase_url_no_send():
    _reset(); T.set_firebase_url("")
    def boom(req, timeout=None):
        raise AssertionError("urlopen must not be called with no URL")
    with patch("urllib.request.urlopen", boom):
        assert T.maybe_send_firebase() is False
        assert T.maybe_send() is False
    _reset()
def test_firebase_not_due_no_send():
    _reset(); T.set_firebase_url(FAKE_FB)
    set_setting("telemetry_last_sent_firebase", str(time.time()))
    assert T.is_due_firebase() is False
    with patch("urllib.request.urlopen",
               side_effect=AssertionError("must not send when not due")):
        assert T.maybe_send_firebase() is False
    _reset()
def test_firebase_urlerror_silent_false():
    _reset(); T.set_firebase_url(FAKE_FB)
    err = urllib.error.URLError("offline")
    with patch("urllib.request.urlopen", side_effect=err):
        assert T.maybe_send_firebase() is False
        assert T._send_firebase() == "failed"
        assert T.maybe_send() is False  # never raises
    assert T._last_sent_ts("telemetry_last_sent_firebase") == 0.0
    _reset()
def test_firebase_denied_distinguishable():
    _reset(); T.set_firebase_url(FAKE_FB)
    for code in (401, 403):
        err = urllib.error.HTTPError(FAKE_FB, code, "Denied", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            assert T._send_firebase() == "denied"  # distinct from "failed"
            assert T.maybe_send_firebase() is False
            assert T.maybe_send() is False  # still silent False, no raise
        assert T._last_sent_ts("telemetry_last_sent_firebase") == 0.0
    _reset()
def test_firebase_denied_silent_stays_due():
    """Denied (401/403): never raises, shows no UI, never updates the
    Firebase last-sent timestamp — stays due, retries once at the next
    app launch (there is no in-app retry loop)."""
    _reset(); T.set_firebase_url(FAKE_FB)
    src = (ROOT / "src" / "models" / "telemetry.py").read_text(encoding="utf-8")
    assert "tkinter" not in src and "messagebox" not in src  # no UI ever
    for code in (401, 403):
        err = urllib.error.HTTPError(FAKE_FB, code, "Denied", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            assert T._send_firebase() == "denied"
            assert T.maybe_send_firebase() is False
            assert T.maybe_send() is False  # silent False, no raise
        assert T._last_sent_ts("telemetry_last_sent_firebase") == 0.0
        assert T.is_due_firebase() is True  # stays due: next launch only
    _reset()
def test_firebase_rules_snippet_in_docs():
    """The rules the owner pastes must match the implemented PUT:
    write allowed under installs/$install_id, denied everywhere else."""
    rules = _rules_from_docs()["rules"]  # valid JSON, or the parse fails
    assert rules[".read"] is False and rules[".write"] is False
    assert set(rules) == {"installs", ".read", ".write"}
    node = rules["installs"]["$install_id"]
    assert node[".write"] is True and node[".read"] is False
    def walk(d):  # every .read/.write in the tree; only one may be True
        for k, v in d.items():
            if k in (".read", ".write"): yield v
            elif isinstance(v, dict): yield from walk(v)
    assert [v for v in walk(rules) if v is True] == [True]
def test_server_post_unchanged_when_firebase_empty():
    _reset(); T.set_url("https://stats.example.com/ping"); T.set_firebase_url("")
    calls = []
    with patch("urllib.request.urlopen", _capture(calls)):
        assert T.maybe_send() is True
    assert len(calls) == 1
    assert calls[0].get_method() == "POST"
    assert calls[0].full_url == "https://stats.example.com/ping"
    assert json.loads(calls[0].data.decode())["install_id"] == T.get_or_create_install_id()
    assert T._last_sent_ts() > 0  # server clock marked
    assert T._last_sent_ts("telemetry_last_sent_firebase") == 0.0
    _reset()
def test_server_failure_does_not_block_firebase():
    _reset(); T.set_url("https://stats.example.com/ping"); T.set_firebase_url(FAKE_FB)
    def fake(req, timeout=None):
        if req.get_method() == "POST": raise urllib.error.URLError("server down")
        return _Resp(200)
    with patch("urllib.request.urlopen", fake):
        assert T.maybe_send() is True  # firebase saved it
    assert T._last_sent_ts() == 0.0  # server still due: retries next time
    assert T._last_sent_ts("telemetry_last_sent_firebase") > 0
    _reset()
def test_firebase_failure_does_not_block_server():
    _reset(); T.set_url("https://stats.example.com/ping"); T.set_firebase_url(FAKE_FB)
    def fake(req, timeout=None):
        if req.get_method() == "PUT": raise urllib.error.URLError("firebase down")
        return _Resp(200)
    with patch("urllib.request.urlopen", fake):
        assert T.maybe_send() is True  # server saved it
    assert T._last_sent_ts() > 0
    assert T._last_sent_ts("telemetry_last_sent_firebase") == 0.0
    _reset()
def test_payload_build_failure_never_raises():
    """R40 hardening: build_payload() used to be called OUTSIDE the
    try in _send_firebase, so a build error escaped into the daemon
    thread and silently killed the Firebase leg on every launch.
    Stubbed to raise: the leg must read "failed" / False instead."""
    _reset(); T.set_firebase_url(FAKE_FB)
    def boom():
        raise RuntimeError("payload build exploded")
    with patch.object(T, "build_payload", boom):
        assert T._send_firebase() == "failed"
        assert T.maybe_send_firebase() is False
        assert T.maybe_send() is False  # still silent, no raise
    assert T._last_sent_ts("telemetry_last_sent_firebase") == 0.0
    _reset()
def test_no_hardcoded_firebase_url_in_source():
    for p in (ROOT / "src").rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        for frag in FORBIDDEN: assert frag not in text, f"{frag} hardcoded in {p}"
def test_no_secrets_in_telemetry_source():
    text = (ROOT / "src" / "models" / "telemetry.py").read_text(encoding="utf-8")
    for frag in ("api_key", "apikey", "service_account", "serviceAccount",
                 "auth_token", "private_key"):
        assert frag not in text.lower(), frag
