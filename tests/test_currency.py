"""Currency: SYP/USD, missing rate, multi-currency base."""
from src.models.currency import convert, save_rate, get_rate, latest_rate, CURRENCIES
from src.config.settings import set_default_currency, get_default_currency
def test_currencies_supported():
    for c in ["SYP", "USD", "EUR", "SAR", "AED", "TRY", "JOD", "LBP", "EGP", "GBP", "IQD"]:
        assert c in CURRENCIES
def test_syp_no_conversion():
    assert convert(100000, "SYP") == (100000, 100000)
def test_usd_100_at_15000():
    assert convert(100, "USD", rate=15000) == (1500000, 100)
def test_usd_missing_rate_returns_none():
    assert convert(100, "USD", rate_date="2099-01-01") == (None, None)
def test_save_get_rate_roundtrip():
    save_rate("2026-11-05", 15000); assert get_rate("2026-11-05") == 15000
    assert latest_rate() is not None
def test_usd_uses_saved_rate():
    save_rate("2026-11-06", 15000)
    assert convert(100, "USD", rate_date="2026-11-06")[0] == 1500000
def test_base_try_usd_100_at_40():
    assert convert(100, "USD", "TRY", rate=40) == (4000, 100)
def test_base_eur_usd_50_at_092():
    assert convert(50, "USD", "EUR", rate=0.92) == (46.0, 50)
def test_default_currency_changeable():
    set_default_currency("TRY"); assert get_default_currency() == "TRY"
    set_default_currency("SYP"); assert get_default_currency() == "SYP"
def test_same_currency_no_rate():
    assert convert(100, "TRY", "TRY") == (100, 100)
