"""Narrow scrollable tree (round 16, Users tab).

A rounded_tree with fixed narrow columns, a vertical scrollbar and
its own mouse-wheel bindings (Linux <Button-4>/<Button-5> + Windows
<MouseWheel>). The tree scrolls itself: the wheel handlers return
"break" so no canvas behind it double-scrolls, and they are bound
with add="+" so they never replace another widget's wheel handler
(round 14 lesson). <200 lines.
"""
import tkinter as tk
from tkinter import ttk

from src.ui.rounded_lists import rounded_tree


def narrow_tree(parent, columns, height, widths, **kw):
    """Build the tree; `widths` are the fixed column widths (no
    stretch), `height` the visible rows. Returns the tree. The
    scrollbar is stored on the tree as _v_scrollbar for the tests."""
    pack = kw.pop("pack", {"side": "left", "fill": "y", "expand": False})
    tree = rounded_tree(parent, columns=columns, height=height, pack=pack, **kw)
    for col, w in zip(columns, widths):
        tree.column(col, width=w, stretch=False)
    sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="left", fill="y")
    tree._v_scrollbar = sb

    def _wheel(event):
        if getattr(event, "num", 0) == 4 or getattr(event, "delta", 0) > 0:
            steps = -1
        else:
            steps = 1
        tree.yview_scroll(steps, "units")
        return "break"

    for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        tree.bind(ev, _wheel, add="+")
    return tree
