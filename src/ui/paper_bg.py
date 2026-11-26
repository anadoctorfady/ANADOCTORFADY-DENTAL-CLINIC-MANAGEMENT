"""Warm beige paper texture (Round 13, Item 5) - LIGHT mode only.

The 256 tile (assets/paper_texture.png) is PIL-generated from Warm
Sand #F6F1E9: per-pixel grain (+/-5), faint wrapped fibres, soft
mottling, all low-contrast; tileable by construction. Helpers:
attach_paper_bg() tiles it on a Canvas behind a window's children
(root background); texturize() blends it into a PIL image
(RoundedFrame panels); apply_treeview_paper() gives the patient-list
Treeview a tiled paper field. DARK mode: all three no-op. The tile
is also generated in memory at runtime, so a missing asset never
breaks the app. R24 item 8: tiled PIL images + the root PhotoImage
are cached (see image_cache.py), not re-tiled on every rebuild.
"""
import random
from pathlib import Path

import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageTk

from src.config.theme import LIGHT, mode
from src.ui.image_cache import cached_photo

ASSETS = Path(__file__).resolve().parent.parent.parent / "assets"
TEXTURE_PATH = ASSETS / "paper_texture.png"
TILE, SEED, STRENGTH = 256, 20261109, 0.35  # paper showing through a panel
BASE = (246, 241, 233)  # Warm Sand LIGHT["bg"]
_tile_cache = None; _TILED_CACHE = {}  # R24: {(w, h): PIL tiled image}, bounded below


def _wrapped(draw, fn):
    """Call fn(draw, dx, dy) for the tile + its 8 wrapped copies."""
    for dx in (-TILE, 0, TILE):
        for dy in (-TILE, 0, TILE):
            fn(draw, dx, dy)


def generate_texture(size=TILE, seed=SEED):
    """Deterministic tileable paper texture (RGB)."""
    rng = random.Random(seed)
    img = Image.new("RGB", (size, size), BASE)
    px = img.load()
    for y in range(size):
        for x in range(size):
            d = rng.randint(-5, 5)  # luminance grain, hue stays warm
            j = rng.randint(-2, 2)  # tiny per-channel jitter
            r, g, b = BASE
            px[x, y] = (max(0, min(255, r + d + j)),
                        max(0, min(255, g + d)),
                        max(0, min(255, b + d - j)))
    # Soft mottling: blurred blobs on a mid-grey layer (mask = distance
    # from mid-grey, so only blobs tint the paper), drawn wrapped.
    mottle = Image.new("L", (size, size), 128)
    md = ImageDraw.Draw(mottle)
    for _ in range(14):
        cx, cy = rng.randint(0, size - 1), rng.randint(0, size - 1)
        rx, ry = rng.randint(30, 80), rng.randint(20, 60)
        tone = rng.choice([146, 110])
        _wrapped(md, lambda d, dx, dy, cx=cx, cy=cy, rx=rx, ry=ry, tone=tone:
                 d.ellipse([cx - rx + dx, cy - ry + dy, cx + rx + dx, cy + ry + dy], fill=tone))
    mottle = mottle.filter(ImageFilter.GaussianBlur(24))
    mask = mottle.point(lambda v: min(255, abs(v - 128) * 4))
    tint = Image.new("RGB", (size, size), (238, 231, 218))
    img.paste(Image.blend(img, tint, 0.5), (0, 0), mask)
    # Faint fibres: short 1px strokes, mostly near-horizontal, wrapped.
    fib = ImageDraw.Draw(img, "RGBA")
    for _ in range(90):
        x, y = rng.randint(0, size - 1), rng.randint(0, size - 1)
        ang = rng.uniform(-0.5, 0.5)  # near-horizontal, like paper grain
        ln = rng.randint(8, 30)
        ex, ey = int(x + ln * (1 if rng.random() < 0.5 else -1)), int(y + ln * ang)
        col = (232, 226, 212, 70) if rng.random() < 0.5 else (255, 250, 240, 70)
        _wrapped(fib, lambda d, dx, dy, x=x, y=y, ex=ex, ey=ey, col=col:
                 d.line([(x + dx, y + dy), (ex + dx, ey + dy)], fill=col, width=1))
    # Sparse specks (1px, wrapped by modulo) on an RGBA overlay at
    # low alpha, so no single pixel goes hard-dark.
    over = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sp = ImageDraw.Draw(over)
    for _ in range(220):
        x, y = rng.randint(0, size - 1), rng.randint(0, size - 1)
        c = (228, 221, 205, 110) if rng.random() < 0.6 else (252, 248, 240, 110)
        sp.point((x % size, y % size), fill=c)
    img = Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")
    return img


def ensure_texture():
    """Write assets/paper_texture.png if missing; return its path."""
    if not TEXTURE_PATH.exists():
        TEXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        generate_texture().save(TEXTURE_PATH)
    return TEXTURE_PATH


def tile_image():
    """The 256 tile as a PIL image (asset file, else regenerated)."""
    global _tile_cache
    if _tile_cache is None:
        try:
            _tile_cache = Image.open(TEXTURE_PATH).convert("RGB")
        except Exception:
            _tile_cache = generate_texture()
    return _tile_cache


def tiled_image(w, h):
    """Tile pasted to (w, h); exact repeats, so no visible seams.
    R24: cached per (w, h) - the tile is deterministic, so a rebuild
    at the same size reuses the PIL image (bounded: 8 sizes, FIFO)."""
    out = _TILED_CACHE.get((w, h))
    if out is None:
        tile = tile_image()
        out = Image.new("RGB", (max(1, w), max(1, h)))
        for y in range(0, h, TILE):
            for x in range(0, w, TILE):
                out.paste(tile, (x, y))
        if w * h <= 3_000_000: _TILED_CACHE[(w, h)] = out  # skip transient giants
        if len(_TILED_CACHE) > 8: _TILED_CACHE.pop(next(iter(_TILED_CACHE)))
    return out


def texturize(img, strength=STRENGTH):
    """Blend the paper tile into a PIL image (light mode only).
    Transparent corners survive via the image's own alpha channel."""
    if img is None or mode() == "dark":
        return img
    w, h = img.size
    out = Image.blend(img.convert("RGB"), tiled_image(w, h), strength)
    out.putalpha(img.split()[3])
    return out


def attach_paper_bg(window):
    """Tile the paper behind a window's children (light mode only).
    The Canvas is created BEFORE the other children, so it sits at
    the bottom of the stacking order; <Configure> re-tiles it on
    resize. Dark mode: any light canvas is removed. Canvas or None."""
    old = getattr(window, "_paper_canvas", None)
    if old is not None:
        try: old.destroy()
        except Exception: pass
        window._paper_canvas = None
    if mode() == "dark":
        return None
    canvas = tk.Canvas(window, bg=LIGHT["bg"], highlightthickness=0, bd=0)
    canvas.place(x=0, y=0, relwidth=1, relheight=1)
    window._paper_canvas = canvas

    def _retile(_e=None):
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w <= 2 or h <= 2 or getattr(canvas, "_paper_size", None) == (w, h):
            return
        canvas._paper_size = (w, h)
        img = cached_photo(canvas, ("paper", w, h), lambda: tiled_image(w, h))
        canvas.delete("all")
        canvas.create_image(0, 0, anchor="nw", image=img)
        canvas._paper_img = img  # GC guard: Tk drops unreferenced images

    canvas.bind("<Configure>", _retile)
    try:  # Misc.lower drops the WIDGET (Canvas.lower is the item method)
        tk.Misc.lower(canvas)
    except Exception:
        pass
    _retile()
    return canvas

_TREEVIEW_FIELD = "Paper.Treeview.field"  # ttk element name, created once per interpreter


def _treeview_layout(field):
    """Default clam Treeview layout, with `field` as the background."""
    return [(field, {"sticky": "nswe", "children": [("Treeview.padding",
        {"sticky": "nswe", "children": [("Treeview.treearea", {"sticky": "nswe"})]})]})]


def apply_treeview_paper(style, th):
    """Patient-list Treeview: paper field background in light mode.
    Keeps the global "Treeview" configure exactly as shell.py had it
    (other tables inherit it), and adds a named "Paper.Treeview"
    style for the shell patient list: its field element is the 256
    tile, and ttk image elements TILE, so it repeats across any tree
    size with no resize handling. The PhotoImage lives on the style's
    master widget (one per Tk interpreter). Dark mode: plain colours + default clam layout, no beige."""
    from src.ui.amiri import tree_font, tree_rowheight
    for name in ("Treeview", "Paper.Treeview"):
        style.configure(name, rowheight=tree_rowheight(), font=tree_font(),
                        background=th["list_bg"], fieldbackground=th["list_bg"],
                        foreground=th["text"])
    if mode() == "dark":
        style.layout("Paper.Treeview", _treeview_layout("Treeview.field"))
        return
    master = getattr(style, "master", None) or tk._default_root
    img = getattr(master, "_paper_tree_img", None) if master is not None else None
    if img is None:
        img = ImageTk.PhotoImage(tile_image(), master=master)
        if master is not None:
            master._paper_tree_img = img  # GC guard, per interpreter
    if _TREEVIEW_FIELD not in style.element_names():
        style.element_create(_TREEVIEW_FIELD, "image", img,
                             border=0, sticky="nsew")
    style.layout("Paper.Treeview", _treeview_layout(_TREEVIEW_FIELD))
