"""Hijri + Gregorian age. <150 lines. Verified 1990-05-15 = 20 Shawwal 1410."""
from datetime import date, datetime
import calendar, re
try:
    from hijri_converter import convert
    HAS = True
except ImportError:
    HAS, convert = False, None
# Birth dates are entered / shown as DD/MM/YYYY in both languages
# (e.g. 15/02/2026); the DB keeps ISO YYYY-MM-DD (see database.py).
BIRTH_FORMAT = "DD/MM/YYYY"
# Legacy bilingual constant, kept for import compatibility only
# (patient_form imports it). New code must use invalid_birth_msg():
# round 17 language purity — user-visible text is ONE language.
INVALID_BIRTH_MSG = ("Invalid birth date — use DD/MM/YYYY "
    "/ تاريخ ميلاد غير صحيح — استخدم DD/MM/YYYY")
_INVALID_EN = "Invalid birth date — use DD/MM/YYYY"
_INVALID_AR = "تاريخ ميلاد غير صحيح — استخدم DD/MM/YYYY"
def _app_lang(lang):
    if lang in ("en", "ar"):
        return lang
    try:
        from src.models.database import get_setting
        return "ar" if (get_setting("language", "en") or "en") == "ar" else "en"
    except Exception:
        return "en"
def invalid_birth_msg(lang=None):
    """Single-language invalid-birth message (lang=None -> app language)."""
    return _INVALID_AR if _app_lang(lang) == "ar" else _INVALID_EN
def parse_birth_date(s, lang=None):
    """Lenient front-door (round 19), strict RESULT: accepts
    d/m/yyyy, dd/m/yyyy, d/mm/yyyy, dd/mm/yyyy (1-2 digit day and
    month, slashes, optional surrounding spaces) and 8 consecutive
    digits ddmmyyyy; the normalised date must be a REAL calendar
    date (31/2/2000 and 29/2/2001 are rejected). ISO YYYY-MM-DD is
    also accepted (legacy DB values / old callers). The ValueError
    text is single-language (see invalid_birth_msg)."""
    msg = invalid_birth_msg(lang)
    if s is None:
        raise ValueError(msg)
    s = str(s).strip()
    m = re.fullmatch(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            raise ValueError(msg) from None
    if re.fullmatch(r"\d{8}", s):
        try:
            return date(int(s[4:8]), int(s[2:4]), int(s[0:2]))
        except ValueError:
            raise ValueError(msg) from None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(msg) from None
    raise ValueError(msg)
def parse_birth_date_lenient(s, lang=None):
    """Explicit lenient entry point (round 19): same rules as
    parse_birth_date(); named for callers that handle typed input."""
    return parse_birth_date(s, lang=lang)
def normalize_birth_input(s, lang=None):
    """Typed birth text -> strict DD/MM/YYYY (round 19 focus-out
    reformatting); raises ValueError (invalid_birth_msg) if invalid."""
    return parse_birth_date_lenient(s, lang=lang).strftime("%d/%m/%Y")
def format_birth_date(value):
    """date, or ISO YYYY-MM-DD string, -> DD/MM/YYYY; '' stays ''."""
    if not value:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return parse_birth_date(str(value)).strftime("%d/%m/%Y")
HIJRI_MONTHS = ["محرم","صفر","ربيع الأول","ربيع الآخر","جمادى الأولى",
    "جمادى الآخرة","رجب","شعبان","رمضان","شوال","ذو القعدة","ذو الحجة"]
HIJRI_MONTHS_EN = ["Muharram", "Safar", "Rabi' al-awwal", "Rabi' al-thani",
    "Jumada al-awwal", "Jumada al-thani", "Rajab", "Sha'ban", "Ramadan",
    "Shawwal", "Dhu al-Qa'dah", "Dhu al-Hijjah"]
def greg_to_hijri(d):
    if HAS:
        h = convert.Gregorian(d.year, d.month, d.day).to_hijri()
        return (h.year, h.month, h.day)
    jd = _greg_jd(d.year, d.month, d.day)
    return _jd_hijri(jd)
def _greg_jd(y, m, d):
    a = (14-m)//12; y2 = y+4800-a; m2 = m+12*a-3
    return d + (153*m2+2)//5 + 365*y2 + y2//4 - y2//100 + y2//400 - 32045
def _hijri_jd(y, m, d):
    return d + (m-1)*29 + m//2 + (y-1)*354 + (3+11*y)//30 + 1948439-1
def _jd_hijri(jd):
    jd0 = jd - 1948439 + 1; y = (30*jd0+10646)//10631
    while _hijri_jd(y, 1, 1) > jd:
        y -= 1
    while _hijri_jd(y+1, 1, 1) <= jd:
        y += 1
    m = 1
    while m < 12 and _hijri_jd(y, m+1, 1) <= jd:
        m += 1
    return (y, m, jd-_hijri_jd(y, m, 1)+1)
def format_hijri(h, lang=None):
    """(y, m, d) Hijri tuple -> display string in ONE language
    (lang=None -> app language). AR is byte-identical to the
    historical format; EN uses Latin month names + ' AH'."""
    y, m, d = h
    if _app_lang(lang) == "ar":
        return f"{d:02d} {HIJRI_MONTHS[m-1]} {y}هـ"
    return f"{d} {HIJRI_MONTHS_EN[m-1]} {y} AH"
def format_hijri_date(greg_value, lang=None):
    """Gregorian value -> formatted Hijri string in `lang`
    (lang=None -> app language). Accepts a datetime.date, an ISO
    'YYYY-MM-DD' string or a 'DD/MM/YYYY' string; returns '' for
    empty / unparseable input and never raises. Display sites use
    this to RE-DERIVE the Hijri date from birth_date_greg instead
    of trusting the stored (possibly other-language) string."""
    if not greg_value:
        return ""
    try:
        if isinstance(greg_value, datetime):
            d = greg_value.date()
        elif isinstance(greg_value, date):
            d = greg_value
        else:
            d = parse_birth_date(str(greg_value).strip())
        return format_hijri(greg_to_hijri(d), lang=lang)
    except Exception:
        return ""
def age_greg(birth, ref=None):
    ref = ref or date.today()
    y, m, d = ref.year-birth.year, ref.month-birth.month, ref.day-birth.day
    if d < 0:
        pm = ref.month-1 or 12; py = ref.year if ref.month > 1 else ref.year-1
        d += calendar.monthrange(py, pm)[1]; m -= 1
    if m < 0:
        m += 12; y -= 1
    return {"years": y, "months": m, "days": d,
            "total_days": (ref-birth).days}
def age_hijri(birth_greg, ref=None):
    ref = ref or date.today()
    hb, hr = greg_to_hijri(birth_greg), greg_to_hijri(ref)
    y, m, d = hr[0]-hb[0], hr[1]-hb[1], hr[2]-hb[2]
    if d < 0:
        m -= 1; d += 30 if (hr[1]-1 or 12) % 2 == 1 else 29
    if m < 0:
        m += 12; y -= 1
    return {"years": y, "months": m, "days": d,
            "hijri_birth": hb, "hijri_today": hr}
def get_all_ages(birth_str, lang=None):
    bd = parse_birth_date(birth_str)
    h = greg_to_hijri(bd)
    return {"greg_age": age_greg(bd), "hijri_age": age_hijri(bd),
            "hijri_date": h, "hijri_formatted": format_hijri(h, lang=lang)}
