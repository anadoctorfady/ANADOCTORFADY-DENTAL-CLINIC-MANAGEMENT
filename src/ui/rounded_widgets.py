"""Rounded input fields (Round 13, Item 2).

Tkinter has NO native rounded Entry / Text: both are square. The
achievable treatment (same trick round 12 used for buttons/panels)
is a PIL rounded-rectangle border on a Canvas behind the real
widget, inset a few px so its square corners sit INSIDE the curve.
The visible outer edge is genuinely rounded; the inner widget keeps
its exact behaviour. Classes are tk.Frame subclasses; the inner
widget is `.widget` (`.entry` alias). get/insert/delete/bind/
focus_set/config/cget and `widget["option"]` delegate to it, so a
mechanical `tk.Entry(` -> `RoundedEntry(` swap keeps call sites
working. Focus turns the border the theme accent. PhotoImages use
master=self (destroyed-root guard, as in rounded.py). Text /
Listbox / Combobox / Treeview wrappers live in rounded_lists.py.
Not roundable: ttk Notebook tabs, Scrollbars, Check/Radiobutton
boxes, the linking guide's ScrolledText, the scans tree (a test
pins it as a direct child). The OS window frame cannot be rounded
by Tk on Win7/10 (Win11 rounds natively); never overrideredirect.
"""
import tkinter as tk
from src.config.theme import RADIUS_FIELD, RADIUS_TEXT, current, field_border, is_dark
from src.ui.image_cache import cached_photo  # R24 item 8: reuse across rebuilds
from src.ui.rounded import rounded_pil

_INNER_KEYS = ("bg", "fg", "font", "state", "textvariable", "show",
               "justify", "width", "height", "values", "wrap", "relief",
               "bd", "selectbackground", "selectforeground",
               "yscrollcommand", "xscrollcommand", "insertbackground",
               "disabledbackground", "disabledforeground", "cursor",
               "takefocus", "selectmode", "activestyle", "exportselection")


class _RoundedBorder(tk.Frame):
    """Frame + Canvas PIL rounded border; subclasses pack the real
    widget into it with a small inset. `field_bg` is the widget bg."""

    def __init__(self, parent, field_bg=None, border=None, radius=RADIUS_FIELD,
                 pad=3, **kw):
        # relief/bd belong to the (now flat) inner widget, never to the
        # wrapper frame: a square frame border would defeat the rounding.
        for _k in ("relief", "bd", "borderwidth", "highlightthickness",
                   "highlightbackground", "highlightcolor"):
            kw.pop(_k, None)
        try:
            outer_bg = parent.cget("bg")
        except Exception:
            outer_bg = current()["bg"]
        super().__init__(parent, bg=outer_bg, **kw)
        th = current()
        self._field_bg = field_bg or th["panel"]
        # R21 item 9: default border = the FIELD_BORDER token (strong,
        # mode-aware) -- the old theme border was ~invisible on panels.
        self._border = border or field_border(is_dark())
        self._focus_border = th["accent"]
        self._radius, self._pad = radius, pad
        self._inner = None  # inner widget, set by the subclass
        self._img = None
        self._size = (0, 0)
        self._canvas = tk.Canvas(self, bg=outer_bg, highlightthickness=0, bd=0)
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bind("<Configure>", self._redraw, add="+")

    def _draw(self, border=None):
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 2 or h <= 2 or (w, h, border) == self._size:
            return
        self._size = (w, h, border)
        _old = self._img  # keep alive until the canvas drops its item
        # R24 item 8: cached on the toplevel, keyed by every render
        # parameter (size, radius, field bg, effective border, width).
        _eff, _bw = border or self._border, 3 if border else 2
        self._img = cached_photo(
            self, ("field", w, h, self._radius, self._field_bg, _eff, _bw),
            lambda: rounded_pil(w, h, self._radius, self._field_bg, _eff, _bw))
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor="nw", image=self._img)
        del _old

    def _redraw(self, _e=None):
        self._draw(self._focus_border if self._focused() else None)

    def _focused(self):
        try:
            return self._inner is not None and self.focus_get() == self._inner
        except Exception:
            return False

    def _attach(self, widget):
        """Pack the inner widget over the border canvas and wire focus."""
        self._inner = widget
        widget.pack(fill="both", expand=True, padx=self._pad, pady=self._pad)
        widget.bind("<FocusIn>", lambda _e: self._draw(self._focus_border), add="+")
        widget.bind("<FocusOut>", lambda _e: self._draw(None), add="+")
        return widget

    # --- delegation to the inner widget -------------------------------
    # Methods tkinter's Misc/Grid define on EVERY widget (size,
    # selection_clear, bbox, ...) would shadow the inner widget's own
    # methods of the same name, because __getattr__ only fires for
    # MISSING attributes (found 2026-11-09: Listbox.size() returned
    # the Frame's (0, 0), selection_clear() raised Misc's TypeError).
    # Delegate them explicitly.
    for _name in ("size", "bbox", "selection_clear", "selection_set",
                  "selection_anchor", "selection_includes",
                  "selection_range", "selection_present", "selection_to",
                  "selection_from", "selection_adjust"):
        def _mk(_n=_name):
            def _m(self, *a, **k):
                return getattr(self._inner, _n)(*a, **k)
            return _m
        locals()[_name] = _mk()
    del _name, _mk

    def __getattr__(self, name):
        w = object.__getattribute__(self, "_inner") if "_inner" in self.__dict__ else None
        if w is not None:
            return getattr(w, name)
        raise AttributeError(name)

    def bind(self, sequence=None, func=None, add=None):
        if self._inner is not None:
            return self._inner.bind(sequence, func, add)
        return super().bind(sequence, func, add)

    def focus_set(self):
        if self._inner is not None:
            return self._inner.focus_set()
        return super().focus_set()

    def configure(self, cnf=None, **kw):
        merged = dict(cnf) if isinstance(cnf, dict) else {}
        merged.update(kw)
        if self._inner is None or not merged:
            return super().configure(merged) if merged else super().configure()
        if "bg" in merged:  # field bg: inner widget + border fill
            self._field_bg = merged.pop("bg")
            try:
                self._inner.configure(bg=self._field_bg)
            except Exception:
                pass
            self._size = (0, 0)
            self._draw(self._focus_border if self._focused() else None)
        inner, rest = {}, {}
        for k, v in merged.items():
            (inner if k in _INNER_KEYS else rest)[k] = v
        if inner:
            try:
                self._inner.configure(inner)
            except Exception:
                rest.update(inner)  # unknown to inner: try the frame
        if rest:
            super().configure(rest)
        return None

    config = configure

    def cget(self, key):
        if self._inner is not None and key in _INNER_KEYS:
            try:
                return self._inner.cget(key)
            except Exception:
                pass
        return super().cget(key)

    # NB: tkinter aliases __getitem__ = cget at CLASS definition time,
    # so the inherited __getitem__ would bypass the cget() override
    # above and read the FRAME's options (e.g. width 0) instead of
    # the inner widget's. Rebind both explicitly.
    def __getitem__(self, key):
        return self.cget(key)

    def __setitem__(self, key, value):
        self.configure({key: value})


class RoundedEntry(_RoundedBorder):
    """tk.Entry with a rounded border. Drop-in for tk.Entry."""

    def __init__(self, parent, font=None, width=None, textvariable=None,
                 show=None, justify=None, bg=None, fg=None, state=None,
                 radius=RADIUS_FIELD, **kw):
        th = current()
        super().__init__(parent, field_bg=bg or th["panel"], radius=radius, **kw)
        e = tk.Entry(self, relief="flat", bd=0, highlightthickness=0,
                     bg=self._field_bg, fg=fg or th["text"])
        if font is not None:
            e.configure(font=font)
        if width is not None:
            e.configure(width=width)
        if textvariable is not None:
            e.configure(textvariable=textvariable)
        if show is not None:
            e.configure(show=show)
        if justify is not None:
            e.configure(justify=justify)
        if state is not None:
            e.configure(state=state)
        self.entry = self.widget = self._attach(e)
