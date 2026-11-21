"""Currency: default (base) currency configurable for any country.
178 ISO codes from src/data/currencies.json; searchable by code/name.
Rate = units of BASE currency per 1 unit of payment currency, on entry
date. Manual entry only (offline, no internet fetch). If payment
currency == base currency, no rate is needed. <110 lines."""
from datetime import date
from src.models.database import get_connection, init_db
from src.utils.currencies import list_currencies

_C = list_currencies()
CURRENCIES = [c["code"] for c in _C]
LABELS = {c["code"]: c["name_ar"] for c in _C}
EN_LABELS = {c["code"]: c["name_en"] for c in _C}
SYMBOLS = {c["code"]: (c.get("symbol") or c["code"]) for c in _C}

def default_currency():
    try:
        from src.config.settings import get_default_currency
        return get_default_currency()
    except Exception:
        return "SYP"

def get_rate(date_str, from_currency="USD", to_currency=None):
    """Rate for exact date (from->to), else None."""
    to_currency = to_currency or default_currency()
    if not date_str or from_currency == to_currency:
        return 1.0 if from_currency == to_currency else None
    init_db()
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT rate FROM exchange_rates WHERE date=? AND from_currency=? AND to_currency=?",
                    (date_str, from_currency, to_currency))
        r = cur.fetchone()
    except Exception:
        cur.execute("SELECT rate FROM exchange_rates WHERE date=?", (date_str,))
        r = cur.fetchone()
    conn.close()
    return float(r["rate"]) if r else None

def latest_rate(from_currency="USD", to_currency=None):
    to_currency = to_currency or default_currency()
    if from_currency == to_currency:
        return 1.0
    init_db()
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("SELECT rate FROM exchange_rates WHERE from_currency=? AND to_currency=? ORDER BY date DESC LIMIT 1",
                    (from_currency, to_currency))
        r = cur.fetchone()
    except Exception:
        cur.execute("SELECT rate FROM exchange_rates ORDER BY date DESC LIMIT 1")
        r = cur.fetchone()
    conn.close()
    return float(r["rate"]) if r else None

def save_rate(date_str, rate, from_currency="USD", to_currency=None, lang=None):
    to_currency = to_currency or default_currency()
    if not date_str:
        date_str = date.today().isoformat()
    rate = float(rate)
    if rate <= 0:
        if lang not in ("en", "ar"):
            try:
                from src.models.database import get_setting
                lang = "ar" if (get_setting("language", "en") or "en") == "ar" else "en"
            except Exception:
                lang = "en"
        raise ValueError("يجب أن يكون سعر الصرف > 0" if lang == "ar" else "Rate must be > 0")
    init_db()
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("INSERT OR REPLACE INTO exchange_rates(date,from_currency,to_currency,rate,source) VALUES(?,?,?,?,?)",
                    (date_str, from_currency, to_currency, rate, "manual"))
    except Exception:
        cur.execute("INSERT OR REPLACE INTO exchange_rates(date,rate,source) VALUES(?,?,?)",
                    (date_str, rate, "manual"))
    conn.commit(); conn.close()
    return rate

def convert(amount, from_currency, base_currency=None, rate_date=None, rate=None):
    """Return (amount_in_base, amount_in_payment_currency).
    Missing rate for a foreign currency -> (None, None)."""
    base_currency = base_currency or default_currency()
    amount = float(amount or 0)
    if from_currency == base_currency:
        return (amount, amount)
    if rate is None:
        rate = get_rate(rate_date, from_currency, base_currency) if rate_date else None
    if rate is None:
        return (None, None)
    return (amount * float(rate), amount)

def format_amount(amount, currency):
    return f"{float(amount or 0):,.2f} {SYMBOLS.get(currency, currency)}"
