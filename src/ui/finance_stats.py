"""Statistics dashboard tab for the Finance tab (Round 49, Section G).

ADMIN-ONLY, mirroring salaries_view.py: the tab is built like the
other finance sub-views, but refresh refuses non-admins via
statistics.ensure_admin (the gate role, tab._gate_role, exactly as
_salaries_view._sal_role resolves it) and draws the admin-only note
instead of any figure. Doctor/nurse gate users never reach it in
practice: FinanceTab covers the whole tab with their role overlay
after unlock, and the whole Finances tab already sits behind the
finance re-auth gate (FinanceGate in FinanceTab._try_unlock), so
this view inherits that gate — verified in finance.py.

Period: Combobox [This month, Last month, Custom] + From/To entries
enabled only for Custom + Refresh. Charts are tk.Canvas drawings
(finance_charts.py) in the vivid palette, theme-aware via
finance_current(). Numbers use the finance format f"{v:,.2f}".
"""
import tkinter as tk
from datetime import date, timedelta

from src.config.theme import finance_current
from src.config.strings_r49_stats import stats_t as t
from src.ui.rounded import rounded_button
from src.ui.rounded_frame import RoundedFrame
from src.ui.rounded_widgets import RoundedEntry
from src.ui.rounded_lists import RoundedCombobox
from src.ui import finance_charts as charts
from src.models import statistics as stats


def _L(tab):
    return getattr(tab, "lang", None) or getattr(
        getattr(tab, "app", None), "lang", "en") or "en"


def _role(tab):
    """Role of the user who unlocked the finance gate (salaries pattern)."""
    return tab._gate_role or tab._role()


def _period(tab):
    """(date_from, date_to) ISO strings for the chosen period."""
    choice = tab.stats_period.get()
    today = date.today()
    if choice == t("stats.last_month", _L(tab)):
        last = today.replace(day=1) - timedelta(days=1)
        return last.replace(day=1).isoformat(), last.isoformat()
    if choice == t("stats.custom", _L(tab)):
        return (tab.stats_from.get().strip() or today.isoformat(),
                tab.stats_to.get().strip() or today.isoformat())
    return today.replace(day=1).isoformat(), today.isoformat()


def _on_period_change(tab):
    custom = tab.stats_period.get() == t("stats.custom", _L(tab))
    state = "normal" if custom else "disabled"
    for e in (tab.stats_from, tab.stats_to):
        e.configure(state=state)
    refresh_stats_tab(tab)


def _stats_resized(tab):
    """R51: redraw the charts when a chart canvas changes WIDTH
    (window resize), coalesced via after(150). Height changes come
    from the draw itself (content-sized canvases) and are ignored,
    so this cannot loop."""
    w = tab.stats_canvases["by_count"].winfo_width()
    if abs(w - getattr(tab, "_stats_w", 0)) < 4:
        return
    tab._stats_w = w
    if getattr(tab, "_stats_resize_pending", False):
        return
    tab._stats_resize_pending = True

    def _go():
        tab._stats_resize_pending = False
        refresh_stats_tab(tab)
    tab.stats_frame.after(150, _go)


def build_stats_tab(nb, tab):
    """Notebook page: controls + summary rows + the four canvases."""
    th = finance_current()
    f = tk.Frame(nb, bg=th["panel"]); nb.add(f, text=t("stats.tab", _L(tab)))
    tab.stats_frame = f
    # R51: the page scrolls (the Settings tab's pattern) -- with
    # content-sized charts the sections no longer fit short windows.
    from tkinter import ttk
    from src.ui.wheel_scroll import bind_canvas_wheel
    sc = tk.Canvas(f, bg=th["panel"], highlightthickness=0)
    sb = ttk.Scrollbar(f, orient="vertical", command=sc.yview)
    sc.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    sc.pack(side="left", fill="both", expand=True)
    body = tk.Frame(sc, bg=th["panel"])
    win = sc.create_window((0, 0), window=body, anchor="nw")
    body.bind("<Configure>",
              lambda e: sc.configure(scrollregion=sc.bbox("all")))
    sc.bind("<Configure>", lambda e: sc.itemconfigure(win, width=e.width))
    bind_canvas_wheel(sc)
    tab.stats_scroll = sc
    bar = RoundedFrame(body, bg=th["panel"], border=th["border"])
    bar.pack(fill="x", padx=6, pady=6); bar = bar.inner
    tk.Label(bar, text=t("stats.period", _L(tab)), bg=th["panel"],
             fg=th["text"]).pack(side="left", padx=4)
    tab.stats_period = RoundedCombobox(
        bar, width=14, values=[t("stats.this_month", _L(tab)),
                               t("stats.last_month", _L(tab)),
                               t("stats.custom", _L(tab))])
    tab.stats_period.pack(side="left", padx=4)
    tab.stats_period.set(t("stats.this_month", _L(tab)))
    tab.stats_period.bind("<<ComboboxSelected>>",
                          lambda e: _on_period_change(tab))
    tk.Label(bar, text=t("stats.from", _L(tab)), bg=th["panel"],
             fg=th["text"]).pack(side="left", padx=4)
    tab.stats_from = RoundedEntry(bar, width=12); tab.stats_from.pack(side="left")
    tab.stats_from.insert(0, date.today().replace(day=1).isoformat())
    tk.Label(bar, text=t("stats.to", _L(tab)), bg=th["panel"],
             fg=th["text"]).pack(side="left", padx=4)
    tab.stats_to = RoundedEntry(bar, width=12); tab.stats_to.pack(side="left")
    tab.stats_to.insert(0, date.today().isoformat())
    for e in (tab.stats_from, tab.stats_to):
        e.configure(state="disabled")
    rounded_button(bar, text=t("stats.refresh", _L(tab)), bg=th["accent"],
                   fg=th["btn_text"], relief="flat",
                   command=lambda: refresh_stats_tab(tab)).pack(side="left", padx=8)
    tab.stats_summary = tk.Label(body, text="", bg=th["panel"], fg=th["text"],
                                 font=("Segoe UI", 10, "bold"), anchor="w")
    tab.stats_summary.pack(fill="x", padx=10, pady=2)
    tab.stats_summary2 = tk.Label(body, text="", bg=th["panel"], fg=th["text"],
                                  font=("Segoe UI", 10, "bold"), anchor="w")
    tab.stats_summary2.pack(fill="x", padx=10, pady=0)
    tab.stats_canvases = {}
    for key, height in (("by_count", 96), ("by_income", 96),
                        ("vs", 74), ("monthly", 140)):
        tk.Label(body, text=t(f"stats.{key}" if key != "vs" else
                           "stats.income_vs_expenses", _L(tab)),
                 bg=th["panel"], fg=th["accent"],
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(
                     fill="x", padx=10, pady=(6, 0))
        cv = tk.Canvas(body, height=height, bg=th["panel"], highlightthickness=0)
        cv.pack(fill="x", padx=10)
        cv.bind("<Configure>", lambda e, tab=tab: _stats_resized(tab))
        tab.stats_canvases[key] = cv
    tab.stats_monthly_canvas = tab.stats_canvases["monthly"]


def refresh_stats_tab(tab):
    """Refill every chart for the chosen period (admin only)."""
    th = finance_current()
    lang = _L(tab)
    empty = t("stats.no_data", lang)
    try:
        stats.ensure_admin(_role(tab))
    except PermissionError:
        tab.stats_summary.config(text=t("stats.admin_only", lang))
        tab.stats_summary2.config(text="")
        for cv in tab.stats_canvases.values():
            charts.draw_hbars(cv, [], t("stats.admin_only", lang), th,
                              family=charts.chart_family(tab))
        return
    date_from, date_to = _period(tab)
    try:
        by_count = stats.top_treatments_by_count(date_from, date_to)
        by_income = stats.top_treatments_by_income(date_from, date_to)
        summary = stats.period_summary(date_from, date_to)
        series = stats.monthly_series(date_from, date_to)
    except Exception:
        by_count, by_income, series = [], [], []
        summary = {"income": 0.0, "expenses_operating": 0.0, "lab": 0.0,
                   "salaries": 0.0, "expenses_total": 0.0, "net": 0.0}
    tab.stats_summary.config(text="  •  ".join([
        f"{t('stats.income', lang)}: {summary['income']:,.2f}",
        f"{t('stats.operating', lang)}: {summary['expenses_operating']:,.2f}",
        f"{t('stats.lab', lang)}: {summary['lab']:,.2f}"]))
    tab.stats_summary2.config(text="  •  ".join([
        f"{t('stats.salaries', lang)}: {summary['salaries']:,.2f}",
        f"{t('stats.expenses_total', lang)}: {summary['expenses_total']:,.2f}",
        f"{t('stats.net', lang)}: {summary['net']:,.2f}"]))
    fam = charts.chart_family(tab)
    charts.draw_hbars(tab.stats_canvases["by_count"], by_count, empty, th,
                      fmt=lambda v: f"{int(v)}", family=fam)
    charts.draw_hbars(tab.stats_canvases["by_income"], by_income, empty,
                      th, family=fam)
    charts.draw_income_vs_expenses(
        tab.stats_canvases["vs"], summary,
        (t("stats.income", lang), t("stats.expenses", lang),
         t("stats.net", lang)), empty, th, family=fam)
    multi = len({(d or "")[:7] for d in (date_from, date_to)}) > 1 \
        or date_from[:7] != date_to[:7]
    if multi:
        charts.draw_monthly(tab.stats_canvases["monthly"], series, empty,
                            th, family=fam)
    else:
        charts.draw_monthly(tab.stats_canvases["monthly"], [], empty, th,
                            family=fam)
