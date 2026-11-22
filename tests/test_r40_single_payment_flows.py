"""Round 40, item 1 (flows): the round-38 scripted credit
scenario through the ONE form, a money-only save against the
day's session, and the kept refusals. Helpers + the other
single-place tests: test_r40_single_payment_place."""
import tkinter as tk
from src.models.finance import patient_totals
from tests.test_payments_e2e import (TODAY, _seed_users, _seed_patient,
                                     _rows, _cleanup, _patch_msgs,
                                     _build_clinical)
from tests.test_r40_single_payment_place import (_money_rows,
                                                 _fill_texts,
                                                 _save_session)


def test_scripted_credit_scenario_single_form():
    """Round 38's scripted scenario through the ONE form:
    advance 500 -> -500; session Total 300 -> -200; Total 400 -> +200."""
    _seed_users(); fid = _seed_patient("R40 Script")
    try:
        caps, restore = _patch_msgs()
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None:
            restore(); return
        try:
            from src.ui import clinical_session_entry as _entry
            tab.app.chart_teeth = lambda: []
            _entry.set_money(tab, 0, 500)
            tab.btn_save_visit.invoke(); root.update_idletasks()
            assert patient_totals(fid)["remaining"] == -500.0
            _save_session(tab, 300, 0, date="2026-11-12")
            root.update_idletasks()
            assert patient_totals(fid)["remaining"] == -200.0
            _save_session(tab, 400, 0, date="2026-11-13")
            root.update_idletasks()
            assert patient_totals(fid) == {"total": 700.0, "paid": 500.0,
                                           "remaining": 200.0}
            kinds = [r[3] for r in _money_rows(fid)]
            assert kinds == ["payment", "session", "session"], kinds
            assert not caps["error"], caps
        finally:
            root.destroy(); restore()
    finally:
        _cleanup(fid)


def test_money_only_save_against_existing_session():
    """A session exists for the entry date; a later money-only
    Save (no texts) writes just the money, same split rule."""
    _seed_users(); fid = _seed_patient("R40 MoneyOnly")
    try:
        caps, restore = _patch_msgs()
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None:
            restore(); return
        try:
            from src.ui import clinical_session_entry as _entry
            _save_session(tab, 200, 0); root.update_idletasks()
            _entry.set_money(tab, 0, 150)  # texts were cleared by save
            tab.btn_save_visit.invoke(); root.update_idletasks()
            assert not caps["error"], caps
            assert patient_totals(fid) == {"total": 200.0, "paid": 150.0,
                                           "remaining": 50.0}
            assert _rows(fid) == 2
        finally:
            root.destroy(); restore()
    finally:
        _cleanup(fid)


def test_refusals_kept():
    """Negative amounts and an untouched 0/0 Save write nothing."""
    _seed_users(); fid = _seed_patient("R40 Refuse")
    try:
        caps, restore = _patch_msgs()
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None:
            restore(); return
        try:
            from src.ui import clinical_session_entry as _entry
            tab.btn_save_visit.invoke(); root.update_idletasks()
            assert caps["error"] and _rows(fid) == 0, caps
            _fill_texts(tab)
            tab.e_sess_tooth.delete(0, tk.END); tab.e_sess_tooth.insert(0, "11")
            _entry.set_money(tab, 100, -5)
            tab.btn_save_visit.invoke(); root.update_idletasks()
            assert caps["error"] and _rows(fid) == 0, caps
            assert patient_totals(fid) == {"total": 0.0, "paid": 0.0,
                                           "remaining": 0.0}
        finally:
            root.destroy(); restore()
    finally:
        _cleanup(fid)
