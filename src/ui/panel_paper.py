"""Tinted paper background for COLOURED panels (Round 13, item 5 ext).

attach_paper_bg() tiles the Warm Sand tile as-is, which only suits
panels whose bg IS Warm Sand. Coloured panels - the patient-details
panel #E8DCC4, the white clinical patient panel - need the same
grain blended toward their own colour, exactly like texturize()
does for RoundedFrame fills. Light mode only; dark mode is a
no-op and any light-mode canvas is removed, so Warm Charcoal
stays flat. The blend keeps the panel's average colour (within
~12/channel), so text contrast is unchanged.
"""
import tkinter as tk
from PIL import Image, ImageColor

from src.config.theme import mode
from src.ui.image_cache import cached_photo  # R24 item 8
from src.ui.paper_bg import STRENGTH, TILE, tile_image

_TILE_CACHE = {}   # R24: {(bg, strength): PIL tinted tile}
_TILED_CACHE = {}  # R24: {(w, h, bg, strength): PIL tiled image}, bounded


def tinted_tile(bg_hex, strength=STRENGTH):
    """Paper tile blended toward a panel colour (RGB, TILE x TILE).
    R24: cached per (bg, strength) - deterministic blend."""
    out = _TILE_CACHE.get((bg_hex, strength))
    if out is None:
        base = Image.new("RGB", (TILE, TILE), ImageColor.getrgb(bg_hex))
        out = Image.blend(base, tile_image(), strength)
        _TILE_CACHE[(bg_hex, strength)] = out
    return out


def tinted_avg_hex(bg_hex, strength=STRENGTH):
    """Average colour of tinted_tile() as hex: labels sitting on a
    tinted panel use this as their bg, so they match the panel's
    average instead of showing as flat chips (dark mode: the caller
    must pass the raw panel colour instead)."""
    px = list(tinted_tile(bg_hex, strength).getdata())
    avg = tuple(sum(c[i] for c in px) // len(px) for i in range(3))
    return "#%02X%02X%02X" % avg


def tiled_tinted(w, h, bg_hex, strength=STRENGTH):
    """Tinted tile pasted to (w, h); exact repeats, no visible seams.
    R24: cached per (w, h, bg, strength), bounded to 8 entries FIFO."""
    key = (w, h, bg_hex, strength)
    out = _TILED_CACHE.get(key)
    if out is None:
        tile = tinted_tile(bg_hex, strength)
        out = Image.new("RGB", (max(1, w), max(1, h)))
        for y in range(0, h, TILE):
            for x in range(0, w, TILE):
                out.paste(tile, (x, y))
        if w * h <= 3_000_000: _TILED_CACHE[key] = out  # skip transient giants
        if len(_TILED_CACHE) > 8: _TILED_CACHE.pop(next(iter(_TILED_CACHE)))
    return out


def attach_panel_paper(window, bg_hex, strength=STRENGTH):
    """Tile tinted paper behind a panel's children (light mode only).
    Mirrors attach_paper_bg: the Canvas is created before the other
    children sit above it, <Configure> re-tiles it on resize, and
    the PhotoImage is kept alive on the canvas. Returns the Canvas
    or None (dark mode)."""
    old = getattr(window, "_panel_paper_canvas", None)
    if old is not None:
        try:
            old.destroy()
        except Exception:
            pass
        window._panel_paper_canvas = None
    if mode() == "dark":
        return None
    canvas = tk.Canvas(window, bg=bg_hex, highlightthickness=0, bd=0)
    canvas.place(x=0, y=0, relwidth=1, relheight=1)
    window._panel_paper_canvas = canvas

    def _retile(_e=None):
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w <= 2 or h <= 2 or getattr(canvas, "_paper_size", None) == (w, h):
            return
        canvas._paper_size = (w, h)
        img = cached_photo(canvas, ("panelpaper", w, h, bg_hex, strength, mode()),
                           lambda: tiled_tinted(w, h, bg_hex, strength))
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=img)
        canvas._paper_img = img  # GC guard: Tk drops unreferenced images

    canvas.bind("<Configure>", _retile)
    # Canvas.lower is the canvas-ITEM method; Misc.lower drops the widget.
    try:
        tk.Misc.lower(canvas)
    except Exception:
        pass
    _retile()
    return canvas
