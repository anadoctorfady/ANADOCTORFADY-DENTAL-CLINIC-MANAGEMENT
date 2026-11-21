"""Round 38, item 2: the patient's money area is THREE zones —
(1) the SESSION entry (unified session entry, unchanged), (2) the
new PAYMENT entry (date / amount / currency / treating doctor /
optional note), (3) the PAYMENTS REVIEW list (all payments with
the running balance). The round-24 finance form (Total box +
tooth box + Remaining box in the finance section) is GONE: session
money is entered in zone 1 only.

GUI test: an advance payment typed into zone 2 lands as a
standalone payment, shows in zone 3 with its running balance, and
both balance lines wear the credit colour + wording."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tkinter as tk

from src.config.theme import credit_color, is_dark
from src.models.finance import patient_totals
from src.ui.clinical_payments_review import FIN_COLS
from tests.test_payments_e2e import (_build_clinical, _seed_patient,
                                     _cleanup, _patch_msgs, _rows)


def test_three_zones_present():
    fid = _seed_patient("R38 Zones")
    try:
        root, tab = _build_clinical("fady", "admin", fid)
        if root is None:
            return  # no display
        # Zone 1: session entry (round 24, unchanged).
        assert hasattr(tab, "e_sess_total") and hasattr(tab, "tree_history")
        # Zone 2: payment entry widgets.
        for attr in ("e_paid", "e_pay_date", "e_pay_note", "cb_doctor",
                     "cb_cur", "e_rate", "btn_invoice"):
            assert hasattr(tab, attr), attr
        # The old finance-form boxes are gone (owner's restructure).
        for attr in ("e_total", "e_fin_tooth", "lbl_rem"):
            assert not hasattr(tab, attr), attr
        # Zone 3: payments review columns + summary line.
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
        tab.e_paid.delete(0, tk.END); tab.e_paid.insert(0, "500")
        tab.e_pay_note.delete(0, tk.END); tab.e_pay_note.insert(0, "advance")
        tab.add_fin()  # nurse records it for the default doctor
        tab.load(fid)  # what the real app's refresh_clinical does
        root.update_idletasks()
        assert not caps["error"], caps
        assert _rows(fid) == 1
        assert patient_totals(fid)["remaining"] == -500.0
        # Review list: one standalone row, balance after = -500.
        kids = tab.tree_fin.get_children()
        assert len(kids) == 1
        vals = tab.tree_fin.item(kids[0], "values")
        assert vals[1] == "500" and vals[5] == "-500.00", vals
        assert vals[6] == "Standalone", vals
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
        tab.e_paid.delete(0, tk.END); tab.e_paid.insert(0, "0")
        tab.add_fin()
        assert _rows(fid) == 0 and caps["info"], caps  # explained, not saved
        root.destroy()
    finally:
        restore(); _cleanup(fid)
