"""Clinical finance section — ROUND 38: the PAYMENT ENTRY zone.

Owner's structure (round 38, item 2): the patient's money area is
three clearly separated zones — (1) the SESSION entry (the unified
clinical table's entry area, clinical_session), (2) this PAYMENT
entry, and (3) the PAYMENTS REVIEW list (clinical_lists tree_fin).

This section is zone 2: ONE standalone payment's compact form —
Date (default today) / Amount / Currency + rate / treating doctor
/ optional note — saved via models.payments.save_standalone_
payment as a kind='payment' row (total 0). Standalone payments are
NEVER capped (round 38 item 1): paying toward a balance and paying
IN ADVANCE (patient credit) both land here; the session entry
keeps round 24's per-session validation. Under the form: the
patient totals line (lbl_pat_totals, credit-aware) + the
per-currency breakdown + Print invoice (not behind the finance
password — nurses print invoices).

Round 28: the section is WIDTH-CAPPED (FIN_CAP_W) and the load /
calc / add-payment ACTIONS live in clinical_finance_actions.py
(this file keeps build + entry widgets)."""
import tkinter as tk
from datetime import datetime
from src.config.strings import t
from src.config.strings_r18_invoice import inv_t
from src.config.strings_r38 import r38_t
from src.config.theme import current, is_dark, RADIUS_FIELD
from src.models.currency import latest_rate, default_currency
from src.utils.auth import list_doctors
from src.utils.currencies import (list_currencies, display as cur_display,
    display_for_code, code_for)
from src.ui.currency_picker import CurrencyPicker  # R25: searchable popup picker
from src.ui.clipboard_picker import bind_clipboard_picker; from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame; from src.ui.rounded_widgets import RoundedEntry; from src.ui.rounded_lists import RoundedCombobox
from src.ui.clinical_currency import build_currency_breakdown, fin_bg as _section_bg, fin_fg, fin_muted
from tkinter import messagebox  # noqa: E402,F401  (test monkeypatch path)
# R28: the finance ACTIONS live in clinical_finance_actions (split
# for the 200-line rule) and are re-exported LAZILY (PEP 562): a
# top-level import here would be circular, because the actions
# module reads this module's helpers.
_ACTIONS = ("load_costs", "cur_code", "rate_label",
            "refresh_invoice_state", "open_invoice", "calc", "add_fin")
def __getattr__(name):
    if name in _ACTIONS:
        from src.ui import clinical_finance_actions as _a
        return getattr(_a, name)
    raise AttributeError(name)
# Distinct box colours: name -> ((light bg, fg), (dark bg, fg)).
BOXES = {"total": (("#FDE68A", "#2C241D"), ("#92400E", "#FFFFFF")),
         "date": (("#EDE9FE", "#2C241D"), ("#6D28D9", "#FFFFFF"))}
FIN_CAP_W = 640  # R28 item 2: clinical finance section max width (px)
def _box(name):  # the active (bg, fg) of a coloured box
    return BOXES[name][1] if is_dark() else BOXES[name][0]
def _open_invoice(tab):
    """R28: the invoice action lives in clinical_finance_actions;
    resolved at call time (a bare global inside this module cannot
    see the lazy PEP 562 re-export)."""
    from src.ui.clinical_finance_actions import open_invoice
    open_invoice(tab)
def build_finance(tab, parent):
    lang = getattr(tab.app, "lang", "en")
    fin_bg = _section_bg()  # R21 item 3: dark = the Total box colour
    # R28 item 2: WIDTH-CAPPED holder (see round-28 note in git
    # history): the frame sits in column 0 over a FIN_CAP_W strut;
    # start-side anchor (AR: right).
    holder = tk.Frame(parent, bg=parent.cget("bg"))
    holder.pack(anchor="e" if lang == "ar" else "w", pady=4)
    tab.fin_section = holder  # R28: the section's pack-slave widget
    fin = RoundedFrame(holder, bg=fin_bg, border=current()["border"], title=r38_t("pay.entry_title", lang), title_fg="#FFD9A0" if is_dark() else "#7A3F16"); fin.grid(row=0, column=0, sticky="ew")
    tk.Frame(holder, width=FIN_CAP_W, height=1, bg=parent.cget("bg")).grid(row=1, column=0)
    tab.fin_frame = fin.inner; fin = fin.inner
    f9 = ("Segoe UI", 9); f9b = ("Segoe UI", 9, "bold")
    today = datetime.now().strftime("%Y-%m-%d")
    r0 = tk.Frame(fin, bg=fin_bg); r0.pack(fill="x", pady=2)
    dbg, dfg = _box("date"); abg, afg = _box("total")
    tab.e_pay_date = RoundedEntry(r0, width=10, font=f9b, justify="center", bg=dbg, fg=dfg)
    tab.e_pay_date.insert(0, today)
    tab.e_paid = RoundedEntry(r0, width=9, font=f9b, justify="center", bg=abg, fg=afg); tab.e_paid.insert(0, "0")
    tab.e_paid.bind("<KeyRelease>", tab.calc)
    tk.Label(r0, text=r38_t("pay.date", lang), bg=fin_bg, fg=fin_fg(), font=f9).pack(side="left", padx=2)
    tab.e_pay_date.pack(side="left", padx=2)
    tk.Label(r0, text=r38_t("pay.amount", lang), bg=fin_bg, fg=fin_fg(), font=f9).pack(side="left", padx=2)
    tab.e_paid.pack(side="left", padx=2)
    rounded_button(r0, text=t("clinical.add_payment", lang), bg="#7A3F16", fg="white", relief="flat", padx=8, command=tab.add_fin).pack(side="left", padx=4)
    build_currency_breakdown(tab, fin)  # patient totals line + per-currency block
    tab.base_cur = default_currency(); tab.cur_var = tk.StringVar(value=display_for_code(tab.base_cur, lang))
    r1 = tk.Frame(fin, bg=fin_bg); r1.pack(fill="x", pady=2); r1b = tk.Frame(fin, bg=fin_bg); r1b.pack(fill="x", pady=2)
    _cur_wrap = RoundedFrame(r1, bg=fin_bg, border=current()["border"], radius=RADIUS_FIELD, pad=2)
    tab.cb_cur = CurrencyPicker(_cur_wrap.inner, items=list_currencies(), display_fn=lambda it: cur_display(it, lang), textvariable=tab.cur_var, width=15, font=f9, lang=lang); tab.cb_cur.pack(fill="both", expand=True)
    tab.e_rate = RoundedEntry(r1, width=8, font=f9); tab.e_rate_date = RoundedEntry(r1b, width=10, font=f9, bg=dbg, fg=dfg)
    tab.e_rate_date.insert(0, today); _lr = latest_rate(tab.cur_code(), tab.base_cur)
    if _lr: tab.e_rate.insert(0, f"{_lr:g}")
    tab.lbl_conv = tk.Label(r1b, text="", bg=fin_bg, fg=fin_muted(), font=("Segoe UI", 9))
    tab.lbl_rate = tk.Label(r1, text="", bg=fin_bg, fg=fin_fg(), font=f9, wraplength=110, justify="left")  # R19: wraps in the narrower right column
    tk.Label(r1, text=t("clinical.currency", lang), bg=fin_bg, fg=fin_fg(), font=f9).pack(side="left", padx=2)
    _cur_wrap.pack(side="left", padx=2)
    tab.lbl_rate.pack(side="left", padx=2); tab._rate_label(); tab.e_rate.pack(side="left", padx=2)
    tk.Label(r1b, text=t("clinical.rate_date", lang), bg=fin_bg, fg=fin_fg(), font=f9).pack(side="left", padx=2)
    tab.e_rate_date.pack(side="left", padx=2); tab.lbl_conv.pack(side="left", padx=2)
    r2 = tk.Frame(fin, bg=fin_bg); r2.pack(fill="x", pady=2)
    tk.Label(r2, text=t("clinical.treating_doctor", lang), bg=fin_bg, fg=fin_fg(), font=f9).pack(side="left", padx=2)
    tab.doctor_var = tk.StringVar(); _docs = list_doctors()
    tab.cb_doctor = RoundedCombobox(r2, textvariable=tab.doctor_var, values=_docs, width=18, state="readonly")
    tab.cb_doctor.pack(side="left", padx=2)
    _me = getattr(tab, "current_user", "fady"); tab.doctor_var.set(_me if _me in _docs else (_docs[0] if _docs else "fady"))
    tk.Label(r2, text=t("clinical.income_note", lang), bg=fin_bg, fg=fin_muted(), font=("Segoe UI", 8)).pack(side="left", padx=2)
    r2b = tk.Frame(fin, bg=fin_bg); r2b.pack(fill="x", pady=2)
    tk.Label(r2b, text=r38_t("pay.note", lang), bg=fin_bg, fg=fin_fg(), font=f9).pack(side="left", padx=2)
    tab.e_pay_note = RoundedEntry(r2b, width=34, font=f9); tab.e_pay_note.pack(side="left", padx=2)
    r3 = tk.Frame(fin, bg=fin_bg); r3.pack(fill="x", pady=2)
    tab.btn_invoice = rounded_button(r3, text=inv_t("inv.print_invoice", lang), bg="#7A3F16", fg="white", relief="flat", state="normal" if getattr(tab.app, "current_patient", None) else "disabled", command=lambda: _open_invoice(tab))
    tab.btn_invoice.pack(side="left", padx=2)
    tab.cb_cur.bind("<<ComboboxSelected>>", tab.calc); tab.e_rate.bind("<KeyRelease>", tab.calc)
    for name, w in (("cost_paid", tab.e_paid), ("cost_rate", tab.e_rate), ("pay_date", tab.e_pay_date), ("pay_note", tab.e_pay_note)):
        bind_clipboard_picker(w); tab.clipboard_fields[name] = w
