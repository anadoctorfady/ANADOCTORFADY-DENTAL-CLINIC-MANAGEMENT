"""World data: 249 countries/nationalities + 178 currencies, searchable."""
from src.utils.nationalities import (list_nationalities, search_nationalities,
    display, display_for, nationality_en_for)
from src.utils.currencies import (list_currencies, search_currencies,
    display_for_code, code_for)
from src.utils.searchable import filter_list
from src.models.currency import CURRENCIES, LABELS, convert
from src.utils.helpers import NATIONALITIES

def test_nationalities_cover_world():
    items = list_nationalities()
    assert len(items) == 249
    codes = {i["code"] for i in items}
    assert {"SY", "TR", "SA", "EG", "US", "GB", "FR", "CN", "IN", "BR"} <= codes
    assert len(codes) == 249
    for i in items:
        assert i["country_ar"] and i["nationality_ar"] and i["nationality_en"]

def test_nationality_search_ar_en_code():
    assert [i["code"] for i in search_nationalities("سوريا")] == ["SY"]
    assert [i["code"] for i in search_nationalities("Turkey")] == ["TR"]
    assert [i["code"] for i in search_nationalities("تركيا")] == ["TR"]
    assert search_nationalities("سوري")  # masculine AR in data
    assert search_nationalities("") == list_nationalities()

def test_nationality_display_single_language_r17():
    # Round 17: nationality display is single-language, like currency;
    # the legacy bilingual string still parses to the stored EN value.
    import re as _re
    assert display_for("Syrian", "en") == "Syrian"
    assert not _re.search(r"[\u0600-\u06FF]", display_for("Syrian", "en"))
    assert display_for("Syrian", "ar") == "سوري"
    assert not _re.search(r"[A-Za-z]{3,}", display_for("Syrian", "ar"))
    assert nationality_en_for("Syrian / سوري") == "Syrian"
    assert nationality_en_for(display_for("Syrian", "ar")) == "Syrian"

def test_nationality_legacy_feminine_maps():
    # Round 17: display_for is single-language (explicit lang here);
    # legacy bilingual strings still PARSE via nationality_en_for.
    assert display_for("سورية", "en") == "Syrian"
    assert display_for("سورية", "ar") == "سوري"
    assert display_for("تركية", "en") == "Turkish"
    assert display_for("Syrian", "en") == "Syrian"
    assert display_for("أخرى", "en") == "Other"
    assert display_for("أخرى", "ar") == "أخرى"
    assert nationality_en_for("سورية") == "Syrian"
    assert nationality_en_for("Syrian / سوري") == "Syrian"
    assert nationality_en_for("SY") == "Syrian"

def test_currencies_cover_world():
    items = list_currencies()
    assert len(items) == 178
    assert len({c["code"] for c in items}) == 178
    assert len(CURRENCIES) == 178
    for c in ["SYP", "USD", "EUR", "SAR", "AED", "TRY", "JOD", "LBP",
              "EGP", "GBP", "IQD", "JPY", "CNY", "INR", "BRL", "ZAR"]:
        assert c in CURRENCIES
    assert LABELS["SYP"] == "ليرة سورية"
    assert LABELS["TRY"] == "ليرة تركية"

def test_currency_search_and_roundtrip():
    assert [c["code"] for c in search_currencies("USD")] == ["USD"]
    assert "USD" in [c["code"] for c in search_currencies("دولار")]
    assert [c["code"] for c in search_currencies("ليرة تركية")] == ["TRY"]
    assert [c["code"] for c in search_currencies("TRY")] == ["TRY"]
    # Round 17 item 5: currency display is single-language (app
    # language); code_for still parses legacy bilingual strings.
    assert display_for_code("SYP", "en") == "SYP - Syrian Pound"
    assert display_for_code("SYP", "ar") == "SYP - ليرة سورية"
    assert display_for_code("USD - US Dollar / دولار أمريكي", "en") == "USD - US Dollar"
    assert display_for_code("USD - US Dollar / دولار أمريكي", "ar") == "USD - دولار أمريكي"
    assert code_for("USD - US Dollar / دولار أمريكي") == "USD"
    assert code_for("USD / دولار أمريكي") == "USD"
    assert code_for("TRY") == "TRY"
    assert convert(100, "USD", rate=15000) == (1500000, 100)

def test_nationality_search_egypt():
    assert [i["code"] for i in search_nationalities("Egypt")] == ["EG"]
    assert [i["code"] for i in search_nationalities("مصر")] == ["EG"]
    assert [i["code"] for i in search_nationalities("مصري")] == ["EG"]
    assert [i["code"] for i in search_nationalities("Egyptian")] == ["EG"]

def test_filter_list_pure():
    items = list_nationalities()
    hits = filter_list(items, "syr", ["country_en", "nationality_en"])
    assert [i["code"] for i in hits] == ["SY"]
    assert filter_list(items, "", ["code"]) == items

def test_helpers_nationalities_full():
    assert len(NATIONALITIES) == 249
    assert "Syrian" in NATIONALITIES  # round 17: single-language names
