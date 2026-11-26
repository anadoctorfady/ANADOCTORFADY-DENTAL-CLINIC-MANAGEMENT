"""Round 14 wheel audit: regression tests for the bind_all bug.

ROOT CAUSE: bind_canvas_wheel() called canvas.bind_all() WITHOUT
add="+", and Tk's bind REPLACES the previous "all" handler — only the
LAST-registered canvas ever scrolled. Build order is PatientForm ->
ClinicalTab -> SettingsTab, so the wheel over the clinical page /
patient form did nothing (the owner's report); after the clipboard
picker closed, its dead handler stayed registered and NO canvas
scrolled until a rebuild. Settings also had its own unscoped handler.

These tests build the surfaces TOGETHER (the bug only shows when more
than one canvas is alive) and assert with real GUI events under Xvfb.
"""
import tkinter as tk
from tkinter import ttk

from src.models.clipboard_history import add_clip
from src.ui.clipboard_picker import open_clipboard_picker
from src.ui.clinical import ClinicalTab
from src.ui.dental_chart import DentalChartFrame
from src.ui.settings_ui import SettingsTab
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


def _scroll_canvas(root):
    f = tk.Frame(root)
    f.pack(side="left", fill="both", expand=True)
    c = tk.Canvas(f, bg="white", highlightthickness=0)
    sb = tk.Scrollbar(f, orient="vertical", command=c.yview)
    c.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    c.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(c)
    c.create_window((0, 0), window=inner, anchor="nw")
    for i in range(60):
        tk.Label(inner, text=f"row {i}").pack()
    inner.bind("<Configure>", lambda e, c=c: c.configure(scrollregion=c.bbox("all")))
    root.update()
    return c, inner


def test_two_canvases_coexist():
    """Core regression: two registered canvases must BOTH scroll.
    Pre-fix, bind_all replaced the first handler — wheel over the
    first canvas did nothing at all."""
    root = _root(900, 500)
    if root is None:
        print("SKIP test_two_canvases_coexist (no display)")
        return
    try:
        c1, i1 = _scroll_canvas(root)
        bind_canvas_wheel(c1)
        c2, i2 = _scroll_canvas(root)
        bind_canvas_wheel(c2)
        assert c1.yview()[1] < 1.0 and c2.yview()[1] < 1.0
        lbl1 = i1.winfo_children()[5]
        lbl1.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert c1.yview()[0] > 0.0, "wheel over canvas 1 did not scroll it"
        assert c2.yview()[0] == 0.0, "wheel over canvas 1 moved canvas 2"
        p1 = c1.yview()
        lbl2 = i2.winfo_children()[5]
        lbl2.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert c2.yview()[0] > 0.0, "wheel over canvas 2 did not scroll it"
        assert c1.yview() == p1, "wheel over canvas 2 moved canvas 1"
    finally:
        root.destroy()


def test_settings_does_not_hijack():
    """Settings canvas scrolls only over itself; a Treeview elsewhere
    scrolls itself and leaves the settings canvas untouched."""
    root = _root(900, 500)
    if root is None:
        print("SKIP test_settings_does_not_hijack (no display)")
        return
    try:
        install_page_wheel(root)  # R56: the App installs this once
        tab = SettingsTab(root, _Stub())
        tab.pack(fill="both", expand=True)
        tree = ttk.Treeview(root, columns=("a",), show="headings", height=6)
        tree.pack(fill="both", expand=True)
        for i in range(40):
            tree.insert("", "end", values=(f"row {i}",))
        root.update()
        assert tab._canvas.yview()[1] < 1.0 and tree.yview()[1] < 1.0
        s0, t0 = tab._canvas.yview(), tree.yview()
        tree.event_generate("<MouseWheel>", delta=-120)
        root.update()
        # R56: the tree lives in NO scroll page, so the delegate
        # falls back to scrolling the tree itself.
        assert tree.yview()[0] > t0[0], "wheel did not scroll the tree"
        assert tab._canvas.yview() == s0, "settings canvas hijacked the tree wheel"
        _down_up(root, tab.body, tab._canvas.yview)
    finally:
        root.destroy()


def test_picker_close_keeps_other_canvases():
    """Opening + closing the clipboard picker must not kill the other
    canvases. Pre-fix, the picker's dead handler stayed registered as
    the only "all" handler, so clinical/settings wheels went dead."""
    root = _root()
    if root is None:
        print("SKIP test_picker_close_keeps_other_canvases (no display)")
        return
    try:
        for i in range(25):
            add_clip(f"clip item {i:02d} for wheel test")
        clin = ClinicalTab(root, _Stub())
        clin.pack(fill="both", expand=True)
        sett = SettingsTab(root, _Stub())
        sett.pack(fill="both", expand=True)
        root.update()
        # Round 19: page canvas anchored by the history section
        # (the input tables now live in a fixed, canvas-less block).
        canvas = _canvas_of(clin, clin.history_section)
        assert canvas is not None and canvas.yview()[1] < 1.0
        win = open_clipboard_picker(root)
        root.update()
        win.destroy()
        root.update()
        _down_up(root, clin.history_section, canvas.yview)
        assert sett._canvas.yview()[0] == 0.0, "clinical wheel moved settings"
    finally:
        root.destroy()


