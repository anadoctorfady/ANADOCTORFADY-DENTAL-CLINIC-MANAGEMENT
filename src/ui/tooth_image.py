"""Tooth image loading for the dental chart (round 15; round 33
per-tooth assets).

Round 33: assets/teeth/ holds ONE anatomically differentiated AI
render per FDI tooth - 'tooth_11.png' .. 'tooth_85.png' for all 32
permanent + 20 deciduous teeth (the owner ruled no two teeth may
share a render; left-side teeth are true anatomical mirrors of the
right-side renders, mesial toward the midline). See
app_screens/teeth_ai/convert_r33_teeth.py for the pipeline.

The source PNGs are generated crown-up / root-down for BOTH jaws, so
the upper jaw displayed roots pointing down - wrong anatomy (upper
roots point UP, lower roots point DOWN). The flip happens here, at
load time, in PIL: upper-jaw images (permanent AND deciduous) are
flipped vertically; lower-jaw images are used as-is. The source PNG
files are never modified, so the conversion tests (which pin
crown-at-top in the files) still pass.

PhotoImages are cached on the toplevel, like the old loader in
dental_chart.py, so a cached image can never outlive the Tk
interpreter that owns it. The chart keeps the transparent PNGs on
Labels whose bg is the cell bg, so a selected cell still shows the
tooth on the accent colour - the flip module knows nothing about
selection or theme, only about the file on disk.
"""
import re
from pathlib import Path

from PIL import Image, ImageTk

from src.utils.helpers import DECIDUOUS, PERMANENT

TEETH_DIR = Path(__file__).resolve().parents[2] / "assets" / "teeth"
ALL_NAMES = [f"tooth_{n}.png" for n in PERMANENT + DECIDUOUS]
_UPPER_FIRST = "1256"  # FDI quadrants 1, 2 (permanent) + 5, 6 (deciduous)


def is_upper_jaw(name):
    """True for upper-jaw files: 'tooth_16.png' / 'tooth_65.png' need
    the vertical flip. Legacy '<kind>_upper.png' names (pre-round-33)
    are still recognised for any caller holding one."""
    m = re.search(r"tooth_(\d+)\.png$", str(name))
    if m:
        return m.group(1)[0] in _UPPER_FIRST
    return str(name).endswith("_upper.png")


def load_tooth_pil(name, teeth_dir=None):
    """PIL RGBA image for a tooth PNG file: upper-jaw images flipped
    vertically (roots up), lower-jaw images as generated (roots
    down). Pure PIL - no Tk needed, so tests assert the flip exactly
    against the file on disk. `teeth_dir` is only for tests that point
    the loader at a fake/missing directory."""
    im = Image.open(Path(teeth_dir or TEETH_DIR) / name).convert("RGBA")
    if is_upper_jaw(name):
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    return im


def tooth_photoimage(master, name, teeth_dir=None):
    """Tk PhotoImage for one tooth file (flipped if upper jaw).
    Cached per toplevel on the master, keyed by file name."""
    try:
        top = master.winfo_toplevel()
    except Exception:
        top = master
    cache = getattr(top, "_tooth_image_cache", None)
    if cache is None:
        cache = top._tooth_image_cache = {}
    img = cache.get(name)
    if img is None:
        img = ImageTk.PhotoImage(load_tooth_pil(name, teeth_dir),
                                 master=master)
        cache[name] = img
    return img


def load_tooth_images(master, teeth_dir=None):
    """All 52 tooth PhotoImages as {file name: PhotoImage}; {} when
    any file fails to load (the chart falls back to glyph buttons)."""
    try:
        return {name: tooth_photoimage(master, name, teeth_dir)
                for name in ALL_NAMES}
    except Exception:
        return {}
