"""No white anywhere (round 16, owner rule): no white BACKGROUND in
the app UI. White TEXT on a dark/accent background stays (correct
contrast); the PDF footer bar is print output, not app UI, and is
not scanned here (src/reports is out of scope for this test).

Static scan over src/ui + src/config/theme.py: any bg=/background=/
fieldbackground= set to "white" / #FFFFFF / #FFF fails, as does a
white light panel/card token. Contrast of the sand panel is pinned
too: the light accent must still reach 4.5:1 on it (it darkened when
white left, #A85F33 -> #8A4A22).
"""
import re
from pathlib import Path

from src.config.theme import LIGHT, DARK

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = [ROOT / "src" / "ui", ROOT / "src" / "config" / "theme.py"]

_BG_RE = re.compile(
    r"""\b(?:bg|background|fieldbackground)\s*=\s*["'](?:white|#[Ff]{3}|#[Ff]{6})["']""")
_PANEL_RE = re.compile(
    r"""["'](?:panel|card)["']\s*:\s*["']#(?:[Ff]{3}|[Ff]{6})["']""")


def _strip_strings_and_comments(src):
    """Drop triple-quoted blocks and full-line comments so docstrings
    that merely MENTION white (e.g. 'was pure white') cannot trip the
    scan; code tokens survive."""
    src = re.sub(r'"""[\s\S]*?"""', '""', src)
    src = re.sub(r"'''[\s\S]*?'''", "''", src)
    lines = [ln for ln in src.splitlines()
             if not ln.strip().startswith("#")]
    return "\n".join(lines)


def _lum(hexcol):
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(fg, bg):
    a, b = _lum(fg), _lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _iter_files():
    for d in SCAN_DIRS:
        if d.is_file():
            yield d
        else:
            yield from sorted(d.glob("*.py"))


def test_no_white_background_in_ui_code():
    """No bg=/background=/fieldbackground= white in UI code, and no
    white panel/card token in the theme. White TEXT (fg=) is allowed
    and is not matched by these patterns."""
    bad = []
    for path in _iter_files():
        clean = _strip_strings_and_comments(
            path.read_text(encoding="utf-8"))
        for lineno, line in enumerate(clean.splitlines(), 1):
            if _BG_RE.search(line) or _PANEL_RE.search(line):
                bad.append(f"{path.name}:{lineno}: {line.strip()[:120]}")
    assert not bad, "white backgrounds remain:\n" + "\n".join(bad)


def test_light_tokens_are_sand_not_white():
    """Light panel/card are warm sand (luminance well below white)."""
    assert LIGHT["panel"] not in ("#FFFFFF", "#FFF")
    assert LIGHT["card"] not in ("#FFFFFF", "#FFF")
    assert _lum(LIGHT["panel"]) < 0.90, LIGHT["panel"]
    assert _lum(LIGHT["card"]) < 0.90, LIGHT["card"]
    assert LIGHT["panel"] != LIGHT["bg"]
    assert LIGHT["card"] != LIGHT["bg"]


def test_light_accent_reads_on_sand_panel():
    """Accent / muted / text / violet all reach 4.5:1 on the sand panel
    and on the main bg, in light mode; dark tokens unchanged."""
    for fg in (LIGHT["accent"], LIGHT["muted"], LIGHT["text"],
               LIGHT["header1"]):
        assert _ratio(fg, LIGHT["panel"]) >= 4.5, f"{fg} on panel"
        assert _ratio(fg, LIGHT["bg"]) >= 4.5, f"{fg} on bg"
    assert _ratio("#FFFFFF", LIGHT["accent"]) >= 4.5  # white text on buttons
    assert DARK["panel"] == "#26211E"  # dark mode untouched
