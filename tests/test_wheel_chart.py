"""Round 14 wheel audit: dental chart (horizontal wheel) and the
clinical page's inner history trees (wheel must scroll the tree, not
the page). Companion to tests/test_wheel_audit.py.
"""
import tkinter as tk
from tkinter import ttk

from src.ui.clinical import ClinicalTab
from src.ui.dental_chart import DentalChartFrame


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



def test_dental_chart_wheel_horizontal():
    """Narrow chart: the wheel scrolls it horizontally (it has no
    vertical content, so a vertical wheel must not be a no-op)."""
    root = _root(800, 400)
    if root is None:
        print("SKIP test_dental_chart_wheel_horizontal (no display)")
        return
    try:
        ch = DentalChartFrame(root, lang="en", on_select=lambda a, b: None)
        ch.pack(fill="x")
        root.update()
        assert ch._canvas.xview()[1] < 1.0, "chart not scrollable in test setup"
        before = ch._canvas.xview()
        cell = next(iter(ch.tooth_cells.values()))
        cell.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert ch._canvas.xview()[0] > before[0], "wheel did not scroll chart right"
        cell.event_generate("<Button-5>")
        root.update()
        assert ch._canvas.xview()[0] > before[0], "Button-5 did not scroll chart"
        cell.event_generate("<MouseWheel>", delta=120)
        root.update()
        assert ch._canvas.xview()[0] < before[0] + 0.2, "wheel up did not scroll chart back"
    finally:
        root.destroy()


def test_clinical_inner_tree_scrolls_itself():
    """Wheel over a history Treeview inside the clinical page scrolls
    the tree, not the page canvas."""
    root = _root()
    if root is None:
        print("SKIP test_clinical_inner_tree_scrolls_itself (no display)")
        return
    try:
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
        c0 = canvas.yview()
        _down_up(root, tr, tr.yview)
        assert canvas.yview() == c0, "wheel over inner tree moved the page"
    finally:
        root.destroy()
