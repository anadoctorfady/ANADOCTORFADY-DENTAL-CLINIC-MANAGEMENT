"""Round 52, Section C: Statistics charts cannot overlap rows at
Windows DPI conditions.

The R51 fix measured the pitch from a "Segoe UI" Font object while
the Arabic labels were DRAWN in Segoe UI too -- a family with no
Arabic glyphs, so Windows fallback glyphs (taller than the measured
linespace) collided on the owner's machine while this VM's metrics
stayed honest. R52 drew Arabic chart text in Amiri and derived the
pitch from the very Font objects that draw. R56: Amiri was REVERTED
by the owner (its linespace made the whole Arabic UI taller) -- the
Arabic labels are drawn in Segoe UI again, and this test proves the
invariant geometrically on the UI font: at tk scaling 1.0 / 1.25 /
1.5, English and Arabic, dense long labels, no two rows' text
bboxes intersect vertically, every text bbox fits inside the canvas
height, and the monthly chart's value/month labels stay inside the
canvas too. (The R55 flattening of multi-line labels stays.)
"""
import tkinter as tk
import tkinter.font as tkfont

from src.ui import finance_charts as charts

TH = {"panel": "#FFFFFF", "text": "#222222", "muted": "#777777",
      "border": "#CCCCCC"}
EN = [("Root canal treatment -- molar, three canals, rotary", 12),
      ("Surgical extraction of impacted lower third molar", 11),
      ("Porcelain fused to metal crown and cementation", 10),
      ("Complete upper and lower removable denture, acrylic", 9),
      ("Orthodontic fixed appliance adjustment, archwire", 8),
      ("Endodontic retreatment, gutta percha removal", 7),
      ("Periodontal flap surgery, regeneration membrane", 6),
      ("Implant placement with guided bone regeneration", 5),
      ("Pediatric pulpotomy, stainless steel crown", 4),
      ("Scaling and root planing, full mouth, four quadrants", 3)]
AR = [("معالجة لبية لقناة جذرية لضرس خلفي ثلاث قنوات", 12),
      ("قلع جراحي لضرس عقل سفلي منطمر مع إزالة عظم", 11),
      ("تاج خزفي معدني كامل مع تحضير وتثبيت بالإسمنت", 10),
      ("طقم أسنان كامل علوي وسفلي متحرك من الأكريل", 9),
      ("تعديل جهاز تقويم ثابت مع تغيير السلك وربط مطاط", 8),
      ("إعادة معالجة لبية مع إزالة الكوتابيركا القديمة", 7),
      ("جراحة لثوية بشريحة مع غشاء تجديد نسيجي موجه", 6),
      ("زراعة سنية فورية مع ترقيع عظمي وغشاء كولاجيني", 5),
      ("بتر لب جزئي لسن لبني مع تاج ستانلس ستيل", 4),
      ("تقليح وتجريف جذور لكامل الفم أربعة أرباع", 3)]


def _rows(cv):
    """Text items clustered into rows by centre-y."""
    items = []
    for iid in cv.find_all():
        if cv.type(iid) == "text":
            bb = cv.bbox(iid)
            if bb:
                items.append(bb)
    rows = []
    for bb in sorted(items, key=lambda b: (b[1] + b[3]) / 2):
        cy = (bb[1] + bb[3]) / 2
        if rows and abs(cy - rows[-1][0]) <= 3:
            rows[-1][1].append(bb)
        else:
            rows.append([cy, [bb]])
    return [(min(b[1] for b in bs), max(b[3] for b in bs))
            for _cy, bs in rows]


def _check_hbars(scaling, family, items):
    root = tk.Tk(); root.withdraw()
    try:
        root.tk.call("tk", "scaling", scaling)
        cv = tk.Canvas(root, width=1000, height=96)
        cv.pack(); root.update()
        charts.draw_hbars(cv, items, "no data", TH,
                          fmt=lambda v: f"{int(v)}", family=family)
        root.update()
        bands = _rows(cv)
        assert len(bands) == len(items), (scaling, family, bands)
        height = int(cv.cget("height"))
        prev_bottom = -1
        for top, bottom in bands:
            assert top >= prev_bottom, (scaling, family, bands)
            assert bottom <= height, (scaling, family, bottom, height)
            prev_bottom = bottom
        font = tkfont.Font(root=root, font=(family, 9))
        pitch = (height - 12) / len(items)
        assert pitch >= font.metrics("linespace"), (
            scaling, family, pitch, font.metrics("linespace"))
    finally:
        root.destroy()


def test_charts_no_overlap_any_scaling():
    # R56: Amiri reverted -- the Arabic labels are drawn in the UI
    # font (Segoe UI) now, so the Arabic non-overlap pin runs on it.
    for scaling in (1.0, 1.25, 1.5):
        _check_hbars(scaling, "Segoe UI", EN)
        _check_hbars(scaling, "Segoe UI", AR)


def test_monthly_labels_fit_at_high_scaling():
    root = tk.Tk(); root.withdraw()
    try:
        root.tk.call("tk", "scaling", 1.5)
        cv = tk.Canvas(root, width=1000, height=140)
        cv.pack(); root.update()
        series = [(f"2026-{m:02d}", 1000.0 * m, 500.0 * m)
                  for m in range(1, 13)]
        charts.draw_monthly(cv, series, "no data", TH)
        root.update()
        height = int(cv.cget("height"))
        bands = _rows(cv)
        for top, bottom in bands:
            assert bottom <= height, (top, bottom, height)
        # value row sits strictly above the month row
        assert len(bands) == 2, bands
        assert bands[0][1] <= bands[1][0], bands
    finally:
        root.destroy()


def run():
    test_charts_no_overlap_any_scaling()
    test_monthly_labels_fit_at_high_scaling()


if __name__ == "__main__":
    run()
    print("test_r52_charts_scaling OK")
