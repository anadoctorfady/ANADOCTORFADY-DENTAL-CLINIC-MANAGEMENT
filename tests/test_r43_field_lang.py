"""Round 43 (item 1, EXPANDED by the owner's clarification):
a per-place Arabic | English template-language selector in EVERY
place templates are offered -- each clinical field's picker, the
patient-form disease/allergy pickers, referral templates, and
the Template Manager per browsed category. Each place's choice
persists per category (settings template_lang_field_<key>); the
round-31 global template_lang stays the default for places never
toggled. GUI tests drive the REAL picker + manager dialogs.
Skips without a display. <200 lines."""
import tkinter as tk
from tkinter import ttk

from src.models.database import get_setting, set_setting
from src.models.field_lang import (field_template_lang,
                                   set_field_template_lang)
from src.models.specialty_templates import set_template_lang_mode
from tests.test_templates_edit import (isolated_db, tmp_overrides,
                                       SEED_EN, SEED_AR)

DIAG_EN, DIAG_AR = "Deep caries", "تسوس عميق"
ALLERGY_EN, ALLERGY_AR = "Penicillin allergy", "حساسية للبنسلين"


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def _listbox(win):
    return next(w for w in _walk(win) if isinstance(w, tk.Listbox))


def _btn(win, prefix):
    for w in _walk(win):
        if isinstance(w, tk.Button) and str(w.cget("text")).startswith(prefix):
            return w


def _root():
    try:
        return tk.Tk()
    except tk.TclError:
        return None


def test_field_lang_model_defaults_and_persistence():
    with isolated_db():
        set_setting("language", "en")
        set_template_lang_mode("app")
        # Untouched place follows the global default (app -> en).
        assert field_template_lang("complaint") == "en"
        # Per-place override, persisted in settings (round-trip).
        set_field_template_lang("complaint", "ar")
        assert get_setting("template_lang_field_complaint") == "ar"
        assert field_template_lang("complaint") == "ar"
        # Independence: another place is untouched.
        assert field_template_lang("diagnosis") == "en"
        # Category normalisation: symptom/symptoms share ONE key.
        set_field_template_lang("symptom", "ar")
        assert get_setting("template_lang_field_symptoms") == "ar"
        assert field_template_lang("symptoms") == "ar"
        # Global default moves untouched places only.
        set_template_lang_mode("ar")
        assert field_template_lang("diagnosis") == "ar"
        assert field_template_lang("complaint") == "ar"  # own choice
        set_field_template_lang("complaint", "en")
        assert field_template_lang("complaint") == "en"  # beats global
        # Clearing an override returns the place to the default.
        set_field_template_lang("complaint", "bogus")
        assert field_template_lang("complaint") == "ar"
        set_template_lang_mode("app")


def test_picker_two_fields_two_languages_gui():
    root = _root()
    if root is None:
        print("SKIP r43 picker gui (no display)"); return
    root.withdraw()
    try:
        with tmp_overrides(), isolated_db():
            from src.ui.phrase_picker import open_template_picker
            set_setting("language", "en"); set_template_lang_mode("app")
            txt_c, txt_d = tk.Text(root), tk.Text(root)
            # Complaint: default EN, toggle to AR, insert Arabic.
            win = open_template_picker(root, "complaint", txt_c, "fady", lang="en")
            root.update_idletasks()
            rows = _listbox(win).get(0, tk.END)
            assert any(SEED_EN.upper() in r for r in rows), rows[:3]
            win.field_lang_toggle.lang_buttons["ar"].invoke()
            root.update_idletasks()
            rows = _listbox(win).get(0, tk.END)
            assert any(SEED_AR in r for r in rows), rows[:3]
            assert not any(SEED_EN.upper() in r for r in rows)
            box = _listbox(win)
            box.selection_set(next(i for i, r in enumerate(rows) if SEED_AR in r))
            _btn(win, "Insert").invoke(); root.update_idletasks()
            assert SEED_AR in txt_c.get("1.0", tk.END)
            assert not win.winfo_exists()
            # Diagnosis SIMULTANEOUSLY stays English (its own place).
            win = open_template_picker(root, "diagnosis", txt_d, "fady", lang="en")
            root.update_idletasks()
            rows = _listbox(win).get(0, tk.END)
            assert any(DIAG_EN.upper() in r for r in rows), rows[:3]
            assert not any(DIAG_AR in r for r in rows)
            box = _listbox(win)
            box.selection_set(next(i for i, r in enumerate(rows)
                                   if DIAG_EN.upper() in r))
            _btn(win, "Insert").invoke(); root.update_idletasks()
            assert DIAG_EN.upper() in txt_d.get("1.0", tk.END)
            # Persisted per place, and a REOPENED picker remembers.
            assert get_setting("template_lang_field_complaint") == "ar"
            win = open_template_picker(root, "complaint", txt_c, "fady", lang="en")
            root.update_idletasks()
            rows = _listbox(win).get(0, tk.END)
            assert any(SEED_AR in r for r in rows)
            win.destroy()
    finally:
        root.destroy()


def test_manager_and_allergy_picker_independent_gui():
    root = _root()
    if root is None:
        print("SKIP r43 manager gui (no display)"); return
    root.withdraw()
    try:
        with tmp_overrides(), isolated_db():
            from src.ui.template_manager import open_template_manager
            from src.ui.phrase_picker import open_template_picker
            set_setting("language", "en"); set_template_lang_mode("app")
            set_field_template_lang("complaint", "en")
            mgr = open_template_manager(root, "fady", lang="en")
            root.update_idletasks()
            rows = _listbox(mgr).get(0, tk.END)
            assert any(SEED_EN.upper() in r for r in rows), rows[:3]
            # Manager toggle -> Arabic for the browsed category.
            mgr.field_lang_toggle.lang_buttons["ar"].invoke()
            root.update_idletasks()
            rows = _listbox(mgr).get(0, tk.END)
            assert any(SEED_AR in r for r in rows), rows[:3]
            # Switch category: diagnosis has its OWN (unset) choice.
            combo = next(w for w in _walk(mgr) if isinstance(w, ttk.Combobox))
            combo.set("diagnosis"); combo.event_generate("<<ComboboxSelected>>")
            root.update_idletasks()
            rows = _listbox(mgr).get(0, tk.END)
            assert any(DIAG_EN.upper() in r for r in rows), rows[:3]
            assert get_setting("template_lang_field_complaint") == "ar"
            assert get_setting("template_lang_field_diagnosis", "") == ""
            assert field_template_lang("diagnosis") == "en"
            mgr.destroy()
            # A patient-form picker (allergy) is independent too.
            txt = tk.Text(root)
            win = open_template_picker(root, "allergy", txt, "fady", lang="en")
            root.update_idletasks()
            rows = _listbox(win).get(0, tk.END)
            assert any(ALLERGY_EN.upper() in r for r in rows), rows[:3]
            win.field_lang_toggle.lang_buttons["ar"].invoke()
            root.update_idletasks()
            rows = _listbox(win).get(0, tk.END)
            assert any(ALLERGY_AR in r for r in rows), rows[:3]
            assert field_template_lang("complaint") == "ar"  # unchanged
            assert field_template_lang("allergy") == "ar"
            assert field_template_lang("diagnosis") == "en"  # unchanged
            win.destroy()
    finally:
        root.destroy()
