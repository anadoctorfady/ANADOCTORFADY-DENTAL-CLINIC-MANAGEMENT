"""Round 15 regression (2026-11-10): upper teeth flipped roots-up.

The AI PNGs are crown-up / root-down for BOTH jaws, so the upper jaw
showed roots pointing down. The flip happens at load time in
src/ui/tooth_image.py (files untouched); lower teeth are unchanged.
These are the pure-PIL tests: they assert the flip exactly
(pixel-identical to a vertical flip of the source for upper,
byte-identical for lower) and in the expected direction (the crown's
opaque mass moves to the bottom half for upper teeth only). The GUI
half (chart loads, order, clicks, main background) lives in
tests/test_teeth_flip_gui.py.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from src.ui import tooth_image
from src.ui.tooth_image import ALL_NAMES, is_upper_jaw, load_tooth_pil

TEETH_DIR = Path(tooth_image.__file__).resolve().parents[2] / "assets" / "teeth"
# Round 33: per-tooth names tooth_<FDI>.png; jaw from the FDI quadrant
# digit (1/2/5/6 = upper, 3/4/7/8 = lower).
UPPER = [n for n in ALL_NAMES if n[6] in "1256"]
LOWER = [n for n in ALL_NAMES if n[6] in "3478"]


def _opaque_halves(im):
    """(top-half, bottom-half) opaque-pixel counts of an RGBA image."""
    a = im.getchannel("A")
    top = sum(1 for x in range(48) for y in range(48)
              if a.getpixel((x, y)) > 128)
    bot = sum(1 for x in range(48) for y in range(48, 96)
              if a.getpixel((x, y)) > 128)
    return top, bot


def test_upper_lower_detection():
    assert len(ALL_NAMES) == 52
    assert len(UPPER) == 26 and len(LOWER) == 26
    for name in UPPER:
        assert is_upper_jaw(name), name
    for name in LOWER:
        assert not is_upper_jaw(name), name
    assert is_upper_jaw("tooth_65.png")
    assert not is_upper_jaw("tooth_85.png")
    # Legacy pre-round-33 names still recognised.
    assert is_upper_jaw("deciduous_molar_upper.png")
    assert not is_upper_jaw("deciduous_molar_lower.png")


def test_upper_images_flipped_vertically():
    """Loaded upper image == source flipped top-to-bottom, pixel for
    pixel; loaded lower image == source byte-for-byte."""
    for name in UPPER:
        src = Image.open(TEETH_DIR / name).convert("RGBA")
        got = load_tooth_pil(name)
        assert got.size == (48, 96) and got.mode == "RGBA", name
        assert got.tobytes() == src.transpose(
            Image.FLIP_TOP_BOTTOM).tobytes(), f"{name} not flipped"
        assert got.tobytes() != src.tobytes(), f"{name} flip is a no-op?"
    for name in LOWER:
        src = Image.open(TEETH_DIR / name).convert("RGBA")
        assert load_tooth_pil(name).tobytes() == src.tobytes(), name


def test_flip_direction_crown_moves_down_for_upper_only():
    """Source PNGs are crown-up: the wide crown holds more opaque
    mass in the top half. After the flip the upper crown is at the
    BOTTOM (roots up); lower teeth keep the crown on top."""
    for name in UPPER:
        stop, sbot = _opaque_halves(Image.open(TEETH_DIR / name))
        gtop, gbot = _opaque_halves(load_tooth_pil(name))
        assert stop > sbot, f"source {name} is not crown-up"
        assert gtop < gbot, f"loaded {name}: crown did not move down"
        assert (gtop, gbot) == (sbot, stop), f"{name}: halves not swapped"
    for name in LOWER:
        gtop, gbot = _opaque_halves(load_tooth_pil(name))
        assert gtop > gbot, f"loaded {name}: lower crown moved"


def test_source_files_still_crown_up():
    """Guard against 'fixing' the bug by editing the assets: every
    source PNG must stay crown-up (top half heavier), the flip stays
    a load-time operation."""
    for name in ALL_NAMES:
        top, bot = _opaque_halves(Image.open(TEETH_DIR / name))
        assert top > bot, f"source {name} was edited: not crown-up"


if __name__ == "__main__":
    for name in sorted(a for a in dir() if a.startswith("test_")):
        globals()[name]()
        print("PASS", name)
    print("ALL TEETH FLIP (PIL) TESTS PASSED")
