"""Round 49 section B: WhatsApp appointment reminders. Meta Cloud
API only; ALL network mocked via urllib.request.urlopen. Pins:
payload shape, h48/h24 windows, log dedupe, disabled -> no HTTP,
failed sends logged, phone normalisation, sync exclusion."""
import json
import re
import urllib.error
from datetime import datetime, timedelta
from unittest import mock

from src.models import whatsapp as wa
from src.models import whatsapp_send as ws
from src.models.database import get_connection, get_setting, set_setting
from tests.test_r16_print import isolated_db

NOW = datetime(2026, 12, 1, 10, 0, 0)
MOBILE = "+962 791 234 567"

class _Resp:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return b"{}"

def _capture(calls, fail=None):
    def fake(req, timeout=None):
        calls.append(req)
        if fail is not None:
            raise fail
        return _Resp()
    return fake

def _configure():
    wa.save_config(True, "+10000000000", "PNID123", "TOKSECRET", "appointment_reminder", "en")

def _seed_appt(fid, when, mobile=MOBILE):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO patients(file_number, first_name, full_name, mobile1) VALUES(?,?,?,?)", (fid, "Test", "Test Patient", mobile))
    cur = conn.execute("INSERT INTO appointments(patient_file, appointment_date, appointment_time, status) VALUES(?,?,?,?)", (fid, when.date().isoformat(), when.strftime("%H:%M"), "upcoming"))
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid

def test_normalize_phone():
    assert wa.normalize_phone("+962 791 234 567") == "962791234567"
    assert wa.normalize_phone("00962791234567") == "962791234567"
    assert wa.normalize_phone("") == ""
    assert wa.normalize_phone(None) == ""

def test_due_windows():
    assert wa.due_windows(NOW, NOW + timedelta(hours=47, minutes=59)) == ["h48"]
    assert wa.due_windows(NOW, NOW + timedelta(hours=23)) == ["h24"]
    assert wa.due_windows(NOW, NOW + timedelta(hours=49)) == []
    assert wa.due_windows(NOW, NOW - timedelta(hours=1)) == []
    assert wa.due_windows(NOW, NOW + timedelta(hours=48)) == ["h48"]
    assert wa.due_windows(NOW, NOW + timedelta(hours=24)) == ["h24"]

def test_payload_shape():
    calls = []
    with mock.patch("urllib.request.urlopen", _capture(calls)):
        ok, detail = ws.send_template("PNID123", "TOKSECRET", "962791234567", "appointment_reminder", "en", ["Test Patient", "Smile Clinic", "2026-12-03", "10:00"])
    assert ok and detail == "http 200" and len(calls) == 1
    req = calls[0]
    assert req.full_url == "https://graph.facebook.com/v21.0/PNID123/messages"
    assert req.headers.get("Authorization") == "Bearer TOKSECRET"
    body = json.loads(req.data.decode())
    assert body["messaging_product"] == "whatsapp"
    assert body["to"] == "962791234567" and body["type"] == "template"
    tpl = body["template"]
    assert tpl["name"] == "appointment_reminder"
    assert tpl["language"]["code"] == "en_US"  # stored 'en' -> Meta code
    params = tpl["components"][0]["parameters"]
    assert [p["text"] for p in params] == ["Test Patient", "Smile Clinic", "2026-12-03", "10:00"]
    assert ws.meta_lang("ar") == "ar" and ws.meta_lang("en") == "en_US"

def test_run_check_sends_once_and_dedupes():
    with isolated_db():
        _configure()
        set_setting("clinic_name", "Smile Clinic")
        aid = _seed_appt(8801, NOW + timedelta(hours=47, minutes=59))
        calls = []
        with mock.patch("urllib.request.urlopen", _capture(calls)):
            assert ws.run_check(now=NOW) == 1
            assert len(calls) == 1
            assert ws.run_check(now=NOW) == 0  # log dedupe across runs
            assert len(calls) == 1
        body = json.loads(calls[0].data.decode())
        assert body["to"] == "962791234567"
        params = body["template"]["components"][0]["parameters"]
        assert params[0]["text"] == "Test Patient"
        assert params[1]["text"] == "Smile Clinic"
        conn = get_connection()
        rows = wa.log_rows(conn, aid)
        conn.close()
        assert len(rows) == 1 and rows[0][4] == "ok" and rows[0][2] == "h48"

def test_run_check_h24_window():
    with isolated_db():
        _configure()
        aid = _seed_appt(8802, NOW + timedelta(hours=23))
        calls = []
        with mock.patch("urllib.request.urlopen", _capture(calls)):
            assert ws.run_check(now=NOW) == 1
        conn = get_connection()
        rows = wa.log_rows(conn, aid)
        conn.close()
        assert rows and rows[0][2] == "h24"

def test_run_check_unconfigured_and_disabled():
    with isolated_db():
        aid = _seed_appt(8803, NOW + timedelta(hours=23))
        calls = []
        with mock.patch("urllib.request.urlopen", _capture(calls)):
            assert ws.run_check(now=NOW) == 0  # nothing configured
            wa.save_config(False, "", "PNID123", "TOKSECRET", "appointment_reminder", "en")
            assert ws.run_check(now=NOW) == 0  # disabled
        assert calls == []
        conn = get_connection()
        assert wa.log_rows(conn, aid) == []
        conn.close()

def test_failed_send_is_logged():
    with isolated_db():
        _configure()
        aid = _seed_appt(8804, NOW + timedelta(hours=23))
        err = urllib.error.HTTPError("u", 500, "err", {}, None)
        with mock.patch("urllib.request.urlopen", _capture([], fail=err)):
            assert ws.run_check(now=NOW) == 0
        conn = get_connection()
        rows = wa.log_rows(conn, aid)
        conn.close()
        assert len(rows) == 1 and rows[0][4] == "failed"
        assert "500" in rows[0][5]

def test_no_mobile_skips_silently():
    with isolated_db():
        _configure()
        aid = _seed_appt(8805, NOW + timedelta(hours=23), mobile="")
        calls = []
        with mock.patch("urllib.request.urlopen", _capture(calls)):
            assert ws.run_check(now=NOW) == 0
        assert calls == []
        conn = get_connection()
        assert wa.log_rows(conn, aid) == []
        conn.close()

def test_wa_keys_never_sync():
    with isolated_db():
        _configure()
        from src.models.sync import pending_changes, queue_change
        from src.models.sync_apply import _upsert
        conn = get_connection()
        queue_change(conn, "patients", "8801", {"patient_file": "8801", "full_name": "Test Patient"})
        queue_change(conn, "settings", "wa_token", {"wa_token": "TOKSECRET"})
        queue_change(conn, "patients", "8802", {"wa_token": "TOKSECRET"})
        blob = json.dumps(pending_changes(conn), ensure_ascii=False)
        assert "wa_" not in blob and "TOKSECRET" not in blob
        # Apply side: a hostile pulled payload cannot write settings.
        assert _upsert(conn, "settings", "key", "wa_token", {"key": "wa_token", "value": "PWNED"}, "2999") == 0
        conn.close()
        assert get_setting("wa_token") == "TOKSECRET"

def test_strings_purity_and_guide():
    from src.config import strings_r49_wa as S
    from src.config.whatsapp_guide import STEPS, TEMPLATE_AR, TEMPLATE_EN
    arabic = re.compile(r"[\u0600-\u06FF]")
    assert all(not arabic.search(v) for v in S.EN.values())
    strip = lambda v: re.sub(r"\{[^}]*\}", "", v)  # {detail} placeholders are code, not text
    assert all(not re.search(r"[A-Za-z]", strip(v)) for v in S.AR.values())
    assert set(S.EN) == set(S.AR)
    assert all(k.startswith("wa.") for k in S.EN)
    assert len(STEPS) == 11
    assert TEMPLATE_EN == "Hello {{1}}, this is a reminder from {{2}} of your appointment on {{3}} at {{4}}."
    assert "{{1}}" in TEMPLATE_AR and "{{4}}" in TEMPLATE_AR
    from src.config.whatsapp_guide import guide_text
    en_text = guide_text("en")
    assert "developers.facebook.com" in en_text  # step BODIES render, not just titles
    assert TEMPLATE_EN in en_text and TEMPLATE_AR in en_text
    assert "24 hours" in en_text and "System Users" in en_text
    blob = json.dumps(STEPS, ensure_ascii=False)
    assert "whatsapp_business_messaging" in blob
    assert "Phone Number ID" in blob and "System Users" in blob
    assert "24 hours" in blob  # temporary-token warning

def test_checker_idempotent():
    # In a full-gate run the app shell may already have started
    # the checker via its startup hook before this test runs;
    # idempotence means: after any call the module reports
    # started, and a further call is always a no-op (None).
    ws.start_checker()
    assert ws._started is True
    assert ws.start_checker() is None  # never a second start
