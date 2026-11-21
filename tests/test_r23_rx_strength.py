"""Round 23 wiring (item 4 follow-through): selecting a drug fills
the Dose entry from the drug's STORED strength.

The round-23 audit corrected every strength in medications.json,
but the prescription form never read it: Dose was free text with a
hard-coded "500 mg" default and on_drug only ran the interaction
check. Now on_drug also calls rx_form.fill_dose, which copies the
selected drug's stored strength into Dose (Amoxicillin -> "500 mg",
Ceftriaxone -> "1 g", Tobramycin -> "0.3%"); the entry stays fully
editable and the EDITED value is what add_item saves. The picker
rows show form + strength next to the name. A drug with NO stored
strength must leave the Dose entry exactly as the user left it.

Both hosts of the form are covered: the Clinical tab's section and
the shell's narrow Rx section (PrescriptionsTab narrow=True).
GUI tests skip gracefully with no display; run with DISPLAY=:98
against the isolated gate copy (ANADOCTORFADY_DATA_DIR).

Round 24 item 7 SUPERSESSION: display()/display_for() are now
single-language and take an explicit lang. This file's display
assertions pin lang="en" explicitly (the stub app is EN too)
instead of relying on the ambient language setting; the format
asserted is the EN form "Amoxicillin (Amoxil) — Capsule 500 mg".
AR display + legacy bilingual parsing live in test_r24_meds_lang.py.
"""
import tkinter as tk

from src.ui.clinical import ClinicalTab
from src.ui.prescriptions import PrescriptionsTab
from src.utils.medications import (display, display_for, generic_for,
    get_medication, list_medications, strength_for)
from tests.test_clinical_save_gate import _stub_app

FAKE = {"generic_en": "GateDrugNoStrength", "generic_ar": "",
        "brand_en": "GateBrand", "brand_ar": "", "category": "Other",
        "form": "Tablet", "strength": "", "class": ""}


def test_display_shows_form_and_strength_and_parses_back():
    text = display(get_medication("Amoxicillin"), "en")  # R24: explicit lang
    assert "Amoxicillin" in text and "Amoxil" in text
    assert "Capsule" in text and "500 mg" in text, text
    assert "1 g" in display_for("Ceftriaxone", "en")
    assert "Injection" in display_for("Ceftriaxone", "en")
    assert "0.3%" in display_for("Tobramycin", "en")
    # The "Name (Brand)" prefix is untouched: generic resolution and
    # the brand extraction used by add_item still round-trip.
    assert generic_for(text) == "Amoxicillin"
    assert text.split("(")[1].split(")")[0] == "Amoxil"
    assert strength_for("Amoxicillin") == "500 mg"
    assert strength_for("Ceftriaxone") == "1 g"
    assert strength_for("Tobramycin") == "0.3%"
    assert strength_for("No Such Drug XYZ") == ""


def _root():
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw()
    return root


def _build_clinical_rx():
    root = _root()
    if root is None:
        return None, None
    try:
        tab = ClinicalTab(root, _stub_app({"file_number": 0}))
        tab.pack()
        root.update_idletasks()
        return root, tab.rx_section
    except Exception:
        root.destroy()
        raise


def _build_narrow_rx():
    root = _root()
    if root is None:
        return None, None
    try:
        rx = PrescriptionsTab(root, _stub_app({"file_number": 0}),
                              narrow=True)
        rx.pack()
        root.update_idletasks()
        return root, rx
    except Exception:
        root.destroy()
        raise


def _pick(rx, generic, preset="111 mg"):
    """Preset a distinctive dose (so a fill is observable even for
    Amoxicillin, whose strength equals the old hard-coded default),
    then select the drug exactly as the combobox leaves it: the
    display string in drug_var + the <<ComboboxSelected>> handler."""
    rx.e_dose.delete(0, tk.END)
    rx.e_dose.insert(0, preset)
    rx.drug_var.set(display_for(generic, "en"))  # R24: stub app is EN
    rx.on_drug()


def _check_fills(build, generic, expected):
    root, rx = build()
    if rx is None:
        print(f"SKIP strength fill {generic} (no display)")
        return
    try:
        _pick(rx, generic)
        assert rx.e_dose.get() == expected, (generic, rx.e_dose.get())
    finally:
        root.destroy()


def test_amoxicillin_fills_500mg_both_hosts():
    _check_fills(_build_clinical_rx, "Amoxicillin", "500 mg")
    _check_fills(_build_narrow_rx, "Amoxicillin", "500 mg")


def test_ceftriaxone_fills_1g_both_hosts():
    _check_fills(_build_clinical_rx, "Ceftriaxone", "1 g")
    _check_fills(_build_narrow_rx, "Ceftriaxone", "1 g")


def test_tobramycin_fills_percent():
    _check_fills(_build_clinical_rx, "Tobramycin", "0.3%")


def test_filled_dose_stays_editable_and_edit_is_what_saves():
    root, rx = _build_clinical_rx()
    if rx is None:
        print("SKIP editable dose (no display)")
        return
    try:
        _pick(rx, "Amoxicillin")
        assert rx.e_dose.get() == "500 mg"  # auto-filled
        rx.e_dose.delete(0, tk.END)
        rx.e_dose.insert(0, "250 mg")  # doctor overrides it
        rx.add_item()
        assert len(rx.items) == 1
        assert rx.items[0]["generic"] == "Amoxicillin"
        assert rx.items[0]["brand"] == "Amoxil"
        assert rx.items[0]["dose"] == "250 mg"  # the EDIT, not the fill
        row = rx.tree.item(rx.tree.get_children()[0], "values")
        assert row[1] == "250 mg"
    finally:
        root.destroy()


def test_drug_without_strength_leaves_dose_untouched():
    fake = dict(FAKE)
    meds = list_medications()  # the shared cache list itself
    meds.append(fake)
    try:
        assert strength_for(fake["generic_en"]) == ""
        root, rx = _build_clinical_rx()
        if rx is None:
            print("SKIP no-strength dose (no display)")
            return
        try:
            rx.e_dose.delete(0, tk.END)
            rx.e_dose.insert(0, "750 mg")
            rx.drug_var.set(display(fake, "en"))  # R24: explicit lang
            rx.on_drug()
            assert rx.e_dose.get() == "750 mg", rx.e_dose.get()
        finally:
            root.destroy()
    finally:
        meds.remove(fake)
