"""Add a drug (Item 6, 2026-11-08): a drug added from the prescription
section is saved persistently and appears in drug search alongside the
315 seed drugs. GUI tests skip gracefully when no display is available."""
import tkinter as tk
from pathlib import Path

from src.utils import medications
from src.utils.medications import (add_user_medication, list_medications,
    list_user_medications, remove_user_medication, search_medications,
    get_medication)
from src.ui.clinical import ClinicalTab

MARKER = "TESTDRUG_XYZQ"


def _cleanup():
    remove_user_medication(MARKER)
    medications._CACHE = None


def test_add_drug_persists_and_is_searchable():
    _cleanup()
    try:
        ok, msg = add_user_medication({
            "generic_en": MARKER, "generic_ar": "دواء اختبار",
            "brand_en": "Testbrand", "brand_ar": "",
            "category": "Antibiotic", "form": "Tablet",
            "strength": "250 mg", "class": "Test class"})
        assert ok, msg
        assert any(m["generic_en"] == MARKER for m in list_user_medications())
        assert any(m["generic_en"] == MARKER for m in search_medications("TESTDRUG"))
        assert any(m["generic_en"] == MARKER for m in search_medications("Testbrand"))
        assert get_medication(MARKER) is not None
        assert get_medication(MARKER)["strength"] == "250 mg"
        # Survives a restart: drop the in-memory cache, reload from disk.
        medications._CACHE = None
        assert any(m["generic_en"] == MARKER for m in list_medications())
        assert len(list_medications()) >= 316  # 315 seeds + the new drug
        # The user file itself holds it (not just memory).
        raw = Path(medications._USER).read_text(encoding="utf-8")
        assert MARKER in raw
    finally:
        _cleanup()
    assert not any(m["generic_en"] == MARKER for m in list_medications())
    assert get_medication(MARKER) is None


def test_add_drug_validation():
    ok, _msg = add_user_medication({"generic_en": "  "})
    assert ok is False
    ok, _msg = add_user_medication({"generic_en": "Amoxicillin", "brand_en": "X"})
    assert ok is False  # seed drug already exists - duplicate refused
    ok, _msg = add_user_medication({"generic_en": "X"})
    assert ok is False  # too short


def test_add_drug_button_opens_dialog_on_clinical_page():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_add_drug_button_opens_dialog (no display)")
        return
    root.withdraw()
    try:
        class FakeApp:
            lang = "en"
            current_patient = {"full_name": "Rx Test", "file_number": 1,
                               "current_medications": "", "allergies": ""}
            current_user = "fady"
            current_role = "admin"
            def chart_teeth(self):
                return []
            def refresh_clinical(self):
                pass
        tab = ClinicalTab(root, FakeApp())
        tab.pack()
        root.update_idletasks()
        rx = tab.rx_section
        assert rx.add_drug_btn is not None
        assert "Add new drug" in rx.add_drug_btn.cget("text")
        # Round 16: EN mode shows English only (was bilingual).
        assert "إضافة دواء" not in rx.add_drug_btn.cget("text")
        # The merged Rx section still loads history for the patient.
        rx.load(1)
        root.update_idletasks()
        rx.add_drug_btn.invoke()
        root.update_idletasks()
        found = []
        def _walk2(w):
            yield w
            for ch in w.winfo_children():
                yield from _walk2(ch)
        dialogs = [w for w in _walk2(root)
                   if isinstance(w, tk.Toplevel) and "Add drug" in str(w.title())]
        assert len(dialogs) == 1, "Add-drug dialog did not open"
        dialogs[0].destroy()
        root.update_idletasks()
    finally:
        root.destroy()
