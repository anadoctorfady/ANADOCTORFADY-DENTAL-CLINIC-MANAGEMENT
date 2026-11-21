"""Hijri: 1990-05-15 = 20 Shawwal 1410."""
import calendar
from datetime import date, timedelta
from src.utils.hijri_age import get_all_ages, greg_to_hijri
def test_hijri_date():
    info = get_all_ages("1990-05-15")
    assert info["hijri_date"] == (1410, 10, 20), info["hijri_date"]
    assert "1410" in info["hijri_formatted"]
def _add_months(d, months):
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
def test_greg_age():
    # Date-independent: the old pinned values (36y 5m 21d / 13323 days)
    # were only true on 2026-11-05 and failed from 2026-11-06 on.
    info = get_all_ages("1990-05-15")
    g = info["greg_age"]
    birth = date(1990, 5, 15)
    today = date.today()
    assert g["total_days"] == (today - birth).days
    assert 0 <= g["months"] < 12 and 0 <= g["days"] < 31
    assert _add_months(birth, g["years"] * 12 + g["months"]) + timedelta(days=g["days"]) == today
def test_hijri_age():
    info = get_all_ages("1990-05-15")
    assert info["hijri_age"]["years"] == 37
