"""Clinical history lists (round 18 item 6; round 23; round 24).
<200 lines. Round 24: the headed History section + Diagnosis /
Procedures notebook are SUPERSEDED by the unified clinical table
(clinical_session builds tab.history_section/tree_history);
build_history_section stays for legacy hosts. Live jobs here:
the bottom notebook (Financial / X-Rays / Scans), referrals, load()."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from pathlib import Path
import shutil
from src.config.strings import t
from src.config.strings_r18_clinical import r18_t
from src.config.theme import current, RADIUS_TABLE
from src.config.settings import XRAYS
from src.models.database import get_connection; from src.models.history_money import money_map
from src.ui.scans_tab import build_scans_section; from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame; from src.ui import clinical_referrals as _ref
from src.ui.vivid_rows import ensure_vivid_style, vivid_tree  # R40 item 2
from src.config.theme import is_dark; from src.ui.clinical_table_style import stack_color
from src.ui import clinical_edit as _edit; from src.ui import clinical_history as _hist; from src.ui import clinical_xray as _xray
from src.ui import clinical_payments_review as _review  # R38 zone 3
# R23: diag/proc trees gained Total/Paid/Remaining after their column.
TREES = [("tree_diag", "clinical.hist_diagnosis", ("date", "tooth", "diag", "total", "paid", "remain"), "diagnoses",
          ("visit_date", "tooth_number", "diagnosis")),
         ("tree_proc", "clinical.hist_procedures", ("date", "tooth", "proc", "total", "paid", "remain"), "procedures",
          ("visit_date", "tooth_number", "procedure_done")),
         ("tree_fin", "clinical.hist_financial", ("date", "amount", "doctor", "by", "balance", "kind", "currency"), "financials",
          ("visit_date", "paid_amount", "currency", "doctor", "entered_by"))]  # R38: tree_fin = the PAYMENTS REVIEW (clinical_payments_review)
COL_KEYS = {"date": "clinical.col_date", "tooth": "clinical.col_tooth",
            "diag": "clinical.col_diag", "proc": "clinical.col_proc",
            "total": "clinical.col_total", "paid": "clinical.col_paid",
            "remain": "clinical.col_remain"}
HIST_WIDTHS = {"date": 90, "tooth": 60, "diag": 460, "proc": 460, "total": 150, "paid": 150, "remain": 150}  # R17 widths
XRAY_COL_KEYS = {"date": "clinical.col_xray_date", "path": "clinical.col_path",
                 "desc": "clinical.col_desc"}
TOP_TREES = ("tree_diag", "tree_proc")  # the "what was done" trees
FIN_LIST_ROWS = 6  # R28 item 2: bounded visible rows of tree_fin

def _ensure_hist_state(tab):
    if not hasattr(tab, "_hist_rows"):
        tab._hist_rows = {}   # tree attr -> {iid: row dict}
    if not hasattr(tab, "_hist_btns"):
        tab._hist_btns = {}   # tree attr -> (edit, delete, status, refresh)

def _make_tree(tab, nb, spec):
    """One history tab (frame + rounded tree) in notebook `nb`."""
    attr, title_key, cols, tbl, _c = spec
    th = current()
    lang = getattr(tab.app, "lang", "en")
    f = tk.Frame(nb, bg=th["panel"])
    nb.add(f, text=_review.r38_t("pay.review_title", lang) if attr == "tree_fin" else t(title_key, lang))
    wrap = RoundedFrame(f, bg=th["panel"], border=th["border"], radius=RADIUS_TABLE)
    wrap.pack(fill="both", expand=True, padx=4, pady=4)
    if attr == "tree_fin":  # R38: current-balance summary atop the review
        tab.lbl_pay_summary = tk.Label(f, text="", bg=th["panel"], fg=th["text"], font=("Segoe UI", 9, "bold"), anchor="w")
        tab.lbl_pay_summary.pack(fill="x", padx=6, pady=(4, 0), before=wrap)
    tr = ttk.Treeview(wrap.inner, columns=cols, show="headings",
                      style=ensure_vivid_style() if attr == "tree_fin" else "Treeview")
    for c in cols:
        if attr == "tree_fin":
            tr.heading(c, text=_review.fin_heading(c, lang))
            tr.column(c, width=_review.FIN_WIDTHS.get(c, 110), minwidth=50, stretch=False)
            continue
        tr.heading(c, text=t(COL_KEYS[c], lang))
        tr.column(c, width=HIST_WIDTHS.get(c, 150), minwidth=50,
                  stretch=c not in ("date", "tooth"))
    if attr == "tree_fin":
        # R28 item 2: the payments list is BOUNDED (6 rows) with its
        # own vertical scrollbar + wheel -- a long payment history
        # scrolls INSIDE the section instead of stretching the page.
        tr.configure(height=FIN_LIST_ROWS)
        sb = ttk.Scrollbar(wrap.inner, orient="vertical", command=tr.yview)
        tr.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tr.pack(side="left", fill="both", expand=True)
        tr._v_scrollbar = sb
        def _fin_wheel(e, tr=tr):
            tr.yview_scroll(-1 if (getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0) else 1, "units")
            return "break"
        for _ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            tr.bind(_ev, _fin_wheel, add="+")
    else:
        tr.pack(fill="both", expand=True)
    setattr(tab, attr, tr)
    tab._hist_rows[attr] = {}
    if attr in TOP_TREES:
        _hist_buttons(tab, f, attr, tbl)
    return f

def build_history_section(tab, parent):
    """LEGACY (R24: superseded by clinical_session.build_unified):
    headed History section + Diagnosis / Procedures notebook."""
    th = current()
    lang = getattr(tab.app, "lang", "en")
    _ensure_hist_state(tab)
    section = tk.Frame(parent, bg=stack_color("history", is_dark()))  # R19 item 7: own colour
    section.pack(fill="x", pady=4)
    tab.history_section = section
    tk.Label(section, text=r18_t("r18.clinical.history_heading", lang),
             bg=stack_color("history", is_dark()), fg=th["accent"],
             font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=4,
                                                 pady=(2, 2))
    _hist.build_history_tree(tab, section)
    nb = ttk.Notebook(section)
    nb.pack(fill="both", expand=True)
    tab.history_top_nb = nb
    _ord = _hist.clinical_display_order(lang); _kind = {"tree_diag": "diagnosis", "tree_proc": "procedure"}
    for spec in sorted((s for s in TREES if s[0] in TOP_TREES),
                       key=lambda s: _ord.index(_kind[s[0]])):
        _make_tree(tab, nb, spec)
    return section

def build_notebook(tab, parent):
    """Bottom notebook: Financial tree, X-Rays, Scans (per patient)."""
    th = current()
    lang = getattr(tab.app, "lang", "en")
    _ensure_hist_state(tab)
    nb = ttk.Notebook(parent)
    nb.pack(fill="both", expand=True)
    tab.history_nb = nb
    for spec in TREES:
        if spec[0] not in TOP_TREES:
            _make_tree(tab, nb, spec)
    f4 = tk.Frame(nb, bg=th["panel"])
    nb.add(f4, text=t("clinical.hist_xrays", lang))
    _xray.build_xray_section(tab, f4)  # R27: thumbnail grid + viewer
    tab.scans_frame = None
    rebuild_scans(tab, tab.patient_id); _ref.build_referrals_section(tab, parent)

def _hist_buttons(tab, parent, attr, table):
    """LEGACY diag/proc Edit/Delete row (24h rule); R24 sessions
    use clinical_session_edit instead."""
    lang = getattr(tab.app, "lang", "en")
    th = current()
    bar = tk.Frame(parent, bg=th["panel"])
    bar.pack(fill="x", padx=4, pady=(0, 4))
    status = tk.Label(bar, text="", bg=th["panel"], fg="#991B1B",
                      font=("Segoe UI", 9))
    status.pack(side="right", padx=4)

    def _selected():
        tree = getattr(tab, attr)
        sel = tree.selection()
        return tab._hist_rows[attr].get(sel[0]) if sel else None

    def _refresh(_e=None):
        row = _selected()
        ok, reason = _edit.row_allowed(tab, row) if row else (False, None)
        btn_e.config(state="normal" if ok else "disabled")
        btn_d.config(state="normal" if ok else "disabled")
        status.config(text=reason or "")

    btn_e = rounded_button(bar, text=t("savegate.edit", lang), bg=th["card"], fg=th["text"],
                      state="disabled",
                      command=lambda: _edit.edit_history_row(
                          tab, table, _selected()))
    btn_e.pack(side="left", padx=2)
    btn_d = rounded_button(bar, text=t("savegate.delete", lang), bg=th["card"], fg=th["text"],
                      state="disabled",
                      command=lambda: _edit.delete_history_row(
                          tab, table, _selected()))
    btn_d.pack(side="left", padx=2)
    getattr(tab, attr).bind("<<TreeviewSelect>>", _refresh)
    tab._hist_btns[attr] = (btn_e, btn_d, status, _refresh)


def rebuild_scans(tab, patient_id):
    """Scans tab after X-Rays; rebuilt per load (captures patient id)."""
    if tab.scans_frame is not None:
        try:
            tab.history_nb.forget(tab.scans_frame)
            tab.scans_frame.destroy()
        except Exception:
            pass
    tab.scans_frame = build_scans_section(tab.history_nb, tab.app, patient_id,
                                          tab.current_user, tab.current_role)
    tab.history_nb.add(tab.scans_frame, text=t("clinical.hist_scans", getattr(tab.app, "lang", "en")))

def add_xray(tab):
    # R25 item 2: multi-file batch lives in clinical_xray (line limit).
    _xray.add_xrays(tab)

def load(tab, fid):
    """Reload the per-patient lists (R24: Financial + X-Ray trees,
    scans, referrals + the unified History; R40: the two money
    lists wear vivid rotating rows, the rest keep zebra)."""
    tab.patient_id = fid
    _ensure_hist_state(tab)
    _review.fill_review(tab, fid)  # R38: payments review (was: raw financials rows)
    _xray.refresh_xray_grid(tab, fid)  # R27: thumbnail grid, no tree
    rebuild_scans(tab, fid); _ref.refresh_referrals(tab, fid); _hist.refresh_history(tab, fid)
    [vivid_tree(getattr(tab, a)) for a in ("tree_fin",) if getattr(tab, a, None) is not None]  # R40: vivid rotation (was R21 zebra)
    try:  # selection is gone after a reload: session buttons off
        from src.ui.clinical_session_edit import sync_edit_buttons
        sync_edit_buttons(tab)
    except Exception:
        pass
