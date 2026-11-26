"""Payments review (Round 38, item 2, zone 3).

The bottom notebook's Financial page becomes the dedicated
PAYMENTS REVIEW: one row per payment the patient made — session
payments and standalone payments (row_kind='payment', incl. advance
payments) alike — with date, amount (in its own currency),
currency, treating doctor, recorded-by, the running patient
balance after that payment (base currency), and the payment type.
Round 41 (item 7): the Currency column moved to LAST (owner: it
should be first or last in the table) — all other columns and
content unchanged. Round 41 (item 4): text cells pass through
clinical_history.flat_cell, like the session table's.
A summary line above the list shows the CURRENT balance, in the
credit wording + credit colour when the patient is in credit.
Charges (session totals with no payment) are not rows here — they
live in the unified session table; they still shift the running
balances (models.payments.patient_payments does the math)."""
import tkinter as tk
from tkinter import messagebox, simpledialog

from src.config.strings import t
from src.config.strings_r38 import r38_t
from src.config.theme import credit_color, current, is_dark
from src.models.edit_rules import can_edit_date
from src.models.finance import patient_totals
from src.models.payments import change_payment_date, patient_payments
from src.ui.clinical_history import flat_cell
from src.ui.rounded import rounded_button

FIN_COLS = ("date", "amount", "doctor", "by", "balance", "kind", "currency")
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
                d.get("doctor") or "", d.get("entered_by") or "",
                f"{d['balance_after']:,.2f}",
                r38_t("pay.kind_payment" if d["row_kind"] == "payment"
                      else "pay.kind_session", lang),
                (d.get("currency") or "").strip() or "—")
        iid = tr.insert("", "end", iid=str(d["id"]),
                        values=tuple(flat_cell(v) for v in vals))
        tab._hist_rows["tree_fin"][iid] = d
    refresh_summary(tab, fid)
    try:
        ensure_date_button(tab)
    except Exception:
        pass


# ---- Round 49 (Section F): admin-only standalone-payment date edit --
EDIT_DATE_LABEL = "Edit date / تعديل التاريخ"


def selected_payment(tab):
    """The payment dict of the selected review row, or None."""
    tr = getattr(tab, "tree_fin", None)
    if tr is None:
        return None
    sel = tr.selection()
    if not sel:
        return None
    return (getattr(tab, "_hist_rows", {}) or {}).get("tree_fin", {}).get(sel[0])


def sync_date_button(tab):
    """Enable the Edit-date button only for ADMIN with a standalone
    payment selected (session-linked rows follow the session)."""
    btn = getattr(tab, "btn_fin_date", None)
    if btn is None:
        return
    row = selected_payment(tab)
    ok = can_edit_date(getattr(tab, "current_role", None)) \
        and row is not None and row.get("row_kind") == "payment"
    try:
        btn.config(state="normal" if ok else "disabled")
    except Exception:
        pass


def ensure_date_button(tab):
    """Create tab.btn_fin_date once, under the review tree (the
    tree's page frame is tree -> RoundedFrame.inner -> RoundedFrame
    -> page), and keep its state in step with the selection."""
    if getattr(tab, "btn_fin_date", None) is not None:
        sync_date_button(tab)
        return
    tr = tab.tree_fin
    page = tr.master.master.master
    th = current()
    btn = rounded_button(page, text=EDIT_DATE_LABEL, bg=th["card"],
                         fg=th["text"], state="disabled",
                         command=lambda: edit_selected_payment_date(tab))
    btn.pack(fill="x", padx=6, pady=(0, 4))
    tab.btn_fin_date = btn
    tr.bind("<<TreeviewSelect>>", lambda _e: sync_date_button(tab), add="+")
    sync_date_button(tab)


def edit_selected_payment_date(tab):
    """Ask for the new date and apply it via the guarded model
    path (payments.change_payment_date). Only the DATE changes;
    on success the review reloads, so the running-balance column
    re-derives in the new date order. True when a date changed."""
    lang = getattr(tab.app, "lang", "en")
    row = selected_payment(tab)
    fid = getattr(tab, "patient_id", None) or \
        (tab.app.current_patient or {}).get("file_number")
    if row is None or not fid:
        return False
    if not can_edit_date(getattr(tab, "current_role", None)) \
            or row.get("row_kind") != "payment":
        messagebox.showwarning(EDIT_DATE_LABEL,
                               "Only the admin may change a payment date"
                               if lang != "ar" else
                               "لا يمكن تغيير تاريخ الدفعة إلا من قبل المدير")
        return False
    new = simpledialog.askstring(EDIT_DATE_LABEL,
                                 r38_t("pay.date", lang) + " (YYYY-MM-DD)",
                                 initialvalue=row.get("visit_date") or "",
                                 parent=tab)
    if not new:
        return False
    try:
        changed = change_payment_date(fid, row["id"], new.strip(),
                                      getattr(tab, "current_role", None))
    except (ValueError, PermissionError, LookupError) as exc:
        messagebox.showerror(t("clinical.error", lang), str(exc))
        return False
    if changed:
        fill_review(tab, fid)
    return changed
