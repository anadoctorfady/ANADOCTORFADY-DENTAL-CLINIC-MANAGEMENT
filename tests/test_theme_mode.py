"""Dark Mode: light/dark tokens differ, mode persists."""
from src.config.theme import LIGHT, DARK, get_tokens, mode
from src.config.settings import set_theme_mode, get_theme_mode
def test_tokens_differ():
    assert get_tokens("light")["bg"] == "#F6F1E9"
    assert get_tokens("dark")["bg"] == "#1A1614"
    assert LIGHT["accent"] == "#8A4A22" and DARK["accent"] == "#D97736"
def test_mode_persists():
    set_theme_mode("dark")
    assert get_theme_mode() == "dark" and mode() == "dark"
    set_theme_mode("light")
    assert get_theme_mode() == "light" and mode() == "light"
def test_invalid_mode_defaults_light():
    set_theme_mode("bogus")
    assert get_theme_mode() == "light"
