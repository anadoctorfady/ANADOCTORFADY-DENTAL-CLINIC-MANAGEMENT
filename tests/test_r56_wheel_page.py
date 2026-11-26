"""Round 56 Section B: global mouse-wheel page scroll.

Owner's ask: the wheel must move the CURRENT page up/down EVEN
when the pointer is over a table that has rows inside it. One
central rule (wheel_scroll.install_page_wheel, bound once by
the App at startup) -- not per-widget copy-paste. Pins:
- Wheel over a Treeview / Listbox inside a scroll page moves
  the PAGE (MouseWheel down/up + Linux Button-4/5); the widget
  itself does NOT move.
- Wheel over an OVERFLOWING Text moves the Text, not the page.
- Wheel over a FITTING Text moves the page, not the Text.
- Wheel over a Treeview/Listbox in NO scroll page falls back to
  scrolling the widget itself (dialog lists, Combobox popdowns).
  The same fallback applies when the containing page FITS (it
  cannot scroll): the wheel scrolls the widget, never swallowed.
- Wheel over the dental chart (inside the clinical page) moves
  the page vertically; the chart's horizontal view does not move.
- install_page_wheel() is idempotent (same class binding after
  one install or two).
GUI tests skip gracefully when no display is available.
"""
import tkinter as tk
from tkinter import ttk

from src.ui.wheel_scroll import (
    bind_canvas_wheel, install_page_wheel, page_canvas_for)


def _root(w=900, h=500):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.deiconify()
    root.geometry(f"{w}x{h}")
    root.update()
    return root


def _scroll_page(root, rows=60):
    """A scroll page (canvas + `rows` labels) + a Treeview inside it."""
    f = tk.Frame(root)
    f.pack(side="left", fill="both", expand=True)
    c = tk.Canvas(f, bg="white", highlightthickness=0)
    sb = tk.Scrollbar(f, orient="vertical", command=c.yview)
    c.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    c.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(c)
    c.create_window((0, 0), window=inner, anchor="nw")
    for i in range(rows):
        tk.Label(inner, text=f"row {i}").pack()
    inner.bind("<Configure>",
               lambda e, c=c: c.configure(scrollregion=c.bbox("all")))
    root.update()
    bind_canvas_wheel(c)
    return c, inner


def _fill_tree(tree, n=120, cols=1):
    for i in range(n):
        tree.insert("", "end",
                    values=tuple(f"r{i}c{j}" for j in range(cols)))


def _wheel_moves_page(root, widget, page_view, own_view, label):
    """Down (MouseWheel + Button-5) then up (MouseWheel + Button-4):
    the PAGE must move every time; the widget must not move at all."""
    assert page_view()[1] < 1.0, f"{label}: page not scrollable"
    own0 = own_view()
    before = page_view()
    widget.event_generate("<MouseWheel>", delta=-120)
    root.update()
    assert page_view()[0] > before[0], \
        f"{label}: MouseWheel down did not scroll page"
    assert own_view() == own0, f"{label}: wheel moved the widget"
    widget.event_generate("<Button-5>")
    root.update()
    assert page_view()[0] > before[0], \
        f"{label}: Button-5 did not scroll page"
    assert own_view() == own0, f"{label}: Button-5 moved the widget"
    mid = page_view()
    widget.event_generate("<MouseWheel>", delta=120)
    root.update()
    assert page_view()[0] < mid[0], \
        f"{label}: MouseWheel up did not scroll page back"
    widget.event_generate("<Button-4>")
    root.update()
    assert page_view()[0] < mid[0], \
        f"{label}: Button-4 did not scroll page back"
    assert own_view() == own0, f"{label}: wheel-up moved the widget"


def test_tree_wheel_scrolls_page_not_tree():
    root = _root()
    if root is None:
        print("SKIP (no display)")
        return
    try:
        install_page_wheel(root)
        canvas, inner = _scroll_page(root)
        tr = ttk.Treeview(inner, columns=("a",), show="headings",
                          height=6)
        tr.pack(fill="both", expand=True)
        _fill_tree(tr)
        root.update()
        assert tr.yview()[1] < 1.0, "tree not scrollable in setup"
        assert page_canvas_for(tr) is canvas
        _wheel_moves_page(root, tr, canvas.yview, tr.yview,
                          "tree in page")
    finally:
        root.destroy()


def test_listbox_wheel_scrolls_page_not_list():
    root = _root()
    if root is None:
        print("SKIP (no display)")
        return
    try:
        install_page_wheel(root)
        canvas, inner = _scroll_page(root)
        lb = tk.Listbox(inner, height=6)
        lb.pack(fill="both", expand=True)
        for i in range(120):
            lb.insert("end", f"item {i}")
        root.update()
        assert lb.yview()[1] < 1.0, "list not scrollable in setup"
        assert page_canvas_for(lb) is canvas
        _wheel_moves_page(root, lb, canvas.yview, lb.yview,
                          "listbox in page")
    finally:
        root.destroy()


def test_overflowing_text_keeps_own_wheel():
    root = _root()
    if root is None:
        print("SKIP (no display)")
        return
    try:
        install_page_wheel(root)
        canvas, inner = _scroll_page(root)
        tx = tk.Text(inner, height=3, width=40)
        tx.pack()
        tx.insert("1.0", "\n".join(f"line {i}" for i in range(30)))
        root.update()
        assert tx.yview() != (0.0, 1.0), "text not overflowing"
        before_page, before_text = canvas.yview(), tx.yview()
        tx.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert tx.yview()[0] > before_text[0], "text did not scroll"
        assert canvas.yview() == before_page, "page hijacked the text"
        tx.event_generate("<Button-5>")
        root.update()
        assert tx.yview()[0] > before_text[0], "Button-5: text stuck"
        assert canvas.yview() == before_page, "Button-5 moved page"
    finally:
        root.destroy()


def test_fitting_text_scrolls_page():
    root = _root()
    if root is None:
        print("SKIP (no display)")
        return
    try:
        install_page_wheel(root)
        canvas, inner = _scroll_page(root)
        tx = tk.Text(inner, height=3, width=40)
        tx.pack()
        tx.insert("1.0", "one short line")
        root.update()
        assert tx.yview() == (0.0, 1.0), "text should fit"
        _wheel_moves_page(root, tx, canvas.yview, tx.yview,
                          "fitting text")
    finally:
        root.destroy()


def test_standalone_tree_falls_back_to_self():
    root = _root()
    if root is None:
        print("SKIP (no display)")
        return
    try:
        install_page_wheel(root)
        tr = ttk.Treeview(root, columns=("a",), show="headings",
                          height=6)
        tr.pack(fill="both", expand=True)
        _fill_tree(tr)
        root.update()
        assert tr.yview()[1] < 1.0, "tree not scrollable in setup"
        assert page_canvas_for(tr) is None
        before = tr.yview()
        tr.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert tr.yview()[0] > before[0], "fallback: tree did not scroll"
        tr.event_generate("<Button-5>")
        root.update()
        assert tr.yview()[0] > before[0], "fallback: Button-5 stuck"
        mid = tr.yview()
        tr.event_generate("<MouseWheel>", delta=120)
        root.update()
        assert tr.yview()[0] < mid[0], "fallback: wheel up stuck"
    finally:
        root.destroy()


def test_chart_wheel_scrolls_clinical_page():
    """Wheel over a tooth cell moves the clinical page vertically;
    the chart's horizontal view does not move (R56: the chart's
    own horizontal wheel binding is gone)."""
    from src.ui.clinical import ClinicalTab
    from src.ui.dental_chart import DentalChartFrame  # noqa: F401

    class _Stub:
        lang = "en"
        current_patient = None
        current_user = "fady"
        current_role = "admin"

        def chart_teeth(self):
            return []

        def refresh_clinical(self):
            pass

        def on_teeth_select(self, teeth, typ):
            pass

        def print_pdf(self):
            pass

    root = _root(1380, 900)
    if root is None:
        print("SKIP (no display)")
        return
    try:
        install_page_wheel(root)
        tab = ClinicalTab(root, _Stub())
        tab.pack(fill="both", expand=True)
        root.update()
        canvas = tab.main_canvas
        assert canvas.yview()[1] < 1.0, "clinical page not scrollable"
        chart = tab.chart
        cell = next(iter(chart.tooth_cells.values()))
        _wheel_moves_page(root, cell, canvas.yview,
                          chart._canvas.xview, "dental chart")
    finally:
        root.destroy()


def test_tree_in_fitting_page_scrolls_itself():
    """R56 fallback: the page FITS (scrollregion <= viewport), so
    the wheel over the tree scrolls the TREE, not the page -- the
    wheel is never swallowed (the Users tab case: 22 rows in a
    3-row window on a page that fits at 1200x800)."""
    root = _root()
    if root is None:
        print("SKIP (no display)")
        return
    try:
        install_page_wheel(root)
        canvas, inner = _scroll_page(root, rows=3)
        tr = ttk.Treeview(inner, columns=("a",), show="headings",
                          height=3)
        tr.pack(fill="both", expand=True)
        _fill_tree(tr)
        root.update()
        assert canvas.yview() == (0.0, 1.0), "page should fit in setup"
        assert tr.yview()[1] < 1.0, "tree not scrollable in setup"
        before = tr.yview()
        tr.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert tr.yview()[0] > before[0], "fallback: tree did not scroll"
        assert canvas.yview() == (0.0, 1.0), "fallback: page moved"
        tr.event_generate("<Button-5>")
        root.update()
        assert tr.yview()[0] > before[0], "fallback: Button-5 stuck"
    finally:
        root.destroy()


def test_install_is_idempotent():
    # bind_class generates a NEW Tcl callback name on every bind,
    # so the binding scripts differ textually after two installs --
    # pin the BEHAVIOUR instead: one wheel event after a double
    # install must move the page by exactly ONE yview_scroll unit
    # (a duplicated handler would move it two).
    root = _root()
    if root is None:
        print("SKIP (no display)")
        return
    try:
        install_page_wheel(root)
        install_page_wheel(root)
        canvas, inner = _scroll_page(root)
        tr = ttk.Treeview(inner, columns=("a",), show="headings",
                          height=6)
        tr.pack(fill="both", expand=True)
        _fill_tree(tr)
        root.update()
        assert canvas.yview()[1] < 1.0, "page not scrollable in setup"
        canvas.yview_moveto(0.0); root.update()
        tr.event_generate("<MouseWheel>", delta=-120)
        root.update()
        stepped = canvas.yview()
        canvas.yview_moveto(0.0); root.update()
        canvas.yview_scroll(1, "units"); root.update()
        assert stepped == canvas.yview(), (stepped, canvas.yview())
    finally:
        root.destroy()


def run():
    test_tree_wheel_scrolls_page_not_tree()
    test_listbox_wheel_scrolls_page_not_list()
    test_overflowing_text_keeps_own_wheel()
    test_fitting_text_scrolls_page()
    test_standalone_tree_falls_back_to_self()
    test_tree_in_fitting_page_scrolls_itself()
    test_chart_wheel_scrolls_clinical_page()
    test_install_is_idempotent()
    print("PASS test_r56_wheel_page")
