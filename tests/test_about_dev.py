"""About tab wording (round 15, 2026-11-10): the About text names Fady
as "the developer / المطور" before his name, in both languages."""
from src.config.settings import ABOUT_EN, ABOUT_AR


def test_about_en_names_developer():
    assert "the developer Dr Fady" in ABOUT_EN
    assert "Dr Fady Abdulkafy Dadoush" in ABOUT_EN
    assert "ongoing charity for the developer Dr Fady Abdulkafy Dadoush" in ABOUT_EN


def test_about_ar_names_developer():
    assert "المطور د. فادي" in ABOUT_AR
    assert "د. فادي عبد الكافي دعدوش" in ABOUT_AR
    assert "صدقة جارية عن المطور د. فادي عبد الكافي دعدوش" in ABOUT_AR
