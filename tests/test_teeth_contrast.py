"""Round 15 integration: selected tooth number must read >= 4.5:1 on the
accent cell bg in BOTH modes. Dark mode was white on #D97736 (3.16:1);
it now uses near-black #241A12 (5.36:1). Light keeps white on #A85F33
(4.82:1). GUI test under xvfb; skips gracefully with no display."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import get_theme_mode, set_theme_mode
from src.ui import dental_chart


def _lum(hexs):
    """Relative luminance of a #RRGGBB colour (WCAG). Tk may return
    named colours (e.g. "white") for fg values set literally."""
    named = {"white": "#FFFFFF", "black": "#000000"}
    hexs = named.get(str(hexs).lower(), hexs)
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hexs[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def _contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _num_label(cell):
    for w in cell.winfo_children():
        if w.winfo_class() == "Label" and not str(w.cget("image")) and w.cget("text"):
            return w
        got = _num_label(w)
        if got is not None:
            return got
    return None


def test_selected_tooth_number_contrast():
    prev = get_theme_mode()
    try:
        for mode in ("light", "dark"):
            set_theme_mode(mode)
            try:
                import tkinter as tk
                root = tk.Tk()
            except Exception:
                return
            root.withdraw()
            try:
                frame = dental_chart.DentalChartFrame(root, on_select=lambda s, t: None)
                frame.pack()
                root.update_idletasks()
                frame.toggle("16")
                root.update_idletasks()
                lbl = _num_label(frame.tooth_cells["16"])
                assert lbl is not None, f"no number label ({mode})"
                fg, bg = lbl.cget("fg"), lbl.cget("bg")
                ratio = _contrast(fg, bg)
                assert ratio >= 4.5, (mode, fg, bg, round(ratio, 2))
            finally:
                root.destroy()
    finally:
        set_theme_mode(prev)


if __name__ == "__main__":
    test_selected_tooth_number_contrast()
    print("PASS test_selected_tooth_number_contrast")
