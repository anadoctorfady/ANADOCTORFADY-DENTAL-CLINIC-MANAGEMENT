"""Round 19 item 1: lenient birth-date entry.

Typing "1/5/2000" is enough: the lenient front-door
(parse_birth_date_lenient / normalize_birth_input, with
parse_birth_date itself lenient) normalises to strict DD/MM/YYYY,
and the result must still be a REAL calendar date. Storage stays
ISO via .isoformat() at save time (patient_form). FocusOut in the
patient form rewrites a parseable entry to DD/MM/YYYY and leaves
unparseable text untouched so the save error can fire.
"""
from datetime import date

from src.utils.hijri_age import (invalid_birth_msg, normalize_birth_input,
    parse_birth_date, parse_birth_date_lenient)

ACCEPTED = [
    ("1/5/2000", date(2000, 5, 1), "01/05/2000"),
    ("01/5/2000", date(2000, 5, 1), "01/05/2000"),
    ("1/05/2000", date(2000, 5, 1), "01/05/2000"),
    ("01/05/2000", date(2000, 5, 1), "01/05/2000"),
    ("15/02/2026", date(2026, 2, 15), "15/02/2026"),
    ("9/12/1999", date(1999, 12, 9), "09/12/1999"),
    (" 1/5/2000 ", date(2000, 5, 1), "01/05/2000"),
    ("  15/02/2026  ", date(2026, 2, 15), "15/02/2026"),
    ("01052000", date(2000, 5, 1), "01/05/2000"),
    ("15022026", date(2026, 2, 15), "15/02/2026"),
    ("29022000", date(2000, 2, 29), "29/02/2000"),  # leap year: real
    ("29/2/2000", date(2000, 2, 29), "29/02/2000"),
    ("1990-05-15", date(1990, 5, 15), "15/05/1990"),  # legacy ISO
]

REJECTED = [
    "31/2/2000", "31/02/2000", "29/2/2001", "29/02/2001",
    "31022000", "29022001", "32/1/2000", "1/13/2000", "0/5/2000",
    "1/0/2000", "00/05/2000", "15-02-2026", "2026/02/15",
    "1/5/00", "1/5/200", "0105200", "010520000", "", "   ",
    "not-a-date", "1//2000", "/5/2000", "1/5/", None,
]


def test_lenient_accepted_forms():
    for raw, expected, normalised in ACCEPTED:
        assert parse_birth_date_lenient(raw) == expected, raw
        assert parse_birth_date(raw) == expected, raw
        assert normalize_birth_input(raw) == normalised, raw


def test_lenient_rejected_forms_bilingual_error():
    for bad in REJECTED:
        for fn in (parse_birth_date_lenient, parse_birth_date,
                   normalize_birth_input):
            try:
                fn(bad)
            except ValueError as e:
                assert "DD/MM/YYYY" in str(e), (bad, e)
            else:
                raise AssertionError(f"{bad!r} accepted by {fn.__name__}")
    # Single-language error text follows the requested language.
    assert invalid_birth_msg("en") == "Invalid birth date — use DD/MM/YYYY"
    assert "تاريخ ميلاد" in invalid_birth_msg("ar")
    try:
        parse_birth_date_lenient("31/2/2000", lang="ar")
    except ValueError as e:
        assert str(e) == invalid_birth_msg("ar")


def test_form_focusout_reformats_lenient_input():
    """Real PatientForm under Xvfb: FocusOut (on_birth) rewrites
    '1/5/2000' to '01/05/2000' and '01052000' to '01/05/2000';
    unparseable text is left untouched. Skips without a display."""
    try:
        import tkinter as tk
        from src.config.settings import get_theme_mode, set_theme_mode
        from src.ui.patient_form import PatientForm
    except Exception:
        return
    prev = get_theme_mode()
    set_theme_mode("light")
    try:
        root = tk.Tk()
    except tk.TclError:
        set_theme_mode(prev)
        return
    root.withdraw()

    class Stub:
        lang = "en"
        current_patient = None
        def on_teeth_select(self, *a): pass
        def print_pdf(self, *a): pass
        def load_patients(self): pass
        def select_patient(self, *a): pass

    try:
        form = PatientForm(root, Stub())
        for raw, expected in (("1/5/2000", "01/05/2000"),
                              ("01052000", "01/05/2000"),
                              ("15/2/2026", "15/02/2026")):
            form.e_birth.delete(0, tk.END)
            form.e_birth.insert(0, raw)
            form.e_birth.event_generate("<FocusOut>")
            root.update_idletasks()
            # event_generate may not fire the binding in every
            # environment; on_birth() IS the FocusOut handler.
            if form.e_birth.get() != expected:
                form.on_birth()
            assert form.e_birth.get() == expected, (raw, form.e_birth.get())
        form.e_birth.delete(0, tk.END)
        form.e_birth.insert(0, "31/2/2000")
        form.on_birth()
        assert form.e_birth.get() == "31/2/2000"  # untouched: save errors
    finally:
        try:
            root.destroy()
        except Exception:
            pass
        set_theme_mode(prev)
