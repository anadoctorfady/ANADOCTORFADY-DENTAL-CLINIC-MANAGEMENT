"""Warm beige paper texture (Round 13, Item 5): the light-mode
background carries a subtle tileable paper texture like the owner's
reference image; dark mode keeps plain Warm Charcoal.

GUI tests build a bare Tk window under Xvfb and skip gracefully
when no display is available (plain `run_tests.py` without Xvfb)."""
import tkinter as tk
from pathlib import Path

from PIL import Image

from src.config.theme import LIGHT, DARK
from src.config.settings import get_theme_mode, set_theme_mode
from src.ui.paper_bg import (TEXTURE_PATH, TILE, BASE, STRENGTH,
                             attach_paper_bg, ensure_texture,
                             generate_texture, texturize, tile_image,
                             tiled_image)
from src.ui.rounded import rounded_pil

ROOT = Path(__file__).resolve().parent.parent


def _lum(rgb):
    f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4
    r, g, b = (f(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(fg_hex, bg_rgb):
    fg = tuple(int(fg_hex[i:i + 2], 16) for i in (1, 3, 5))
    a, b = _lum(fg), _lum(bg_rgb)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _pixels(img):
    return list(img.getdata())


def test_texture_asset_exists_and_matches_generator():
    """The committed asset is 256x256 RGB and pixel-identical to what
    generate_texture() produces (a replaced / non-tileable asset trips
    this, and the app regenerates it in memory when it is missing)."""
    assert TEXTURE_PATH.exists(), f"missing {TEXTURE_PATH}"
    asset = Image.open(TEXTURE_PATH).convert("RGB")
    assert asset.size == (TILE, TILE), asset.size
    assert _pixels(asset) == _pixels(generate_texture())
    assert ensure_texture() == TEXTURE_PATH


def test_texture_subtle_low_contrast():
    """Subtle: every pixel stays close to the Warm Sand base, and the
    luminance span is narrow - paper grain, not a pattern."""
    px = _pixels(generate_texture())
    for c in px:
        for i, base in enumerate(BASE):
            assert abs(c[i] - base) <= 20, f"pixel {c} too far from base {BASE}"
    ls = [_lum(c) for c in px]
    assert max(ls) - min(ls) < 0.18, f"luminance range {max(ls) - min(ls):.3f}"
    assert 0.75 < min(ls) and max(ls) < 0.95


def test_texture_tileable_no_seam():
    """Tiling 2x2 repeats the tile exactly, and the jump across the
    seam is no worse than a typical jump between adjacent columns
    inside the tile (wrapped fibres/mottling, per-pixel grain)."""
    tile = generate_texture()
    big = Image.new("RGB", (2 * TILE, TILE))
    big.paste(tile, (0, 0))
    big.paste(tile, (TILE, 0))
    assert big.crop((0, 0, TILE, TILE)).tobytes() == big.crop((TILE, 0, 2 * TILE, TILE)).tobytes()
    seam = [max(abs(big.getpixel((TILE - 1, y))[i] - big.getpixel((TILE, y))[i])
                for i in range(3)) for y in range(TILE)]
    inside = [max(abs(big.getpixel((x, y))[i] - big.getpixel((x + 1, y))[i])
                  for i in range(3)) for x in range(0, TILE - 1)
              for y in range(0, TILE, 17)]
    assert max(seam) <= max(inside), f"seam jump {max(seam)} > inside {max(inside)}"


def test_text_contrast_on_texture():
    """Theme text + muted stay >= 4.5:1 on BOTH the darkest and the
    lightest texture pixels (the texture must never break legibility).
    The light accent (3.13:1 on plain Warm Sand) is out of scope."""
    px = _pixels(generate_texture())
    darkest, lightest = min(px, key=_lum), max(px, key=_lum)
    for fg in (LIGHT["text"], LIGHT["muted"]):
        for bg in (darkest, lightest):
            assert _ratio(fg, bg) >= 4.5, f"{fg} on {bg}: {_ratio(fg, bg):.2f}"
    # And on a texturized white panel (RoundedFrame fill #FFFFFF).
    prev = get_theme_mode()
    try:
        set_theme_mode("light")
        panel = texturize(rounded_pil(200, 100, 12, "#FFFFFF"))
    finally:
        set_theme_mode(prev)
    assert panel.mode == "RGBA"
    # Only opaque pixels count: transparent corners convert to black.
    px2 = [c[:3] for c in _pixels(panel) if c[3] == 255]
    assert px2, "texturized panel has no opaque pixels"
    for fg in (LIGHT["text"], LIGHT["muted"]):
        assert _ratio(fg, min(px2, key=_lum)) >= 4.5, fg


def test_texturize_keeps_transparent_corners_light_only():
    """Rounded corners stay transparent after texturizing (light);
    dark mode returns the image untouched."""
    prev = get_theme_mode()
    try:
        set_theme_mode("light")
        img = rounded_pil(120, 80, 12, "#F6F1E9", "#E3D8CC")
        out = texturize(img)
        assert out.size == img.size
        assert out.split()[3].getpixel((0, 0)) == 0  # corner transparent
        assert out.split()[3].getpixel((60, 40)) == 255  # centre opaque
        assert out.convert("RGB").getpixel((60, 40)) != (246, 241, 233)
        set_theme_mode("dark")
        assert texturize(img) is img  # dark: no texture, same object
    finally:
        set_theme_mode(prev)


def _build_root(mode):
    """Bare Tk root in the requested theme; None when no display."""
    prev = get_theme_mode()
    set_theme_mode(mode)
    try:
        root = tk.Tk()
    except tk.TclError:
        set_theme_mode(prev)
        return None, prev
    root.withdraw()
    return root, prev


def test_attach_paper_bg_light_and_dark():
    """Light mode attaches a tiling Canvas behind the window;
    dark mode attaches nothing and removes a light-mode canvas."""
    for mode_name, expect_canvas in (("light", True), ("dark", False)):
        root, prev = _build_root(mode_name)
        if root is None:
            print(f"SKIP test_attach_paper_bg_{mode_name} (no display)")
            continue
        try:
            canvas = attach_paper_bg(root)
            if expect_canvas:
                assert canvas is not None and isinstance(canvas, tk.Canvas)
                assert root._paper_canvas is canvas
                root.geometry("800x600")
                root.deiconify()  # withdrawn roots report 1x1: no tiling yet
                root.update_idletasks()
                root.update()
                assert canvas.find_all(), "canvas has no tiled image"
                root.withdraw()
            else:
                assert canvas is None
                assert getattr(root, "_paper_canvas", None) is None
        finally:
            root.destroy()
            set_theme_mode(prev)
    # Light -> dark transition on the same window removes the canvas.
    root, prev = _build_root("light")
    if root is None:
        print("SKIP test_attach_paper_bg_transition (no display)")
        return
    try:
        assert attach_paper_bg(root) is not None
        set_theme_mode("dark")
        assert attach_paper_bg(root) is None
        assert getattr(root, "_paper_canvas", None) is None
    finally:
        root.destroy()
        set_theme_mode(prev)


def test_shell_wiring_line_neutral():
    """shell.py still fits the 200-line rule and calls the helpers in
    __init__ / _rebuild (theme toggle re-tiles) and _main (paper
    patient list); RoundedFrame texturizes its panels; clinical.py
    and patient_form.py now wire the paper into their own panels
    (round 13 item 5 extension)."""
    shell = (ROOT / "src" / "ui" / "shell.py").read_text(encoding="utf-8")
    lines = shell.splitlines()
    assert len(lines) <= 200, f"shell.py is {len(lines)} lines, must stay <= 200"
    assert shell.count("_paper(self)") == 2, "attach in __init__ + _rebuild"
    assert "attach_paper_bg" in shell
    assert "_tree_paper(style, th)" in shell
    # R21 item 2: the patient tree moved into shell_left.py (build_left_column).
    shell_left = (ROOT / "src" / "ui" / "shell_left.py").read_text(encoding="utf-8")
    assert 'style="Paper.Treeview"' in shell_left
    assert "texturize" in (ROOT / "src" / "ui" / "rounded_frame.py").read_text(encoding="utf-8")
    assert "attach_panel_paper" in (ROOT / "src" / "ui" / "clinical.py").read_text(encoding="utf-8")
    assert "attach_panel_paper" in (ROOT / "src" / "ui" / "patient_form.py").read_text(encoding="utf-8")


def test_dark_tokens_untouched():
    """Dark mode keeps plain Warm Charcoal - no beige anywhere."""
    assert DARK["bg"] == "#1A1614" and DARK["panel"] == "#26211E"
    assert LIGHT["bg"] == "#F6F1E9"  # Warm Sand base unchanged
    assert tile_image().size == (TILE, TILE)
    assert tiled_image(512, 300).size == (512, 300)
    assert abs(_lum(BASE) - 0.884) < 0.01
