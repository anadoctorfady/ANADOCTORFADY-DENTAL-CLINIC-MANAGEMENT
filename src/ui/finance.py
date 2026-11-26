"""Finance: expenses, lab, debts, net income. Role-scoped views (admin
full / doctor own-income only / nurse none). <200 lines."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from src.config.theme import finance_current, tree_style, notebook_style
from src.config.strings import t
from src.models.database import get_connection
from src.models.finance import debts_list, doctor_income, add_expense, add_lab_cost
from src.models.finance_totals import flexible_totals
from src.models.permissions import finance_scope, has_perm
from src.utils.auth import get_user_role
from src.utils.finance_gate import FinanceGate
from src.ui.finance_views import (build_lock_view, build_expenses_tab,
                                  build_lab_tab, build_debts_tab, build_centers_tab,
                                  refresh_centers_tab, recolour_tab_frame,
                                  build_doctor_view, build_nurse_view)
from src.ui.finance_records import (build_totals_toggles, wire_auto_lock,
                                    hide_finance_numbers, totals_selection,
                                    refresh_all_record_buttons)
from src.ui.salaries_view import build_salaries_tab, refresh_salaries_tab; from src.ui.finance_stats import build_stats_tab, refresh_stats_tab; from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame; from src.ui.rounded_widgets import RoundedEntry; from src.ui.finance_currency import build_currency_selector, admin_result, doctor_result, build_rate_row; from src.ui.zebra import zebra_tree; from src.ui.scroll_page import make_scroll_page
from src.models.currency import get_rate, save_rate, latest_rate, default_currency
class FinanceTab(tk.Frame):
    def __init__(self, parent, app, **kw):
        th = finance_current(); self._needs_load = kw.pop("defer_load", False); super().__init__(parent, bg=th["bg"], **kw)
        self.app = app
        self.lang = getattr(app, "lang", "en") or "en"
        # Re-auth gate: one in-memory instance per app (survives rebuilds).
        self.gate = getattr(app, "finance_gate", None) or FinanceGate()
        app.finance_gate = self.gate
        self._tv = tree_style("Finance", th)
        # R54 (Section G): the whole page rides a vertical scroll page
        # (Appointments/Users pattern) -- AR rows overflow 1080px, so the
        # expenses bottom + Edit/Delete were unreachable; overlays stay
        # placed on the tab itself, above the scroll host.
        self._scroll_page, body = make_scroll_page(self, th["bg"])
        cards = tk.Frame(body, bg=th["bg"]); cards.pack(fill="x", padx=10, pady=8)
        self.cards = {}
        # Keys stay the English titles (tests + calc() use them); only
        # the DISPLAYED label goes through t() at build time.
        for title, key, col in [("Total Income", "income", th["income"]), ("Total Expenses", "expenses", th["expenses"]), ("Total Lab", "lab", th["lab"]), ("Total Debts", "debts", th["debts"]), ("Net Income", "net", th["net"])]:
            c = RoundedFrame(cards, bg=th["panel"], border=th["border"])
            c.pack(side="left", fill="x", expand=True, padx=6); c = c.inner
            tk.Label(c, text=t(f"fin.card_{key}", self.lang), bg=th["panel"], fg=th["muted"], font=("Segoe UI", 8)).pack(pady=(8, 2)); lbl = tk.Label(c, text="0.00", bg=th["panel"], fg=col, font=("Segoe UI", 14, "bold")); lbl.pack(pady=(0, 8))
            tk.Frame(c, bg=col, height=4).pack(fill="x", side="bottom", padx=8)  # R19 item 7: inset so the strip's square corners stay inside the card's rounded corners
            self.cards[title] = lbl
        build_totals_toggles(self, th, body)  # Job 9a: lab/salaries/expenses toggles
        build_currency_selector(self, th, body)  # R19-E: All / per-currency selector
        per = RoundedFrame(body, bg=th["panel"], border=th["border"])
        per.pack(fill="x", padx=10, pady=4); per = per.inner
        tk.Label(per, text=t("fin.from", self.lang), bg=th["panel"], fg=th["text"]).pack(side="left", padx=6)
        self.e_from = RoundedEntry(per, width=12); self.e_from.pack(side="left", padx=4); self.e_from.insert(0, date.today().replace(day=1).isoformat())
        tk.Label(per, text=t("fin.to", self.lang), bg=th["panel"], fg=th["text"]).pack(side="left", padx=4)
        self.e_to = RoundedEntry(per, width=12); self.e_to.pack(side="left", padx=4); self.e_to.insert(0, date.today().isoformat())
        rounded_button(per, text=t("fin.calculate", self.lang), bg=th["accent"], fg=th["btn_text"], relief="flat", command=self.calc).pack(side="left", padx=8); self.lbl_usd = tk.Label(per, text="", bg=th["panel"], fg=th["muted"], font=("Segoe UI", 9)); self.lbl_usd.pack(side="left", padx=8)
        build_rate_row(self, th, body)  # today's rate row (R21: ANY currency -> base, manual)
        nb = ttk.Notebook(body, style=notebook_style("Finance", th)); nb.pack(fill="both", expand=True, padx=10, pady=6)
        build_expenses_tab(nb, self); build_lab_tab(nb, self); build_debts_tab(nb, self)
        build_centers_tab(nb, self); build_salaries_tab(nb, self); build_stats_tab(nb, self)
        for _i in nb.tabs():  # salaries tab paints global panel: recolour to finance surfaces
            _txt = nb.tab(_i, "text")
            if "Salaries" in _txt or "الرواتب" in _txt:
                recolour_tab_frame(nb.nametowidget(_i), th)
        self._gate_user = None; self._gate_role = None; build_lock_view(self, th); build_doctor_view(self, th); build_nurse_view(self, th)
        wire_auto_lock(self)  # Job 9b: re-lock 15 min after last activity
        self.bind("<Map>", self._on_map)
        if not self.gate.is_unlocked: self._show_lock()
        # R24 item 8: defer_load (shell) defers load/calc to first Map+unlock in _on_map; load() still refuses when locked.
        if not self._needs_load: self.load(); self.calc()
    def _show_lock(self):
        self.e_gate_user.delete(0, tk.END); self.e_gate_user.insert(0, getattr(self.app, "current_user", "") or "")
        self.e_gate_pass.delete(0, tk.END); self.lbl_gate_err.config(text="")
        if hasattr(self, "lbl_gate_auto"): self.lbl_gate_auto.config(text="")
        self._lock.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.e_gate_pass.focus_set()
    def _try_unlock(self):
        user = self.e_gate_user.get().strip()
        if self.gate.try_unlock(user, self.e_gate_pass.get()):
            # Role comes from the GATE user (whoever presented credentials), not necessarily the logged-in user.
            self._gate_user = user; self._gate_role = get_user_role(user)
            self._lock.place_forget()
            scope = finance_scope(self._gate_role)
            if scope == "none": self._nurse_view.place(relx=0, rely=0, relwidth=1, relheight=1)  # nurse: no finance access
            elif scope == "own": self._doc_view.place(relx=0, rely=0, relwidth=1, relheight=1); self._calc_doctor()  # doctor: own income only
            else: self.load(); self.calc()  # admin: full view
        else:
            self.lbl_gate_err.config(text=t("fin.gate_wrong", self.lang))
            self.e_gate_pass.delete(0, tk.END); self.e_gate_pass.focus_set()
    def _finance_scope(self):
        """Scope of whoever unlocked the gate; an extra finance.view
        grant lifts a nurse to the doctor's own-income view (own income
        only — still no center totals)."""
        scope = finance_scope(self._gate_role or self._role())
        if scope == "none" and self._gate_user and has_perm(self._gate_user, "finance.view"):
            return "own"
        return scope
    def _calc_doctor(self):
        self.gate.touch()  # calculating is finance activity
        user = self._gate_user or getattr(self.app, "current_user", "") or ""
        res = doctor_result(self, user)  # R19-E: All converted / one currency raw
        self._doc_total.config(text=f"{res['total']:.2f}")
        self._doc_paid.config(text=f"{res['paid']:.2f}")
        self._doc_rem.config(text=f"{res['remaining']:.2f}")
    def relock(self):
        """Logout: lock the gate and show the prompt again."""
        self.gate.lock()
        hide_finance_numbers(self)  # locked: no numbers left visible
        self._gate_user = None; self._gate_role = None
        if hasattr(self, "_doc_view"): self._doc_view.place_forget()
        if hasattr(self, "_nurse_view"): self._nurse_view.place_forget()
        if hasattr(self, "_lock"): self._show_lock()
    def _on_map(self, event):
        if event.widget is not self: return
        if not self.gate.is_unlocked: self._show_lock(); return
        self.gate.touch()
        if self._needs_load: self.load(); self.calc()  # R24: deferred first load, gate already unlocked
    def load(self):
        self.gate.touch(); self._needs_load = self._needs_load and not self.gate.is_unlocked
        if not self.gate.is_unlocked: return  # locked: reveal nothing, stay deferred
        if self._finance_scope() == "none": self._nurse_view.place(relx=0, rely=0, relwidth=1, relheight=1); return  # nurse: message, no numbers
        if self._finance_scope() == "own":  # doctor: own income only
            self._doc_view.place(relx=0, rely=0, relwidth=1, relheight=1); self._calc_doctor(); return
        self._doc_view.place_forget(); self._nurse_view.place_forget()
        conn = get_connection(); cur = conn.cursor()
        for tr in (self.tree_exp, self.tree_lab, self.tree_debt):
            [tr.delete(i) for i in tr.get_children()]
        cur.execute("SELECT * FROM expenses ORDER BY date DESC LIMIT 200")
        for r in cur.fetchall(): self.tree_exp.insert("", "end", iid=str(r["id"]), values=(r["date"], r["category"], r["description"], r["amount"]))
        cur.execute("SELECT * FROM lab_costs ORDER BY date DESC LIMIT 200")
        for r in cur.fetchall(): self.tree_lab.insert("", "end", iid=str(r["id"]), values=(r["date"], r["lab_name"], r["description"], r["cost"]))
        for d in debts_list():
            self.tree_debt.insert("", "end", values=(d["file_number"], d["full_name"], d["total"], d["paid"], d["remain"]))
        zebra_tree(self.tree_exp); zebra_tree(self.tree_lab); zebra_tree(self.tree_debt)  # R21 item 6
        refresh_centers_tab(self); refresh_salaries_tab(self); refresh_stats_tab(self)
        conn.close()
        refresh_all_record_buttons(self)
    def calc(self):
        self.gate.touch()  # calculating is finance activity
        if not self.gate.is_unlocked: return  # locked: reveal no finance data
        if self._finance_scope() != "full": return  # doctor/nurse: no center totals
        res = admin_result(self)  # R19-E: All -> flexible_totals() as before; one currency -> raw
        self.cards["Total Income"].config(text=f"{res['total_income']:.2f}")
        _exp_on = "expenses" in res["included"] or "salaries" in res["included"]
        self.cards["Total Expenses"].config(text=f"{res['total_expenses']:.2f}" if _exp_on else "—")
        self.cards["Total Lab"].config(text=f"{res['total_lab']:.2f}" if "lab" in res["included"] else "—")
        self.cards["Total Debts"].config(text=f"{res['total_debts']:.2f}")
        self.cards["Net Income"].config(text=f"{res['net_income']:.2f}")
        parts = ", ".join(t(f"fintot.part_{p}", self.lang) for p in res["included"]) or t("fintot.none", self.lang); self.lbl_tot_included.config(text=t("fintot.included", self.lang).format(parts=parts))
        base = res.get("base_currency", self.base_cur)
        if res.get("currency"):
            self.lbl_usd.config(text=t("fincur.raw_note", self.lang).format(cur=res["currency"]))
        elif res.get("rate") and res.get("total_income_usd") is not None:
            self.lbl_usd.config(text=t("fin.usd_equiv", self.lang).format(base=base, inc=res["total_income_usd"], net=res["net_usd"], rate=res["rate"]))
        else:
            self.lbl_usd.config(text=t("fin.usd_set_rate", self.lang).format(base=base))
        if not res.get("currency"):  # R23 item 6: foreign rows with NO saved
            # rate are excluded from the converted cards -- surface them RAW
            # here (per-currency lines) instead of dropping them silently.
            try:
                from src.models.finance_currency import unconverted_totals
                unc = unconverted_totals(self.e_from.get().strip() or None, self.e_to.get().strip() or None)
                if unc:
                    extra = "; ".join(t("fincur.patient_line", self.lang).format(cur=u["currency"], total=f"{u['total']:.2f}", paid=f"{u['paid']:.2f}", rem=f"{u['remaining']:.2f}") for u in unc)
                    self.lbl_usd.config(text=self.lbl_usd.cget("text") + "  •  " + t("fincur.breakdown_title", self.lang) + ": " + extra)
            except Exception: pass
    def save_rate_today(self):
        try:
            r = float(self.e_rate_today.get()); assert r > 0
        except Exception:
            messagebox.showerror(t("fin.err_title", self.lang), t("fin.err_rate", self.lang).format(cur=self.base_cur)); return
        _from = self.rate_from_code() if hasattr(self, "rate_from_code") else "USD"
        save_rate(date.today().isoformat(), r, _from, self.base_cur)
        self.lbl_rate.config(text=t("fin.last_saved", self.lang).format(rate=r, cur=self.base_cur)); self.calc()
        messagebox.showinfo(t("fin.saved_title", self.lang), t("fin.rate_saved", self.lang).format(rate=r, cur=self.base_cur))
    def _role(self):
        """Current user's role (threaded from shell/app; 'doctor' fallback)."""
        return getattr(self.app, "current_role", None) or "doctor"
    def _can_pay(self):
        """Payments are admin-only (owner's rule) — or anyone holding the extra finance.edit_amounts grant."""
        from src.models.permissions import can_edit_payments
        if can_edit_payments(self._role()) or has_perm(getattr(self.app, "current_user", ""), "finance.edit_amounts"):
            return True
        messagebox.showerror(t("fin.not_allowed_title", self.lang),
            t("fin.not_allowed_payments", self.lang))
        return False
    def add_exp(self):
        if not self._can_pay():
            return
        try: amt = float(self.e_exp_amt.get() or 0)
        except Exception: messagebox.showerror(t("fin.err_title", self.lang), t("fin.err_amount", self.lang)); return
        add_expense(self.e_exp_date.get(), self.e_exp_cat.get(), self.e_exp_desc.get(), amt)
        self.load(); self.calc()
    def add_lab(self):
        if not self._can_pay():
            return
        try: cost = float(self.e_lab_cost.get() or 0)
        except Exception: messagebox.showerror(t("fin.err_title", self.lang), t("fin.err_cost", self.lang)); return
        pf = self.app.current_patient["file_number"] if self.app.current_patient else None
        add_lab_cost(self.e_lab_date.get(), self.e_lab_name.get(), pf, self.e_lab_desc.get(), cost)
        self.load(); self.calc()
