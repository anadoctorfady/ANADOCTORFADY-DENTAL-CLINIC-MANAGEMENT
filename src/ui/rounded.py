"""Rounded buttons for Tkinter (Round 12, Item B).

Tk has NO native rounded corners: PIL-rendered rounded-rectangle
images (solid theme colour or the iOS27 gradient) with transparent
corners carry the button, its label drawn on top (compound="center");
hover / pressed / disabled are shaded copies. Panels / table wrappers
live in rounded_frame.py; the PIL renderers live in rounded_render.py
(re-exported here). PhotoImages come from image_cache.cached_photo
(master=self; a bare PhotoImage may bind a DESTROYED root after an
earlier Tk closed - TclError, 2026-11-09). R51: font objects and
linespaces are cached per toplevel (they die with the interpreter);
variants stay eager (pinned by test_r24_toggle_perf)."""
import tkinter as tk
from tkinter import font as tkfont
from PIL import ImageColor
from src.config.theme import GRADIENT, RADIUS_BTN; _MEASURE_CACHE = {}
from src.ui.image_cache import cached_photo  # R24 item 8: reuse across rebuilds
from src.ui.rounded_render import rounded_pil, gradient_pil  # re-exported


def hex_to_rgb(h):
    return ImageColor.getrgb(h)[:3]  # '#RRGGBB' or a Tk name ('white')


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(c))) for c in rgb)


def shade(c, f):
    return rgb_to_hex(tuple(v * f for v in hex_to_rgb(c)))  # f<1 darkens


def blend(a, b, t):
    ra, rb = hex_to_rgb(a), hex_to_rgb(b)  # t=0 -> a, t=1 -> b
    return rgb_to_hex(tuple(ra[i] + (rb[i] - ra[i]) * t for i in range(3)))


def _font_for(widget, font_spec):
    """(Font, linespace) cached on the widget's TOPLEVEL: a Font dies
    with its Tk interpreter, so its cache lives there too."""
    try: top = widget.winfo_toplevel()
    except Exception: top = widget
    cache = getattr(top, "_r51_font_cache", None)
    if cache is None:
        cache = {}; setattr(top, "_r51_font_cache", cache)
    key = str(font_spec)
    hit = cache.get(key)
    if hit is None:
        f = tkfont.Font(root=widget, font=font_spec)
        hit = (f, f.metrics("linespace")); cache[key] = hit
    return hit


class RoundedButton(tk.Button):
    """A tk.Button with genuinely rounded corners (PIL image). Drop-in for the call sites we use: text / bg / fg / font / command / state."""

    def __init__(self, parent, text="", bg="#A85F33", fg="white",
                 font=("Segoe UI", 10), radius=RADIUS_BTN, padx=12, pady=6,
                 gradient=False, border=None, **kw):
        # R52: adopt the build family noted on the toplevel (R56: always None since the Amiri revert -- amiri.note_build_family) so the button is measured/rendered ONCE, in the family it is built in.
        try: _fam = getattr(parent.winfo_toplevel(), "_ui_family", None)
        except Exception: _fam = None
        if _fam and font and font[0] in ("Segoe UI", "Tahoma"):
            font = (_fam,) + tuple(font[1:])
        self._text, self._bg, self._fg = text, bg, fg
        self._font, self._radius = font, radius
        self._padx, self._pady = padx, pady
        self._gradient, self._border = gradient, border
        self._hover = False
        self._inset = None  # Tk button inset, measured lazily in _on_resize.
        try:  # widget bg = PARENT bg, not the fill: transparent corners show it
            _parent_bg = parent.cget("bg")
        except Exception:
            _parent_bg = "#F6F1E9"
        kw["bg"] = _parent_bg; kw["activebackground"] = _parent_bg
        kw.setdefault("fg", fg); kw.setdefault("font", font)
        kw.setdefault("relief", "flat"); kw.setdefault("bd", 0)
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("activeforeground", fg)
        kw.setdefault("disabledforeground", "#9CA3AF")
        kw["padx"] = 0; kw["pady"] = 0  # MUST be 0: Tk defaults make the widget bigger than its image
        super().__init__(parent, **kw)
        self._measure(); self._render_images(); self._sync()
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.bind("<Configure>", self._on_resize, add="+")

    def _measure(self):
        # R21 item 11 + R51: widths cached module-wide (ints are safe);
        # Font + linespace come from the toplevel cache.
        f, linespace = _font_for(self, self._font)
        key = (str(self._font), self._text)
        wdt = _MEASURE_CACHE.get(key)
        if wdt is None:
            wdt = f.measure(self._text) if self._text else 0
            _MEASURE_CACHE[key] = wdt
        self._size = self._content_size = (wdt + 2 * self._padx, linespace + 2 * self._pady)  # R53: _content_size is the floor _on_resize never goes below

    def _variant_specs(self):
        if self._gradient:
            return {"normal": GRADIENT, "hover": [shade(c, 0.92) for c in GRADIENT],
                    "pressed": [shade(c, 0.82) for c in GRADIENT],
                    "disabled": [blend(c, "#9CA3AF", 0.5) for c in GRADIENT]}
        return {"normal": self._bg, "hover": shade(self._bg, 0.92),
                "pressed": shade(self._bg, 0.82),
                "disabled": blend(self._bg, "#9CA3AF", 0.45)}

    def _make_variant(self, key):
        w, h = self._size; spec = self._variant_specs()[key]
        if self._gradient:
            return cached_photo(self, ("gradient", w, h, self._radius, tuple(spec)),
                                lambda cs=spec: gradient_pil(w, h, self._radius, cs))
        return cached_photo(self, ("rounded", w, h, self._radius, spec, self._border),
                            lambda f=spec: rounded_pil(w, h, self._radius, f, self._border))

    def _image_for(self, key):
        img = self._images.get(key)
        if img is None:
            img = self._make_variant(key); self._images[key] = img
        return img

    def set_ui_family(self, family):
        """R56: swap the font family (kept for callers; the Amiri swap
        was removed with the revert), keeping size/styles; re-render."""
        f = self._font
        if not f or f[0] == family:
            return
        self._font = (family,) + tuple(f[1:])
        self._measure(); self._render_images(); self._sync()

    def _render_images(self):
        # R24 item 8: PhotoImages cached on the toplevel, keyed by
        # EVERY PIL parameter (text/fg are not key parts).
        self._stale_images = getattr(self, "_images", {})  # kept alive until _sync() repoints (GC/TclError)
        self._images = {k: self._make_variant(k) for k in
                        ("normal", "hover", "pressed", "disabled")}

    def _state_key(self):
        return "disabled" if str(self.cget("state")) == "disabled" else "normal"

    def _sync(self):
        # R31: fg/font MUST be re-applied here (the 1.85:1 restyle bug).
        super().configure(text=self._text, image=self._image_for(self._state_key()), compound="center", fg=self._fg, font=self._font, activeforeground=self._fg)
        self._stale_images = {}  # widget now points at the new images

    def _set_image(self, key):
        if self._state_key() == "disabled":
            key = "disabled"
        try: super().configure(image=self._image_for(key))
        except Exception: pass

    def _on_enter(self, _e=None):
        if self._state_key() != "disabled": self._hover = True; self._set_image("hover")

    def _on_leave(self, _e=None):
        self._hover = False; self._set_image("normal")

    def _on_press(self, _e=None):
        if self._state_key() != "disabled": self._set_image("pressed")

    def _on_release(self, _e=None):
        self._set_image("hover" if self._hover else "normal")

    def _on_resize(self, _e=None):
        """Re-render when stretched, at widget size MINUS Tk's inset -- but never below the measured content size (R53: a too-short parent used to shrink the pill under its text, so the text spilled past the image)."""
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1: return
        if self._inset is None:
            self._inset = (self.winfo_reqwidth() - self._images["normal"].width(),
                           self.winfo_reqheight() - self._images["normal"].height())
        iw, ih = max(self._content_size[0], w - self._inset[0]), max(self._content_size[1], h - self._inset[1])
        if (iw, ih) == self._size: return
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
