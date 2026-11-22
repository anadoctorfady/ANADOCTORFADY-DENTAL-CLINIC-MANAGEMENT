"""Round 40 (item 1): the money STRIP inside the unified entry
area — ONE payment place (owner correction of round 38's two-zone
layout: the standalone "Payment entry" section is REMOVED).

The unified session entry is now the only money entry. Directly
under its Date / Tooth / Total / Paid / Remaining row, this strip
carries everything the removed zone held, in the same place:
currency + rate + rate date, the treating-doctor selector, the
optional payment Note, the Print invoice button, and the patient
balance band (lbl_pat_totals, credit-aware, + the per-currency
breakdown). Widget attribute names are UNCHANGED (cb_cur /
e_rate / e_rate_date / doctor_var / cb_doctor / e_pay_note /
btn_invoice), so money_context / load_costs / calc keep reading
them exactly as before. <200 lines."""
import tkinter as tk
from datetime import datetime

from src.config.strings import t
from src.config.strings_r18_invoice import inv_t
from src.config.strings_r38 import r38_t
from src.config.theme import current, RADIUS_FIELD
from src.models.currency import latest_rate, default_currency
from src.utils.auth import list_doctors
from src.utils.currencies import (list_currencies, display as cur_display,
                                  display_for_code)
from src.ui.currency_picker import CurrencyPicker
from src.ui.clipboard_picker import bind_clipboard_picker
from src.ui.rounded import rounded_button
from src.ui.rounded_frame import RoundedFrame
from src.ui.rounded_widgets import RoundedEntry
from src.ui.rounded_lists import RoundedCombobox
from src.ui.clinical_currency import build_currency_breakdown, _box
from src.ui.clinical_finance_actions import open_invoice


def build_money_strip(tab, parent):
    """Build the strip under the session money row of the unified
    entry block (`parent` = tab.input_block)."""
    th = current(); lang = getattr(tab.app, "lang", "en")
    bg = parent.cget("bg")
    strip = tk.Frame(parent, bg=bg); strip.pack(fill="x", padx=3, pady=(1, 0))
    tab.money_strip = strip
    f9 = ("Segoe UI", 9)
    today = datetime.now().strftime("%Y-%m-%d")
    dbg, dfg = _box("date")
    # Currency + rate row(s).
    r1 = tk.Frame(strip, bg=bg); r1.pack(fill="x", pady=1)
    r1b = tk.Frame(strip, bg=bg); r1b.pack(fill="x", pady=1)
    tab.base_cur = default_currency()
    tab.cur_var = tk.StringVar(value=display_for_code(tab.base_cur, lang))
    wrap = RoundedFrame(r1, bg=bg, border=th["border"], radius=RADIUS_FIELD, pad=2)
    tab.cb_cur = CurrencyPicker(wrap.inner, items=list_currencies(),
                                display_fn=lambda it: cur_display(it, lang),
                                textvariable=tab.cur_var, width=15, font=f9, lang=lang)
    tab.cb_cur.pack(fill="both", expand=True)
    tab.e_rate = RoundedEntry(r1, width=8, font=f9)
    tab.e_rate_date = RoundedEntry(r1b, width=10, font=f9, bg=dbg, fg=dfg)
    tab.e_rate_date.insert(0, today)
    _lr = latest_rate(tab.cur_code(), tab.base_cur)
    if _lr:
        tab.e_rate.insert(0, f"{_lr:g}")
    tab.lbl_rate = tk.Label(r1, text="", bg=bg, fg=th["text"], font=f9,
                            wraplength=110, justify="left")
    tab.lbl_conv = tk.Label(r1b, text="", bg=bg, fg=th["muted"], font=f9)
    tk.Label(r1, text=t("clinical.currency", lang), bg=bg, fg=th["text"], font=f9).pack(side="left", padx=2)
    wrap.pack(side="left", padx=2)
    tab.lbl_rate.pack(side="left", padx=2); tab._rate_label(); tab.e_rate.pack(side="left", padx=2)
    tk.Label(r1b, text=t("clinical.rate_date", lang), bg=bg, fg=th["text"], font=f9).pack(side="left", padx=2)
    tab.e_rate_date.pack(side="left", padx=2); tab.lbl_conv.pack(side="left", padx=2)
    # Treating doctor row.
    r2 = tk.Frame(strip, bg=bg); r2.pack(fill="x", pady=1)
    tk.Label(r2, text=t("clinical.treating_doctor", lang), bg=bg, fg=th["text"], font=f9).pack(side="left", padx=2)
    tab.doctor_var = tk.StringVar(); _docs = list_doctors()
    tab.cb_doctor = RoundedCombobox(r2, textvariable=tab.doctor_var, values=_docs,
                                    width=18, state="readonly")
    tab.cb_doctor.pack(side="left", padx=2)
    _me = getattr(tab, "current_user", "fady")
    tab.doctor_var.set(_me if _me in _docs else (_docs[0] if _docs else "fady"))
    tk.Label(r2, text=t("clinical.income_note", lang), bg=bg, fg=th["muted"],
             font=("Segoe UI", 8)).pack(side="left", padx=2)
    # Note + Print invoice row.
    r3 = tk.Frame(strip, bg=bg); r3.pack(fill="x", pady=1)
    tk.Label(r3, text=r38_t("pay.note", lang), bg=bg, fg=th["text"], font=f9).pack(side="left", padx=2)
    tab.e_pay_note = RoundedEntry(r3, width=34, font=f9); tab.e_pay_note.pack(side="left", padx=2)
    tab.btn_invoice = rounded_button(r3, text=inv_t("inv.print_invoice", lang), bg="#7A3F16",
                                     fg="white", relief="flat",
                                     state="normal" if getattr(tab.app, "current_patient", None) else "disabled",
                                     command=lambda: open_invoice(tab))
    tab.btn_invoice.pack(side="left", padx=6)
    # Patient balance band (credit-aware) + per-currency breakdown.
    build_currency_breakdown(tab, strip)
    tab.cb_cur.bind("<<ComboboxSelected>>", tab.calc)
    tab.e_rate.bind("<KeyRelease>", tab.calc)
    for name, w in (("cost_rate", tab.e_rate), ("pay_note", tab.e_pay_note)):
        bind_clipboard_picker(w); tab.clipboard_fields[name] = w
    return strip
