"""Clinical finance ACTIONS (round 28 split; round 40 form):
load / calc for the unified entry's money strip.

Round 40 (item 1): the round-38 standalone "Payment entry" zone
is REMOVED — add_fin is gone with it; the unified session entry
is the ONE payment place (money flow: clinical_money_flow).
What remains serves the money strip inside the unified area:
load_costs (doctor default + fresh entry + totals), cur_code,
rate_label, calc (live conversion of the entry's Paid), and the
Print invoice button helpers (round 18 item 7: NOT behind the
finance password). <200 lines."""
import tkinter as tk
from tkinter import messagebox
from src.config.strings import t
from src.config.strings_r18_invoice import inv_t
from src.models.currency import convert
from src.utils.currencies import code_for
from src.utils.auth import list_doctors
from src.models.finance import last_treating_doctor
from src.ui import clinical_session_entry as _entry
from src.ui.clinical_currency import refresh_currency_breakdown, refresh_patient_totals


def load_costs(tab, fid):
    """Patient open: treating-doctor default + a FRESH unified
    entry (session money 0 / 0, note blank) + the totals line."""
    if fid is None:
        return
    try:  # refresh the treating-doctor list (new users appear at once)
        _docs = list_doctors()
        if hasattr(tab, "cb_doctor"):
            tab.cb_doctor["values"] = _docs
            # Default = doctor of the patient's LAST visit/payment; no
            # visit yet -> logged-in user, else the first doctor.
            _last = last_treating_doctor(fid); _me = getattr(tab, "current_user", "fady")
            tab.doctor_var.set(_last if _last in _docs else (_me if _me in _docs else (_docs[0] if _docs else "fady")))
    except Exception:
        pass
    _entry.set_money(tab, 0, 0)
    _note = getattr(tab, "e_pay_note", None)
    if _note is not None:
        _note.delete(0, tk.END)
    refresh_patient_totals(tab, fid); refresh_currency_breakdown(tab, fid)  # R19-E
    try:
        tab.calc()
    except Exception:
        pass


def cur_code(tab):
    return code_for(tab.cur_var.get())


def rate_label(tab):
    cur = tab.cur_code()
    lang = getattr(tab.app, "lang", "en")
    tab.lbl_rate.config(text=t("clinical.rate_fmt", lang).format(cur=cur, base=tab.base_cur) if cur != tab.base_cur else t("clinical.rate_base_fmt", lang).format(base=tab.base_cur))


def refresh_invoice_state(tab):
    btn = getattr(tab, "btn_invoice", None)
    if btn is not None:
        try:
            btn.config(state="normal" if getattr(tab.app, "current_patient", None) else "disabled")
        except Exception:
            pass


def open_invoice(tab):
    if not getattr(tab.app, "current_patient", None):
        messagebox.showwarning(t("clinical.select_title", getattr(tab.app, "lang", "en")), inv_t("inv.select_patient", getattr(tab.app, "lang", "en")))
        return
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
                # R40: the conversion reads the ONE entry's Paid.
                base_amt, _ = convert(float(tab.e_sess_paid.get() or 0), cur, tab.base_cur, rate=r)
                tab.lbl_conv.config(text=t("clinical.converted_fmt", lang).format(amt=f"{base_amt:,.0f}", base=tab.base_cur, rate=f"{r:g}"))
            except Exception:
                tab.lbl_conv.config(text=t("clinical.enter_rate", lang))
    except Exception:
        pass
