"""Round 26: the two remaining SearchableCombobox hosts get the
round-25 popup-picker pattern (owner-approved follow-up).
Before: SearchableCombobox._on_key rewrote its values on every
<KeyRelease> but NEVER opened the popdown, so typed filtering was
invisible in (1) the patient form's NATIONALITY combobox and
(2) the prescription DRUG combobox. Both are now
ui.searchable_picker.SearchablePicker: click (or a printable key)
opens a popup whose filter entry has focus; typing narrows the
VISIBLE list live (filter_list over code / EN / AR fields).
Pinned contracts, unchanged from the combobox era: nationality —
nat var holds the ONE-language display, the stored value still
comes from nationality_en_for(nat.get()), default Syrian, all
249 values listed. Drug — drug_var holds medications.display()
in the app language, generic_for() resolves it, picking still
fires on_drug -> dose auto-fill from the stored strength
(round 23) and the penicillin/allergy + interaction alerts, and
the category-first contract (cb_drug._items / ["values"] follow
cb_cat) holds. GUI tests skip gracefully with no display."""
import tkinter as tk
from types import SimpleNamespace

from src.models.database import init_db
from src.ui.patient_form import PatientForm
from src.ui.prescriptions import PrescriptionsTab
from src.utils.medications import (categories, display, generic_for,
    list_by_category, list_medications)
from src.utils.nationalities import (display_for, list_nationalities,
    nationality_en_for)
from tests.test_clinical_save_gate import _stub_app
AMOX_EN = "Amoxicillin (Amoxil) — Capsule 500 mg"
AMOX_AR = "أموكسيسيلين — Capsule 500 mg"


def _root():
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw()
    return root


def _type(picker, text, root):
    """Type into the popup's filter entry (real KeyRelease path)."""
    if picker.popup is None:
        picker.open_popup()
    entry = picker.popup_entry.widget  # RoundedEntry's inner Entry
    entry.focus_force(); root.update_idletasks()
    entry.delete(0, tk.END); entry.insert(0, text)
    entry.event_generate("<KeyRelease>", when="now")
    root.update_idletasks()
    return picker.visible_values()


def _pick(picker, display_text, root):
    """Pick `display_text` from the open popup, as a mouse click."""
    vis = picker.visible_values()
    assert display_text in vis, (display_text, vis[:8])
    idx = vis.index(display_text)
    lb = picker.popup_listbox
    lb.selection_clear(0, tk.END); lb.selection_set(idx); lb.activate(idx)
    picker._pick_current()
    root.update_idletasks()
    assert picker.popup is None, "picking did not close the popup"


def _form(root, lang):
    init_db()
    form = PatientForm(root, _stub_app(lang=lang))
    form.pack(); root.update_idletasks()
    return form


def _rx(root, lang, patient=None):
    rx = PrescriptionsTab(root, _stub_app(patient or {"file_number": 0},
                                          lang=lang), narrow=True)
    rx.pack(); root.update_idletasks()
    return rx

def test_gui_nationality_en():
    root = _root()
    if root is None:
        print("SKIP r26 nationality EN (no display)"); return
    try:
        form = _form(root, "en")
        picker = form.e_nat
        assert form.nat.get() == "Syrian"  # default preserved
        assert len(picker["values"]) == len(list_nationalities()) == 249
        # Type-ahead: a printable key on the closed control opens it.
        picker._on_control_key(SimpleNamespace(char="e"))
        root.update_idletasks()
        assert picker.popup is not None and picker.visible_values()
        picker.close_popup()
        vis = _type(picker, "egy", root)
        assert vis and vis[0] == "Egyptian", vis[:5]
        assert len(vis) < 20, len(vis)  # visibly narrowed
        _pick(picker, "Egyptian", root)
        assert form.nat.get() == "Egyptian"
        # The stored value is exactly what the old control produced.
        assert nationality_en_for(form.nat.get()) == "Egyptian"
        # First letter alone already narrows, F-names lead.
        vis = picker.set_filter("f")
        assert vis and vis[0].startswith("F") and len(vis) < 249, vis[:5]
        picker.close_popup()
        # Esc closes without changing the selection.
        keep = form.nat.get()
        picker.open_popup(); root.update_idletasks()
        picker.popup_listbox.event_generate("<Escape>")
        root.update_idletasks()
        assert picker.popup is None and form.nat.get() == keep
    finally:
        root.destroy()


def test_gui_nationality_ar():
    root = _root()
    if root is None:
        print("SKIP r26 nationality AR (no display)"); return
    try:
        form = _form(root, "ar")
        picker = form.e_nat
        assert form.nat.get() == display_for("Syrian", "ar")
        assert len(picker["values"]) == 249
        vis = _type(picker, "مصر", root)  # country name finds it
        assert vis and vis[0] == "مصري", vis[:5]
        _pick(picker, "مصري", root)
        assert form.nat.get() == "مصري"
        assert nationality_en_for(form.nat.get()) == "Egyptian"
        vis = picker.set_filter("مصري")  # nationality adjective too
        assert vis and vis[0] == "مصري", vis[:5]
        picker.close_popup()
    finally:
        root.destroy()


def test_gui_drug_picker_en_dose_and_allergy_alert():
    root = _root()
    if root is None:
        print("SKIP r26 drug EN (no display)"); return
    try:
        patient = {"file_number": 0, "allergies": "Penicillin", "current_medications": ""}
        rx = _rx(root, "en", patient)
        picker = rx.cb_drug
        assert len(picker["values"]) == len(list_medications()) == 463  # R49 count pin (was 315)
        vis = _type(picker, "amox", root)
        assert AMOX_EN in vis and len(vis) <= 6, vis
        rx.e_dose.delete(0, tk.END); rx.e_dose.insert(0, "111 mg")
        _pick(picker, AMOX_EN, root)
        assert rx.drug_var.get() == AMOX_EN
        assert generic_for(rx.drug_var.get()) == "Amoxicillin"
        # Round 23 wiring survives: Dose <- the stored strength.
        assert rx.e_dose.get() == "500 mg", rx.e_dose.get()
        # The penicillin-allergy alert still fires on selection.
        assert rx.alerts, "no alerts for a penicillin-allergic patient"
        assert rx.alert_box.cget("text"), "alert box stayed empty"
    finally:
        root.destroy()


def test_gui_drug_picker_ar():
    root = _root()
    if root is None:
        print("SKIP r26 drug AR (no display)"); return
    try:
        rx = _rx(root, "ar")
        picker = rx.cb_drug
        vis = _type(picker, "أموكسيسيلين", root)
        assert vis and vis[0] == AMOX_AR, vis[:5]
        rx.e_dose.delete(0, tk.END); rx.e_dose.insert(0, "111 mg")
        _pick(picker, AMOX_AR, root)
        assert rx.drug_var.get() == AMOX_AR
        assert generic_for(rx.drug_var.get()) == "Amoxicillin"
        assert rx.e_dose.get() == "500 mg", rx.e_dose.get()
    finally:
        root.destroy()


def test_gui_drug_picker_category_contract_intact():
    root = _root()
    if root is None:
        print("SKIP r26 drug category contract (no display)"); return
    try:
        rx = _rx(root, "en")
        cat = next(c for c in categories() if c != "All" and len(list_by_category(c)) >= 2)
        rx.cat_var.set(cat)
        rx.on_category()  # the handler <<ComboboxSelected>> fires
        root.update_idletasks()
        expected = list_by_category(cat)
        assert rx.cb_drug._items == expected
        assert list(rx.cb_drug["values"]) == [display(i, "en") for i in expected]
        # Filtering now searches WITHIN the category's drugs only.
        first = expected[0]
        needle = first["generic_en"][:4].lower()
        vis = _type(rx.cb_drug, needle, root)
        assert display(first, "en") in vis, (needle, vis[:5])
        assert len(vis) <= len(expected)
        _pick(rx.cb_drug, display(first, "en"), root)
        assert generic_for(rx.drug_var.get()) == first["generic_en"]
    finally:
        root.destroy()
