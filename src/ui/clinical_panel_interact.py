"""Round 16 item 14: right-panel interactivity.

- Click a panel header to expand / collapse that panel (the body is
  hidden, the header gains a ▸/▾ marker; the state survives panel
  refreshes, which only rewrite the body text).
- Click a payment / prescription row to open its detail dialog.
  Panel bodies show one line per record, so the clicked line number
  maps 1:1 onto tab._panel_rows (set by clinical_panels.
  refresh_panels); empty states and the Health panel have no rows
  and do nothing on click. The bodies are disabled read-only Text
  widgets, but widget-level <Button-1> bindings still fire on them.
"""
import tkinter as tk
from tkinter import messagebox

from src.config.strings_r16_clinical import r16_t
from src.models.prescriptions import get_prescription_items
from src.ui.clinical_table_style import r15_t

CLICKABLE = ("payments", "rx")


def attach_panel_interactions(tab):
    """Wire header collapse + row-click detail onto built panels."""
    tab._panel_collapsed = {}
    tab._panel_titles = {}
    tab._panel_headers = {}
    for key in ("meds", "payments", "procedures", "rx"):
        frm = (getattr(tab, "panel_frames", {}) or {}).get(key)
        body = (getattr(tab, "panel_texts", {}) or {}).get(key)
        if frm is None or body is None:
            continue
        hdr = next((w for w in frm.inner.winfo_children()
                    if isinstance(w, tk.Frame)), None)
        if hdr is None:
            continue
        lbl = next((w for w in hdr.winfo_children()
                    if isinstance(w, tk.Label)), None)
        if lbl is None:
            continue
        tab._panel_titles[key] = lbl.cget("text")
        tab._panel_headers[key] = lbl
        tab._panel_collapsed[key] = False
        lbl.config(text=f"▾ {tab._panel_titles[key]}")
        for w in (hdr, lbl):
            w.bind("<Button-1>",
                   lambda _e, k=key: toggle_panel(tab, k), add="+")
        if key in CLICKABLE:
            body.bind("<Button-1>",
                      lambda e, k=key: _show_detail(tab, k, e), add="+")


def toggle_panel(tab, key):
    """Collapse / expand one panel body; the header marker follows."""
    body = (getattr(tab, "panel_texts", {}) or {}).get(key)
    lbl = (getattr(tab, "_panel_headers", {}) or {}).get(key)
    if body is None or lbl is None:
        return
    collapsed = not tab._panel_collapsed.get(key, False)
    tab._panel_collapsed[key] = collapsed
    if collapsed:
        body.pack_forget()
    else:
        body.pack(fill="x", padx=6, pady=4)
    mark = "▸" if collapsed else "▾"
    lbl.config(text=f"{mark} {tab._panel_titles[key]}")


def _show_detail(tab, key, event):
    rows = (getattr(tab, "_panel_rows", {}) or {}).get(key) or []
    if not rows:
        return
    body = tab.panel_texts[key]
    try:
        line = int(body.index(f"@{event.x},{event.y}").split(".")[0])
    except Exception:
        return
    if line < 1 or line > len(rows):
        return
    row = rows[line - 1]
    lang = getattr(tab.app, "lang", "en")
    if key == "payments":
        _show_payment_detail(row, lang)
    else:
        _show_rx_detail(row, lang)


def _show_payment_detail(row, lang):
    what = (r15_t("r15.panels.tooth_fmt", lang).format(teeth=row["tooth"])
            if row["tooth"] else r15_t("r15.panels.visit", lang))
    text = r16_t("r16.panels.payment_detail_fmt", lang).format(
        date=row["date"] or "—", what=what,
        paid=f"{row['paid']:g}", total=f"{row['total']:g}")
    messagebox.showinfo(r16_t("r16.panels.payment_detail_title", lang), text)


def _show_rx_detail(row, lang):
    items = get_prescription_items(row["id"])
    drugs = "\n".join(
        r16_t("r16.panels.rx_drug_fmt", lang).format(
            drug=i.get("generic") or "", dose=i.get("dose") or "—",
            freq=i.get("frequency") or "—") for i in items)
    text = r16_t("r16.panels.rx_detail_fmt", lang).format(
        doctor=row["doctor"] or "—", date=row["date"] or "—",
        drugs=drugs or r15_t("r15.panels.none", lang))
    messagebox.showinfo(
        r16_t("r16.panels.rx_detail_title", lang).format(pid=row["id"]), text)
