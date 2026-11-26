"""Round 48, item 2 (owner question 2026-11-23): is there an
option to choose the default nationality? There was none — the
patient form hardcoded "Syrian". Now Settings carries a
"Default nationality / الجنسية الافتراضية" searchable picker
(the same 249-nationality list + EN/AR search behaviour as the
patient form's own picker), stored as the `default_nationality`
setting (EN canonical). Unset or blank -> "Syrian", exactly as
before. The setting feeds NEW patients only: the form's initial
value and its clear() reset; editing an existing patient still
shows that patient's own stored nationality, and the DB column
default is untouched.

Pins:
  1. unset setting -> helper and a fresh form both say Syrian;
  2. setting = Jordanian -> a fresh form (and its clear()) opens
     with Jordanian;
  3. fill() of an existing Egyptian patient shows Egyptian even
     while the default is Jordanian;
  4. the Settings field round-trips: initial value, EN + AR
     labels, save persists the EN canonical name, and a rebuilt
     section + a fresh form both pick it up.
"""
import tkinter as tk
from unittest import mock

from src.models.database import get_setting, set_setting
from src.utils.nationalities import (default_nationality_en,
                                     default_nationality_display)
from tests.test_r16_print import isolated_db


class _Stub:
    lang = "en"
    current_patient = None

    def on_teeth_select(self, *a): pass
    def print_pdf(self, *a): pass
    def load_patients(self): pass
    def select_patient(self, *a): pass


def _root():
    try:
        return tk.Tk()
    except tk.TclError:
        return None


def _form(root):
    from src.ui.patient_form import PatientForm
    form = PatientForm(root, _Stub())
    form.pack()
    root.update_idletasks()
    return form


def test_unset_default_is_syrian():
    with isolated_db():
        conn_setting = get_setting("default_nationality", "")
        assert (conn_setting or "") == ""
        assert default_nationality_en() == "Syrian"
        assert default_nationality_display("en") == "Syrian"
        root = _root()
        if root is None:
            return
        try:
            root.withdraw()
            form = _form(root)
            assert form.nat.get() == "Syrian", form.nat.get()
        finally:
            root.destroy()


def test_configured_default_used_for_new_patients():
    with isolated_db():
        set_setting("default_nationality", "Jordanian")
        assert default_nationality_en() == "Jordanian"
        root = _root()
        if root is None:
            return
        try:
            root.withdraw()
            form = _form(root)
            assert form.nat.get() == "Jordanian", form.nat.get()
            form.nat.set("Egyptian")  # user picks something else
            form.clear()              # reset for the NEXT new patient
            assert form.nat.get() == "Jordanian", form.nat.get()
        finally:
            root.destroy()


def test_existing_patient_keeps_own_nationality():
    with isolated_db():
        set_setting("default_nationality", "Jordanian")
        root = _root()
        if root is None:
            return
        try:
            root.withdraw()
            form = _form(root)
            row = {"first_name": "Test", "father_name": "F",
                   "grand_name": "G", "last_name": "L",
                   "birth_date_greg": "1990-05-15", "mobile1": "",
                   "mobile2": "", "emergency_phone": "", "address": "",
                   "nationality": "Egyptian", "current_medications": "",
                   "allergies": "", "diseases": "", "file_number": 999,
                   "age_years": 36, "age_months": 5, "age_days": 21,
                   "age_hijri_years": 37, "age_hijri_months": 0,
                   "age_hijri_days": 0}
            form.fill(row)
            assert form.nat.get() == "Egyptian", form.nat.get()
        finally:
            root.destroy()


def test_settings_field_roundtrip():
    root = _root()
    if root is None:
        return
    try:
        root.withdraw()
        with isolated_db():
            from src.ui import settings_storage_ui as SUI
            assert SUI._s("settings.default_nationality", "en") == \
                "Default nationality:"
            assert SUI._s("settings.default_nationality", "ar") == \
                "الجنسية الافتراضية:"
            tab = tk.Frame(root); tab.lang = "en"
            body = tk.Frame(root)
            SUI.attach_storage_section(body, tab)
            root.update()
            # Unset -> the picker shows Syrian, as the form did.
            assert tab.default_nationality_var.get() == "Syrian"
            tab.default_nationality_var.set("Lebanese")
            with mock.patch.object(SUI.messagebox, "showinfo"):
                SUI.save_storage(tab)
            # Stored as the EN canonical name...
            assert get_setting("default_nationality", "") == "Lebanese"
            # ...and a fresh patient form opens with it.
            form = _form(root)
            assert form.nat.get() == "Lebanese", form.nat.get()
    finally:
        root.destroy()
