"""Dental chart corrected anatomy order (round 12, item C, 2026-11-09).

Regression for the owner-caught error: the chart used to show the upper
row left-to-right as 11..18, 21..28, putting 11 where 18 belongs and 18
next to 21 in the middle. Correct clinical display (facing the patient)
has the midline in the centre: upper 18..11 | 21..28, lower
48..41 | 31..38, deciduous upper 55..51 | 61..65, lower 85..81 | 71..75.
Images must follow the FDI number, not the screen position (11 stays a
central incisor at the centre), and clicking a tooth must select by its
number. Also guards the AI teeth: photorealistic shading, crown top
brighter than root tips (relative bands; old flat PNGs were >245 white).
GUI tests skip (return) with no display, like test_dental_chart."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ui import dental_chart
from src.ui.dental_chart import display_order, tooth_image_name
from src.utils.helpers import DECIDUOUS, PERMANENT

TEETH_DIR = Path(dental_chart.__file__).resolve().parents[2] / "assets" / "teeth"

EXP_UPPER = ["18", "17", "16", "15", "14", "13", "12", "11",
             "21", "22", "23", "24", "25", "26", "27", "28"]
EXP_LOWER = ["48", "47", "46", "45", "44", "43", "42", "41",
             "31", "32", "33", "34", "35", "36", "37", "38"]
EXP_DEC_UPPER = ["55", "54", "53", "52", "51",
                 "61", "62", "63", "64", "65"]
EXP_DEC_LOWER = ["85", "84", "83", "82", "81",
                 "71", "72", "73", "74", "75"]


def test_display_order_function():
    assert display_order(PERMANENT[0:16], "upper") == EXP_UPPER
    assert display_order(PERMANENT[16:32], "lower") == EXP_LOWER
    assert display_order(DECIDUOUS[0:10], "upper") == EXP_DEC_UPPER
    assert display_order(DECIDUOUS[10:20], "lower") == EXP_DEC_LOWER
    # Midline neighbours: 11 next to 21, 41 next to 31, 51 next to 61.
    assert display_order(PERMANENT[0:16], "upper")[7:9] == ["11", "21"]
    assert display_order(PERMANENT[16:32], "lower")[7:9] == ["41", "31"]
    assert display_order(DECIDUOUS[0:10], "upper")[4:6] == ["51", "61"]
    assert display_order(DECIDUOUS[10:20], "lower")[4:6] == ["81", "71"]


def _chart():
    """Real DentalChartFrame under xvfb. Raises if there is no display."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    frame = dental_chart.DentalChartFrame(root, on_select=lambda s, t: None)
    frame.pack()
    root.update_idletasks()
    return root, frame


def _row_order(frame, numbers):
    """FDI numbers of one jaw sorted by grid column (left to right)."""
    return sorted(numbers,
                  key=lambda n: int(frame.tooth_cells[n].grid_info()["column"]))


def _pic_label(cell):
    # Round 13: the picture label sits inside the tooth cell's
    # RoundedFrame .inner, so recurse one level down.
    for w in cell.winfo_children():
        if w.winfo_class() == "Label" and str(w.cget("image")): return w
        got = _pic_label(w)
        if got is not None: return got
    return None


def test_widget_rows_in_clinical_order():
    try:
        root, frame = _chart()
    except Exception:
        return
    try:
        assert _row_order(frame, PERMANENT[0:16]) == EXP_UPPER
        assert _row_order(frame, PERMANENT[16:32]) == EXP_LOWER
        # 11 sits at the centre (column 7), 18 at the far left (column 0);
        # one empty midline-gap column lies between 11 and 21.
        assert int(frame.tooth_cells["11"].grid_info()["column"]) == 7
        assert int(frame.tooth_cells["18"].grid_info()["column"]) == 0
        c11 = int(frame.tooth_cells["11"].grid_info()["column"])
        c21 = int(frame.tooth_cells["21"].grid_info()["column"])
        assert c21 - c11 == 2, "no midline gap between 11 and 21"
        frame.tooth_type.set("لبني")
        frame.refresh()
        root.update_idletasks()
        assert _row_order(frame, DECIDUOUS[0:10]) == EXP_DEC_UPPER
        assert _row_order(frame, DECIDUOUS[10:20]) == EXP_DEC_LOWER
        c51 = int(frame.tooth_cells["51"].grid_info()["column"])
        c61 = int(frame.tooth_cells["61"].grid_info()["column"])
        assert c61 - c51 == 2, "no midline gap between 51 and 61"
    finally:
        root.destroy()


def test_each_tooth_shows_its_own_shape():
    """The image follows the FDI number, not the screen position: 11
    (centre) is still an incisor, 18 (far left) still a molar."""
    try:
        root, frame = _chart()
    except Exception:
        return
    try:
        assert frame._images, "tooth PNGs did not load"
        for n in PERMANENT:
            pic = _pic_label(frame.tooth_cells[n])
            assert pic is not None, f"tooth {n} shows no PNG"
            want = str(frame._images[tooth_image_name(n)])
            assert str(pic.cget("image")) == want, (
                f"tooth {n} shows the wrong image, want {tooth_image_name(n)}")
        frame.tooth_type.set("لبني")
        frame.refresh()
        root.update_idletasks()
        for n in DECIDUOUS:
            pic = _pic_label(frame.tooth_cells[n])
            assert pic is not None, f"tooth {n} shows no PNG"
            want = str(frame._images[tooth_image_name(n)])
            assert str(pic.cget("image")) == want, (
                f"tooth {n} shows the wrong image, want {tooth_image_name(n)}")
        # Round 33 re-pin: per-tooth assets - every FDI names its OWN render.
        assert tooth_image_name("11") == "tooth_11.png"
        assert tooth_image_name("18") == "tooth_18.png"
        assert tooth_image_name("48") == "tooth_48.png"
        assert tooth_image_name("55") == "tooth_55.png"
        assert tooth_image_name("51") == "tooth_51.png"
    finally:
        root.destroy()


def test_click_selects_by_number_not_position():
    """Clicking the centre cell selects 11 and the far-left cell 18:
    the handler resolves by tooth number, not grid position."""
    try:
        root, frame = _chart()
    except Exception:
        return
    try:
        frame.tooth_cells["11"].event_generate("<Button-1>")
        root.update_idletasks()
        assert frame.get_selection()[0] == ["11"], frame.get_selection()
        frame.tooth_cells["18"].event_generate("<Button-1>")
        root.update_idletasks()
        assert frame.get_selection()[0] == ["11", "18"]
        frame.tooth_cells["11"].event_generate("<Button-1>")
        root.update_idletasks()
        assert frame.get_selection()[0] == ["18"]
    finally:
        root.destroy()


def test_order_survives_selection_refresh():
    """set_selection + refresh (as the shell does on patient select)
    must not scramble the order back."""
    try:
        root, frame = _chart()
    except Exception:
        return
    try:
        frame.set_selection(["11", "26", "36"], "دائم")
        root.update_idletasks()
        assert _row_order(frame, PERMANENT[0:16]) == EXP_UPPER
        assert _row_order(frame, PERMANENT[16:32]) == EXP_LOWER
        assert frame.get_selection()[0] == ["11", "26", "36"]
    finally:
        root.destroy()


def test_render_has_bright_crown_and_warm_roots():
    """AI teeth: crown top brighter than root tips (relative bands;
    thresholds match test_teeth_regen: worst margin 4.2, top 219)."""
    from PIL import Image
    files = sorted(p.name for p in TEETH_DIR.glob("*.png"))
    assert len(files) == 52, files  # round 33: one render per tooth
    for name in files:
        assert name.startswith("tooth_") and name[6:-4].isdigit(), name
        im = Image.open(TEETH_DIR / name).convert("RGBA")
        assert im.size == (48, 96) and im.mode == "RGBA"
        _, y0, _, y1 = im.getchannel("A").getbbox()
        h = y1 - y0

        def mean_r(ya, yb):
            px = [im.getpixel((x, y)) for y in range(ya, yb)
                  for x in range(48) if im.getpixel((x, y))[3] > 50]
            assert px, f"{name}: empty band {ya}-{yb}"
            return sum(c[0] for c in px) / len(px)
        crown = mean_r(y0, y0 + max(4, int(0.15 * h)))
        root = mean_r(y1 - max(4, int(0.20 * h)), y1)
        assert crown > 210, f"{name}: crown top {crown:.1f}"
        assert crown - root > 3, f"{name}: margin {crown - root:.1f}"


if __name__ == "__main__":
    for name in sorted(a for a in dir() if a.startswith("test_")):
        globals()[name]()
        print("PASS", name)
    print("ALL DENTAL CHART ORDER TESTS PASSED")
