"""Round 30 item 3 (Worker C) -- GUI half: the Add New Drug
dialog's class picker (tokens listed, category-first re-ordering,
verbatim save, empty class allowed, squeezed-size layout) and the
Rx alert area (unclassified user drug -> amber info line instead
of the green all-clear; classified user drug and seed drugs keep
the existing messages exactly; a classified user drug's SEVERE
allergy alert fires through the real form). Engine proofs live in
tests/test_r30_user_drug_alerts.py, whose seed/cleanup helpers
this module reuses (unique R30T_ names, always removed)."""
import tkinter as tk

from src.utils.medications import get_medication
from src.utils.drug_classes import (class_tokens,
    classes_for_category, is_unclassified_user_drug)
from tests.test_r30_user_drug_alerts import (PEN, NONE, _cleanup,
    _fresh, _seed_user_drugs)


def _root():
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw()
    return root


def _silence_messagebox():
    from src.ui import add_drug
    orig = {}
    for name in ("showinfo", "showwarning", "showerror"):
        orig[name] = getattr(add_drug.messagebox, name)
        setattr(add_drug.messagebox, name, lambda *a, **k: None)
    return orig


def _restore_messagebox(orig):
    from src.ui import add_drug
    for name, fn in orig.items():
        setattr(add_drug.messagebox, name, fn)


def test_dialog_class_picker_saves_token_verbatim():
    root = _root()
    if root is None:
        print("SKIP r30 dialog (no display)"); return
    _cleanup()
    orig = _silence_messagebox()
    try:
        from src.ui.add_drug import open_add_drug_dialog
        win = open_add_drug_dialog(root, lang="en")
        root.update_idletasks()
        picker = win._ad_class_picker
        # Picker lists every tracked token (+ the "(No class)" row).
        assert set(picker.values[1:]) == set(class_tokens())
        assert picker.values[0] == win._ad_class_var.get()
        # The no-class warning note is present in the dialog text.
        texts = [w.cget("text") for w in win._ad_body.winfo_children()
                 if isinstance(w, tk.Label)]
        assert any("cannot be checked" in tx for tx in texts), texts
        # Category-first ordering inside the dialog: pick Antibiotic
        # and the picker re-orders (its classes lead the list).
        win._ad_cat_var.set("Antibiotic")
        # RoundedCombobox binds on its inner ttk widget (.widget),
        # which is where a real selection fires the virtual event.
        win._ad_cat_combo.widget.event_generate("<<ComboboxSelected>>")
        root.update_idletasks()
        abx = classes_for_category("Antibiotic")
        assert picker.values[1:1 + len(abx)] == sorted(abx)
        # Save with a chosen class: stored verbatim.
        win._ad_entries["generic_en"].insert(0, PEN)
        win._ad_class_var.set("Penicillin")
        win._ad_save_btn.invoke()
        root.update_idletasks()
        _fresh()
        med = get_medication(PEN)
        assert med is not None and med["class"] == "Penicillin", med
    finally:
        _restore_messagebox(orig)
        _cleanup()
        root.destroy()


def test_dialog_empty_class_allowed_and_squeezed_layout():
    root = _root()
    if root is None:
        print("SKIP r30 dialog squeezed (no display)"); return
    _cleanup()
    orig = _silence_messagebox()
    try:
        from src.ui.add_drug import open_add_drug_dialog
        win = open_add_drug_dialog(root, lang="en")
        root.update_idletasks()
        # Default sizing (round-16 rule): the Save button is fully
        # inside the window -- the new field did not clip it.
        root.update_idletasks()
        btn_bottom = (win._ad_save_btn.winfo_rooty()
                      + win._ad_save_btn.winfo_height())
        assert btn_bottom <= win.winfo_rooty() + win.winfo_height() + 2
        # Squeezed: the scrollable body keeps every field reachable
        # (scrollregion covers the full content height).
        win.geometry("460x300")
        root.update_idletasks()
        canvas = [w for w in win.winfo_children()
                  if isinstance(w, tk.Canvas)][0]
        region = canvas.cget("scrollregion").split()
        assert float(region[3]) >= win._ad_body.winfo_reqheight() - 2
        # Saving with the default "(No class)" stores class="".
        win._ad_entries["generic_en"].insert(0, NONE)
        win._ad_save_btn.invoke()
        root.update_idletasks()
        _fresh()
        med = get_medication(NONE)
        assert med is not None and med["class"] == "", med
        assert is_unclassified_user_drug(NONE) is True
    finally:
        _restore_messagebox(orig)
        _cleanup()
        root.destroy()


def _rx_tab(patient, lang="en"):
    from src.ui.prescriptions import PrescriptionsTab
    from tests.test_clinical_save_gate import _stub_app
    root = _root()
    if root is None:
        return None, None
    rx = PrescriptionsTab(root, _stub_app(patient, lang=lang),
                          narrow=True)
    rx.pack()
    root.update_idletasks()
    return root, rx


def test_rx_unclassified_user_drug_info_line_not_all_clear():
    _seed_user_drugs()
    patient = {"file_number": 0, "diseases": "",
               "current_medications": "", "allergies": ""}
    root, rx = _rx_tab(patient)
    if rx is None:
        _cleanup(); print("SKIP r30 rx info line (no display)"); return
    try:
        from src.config.strings import t
        from src.config.strings_r30_drug import r30_t
        rx._check(NONE)
        assert rx.alerts == [] and rx.has_severe is False
        shown = rx.alert_box.cget("text")
        assert shown == r30_t("rx.unclassified_info", "en"), shown
        assert shown != t("rx.no_interaction", "en")
        assert rx.alert_box.cget("fg") == "#D97706"
        # A CLASSIFIED user drug keeps the green all-clear exactly.
        rx._check(PEN)
        assert rx.alert_box.cget("text") == t("rx.no_interaction", "en")
        assert rx.alert_box.cget("fg") == "#059669"
        # A seed drug with no interactions: green all-clear unchanged.
        rx._check("Chlorhexidine")
        assert rx.alert_box.cget("text") == t("rx.no_interaction", "en")
        assert rx.alert_box.cget("fg") == "#059669"
    finally:
        root.destroy()
        _cleanup()


def test_rx_user_drug_alert_fires_through_real_form():
    # Case 1 through the real PrescriptionsTab._check merge path:
    # penicillin-allergic patient + user Penicillin-class drug.
    _seed_user_drugs()
    patient = {"file_number": 0, "diseases": "",
               "current_medications": "", "allergies": "Penicillin"}
    root, rx = _rx_tab(patient)
    if rx is None:
        _cleanup(); print("SKIP r30 rx form alert (no display)"); return
    try:
        rx._check(PEN)
        assert rx.has_severe is True, rx.alerts
        assert any(a["severity"] == "severe" for a in rx.alerts)
        assert "Penicillin" in rx.alert_box.cget("text")
    finally:
        root.destroy()
        _cleanup()
