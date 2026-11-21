"""Round 27: thumbnail grid for patient files (X-Rays + Scans).

Replaces the round-25 list+preview presentation in both sections
with a wrapping grid of tiles: one tile per stored file, a PIL
thumbnail (or a type glyph for .dcm / 3D / other files) and the
SAVED NAME under it. Single click selects (accent border + bold
name); double click calls on_open (large viewer / detail view --
wired by the host section). No storage path is ever displayed:
tiles carry the bare file name only.

The grid is a plain Frame (no nested canvas): it lives inside the
clinical page's own scroll canvas, so the mouse wheel keeps
scrolling the page (wheel_scroll skips only Text/Listbox/Treeview).
Tile backgrounds alternate the theme's zebra_colors, the same pair
the record trees use. Thumbnails render through the round-24
image_cache (bounded, keyed by path + mtime + size), so rebuilds
and language/theme toggles stay fast.
"""
import tkinter as tk
from pathlib import Path

from PIL import Image

from src.config.strings import t
from src.config.theme import current, is_dark, zebra_colors
from src.models.scans import IMAGE_EXTS, MESH_EXTS
from src.ui.image_cache import cached_photo

THUMB_W, THUMB_H = 128, 92
TILE_W, TILE_H = 148, 156
_GAP = 8


def kind_for(path):
    """Tile kind for a stored file: image / dcm / mesh / other."""
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext == ".dcm":
        return "dcm"
    if ext in MESH_EXTS:
        return "mesh"
    return "other"


def _thumb_pil(path):
    with Image.open(path) as im:
        im = im.convert("RGBA")
        im.thumbnail((THUMB_W, THUMB_H))
        return im.copy()


class ThumbGrid(tk.Frame):
    """Wrapping thumbnail tiles with single/double-click actions.

    Items are dicts: {key, name, sub, path, kind} (+ host extras).
    on_select(item) / on_open(item) fire on click / double-click.
    """

    def __init__(self, parent, on_select=None, on_open=None, lang="en"):
        th = current()
        super().__init__(parent, bg=th["panel"])
        self.lang = lang or "en"
        self.on_select = on_select
        self.on_open = on_open
        self.items = []
        self.tiles = []
        self.tile_names = []
        self.selected = None
        self._sel_key = None
        self._cols = 0
        self._photos = []
        self.empty_label = tk.Label(
            self, text=t("gallery.no_images", self.lang), bg=th["panel"],
            fg=th["muted"], font=("Segoe UI", 10, "italic"))
        self.bind("<Configure>", self._on_configure)

    # -- content ----------------------------------------------------
    def set_items(self, items):
        """Rebuild all tiles from `items` (display order preserved)."""
        for tile in self.tiles:
            tile.destroy()
        self.tiles, self.tile_names = [], []
        self.items = list(items or [])
        self.selected, self._sel_key = None, None
        self._photos = []
        if not self.items:
            self.empty_label.grid(row=0, column=0, padx=10, pady=10,
                                  sticky="w")
            self._cols = 0
            return
        self.empty_label.grid_remove()
        for i, item in enumerate(self.items):
            self._build_tile(i, item)
        self._cols = 0
        self._relayout()

    def clear(self):
        self.set_items([])

    def _glyph(self, item):
        # "DICOM" / "3D" are language-neutral technical acronyms
        # (constants, not UI wording -- cf. the purity allowlist).
        if item["kind"] == "dcm":
            return "DICOM"
        if item["kind"] == "mesh":
            return "3D"
        ext = Path(item["name"]).suffix.upper().lstrip(".")
        return ext or t("gallery.other_file", self.lang)

    def _photo(self, tile, item):
        """Cached thumbnail PhotoImage, or None (glyph fallback)."""
        try:
            st = Path(item["path"]).stat()
            key = ("thumb", THUMB_W, THUMB_H, str(item["path"]),
                   st.st_mtime_ns, st.st_size)
            return cached_photo(tile, key, lambda: _thumb_pil(item["path"]))
        except Exception:
            return None

    def _build_tile(self, idx, item):
        th = current()
        even, odd = zebra_colors(is_dark())
        bg = even if idx % 2 == 0 else odd
        tile = tk.Frame(self, width=TILE_W, height=TILE_H, bg=bg,
                        highlightthickness=2,
                        highlightbackground=th["border"],
                        highlightcolor=th["border"])
        tile.grid_propagate(False)
        wrap = tk.Frame(tile, width=THUMB_W + 8, height=THUMB_H + 4,
                        bg=bg)
        wrap.pack_propagate(False)
        wrap.pack(pady=(6, 0))
        pic = tk.Label(wrap, bg=bg)
        photo = self._photo(tile, item) if item["kind"] == "image" else None
        if photo is not None:
            self._photos.append(photo)
            pic.config(image=photo)
        else:
            pic.config(text=self._glyph(item), fg=th["muted"],
                       font=("Segoe UI", 15, "bold"))
        pic.pack(expand=True)
        name = tk.Label(tile, text=item["name"], bg=bg, fg=th["text"],
                        font=("Segoe UI", 9), wraplength=TILE_W - 12,
                        justify="center", height=2)
        name.pack(fill="x", padx=4)
        sub = tk.Label(tile, text=item.get("sub", ""), bg=bg,
                       fg=th["muted"], font=("Segoe UI", 8), height=1)
        sub.pack(fill="x", padx=4)
        item["_tile"] = tile
        item["_name_lbl"] = name
        for w in (tile, wrap, pic, name, sub):
            w.bind("<Button-1>", lambda _e, it=item: self._select(it))
            w.bind("<Double-Button-1>",
                   lambda _e, it=item: self._open(it))
        self.tiles.append(tile)
        self.tile_names.append(name)

    # -- layout -------------------------------------------------------
    def _relayout(self):
        width = self.winfo_width()
        if width <= 1:
            width = 900
        cols = max(1, (width + _GAP) // (TILE_W + _GAP))
        if cols == self._cols and self.tiles:
            return
        self._cols = cols
        for i, tile in enumerate(self.tiles):
            tile.grid(row=i // cols, column=i % cols, padx=_GAP // 2,
                      pady=_GAP // 2, sticky="nw")

    def _on_configure(self, event):
        if event.widget is self and self.tiles:
            self._relayout()

    # -- actions ------------------------------------------------------
    def _select(self, item):
        th = current()
        prev = next((i for i in self.items
                     if i.get("key") == self._sel_key), None)
        if prev is not None and prev.get("_tile") is not None:
            prev["_tile"].config(highlightbackground=th["border"])
            prev["_name_lbl"].config(fg=th["text"],
                                     font=("Segoe UI", 9))
        self.selected = item
        self._sel_key = item.get("key")
        item["_tile"].config(highlightbackground=th["accent"])
        item["_name_lbl"].config(fg=th["accent"],
                                 font=("Segoe UI", 9, "bold"))
        if self.on_select:
            self.on_select(item)

    def _open(self, item):
        self._select(item)
        if self.on_open:
            self.on_open(item)
