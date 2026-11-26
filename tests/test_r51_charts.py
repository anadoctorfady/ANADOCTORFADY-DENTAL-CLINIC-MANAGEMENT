"""Round 51 Section B: Statistics chart overlap regression pins.

The R49 charts squeezed 10 rows into a fixed 96px canvas with a
13px pitch floor -- below the label font's line height, so rows
and letters collided (owner report, 2026-11-24). Pins: the pitch
comes from the measured font linespace, the canvas is sized to
its content, long labels are ellipsised to the measured column
(not cut at a fixed character count), and every value is drawn.
"""
import tkinter as tk
import tkinter.font as tkfont

from src.config.theme import finance_current
from src.ui import finance_charts as charts

LONG = [
    "Endodontic Retreatment of Mandibular Molar with Broken File",
    "Full Ceramic Zirconia Crown Restoration Upper Anterior",
    "Surgical Extraction of Impacted Third Molar with Suturing",
    "Guided Bone Regeneration with Resorbable Membrane",
    "Complete Removable Denture Upper and Lower Arches",
    "Orthodontic Fixed Appliance Adjustment with Archwire Change",
    "Periodontal Flap Surgery with Bone Grafting Deep Pocket",
    "Dental Implant Placement with Healing Abutment Follow-up",
    "Composite Veneer Restoration Multiple Anterior Surfaces",
    "Root Canal Treatment Premolar Two Canals Thermal Obturation",
]


def _canvas(root, width=900):
    cv = tk.Canvas(root, width=width, height=96)
    cv.pack()
    root.update_idletasks()
    return cv


def _texts(cv):
    return [(cv.itemcget(i, "text"), cv.coords(i))
            for i in cv.find_all() if cv.type(i) == "text"]


def test_hbars_pitch_from_font_metrics():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_r51_charts (no display)"); return
    try:
        th = finance_current()
        cv = _canvas(root)
        items = [(name, float(1000 * (i + 1)))
                 for i, name in enumerate(LONG)]
        assert charts.draw_hbars(cv, items, "none", th) == 10
        root.update_idletasks()
        linespace = tkfont.Font(font=("Segoe UI", 9)).metrics("linespace")
        # Canvas sized to content: 10 rows at >= linespace+6 pitch.
        assert int(cv.cget("height")) >= 8 + 10 * (linespace + 6), \
            cv.cget("height")
        labels = [(txt, xy) for txt, xy in _texts(cv)
                  if not txt.replace(",", "").replace(".", "").isdigit()]
        assert len(labels) == 10, len(labels)
        ys = sorted(xy[1] for _t, xy in labels)
        for a, b in zip(ys, ys[1:]):
            assert b - a >= linespace, (a, b, linespace)  # never overlap
        # Long labels ellipsised cleanly and inside the label column.
        font = tkfont.Font(font=("Segoe UI", 9))
        widest = max(font.measure(txt) for txt, _xy in labels)
        assert any(txt.endswith("…") for txt, _xy in labels)
        assert widest <= 900 * 2 // 5, widest
        # Every value drawn exactly once, formatted.
        values = [txt for txt, _xy in _texts(cv)
                  if txt.replace(",", "").replace(".", "").isdigit()]
        assert len(values) == 10, values
    finally:
        root.destroy()


def test_hbars_narrow_and_empty():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_r51_charts narrow (no display)"); return
    try:
        th = finance_current()
        cv = _canvas(root, width=420)
        items = [(name, 5.0) for name in LONG[:4]]
        assert charts.draw_hbars(cv, items, "none", th) == 4
        assert charts.draw_hbars(cv, [], "No data in this period", th) == 0
        texts = [txt for txt, _xy in _texts(cv)]
        assert texts == ["No data in this period"], texts
        assert int(cv.cget("height")) == 44
    finally:
        root.destroy()


def run():
    test_hbars_pitch_from_font_metrics()
    test_hbars_narrow_and_empty()
    print("PASS test_r51_charts")
