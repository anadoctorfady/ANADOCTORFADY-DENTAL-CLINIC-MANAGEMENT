"""Telemetry: silent automatic, always ON (no off switch), every
hour (round 40, owner decision 2026-11-21 — was every 4h),
only 4 fields, offline silent. ROUND-38 RE-PIN (owner-directed):
the payload was exactly 3 fields until the owner confirmed Firebase
receives installs but never the country — `country` is now the 4th
field, derived on-device (models.geo_country). Nothing else about
the payload may ever appear (no ip / name / patient data)."""
import importlib.util
import time
import uuid
from pathlib import Path
from src.models import telemetry as T
from src.models.database import get_connection, set_setting
ROOT = Path(__file__).resolve().parent.parent
def _clear(key):
    c = get_connection(); c.execute("DELETE FROM settings WHERE key=?", (key,)); c.commit(); c.close()
def _server():
    spec = importlib.util.spec_from_file_location("tserver", ROOT / "server" / "telemetry_server.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def test_install_id_stable_uuid():
    a, b = T.get_or_create_install_id(), T.get_or_create_install_id()
    assert a == b and str(uuid.UUID(a)) == a
def test_payload_exactly_four_keys():
    # Round 38: was test_payload_exactly_three_keys; country added.
    p = T.build_payload()
    assert set(p) == {"install_id", "app_version", "platform", "country"}
    assert p["platform"] == "windows" and "ip" not in p and "name" not in p and "patient" not in str(p)
    assert p["country"] == "unknown" or (len(p["country"]) == 2 and p["country"].isalpha())
def test_always_on_no_off_switch():
    # R40 re-pin: interval is 1h by owner decision 2026-11-21 (was 4).
    assert T.TELEMETRY_INTERVAL_HOURS == 1
    assert T.is_enabled() is True
    assert not hasattr(T, "set_enabled")
def test_interval_one_hour():
    # R40 re-pin (was test_interval_four_hours): the due threshold
    # is 1h by owner decision 2026-11-21 (was 4h).
    now = time.time()
    set_setting("telemetry_last_sent", str(now))
    assert T.is_due(now) is False
    set_setting("telemetry_last_sent", str(now - 1800))  # 30 min ago: not due
    assert T.is_due(now) is False
    set_setting("telemetry_last_sent", str(now - 3600 - 1))  # 1h+: due
    assert T.is_due(now) is True
    set_setting("telemetry_last_sent", "2000-01-01")  # legacy date: due
    assert T.is_due(now) is True
    _clear("telemetry_last_sent")
def test_no_url_no_send():
    _clear("telemetry_last_sent"); T.set_url("")
    assert T.maybe_send() is False; T.set_url("")
def test_unreachable_url_silent():
    set_setting("telemetry_last_sent", "0")  # due, so it attempts
    T.set_url("http://127.0.0.1:9/ping")
    assert T.maybe_send() is False  # no exception, no crash
    assert T._last_sent_ts() == 0.0  # failed send must not mark sent
    T.set_url(""); _clear("telemetry_last_sent")
def test_no_toggle_in_settings_ui():
    text = (ROOT / "src" / "ui" / "settings_ui.py").read_text(encoding="utf-8")
    assert "tel_var" not in text and "set_enabled" not in text
    assert "is_enabled" not in text and "Checkbutton" not in text
def test_server_rejects_extra_fields():
    s, good = _server(), {"install_id": str(uuid.uuid4()), "app_version": "2.1.0", "platform": "windows"}
    assert s.validate_payload(good) is True  # legacy 3-field client still ok
    # Round 38: a valid client country is now ACCEPTED (was rejected).
    assert s.validate_payload({**good, "country": "SY"}) is True
    assert s.validate_payload({**good, "country": "unknown"}) is True
    assert s.validate_payload({**good, "country": "Syria"}) is False
    assert s.validate_payload({**good, "name": "Fady"}) is False
    assert s.validate_payload({**good, "ip": "1.2.3.4"}) is False
