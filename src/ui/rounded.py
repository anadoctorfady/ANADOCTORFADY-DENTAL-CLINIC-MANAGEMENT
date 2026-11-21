"""Rounded buttons for Tkinter (Round 12, Item B).

Tkinter has NO native rounded corners: tk.Button is square. What IS
achievable: PIL-rendered rounded-rectangle images (solid theme colour,
or the iOS27 gradient) with transparent corners, used as the button
image with the label drawn on top (compound="center"). Hover / pressed
/ disabled variants are shaded copies; the image re-renders when the
button is stretched (pack fill="x"). Panels / table wrappers live in
rounded_frame.py; ttk Treeview itself cannot be rounded. PhotoImages are
created via image_cache.cached_photo (master=self; a bare PhotoImage
binds to tkinter._default_root, which may be a DESTROYED root after
an earlier Tk closed - TclError, gate 2026-11-09)."""
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageColor, ImageDraw
from src.config.theme import GRADIENT, RADIUS_BTN; _MEASURE_CACHE = {}
from src.ui.image_cache import cached_photo  # R24 item 8: reuse across rebuilds


def hex_to_rgb(h):
    return ImageColor.getrgb(h)[:3]  # '#RRGGBB' or a Tk name ('white')


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(c))) for c in rgb)


def shade(c, f):
    return rgb_to_hex(tuple(v * f for v in hex_to_rgb(c)))  # f<1 darkens


def blend(a, b, t):
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)  # t=0 -> a, t=1 -> b
    return rgb_to_hex(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))


def rounded_pil(w, h, radius, fill, border=None, border_width=1):
    # RGBA image: rounded rectangle `fill`, transparent corners.
    w, h = max(int(w), 1), max(int(h), 1)
    r = max(0, min(int(radius), w // 2, h // 2))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, w - 1, h - 1], radius=r,
        fill=fill, outline=border, width=border_width if border else 1)
    return img


def gradient_pil(w, h, radius, colors=GRADIENT):
    # RGBA image: horizontal gradient across `colors`, rounded mask.
    w, h = max(int(w), 1), max(int(h), 1)
    stops = [hex_to_rgb(c) for c in colors]
    n = len(stops)
    row = Image.new("RGB", (w, 1))
    px = row.load()
    for x in range(w):
        pos = (x / max(w - 1, 1)) * (n - 1)
        i = min(int(pos), n - 2); f = pos - i
        px[x, 0] = tuple(round(stops[i][k] + (stops[i + 1][k] - stops[i][k]) * f)
                         for k in range(3))
    base = row.resize((w, h)).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    r = max(0, min(int(radius), w // 2, h // 2))
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
    base.putalpha(mask)
    return base


class RoundedButton(tk.Button):
    """A tk.Button with genuinely rounded corners (PIL image). Drop-in
    for the call sites we use: text / bg / fg / font / command / state
    all work; hover / pressed / disabled swap to shaded copies."""

    def __init__(self, parent, text="", bg="#A85F33", fg="white",
                 font=("Segoe UI", 10), radius=RADIUS_BTN, padx=12, pady=6,
                 gradient=False, border=None, **kw):
        self._text, self._bg, self._fg = text, bg, fg
        self._font, self._radius = font, radius
        self._padx, self._pady = padx, pady
        self._gradient, self._border = gradient, border
        self._hover = False
        self._inset = None  # Tk button inset, measured lazily in _on_resize.
        # Widget bg = PARENT bg, not the fill: transparent corners show it.
        try:
            _parent_bg = parent.cget("bg")
        except Exception:
            _parent_bg = "#F6F1E9"
        kw["bg"] = _parent_bg; kw["activebackground"] = _parent_bg
        kw.setdefault("fg", fg); kw.setdefault("font", font)
        kw.setdefault("relief", "flat"); kw.setdefault("bd", 0)
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("activeforeground", fg)
        kw.setdefault("disabledforeground", "#9CA3AF")
        # Widget padx/pady MUST be 0: Tk defaults make the widget bigger than its image.
        kw["padx"] = 0; kw["pady"] = 0
        super().__init__(parent, **kw)
        self._measure(); self._render_images(); self._sync()
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.bind("<Configure>", self._on_resize, add="+")

    def _measure(self):
        # R21 item 11: (font, text) measurements cached module-wide.
        key = (str(self._font), self._text)
        hit = _MEASURE_CACHE.get(key)
        if hit is None:
            f = tkfont.Font(root=self, font=self._font)  # root=self: a bare Font() may bind a dead root
            hit = (f.measure(self._text) if self._text else 0, f.metrics("linespace"))
            _MEASURE_CACHE[key] = hit
        self._size = (hit[0] + 2 * self._padx, hit[1] + 2 * self._pady)

    def _render_images(self):
        # R24 item 8: PhotoImages cached on the toplevel, keyed by
        # EVERY PIL parameter; text/fg are NOT key parts (Tk draws
        # the label over the image; text affects only (w, h)).
        self._stale_images = getattr(self, "_images", {})  # keep the old
        # set alive until _sync() repoints the widget (GC/TclError).
        w, h = self._size
        if self._gradient:
            variants = {"normal": GRADIENT, "hover": [shade(c, 0.92) for c in GRADIENT],
                        "pressed": [shade(c, 0.82) for c in GRADIENT],
                        "disabled": [blend(c, "#9CA3AF", 0.5) for c in GRADIENT]}
            self._images = {k: cached_photo(self, ("gradient", w, h, self._radius, tuple(cs)),
                                            lambda cs=cs: gradient_pil(w, h, self._radius, cs))
                            for k, cs in variants.items()}
        else:
            fills = {"normal": self._bg, "hover": shade(self._bg, 0.92),
                     "pressed": shade(self._bg, 0.82), "disabled": blend(self._bg, "#9CA3AF", 0.45)}
            self._images = {k: cached_photo(self, ("rounded", w, h, self._radius, f, self._border),
                                            lambda f=f: rounded_pil(w, h, self._radius, f, self._border))
                            for k, f in fills.items()}

    def _state_key(self):
        return "disabled" if str(self.cget("state")) == "disabled" else "normal"

    def _sync(self):
        # R31: fg/font MUST be re-applied here -- configure() pops
        # them into _fg/_font without forwarding, so the label kept
        # its CONSTRUCTION colours after any restyle (1.85:1 bug).
        super().configure(text=self._text, image=self._images[self._state_key()], compound="center", fg=self._fg, font=self._font, activeforeground=self._fg)
        self._stale_images = {}  # widget now points at the new images

    def _set_image(self, key):
        if self._state_key() == "disabled":
            key = "disabled"
        try: super().configure(image=self._images[key])
        except Exception: pass

    def _on_enter(self, _e=None):
        if self._state_key() != "disabled":
            self._hover = True; self._set_image("hover")

    def _on_leave(self, _e=None):
        self._hover = False; self._set_image("normal")

    def _on_press(self, _e=None):
        if self._state_key() != "disabled":
            self._set_image("pressed")

    def _on_release(self, _e=None):
        self._set_image("hover" if self._hover else "normal")

    def _on_resize(self, _e=None):
        """Re-render when stretched (pack fill="x") at widget size
        MINUS Tk's button inset, else it grows 2px per re-render."""
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1:
            return
        if self._inset is None:
            self._inset = (self.winfo_reqwidth() - self._images["normal"].width(),
                           self.winfo_reqheight() - self._images["normal"].height())
        iw, ih = max(1, w - self._inset[0]), max(1, h - self._inset[1])
        if (iw, ih) == self._size:
            return
        self._size = (iw, ih); self._render_images(); self._sync()

    def configure(self, cnf=None, **kw):
        merged = dict(cnf) if isinstance(cnf, dict) else {}
        merged.update(kw)
        if not hasattr(self, "_images"):
            return super().configure(merged)
        dirty = False
        for key, attr in (("text", "_text"), ("bg", "_bg"), ("fg", "_fg"),
                          ("font", "_font"), ("padx", "_padx"), ("pady", "_pady")):
            if key in merged:
                setattr(self, attr, merged.pop(key)); dirty = True
        if dirty:
            self._measure(); self._render_images()
        if not merged and not dirty:
            return super().configure()
        if merged:
            super().configure(merged)
        self._sync()

    config = configure  # .config() must not bypass the override above


def rounded_button(parent, text="", **kw):
    """Factory: RoundedButton(parent, text=..., bg=..., fg=...)."""
    return RoundedButton(parent, text=text, **kw)
