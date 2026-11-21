"""Round 19 (item 11): referrals in the clinical history.

Kept in its own module so clinical_lists.py stays at its line
cap: clinical_lists.build_notebook() calls
build_referrals_section() once -- a headed "Referrals" section
packed right after the bottom history notebook (Financial /
X-Rays / Scans). A section, NOT a notebook tab: the round-18
layout tests pin both history notebooks' exact tab lists.
clinical_lists.load() calls refresh_referrals() per patient.
Rows are (date, to, from, note) in the app language only;
history_rows() is the pure display-data function the tree is
filled from (and what tests assert on). Round 24 (item 1):
tab._ref_rows maps iid -> the FULL referral dict (it held the
display tuple before round 24) so the section's Print button --
enabled only while a row is selected -- can print that referral
via the print preview. <200 lines.
"""
import tkinter as tk
from tkinter import ttk

from src.config.strings_r19_referral import tr
from src.config.theme import current, is_dark, RADIUS_TABLE
from src.models.referrals import list_referrals
from src.ui.clinical_table_style import stack_color; from src.ui.zebra import zebra_tree
from src.ui.rounded import rounded_button
from src.ui.rounded_frame import RoundedFrame

COLS = ("date", "to", "from", "note")
WIDTHS = {"date": 90, "to": 170, "from": 120, "note": 420}
COL_KEYS = {"date": "refer.col_date", "to": "refer.col_to",
            "from": "refer.col_from", "note": "refer.col_note"}


def history_rows(patient_id):
    """Display rows for one patient: [(date, to_doctor, from_user,
    note)] newest first; [] when no patient / no referrals."""
    out = []
    for r in list_referrals(patient_id):
        out.append(((r.get("created_at") or "")[:10],
                    r.get("to_doctor") or "",
                    r.get("from_user") or "",
                    r.get("note") or ""))
    return out


def build_referrals_section(tab, parent):
    """Headed Referrals section (heading + tree) packed into the
    clinical page `parent` after the history notebook; remembered
    as tab.tree_ref (+ tab._ref_rows by iid) and tab.ref_section."""
    th = current()
    lang = getattr(tab.app, "lang", "en")
    ref_bg = stack_color("referrals", is_dark())  # R19 item 7: own colour
    section = tk.Frame(parent, bg=ref_bg)
    section.pack(fill="x", pady=4)
    tab.ref_section = section
    tk.Label(section, text=tr("refer.hist_tab", lang),
             bg=ref_bg, fg=th["accent"],
             font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=4,
                                                 pady=(2, 2))
    wrap = RoundedFrame(section, bg=ref_bg, border=th["border"],
                        radius=RADIUS_TABLE)
    wrap.pack(fill="x", padx=4, pady=2)
    tree = ttk.Treeview(wrap.inner, columns=COLS, show="headings",
                        height=4)
    for c in COLS:
        tree.heading(c, text=tr(COL_KEYS[c], lang))
        tree.column(c, width=WIDTHS[c], minwidth=50,
                    stretch=(c == "note"))
    tree.pack(fill="both", expand=True)
    tab.tree_ref = tree
    tab._ref_rows = {}
    # Round 24 (item 1): Print button under the tree; enabled only
    # while a row is selected (state synced on selection + refresh).
    btn_row = tk.Frame(section, bg=ref_bg)
    btn_row.pack(fill="x", padx=4, pady=(0, 2))
    tab.btn_ref_print = rounded_button(
        btn_row, text=tr("refer.print_btn", lang), bg=th["card"],
        fg=th["text"], state="disabled",
        command=lambda: print_selected_referral(tab))
    tab.btn_ref_print.pack(side="left")
    tree.bind("<<TreeviewSelect>>",
              lambda _e: sync_ref_print(tab), add="+")
    return section


def selected_referral(tab):
    """The full referral dict of the selected tree row, or None."""
    tree = getattr(tab, "tree_ref", None)
    if tree is None:
        return None
    sel = tree.selection()
    if not sel:
        return None
    row = (getattr(tab, "_ref_rows", {}) or {}).get(sel[0])
    return row if isinstance(row, dict) else None


def sync_ref_print(tab):
    """Enable the section Print button iff a referral row with an
    id is selected; called on selection change and on refresh."""
    btn = getattr(tab, "btn_ref_print", None)
    if btn is None:
        return
    ref = selected_referral(tab)
    try:
        btn.config(state="normal" if ref and ref.get("id")
                   else "disabled")
    except Exception:
        pass


def print_selected_referral(tab):
    """Open the referral print preview for the selected row.
    Returns the preview window, or None when nothing is selected."""
    ref = selected_referral(tab)
    if not ref or not ref.get("id"):
        return None
    from src.reports.print_preview import open_referral_preview
    return open_referral_preview(tab.app, ref["id"], parent=tab)


def refresh_referrals(tab, fid):
    """Refill tab.tree_ref for patient `fid` (None clears it).
    No-op when the tab was never built."""
    tree = getattr(tab, "tree_ref", None)
    if tree is None:
        return
    for i in tree.get_children():
        tree.delete(i)
    tab._ref_rows = {}
    for idx, r in enumerate(list_referrals(fid) if fid else []):
        row = ((r.get("created_at") or "")[:10],
               r.get("to_doctor") or "", r.get("from_user") or "",
               r.get("note") or "")
        iid = tree.insert("", "end", iid=f"ref{idx}", values=row)
        tab._ref_rows[iid] = r  # R24: full dict (was the tuple)
    zebra_tree(tree)  # R21 item 6
    sync_ref_print(tab)  # R24: selection is gone after a refill
