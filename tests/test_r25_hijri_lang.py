"""Round 25 item 1: Hijri month names follow the app language.

format_hijri()/format_hijri_date()/get_all_ages() take a language;
EN output uses Latin month names + ' AH' with NO Arabic script,
AR output is byte-identical to the historical Arabic format.
Display sites (report_text) RE-DERIVE the Hijri date from
birth_date_greg instead of trusting the stored string, so a
patient saved while the UI was in Arabic still shows an English
Hijri date in an English report. Pinned case: 1990-05-15 =
20 Shawwal 1410."""
import re
from datetime import date

from src.utils.hijri_age import (format_hijri, format_hijri_date,
                                 get_all_ages)

_ARABIC_RE = re.compile(r"[؀-ۿ]")  # Arabic script block


def test_format_hijri_en():
    s = format_hijri((1410, 10, 20), "en")
    assert s == "20 Shawwal 1410 AH", s
    assert "Shawwal" in s and "1410" in s
    assert not _ARABIC_RE.search(s), s


def test_format_hijri_ar():
    s = format_hijri((1410, 10, 20), "ar")
    assert s == "20 شوال 1410هـ", s
    assert "شوال" in s


def test_format_hijri_date_iso():
    assert format_hijri_date("1990-05-15", "en") == "20 Shawwal 1410 AH"
    assert "Shawwal" in format_hijri_date("1990-05-15", "en")
    assert "شوال" in format_hijri_date("1990-05-15", "ar")


def test_format_hijri_date_other_inputs():
    # DD/MM/YYYY string and date object give the same result.
    assert format_hijri_date("15/05/1990", "en") == "20 Shawwal 1410 AH"
    assert format_hijri_date(date(1990, 5, 15), "en") == "20 Shawwal 1410 AH"
    # Empty / unparseable input -> "" and never raises.
    assert format_hijri_date("", "en") == ""
    assert format_hijri_date(None) == ""
    assert format_hijri_date("not-a-date", "en") == ""
    assert format_hijri_date("31/02/2000", "ar") == ""


def test_get_all_ages_lang():
    en = get_all_ages("1990-05-15", lang="en")["hijri_formatted"]
    assert "Shawwal" in en and not _ARABIC_RE.search(en), en
    ar = get_all_ages("1990-05-15", lang="ar")["hijri_formatted"]
    assert "شوال" in ar, ar


def test_report_text_rederives_hijri_en():
    """Stored-Arabic-string regression: the patient's stored
    birth_date_hijri is the Arabic string, but an EN report must
    show the re-derived English Hijri date, not the stored one."""
    from src.reports.report_text import patient_preview_lines
    patient = {"file_number": 925, "full_name": "Hijri Lang Test",
               "birth_date_greg": "1990-05-15",
               "birth_date_hijri": "20 شوال 1410هـ",
               "age_years": 36, "age_months": 0, "age_days": 0,
               "nationality": "Syrian", "mobile1": "", "mobile2": "",
               "emergency_phone": "", "address": "",
               "created_at": "2026-11-18", "diseases": ""}
    lines = patient_preview_lines(patient, language="en")
    hijri_lines = [ln for ln in lines if "Hijri" in ln]
    assert hijri_lines, lines
    assert any("Shawwal" in ln for ln in hijri_lines), hijri_lines
    assert not any("شوال" in ln for ln in hijri_lines), hijri_lines


def test_report_text_rederives_hijri_ar():
    from src.reports.report_text import patient_preview_lines
    patient = {"file_number": 926, "full_name": "Hijri Lang Test",
               "birth_date_greg": "1990-05-15",
               "birth_date_hijri": "20 Shawwal 1410 AH",
               "age_years": 36, "age_months": 0, "age_days": 0,
               "nationality": "Syrian", "mobile1": "", "mobile2": "",
               "emergency_phone": "", "address": "",
               "created_at": "2026-11-18", "diseases": ""}
    lines = patient_preview_lines(patient, language="ar")
    assert any("شوال" in ln for ln in lines), lines
    assert not any("Shawwal" in ln for ln in lines), lines
