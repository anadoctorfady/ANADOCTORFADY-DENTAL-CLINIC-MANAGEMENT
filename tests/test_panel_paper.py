"""Tinted paper panels (Round 13, item 5 extension): the clinical +
patient-form content panels carry the paper grain blended toward
their own colour (patient details #E8DCC4, white patient panel),
while dark mode stays plain Warm Charcoal. GUI tests skip
gracefully with no display, like the other paper tests."""
import tkinter as tk
from pathlib import Path

from src.config.theme import LIGHT
from src.config.settings import get_theme_mode, set_theme_mode
from src.ui.panel_paper import (attach_panel_paper, tinted_avg_hex,
                                tinted_tile, tiled_tinted)
from tests.test_paper_texture import _build_root, _lum, _pixels, _ratio

ROOT = Path(__file__).resolve().parent.parent
PANELS = {"patient_bg": LIGHT["patient_bg"], "panel": LIGHT["panel"]}


def _avg(img):
    px = _pixels(img)
    return tuple(sum(c[i] for c in px) // len(px) for i in range(3))


def test_tinted_tile_average_near_panel_colour():
    """Blending keeps the panel's average colour (within 15/channel):
    the grain shows, the panel does not change colour."""
    for name, bg in PANELS.items():
        avg = _avg(tinted_tile(bg))
        want = tuple(int(bg[i:i + 2], 16) for i in (1, 3, 5))
        for i in range(3):
            assert abs(avg[i] - want[i]) <= 15, f"{name}: {avg} vs {want}"
        assert tiled_tinted(512, 300, bg).size == (512, 300)


def test_tinted_avg_hex_matches_tile_average():
    """tinted_avg_hex() is the average of tinted_tile() (labels on a
    tinted panel use it as their bg so they do not show as chips)."""
    for bg in PANELS.values():
        px = _pixels(tinted_tile(bg, 0.25))
        want = tuple(sum(c[i] for c in px) // len(px) for i in range(3))
        assert tinted_avg_hex(bg, 0.25) == "#%02X%02X%02X" % want


def test_text_contrast_on_tinted_panels():
    """Theme text + muted stay >= 4.5:1 on the darkest and lightest
    pixels of each tinted panel (texture must never break legibility)."""
    for name, bg in PANELS.items():
        px = _pixels(tinted_tile(bg))
        darkest, lightest = min(px, key=_lum), max(px, key=_lum)
        for fg in (LIGHT["text"], LIGHT["muted"]):
            for spot in (darkest, lightest):
                assert _ratio(fg, spot) >= 4.5, f"{name} {fg} on {spot}: {_ratio(fg, spot):.2f}"


def test_attach_panel_paper_light_and_dark():
    """Light mode attaches a tiling Canvas; dark mode attaches
    nothing and removes a light-mode canvas (same contract as
    attach_paper_bg)."""
    for mode_name, expect in (("light", True), ("dark", False)):
        root, prev = _build_root(mode_name)
        if root is None:
            print(f"SKIP test_attach_panel_paper_{mode_name} (no display)")
            continue
        try:
            canvas = attach_panel_paper(root, LIGHT["patient_bg"])
            if expect:
                assert canvas is not None and isinstance(canvas, tk.Canvas)
                assert root._panel_paper_canvas is canvas
                root.geometry("800x600")
                root.deiconify()  # withdrawn roots report 1x1: no tiling yet
                root.update_idletasks()
                root.update()
                assert canvas.find_all(), "panel canvas has no tiled image"
                root.withdraw()
            else:
                assert canvas is None
                assert getattr(root, "_panel_paper_canvas", None) is None
        finally:
            root.destroy()
            set_theme_mode(prev)
    root, prev = _build_root("light")
    if root is None:
        print("SKIP test_attach_panel_paper_transition (no display)")
        return
    try:
        assert attach_panel_paper(root, LIGHT["panel"]) is not None
        set_theme_mode("dark")
        assert attach_panel_paper(root, LIGHT["panel"]) is None
        assert getattr(root, "_panel_paper_canvas", None) is None
    finally:
        root.destroy()
        set_theme_mode(prev)


def test_clinical_form_panel_wiring():
    """clinical.py + patient_form.py wire the paper in and stay
    within the 200-line rule (item 5 extension, round 13)."""
    for name in ("clinical.py", "patient_form.py"):
        src = (ROOT / "src" / "ui" / name).read_text(encoding="utf-8")
        assert len(src.splitlines()) <= 200, f"{name} exceeds 200 lines"
        assert "attach_paper_bg" in src, f"{name}: no page paper"
        assert "attach_panel_paper" in src, f"{name}: no panel paper"
    form = (ROOT / "src" / "ui" / "patient_form.py").read_text(encoding="utf-8")
    assert "bg=_pb" in form, "form labels must use the tinted average bg"
    assert "attach_paper_bg(bar)" in (ROOT / "src" / "ui" / "clinical.py").read_text(encoding="utf-8")
