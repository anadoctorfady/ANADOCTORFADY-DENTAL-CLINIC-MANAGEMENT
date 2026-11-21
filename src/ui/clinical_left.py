"""Clinical main-flow panel section + Add-image button.

History: rounds 19-21 built a LEFT patient column here (the four
coloured panels, the Rx print row, the Add-image button), first
inside the tab, then in the shell's far-left column. Round 22
(owner redesign) dissolves that column:

- The Recent Payments + Therapeutic Procedures panels are built
  by build_main_panels() into the tab's MAIN SCROLL FLOW, under
  the History section (the Health panel moved into the pinned
  header; the Rx summary panel is superseded by the full
  Prescriptions section in the shell's left column, which carries
  its OWN print row -- so the old duplicate "print most recent"
  row and its helpers are removed).
- The Add-image button (round 12 feature) is built by
  build_add_image() into the scroll flow, directly above the
  finance / x-ray / scans notebook it feeds.

scrollable_frame() also lives here (moved from clinical.py in
round 21 so clinical.py stays in budget). <200 lines."""
import tkinter as tk
from tkinter import ttk

from src.config.strings import t
from src.config.theme import current
from src.ui import clinical_panels as _panels
from src.ui.rounded import rounded_button
from src.ui.wheel_scroll import bind_canvas_wheel


def scrollable_frame(parent):
    """Vertical-scroll wrapper; returns the inner frame to pack
    content into."""
    th = current()
    canvas = tk.Canvas(parent, bg=th["bg"], highlightthickness=0)
    sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=th["bg"])
    wid = canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(wid, width=e.width))
    bind_canvas_wheel(canvas)
    return inner


def build_main_panels(tab, parent):
    """Build the Recent Payments + Therapeutic Procedures panels
    into the main scroll flow (round 22 order: after History,
    before the finance section). Sets tab.panels_section plus
    tab.panel_frames / tab.panel_texts (via clinical_panels)."""
    th = current()
    section = tk.Frame(parent, bg=th["bg"])
    section.pack(fill="x", pady=2)
    tab.panels_section = section
    _panels.build_panels(tab, section)
    return section


def build_add_image(tab, parent):
    """The Add-image button on its own row in the scroll flow,
    directly above the scans notebook (round 22 home; the Scans
    tab keeps its own big upload button too)."""
    th = current()
    lang = getattr(tab.app, "lang", "en")
    row = tk.Frame(parent, bg=th["bg"])
    row.pack(fill="x")
    tab.btn_add_image = rounded_button(
        row, text=t("scan_add_image", lang), bg=th["accent"],
        fg="white", command=tab.open_add_image)
    tab.btn_add_image.pack(anchor="w", padx=10, pady=6)
    return row
