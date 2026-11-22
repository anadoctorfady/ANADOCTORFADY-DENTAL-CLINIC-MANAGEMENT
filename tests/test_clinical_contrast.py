"""Contrast fixes from the clinical redesign (Items 5 bonus + prereq 1):
dental-chart unselected teeth use the current theme text in dark mode,
and the clinical finance pairs are >= 4.5:1. GUI tests skip gracefully
when no display is available."""
import tkinter as tk

from src.config.theme import DARK
from src.ui.clinical import ClinicalTab
from src.ui.dental_chart import DentalChartFrame
from src.config.settings import get_theme_mode, set_theme_mode


def _lum(hexcol):
    named = {"white": "#FFFFFF", "black": "#000000"}
    hexcol = named.get(str(hexcol).lower(), str(hexcol))
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(fg, bg):
    a, b = _lum(fg), _lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _walk(widget):
    yield widget
    for ch in widget.winfo_children():
        yield from _walk(ch)


def test_dental_chart_unselected_teeth_use_dark_text():
    prev = get_theme_mode()
    set_theme_mode("dark")
    try:
        root = tk.Tk()
    except tk.TclError:
        set_theme_mode(prev)
        print("SKIP test_dental_chart_unselected_teeth_use_dark_text (no display)")
        return
    root.withdraw()
    try:
        chart = DentalChartFrame(root)
        chart.pack()
        root.update_idletasks()
        assert not chart.selected
        def _walk(w):  # round 13: number label sits in the cell's RoundedFrame .inner
            yield w
            for c in w.winfo_children():
                yield from _walk(c)
        for n, cell in chart.tooth_cells.items():
            for w in _walk(cell):
                if isinstance(w, tk.Label) and str(w.cget("text")) == str(n):
                    assert str(w.cget("fg")) == DARK["text"], (n, w.cget("fg"))
                    assert _ratio(str(w.cget("fg")), str(w.cget("bg"))) >= 4.5
                    break
            else:
                raise AssertionError(f"no number label for tooth {n}")
    finally:
        root.destroy()
        set_theme_mode(prev)


def test_finance_contrast_fixed():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_finance_contrast_fixed (no display)")
        return
    root.withdraw()
    try:
        class FakeApp:
            lang = "en"
            current_patient = None
            current_user = "fady"
            current_role = "admin"
            def chart_teeth(self):
                return []
            def refresh_clinical(self):
                pass
        tab = ClinicalTab(root, FakeApp())
        tab.pack()
        root.update_idletasks()
        # R40 RE-PIN (owner correction 2026-11-21): the "Add
        # Payment" button is GONE with its zone — the money action
        # button in the ONE entry place is Print invoice; its
        # fill/text pair keeps the >= 4.5:1 bar.
        btns = [w for w in _walk(tab) if isinstance(w, tk.Button)
                and str(w.cget("text")) == "Add Payment"]
        assert len(btns) == 0
        inv = tab.btn_invoice
        # RoundedButton's visible fill is _bg; the bg option is only
        # the transparent-corner backdrop (parent bg), not what is drawn.
        _fill = getattr(inv, "_bg", inv.cget("bg"))
        assert _ratio(str(inv.cget("fg")), str(_fill)) >= 4.5
        # R38: the Remaining label is gone; the balance line
        # (lbl_pat_totals) is the money area's state text.
        assert _ratio(str(tab.lbl_pat_totals.cget("fg")), str(tab.lbl_pat_totals.cget("bg"))) >= 4.5
        # R40: the titled finance section (and its #7A3F16 title
        # label) is removed by the one-place correction — nothing
        # replaces the title; the strip has no section heading.
        assert not hasattr(tab, "fin_frame")
    finally:
        root.destroy()
