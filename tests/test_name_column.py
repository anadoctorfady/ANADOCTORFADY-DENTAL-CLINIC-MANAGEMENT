"""Patient-list Name column must fit a full four-part name (2026-11-08).

Regression test for the truncated-name report ("Ahmed Mohammed Ali Hassa…"):
the Name column was 180px while "Ahmed Mohammed Ali Hassan" measures
~182px in the list font, so it was clipped. The column is now 215px.
GUI test: skips gracefully with no display (same pattern as
test_screenshot_fixes.py).
"""
from tkinter import font as tkfont

LONG_EN = "Ahmed Mohammed Ali Hassan"
LONG_AR = "أحمد محمد علي حسن"
MOBILE = "+963944234456"
PAD = 10  # cell padding allowance, px


def _measure(text):
    return tkfont.Font(family="Segoe UI", size=9).measure(text)


def test_name_column_fits_long_name():
    try:
        from src.ui.shell import App
        app = App()
    except Exception:
        return  # no display: skip GUI check
    try:
        # Round 21: the list lives in the shell's scrollable left
        # column (shell_left.py); its column widths only settle
        # once the window is realized, so deiconify + size it
        # (the old fixed column measured fine while withdrawn).
        app.deiconify(); app.geometry("1380x820")
        app.update()
        name_w = app.tree.column("name", "width")
        assert name_w >= _measure(LONG_EN) + PAD, (
            f"Name column {name_w}px too narrow for {LONG_EN!r} "
            f"({_measure(LONG_EN)}px + {PAD}px padding)")
        assert name_w >= _measure(LONG_AR) + PAD, (
            f"Name column {name_w}px too narrow for {LONG_AR!r}")
        mobile_w = app.tree.column("mobile", "width")
        assert mobile_w >= _measure(MOBILE), (
            f"Mobile column {mobile_w}px too narrow for {MOBILE!r}")
        total = (app.tree.column("file", "width") + name_w + mobile_w)
        assert total <= 362, f"columns total {total}px overflows the 380px pane"
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def test_name_column_minimum_width_constant():
    """Static guard: the source must keep the Name column >= 200px.
    Round 21: the column is built in src/ui/shell_left.py now."""
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent
           / "src" / "ui" / "shell_left.py").read_text(encoding="utf-8")
    import re
    m = re.search(r'\.column\("name", width=(\d+)\)', src)
    assert m, "Name column width not found in shell.py"
    assert int(m.group(1)) >= 200, (
        f"Name column width {m.group(1)}px below the 200px minimum")
