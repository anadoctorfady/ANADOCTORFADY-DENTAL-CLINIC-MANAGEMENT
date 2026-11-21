"""Shell far-left column builder (round 21 item 2; round 22).

Builds the far-left column inside the shell's left frame, top to
bottom: quick search, "+ New Patient", the Advanced Search
panel, the patient list, and `app.rx_host` -- the frame the
clinical tab builds its Prescriptions section into (compose new
+ history + Print), so prescriptions live in this column too.

Round 22 (owner redesign): the Patient info panel and the
clinical panels host are GONE from this column -- the patient
personal info + Health lines + alert strips + Edit/Delete/Refer
moved into the clinical tab's PINNED HEADER (patient_info.py),
and the Recent Payments / Therapeutic Procedures panels moved
into the clinical tab's main scroll flow. This column keeps ONLY
search, the list, and prescriptions.

The whole column lives inside ONE vertically scrollable canvas
so the Rx section stays reachable at small window heights; the
patient list keeps a fixed, usable height (11 rows). Widget
construction mirrors the old inline shell code exactly (same
entry, button, headings). <200 lines."""
import tkinter as tk
from tkinter import ttk

from src.config.strings import t
from src.config.theme import current, RADIUS_TABLE
from src.ui.patient_search import AdvancedSearchPanel
from src.ui.rounded import rounded_button
from src.ui.rounded_frame import RoundedFrame
from src.ui.rounded_widgets import RoundedEntry
from src.ui.wheel_scroll import bind_canvas_wheel


def build_left_column(app, parent):
    """Build the column into `parent` (the shell left frame's
    inner frame); sets app.search_var / adv_search / tree /
    rx_host / left_canvas."""
    th = current()
    canvas = tk.Canvas(parent, bg=th["list_bg"], highlightthickness=0)
    sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=th["list_bg"])
    wid = canvas.create_window((0, 0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda _e: canvas.configure(
        scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(wid, width=e.width))
    bind_canvas_wheel(canvas)
    app.left_canvas = canvas
    app.left_inner = inner
    sf = tk.Frame(inner, bg=th["list_bg"]); sf.pack(fill="x", padx=8, pady=8)
    tk.Label(sf, text="🔍", bg=th["list_bg"], fg=th["text"]).pack(side="left")
    app.search_var = tk.StringVar()
    app.search_var.trace_add("write", lambda *a: app.load_patients())
    RoundedEntry(sf, textvariable=app.search_var,
                 font=("Segoe UI", 10)).pack(side="left", fill="x",
                                             expand=True, padx=6)
    bf = tk.Frame(inner, bg=th["list_bg"]); bf.pack(fill="x", padx=8)
    rounded_button(bf, text=t("shell.new_patient", app.lang), bg=th["accent"],
                   fg="white", font=("Segoe UI", 9, "bold"),
                   command=app.new_patient).pack(fill="x", pady=4)
    app.adv_search = AdvancedSearchPanel(inner, app, on_search=app.load_patients)
    app.adv_search.pack(fill="x", padx=8)
    tf = RoundedFrame(inner, bg=th["list_bg"], border=th["border"], radius=RADIUS_TABLE)
    tf.pack(fill="x", padx=8, pady=8)
    # The Paper.Treeview style's paper field image inflates the
    # tree's requested height (~550px); in the old fixed column the
    # expanding frame absorbed that, but in this scroll column the
    # frame height is capped so the list shows ~10 rows and the
    # rest of the column stays reachable without excessive scroll.
    tf.configure(height=300); tf.pack_propagate(False)
    app.tree = ttk.Treeview(tf.inner, columns=("file", "name", "mobile"),
                            show="headings", height=11, style="Paper.Treeview")
    app.tree.heading("file", text="#")
    app.tree.heading("name", text=t("shell.head_name", app.lang))
    app.tree.heading("mobile", text=t("shell.head_mobile", app.lang))
    app.tree.column("file", width=35, anchor="center")
    app.tree.column("name", width=215)
    app.tree.column("mobile", width=100)
    app.tree.pack(side="left", fill="both", expand=True)
    app.tree.bind("<<TreeviewSelect>>", lambda e: app._on_tree_select())  # R31: handler swallows select_patient()'s echo (see shell.py)
    # Round 22: the Prescriptions section (compose + history +
    # Print) is built by the Clinical tab into this host, directly
    # under the patient list; reachable by scrolling the column.
    host = tk.Frame(inner, bg=th["list_bg"]); host.pack(fill="x", padx=4)
    app.rx_host = host
    return inner
