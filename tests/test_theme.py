"""Theme tokens: Warm Sand light/dark."""
from src.config.theme import LIGHT, DARK, tokens
def test_light():
    assert LIGHT["bg"] == "#F6F1E9" and LIGHT["accent"] == "#8A4A22"
    assert LIGHT["panel"] == "#EDE4D3" and LIGHT["card"] == "#F2EBDD" and LIGHT["patient_bg"] == "#E8DCC4"
def test_dark():
    assert DARK["bg"] == "#1A1614" and DARK["accent"] == "#D97736"
    assert DARK["text"] == "#F5F0EB"
def test_tokens():
    assert tokens(False)["bg"] == "#F6F1E9"
    assert tokens(True)["bg"] == "#1A1614"
