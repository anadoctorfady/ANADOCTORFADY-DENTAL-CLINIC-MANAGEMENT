"""Narrow scrollable tree (round 16, Users tab).

A rounded_tree with fixed narrow columns, a vertical scrollbar.
R56: the tree has NO wheel binding of its own any more -- the
wheel over it scrolls the containing page (wheel_scroll.
install_page_wheel, the global page-scroll rule); when it lives
in no scroll page, that delegate scrolls the tree itself. <200 lines.
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
    # R56: NO wheel binding of its own any more -- the wheel over
    # this tree scrolls the containing page (wheel_scroll.
    # install_page_wheel, the global page-scroll rule); when the
    # tree lives in no scroll page, that same delegate scrolls
    # the tree itself. The scrollbar still scrolls it directly.
    return tree
