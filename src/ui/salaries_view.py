"""Salaries tab builders + form handlers for the Finance tab.
Admin-only: employees + monthly salary payments. Doctors/nurses never
see this (role overlays cover the whole tab after the gate). Split from
finance_views.py so it stays <200 lines. Builders set attributes on `tab`."""
import tkinter as tk
from datetime import date
from src.config.theme import current; from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame; from src.ui.rounded_widgets import RoundedEntry; from src.ui.rounded_lists import RoundedCombobox, rounded_tree; from src.ui.zebra import zebra_tree
from src.config.strings import t


def _L(tab):
    """Active language of the tab (set by FinanceTab at build time)."""
    return getattr(tab, "lang", None) or getattr(getattr(tab, "app", None), "lang", "en") or "en"


def _sal_role(tab):
    """Role of the user who unlocked the finance gate."""
    return tab._gate_role or tab._role()


def build_salaries_tab(nb, tab):
    """Admin-only: employees + monthly salary payments."""
    from tkinter import ttk
    f = tk.Frame(nb, bg=current()["panel"]); nb.add(f, text=t("fin.sal_tab", _L(tab)))
    frm = RoundedFrame(f, bg=current()["panel"], border=current()["border"]); frm.pack(fill="x", padx=6, pady=6); frm = frm.inner
    def _field(label, row, col, width=12, values=None):
        tk.Label(frm, text=label, bg=current()["panel"], fg=current()["text"]).grid(row=row, column=col)
        w = RoundedCombobox(frm, values=values, width=width) if values else RoundedEntry(frm, width=width)
        w.grid(row=row, column=col + 1, padx=4, pady=2)
        return w
    tab.e_emp_name = _field(t("fin.sal_name", _L(tab)), 0, 0, 16)
    tab.e_emp_job = _field(t("fin.sal_job", _L(tab)), 0, 2, 10, ["doctor", "nurse", "other"]); tab.e_emp_job.set("other")
    tab.e_emp_sal = _field(t("fin.sal_monthly", _L(tab)), 0, 4, 10)
    tab.e_emp_center = _field(t("fin.sal_center", _L(tab)), 0, 6, 10)
    tab.e_emp_phone = _field(t("fin.sal_phone", _L(tab)), 1, 0, 12)
    tab.e_emp_link = _field(t("fin.sal_login", _L(tab)), 1, 2, 12)
    rounded_button(frm, text=t("fin.sal_add_emp", _L(tab)), bg=current()["accent"], fg="white", relief="flat",
              command=lambda: add_employee_from_form(tab)).grid(row=1, column=5, padx=6)
    pay = RoundedFrame(f, bg=current()["panel"], border=current()["border"]); pay.pack(fill="x", padx=6, pady=4); pay = pay.inner
    tk.Label(pay, text=t("fin.sal_month", _L(tab)), bg=current()["panel"], fg=current()["text"]).pack(side="left")
    tab.e_sal_month = RoundedEntry(pay, width=10); tab.e_sal_month.pack(side="left", padx=4)
    tab.e_sal_month.insert(0, date.today().strftime("%Y-%m"))
    tab.cb_sal_emp = RoundedCombobox(pay, width=24); tab.cb_sal_emp.pack(side="left", padx=4)
    tk.Label(pay, text=t("fin.sal_amount", _L(tab)), bg=current()["panel"], fg=current()["text"]).pack(side="left")
    tab.e_sal_amt = RoundedEntry(pay, width=10); tab.e_sal_amt.pack(side="left", padx=4)
    rounded_button(pay, text=t("fin.sal_record", _L(tab)), bg=current()["accent"], fg="white", relief="flat",
              command=lambda: add_salary_payment_from_form(tab)).pack(side="left", padx=6)
    tab.tree_sal = rounded_tree(f, columns=("name", "job", "salary", "paid", "remaining", "center"), style=tab._tv, pack={"fill": "both", "expand": True, "padx": 6, "pady": 4})
    for c, h in [("name", t("fin.sal_col_employee", _L(tab))), ("job", t("fin.sal_col_job", _L(tab))), ("salary", t("fin.sal_col_salary", _L(tab))), ("paid", t("fin.sal_col_paid", _L(tab))), ("remaining", t("fin.sal_col_remaining", _L(tab))), ("center", t("fin.sal_col_center", _L(tab)))]:
        tab.tree_sal.heading(c, text=h)
    # Explicit widths: Tk defaults to 200px/column, so 6 columns (=1200px)
    # clipped the Center column off the right edge at 1380px window width.
    for c, w in [("name", 190), ("job", 90), ("salary", 130), ("paid", 130), ("remaining", 130), ("center", 130)]:
        tab.tree_sal.column(c, width=w)


def add_employee_from_form(tab):
    from tkinter import messagebox
    from src.models.database import get_connection, get_setting
    from src.models.salaries import add_employee
    try: sal = float(tab.e_emp_sal.get() or 0)
    except Exception: return messagebox.showerror(t("fin.err_title", _L(tab)), t("fin.sal_err_salary", _L(tab)))
    conn = get_connection()
    try:
        add_employee(conn, _sal_role(tab), tab.e_emp_name.get().strip(), tab.e_emp_job.get().strip() or "other", sal,
                     tab.e_emp_center.get().strip() or get_setting("sync_center_id", "main") or "main",
                     linked_username=tab.e_emp_link.get().strip() or None, phone=tab.e_emp_phone.get().strip() or None)
    except PermissionError: messagebox.showerror(t("fin.not_allowed_title", _L(tab)), t("fin.sal_not_allowed", _L(tab)))
    except Exception as e: messagebox.showerror(t("fin.err_title", _L(tab)), str(e))
    finally: conn.close()
    refresh_salaries_tab(tab)


def add_salary_payment_from_form(tab):
    from tkinter import messagebox
    from src.models.database import get_connection
    from src.models.salaries import record_salary_payment
    try:
        eid = int((tab.cb_sal_emp.get() or "").split(":")[0].strip())
        amt = float(tab.e_sal_amt.get() or 0)
    except Exception: return messagebox.showerror(t("fin.err_title", _L(tab)), t("fin.sal_err_pick", _L(tab)))
    conn = get_connection()
    try:
        record_salary_payment(conn, _sal_role(tab), eid, tab.e_sal_month.get().strip(),
                              amt, date.today().isoformat(), getattr(tab.app, "current_user", "") or "")
    except PermissionError: messagebox.showerror(t("fin.not_allowed_title", _L(tab)), t("fin.sal_not_allowed", _L(tab)))
    except Exception as e: messagebox.showerror(t("fin.err_title", _L(tab)), str(e))
    finally: conn.close()
    refresh_salaries_tab(tab)


def refresh_salaries_tab(tab):
    """Refill the salaries tree + employee picker for the chosen month."""
    from src.models.database import get_connection
    from src.models.salaries import month_summary
    month = tab.e_sal_month.get().strip() or date.today().strftime("%Y-%m")
    conn = get_connection()
    try: rows = month_summary(conn, _sal_role(tab), month)
    except PermissionError: rows = []
    finally: conn.close()
    for i in tab.tree_sal.get_children(): tab.tree_sal.delete(i)
    tab.cb_sal_emp["values"] = [f"{r['employee_id']}: {r['name']}" for r in rows]
    for r in rows:
        tab.tree_sal.insert("", "end", values=(r["name"], r["job_title"], f"{r['monthly_salary']:.2f}",
                             f"{r['paid']:.2f}", f"{r['remaining']:.2f}", r["center_id"]))
    zebra_tree(tab.tree_sal)  # R21 item 6
