"""Finance view helpers (Round 12, Job 9): flexible-totals toggles,
15-minute auto-lock wiring, expense/lab edit+delete (admin-only).
Kept out of finance.py so it stays under 200 lines."""
import tkinter as tk
from tkinter import messagebox, simpledialog
from src.config.strings import t
from src.config.theme import finance_current; from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame
from src.models.finance_records import (get_expense, get_lab_cost, delete_expense,
    delete_lab_cost, update_expense_amount, update_lab_cost, may_change_record)


def _L(tab):
    return getattr(tab, "lang", None) or getattr(getattr(tab, "app", None), "lang", "en") or "en"


def _who(tab):
    """(role, username) of whoever unlocked the finance gate."""
    role = getattr(tab, "_gate_role", None) or tab._role()
    user = getattr(tab, "_gate_user", None) or getattr(tab.app, "current_user", "") or ""
    return role, user


# --- Flexible totals toggles (Job 9a) -------------------------------------

def build_totals_toggles(tab, th):
    """Row of Lab / Salaries / Expenses checkboxes above the cards.
    Each toggle re-computes the totals (tab.calc) and resets the
    auto-lock timer. The doctor overlay covers this row for doctors,
    so only the admin (full scope) ever reaches the toggles."""
    fr = RoundedFrame(tab, bg=th["panel"], border=th["border"])
    fr.pack(fill="x", padx=10, pady=4); fr = fr.inner
    tab.tot_lab_var = tk.BooleanVar(value=True)
    tab.tot_sal_var = tk.BooleanVar(value=True)
    tab.tot_exp_var = tk.BooleanVar(value=True)
    for var, key in ((tab.tot_lab_var, "fintot.lab"), (tab.tot_sal_var, "fintot.salaries"), (tab.tot_exp_var, "fintot.expenses")):
        tk.Checkbutton(fr, text=t(key, _L(tab)), variable=var, bg=th["panel"], fg=th["text"],
                       selectcolor=th["panel"], command=lambda: _on_toggle(tab)).pack(side="left", padx=8)
    tab.lbl_tot_included = tk.Label(fr, text="", bg=th["panel"], fg=th["muted"])
    tab.lbl_tot_included.pack(side="left", padx=8)


def _on_toggle(tab):
    tab.gate.touch(); tab.calc()  # changing a toggle is finance activity


def totals_selection(tab):
    """(include_lab, include_salaries, include_expenses) from toggles."""
    return (bool(getattr(tab, "tot_lab_var", None) and tab.tot_lab_var.get()),
            bool(getattr(tab, "tot_sal_var", None) and tab.tot_sal_var.get()),
            bool(getattr(tab, "tot_exp_var", None) and tab.tot_exp_var.get()))


# --- 15-minute auto-lock (Job 9b) -----------------------------------------

def hide_finance_numbers(tab):
    """Clear EVERY finance number from the view (cards, USD line,
    doctor labels, all trees) so a locked tab leaks nothing."""
    for lbl in getattr(tab, "cards", {}).values():
        lbl.config(text="—")
    if hasattr(tab, "lbl_usd"):
        tab.lbl_usd.config(text="")
    for key in ("_doc_total", "_doc_paid", "_doc_rem"):
        if hasattr(tab, key): getattr(tab, key).config(text="—")
    for key in ("tree_exp", "tree_lab", "tree_debt", "tree_centers"):
        tr = getattr(tab, key, None)
        if tr is not None: [tr.delete(i) for i in tr.get_children()]


def check_auto_lock(tab):
    """If the gate timed out, hide the numbers and show the password prompt again. True when the lock engaged here."""
    if tab.gate.is_unlocked:
        return False
    if hasattr(tab, "_lock") and tab._lock.winfo_ismapped():
        return False  # lock prompt already showing
    hide_finance_numbers(tab)
    if hasattr(tab, "_show_lock"): tab._show_lock()  # clears lbl_gate_auto: set the note AFTER it
    if hasattr(tab, "lbl_gate_auto"): tab.lbl_gate_auto.config(text=t("finlock.auto", _L(tab)))
    return True


def wire_auto_lock(tab, interval_ms=5000):
    """Poll the gate every `interval_ms`; engaging the lock hides the numbers and re-shows the prompt. The pending tick is cancelled when the tab is destroyed, so no stale callback fires after the root is gone (that printed 'invalid command name ..._tick' noise in the gate)."""
    state = {"id": None}
    def _tick():
        try: check_auto_lock(tab)
        except tk.TclError: return
        try: state["id"] = tab.after(interval_ms, _tick)
        except tk.TclError: pass
    def _cancel(event):
        if event.widget is tab and state["id"]:
            try: tab.after_cancel(state["id"])
            except tk.TclError: pass
    tab.bind("<Destroy>", _cancel, add="+")
    state["id"] = tab.after(interval_ms, _tick)


# --- Expense / lab edit + delete (admin-only) ---------------------------

def _selected_row(tab, tree, kind):
    sel = tree.selection()
    if not sel:
        return None, None
    rid = sel[0]
    try:
        row_id = int(tree.item(rid, "text") or rid)
    except (TypeError, ValueError):
        return None, None
    get = get_expense if kind == "expense" else get_lab_cost
    return row_id, get(row_id)


def _set_status(tab, kind, key):
    lbl = getattr(tab, f"lbl_{kind}_status", None)
    if lbl is not None: lbl.config(text=t(key, _L(tab)) if key else "")


def refresh_record_buttons(tab, tree, kind):
    """Enable Edit/Delete only for rows the user may change (admin
    only); otherwise disable them and show the bilingual reason."""
    btn_e = getattr(tab, f"btn_{kind}_edit", None)
    btn_d = getattr(tab, f"btn_{kind}_del", None)
    if btn_e is None:
        return
    _rid, row = _selected_row(tab, tree, kind)
    if row is None:
        btn_e.config(state="disabled"); btn_d.config(state="disabled")
        _set_status(tab, kind, "fintot.select_first")
        return
    role, user = _who(tab)
    created = row.get("created_at") or row.get("date")
    if may_change_record(role, created, user):
        btn_e.config(state="normal"); btn_d.config(state="normal")
        _set_status(tab, kind, "")
    else:
        btn_e.config(state="disabled"); btn_d.config(state="disabled")
        _set_status(tab, kind, "fintot.admin_only")


def _guarded(tab, tree, kind):
    """(row_id, row, role, user) when the selection may be changed,
    else None (and the buttons/status are refreshed to explain why)."""
    row_id, row = _selected_row(tab, tree, kind)
    if row is None:
        return None
    role, user = _who(tab)
    if not may_change_record(role, row.get("created_at") or row.get("date"), user):
        refresh_record_buttons(tab, tree, kind)
        return None
    return row_id, row, role, user


def edit_selected(tab, tree, kind):
    tab.gate.touch()
    g = _guarded(tab, tree, kind)
    if g is None:
        return
    row_id, row, role, user = g
    old = row.get("amount") if kind == "expense" else row.get("cost")
    new = simpledialog.askfloat(t("fintot.edit", _L(tab)), t("fintot.new_amount", _L(tab)), initialvalue=float(old or 0))
    if new is None:
        return
    fn = update_expense_amount if kind == "expense" else update_lab_cost
    if fn(row_id, new, role, user):
        tab.load(); tab.calc(); _set_status(tab, kind, "fintot.updated")


def delete_selected(tab, tree, kind):
    tab.gate.touch()
    g = _guarded(tab, tree, kind)
    if g is None:
        return
    row_id, row, role, user = g
    if not messagebox.askyesno(t("fintot.delete", _L(tab)), t("fintot.delete_confirm", _L(tab))):
        return
    fn = delete_expense if kind == "expense" else delete_lab_cost
    if fn(row_id, role, user):
        tab.load(); tab.calc(); _set_status(tab, kind, "fintot.deleted")


def refresh_all_record_buttons(tab):
    """Re-evaluate Edit/Delete state for both finance trees (e.g. after load() cleared the selection)."""
    if hasattr(tab, "tree_exp"): refresh_record_buttons(tab, tab.tree_exp, "expense")
    if hasattr(tab, "tree_lab"): refresh_record_buttons(tab, tab.tree_lab, "lab")


def build_record_buttons(tab, parent, tree, kind):
    """Edit/Delete row under a finance tree; state follows selection.
    Explicit hex colours: the finance contrast audit requires every
    rendered Button/Label to carry a #rrggbb fg/bg at >= 4.5:1."""
    th = finance_current()
    th_bg = parent.cget("bg")
    fr = RoundedFrame(parent, bg=th_bg, border=th["border"])
    fr.pack(fill="x", padx=6, pady=4); fr = fr.inner
    be = rounded_button(fr, text=t("fintot.edit", _L(tab)), state="disabled", bg=th["accent"], fg=th["btn_text"], relief="flat", command=lambda: edit_selected(tab, tree, kind)); be.pack(side="left", padx=2)
    bd = rounded_button(fr, text=t("fintot.delete", _L(tab)), state="disabled", bg="#B91C1C", fg="#FFFFFF", relief="flat", command=lambda: delete_selected(tab, tree, kind)); bd.pack(side="left", padx=2)
    lbl = tk.Label(fr, text=t("fintot.select_first", _L(tab)), bg=th_bg, fg=th["muted"])
    lbl.pack(side="left", padx=8)
    setattr(tab, f"btn_{kind}_edit", be); setattr(tab, f"btn_{kind}_del", bd); setattr(tab, f"lbl_{kind}_status", lbl)
    tree.bind("<<TreeviewSelect>>", lambda e: refresh_record_buttons(tab, tree, kind))
