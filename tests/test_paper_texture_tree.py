"""Paper Treeview (Round 13, Item 5): the patient-list Treeview's
empty area shows the tiled paper in light mode and stays perfectly
flat in dark mode. GUI test under Xvfb; skips without a display."""
import statistics
import tkinter as tk
from tkinter import ttk

from PIL import ImageGrab

from src.config.settings import get_theme_mode, set_theme_mode
from src.config.theme import tokens
from src.ui.paper_bg import apply_treeview_paper


def test_treeview_paper_light_textured_dark_flat():
    """Empty area below the last row: textured in light mode
    (luminance stdev > 1, mean Warm Sand) and flat in dark mode;
    the layout uses the paper field element only in light mode."""
    for mode_name, textured in (("light", True), ("dark", False)):
        prev = get_theme_mode()
        set_theme_mode(mode_name)
        try:
            root = tk.Tk()
        except tk.TclError:
            set_theme_mode(prev)
            print(f"SKIP test_treeview_paper_{mode_name} (no display)")
            continue
        try:
            root.geometry("500x400")
            st = ttk.Style(root)
            try:
                st.theme_use("clam")
            except Exception:
                pass
            apply_treeview_paper(st, tokens(mode_name == "dark"))
            assert ("Paper.Treeview.field" in str(st.layout("Paper.Treeview"))) == textured
            tr = ttk.Treeview(root, columns=("a",), show="headings", height=8,
                              style="Paper.Treeview")
            tr.heading("a", text="Name")
            tr.pack(fill="both", expand=True)
            for i in range(2):
                tr.insert("", "end", values=(f"Row {i}",))
            root.deiconify()
            root.update_idletasks()
            root.update()
            x, y = tr.winfo_rootx(), tr.winfo_rooty()
            w, h = tr.winfo_width(), tr.winfo_height()
            shot = ImageGrab.grab(bbox=(x, y, x + w, y + h)).convert("RGB")
            band = [shot.getpixel((xx, yy)) for yy in range(h - 60, h - 10, 5)
                    for xx in range(10, w - 10, 10)]
            lum = [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in band]
            sd = statistics.stdev(lum)
            if textured:
                assert sd > 1.0, f"light tree empty area flat (stdev {sd:.2f})"
                assert abs(statistics.mean(lum) - 241.5) < 5, statistics.mean(lum)
            else:
                assert sd == 0.0, f"dark tree empty area textured (stdev {sd:.2f})"
        finally:
            root.destroy()
            set_theme_mode(prev)


def test_treeview_paper_survives_theme_toggle():
    """Light -> dark -> light on the same root: the paper element is
    created once, the layout flips back and forth, no TclError."""
    prev = get_theme_mode()
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_treeview_paper_toggle (no display)")
        return
    try:
        st = ttk.Style(root)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        for mode_name, textured in (("light", True), ("dark", False), ("light", True)):
            set_theme_mode(mode_name)
            apply_treeview_paper(st, tokens(mode_name == "dark"))
            assert ("Paper.Treeview.field" in str(st.layout("Paper.Treeview"))) == textured
    finally:
        root.destroy()
        set_theme_mode(prev)
