"""Rounded text/list/table widgets (Round 13, Item 2) - companion
to rounded_widgets.py (which holds the border base + RoundedEntry).

RoundedListbox / RoundedCombobox are the same Canvas+PIL rounded
border with the real widget inset; rounded_tree() wraps a ttk
Treeview in a RoundedFrame (the tree itself cannot be rounded).
SearchableCombobox is NOT wrapped here: it keeps its own filtering
attributes, so call sites wrap it in a RoundedFrame instead.
"""
import tkinter as tk
from tkinter import ttk
from src.config.theme import RADIUS_FIELD, RADIUS_TABLE, RADIUS_TEXT, current
from src.ui.rounded_widgets import _RoundedBorder
from src.ui.rounded_frame import RoundedFrame


class RoundedText(_RoundedBorder):
    """tk.Text with a rounded border. Drop-in for tk.Text."""

    def __init__(self, parent, font=None, width=None, height=None, wrap=None,
                 bg=None, fg=None, state=None, radius=RADIUS_TEXT, **kw):
        th = current()
        super().__init__(parent, field_bg=bg or th["panel"], radius=radius, **kw)
        tx = tk.Text(self, relief="flat", bd=0, highlightthickness=0,
                     bg=self._field_bg, fg=fg or th["text"])
        for k, v in (("font", font), ("width", width), ("height", height),
                     ("wrap", wrap), ("state", state)):
            if v is not None:
                tx.configure(**{k: v})
        self.text = self.widget = self._attach(tx)

class RoundedListbox(_RoundedBorder):
    """tk.Listbox with a rounded border. Drop-in for tk.Listbox."""

    def __init__(self, parent, font=None, width=None, height=None, bg=None,
                 fg=None, selectbackground=None, selectforeground=None,
                 radius=RADIUS_TEXT, **kw):
        th = current()
        super().__init__(parent, field_bg=bg or th["panel"], radius=radius, **kw)
        lb = tk.Listbox(self, relief="flat", bd=0, highlightthickness=0,
                        bg=self._field_bg, fg=fg or th["text"])
        for k, v in (("font", font), ("width", width), ("height", height),
                     ("selectbackground", selectbackground),
                     ("selectforeground", selectforeground)):
            if v is not None:
                lb.configure(**{k: v})
        self.listbox = self.widget = self._attach(lb)


class RoundedCombobox(_RoundedBorder):
    """ttk.Combobox with a rounded border. Drop-in for ttk.Combobox
    (NOT for SearchableCombobox - that subclass keeps its own
    attributes; wrap it in a RoundedFrame instead, see patient_form)."""

    def __init__(self, parent, textvariable=None, values=None, width=None,
                 state=None, font=None, bg=None, radius=RADIUS_FIELD, **kw):
        th = current()
        super().__init__(parent, field_bg=bg or th["panel"], radius=radius, **kw)
        cb = ttk.Combobox(self)
        for k, v in (("textvariable", textvariable), ("values", values),
                     ("width", width), ("state", state), ("font", font)):
            if v is not None:
                cb.configure(**{k: v})
        self.combo = self.widget = self._attach(cb)


def rounded_tree(parent, columns=None, show="headings", style=None, bg=None,
                 border=None, radius=RADIUS_TABLE, pack=None, **kw):
    """A ttk.Treeview inside a RoundedFrame (the tree itself cannot be
    rounded). Returns the tree; the wrapper is on tree._rounded_wrapper.
    `pack` is the wrapper's pack kwargs (default: fill both, expand)."""
    th = current()
    wrap = RoundedFrame(parent, bg=bg or th["panel"],
                        border=border or th["border"], radius=radius, pad=4)
    wrap.pack(**(pack or {"fill": "both", "expand": True, "padx": 6, "pady": 4}))
    tree = ttk.Treeview(wrap.inner, columns=columns, show=show,
                        style=style, **kw)
    tree.pack(fill="both", expand=True)
    tree._rounded_wrapper = wrap
    return tree


def is_rounded(widget):
    """True when a widget (or any ancestor up to 2 levels) is one of
    the rounded wrappers / a RoundedButton / inside a RoundedFrame."""
    from src.ui.rounded import RoundedButton
    w = widget
    for _ in range(3):
        if w is None:
            return False
        if isinstance(w, (_RoundedBorder, RoundedFrame, RoundedButton)):
            return True
        try:
            w = w.master
        except Exception:
            return False
    return False
