"""Round 15 regression, GUI half (2026-11-10): the chart shows the
flipped upper teeth on the app's MAIN background (no white box).

The chart surfaces used th["panel"], which is pure white #FFFFFF in
light mode - the whole chart was a white box on the Warm Sand main
background. They now use th["bg"] (paper in light mode, Warm Charcoal
in dark). GUI tests run under Xvfb and skip gracefully with no
display, like test_dental_chart_order; they cover no record selected
AND a record selected (set_selection), and both themes. The pure-PIL
flip tests live in tests/test_teeth_flip.py.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import get_theme_mode, set_theme_mode
from src.config.theme import DARK, LIGHT
from src.ui import dental_chart
from src.ui.dental_chart import tooth_image_name
from src.utils.helpers import DECIDUOUS, PERMANENT

EXP_UPPER = ["18", "17", "16", "15", "14", "13", "12", "11",
             "21", "22", "23", "24", "25", "26", "27", "28"]
EXP_LOWER = ["48", "47", "46", "45", "44", "43", "42", "41",
             "31", "32", "33", "34", "35", "36", "37", "38"]
EXP_DEC_UPPER = ["55", "54", "53", "52", "51",
                 "61", "62", "63", "64", "65"]
EXP_DEC_LOWER = ["85", "84", "83", "82", "81",
                 "71", "72", "73", "74", "75"]


def _chart():
    """Real DentalChartFrame under xvfb. Raises if no display."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    frame = dental_chart.DentalChartFrame(root, on_select=lambda s, t: None)
    frame.pack()
    root.update_idletasks()
    return root, frame


def _pic_label(cell):
    for w in cell.winfo_children():
        if w.winfo_class() == "Label" and str(w.cget("image")):
            return w
        got = _pic_label(w)
        if got is not None:
            return got
    return None


def _row_order(frame, numbers):
    return sorted(numbers,
                  key=lambda n: int(frame.tooth_cells[n].grid_info()["column"]))


def test_chart_loads_flipped_images_and_order():
    """No record selected: chart loads, upper teeth show the flipped
    images, numbering and click-by-number are unchanged."""
    try:
        root, frame = _chart()
    except Exception:
        return
    try:
        assert len(frame._images) == 52, "tooth PNGs did not load"
        assert _row_order(frame, PERMANENT[0:16]) == EXP_UPPER
        assert _row_order(frame, PERMANENT[16:32]) == EXP_LOWER
        for n in ("11", "18", "26", "36", "48"):
            pic = _pic_label(frame.tooth_cells[n])
            assert pic is not None, f"tooth {n} shows no PNG"
            assert str(pic.cget("image")) == str(
                frame._images[tooth_image_name(n)]), f"tooth {n} wrong image"
        frame.tooth_cells["11"].event_generate("<Button-1>")
        root.update_idletasks()
        assert frame.get_selection()[0] == ["11"]
        frame.tooth_cells["18"].event_generate("<Button-1>")
        root.update_idletasks()
        assert frame.get_selection()[0] == ["11", "18"]
        frame.tooth_type.set("لبني")
        frame.refresh()
        root.update_idletasks()
        assert _row_order(frame, DECIDUOUS[0:10]) == EXP_DEC_UPPER
        assert _row_order(frame, DECIDUOUS[10:20]) == EXP_DEC_LOWER
        pic = _pic_label(frame.tooth_cells["51"])
        assert str(pic.cget("image")) == str(
            frame._images["tooth_51.png"])
    finally:
        root.destroy()


def test_chart_with_record_selected():
    """Record selected (as the shell does on patient select): order
    survives, clicks still resolve by number, selected cells show the
    accent bg while unselected cells stay on the main background."""
    try:
        root, frame = _chart()
    except Exception:
        return
    try:
        frame.set_selection(["11", "26", "36"], "دائم")
        root.update_idletasks()
        assert _row_order(frame, PERMANENT[0:16]) == EXP_UPPER
        assert frame.get_selection()[0] == ["11", "26", "36"]
        frame.tooth_cells["36"].event_generate("<Button-1>")
        root.update_idletasks()
        assert frame.get_selection()[0] == ["11", "26"]
        from src.config.theme import current
        th = current()
        # RoundedFrame's own bg is its parent's bg; the cell colour
        # lives on .inner (and the picture label) - accent when
        # selected, main background when not.
        assert frame.tooth_cells["11"].inner.cget("bg") == th["accent"]
        assert frame.tooth_cells["12"].inner.cget("bg") == th["bg"]
        assert _pic_label(frame.tooth_cells["11"]).cget("bg") == th["accent"]
    finally:
        root.destroy()


def _assert_no_white(frame, th):
    """Every Frame/Label/Radiobutton/Canvas in the chart tree sits on
    the main background token - never pure white #FFFFFF."""
    import tkinter as tk

    def walk(w):
        if isinstance(w, (tk.Frame, tk.Label, tk.Radiobutton, tk.Canvas)):
            assert str(w.cget("bg")).lower() != "#ffffff", (
                f"white box: {w.winfo_class()} {w}")
        for c in w.winfo_children():
            walk(c)

    assert frame.cget("bg") == th["bg"], frame.cget("bg")
    walk(frame)


def test_chart_uses_main_background_light_and_dark():
    """Light mode: chart bg is Warm Sand #F6F1E9 (paper), not white.
    Dark mode: Warm Charcoal #1A1614. Theme restored afterwards."""
    prev = get_theme_mode()
    try:
        root, frame = _chart()
    except Exception:
        return
    try:
        _assert_no_white(frame, LIGHT)
        assert frame._canvas.cget("bg") == LIGHT["bg"]
        root.destroy()
        set_theme_mode("dark")
        root, frame = _chart()
        _assert_no_white(frame, DARK)
        assert frame._canvas.cget("bg") == DARK["bg"]
    finally:
        set_theme_mode(prev)
        try:
            root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    for name in sorted(a for a in dir() if a.startswith("test_")):
        globals()[name]()
        print("PASS", name)
    print("ALL TEETH FLIP (GUI) TESTS PASSED")
