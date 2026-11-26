"""Corner-radius scale, pinned at the central constants.

History: the original scale was CARD/PANEL 12, TABLE/TEXT/ICON
10, FIELD/BTN 8. Round 28 item 1 REDUCED it to 8/6 on a
MISREADING of the owner's request. Round 30 RAISED it ABOVE the
originals per the owner's explicit correction (CARD/PANEL 16,
all other surfaces 12). Round 31 (owner live-use feedback):
the tables/fields he TYPES in go rounder still -- TABLE/TEXT
16, FIELD 14; CARD/PANEL 16 and BTN/ICON 12 unchanged.
Pins the new values so the scale cannot silently regress, and
checks the render layer actually consumes them (RoundedFrame /
rounded_tree defaults + the image-cache key, which must include
the radius so no stale corner image survives the change).
GUI parts skip without a display."""
import tkinter as tk
from src.config import theme
from src.config.theme import (RADIUS_BTN, RADIUS_CARD, RADIUS_FIELD,
                              RADIUS_ICON, RADIUS_PANEL, RADIUS_TABLE,
                              RADIUS_TEXT)

def test_radius_constants_reduced():
    # Round 31 scale: R30 was CARD/PANEL 16, all others 12; R31
    # raises TABLE/TEXT to 16 and FIELD to 14 (owner live use).
    assert (RADIUS_CARD, RADIUS_PANEL) == (16, 16), (RADIUS_CARD, RADIUS_PANEL)
    assert RADIUS_TABLE == 24, RADIUS_TABLE  # R43: 16 -> 24 (owner: tables more rounded)
    assert (RADIUS_TEXT, RADIUS_ICON) == (16, 12), (RADIUS_TEXT, RADIUS_ICON)
    assert (RADIUS_FIELD, RADIUS_BTN) == (14, 12), (RADIUS_FIELD, RADIUS_BTN)
    assert max(RADIUS_CARD, RADIUS_PANEL, RADIUS_TABLE, RADIUS_TEXT,
               RADIUS_ICON, RADIUS_FIELD, RADIUS_BTN) == 24
    assert min(RADIUS_CARD, RADIUS_PANEL, RADIUS_TABLE, RADIUS_TEXT,
               RADIUS_ICON, RADIUS_FIELD, RADIUS_BTN) == 12
    assert theme.RADIUS_CARD == RADIUS_CARD  # single source of truth

def _root():
    try:
        root = tk.Tk(); root.withdraw(); return root
    except tk.TclError:
        return None

def test_render_defaults_use_constants():
    root = _root()
    if root is None:
        print("SKIP r28 radius render (no display)"); return
    try:
        import inspect
        from src.ui.rounded_frame import RoundedFrame
        from src.ui.rounded_lists import rounded_tree
        assert inspect.signature(RoundedFrame.__init__).parameters[
            "radius"].default == RADIUS_CARD
        f = RoundedFrame(root, bg="#EDE4D3", border="#D9C39A")
        assert f._radius == RADIUS_CARD
        tr = rounded_tree(root, ("a",))
        assert tr._rounded_wrapper._radius == RADIUS_TABLE
    finally:
        root.destroy()

def test_image_cache_key_includes_radius():
    root = _root()
    if root is None:
        print("SKIP r28 cache key (no display)"); return
    try:
        root.deiconify(); root.geometry("300x200+0+0")
        from src.ui.image_cache import _cache_for
        from src.ui.rounded_frame import RoundedFrame
        a = RoundedFrame(root, bg="#EDE4D3", border="#D9C39A", radius=6)
        a.pack(fill="both", expand=True)
        b = RoundedFrame(root, bg="#EDE4D3", border="#D9C39A", radius=12)
        b.pack(fill="both", expand=True)
        root.update_idletasks(); root.update()
        radii = {k[3] for tier in _cache_for(root).values() for k in tier if k and k[0] == "frame"}  # R52: cache is tiered (small/large dicts)
        assert 6 in radii and 12 in radii, radii  # radius is in the key
    finally:
        root.destroy()
