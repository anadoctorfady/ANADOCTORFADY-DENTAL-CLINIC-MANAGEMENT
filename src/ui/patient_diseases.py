"""Diseases-field Templates button for the patient form (R19-A).

The patient form is at the 200-line cap, so the diseases wiring
lives here. The existing phrase picker (phrase_picker) speaks the
tk.Text API ("1.0"..END), while the diseases field is a single-line
Entry (RoundedEntry): _EntryTextAdapter bridges the two so the
picker works unchanged. Append joins with ", " (the diseases field
is comma-separated); Replace overwrites. Only the app language is
ever shown/inserted: the picker already filters by app language
via search_phrases(lang=...) + template caps transform. <200 lines.
"""
import tkinter as tk

from src.config.strings_r19_patient import tr as _tr19
from src.ui.rounded import rounded_button


class EntryTextAdapter:
    """Text-widget facade over a single-line Entry widget.

    Picker calls: get("1.0", END), delete("1.0", END),
    insert("1.0", text) and insert(END, text). Append semantics:
    inserting at END onto non-empty content joins with ", " so
    diseases stay comma-separated; a leading separator/newline
    supplied by the picker's generic _insert is normalised away.
    """

    def __init__(self, entry):
        self._entry = entry

    def get(self, *_a, **_k):
        return self._entry.get()

    def delete(self, *_a, **_k):
        self._entry.delete(0, tk.END)

    def insert(self, index, text):
        text = (text or "").lstrip("\n, ").rstrip("\n")
        if not text:
            return
        if str(index) == "1.0":
            # Replace path: the picker deleted first, so just set.
            if self._entry.get():
                self._entry.delete(0, tk.END)
            self._entry.insert(0, text)
            return
        cur = self._entry.get().strip()
        self._entry.insert(tk.END, (", " if cur else "") + text)


def append_phrase(entry, text):
    """Append one already language-filtered phrase to the entry."""
    EntryTextAdapter(entry).insert(tk.END, text)


def open_disease_picker(parent, entry, lang="en"):
    """Open the existing template picker for category 'disease'
    over the diseases entry (Append default in the picker)."""
    from src.ui.phrase_picker import open_template_picker
    return open_template_picker(parent, "disease",
                                EntryTextAdapter(entry), lang=lang)


def make_diseases_button(parent, entry, lang="en"):
    """The Templates button that sits beside the diseases field.
    Its label comes from strings_r19_patient (app language only).
    The button object is returned un-gridded; the form grids it."""
    btn = rounded_button(
        parent, text=_tr19("r19.diseases_templates_btn", lang),
        relief="flat",
        command=lambda: open_disease_picker(parent, entry, lang))
    btn.diseases_entry = entry  # test/inspection hook
    return btn
