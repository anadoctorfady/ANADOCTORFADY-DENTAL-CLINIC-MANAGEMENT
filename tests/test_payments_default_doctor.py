"""Treating-doctor default = patient's LAST VISIT doctor (Round 12,
final integration, fix (a)): the selector in the clinical Cost
section must default to the doctor of the patient's most recent
payment row, not to whoever is logged in. No visit yet -> the old
fallback (logged-in doctor; first doctor for a nurse). Doctorless
rows and doctors no longer in the user list are ignored.
Helpers live in tests/test_payments_e2e.py. GUI tests skip with no display."""
from src.models.database import save_financial
from src.models.finance import last_treating_doctor
from src.utils.auth import list_doctors
from tests.test_payments_e2e import (TODAY, _seed_users, _seed_patient,
                                     _cleanup, _build_clinical)


def test_last_treating_doctor_model():
    """Model: latest payment row wins; doctorless rows skipped; None
    when the patient has no payment with a doctor recorded."""
    _seed_users()
    fid = _seed_patient("LastDoc")
    try:
        assert last_treating_doctor(fid) is None
        save_financial(fid, "11", 100000, 50000, TODAY, doctor=None,
                       entered_by="doc_x")
        assert last_treating_doctor(fid) is None
        save_financial(fid, "11", 200000, 100000, TODAY, doctor="doc_x",
                       entered_by="doc_x")
        assert last_treating_doctor(fid) == "doc_x"
        save_financial(fid, "11", 300000, 150000, TODAY, doctor="doc_y",
                       entered_by="doc_y")
        assert last_treating_doctor(fid) == "doc_y"
    finally:
        _cleanup(fid)


def test_default_is_last_visit_doctor():
    """Payments by doc_x, then doc_y (later row): opening the file as
    doc_x must still default the selector to doc_y (last visit)."""
    _seed_users()
    fid = _seed_patient("LastDocGui")
    try:
        save_financial(fid, "11", 100000, 50000, TODAY, doctor="doc_x",
                       entered_by="doc_x")
        save_financial(fid, "11", 300000, 150000, TODAY, doctor="doc_y",
                       entered_by="doc_y")
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None:
            print("SKIP test_default_is_last_visit_doctor (no display)")
            return
        try:
            assert tab.doctor_var.get() == "doc_y", tab.doctor_var.get()
        finally:
            root.destroy()
    finally:
        _cleanup(fid)


def test_last_visit_beats_logged_in_doctor():
    """Single payment by doc_x; opening as doc_y (or the nurse) must
    default to doc_x, not to the logged-in user."""
    _seed_users()
    fid = _seed_patient("LastDocGui2")
    try:
        save_financial(fid, "11", 100000, 50000, TODAY, doctor="doc_x",
                       entered_by="nurse1")
        for user, role in (("doc_y", "doctor"), ("nurse1", "nurse")):
            root, tab = _build_clinical(user, role, fid)
            if tab is None:
                print("SKIP test_last_visit_beats_logged_in_doctor (no display)")
                return
            try:
                assert tab.doctor_var.get() == "doc_x", (user, tab.doctor_var.get())
            finally:
                root.destroy()
    finally:
        _cleanup(fid)


def test_no_visit_falls_back_to_logged_in():
    """No payments at all: doctor keeps the old fallback (themselves),
    a nurse gets the first doctor in the list."""
    _seed_users()
    fid = _seed_patient("LastDocGui3")
    try:
        root, tab = _build_clinical("doc_y", "doctor", fid)
        if tab is None:
            print("SKIP test_no_visit_falls_back_to_logged_in (no display)")
            return
        try:
            assert tab.doctor_var.get() == "doc_y", tab.doctor_var.get()
        finally:
            root.destroy()
        root, tab = _build_clinical("nurse1", "nurse", fid)
        try:
            assert tab.doctor_var.get() == list_doctors()[0], tab.doctor_var.get()
        finally:
            root.destroy()
    finally:
        _cleanup(fid)


def test_unknown_last_doctor_falls_back():
    """Latest payment names a doctor who is not in the user list
    (deleted/renamed): fall back to the logged-in doctor, not a name
    the combobox cannot offer."""
    _seed_users()
    fid = _seed_patient("LastDocGui4")
    try:
        save_financial(fid, "11", 100000, 50000, TODAY, doctor="doc_x",
                       entered_by="doc_x")
        save_financial(fid, "11", 200000, 100000, TODAY, doctor="ghost",
                       entered_by="doc_x")
        root, tab = _build_clinical("doc_y", "doctor", fid)
        if tab is None:
            print("SKIP test_unknown_last_doctor_falls_back (no display)")
            return
        try:
            assert tab.doctor_var.get() == "doc_y", tab.doctor_var.get()
            assert tab.doctor_var.get() in list_doctors()
        finally:
            root.destroy()
    finally:
        _cleanup(fid)
