"""Round 24: unified-table ENTRY-AREA helpers + session data
fetchers (split from clinical_session.py / _edit for the line cap).

entry_date / entry_tooth / get_money / set_money read and write
the entry widgets built by clinical_session._build_money_row;
clear_entry resets the whole entry area; session_note /
session_raw_money fetch what an Edit needs from the DB (the
session dict from history_money carries display text + ids, not
the stored visit note or the RAW money amounts). <200 lines."""
import tkinter as tk
from datetime import datetime
from src.models.database import get_connection
from src.models.finance_totals import normalize_tooth_key


def entry_date(tab):
    """The entry area's visit date (YYYY-MM-DD); today when blank
    or the widget is missing."""
    w = getattr(tab, "e_sess_date", None)
    txt = w.get().strip() if w is not None else ""
    return txt or datetime.now().strftime("%Y-%m-%d")


def entry_tooth(tab):
    """Normalised tooth bucket of the entry: the session Tooth
    box, else the finance Tooth box, else the chart selection;
    '' = the general bucket."""
    for attr in ("e_sess_tooth", "e_fin_tooth"):
        w = getattr(tab, attr, None)
        if w is not None:
            try:
                raw = w.get().strip()
            except Exception:
                raw = ""
            if raw:
                return normalize_tooth_key(raw)
    try:
        return normalize_tooth_key(",".join(tab.app.chart_teeth()))
    except Exception:
        return ""


def get_money(tab):
    """(total, paid) floats from the entry money boxes.
    Raises ValueError on non-numeric input."""
    tot = float(str(tab.e_sess_total.get()).strip() or 0)
    paid = float(str(tab.e_sess_paid.get()).strip() or 0)
    return tot, paid


def set_money(tab, total, paid):
    for entry, value in ((tab.e_sess_total, total), (tab.e_sess_paid, paid)):
        entry.delete(0, tk.END)
        entry.insert(0, f"{float(value):g}")
    update_sess_remaining(tab)


def update_sess_remaining(tab, _e=None):
    """Live Remaining of the row being entered: max(Total-Paid, 0)
    (the patient's overall remaining comes from patient sums)."""
    lbl = getattr(tab, "lbl_sess_remain", None)
    if lbl is None:
        return
    try:
        tot, paid = get_money(tab)
        lbl.config(text=f"{max(tot - paid, 0.0):.2f}")
    except Exception:
        lbl.config(text="—")


def set_entry_text(tab, attr, text):
    w = getattr(tab, attr, None)
    if w is not None:
        w.delete("1.0", tk.END)
        if text:
            w.insert("1.0", text)


def clear_entry(tab):
    """Reset the entry area for the next session: the four texts,
    the visit note, money 0/0, today's date, the chart tooth."""
    for attr in ("txt_complaint", "txt_sym", "txt_diagnosis",
                 "txt_procedure", "txt_visit_note"):
        w = getattr(tab, attr, None)
        if w is not None:
            try:
                w.delete("1.0", tk.END)
            except Exception:
                pass
    if getattr(tab, "e_sess_total", None) is not None:
        set_money(tab, 0, 0)
    if getattr(tab, "e_sess_date", None) is not None:
        tab.e_sess_date.delete(0, tk.END)
        tab.e_sess_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
    tooth = ""
    try:
        tooth = ",".join(tab.app.chart_teeth())
    except Exception:
        pass
    if getattr(tab, "e_sess_tooth", None) is not None:
        tab.e_sess_tooth.delete(0, tk.END)
        tab.e_sess_tooth.insert(0, tooth)


def session_note(session):
    """The visit note stored on the session's rows (first non-empty
    notes column across complaints / diagnoses / procedures)."""
    conn = get_connection(); cur = conn.cursor()
    note = ""
    try:
        for table, ids in (("complaints", [session.get("complaints_id")]),
                           ("diagnoses", session.get("diagnosis_ids") or []),
                           ("procedures", session.get("procedure_ids") or [])):
            for rid in ids:
                if not rid:
                    continue
                row = cur.execute(f"SELECT notes FROM {table} WHERE id=?", (rid,)).fetchone()
                if row and row[0]:
                    note = row[0]; break
            if note:
                break
    except Exception:
        note = ""
    conn.close()
    return note


def session_raw_money(session):
    """(total, paid, currency, rate) RAW sums over the session's
    financial rows (what was originally typed, in its currency),
    or (0, 0, None, None) when the session has no money."""
    ids = session.get("financial_ids") or []
    if not ids:
        return 0.0, 0.0, None, None
    conn = get_connection(); cur = conn.cursor()
    tot = paid = 0.0; cur_code = None; rate = None
    try:
        for rid in ids:
            row = cur.execute("SELECT total_cost,paid_amount,currency,exchange_rate FROM financials WHERE id=?", (rid,)).fetchone()
            if row:
                tot += float(row[0] or 0); paid += float(row[1] or 0)
                cur_code = cur_code or (row[2] or None)
                rate = rate if rate is not None else row[3]
    except Exception:
        pass
    conn.close()
    return tot, paid, cur_code, rate
