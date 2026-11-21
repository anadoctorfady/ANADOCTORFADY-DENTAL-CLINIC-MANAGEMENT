"""App icon (item 14): app.ico is the gold tooth + crown logo, not a feather.

Regenerated from assets/logo_anadoctorfady.png (emblem only, no text —
text is illegible at icon sizes). Asserts the ICO holds the full size
set 16/20/24/32/48/64/128/256, renders non-blank with gold pixels and
transparent corners (the OLD icon was the retired "FADY DENTAL CLINIC"
logo on an opaque black square), the PyInstaller spec embeds it, and
the login window sets a Tk icon. Round 19: the emblem is cropped to
its opaque bounding box and padded ~5% per side, so it fills ~90% of
the frame instead of ~72% (the installed icon looked too small).
Runs with plain python (no pytest needed).
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ICO = ROOT / "assets" / "app.ico"
SPEC = ROOT / "installer" / "ANADOCTORFADY.spec"
LOGIN = ROOT / "src" / "ui" / "login.py"
SIZES = {(16, 16), (20, 20), (24, 24), (32, 32), (48, 48), (64, 64),
         (128, 128), (256, 256)}


def _render(size):
    """One ICO frame as RGBA (composited copy, never mutates the file)."""
    im = Image.open(ICO)
    im.size = size
    return im.copy().convert("RGBA")


def _gold_pixels(img):
    """Gold-ish pixels: strong red, mid green, low blue (logo gold)."""
    n = 0
    for r, g, b, a in img.getdata():
        if a > 10 and r > 150 and g > 90 and b < 140 and r - b > 40:
            n += 1
    return n


def test_app_icon_exists_and_sizes():
    assert ICO.is_file(), "assets/app.ico missing"
    assert ICO.stat().st_size > 1000, "app.ico suspiciously small"
    im = Image.open(ICO)
    assert im.format == "ICO", im.format
    assert set(im.info.get("sizes", [])) == SIZES, im.info.get("sizes")


def test_app_icon_renders_gold_on_transparent():
    for size in sorted(SIZES):
        img = _render(size)
        assert img.size == size
        gold = _gold_pixels(img)
        # Even the 16px frame must show the gold tooth + crown.
        assert gold >= 20, (size, gold)
        # Transparent corners: no opaque black square behind the logo
        # (the old icon was fully opaque, alpha 255 everywhere).
        w, h = size
        corners = [img.getpixel(p)[3] for p in
                   ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
        assert all(a == 0 for a in corners), (size, corners)
        # Not mostly black: the old icon's background was a black square.
        px = list(img.getdata())
        black = sum(1 for r, g, b, a in px if a > 10 and r < 30 and g < 30 and b < 30)
        assert black < len(px) * 0.05, (size, black)


def test_app_icon_matches_logo_emblem():
    """New ICO gold comes from the current logo (not the retired FADY one)."""
    logo = Image.open(ROOT / "assets" / "logo_anadoctorfady.png")
    assert logo.size == (508, 470) and logo.mode == "RGBA"
    assert _gold_pixels(logo.convert("RGBA")) > 10000
    assert _gold_pixels(_render((256, 256))) > 1000


def test_app_icon_emblem_fills_frame():
    """Round 19: emblem fills >=80% of the 256 frame width (was ~72%).

    "Opaque" = alpha > 10, the same threshold the gold-pixel count uses;
    near-invisible resampling halo does not count as emblem.
    """
    img = _render((256, 256))
    mask = img.getchannel("A").point(lambda a: 255 if a > 10 else 0)
    bbox = mask.getbbox()
    assert bbox is not None, "256 frame is fully transparent"
    fill = (bbox[2] - bbox[0]) / 256
    assert fill >= 0.80, (bbox, fill)


def test_spec_embeds_app_icon():
    text = SPEC.read_text(encoding="utf-8")
    assert "app.ico" in text, "spec does not reference app.ico"
    assert "icon=" in text and "../assets/app.ico" in text, text


def test_login_sets_window_icon():
    src = LOGIN.read_text(encoding="utf-8")
    assert "iconphoto" in src, "login.py never calls iconphoto"
    assert "photo(" in src, "login.py does not use the logo helper"
