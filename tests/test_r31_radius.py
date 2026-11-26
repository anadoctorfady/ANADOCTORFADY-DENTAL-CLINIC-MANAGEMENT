"""Round 31, Item 1: entry tables/fields MORE rounded.

History: original scale CARD/PANEL 12, TABLE/TEXT/ICON 10,
FIELD/BTN 8. Round 28 REDUCED it (8/6) on a MISREADING of the
owner's request. Round 30 RAISED it above the originals
(CARD/PANEL 16, all other surfaces 12) per his correction.
Round 31 (owner live-use feedback after round 30): the tables
and fields he TYPES in need EVEN MORE rounding -- TABLE/TEXT
12->16, FIELD 12->14. Cards/panels (16), buttons (12) and
icons (12) are UNCHANGED.

Pins: (1) the central constant values; (2) ZERO hardcoded
radius literals anywhere in src/ -- every rounded surface must
route through the theme constants, so a future scale change is
one edit; (3) the render layer's defaults ARE the constants.
GUI parts skip without a display."""
import inspect
import re
import tkinter as tk
from pathlib import Path

from src.config import theme
from src.config.theme import (RADIUS_BTN, RADIUS_CARD, RADIUS_FIELD,
                              RADIUS_ICON, RADIUS_PANEL, RADIUS_TABLE,
                              RADIUS_TEXT)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def test_r31_radius_constants():
    assert (RADIUS_CARD, RADIUS_PANEL) == (16, 16)
    assert RADIUS_TABLE == 24, RADIUS_TABLE  # R31: 16 -> R43: 24 (owner: tables MORE rounded, corners antialiased)
    assert RADIUS_TEXT == 16, RADIUS_TEXT    # R30: 12 -> R31: 16
    assert RADIUS_FIELD == 14, RADIUS_FIELD  # R30: 12 -> R31: 14
    assert (RADIUS_BTN, RADIUS_ICON) == (12, 12)  # unchanged in R31
    assert theme.RADIUS_TABLE == 24 and theme.RADIUS_FIELD == 14


def test_no_hardcoded_radius_literals_in_src():
    """No `radius=<digit>` anywhere in src/, and the RADIUS_*
    constants are assigned ONLY in src/config/theme.py."""
    pat = re.compile(r"radius\s*=\s*\d")
    assign = re.compile(r"^RADIUS_\w+\s*=\s*\d", re.M)
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert not pat.search(text), f"{path}: hardcoded radius literal"
        if assign.search(text):
            assert path.name == "theme.py", f"{path}: RADIUS_* assignment"


def test_render_defaults_are_the_constants():
    from src.ui.rounded import RoundedButton
    from src.ui.rounded_frame import RoundedFrame
    from src.ui.rounded_lists import RoundedListbox, RoundedText
    from src.ui.rounded_widgets import RoundedEntry
    sig = inspect.signature
    assert sig(RoundedFrame.__init__).parameters["radius"].default == RADIUS_CARD
    assert sig(RoundedButton.__init__).parameters["radius"].default == RADIUS_BTN
    assert sig(RoundedEntry.__init__).parameters["radius"].default == RADIUS_FIELD
    assert sig(RoundedText.__init__).parameters["radius"].default == RADIUS_TEXT
    assert sig(RoundedListbox.__init__).parameters["radius"].default == RADIUS_TEXT


def _root():
    try:
        root = tk.Tk(); root.withdraw(); return root
    except tk.TclError:
        return None


def test_wrappers_instantiate_with_new_radii():
    root = _root()
    if root is None:
        print("SKIP r31 radius wrappers (no display)"); return
    try:
        from src.ui.rounded_lists import rounded_tree
        from src.ui.rounded_widgets import RoundedEntry
        e = RoundedEntry(root, width=8); e.pack()
        assert e._radius == RADIUS_FIELD == 14
        tr = rounded_tree(root, ("a",))
        assert tr._rounded_wrapper._radius == RADIUS_TABLE == 24
        root.update_idletasks()
    finally:
        root.destroy()
