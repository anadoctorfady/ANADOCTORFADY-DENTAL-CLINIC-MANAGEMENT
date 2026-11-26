"""Round 49 section B: WhatsApp reminder settings + send log.

Settings live in the normal settings table under wa_* keys via
database.get_setting/set_setting. They are PER-DEVICE and must
never sync (credentials stay local): sync.py queue_change refuses
settings rows and sync_apply._upsert refuses the settings table,
and no code path queues settings today - tests pin all of that.

The wa_send_log table is created lazily HERE (database.py is not
touched): one row per (appointment, kind) send attempt, kind is
'h48' or 'h24'. Dedupe rule: a kind counts as sent only when a
row with status 'ok' exists, so a failed attempt may retry on a
later check while a successful one never repeats.
"""
import re
from datetime import datetime, timedelta

from src.models.database import get_connection, get_setting, set_setting

KEYS = ("wa_enabled", "wa_number", "wa_phone_number_id", "wa_token",
        "wa_template_name", "wa_template_lang")
DEFAULT_TEMPLATE = "appointment_reminder"


def ensure_log_table(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS wa_send_log(
        id INTEGER PRIMARY KEY, appointment_id INT, kind TEXT,
        sent_at TEXT, status TEXT, detail TEXT)""")
    conn.commit()


def get_config():
    """All wa_* settings + a `configured` flag: enabled AND phone
    number id AND token AND template name all non-empty."""
    lang = (get_setting("wa_template_lang", "") or "").strip()
    if lang not in ("en", "ar"):
        lang = "ar" if (get_setting("language", "en") or "en") == "ar" else "en"
    cfg = {
        "enabled": (get_setting("wa_enabled", "0") or "0") == "1",
        "number": (get_setting("wa_number", "") or "").strip(),
        "phone_number_id": (get_setting("wa_phone_number_id", "") or "").strip(),
        "token": (get_setting("wa_token", "") or "").strip(),
        "template_name": (get_setting("wa_template_name", "") or "").strip()
                         or DEFAULT_TEMPLATE,
        "template_lang": lang,
    }
    cfg["configured"] = bool(cfg["enabled"] and cfg["phone_number_id"]
                             and cfg["token"] and cfg["template_name"])
    return cfg


def save_config(enabled, number, phone_number_id, token,
                template_name, template_lang):
    set_setting("wa_enabled", "1" if enabled else "0")
    set_setting("wa_number", (number or "").strip())
    set_setting("wa_phone_number_id", (phone_number_id or "").strip())
    set_setting("wa_token", (token or "").strip())
    set_setting("wa_template_name", (template_name or "").strip()
                or DEFAULT_TEMPLATE)
    set_setting("wa_template_lang",
                template_lang if template_lang in ("en", "ar") else "en")


def normalize_phone(mobile):
    """Digits only; a leading international '00' prefix is dropped
    ('+962 791 234 567' -> '962791234567'). '' for empty input."""
    digits = re.sub(r"\D", "", str(mobile or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    return digits


def due_windows(now, appt_datetime):
    """Which reminder kinds are due for an appointment: 'h48'
    when 24h < delta <= 48h, 'h24' when 0 < delta <= 24h.
    The windows are disjoint, so at most one kind is returned."""
    if now is None or appt_datetime is None:
        return []
    delta = appt_datetime - now
    if timedelta(hours=24) < delta <= timedelta(hours=48):
        return ["h48"]
    if timedelta(0) < delta <= timedelta(hours=24):
        return ["h24"]
    return []


def already_sent(conn, appt_id, kind):
    """True when a SUCCESSFUL send of this kind is in the log."""
    ensure_log_table(conn)
    row = conn.execute(
        "SELECT 1 FROM wa_send_log WHERE appointment_id=? AND kind=?"
        " AND status='ok' LIMIT 1", (appt_id, kind)).fetchone()
    return row is not None


def record_log(conn, appt_id, kind, status, detail):
    ensure_log_table(conn)
    conn.execute(
        "INSERT INTO wa_send_log(appointment_id, kind, sent_at, status,"
        " detail) VALUES(?,?,?,?,?)",
        (appt_id, kind, datetime.now().isoformat(timespec="seconds"),
         status, str(detail or "")[:500]))
    conn.commit()


def log_rows(conn, appt_id=None):
    ensure_log_table(conn)
    if appt_id is None:
        return conn.execute("SELECT * FROM wa_send_log ORDER BY id").fetchall()
    return conn.execute("SELECT * FROM wa_send_log WHERE appointment_id=?"
                        " ORDER BY id", (appt_id,)).fetchall()
