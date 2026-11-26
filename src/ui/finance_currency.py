"""Finance tab per-currency selector (Round 19, Job R19-E).

A selector row -- "All currencies" + one entry per currency
actually present in the finance records -- switching the totals
cards between today's converted All view (flexible_totals /
doctor_income, untouched) and RAW per-currency totals
(finance_currency.totals_for_currency / doctor_income_currency,
no conversion). The doctor's own-income overlay has its own
combobox bound to the SAME variable, so both views respect the
same selection. Kept out of finance.py so it stays <200 lines.
"""
import tkinter as tk
from src.config.strings import t
from src.config.theme import finance_current, RADIUS_FIELD
from src.models.finance import doctor_income
from src.models.finance_currency import (currencies_present,
                                         doctor_income_currency,
                                         totals_for_currency)
from src.ui.finance_records import totals_selection
from src.ui.rounded_frame import RoundedFrame
from src.ui.currency_picker import CurrencyPicker  # R25 item 5


def _L(tab):
    return getattr(tab, "lang", None) or getattr(
        getattr(tab, "app", None), "lang", "en") or "en"


def selected_currency(tab):
    """The selected currency code, or None for 'All currencies'."""
    disp = getattr(tab, "cur_var", None).get() if getattr(tab, "cur_var", None) else ""
    if not disp or disp == getattr(tab, "_cur_all_label", None):
        return None
    return disp.strip().upper()


def _displays(tab):
    return [t("fincur.all", _L(tab))] + currencies_present()


def refresh_currency_selector(tab):
    """Re-derive the selector entries from the records (a currency
    appears automatically with its first record). A selection that
    no longer exists falls back to 'All currencies'."""
    try:
        displays = _displays(tab)
    except Exception:
        return
    tab._cur_displays = displays
    for attr in ("cb_fin_cur", "cb_doc_cur"):
        combo = getattr(tab, attr, None)
        if combo is not None:
            try:
                combo["values"] = displays  # R25: picker contract (was combo.widget)
            except Exception:
                pass
    if selected_currency(tab) is not None and \
            tab.cur_var.get() not in displays:
        tab.cur_var.set(displays[0])
    note = getattr(tab, "lbl_cur_note", None)
    if note is not None:
        cur = selected_currency(tab)
        note.config(text=t("fincur.raw_note", _L(tab)).format(cur=cur) if cur else "")


def build_currency_selector(tab, th, parent=None):
    """Build the selector row on the Finance tab (admin view; the
    doctor overlay carries its own combobox on the same variable).
    R54 (Section G): `parent` is the Finance scroll host."""
    fr = RoundedFrame(parent or tab, bg=th["panel"], border=th["border"])
    fr.pack(fill="x", padx=10, pady=4); fr = fr.inner
    tk.Label(fr, text=t("fincur.selector_label", _L(tab)), bg=th["panel"],
             fg=th["text"]).pack(side="left", padx=6)
    tab._cur_all_label = t("fincur.all", _L(tab))
    tab.cur_var = tk.StringVar(value=tab._cur_all_label)
    tab._cur_displays = _displays(tab)
    # R25 item 5: was a readonly RoundedCombobox (typing impossible);
    # now the searchable CurrencyPicker -- values mode (All + codes).
    tab.cb_fin_cur = CurrencyPicker(fr, textvariable=tab.cur_var,
                                    values=tab._cur_displays, width=18,
                                    lang=_L(tab))
    tab.cb_fin_cur.pack(side="left", padx=4)
    tab.cb_fin_cur.bind("<<ComboboxSelected>>",
                        lambda e: on_currency_change(tab))
    tab.lbl_cur_note = tk.Label(fr, text="", bg=th["panel"], fg=th["muted"])
    tab.lbl_cur_note.pack(side="left", padx=8)


def on_currency_change(tab):
    """Selector changed: recompute whichever view is showing."""
    try:
        tab.gate.touch()
    except Exception:
        pass
    scope = tab._finance_scope()
    if scope == "full":
        tab.calc()
    elif scope == "own":
        tab._calc_doctor()


def admin_result(tab):
    """Totals dict for the admin cards: 'All' -> flexible_totals()
    exactly as before this round; one currency -> RAW totals."""
    refresh_currency_selector(tab)
    cur = selected_currency(tab)
    lab, sal, exp = totals_selection(tab)
    if cur is None:
        # All view: identical to the pre-round code path in calc().
        from src.models.finance_totals import flexible_totals
        try:
            return flexible_totals(tab.e_from.get().strip(),
                                   tab.e_to.get().strip(), lab, sal, exp)
        except Exception:
            return flexible_totals()
    try:
        return totals_for_currency(cur, tab.e_from.get().strip(),
                                   tab.e_to.get().strip(), lab, sal, exp)
    except Exception:
        return totals_for_currency(cur, include_lab=lab,
                                   include_salaries=sal, include_expenses=exp)


def doctor_result(tab, user):
    """Income dict for the doctor overlay: 'All' -> doctor_income()
    exactly as before; one currency -> RAW own income in it."""
    refresh_currency_selector(tab)
    cur = selected_currency(tab)
    try:
        start, end = tab._doc_from.get().strip(), tab._doc_to.get().strip()
    except Exception:
        start = end = None
    if cur is None:
        try:
            return doctor_income(user, start, end)
        except Exception:
            return doctor_income(user)
    try:
        return doctor_income_currency(user, cur, start, end)
    except Exception:
        return doctor_income_currency(user, cur)


def build_rate_row(tab, th, parent=None):
    """Round 21 (item 8): the Today's-rate row, generalised from
    USD-only to ANY currency. A searchable picker over the FULL
    currency list (178) chooses the source currency; the manual
    rate box + Save work for the chosen pair exactly as they did
    for USD (models.currency.save_rate / latest_rate are already
    pair-generic). Changing the picker reloads the pair's last
    saved rate into the box. tab.rate_from_code() -> the code.
    R54 (Section G): `parent` is the Finance scroll host."""
    from src.models.currency import default_currency, latest_rate
    from src.ui.rounded import rounded_button
    from src.ui.rounded_widgets import RoundedEntry
    from src.utils.currencies import (code_for, display as cur_display,
                                      display_for_code, list_currencies)
    from src.ui.currency_picker import CurrencyPicker
    lang = _L(tab)
    tab.base_cur = default_currency()
    rate = RoundedFrame(parent or tab, bg=th["panel"], border=th["border"])
    rate.pack(fill="x", padx=10, pady=4); rate = rate.inner
    tk.Label(rate, text=t("fin.rate_today", lang), bg=th["panel"],
             fg=th["text"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=6)
    tab.rate_from_var = tk.StringVar(value=display_for_code("USD", lang))
    wrap = RoundedFrame(rate, bg=th["panel"], border=th["border"], radius=RADIUS_FIELD, pad=2)
    tab.cb_rate_from = CurrencyPicker(
        wrap.inner, items=list_currencies(),
        display_fn=lambda it: cur_display(it, lang),
        textvariable=tab.rate_from_var, width=20, lang=lang)
    tab.cb_rate_from.pack(fill="both", expand=True); wrap.pack(side="left", padx=4)
    tab.rate_from_code = lambda: code_for(tab.rate_from_var.get()) or "USD"
    tab.e_rate_today = RoundedEntry(rate, width=12)
    tab.e_rate_today.pack(side="left", padx=4)
    rounded_button(rate, text=t("fin.save_rate", lang), bg=th["accent"],
                   fg=th["btn_text"], relief="flat",
                   command=tab.save_rate_today).pack(side="left", padx=6)
    tab.lbl_rate = tk.Label(rate, text="", bg=th["panel"], fg=th["muted"])
    tab.lbl_rate.pack(side="left", padx=6)
    # (No trailing base-currency label: with the picker added it
    # overflowed the row's right edge; the base is named in the
    # "Last saved" text and in the period row's equivalents line.)

    def _refresh_rate_box(*_a):
        lr = latest_rate(tab.rate_from_code(), tab.base_cur)
        tab.e_rate_today.delete(0, tk.END)
        if lr:
            tab.e_rate_today.insert(0, f"{lr:g}")
        tab.lbl_rate.config(
            text=t("fin.last_saved", lang).format(rate=lr, cur=tab.base_cur)
            if lr else t("fin.no_rate", lang))
    tab._refresh_rate_box = _refresh_rate_box
    tab.cb_rate_from.bind("<<ComboboxSelected>>", _refresh_rate_box, add="+")
    _refresh_rate_box()
