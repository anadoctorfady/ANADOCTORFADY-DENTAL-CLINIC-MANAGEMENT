"""Round 43: items 2 + 3 + the item-4 meaning-colour proof.

Item 3 (owner): pressing All / Upper / Lower when that exact set
is already selected DESELECTS it and auto-clears the tooth
numbers from the entry + the four clinical fields (no manual
removal); pressing a different button switches the set. Driven
through the REAL chart buttons on BOTH chart types, with the
clinical tab's wiring replicated (entry follows on_select;
insert_selected_teeth fills the fields; on_jaw_clear scrubs).

Item 2: table radius is 24 and corners are ANTIALIASED (the 1x
PIL draw had ZERO partial-alpha corner pixels -- the owner's
"corner breaks"); the RoundedFrame inner inset keeps square
content inside the bigger curve.

Item 4 proof: on a tree striped by zebra_tree (now vivid), a
meaning FOREGROUND configured BEFORE striping (the app's pattern:
debtor red, attendance statuses) still renders in its meaning
colour over the vivid background -- verified in PIXELS.
Skips without a display. <200 lines."""
import tkinter as tk
from tkinter import ttk

from src.config.theme import RADIUS_TABLE
from src.ui import chart_status
from src.ui.dental_chart import DentalChartFrame
from src.ui.rounded import gradient_pil, rounded_pil
from src.ui.rounded_frame import RoundedFrame
from src.ui.zebra import zebra_tree
from src.utils.helpers import DECIDUOUS, PERMANENT

UP_P, LO_P = set(PERMANENT[:16]), set(PERMANENT[16:])
UP_D, LO_D = set(DECIDUOUS[:10]), set(DECIDUOUS[10:])


def _root():
    try:
        return tk.Tk()
    except tk.TclError:
        return None


class _Tab:
    """The clinical tab's field set + chart wiring, replicated."""

    def __init__(self, root):
        self.entry = tk.Entry(root)
        self.txt_complaint = tk.Text(root, height=2)
        self.txt_sym = tk.Text(root, height=2)
        self.txt_diagnosis = tk.Text(root, height=2)
        self.txt_procedure = tk.Text(root, height=2)

    def on_select(self, teeth, _typ):  # clinical._on_chart_select
        self.entry.delete(0, tk.END)
        self.entry.insert(0, ",".join(teeth))
        chart_status.insert_selected_teeth(self, teeth)

    def fields(self):
        return [w.get("1.0", tk.END).strip() for w in
                (self.txt_complaint, self.txt_sym,
                 self.txt_diagnosis, self.txt_procedure)]


def _press(chart, tab, scope):
    chart.jaw_buttons[scope].invoke()


def test_jaw_toggle_off_clears_numbers():
    root = _root()
    if root is None:
        print("SKIP r43 jaw (no display)"); return
    root.withdraw()
    try:
        tab = _Tab(root)
        chart = DentalChartFrame(root, lang="en", on_select=tab.on_select)
        chart.on_jaw_clear = lambda teeth: \
            chart_status.remove_teeth_from_fields(tab, teeth)
        root.update_idletasks()
        for typ, up, lo in (("دائم", UP_P, LO_P), ("لبني", UP_D, LO_D)):
            chart.tooth_type.set(typ); chart.refresh()
            for w in (tab.txt_complaint, tab.txt_sym,
                      tab.txt_diagnosis, tab.txt_procedure):
                w.delete("1.0", tk.END)  # clean slate per chart type
            _press(chart, tab, "upper")
            assert chart.selected == up, (typ, chart.selected)
            assert set(tab.entry.get().split(",")) == up
            for f in tab.fields():
                assert set(x.strip() for x in f.split(",")) == up, (typ, f)
            # Typed text around the numbers must survive the scrub.
            tab.txt_complaint.delete("1.0", tk.END)
            tab.txt_complaint.insert("1.0", "Severe pain in tooth, "
                                         + ", ".join(sorted(up)[:2]))
            _press(chart, tab, "upper")  # toggle OFF
            assert chart.selected == set(), typ
            assert tab.entry.get() == ""
            fields = tab.fields()
            assert fields[0] == "Severe pain in tooth", fields
            assert fields[1:] == ["", "", ""], fields
            # Different button switches the set; All toggles off too.
            _press(chart, tab, "lower")
            assert chart.selected == lo
            _press(chart, tab, "all")
            assert chart.selected == up | lo
            _press(chart, tab, "all")
            assert chart.selected == set()
            fields = tab.fields()  # numbers gone; TYPED text survives
            assert fields[0] == "Severe pain in tooth", fields
            assert fields[1:] == ["", "", ""], fields
    finally:
        root.destroy()


def test_radius24_antialiased_corners():
    assert RADIUS_TABLE == 24, RADIUS_TABLE  # owner: MORE rounded
    for img in (rounded_pil(300, 160, 24, "#E8DCC4", "#D9C39A"),
                gradient_pil(300, 160, 24)):
        corner = img.crop((0, 0, 28, 28))
        partial = sum(1 for p in corner.getdata() if 0 < p[3] < 255)
        assert partial > 20, partial  # was ZERO before the R43 fix
    root = _root()
    if root is None:
        print("SKIP r43 pad (no display)"); return
    root.withdraw()
    try:
        f24 = RoundedFrame(root, bg="#FFFFFF", radius=24)
        assert int(f24.inner.pack_info()["padx"]) >= 9
        f16 = RoundedFrame(root, bg="#FFFFFF", radius=16)
        assert int(f16.inner.pack_info()["padx"]) == 6  # unchanged
    finally:
        root.destroy()


def test_vivid_meaning_foreground_survives_pixels():
    root = _root()
    if root is None:
        print("SKIP r43 pixels (no display)"); return
    try:
        root.deiconify(); root.geometry("420x200+0+0")
        tree = ttk.Treeview(root, columns=("n",), show="headings")
        tree.heading("n", text="Name")
        tree.pack(fill="both", expand=True)
        # The app's pattern: meaning tag configured BEFORE striping.
        tree.tag_configure("debt", foreground="#C81E1E",
                           font=("Segoe UI", 9, "bold"))
        kids = []
        for i in range(6):
            kids.append(tree.insert("", "end", values=(f"Patient {i}",),
                                    tags=("debt",) if i == 0 else ()))
        zebra_tree(tree)  # R43: vivid rotation via delegation
        root.update_idletasks(); root.update()
        from PIL import ImageGrab
        x, y = tree.winfo_rootx(), tree.winfo_rooty()
        shot = ImageGrab.grab(bbox=(x, y, x + tree.winfo_width(),
                                    y + tree.winfo_height())).convert("RGB")
        def _has_reddish(img):
            return any(r > 140 and r > g + 50 and r > b + 50
                       for r, g, b in img.getdata())
        def _has_vivid(img):
            from src.ui.vivid_rows import PALETTE
            px = {tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
                  for c in PALETTE}
            return any(p in px for p in img.getdata())
        # The debtor row is row 0 = vivid SKY (no red in its bg, so
        # reddish pixels can only be the red meaning foreground).
        bx, by, bw, bh = tree.bbox(kids[0])
        row0 = shot.crop((bx, by, bx + bw, by + bh))
        assert _has_reddish(row0), "debtor red text lost over vivid bg"
        assert _has_vivid(shot), "vivid row backgrounds not rendered"
    finally:
        root.destroy()
