"""Current-medications-field Templates button for the patient
form (R57, Section C).

Round 57: the Allergies and Diseases fields each have a Templates
button; Current Medications had none. The wiring mirrors
patient_allergies.py exactly -- same button label, same
EntryTextAdapter bridge to the single-line RoundedEntry, comma
separation -- but the picker is the medications picker
(medication_picker.open_medication_picker): the 463-drug
medications data, searchable by generic name, with its own
Arabic | English choice (field_lang category "medication"),
multi-select insert, and Ctrl+C / Ctrl+V clipboard support.
The patient form is at the 200-line cap, so the wiring lives
here. <200 lines.
"""
import tkinter as tk

from src.config.strings_r19_patient import tr as _tr19
from src.ui.patient_diseases import EntryTextAdapter
from src.ui.rounded import rounded_button


def open_medication_picker(parent, entry, lang="en"):
    """Open the medication templates picker over the meds entry
    (Append default in the picker)."""
    from src.ui.medication_picker import open_medication_picker as _open
    return _open(parent, entry, lang=lang)


def make_medications_button(parent, entry, lang="en"):
    """The Templates button beside the Current Medications field
    (same bilingual label as the allergies/diseases buttons).
    Returned un-gridded; the form grids it. `medications_entry`
    is a test/inspection hook."""
    btn = rounded_button(
        parent, text=_tr19("r19.diseases_templates_btn", lang),
        relief="flat",
        command=lambda: open_medication_picker(parent, entry, lang))
    btn.medications_entry = entry
    return btn
