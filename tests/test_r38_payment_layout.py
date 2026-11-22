"""Round 38, item 2 — ROUND-40 RE-PIN (owner correction
2026-11-21): the two-zone layout is SUPERSEDED. There is ONE
payment place now: the unified session entry + its money strip
(currency / rate / rate date / treating doctor / note / Print
invoice / balance band). The round-38 "Payment entry" zone is
gone (no e_paid / e_pay_date / fin_section). The PAYMENTS REVIEW
list (zone 3) is unchanged: all payments with the running
balance + the credit-coloured summary line.

GUI test: an advance payment typed into the ONE entry lands as
a standalone payment, shows in the review with its running
balance, and both balance lines wear the credit colour."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk

from src.config.theme import credit_color, is_dark
from src.models.finance import patient_totals
from src.ui.clinical_payments_review import FIN_COLS
from tests.test_payments_e2e import (_build_clinical, _seed_patient,
                                     _cleanup, _patch_msgs, _rows)


def test_single_payment_place():
    fid = _seed_patient("R38 Zones")
    try:
        root, tab = _build_clinical("fady", "admin", fid)
        if root is None:
            return  # no display
        # The ONE entry: session money row (round 24) + money strip.
        assert hasattr(tab, "e_sess_total") and hasattr(tab, "tree_history")
        for attr in ("e_pay_note", "cb_doctor", "cb_cur", "e_rate",
                     "e_rate_date", "btn_invoice", "money_strip"):
            assert hasattr(tab, attr), attr
        # The round-38 payment-entry zone is GONE (owner correction).
        for attr in ("e_paid", "e_pay_date", "fin_section", "fin_frame",
                     "e_total", "e_fin_tooth", "lbl_rem"):
            assert not hasattr(tab, attr), attr
        # Payments review: columns + summary line (unchanged).
        assert tuple(tab.tree_fin["columns"]) == FIN_COLS
        assert hasattr(tab, "lbl_pay_summary")
        root.destroy()
    finally:
        _cleanup(fid)


def test_advance_payment_via_the_form():
    fid = _seed_patient("R38 Form")
    caps, restore = _patch_msgs()
    try:
        root, tab = _build_clinical("nurse1", "nurse", fid)
        if root is None:
            return
        # R40: pure advance through the ONE entry (no tooth, no
        # clinical text, Total 0, Paid 500) — the nurse records it
        # for the default treating doctor.
        tab.app.chart_teeth = lambda: []
        from src.ui import clinical_session_entry as _entry
        _entry.set_money(tab, 0, 500)
        tab.e_pay_note.delete(0, tk.END); tab.e_pay_note.insert(0, "advance")
        tab.btn_save_visit.invoke()
        tab.load(fid)  # what the real app's refresh_clinical does
        root.update_idletasks()
        assert not caps["error"], caps
        assert _rows(fid) == 1
        assert patient_totals(fid)["remaining"] == -500.0
        # Review list: one standalone row, balance after = -500.
        kids = tab.tree_fin.get_children()
        assert len(kids) == 1
        vals = tab.tree_fin.item(kids[0], "values")
        # R41 item 7: Currency moved to LAST — the order is now
        # (date, amount, doctor, by, balance, kind, currency).
        assert vals[1] == "500" and vals[4] == "-500.00", vals
        assert vals[5] == "Standalone" and vals[6] == "SYP", vals
        # Credit colour + wording on BOTH balance lines.
        assert tab.lbl_pat_totals.cget("fg") == credit_color(is_dark())
        assert "Credit" in tab.lbl_pat_totals.cget("text")
        assert tab.lbl_pay_summary.cget("fg") == credit_color(is_dark())
        assert "Credit" in tab.lbl_pay_summary.cget("text")
        root.destroy()
    finally:
        restore(); _cleanup(fid)


def test_zero_amount_is_a_noop_not_a_row():
    fid = _seed_patient("R38 Zero")
    caps, restore = _patch_msgs()
    try:
        root, tab = _build_clinical("fady", "admin", fid)
        if root is None:
            return
        # R40: an untouched 0/0 Save in the ONE entry writes no row
        # (the session gate explains; R38's no-change info is gone).
        tab.btn_save_visit.invoke()
        assert _rows(fid) == 0 and caps["error"], caps
        root.destroy()
    finally:
        restore(); _cleanup(fid)
