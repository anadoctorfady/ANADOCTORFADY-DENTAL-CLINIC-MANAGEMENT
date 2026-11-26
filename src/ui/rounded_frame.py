"""RoundedFrame: a Frame with rounded corners (Round 12, Item B).

A normal Frame with a Canvas behind it that draws a PIL rounded
rectangle (see rounded.py); the content lives in .inner, inset by
`pad` so its square corners sit inside the curve. The outer frame
takes the parent's background (or `outer_bg`) so the transparent
corners blend in. Use it as the rounded container around a ttk
Treeview (which itself cannot be rounded) and around cards/panels.
The canvas image is created with master=self: a bare PhotoImage binds
to tkinter._default_root, which may be a destroyed interpreter after
an earlier Tk closed (TclError, gate 2026-11-09)."""
import tkinter as tk
from src.config.theme import RADIUS_CARD, mode
from src.ui.image_cache import cached_photo  # R24 item 8: reuse across rebuilds
from src.ui.rounded import rounded_pil
from src.ui.paper_bg import texturize  # paper texture on panels, light mode only


class RoundedFrame(tk.Frame):
    """A Frame with rounded corners. Children go in .inner.

    `title` (optional) paints a bold heading at the top of the frame
    itself - NOT inside .inner: section titles used to be a Label
    packed into .inner, which broke every section whose children use
    grid() (Tk forbids pack + grid in one container)."""

    def __init__(self, parent, bg, border=None, radius=RADIUS_CARD,
                 pad=6, title=None, title_fg=None, **kw):
        # R43: the square-cornered .inner must stay INSIDE the curve:
        # its corner sits at (pad, pad), the corner circle centre at
        # (radius, radius) -- inside iff pad >= radius*(1 - 1/sqrt2).
        # At radius 24 (tables) the old pad 6 would let the tree's
        # square corners poke past the curve; the floor below keeps
        # every radius safe (radius 16 still yields the classic 6).
        import math
        pad = max(pad, math.ceil(radius * 0.2929) + 1)
        outer = kw.pop("outer_bg", None)
        if outer is None:
            try:
                outer = parent.cget("bg")
            except Exception:
                outer = "#F6F1E9"
        super().__init__(parent, bg=outer, **kw)
        self._bg, self._border, self._radius = bg, border, radius
        self._canvas = tk.Canvas(self, bg=outer, highlightthickness=0, bd=0)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        if title is not None:
            tk.Label(self, text=title, bg=bg, fg=title_fg or "#7A3F16",
                     font=("Segoe UI", 9, "bold")).pack(
                         anchor="w", padx=pad + 4, pady=(pad, 0))
        self.inner = tk.Frame(self, bg=bg)
        self.inner.pack(fill="both", expand=True, padx=pad, pady=pad)
        self._img = None; self._size = (0, 0)
        self._redraw_pending = False
        self.bind("<Configure>", self._redraw, add="+")

    def _redraw(self, _e=None):
        # R51: <Configure> fires repeatedly during layout with
        # TRANSIENT sizes; rendering every one (a supersampled PIL
        # render + PhotoImage per size) dominated startup/toggles.
        # Coalesce to one trailing redraw at the final size.
        if self._redraw_pending:
            return
        self._redraw_pending = True
        self.after_idle(self._redraw_now)

    def _redraw_now(self):
        self._redraw_pending = False
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 2 or h <= 2 or (w, h) == self._size:
            return
        self._size = (w, h)
        _old = self._img  # keep alive until the canvas drops its item
        # R24 item 8: cached on the toplevel, keyed by every render
        # parameter - size, radius, bg, border AND theme mode (mode
        # decides whether texturize() blends the paper tile in).
        self._img = cached_photo(
            self, ("frame", w, h, self._radius, self._bg, self._border, mode()),
            lambda: texturize(rounded_pil(w, h, self._radius, self._bg, self._border)))
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor="nw", image=self._img)
        del _old
