"""Payments review (Round 38, item 2, zone 3).

The bottom notebook's Financial page becomes the dedicated
PAYMENTS REVIEW: one row per payment the patient made — session
payments and standalone payments (row_kind='payment', incl. advance
payments) alike — with date, amount (in its own currency),
currency, treating doctor, recorded-by, the running patient
balance after that payment (base currency), and the payment type.
A summary line above the list shows the CURRENT balance, in the
credit wording + credit colour when the patient is in credit.
Charges (session totals with no payment) are not rows here — they
live in the unified session table; they still shift the running
balances (models.payments.patient_payments does the math)."""
import tkinter as tk

from src.config.strings import t
from src.config.strings_r38 import r38_t
from src.config.theme import credit_color, current, is_dark
from src.models.finance import patient_totals
from src.models.payments import patient_payments

FIN_COLS = ("date", "amount", "currency", "doctor", "by", "balance", "kind")
FIN_WIDTHS = {"date": 90, "amount": 110, "currency": 70, "doctor": 120,
              "by": 110, "balance": 130, "kind": 90}


def fin_heading(col, lang):
    """Review column heading (date reuses the shared column key)."""
    if col == "date":
        return t("clinical.col_date", lang)
    return r38_t("pay.col_" + col, lang)


def balance_text(tot, lang):
    """(text, is_credit) for a patient_totals() dict: the credit
    wording when remaining < 0, the plain balance line otherwise."""
    if tot["remaining"] < 0:
        return r38_t("credit.balance_fmt", lang).format(
            total=f"{tot['total']:,.2f}", paid=f"{tot['paid']:,.2f}",
            remaining=f"{abs(tot['remaining']):,.2f}"), True
    return t("sess.pat_balance", lang).format(
        total=f"{tot['total']:,.2f}", paid=f"{tot['paid']:,.2f}",
        remaining=f"{tot['remaining']:,.2f}"), False


def refresh_summary(tab, fid):
    """Fill tab.lbl_pay_summary (the review's current-balance line)."""
    lbl = getattr(tab, "lbl_pay_summary", None)
    if lbl is None:
        return
    if not fid:
        lbl.config(text="")
        return
    try:
        text, credit = balance_text(patient_totals(fid),
                                    getattr(tab.app, "lang", "en"))
        lbl.config(text=text,
                   fg=credit_color(is_dark()) if credit else current()["text"])
    except Exception:
        pass


def fill_review(tab, fid):
    """Reload tab.tree_fin with the patient's payments (newest
    first) + refresh the summary line. Rows stored in
    tab._hist_rows['tree_fin'] as the payment dicts."""
    tr = getattr(tab, "tree_fin", None)
    if tr is None:
        return
    lang = getattr(tab.app, "lang", "en")
    for i in tr.get_children():
        tr.delete(i)
    tab._hist_rows["tree_fin"] = {}
    for d in patient_payments(fid):
        vals = (d.get("visit_date") or "",
                f"{float(d.get('paid_amount') or 0):g}",
                (d.get("currency") or "").strip() or "—",
                d.get("doctor") or "", d.get("entered_by") or "",
                f"{d['balance_after']:,.2f}",
                r38_t("pay.kind_payment" if d["row_kind"] == "payment"
                      else "pay.kind_session", lang))
        iid = tr.insert("", "end", iid=str(d["id"]), values=vals)
        tab._hist_rows["tree_fin"][iid] = d
    refresh_summary(tab, fid)
