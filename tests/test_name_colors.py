"""Patient-name colours (2026-11-07, owner-approved): same six hues in
the same order in both modes - darker shades in light mode, lighter
shades in dark mode - every colour >= 4.5:1 WCAG on its own mode's list
background. Hues and rotation logic are unchanged; only shades differ."""
import colorsys
from pathlib import Path

from src.config.theme import (NAME_COLORS_LIGHT, NAME_COLORS_DARK,
                              LIGHT, DARK, name_colors)

ROOT = Path(__file__).resolve().parent.parent


def _lum(hexcol):
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(fg, bg):
    a, b = _lum(fg), _lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _hue(hexcol):
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hsv(r, g, b)[0] * 360


def test_name_colors_light_readable():
    assert len(NAME_COLORS_LIGHT) == 6
    for c in NAME_COLORS_LIGHT:
        r = _ratio(c, LIGHT["list_bg"])
        assert r >= 4.5, f"light name {c}: {r:.2f} on {LIGHT['list_bg']}"


def test_name_colors_dark_readable():
    assert len(NAME_COLORS_DARK) == 6
    for c in NAME_COLORS_DARK:
        r = _ratio(c, DARK["list_bg"])
        assert r >= 4.5, f"dark name {c}: {r:.2f} on {DARK['list_bg']}"


def test_name_colors_same_hue_order():
    """Same six hues in the same order - only the shade changes per mode."""
    assert len(NAME_COLORS_LIGHT) == len(NAME_COLORS_DARK) == 6
    for a, b in zip(NAME_COLORS_LIGHT, NAME_COLORS_DARK):
        d = abs(_hue(a) - _hue(b))
        assert min(d, 360 - d) <= 15, f"hue drift {a} vs {b}"


def test_name_colors_selector():
    assert name_colors(False) == NAME_COLORS_LIGHT
    assert name_colors(True) == NAME_COLORS_DARK
    # shell.py colours names from the per-mode palette, not the old constant.
    shell = (ROOT / "src" / "ui" / "shell.py").read_text(encoding="utf-8")
    assert "name_colors(" in shell
    assert "NAME_COLORS" not in shell
