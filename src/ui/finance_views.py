"""Finance tab builders: lock prompt, expenses/lab/debts tabs, and the
role overlays (doctor own-income / nurse no-access). Kept separate so
src/ui/finance.py stays <200 lines. Builders set attributes on `tab`."""
import tkinter as tk
from datetime import date
from src.config.theme import finance_current
from src.config.strings import t
from src.ui.finance_records import build_record_buttons; from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame; from src.ui.rounded_widgets import RoundedEntry; from src.ui.rounded_lists import rounded_tree; from src.ui.zebra import zebra_tree; from src.ui.expense_icons import ExpenseIconPicker; from src.ui.currency_picker import CurrencyPicker  # R25 item 5


def _L(tab):
    """Active language of the tab (set by FinanceTab at build time)."""
    return getattr(tab, "lang", None) or getattr(getattr(tab, "app", None), "lang", "en") or "en"


def recolour_tab_frame(frame, th):
    """Repaint a tab frame built with the global theme (e.g. Salaries,
    built by salaries_view.py) onto the darker finance surfaces: every
    tk Frame/Label takes the finance panel, accent buttons take the
    finance accent + button text. ttk widgets (entries, trees) keep
    their style, which already uses the finance Treeview style."""
    if isinstance(frame, tk.Frame):
        frame.config(bg=th["panel"])
    for w in frame.winfo_children():
        recolour_tab_frame(w, th)
        if isinstance(w, tk.Frame):
            w.config(bg=th["panel"])
        elif isinstance(w, tk.Label):
            w.config(bg=th["panel"])
        elif isinstance(w, tk.Button):
            w.config(bg=th["accent"], fg=th["btn_text"])


def build_lock_view(tab, th):
    """Re-auth prompt overlay: covers the whole tab until unlocked."""
    tab._lock = tk.Frame(tab, bg=th["bg"])
    box = RoundedFrame(tab._lock, bg=th["panel"], border=th["border"])
    box.pack(expand=True, pady=60); box = box.inner
    tk.Label(box, text=t("fin.lock_title", _L(tab)), bg=th["panel"], fg=th["accent"],
             font=("Segoe UI", 12, "bold")).pack(padx=30, pady=(16, 4))
    tk.Label(box, text=t("fin.lock_sub", _L(tab)),
             bg=th["panel"], fg=th["muted"]).pack(padx=30, pady=4)
    tk.Label(box, text=t("fin.username", _L(tab)), bg=th["panel"], fg=th["text"]).pack(anchor="w", padx=30)
    tab.e_gate_user = RoundedEntry(box, width=24); tab.e_gate_user.pack(padx=30, pady=2)
    tk.Label(box, text=t("fin.password", _L(tab)), bg=th["panel"], fg=th["text"]).pack(anchor="w", padx=30)
    tab.e_gate_pass = RoundedEntry(box, width=24, show="*"); tab.e_gate_pass.pack(padx=30, pady=2)
    tab.e_gate_pass.bind("<Return>", lambda e: tab._try_unlock())
    tab.lbl_gate_err = tk.Label(box, text="", bg=th["panel"], fg=th["danger"]); tab.lbl_gate_err.pack(padx=30)
    tab.lbl_gate_auto = tk.Label(box, text="", bg=th["panel"], fg=th["muted"]); tab.lbl_gate_auto.pack(padx=30)
    rounded_button(box, text=t("fin.unlock", _L(tab)), bg=th["accent"], fg=th["btn_text"], relief="flat",
              command=tab._try_unlock).pack(pady=12)


def build_expenses_tab(nb, tab):
    from tkinter import ttk
    th = finance_current()
    f = tk.Frame(nb, bg=th["panel"]); nb.add(f, text=t("fin.tab_expenses", _L(tab)))
    frm = RoundedFrame(f, bg=th["panel"], border=th["border"]); frm.pack(fill="x", padx=6, pady=6); frm = frm.inner
    tab.e_exp_date = RoundedEntry(frm, width=12); tab.e_exp_date.grid(row=0, column=1, padx=4); tab.e_exp_date.insert(0, date.today().isoformat())
    tk.Label(frm, text=t("fin.exp_date", _L(tab)), bg=th["panel"], fg=th["text"]).grid(row=0, column=0)
    tab.e_exp_desc = RoundedEntry(frm, width=20); tab.e_exp_desc.grid(row=0, column=5, padx=4)
    tab.e_exp_amt = RoundedEntry(frm, width=10); tab.e_exp_amt.grid(row=0, column=7, padx=4)
    rounded_button(frm, text=t("fin.add", _L(tab)), bg=th["accent"], fg=th["btn_text"], relief="flat", command=tab.add_exp).grid(row=0, column=8, padx=6)
    # R24 item 5: category is an icon picker on its own row (the form
    # row is crowded); .get()/.set() keep the combobox contract, so
    # FinanceTab.add_exp() works unchanged and stores English literals.
    tk.Label(frm, text=t("fin.exp_category", _L(tab)), bg=th["panel"], fg=th["text"]).grid(row=1, column=0, pady=(4, 0))
    tab.e_exp_cat = ExpenseIconPicker(frm, lang=_L(tab), th=th); tab.e_exp_cat.grid(row=1, column=1, columnspan=8, sticky="ew", padx=4, pady=(4, 0))
    tab.tree_exp = rounded_tree(f, columns=("date", "cat", "desc", "amount"), style=tab._tv, pack={"fill": "both", "expand": True, "padx": 6, "pady": 4})
    for c in ("date", "cat", "desc", "amount"):
        tab.tree_exp.heading(c, text=t(f"fin.exp_col_{c}", _L(tab)))
    build_record_buttons(tab, f, tab.tree_exp, "expense")  # Job 9: 24h-rule edit/delete


def build_lab_tab(nb, tab):
    from tkinter import ttk
    th = finance_current()
    f = tk.Frame(nb, bg=th["panel"]); nb.add(f, text=t("fin.tab_lab", _L(tab)))
    frm = RoundedFrame(f, bg=th["panel"], border=th["border"]); frm.pack(fill="x", padx=6, pady=6); frm = frm.inner
    tab.e_lab_date = RoundedEntry(frm, width=12); tab.e_lab_date.grid(row=0, column=1, padx=4); tab.e_lab_date.insert(0, date.today().isoformat())
    tab.e_lab_name = RoundedEntry(frm, width=14); tab.e_lab_name.grid(row=0, column=3, padx=4); tab.e_lab_name.insert(0, "Dental Lab")
    tab.e_lab_cost = RoundedEntry(frm, width=10); tab.e_lab_cost.grid(row=0, column=5, padx=4)
    tab.e_lab_desc = RoundedEntry(frm, width=18); tab.e_lab_desc.grid(row=0, column=7, padx=4)
    rounded_button(frm, text=t("fin.add", _L(tab)), bg="#5E5CE6", fg="#FFFFFF", relief="flat", command=tab.add_lab).grid(row=0, column=8, padx=6)
    tab.tree_lab = rounded_tree(f, columns=("date", "lab", "desc", "cost"), style=tab._tv, pack={"fill": "both", "expand": True, "padx": 6, "pady": 4})
    for c in ("date", "lab", "desc", "cost"):
        tab.tree_lab.heading(c, text=t(f"fin.lab_col_{c}", _L(tab)))
    build_record_buttons(tab, f, tab.tree_lab, "lab")  # Job 9: 24h-rule edit/delete


def build_debts_tab(nb, tab):
    from tkinter import ttk
    th = finance_current()
    f = tk.Frame(nb, bg=th["panel"]); nb.add(f, text=t("fin.tab_debts", _L(tab)))
    tab.tree_debt = rounded_tree(f, columns=("file", "name", "total", "paid", "remain"), style=tab._tv, pack={"fill": "both", "expand": True, "padx": 6, "pady": 4})
    for c, h in [("file", t("fin.debt_col_file", _L(tab))), ("name", t("fin.debt_col_patient", _L(tab))), ("total", t("fin.debt_col_total", _L(tab))), ("paid", t("fin.debt_col_paid", _L(tab))), ("remain", t("fin.debt_col_remaining", _L(tab)))]:
        tab.tree_debt.heading(c, text=h)


def build_centers_tab(nb, tab):
    """Admin-only per-center breakdown (synced centers included).
    Standalone (no synced data) it lists just the local center."""
    from tkinter import ttk
    th = finance_current()
    f = tk.Frame(nb, bg=th["panel"]); nb.add(f, text=t("fin.tab_centers", _L(tab)))
    tk.Label(f, text=t("fin.centers_note", _L(tab)),
             bg=th["panel"], fg=th["muted"]).pack(anchor="w", padx=6, pady=4)
    tab.tree_centers = rounded_tree(f, columns=("center", "income", "expenses", "salaries", "lab", "debts", "net"), style=tab._tv, pack={"fill": "both", "expand": True, "padx": 6, "pady": 4})
    for c, h in [("center", t("fin.center_col_center", _L(tab))), ("income", t("fin.center_col_income", _L(tab))), ("expenses", t("fin.center_col_expenses", _L(tab))), ("salaries", t("fin.center_col_salaries", _L(tab))), ("lab", t("fin.center_col_lab", _L(tab))), ("debts", t("fin.center_col_debts", _L(tab))), ("net", t("fin.center_col_net", _L(tab)))]:
        tab.tree_centers.heading(c, text=h)
    # Explicit widths: Tk defaults to 200px/column, so 7 columns (=1400px)
    # clipped Debts + Net off the right edge at 1380px window width.
    for c, w in [("center", 120), ("income", 130), ("expenses", 130), ("salaries", 120), ("lab", 120), ("debts", 130), ("net", 130)]:
        tab.tree_centers.column(c, width=w)


def refresh_centers_tab(tab):
    """Refill the centers tree from per_center_totals (current period)."""
    from src.models.finance import per_center_totals
    try: rows = per_center_totals(tab.e_from.get().strip(), tab.e_to.get().strip())
    except Exception: rows = per_center_totals()
    for i in tab.tree_centers.get_children(): tab.tree_centers.delete(i)
    for r in rows:
        tab.tree_centers.insert("", "end", values=(r["center_id"], f"{r['income']:.2f}", f"{r['expenses']:.2f}", f"{r['salaries']:.2f}", f"{r['lab']:.2f}", f"{r['debts']:.2f}", f"{r['net']:.2f}"))
    zebra_tree(tab.tree_centers)  # R21 item 6


def build_doctor_view(tab, th):
    """Doctor overlay after unlock: ONLY their own income (day / month /
    chosen period). No center totals, no expenses/lab/debts, no names."""
    f = tk.Frame(tab, bg=th["bg"])
    box = RoundedFrame(f, bg=th["panel"], border=th["border"])
    box.pack(fill="x", padx=20, pady=20); box = box.inner
    tk.Label(box, text=t("fin.doc_title", _L(tab)), bg=th["panel"], fg=th["accent"],
             font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
    tk.Label(box, text=t("fin.doc_note", _L(tab)),
             bg=th["panel"], fg=th["muted"], justify="left").pack(anchor="w", padx=16, pady=2)
    tk.Label(box, text=t("fintot.doctor_note", _L(tab)),
             bg=th["panel"], fg=th["muted"], justify="left").pack(anchor="w", padx=16, pady=2)
    row = tk.Frame(box, bg=th["panel"]); row.pack(fill="x", padx=16, pady=8)
    tk.Label(row, text=t("fin.from", _L(tab)), bg=th["panel"], fg=th["text"]).pack(side="left")
    tab._doc_from = RoundedEntry(row, width=12); tab._doc_from.pack(side="left", padx=4)
    tab._doc_from.insert(0, date.today().replace(day=1).isoformat())
    tk.Label(row, text=t("fin.to", _L(tab)), bg=th["panel"], fg=th["text"]).pack(side="left", padx=4)
    tab._doc_to = RoundedEntry(row, width=12); tab._doc_to.pack(side="left", padx=4)
    tab._doc_to.insert(0, date.today().isoformat())
    rounded_button(row, text=t("fin.doc_calc", _L(tab)), bg=th["accent"], fg=th["btn_text"],
              relief="flat", command=tab._calc_doctor).pack(side="left", padx=8)
    # R19-E: the doctor view respects the same currency selector
    # (own combobox, SAME variable as the admin selector row).
    crow = tk.Frame(box, bg=th["panel"]); crow.pack(fill="x", padx=16, pady=4)
    tk.Label(crow, text=t("fincur.selector_label", _L(tab)), bg=th["panel"], fg=th["text"]).pack(side="left")
    # R25 item 5: searchable CurrencyPicker on the SAME variable
    # (was a readonly RoundedCombobox -- typing was impossible).
    tab.cb_doc_cur = CurrencyPicker(crow, textvariable=getattr(tab, "cur_var", None),
                                    values=getattr(tab, "_cur_displays", []), width=18, lang=_L(tab))
    tab.cb_doc_cur.pack(side="left", padx=4)
    tab.cb_doc_cur.bind("<<ComboboxSelected>>", lambda e: tab._calc_doctor())
    for key, label in (("_doc_total", t("fin.doc_total", _L(tab))), ("_doc_paid", t("fin.doc_paid", _L(tab))), ("_doc_rem", t("fin.doc_remaining", _L(tab)))):
        r = tk.Frame(box, bg=th["panel"]); r.pack(fill="x", padx=16, pady=2)
        tk.Label(r, text=label, bg=th["panel"], fg=th["muted"], width=20, anchor="w").pack(side="left")
        lbl = tk.Label(r, text="0.00", bg=th["panel"], fg=th["accent"], font=("Segoe UI", 12, "bold"))
        lbl.pack(side="left"); setattr(tab, key, lbl)
    tab._doc_view = f


def build_nurse_view(tab, th):
    """Nurse overlay after unlock: NO finance access at all (she records
    payments in the patient file, but sees no income totals)."""
    f = tk.Frame(tab, bg=th["bg"])
    box = RoundedFrame(f, bg=th["panel"], border=th["border"])
    box.pack(fill="x", padx=20, pady=40); box = box.inner
    tk.Label(box, text=t("fin.nurse_title", _L(tab)), bg=th["panel"],
             fg=th["accent"], font=("Segoe UI", 12, "bold")).pack(padx=30, pady=(16, 4))
    tk.Label(box, text=t("fin.nurse_note", _L(tab)),
             bg=th["panel"], fg=th["muted"], justify="left").pack(padx=30, pady=8)
    tab._nurse_view = f
