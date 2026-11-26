"""Round 24 item 7: medication names display in ONE language --
the app language.

Before round 24, medications.display() ALWAYS returned the
bilingual form "Amoxicillin (Amoxil) / أموسيسيلين — Capsule 500 mg",
so an English UI showed Arabic drug names and an Arabic UI showed
English ones. Now:
  EN: "Amoxicillin (Amoxil) — Capsule 500 mg"  (no Arabic at all)
  AR: "أموكسيسيلين — Capsule 500 mg"           (Arabic generic only;
      form/strength keep their standard Latin units)
display()/display_for() take lang=None, which resolves from the
app language setting (an explicit "en"/"ar" wins). generic_for()
resolves EN displays, AR displays AND the legacy bilingual form
back to the canonical generic_en BY LOOKUP (generic_en, generic_ar,
"X (Y)" head, brand_en, brand_ar), so stored prescription items
keep the canonical generic no matter which language was picked in.

GUI tests skip gracefully with no display; run with DISPLAY=:102
against the isolated copy (ANADOCTORFADY_DATA_DIR=/tmp/r24_med).
"""
import re
import tkinter as tk

from src.models.database import get_connection, get_setting, set_setting
from src.models.prescriptions import (get_prescription_items,
    save_prescription)
from src.ui.prescriptions import PrescriptionsTab
from src.utils.medications import (display, display_for, generic_for,
    get_medication, list_medications)
from tests.test_clinical_save_gate import _cleanup, _seed_patient, _stub_app

_AR = re.compile(r"[؀-ۿ]")
SAMPLE = ("Amoxicillin", "Ceftriaxone", "Tobramycin", "Paracetamol",
          "Ibuprofen")


def _legacy(m):
    """The pre-round-24 bilingual display string."""
    dose = " ".join(p for p in (m.get("form", ""), m.get("strength", ""))
                    if p)
    base = f"{m['generic_en']} ({m['brand_en']}) / {m['generic_ar']}"
    return f"{base} — {dose}" if dose else base


def test_display_en_has_no_arabic():
    for name in SAMPLE:
        text = display(get_medication(name), "en")
        assert not _AR.search(text), text
    # Every drug, not just the sample: EN rows are Latin-only.
    for m in list_medications():
        assert not _AR.search(display(m, "en")), m["generic_en"]
    assert display(get_medication("Amoxicillin"), "en") == \
        "Amoxicillin (Amoxil) — Capsule 500 mg"


def test_display_ar_has_no_latin_generic_or_brand():
    for name in SAMPLE:
        m = get_medication(name)
        text = display(m, "ar")
        assert m["generic_en"] not in text, text
        assert m["brand_en"] not in text, text
        assert m["generic_ar"] in text, text
    for m in list_medications():
        text = display(m, "ar")
        assert m["generic_en"] not in text, (m["generic_en"], text)
        # R49: combos and the new singles carry brand_en "" by
        # design (no brand is claimed for them); an empty brand
        # cannot leak into the AR display, so skip it.
        assert not m["brand_en"] or m["brand_en"] not in text, \
            (m["generic_en"], text)
    # Form/strength stay in their standard Latin units.
    assert display(get_medication("Amoxicillin"), "ar") == \
        "أموكسيسيلين — Capsule 500 mg"


def test_display_default_lang_comes_from_setting():
    m = get_medication("Amoxicillin")
    prev = get_setting("language", "en")
    try:
        set_setting("language", "ar")
        assert display(m) == display(m, "ar")
        assert display_for("Amoxicillin") == display(m, "ar")
        set_setting("language", "en")
        assert display(m) == display(m, "en")
        assert display_for("Amoxicillin") == display(m, "en")
    finally:
        set_setting("language", prev or "en")


def test_generic_for_round_trips_all_formats():
    for name in SAMPLE:
        m = get_medication(name)
        assert generic_for(display(m, "en")) == name
        assert generic_for(display(m, "ar")) == name
        assert generic_for(_legacy(m)) == name, _legacy(m)
        assert generic_for(m["brand_en"]) == name
        assert generic_for(m["generic_ar"]) == name
        assert generic_for(m["generic_en"]) == name
    # All 315: both live formats resolve back to the canonical name.
    for m in list_medications():
        assert generic_for(display(m, "en")) == m["generic_en"]
        assert generic_for(display(m, "ar")) == m["generic_en"]


def _root():
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw()
    return root


def _build_rx(lang):
    root = _root()
    if root is None:
        return None, None
    try:
        rx = PrescriptionsTab(root, _stub_app({"file_number": 0},
                                              lang=lang), narrow=True)
        rx.pack()
        root.update_idletasks()
        return root, rx
    except Exception:
        root.destroy()
        raise


def _pick_and_add(rx, display_text):
    """Select a drug by its picker string, exactly as the combobox
    leaves it, then add the item (dose preset so the round-23
    auto-fill from the stored strength is observable)."""
    rx.e_dose.delete(0, tk.END)
    rx.e_dose.insert(0, "111 mg")
    rx.drug_var.set(display_text)
    rx.on_drug()
    assert rx.e_dose.get() == "500 mg", rx.e_dose.get()
    rx.add_item()
    assert len(rx.items) == 1
    item = rx.items[0]
    assert item["generic"] == "Amoxicillin", item
    assert item["brand"] == "Amoxil", item  # canonical brand_en stored
    assert item["dose"] == "500 mg", item
    return item


def test_gui_rx_picker_arabic_single_language_and_stores_canonical():
    root, rx = _build_rx("ar")
    if rx is None:
        print("SKIP r24 AR picker (no display)")
        return
    fid = _seed_patient()
    try:
        values = list(rx.cb_drug["values"])
        ar_text = display_for("Amoxicillin", "ar")
        assert ar_text in values
        assert not any("Amoxicillin" in v or "Amoxil" in v
                       for v in values), values[:3]
        assert all(_AR.search(v) for v in values)
        # Picker SEARCH in AR: typing the Arabic name finds the drug.
        rx.drug_var.set("أموكسيسيلين")
        rx.cb_drug._on_key()
        assert ar_text in list(rx.cb_drug["values"])
        item = _pick_and_add(rx, ar_text)
        # The STORED prescription row keeps the canonical generic.
        pid = save_prescription(fid, [item], "", "dr_fady", [])
        stored = get_prescription_items(pid)
        assert stored[0]["generic"] == "Amoxicillin", stored
        assert stored[0]["brand"] == "Amoxil", stored
        conn = get_connection()
        conn.execute("DELETE FROM prescriptions WHERE id=?", (pid,))
        conn.commit(); conn.close()
    finally:
        root.destroy()
        _cleanup(fid)


def test_gui_rx_picker_english_single_language():
    root, rx = _build_rx("en")
    if rx is None:
        print("SKIP r24 EN picker (no display)")
        return
    try:
        values = list(rx.cb_drug["values"])
        en_text = display_for("Amoxicillin", "en")
        assert en_text == "Amoxicillin (Amoxil) — Capsule 500 mg"
        assert en_text in values
        assert not any(_AR.search(v) for v in values)
        _pick_and_add(rx, en_text)
    finally:
        root.destroy()
