"""Country of THIS install for the telemetry payload (Round 38).

The owner confirmed Firebase receives install_id / app_version /
platform but never the country -- the payload simply never carried
it (the optional /stats server derived country from the request IP
server-side; Firebase got no country at all). The country is now
derived CLIENT-SIDE, on this machine, with NO external network
calls and NO new permissions, in this order:

  1. Windows region (ctypes GetUserGeoID + GetGeoInfoW ISO-2) --
     Windows only, fully guarded; the shipped app targets Windows.
  2. The OS locale's country part (ar_SY -> SY, en_US -> US).
  3. A small timezone -> country map for common zones.
  4. "unknown".

The result is an ISO 3166 alpha-2 code, uppercase. Computed once
per process and cached; _reset_cache() exists for tests, which
stub the three sources deterministically. <200 lines."""
import locale
import os
import sys
from datetime import datetime
from pathlib import Path

_CACHE = None

# Common IANA zones -> ISO alpha-2. Deliberately small: the zones a
# clinic running this app is plausibly in, plus major world zones.
TZ_COUNTRIES = {
    "Asia/Damascus": "SY", "Asia/Riyadh": "SA", "Asia/Beirut": "LB",
    "Asia/Amman": "JO", "Asia/Dubai": "AE", "Asia/Baghdad": "IQ",
    "Asia/Kuwait": "KW", "Asia/Qatar": "QA", "Asia/Muscat": "OM",
    "Asia/Jerusalem": "IL", "Asia/Nicosia": "CY", "Asia/Tehran": "IR",
    "Europe/Istanbul": "TR", "Africa/Cairo": "EG", "Africa/Tunis": "TN",
    "Africa/Algiers": "DZ", "Africa/Casablanca": "MA",
    "Africa/Tripoli": "LY", "Africa/Khartoum": "SD",
    "Europe/London": "GB", "Europe/Berlin": "DE", "Europe/Paris": "FR",
    "Europe/Madrid": "ES", "Europe/Rome": "IT", "Europe/Athens": "GR",
    "Europe/Moscow": "RU", "America/New_York": "US",
    "America/Chicago": "US", "America/Denver": "US",
    "America/Los_Angeles": "US", "America/Toronto": "CA",
    "America/Sao_Paulo": "BR", "Asia/Karachi": "PK",
    "Asia/Kolkata": "IN", "Asia/Dhaka": "BD", "Asia/Jakarta": "ID",
    "Asia/Singapore": "SG", "Asia/Kuala_Lumpur": "MY",
    "Asia/Manila": "PH", "Asia/Bangkok": "TH", "Asia/Shanghai": "CN",
    "Asia/Hong_Kong": "HK", "Asia/Taipei": "TW", "Asia/Tokyo": "JP",
    "Asia/Seoul": "KR", "Australia/Sydney": "AU",
    "Pacific/Auckland": "NZ", "Africa/Lagos": "NG",
    "Africa/Johannesburg": "ZA", "Africa/Nairobi": "KE",
}

# Locale tails that are language codes, not countries (Esperanto's
# "eo" locale has no country part yet parses as alpha-2; _YU is the
# defunct Yugoslavia code). Real alpha-2 countries are never listed.
_NOT_COUNTRIES = {"EO", "YU"}


def _valid(code):
    """An uppercase ISO alpha-2 code, or None."""
    if not code:
        return None
    code = str(code).strip().upper()
    if len(code) == 2 and code.isalpha() and code not in _NOT_COUNTRIES:
        return code
    return None


def _country_from_windows():
    """Windows region via GetUserGeoID/GetGeoInfoW (ISO-2). None
    off Windows or on any error -- never raises."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        GEOCLASS_NATION = 16
        GEO_ISO2 = 4
        k32 = ctypes.windll.kernel32
        geo_id = k32.GetUserGeoID(GEOCLASS_NATION)
        if not geo_id or geo_id == -1:
            return None
        buf = ctypes.create_unicode_buffer(16)
        n = k32.GetGeoInfoW(geo_id, GEO_ISO2, buf, len(buf), 0)
        return _valid(buf.value) if n else None
    except Exception:
        return None


def _country_from_locale():
    """Country part of the OS locale (ar_SY / en_US / ...)."""
    for getter in (locale.getlocale, locale.getdefaultlocale):
        try:
            loc = getter()[0]
        except Exception:
            loc = None
        code = _locale_country(loc)
        if code:
            return code
    return None


def _locale_country(loc):
    if not loc:
        return None
    s = str(loc)
    if "_" not in s and "-" not in s:
        return None  # bare language name ('fr'): no country part
    base = s.split(".")[0].split("@")[0]  # drop encoding / modifier
    tail = base.replace("-", "_").split("_")[-1]
    return _valid(tail)


def _zone_name():
    """The local IANA zone name when discoverable, else None."""
    tz = (os.environ.get("TZ") or "").strip().lstrip(":")
    if tz:
        return tz
    try:  # zoneinfo-backed tzinfo carries its key
        key = getattr(datetime.now().astimezone().tzinfo, "key", None)
        if key:
            return str(key)
    except Exception:
        pass
    try:  # Linux: /etc/localtime is a symlink into zoneinfo
        p = Path("/etc/localtime").resolve()
        s = str(p)
        if "zoneinfo/" in s:
            return s.split("zoneinfo/", 1)[1]
    except Exception:
        pass
    return None


def _country_from_timezone():
    return TZ_COUNTRIES.get(_zone_name() or "")


def country_code():
    """ISO alpha-2 of this machine's country, or "unknown".
    Cached after the first call (tests: _reset_cache())."""
    global _CACHE
    if _CACHE is None:
        _CACHE = (_country_from_windows() or _country_from_locale()
                  or _country_from_timezone() or "unknown")
    return _CACHE


def _reset_cache():
    global _CACHE
    _CACHE = None
