"""Clinical finance ACTIONS (round 28 split; round 38 form):
load / calc / add-payment for the PAYMENT ENTRY zone.

Round 38: add_fin records a STANDALONE payment via
models.payments.save_standalone_payment (kind='payment', total 0)
— never capped, so advance payments (patient credit) and ordinary
payments toward a balance both save. The round-24 per-session cap
still governs the SESSION entry only (session_money.validate).
Validations that remain here: a patient must be open, the
can_add_payment permission rule (nurse collects for any treating
doctor), a positive numeric amount, a YYYY-MM-DD date, and a rate
for foreign currencies."""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from src.config.strings import t; from src.config.strings_r18_invoice import inv_t
from src.config.strings_r38 import r38_t
from src.models.currency import get_rate, save_rate, convert
from src.utils.currencies import code_for
from src.utils.auth import list_doctors
from src.models.finance import last_treating_doctor
from src.models.permissions import can_add_payment
from src.models import payments as _pay
from src.ui.clinical_currency import refresh_currency_breakdown, refresh_patient_totals

def load_costs(tab, fid):
    """Patient open: treating-doctor default + a FRESH payment
    entry (amount 0, note blank, date today) + the totals line."""
    if fid is None: return
    try:  # refresh the treating-doctor list (new users appear at once)
        _docs = list_doctors()
        if hasattr(tab, "cb_doctor"):
            tab.cb_doctor["values"] = _docs
            # Default = doctor of the patient's LAST visit/payment; no
            # visit yet -> logged-in user, else the first doctor.
            _last = last_treating_doctor(fid); _me = getattr(tab, "current_user", "fady")
            tab.doctor_var.set(_last if _last in _docs else (_me if _me in _docs else (_docs[0] if _docs else "fady")))
    except Exception: pass
    tab.e_paid.delete(0, tk.END); tab.e_paid.insert(0, "0")
    for w, val in ((getattr(tab, "e_pay_note", None), ""),
                   (getattr(tab, "e_pay_date", None), datetime.now().strftime("%Y-%m-%d"))):
        if w is not None:
            w.delete(0, tk.END)
            if val: w.insert(0, val)
    refresh_patient_totals(tab, fid); refresh_currency_breakdown(tab, fid)  # R19-E
    try: tab.calc()
    except Exception: pass

def cur_code(tab):
    return code_for(tab.cur_var.get())

def rate_label(tab):
    cur = tab.cur_code()
    lang = getattr(tab.app, "lang", "en")
    tab.lbl_rate.config(text=t("clinical.rate_fmt", lang).format(cur=cur, base=tab.base_cur) if cur != tab.base_cur else t("clinical.rate_base_fmt", lang).format(base=tab.base_cur))

def refresh_invoice_state(tab):
    btn = getattr(tab, "btn_invoice", None)
    if btn is not None:
        try: btn.config(state="normal" if getattr(tab.app, "current_patient", None) else "disabled")
        except Exception: pass

def open_invoice(tab):
    if not getattr(tab.app, "current_patient", None):
        messagebox.showwarning(t("clinical.select_title", getattr(tab.app, "lang", "en")), inv_t("inv.select_patient", getattr(tab.app, "lang", "en"))); return
    from src.reports.print_preview import open_invoice_preview
    open_invoice_preview(tab.app, parent=tab)

def calc(tab, _e=None):
    refresh_invoice_state(tab); lang = getattr(tab.app, "lang", "en")
    try:
        cur = tab.cur_code()
        tab._rate_label()
        if cur == tab.base_cur:
            tab.lbl_conv.config(text=t("clinical.no_rate_fmt", lang).format(base=tab.base_cur))
        else:
            try:
                r = float(tab.e_rate.get())
                base_amt, _ = convert(float(tab.e_paid.get() or 0), cur, tab.base_cur, rate=r)
                tab.lbl_conv.config(text=t("clinical.converted_fmt", lang).format(amt=f"{base_amt:,.0f}", base=tab.base_cur, rate=f"{r:g}"))
            except Exception:
                tab.lbl_conv.config(text=t("clinical.enter_rate", lang))
    except Exception: pass

def add_fin(tab):
    lang = getattr(tab.app, "lang", "en")
    cur_user = getattr(tab, "current_user", "fady")
    cur_role = getattr(tab, "current_role", "admin")
    doctor = (tab.doctor_var.get().strip() if getattr(tab, "doctor_var", None) else "") or cur_user
    # Nurse collects the money: she may record it for any treating doctor.
    if not can_add_payment(cur_role, doctor, cur_user):
        messagebox.showerror(t("clinical.permission_title", lang), t("clinical.permission_msg", lang)); return
    if not tab._need(): return
    try:
        amount = float(tab.e_paid.get() or 0)
    except Exception:
        messagebox.showerror(t("clinical.error", lang), t("clinical.invalid_numbers", lang)); return
    if amount == 0.0:  # nothing entered: no row (no-op kept from R23/R24)
        messagebox.showinfo(t("pay_no_change_title", lang), t("pay_no_change_msg", lang)); return
    if amount < 0:
        messagebox.showerror(t("clinical.error", lang), r38_t("pay.amount_required", lang)); return
    fid = tab.app.current_patient["file_number"]
    pdate = (tab.e_pay_date.get().strip() if getattr(tab, "e_pay_date", None) else "") or datetime.now().strftime("%Y-%m-%d")
    try:
        datetime.strptime(pdate, "%Y-%m-%d")
    except Exception:
        messagebox.showerror(t("clinical.error", lang), r38_t("pay.bad_date", lang)); return
    cur = tab.cur_code(); rdate = tab.e_rate_date.get().strip() or datetime.now().strftime("%Y-%m-%d")
    rate = None
    if cur != tab.base_cur:
        try:
            rate = float(tab.e_rate.get())
            if rate <= 0: raise ValueError
        except Exception:
            rate = get_rate(rdate, cur, tab.base_cur)
            if not rate:
                messagebox.showerror(t("clinical.rate_required_title", lang), t("clinical.rate_required_msg", lang).format(cur=cur, base=tab.base_cur))
                return
        save_rate(rdate, rate, cur, tab.base_cur)
    note = tab.e_pay_note.get().strip() if getattr(tab, "e_pay_note", None) else ""
    _pay.save_standalone_payment(fid, amount, pdate, currency=cur, rate=rate, rate_date=rdate, base=tab.base_cur, doctor=doctor, entered_by=cur_user, note=note)
    tab.e_paid.delete(0, tk.END); tab.e_paid.insert(0, "0")
    if getattr(tab, "e_pay_note", None) is not None:
        tab.e_pay_note.delete(0, tk.END)
    tab.calc(); refresh_patient_totals(tab, fid); tab.app.refresh_clinical()
