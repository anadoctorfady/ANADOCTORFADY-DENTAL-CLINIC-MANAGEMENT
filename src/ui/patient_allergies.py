"""Allergies-field Templates button for the patient form (R21).

Round 21 (item 12): the round-19 diseases Templates treatment,
applied to the ALLERGIES field -- a ready-made bilingual template
category ("allergy" in phrases.py, seeded in phrases_seed.json)
with a Templates button beside the allergies entry in the patient
form. The patient form is at the 200-line cap, so the wiring
lives here, mirroring patient_diseases.py exactly: the existing
phrase picker speaks the tk.Text API, EntryTextAdapter bridges
it to the single-line RoundedEntry, Append joins with ", ", and
only the app language is shown/inserted (EN in ALL CAPS at the
display/insert boundary, like every other template category).
<200 lines.
"""
import tkinter as tk

from src.config.strings_r19_patient import tr as _tr19
from src.ui.patient_diseases import EntryTextAdapter, append_phrase
from src.ui.rounded import rounded_button


def open_allergy_picker(parent, entry, lang="en"):
    """Open the template picker for category 'allergy' over the
    allergies entry (Append default in the picker)."""
    from src.ui.phrase_picker import open_template_picker
    return open_template_picker(parent, "allergy",
                                EntryTextAdapter(entry), lang=lang)


def make_allergies_button(parent, entry, lang="en"):
    """The Templates button beside the allergies field (same
    bilingual label as the diseases button). Returned un-gridded;
    the form grids it. `allergy_entry` is a test/inspection hook."""
    btn = rounded_button(
        parent, text=_tr19("r19.diseases_templates_btn", lang),
        relief="flat",
        command=lambda: open_allergy_picker(parent, entry, lang))
    btn.allergy_entry = entry
    return btn
