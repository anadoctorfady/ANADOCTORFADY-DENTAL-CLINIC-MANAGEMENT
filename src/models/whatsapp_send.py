"""Round 49 section B: WhatsApp Cloud API client + scheduler.

Official Meta WhatsApp Business Cloud API only (graph.facebook
.com template messages), stdlib urllib exactly like telemetry /
updater. Nothing here ever raises; tests mock urllib.request
.urlopen, so no real network call happens in the gate.

Template language mapping: the app stores 'en'/'ar' (the choice
the doctor made in Settings), but Meta template language codes
are locale codes - 'en' alone is not a valid code, while Arabic
templates are registered under plain 'ar'. Map: en -> en_US,
ar -> ar. The code sent is the language the template was
APPROVED under, which is why the guide says to create both.
"""
import json
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from src.models import whatsapp as wa
from src.models.database import get_connection, get_setting

GRAPH_BASE = "https://graph.facebook.com/v21.0"
TIMEOUT = 10
LANG_MAP = {"en": "en_US", "ar": "ar"}  # stored code -> Meta code
_started = False
_start_lock = threading.Lock()


def meta_lang(stored):
    return LANG_MAP.get((stored or "en").strip(), "en_US")


def build_payload(to, template_name, lang, params):
    return {
        "messaging_product": "whatsapp", "to": to, "type": "template",
        "template": {"name": template_name,
                     "language": {"code": meta_lang(lang)},
                     "components": [{"type": "body", "parameters": [
                         {"type": "text", "text": str(p)} for p in params]}]}}


def send_template(phone_number_id, token, to, template_name, lang, params):
    """POST one template message. -> (ok, detail); detail carries
    the HTTP status ('http 200') or the exception class name."""
    url = f"{GRAPH_BASE}/{phone_number_id}/messages"
    body = json.dumps(build_payload(to, template_name, lang, params)).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status = getattr(resp, "status", 200)
            return (200 <= status < 300), f"http {status}"
    except urllib.error.HTTPError as e:
        return False, f"http {e.code}"
    except Exception as e:  # offline / DNS / timeout: never raise
        return False, type(e).__name__


def _centre_name():
    try:
        from src.reports.pdf_common import clinic_name
        return clinic_name()
    except Exception:
        return (get_setting("clinic_name", "") or "").strip()


def _appt_dt(date_str, time_str):
    try:
        return datetime.fromisoformat(
            f"{str(date_str)[:10]}T{str(time_str)[:5]}")
    except (TypeError, ValueError):
        return None


def _upcoming(conn, now):
    """Appointments from today through +3 days, with the patient's
    name + mobile1 (same join shape the calendar uses)."""
    lo = now.date().isoformat()
    hi = (now + timedelta(days=3)).date().isoformat()
    return conn.execute(
        "SELECT a.id, a.appointment_date, a.appointment_time,"
        " p.full_name, p.mobile1 FROM appointments a"
        " LEFT JOIN patients p ON p.file_number = a.patient_file"
        " WHERE a.appointment_date >= ? AND a.appointment_date <= ?"
        " ORDER BY a.appointment_date, a.appointment_time",
        (lo, hi)).fetchall()


def run_check(now=None):
    """Send every due, not-yet-sent reminder. -> count sent OK.
    Unconfigured/disabled -> 0 and no HTTP is attempted."""
    now = now or datetime.now()
    cfg = wa.get_config()
    if not cfg["configured"]:
        return 0
    sent = 0
    conn = get_connection()
    try:
        wa.ensure_log_table(conn)
        centre = _centre_name()
        for appt_id, dstr, tstr, name, mobile in _upcoming(conn, now):
            appt_dt = _appt_dt(dstr, tstr)
            kinds = wa.due_windows(now, appt_dt)
            if not kinds:
                continue
            to = wa.normalize_phone(mobile)
            if not to:
                continue  # no mobile: skip, record nothing
            params = [name or "", centre, str(dstr)[:10], str(tstr)[:5]]
            for kind in kinds:
                if wa.already_sent(conn, appt_id, kind):
                    continue
                ok, detail = send_template(
                    cfg["phone_number_id"], cfg["token"], to,
                    cfg["template_name"], cfg["template_lang"], params)
                wa.record_log(conn, appt_id, kind,
                              "ok" if ok else "failed", detail)
                if ok:
                    sent += 1
    except Exception:
        pass  # a reminder failure must never disturb the app
    finally:
        conn.close()
    return sent


def send_test(destination):
    """One template message to `destination` (UI test button).
    -> (ok, detail); 'not configured' when settings are missing."""
    cfg = wa.get_config()
    if not (cfg["phone_number_id"] and cfg["token"] and cfg["template_name"]):
        return False, "not configured"
    to = wa.normalize_phone(destination)
    if not to:
        return False, "no destination"
    now = datetime.now()
    params = ["Test", _centre_name(), now.date().isoformat(),
              now.strftime("%H:%M")]
    return send_template(cfg["phone_number_id"], cfg["token"], to,
                         cfg["template_name"], cfg["template_lang"], params)


def start_checker():
    """Idempotent: one daemon thread - first check after ~60s,
    then every 30 minutes while the app runs. Wired by the
    coordinator in shell.py; safe to call more than once."""
    global _started
    with _start_lock:
        if _started:
            return None
        _started = True

    def _loop():
        time.sleep(60)
        while True:
            try:
                run_check()
            except Exception:
                pass
            time.sleep(30 * 60)

    th = threading.Thread(target=_loop, daemon=True, name="wa-checker")
    th.start()
    return th
