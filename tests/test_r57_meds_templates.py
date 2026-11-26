"""Round 57, Section C: Current Medications Templates button +
picker (463-drug source, per-place AR | EN choice, multi-select
insert, Ctrl+C / Ctrl+V clipboard round-trip). Isolated DB only;
GUI tests need a display (the gate provides :98)."""
import tkinter as tk

from tests.test_r16_print import isolated_db


def _tk():
    # VISIBLE root (never withdrawn): the established GUI-test
    # pattern (test_r21_template_search) -- focus_force() +
    # event_generate(..., when="now") only fires reliably that way.
    try:
        return tk.Tk()
    except tk.TclError:
        return None


class _StubApp:
    lang = "en"
    current_patient = None

    def __init__(self, lang="en"):
        self.lang = lang

    def print_pdf(self):
        pass

    def load_patients(self):
        pass

    def select_patient(self, fid):
        pass


def _form(lang="en"):
    from src.ui.patient_form import PatientForm
    root = _tk()
    assert root is not None, "no display"
    form = PatientForm(root, _StubApp(lang))
    form.pack(); root.update_idletasks()
    return form, root


def test_meds_templates_button_present():
    """C: the meds field has a Templates button like allergies /
    diseases, same label, gridded beside the field (row 7 col 3);
    the field itself shrinks to columnspan 2. EN + AR."""
    for lang in ("en", "ar"):
        with isolated_db():
            form, root = _form(lang)
            try:
                assert hasattr(form, "btn_meds_templates")
                assert form.btn_meds_templates.cget("text") == \
                    form.btn_diseases_templates.cget("text")
                assert form.btn_meds_templates.grid_info()["row"] == 7
                assert form.btn_meds_templates.grid_info()["column"] == 3
                assert form.e_meds.grid_info()["columnspan"] == 2
                assert form.btn_meds_templates.medications_entry is form.e_meds
            finally:
                root.destroy()


def _open_picker(form, lang="en"):
    from src.ui.patient_medications import open_medication_picker
    win = open_medication_picker(form, form.e_meds, lang)
    form.update_idletasks()
    return win


def _search(win, query):
    win.search.delete(0, tk.END)
    win.search.insert(0, query)
    # The KeyRelease binding lives on the search entry's INNER widget
    # (RoundedEntry delegates bind there); generating on the frame
    # would not fire it. when="now" + focus_force: the queued form
    # never fires under Xvfb (cf. test_r21_template_search).
    win.search.entry.focus_force()
    win.search.entry.event_generate("<KeyRelease>", when="now")
    win.update_idletasks()


def test_medication_picker_insert_multiselect_and_language():
    """C: search finds drugs by generic name; multi-select inserts
    both, comma-separated; the AR toggle lists/inserts Arabic names;
    a repeat insert never duplicates a drug already in the field."""
    with isolated_db():
        form, root = _form("en")
        try:
            win = _open_picker(form)
            _search(win, "amox")
            assert win.listbox.size() >= 2, win.listbox.size()
            assert "Amoxicillin" in win.listbox.get(0)
            win.listbox.selection_set(0, 1)
            assert win.insert_selected()
            got = form.e_meds.get()
            parts = [p.strip() for p in got.split(",")]
            assert len(parts) == 2 and all(parts), got
            assert parts[0].startswith("Amoxicillin"), got
            # Arabic toggle: list + insert in Arabic (a drug NOT
            # already in the field -- the AR name of an inserted EN
            # drug dedupes by canonical generic, by design).
            win = _open_picker(form)
            win.field_lang_toggle.lang_buttons["ar"].invoke()
            form.update_idletasks()
            _search(win, "paracetamol")
            assert "باراسيتامول" in win.listbox.get(0), win.listbox.get(0)
            win.listbox.selection_set(0)
            assert win.insert_selected()
            assert "باراسيتامول" in form.e_meds.get()
            # No duplicates on a repeat insert of the same drug.
            before = form.e_meds.get()
            win = _open_picker(form)
            _search(win, "amox")
            win.listbox.selection_set(0)
            assert win.insert_selected() is False
            assert form.e_meds.get() == before
            win.destroy()
        finally:
            root.destroy()


def test_medication_picker_copy_paste_roundtrip():
    """C: Ctrl+C copies the selection to the system clipboard AND
    the clipboard history (Ctrl+Shift+V recalls it); Ctrl+V pastes
    clipboard text into the field."""
    from src.models.clipboard_history import list_clips
    with isolated_db():
        form, root = _form("en")
        try:
            win = _open_picker(form)
            _search(win, "amox")
            win.listbox.selection_set(0)
            # The Ctrl+C / Ctrl+V bindings live on the listbox's INNER
            # widget (RoundedListbox delegates bind there); focus +
            # when="now" (cf. _search above).
            win.listbox._inner.focus_force()
            win.listbox._inner.event_generate("<Control-c>", when="now")
            root.update_idletasks()
            assert root.clipboard_get() == "Amoxicillin", root.clipboard_get()
            assert any("Amoxicillin" in r["text"]
                       for r in list_clips(20)), list_clips(20)
            win.clipboard_clear()
            win.clipboard_append("Paracetamol, Ibuprofen")
            win.listbox._inner.event_generate("<Control-v>", when="now")
            root.update_idletasks()
            got = form.e_meds.get()
            assert "Paracetamol" in got and "Ibuprofen" in got, got
            win.destroy()
        finally:
            root.destroy()


def test_medication_picker_language_choice_persists():
    """C: the AR | EN choice is the per-place field_lang choice
    (template_lang_field_medication); a reopened picker honours it."""
    from src.models.field_lang import (field_template_lang,
                                       set_field_template_lang)
    with isolated_db():
        form, root = _form("en")
        try:
            assert field_template_lang("medication") in ("ar", "en")
            win = _open_picker(form)
            win.field_lang_toggle.lang_buttons["ar"].invoke()
            assert field_template_lang("medication") == "ar"
            win.destroy()
            win = _open_picker(form)
            assert "أموكسيسيلين" in win.listbox.get(0), win.listbox.get(0)
            win.destroy()
            set_field_template_lang("medication", "")
        finally:
            root.destroy()
