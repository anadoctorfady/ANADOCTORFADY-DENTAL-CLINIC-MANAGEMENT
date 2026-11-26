"""Round 52, Section D: regional Arabic Gregorian month names.

Arabic month names differ by region -- the Levant uses the
Syriac-derived names (كانون الثاني، شباط، ...), Egypt & the Gulf
use the transliterated Latin names (يناير، فبراير، ...), and the
Maghreb has its own forms (جانفي، فيفري، ...). The owner picks the
set once in Settings (key `ar_month_names`, DEFAULT "levant");
every Arabic Gregorian month display routes through months_ar().

English month names and the Hijri month names (utils/hijri_age.py)
are NOT here and are untouched by the choice.
"""

MONTHS_EN = ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November",
             "December"]

MONTH_SETS = {
    "levant": ["كانون الثاني", "شباط", "آذار", "نيسان", "أيار",
               "حزيران", "تموز", "آب", "أيلول", "تشرين الأول",
               "تشرين الثاني", "كانون الأول"],
    "egypt_gulf": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                   "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر",
                   "ديسمبر"],
    "maghreb": ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
                "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر",
                "ديسمبر"],
}
DEFAULT_SET = "levant"
SET_KEYS = ("levant", "egypt_gulf", "maghreb")


def valid_set(key):
    """The stored key if it names a set, else the default."""
    return key if key in MONTH_SETS else DEFAULT_SET


def months_ar(key=None):
    """The 12 Arabic month names for a set key (default: Levant)."""
    return MONTH_SETS[valid_set(key)]


def month_name_ar(month, key=None):
    """Arabic name of month 1..12 under a set key."""
    return months_ar(key)[int(month) - 1]


def current_months_ar():
    """The 12 Arabic month names for the SAVED Settings choice."""
    try:
        from src.models.database import get_setting
        key = get_setting("ar_month_names", DEFAULT_SET)
    except Exception:
        key = DEFAULT_SET
    return months_ar(key)


def current_month_name_ar(month):
    """Arabic name of month 1..12 under the saved Settings choice."""
    return current_months_ar()[int(month) - 1]
