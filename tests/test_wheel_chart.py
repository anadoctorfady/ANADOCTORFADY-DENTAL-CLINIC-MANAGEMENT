"""Round 14 wheel audit: dental chart and the clinical page's inner
history trees. R56 SUPERSESSION: the wheel over the chart used to
scroll the jaw horizontally, and the wheel over a history tree used
to scroll the tree itself -- both now scroll the PAGE up/down (the
global page-scroll rule); the chart's horizontal view and the tree
must NOT move. Companion to tests/test_wheel_audit.py.
"""
import tkinter as tk
from tkinter import ttk

from src.ui.clinical import ClinicalTab
from src.ui.dental_chart import DentalChartFrame
from src.ui.wheel_scroll import bind_canvas_wheel, install_page_wheel


class _Stub:
    lang = "en"
    current_patient = None
    current_user = "fady"
    current_role = "admin"
    finance_gate = None

    def chart_teeth(self):
        return []

    def refresh_clinical(self):
        pass

    def on_teeth_select(self, teeth, typ):
        pass

    def print_pdf(self):
        pass


def _root(w=1380, h=900):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.deiconify()
    root.geometry(f"{w}x{h}")
    root.update()
    return root


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def _canvas_of(tab, widget):
    w = widget
    while w is not None:
        if isinstance(w, tk.Canvas) and w.cget("yscrollcommand"):
            return w
        w = w.master
    return None



def _down_up(root, widget, view):
    """Wheel down must move the view, wheel up must move it back."""
    before = view()
    widget.event_generate("<MouseWheel>", delta=-120)
    root.update()
    assert view()[0] > before[0], f"MouseWheel down did not scroll {widget}"
    widget.event_generate("<Button-5>")
    root.update()
    assert view()[0] > before[0], "Button-5 did not scroll down"
    mid = view()
    widget.event_generate("<MouseWheel>", delta=120)
    root.update()
    assert view()[0] < mid[0], "MouseWheel up did not scroll back"
    widget.event_generate("<Button-4>")
    root.update()
    assert view()[0] < mid[0], "Button-4 did not scroll back"



def test_dental_chart_wheel_scrolls_page():
    """R56: the wheel over the chart scrolls the PAGE up/down (it
    used to scroll the jaw horizontally); the chart's horizontal
    view does not move. The chart rides inside a scroll page, as
    it does in the real clinical tab."""
    root = _root(800, 400)
    if root is None:
        print("SKIP test_dental_chart_wheel_scrolls_page (no display)")
        return
    try:
        install_page_wheel(root)
        f = tk.Frame(root)
        f.pack(fill="both", expand=True)
        c = tk.Canvas(f, bg="white", highlightthickness=0)
        sb = tk.Scrollbar(f, orient="vertical", command=c.yview)
        c.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        c.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(c)
        c.create_window((0, 0), window=inner, anchor="nw")
        ch = DentalChartFrame(inner, lang="en",
                              on_select=lambda a, b: None)
        ch.pack(fill="x")
        for i in range(40):
            tk.Label(inner, text=f"below {i}").pack()
        inner.bind("<Configure>",
                   lambda e: c.configure(scrollregion=c.bbox("all")))
        root.update()
        bind_canvas_wheel(c)
        assert c.yview()[1] < 1.0, "page not scrollable in test setup"
        cell = next(iter(ch.tooth_cells.values()))
        x0 = ch._canvas.xview()
        _down_up(root, cell, c.yview)
        assert ch._canvas.xview() == x0, \
            "wheel over chart moved the jaw horizontally"
    finally:
        root.destroy()


def test_clinical_inner_tree_scrolls_page():
    """R56 SUPERSESSION: wheel over a history Treeview inside the
    clinical page scrolls the PAGE, not the tree (the round-14 rule
    -- the tree scrolls itself -- is replaced by the global
    page-scroll rule)."""
    root = _root()
    if root is None:
        print("SKIP test_clinical_inner_tree_scrolls_page (no display)")
        return
    try:
        install_page_wheel(root)
        tab = ClinicalTab(root, _Stub())
        tab.pack(fill="both", expand=True)
        root.update()
        # Round 19: page canvas anchored by a history tree (the
        # input tables now live in a fixed, canvas-less block).
        # R24: the history tree is the unified session tree.
        canvas = _canvas_of(tab, tab.tree_history)
        trees = [w for w in _walk(tab) if isinstance(w, ttk.Treeview)]
        assert trees and canvas is not None
        tr = trees[0]
        for i in range(40):
            tr.insert("", "end", values=(f"a{i}", f"b{i}", f"c{i}"))
        root.update()
        assert tr.yview()[1] < 1.0
        assert canvas.yview()[1] < 1.0, "clinical page not scrollable"
        t0 = tr.yview()
        _down_up(root, tr, canvas.yview)
        assert tr.yview() == t0, "wheel over inner tree moved the tree"
    finally:
        root.destroy()
