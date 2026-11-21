"""Anonymous usage stats: count + countries ONLY. No patient data here.

SILENT automatic mode — owner's explicit decision (2026-11-05): no
consent dialog, no ask-once flow, NO off switch. The app sends ONLY
{install_id, app_version, platform, country} when online, at most
once every 4 hours. Offline the app works fully; sending fails
silently. Round 38 (owner-directed): `country` added — before, the
payload was exactly 3 fields and the country NEVER reached
Firebase (only the optional /stats server derived one, from the
request IP). The country is now derived on this machine by
models.geo_country — no external calls, no new permissions.
"""
import json
import threading
import time
import urllib.request
from urllib.error import HTTPError
import uuid
from datetime import date, datetime

from src.models.database import get_setting, set_setting

APP_VERSION = "2.1.0"
ALLOWED_KEYS = {"install_id", "app_version", "platform", "country"}
TELEMETRY_INTERVAL_HOURS = 4
TELEMETRY_INTERVAL_SECONDS = TELEMETRY_INTERVAL_HOURS * 3600
INFO_TEXT = ("إحصاء مجهول تلقائي (عدد المستخدمين + البلد فقط) عند الاتصال "
    "بالإنترنت، كل 4 ساعات كحد أقصى. لا يُرسل أي شيء آخر، ولا بيانات "
    "مرضى أبداً. لا يوجد زر إيقاف — الإحصاء لا يؤثر على المستخدم أو "
    "خصوصيته، فهو عدد ودول فقط.")
CONSENT_TEXT = INFO_TEXT  # backwards-compat alias; no consent is asked


def get_or_create_install_id():
    """Random UUID, stored in settings. No name/email/phone anywhere."""
    iid = get_setting("telemetry_install_id")
    try:
        uuid.UUID(str(iid))
        return str(iid)
    except Exception:
        iid = str(uuid.uuid4())
        set_setting("telemetry_install_id", iid)
        return iid


def build_payload():
    """EXACTLY the 4 allowed fields - nothing else, ever. Round 38:
    `country` (ISO alpha-2 from models.geo_country, client-side)
    joins the original 3 — the owner's most-wanted field."""
    from src.models.geo_country import country_code
    payload = {"install_id": get_or_create_install_id(),
               "app_version": APP_VERSION, "platform": "windows",
               "country": country_code()}
    assert set(payload) == ALLOWED_KEYS, "telemetry payload keys changed!"
    return payload


def is_enabled():
    """Always ON (owner's decision). There is no off switch."""
    return True


def get_url():
    return (get_setting("telemetry_url", "") or "").strip()


def set_url(url):
    set_setting("telemetry_url", (url or "").strip())


def get_firebase_url():
    """Firebase Realtime Database root URL (the https URL shown in the
    Firebase console for the owner's project).

    EMPTY by default: a fresh build sends nothing to Firebase. The owner
    sets it on his own machine only (see TELEMETRY.md). It is NEVER
    hardcoded here — this project is MIT open source, and a hardcoded
    URL would route every open-source user's stats to the owner's DB.
    No API key / service account / auth token is used or stored."""
    return (get_setting("firebase_url", "") or "").strip()


def set_firebase_url(url):
    set_setting("firebase_url", (url or "").strip())


def _last_sent_ts(key="telemetry_last_sent"):
    """Stored value is an epoch timestamp; legacy 'YYYY-MM-DD' still
    parses (midnight that day), anything else means 'never sent'."""
    raw = (get_setting(key) or "").strip()
    try:
        return float(raw)
    except Exception:
        pass
    try:
        return datetime.combine(date.fromisoformat(raw),
                                datetime.min.time()).timestamp()
    except Exception:
        return 0.0


def is_due(now=None, key="telemetry_last_sent"):
    """True when 4+ hours passed since the last successful send."""
    now = time.time() if now is None else now
    return (now - _last_sent_ts(key)) >= TELEMETRY_INTERVAL_SECONDS


def is_due_firebase(now=None):
    """Firebase has its own last-sent clock, so a failed Firebase send
    retries next time instead of waiting out the server's success."""
    return is_due(now, key="telemetry_last_sent_firebase")


def _post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=3) as resp:
        return resp.status == 200


def _send_firebase():
    """PUT the same 4-field payload to <firebase_url>/installs/<id>.json
    (REST API, one node per install, refreshed every 4h). Returns a
    status string so callers/tests can tell a denied write apart from
    a network failure: "ok" | "denied" (HTTP 401/403, Locked-mode rules)
    | "failed" (offline / any network error / other HTTP status) |
    "skipped" (no URL set). Never raises; never blocks the app."""
    url = get_firebase_url()
    if not url:
        return "skipped"
    payload = build_payload()
    target = (url.rstrip("/") + "/installs/" +
              payload["install_id"] + ".json")
    req = urllib.request.Request(target, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            ok = resp.status == 200
    except HTTPError as e:
        return "denied" if e.code in (401, 403) else "failed"
    except Exception:
        return "failed"
    if ok:
        set_setting("telemetry_last_sent_firebase", str(time.time()))
        return "ok"
    return "failed"


def maybe_send_firebase():
    """Firebase leg of the 4-hour ping. False (silently) if no URL,
    not due yet, offline, denied, or any error. Never raises."""
    if not get_firebase_url() or not is_due_firebase():
        return False
    return _send_firebase() == "ok"


def maybe_send():
    """Send at most once per 4 hours, to each destination that is set.
    False (silently) if no URL, not due yet, offline, or any error.
    Never raises. Each destination has its own last-sent clock, so a
    failure of one never blocks the other (the failed one retries
    next time). True if at least one destination accepted the ping."""
    sent = False
    url = get_url()
    if url and is_due():
        try:
            ok = _post(url, build_payload())
        except Exception:
            ok = False
        if ok:
            set_setting("telemetry_last_sent", str(time.time()))
            sent = True
    if maybe_send_firebase():
        sent = True
    return sent


def maybe_send_async():
    """Fire-and-forget in a daemon thread: never blocks startup."""
    threading.Thread(target=maybe_send, daemon=True).start()
