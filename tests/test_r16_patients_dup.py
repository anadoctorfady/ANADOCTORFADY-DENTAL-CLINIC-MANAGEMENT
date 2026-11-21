"""Round 16 worker A (patients): duplicate-patient refusal.

Adding a patient whose first + father + family name (strip +
casefold) matches an existing patient is refused -- even when the
birth date differs -- with a bilingual message naming the existing
file number and an option to open that patient. Helpers live in
tests.test_r16_patients. Seeded rows are cleaned up. GUI tests skip
with no display; run with DISPLAY=:98 under Xvfb.
"""
from src.models.database import init_db
from src.models.patients import (DuplicatePatientError, find_duplicate)
from tests.test_r16_patients import (_attempt, _cleanup, _row, _seed)


def test_duplicate_refused_names_file_number():
    """Same first + father + family, DIFFERENT birth date: refused,
    the message names the existing file number, no row is added."""
    init_db()
    fid = _seed("R16Dup", "R16Dad", "R16Fam", birth="1990-05-15")
    try:
        got = _attempt("R16Dup", "R16Dad", "", "R16Fam",
                       birth="01/01/2001", ask_answer=False)
        if got is None:
            print("SKIP test_duplicate_refused_names_file_number (no display)"); return
        assert got["ask"], "no duplicate dialog shown"
        assert str(fid) in got["ask"][0][1], got["ask"]
        assert got["after"] == got["before"], "duplicate save inserted a row"
        assert got["selected"] is None
    finally:
        _cleanup(fid)


def test_duplicate_case_whitespace_variant_refused():
    """Case / surrounding-space variants of the same three names are
    the same duplicate and are refused with the same file number."""
    init_db()
    fid = _seed("R16Dup", "R16Dad", "R16Fam", birth="1990-05-15")
    try:
        got = _attempt("  r16dup ", "R16DAD", "", "r16fam",
                       birth="02/02/2002", ask_answer=False)
        if got is None:
            print("SKIP test_duplicate_case_whitespace_variant_refused (no display)"); return
        assert got["ask"] and str(fid) in got["ask"][0][1], got["ask"]
        assert got["after"] == got["before"]
    finally:
        _cleanup(fid)


def test_duplicate_open_existing_option():
    """Answering Yes on the duplicate dialog opens the existing
    patient (load + select are called with its file number)."""
    init_db()
    fid = _seed("R16Dup", "R16Dad", "R16Fam", birth="1990-05-15")
    try:
        got = _attempt("R16Dup", "R16Dad", "", "R16Fam",
                       birth="03/03/2003", ask_answer=True)
        if got is None:
            print("SKIP test_duplicate_open_existing_option (no display)"); return
        assert got["selected"] == fid, got
        assert got["loaded"] >= 1
        assert got["after"] == got["before"]
    finally:
        _cleanup(fid)


def test_duplicate_helper_direct():
    """find_duplicate() is case/space-insensitive and skips the file
    being edited; save_patient_record() raises DuplicatePatientError."""
    init_db()
    fid = _seed("R16Dup", "R16Dad", "R16Fam", birth="1990-05-15")
    try:
        assert find_duplicate("R16Dup", "R16Dad", "R16Fam") == fid
        assert find_duplicate("  R16DUP ", "r16dad", "R16FAM") == fid
        assert find_duplicate("R16Dup", "R16Dad", "R16Fam",
                              exclude_file=fid) is None
        assert find_duplicate("Nobody", "R16Dad", "R16Fam") is None
        try:
            _seed("R16Dup", "R16Dad", "R16Fam", birth="2000-01-01")
            raise AssertionError("duplicate seed was not refused")
        except DuplicatePatientError as e:
            assert e.file_number == fid
    finally:
        _cleanup(fid)


def test_different_name_save_succeeds():
    """Same father + family but a different first name is a different
    patient and saves fine."""
    init_db()
    fid = _seed("R16Dup", "R16Dad", "R16Fam", birth="1990-05-15")
    try:
        got = _attempt("R16Other", "R16Dad", "", "R16Fam")
        if got is None:
            print("SKIP test_different_name_save_succeeds (no display)"); return
        try:
            assert not got["errors"] and not got["ask"], (got["errors"], got["ask"])
            assert got["selected"] is not None and got["selected"] != fid
            assert got["after"] == got["before"] + 1
        finally:
            if got["selected"]: _cleanup(got["selected"])
    finally:
        _cleanup(fid)


def test_grandfather_empty_save_succeeds():
    """Round-15 regression: empty grandfather still saves, and the
    stored full_name has no double space."""
    got = _attempt("R16Grand", "R16Dad", "", "R16Fam")
    if got is None:
        print("SKIP test_grandfather_empty_save_succeeds (no display)"); return
    fid = got["selected"]
    try:
        assert not got["errors"], got["errors"]
        assert fid is not None
        assert _row(fid)["full_name"] == "R16Grand R16Dad R16Fam", _row(fid)
    finally:
        if fid: _cleanup(fid)


def test_edit_same_patient_not_duplicate():
    """Re-saving the SAME patient (e.g. adding diseases) is not a
    duplicate of itself."""
    init_db()
    fid = _seed("R16Edit", "R16Dad", "R16Fam", birth="1990-05-15")
    try:
        got = _attempt("", "", "", "", patient={"file_number": fid},
                       fill_row=_row(fid), diseases="Asthma")
        if got is None:
            print("SKIP test_edit_same_patient_not_duplicate (no display)"); return
        assert not got["errors"] and not got["ask"], (got["errors"], got["ask"])
        assert got["selected"] == fid
        assert got["after"] == got["before"], "edit inserted a new row"
        assert _row(fid)["diseases"] == "Asthma", _row(fid)
    finally:
        _cleanup(fid)
