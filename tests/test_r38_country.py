"""Round 38, item 4: telemetry `country` — client-side derivation.

The owner confirmed Firebase receives install_id / app_version /
platform but never the country (the payload was exactly 3 fields by
design; only the optional /stats server derived a country, from the
request IP). Round 38 adds `country` as the 4th field, derived on
this machine with NO network calls: Windows GeoID -> locale ->
timezone map -> "unknown". Every source is stubbed here so the
tests are environment-independent."""
import json
from unittest.mock import patch
from src.models import geo_country as G
from src.models import telemetry as T


def _with_sources(win=None, loc=None, tz=None):
    """Run country_code() with the three sources stubbed + cache off."""
    G._reset_cache()
    with patch.object(G, "_country_from_windows", lambda: win), \
         patch.object(G, "_country_from_locale", lambda: loc), \
         patch.object(G, "_country_from_timezone", lambda: tz):
        return G.country_code()


def test_windows_source_wins():
    assert _with_sources(win="SY", loc="US", tz="EG") == "SY"
    G._reset_cache()


def test_locale_source_second():
    assert _with_sources(win=None, loc="LB", tz="EG") == "LB"
    G._reset_cache()


def test_timezone_source_third():
    assert _with_sources(win=None, loc=None, tz="SA") == "SA"
    G._reset_cache()


def test_all_sources_empty_is_unknown():
    assert _with_sources() == "unknown"
    G._reset_cache()


def test_result_is_cached():
    G._reset_cache()
    with patch.object(G, "_country_from_windows", lambda: "SY") as _w:
        assert G.country_code() == "SY"
        with patch.object(G, "_country_from_windows",
                          lambda: (_ for _ in ()).throw(AssertionError)):
            assert G.country_code() == "SY"  # cache: no second lookup
    G._reset_cache()


def test_locale_country_parsing():
    assert G._locale_country("ar_SY") == "SY"
    assert G._locale_country("en-US") == "US"
    assert G._locale_country("fr") is None       # no country part
    assert G._locale_country("eo") is None       # Esperanto: not a country
    assert G._locale_country("") is None
    assert G._locale_country(None) is None
    # Re-pinned round 38: 'de_DE@euro' DOES carry a country (DE) —
    # '@euro' is a modifier, stripped before validation.
    assert G._locale_country("de_DE@euro") == "DE"
    assert G._locale_country("en_US.UTF-8") == "US"


def test_timezone_map_entries():
    assert G.TZ_COUNTRIES["Asia/Damascus"] == "SY"
    assert G.TZ_COUNTRIES["Asia/Riyadh"] == "SA"
    assert G.TZ_COUNTRIES["Europe/Istanbul"] == "TR"
    with patch.object(G, "_zone_name", lambda: "Asia/Damascus"):
        assert G._country_from_timezone() == "SY"
    with patch.object(G, "_zone_name", lambda: "Pacific/Kiritimati"):
        assert G._country_from_timezone() is None  # unmapped zone


def test_windows_source_off_windows_is_none():
    # This gate runs on Linux: the Windows source must quietly give up.
    assert G._country_from_windows() is None


def test_payload_carries_country():
    G._reset_cache()
    with patch.object(G, "_country_from_windows", lambda: "SY"), \
         patch.object(G, "_country_from_locale", lambda: None), \
         patch.object(G, "_country_from_timezone", lambda: None):
        p = T.build_payload()
    G._reset_cache()
    assert set(p) == {"install_id", "app_version", "platform", "country"}
    assert p["country"] == "SY"
    json.dumps(p)  # the payload stays JSON-serialisable


def test_firebase_body_includes_country():
    """The exact JSON PUT to Firebase carries the country field."""
    from tests.test_telemetry_firebase import _Resp, _reset, FAKE_FB
    _reset()
    T.set_firebase_url(FAKE_FB)
    calls = []
    def fake(req, timeout=None):
        calls.append(req)
        return _Resp(200)
    with patch("urllib.request.urlopen", fake):
        assert T.maybe_send_firebase() is True
    body = json.loads(calls[0].data.decode())
    assert body["country"] == T.build_payload()["country"]
    assert set(body) == {"install_id", "app_version", "platform", "country"}
    _reset()
