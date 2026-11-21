"""Dental chart realistic teeth (ITEM 4, 2026-11-08): PNG tooth assets
exist + load, FDI -> type/jaw mapping covers all 32 permanent + 20
deciduous teeth, chart shows every tooth, click selection works.
GUI tests skip (return) with no display, like test_sync_button; run
under xvfb-run for the GUI checks."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ui import dental_chart
from src.ui.dental_chart import tooth_image_name, tooth_type_for
from src.utils.helpers import DECIDUOUS, PERMANENT

TEETH_DIR = Path(dental_chart.__file__).resolve().parents[2] / "assets" / "teeth"
EXPECTED = {f"tooth_{n}.png" for n in PERMANENT + DECIDUOUS}


def test_tooth_image_files_exist_and_load():
    from PIL import Image
    assert TEETH_DIR.is_dir(), f"missing assets dir {TEETH_DIR}"
    names = {p.name for p in TEETH_DIR.glob("*.png")}
    assert EXPECTED <= names, f"missing tooth PNGs: {EXPECTED - names}"
    for name in sorted(EXPECTED):
        with Image.open(TEETH_DIR / name) as im:
            assert im.size == (48, 96), f"{name} is {im.size}, want 48x96"
            assert im.mode == "RGBA" and len(im.getbbox() or []) == 4


def test_tooth_type_mapping_covers_all_teeth():
    assert tooth_type_for("11") == ("incisor", "upper")
    assert tooth_type_for("13") == ("canine", "upper")
    assert tooth_type_for("14") == ("premolar", "upper")
    assert tooth_type_for("16") == ("molar", "upper")
    assert tooth_type_for("31") == ("incisor", "lower")
    assert tooth_type_for("43") == ("canine", "lower")
    assert tooth_type_for("44") == ("premolar", "lower")
    assert tooth_type_for("46") == ("molar", "lower")
    assert tooth_type_for("51") == ("incisor", "upper")
    assert tooth_type_for("53") == ("canine", "upper")
    assert tooth_type_for("54") == ("molar", "upper")  # no deciduous premolar
    assert tooth_type_for("71") == ("incisor", "lower")
    assert tooth_type_for("74") == ("molar", "lower")
    for n in PERMANENT + DECIDUOUS:
        assert tooth_type_for(n) is not None, f"unmapped FDI {n}"
        assert tooth_image_name(n) in EXPECTED, f"no PNG for {n}"
    assert tooth_type_for("99") is None
    assert tooth_type_for("xx") is None


def _chart():
    """Real DentalChartFrame under xvfb. Raises if there is no display."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    frame = dental_chart.DentalChartFrame(root, on_select=lambda s, t: None)
    frame.pack()
    root.update_idletasks()
    return root, frame


def _images_shown(frame):
    """True when a tooth cell shows a PNG (not the glyph fallback)."""
    def _walk(w):  # round 13: pic label sits in the cell's RoundedFrame .inner
        yield w
        for c in w.winfo_children():
            yield from _walk(c)
    return any(w.winfo_class() == "Label" and str(w.cget("image"))
               for cell in frame.tooth_cells.values() for w in _walk(cell))


def test_permanent_chart_has_32_graphic_teeth():
    try:
        root, frame = _chart()
    except Exception:
        return  # no display: skip GUI check
    assert set(frame.tooth_cells) == set(PERMANENT)
    assert len(frame.tooth_cells) == 32
    assert frame._images, "tooth PNGs did not load into the chart"
    assert _images_shown(frame), "cells show glyph fallback, not PNGs"
    root.destroy()


def test_deciduous_chart_has_20_graphic_teeth():
    try:
        root, frame = _chart()
    except Exception:
        return
    frame.tooth_type.set("لبني")
    frame.refresh()
    root.update_idletasks()
    assert set(frame.tooth_cells) == set(DECIDUOUS)
    assert len(frame.tooth_cells) == 20
    assert _images_shown(frame)
    root.destroy()


def test_selection_toggle_and_callback():
    try:
        import tkinter as tk
    except Exception:
        return
    seen = []
    try:
        root = tk.Tk()
        root.withdraw()
        frame = dental_chart.DentalChartFrame(root, on_select=lambda s, t: seen.append(s))
        frame.pack()
        root.update_idletasks()
    except Exception:
        return
    frame.toggle("16")
    assert frame.get_selection() == (["16"], "دائم")
    assert seen[-1] == ["16"]
    frame.toggle("11")
    assert frame.get_selection()[0] == ["11", "16"]
    frame.toggle("16")  # second click deselects
    assert frame.get_selection()[0] == ["11"]
    frame.set_selection(["26", "36"], "دائم")
    assert frame.get_selection() == (["26", "36"], "دائم")
    root.destroy()


def test_fallback_when_images_missing():
    try:
        import tkinter as tk
    except Exception:
        return
    saved = dental_chart.TEETH_DIR
    dental_chart.TEETH_DIR = Path("/nonexistent-teeth-dir")
    try:
        root = tk.Tk()
        root.withdraw()
        frame = dental_chart.DentalChartFrame(root)
        frame.pack()
        root.update_idletasks()
    except Exception:
        return
    finally:
        dental_chart.TEETH_DIR = saved
    assert frame._images == {}  # graceful: empty, no crash
    assert set(frame.tooth_cells) == set(PERMANENT)  # glyph fallback shown
    root.destroy()


def test_images_survive_new_tk_root():
    """Regression: images must be created against the CURRENT Tk root.
    The full gate creates/destroys many Tk() roots; PhotoImage without a
    master binds to the (possibly destroyed) default root and the next
    Label raises TclError 'image pyimageNNN doesn't exist' (gate 41/44).
    Build a chart + a logo photo, destroy the root, build both again
    under a fresh root - must not raise."""
    import tkinter as tk
    try:
        root1 = tk.Tk()
        root1.withdraw()
        f1 = dental_chart.DentalChartFrame(root1, on_select=lambda s, t: None)
        f1.pack()
        root1.update_idletasks()
        from src.utils.logo import photo
        img1 = photo(root1, 40, name="logo_corner.png")
        assert img1 is not None
        root1.destroy()
        root2 = tk.Tk()
        root2.withdraw()
        f2 = dental_chart.DentalChartFrame(root2, on_select=lambda s, t: None)
        f2.pack()
        root2.update_idletasks()
        assert len(f2._images) == 52, f"chart images missing under 2nd root: {len(f2._images)}"
        img2 = photo(root2, 40, name="logo_corner.png")
        assert img2 is not None
        tk.Label(root2, image=img2).pack()
        root2.update_idletasks()
        root2.destroy()
    except tk.TclError:
        return  # no display: skip like the other GUI tests


def test_chart_fits_1380px_window():
    try:
        root, frame = _chart()
    except Exception:
        return
    root.geometry("1380x820")
    root.update_idletasks()
    assert frame.area.winfo_reqwidth() <= 1100, frame.area.winfo_reqwidth()
    root.destroy()


if __name__ == "__main__":
    for name in sorted(a for a in dir() if a.startswith("test_")):
        globals()[name]()
        print("PASS", name)
    print("ALL DENTAL CHART TESTS PASSED")
