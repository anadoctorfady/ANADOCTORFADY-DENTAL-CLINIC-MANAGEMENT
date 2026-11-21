"""Round 18 item 4: prescriptions entry form layout.

The doctor wants CATEGORY FIRST, then the drug list filtered by
it, and reported the FREQUENCY control clipped (the old grid form
requested ~1168px inside a ~665px section; the frequency combobox
ended past the frame's right edge).

At the real clinical pane width, EN and AR:
- the category combobox sits ABOVE the drug combobox, which sits
  above the dose/frequency/days row (geometry order);
- every entry-form control fits at full requested width and no
  control extends past the form frame's right edge;
- the frequency combobox is sized from its longest value;
- the drug list is filtered by the selected category from the
  start and whenever the category changes.

GUI tests skip gracefully with no display; run with DISPLAY=:98
against the isolated gate copy (ANADOCTORFADY_DATA_DIR).

Round 24 item 7 SUPERSESSION: medications.display() is now
single-language with an explicit lang parameter; the two display
comparisons below pin lang="en" (these tests build EN tabs) instead
of relying on the ambient language setting.
"""
import tkinter as tk

from src.models.database import set_setting
from src.ui import rx_form
from src.ui.clinical import ClinicalTab
from src.utils.medications import display, list_by_category, list_medications
from tests.test_clinical_save_gate import _cleanup, _seed_patient, _stub_app

CONTROLS = ("cb_cat", "cb_drug", "e_dose", "cb_freq", "e_dur", "e_inst")


def _build(lang="en"):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.geometry("1380x1000")
    set_setting("language", lang)
    app = _stub_app(None, lang=lang)
    try:
        tab = ClinicalTab(root, app)
        tab.pack(fill="both", expand=True)
        root.update_idletasks()
        root.update()
        return root, tab.rx_section
    except Exception:
        root.destroy()
        raise


def _check_layout(root, rx, lang):
    form = rx.rx_form_frame
    assert form.winfo_reqwidth() <= form.winfo_width(), (
        lang, form.winfo_reqwidth(), form.winfo_width())
    right_edge = form.winfo_rootx() + form.winfo_width()
    for attr in CONTROLS:
        w = getattr(rx, attr)
        assert w.winfo_width() >= w.winfo_reqwidth(), (
            lang, attr, w.winfo_width(), w.winfo_reqwidth())
        assert w.winfo_rootx() + w.winfo_width() <= right_edge + 2, (
            lang, attr, w.winfo_rootx() + w.winfo_width(), right_edge)
    # Row order: category, then drug, then dose/frequency/days.
    assert rx.cb_cat.winfo_rooty() < rx.cb_drug.winfo_rooty(), lang
    assert rx.cb_drug.winfo_rooty() < rx.cb_freq.winfo_rooty(), lang
    # Dose / frequency / days share one row frame (pack centres
    # widgets vertically, so rooty may differ by a couple of px).
    assert rx.e_dose.master is rx.cb_freq.master is rx.e_dur.master
    assert abs(rx.e_dose.winfo_rooty()
               - rx.cb_freq.winfo_rooty()) <= 4, lang
    assert abs(rx.e_dur.winfo_rooty()
               - rx.cb_freq.winfo_rooty()) <= 4, lang
    # Frequency sized to its longest value, at full requested width.
    assert int(rx.cb_freq.cget("width")) == rx_form.FREQ_WIDTH
    assert rx_form.FREQ_WIDTH >= max(
        len(v) for v in rx_form.FREQUENCIES) + 2
    assert rx.freq_var.get() in rx_form.FREQUENCIES


def test_rx_layout_en():
    root, rx = _build("en")
    if rx is None:
        print("SKIP test_rx_layout_en (no display)")
        return
    try:
        _check_layout(root, rx, "en")
    finally:
        root.destroy()


def test_rx_layout_ar():
    root, rx = _build("ar")
    if rx is None:
        print("SKIP test_rx_layout_ar (no display)")
        return
    try:
        _check_layout(root, rx, "ar")
    finally:
        set_setting("language", "en")
        root.destroy()


def test_rx_drug_list_filtered_by_category():
    root, rx = _build("en")
    if rx is None:
        print("SKIP test_rx_drug_list_filtered_by_category (no display)")
        return
    try:
        # From the start: category "All" -> every drug listed.
        assert rx.cat_var.get() == "All"
        assert rx.cb_drug._items == list_by_category("All")
        assert len(rx.cb_drug["values"]) == len(list_medications())
        # Pick a category: the drug list is exactly that category.
        rx.cat_var.set("Antibiotic")
        rx.on_category()
        expected = list_by_category("Antibiotic")
        assert 0 < len(expected) < len(list_medications())
        assert rx.cb_drug._items == expected
        assert list(rx.cb_drug["values"]) == [display(i, "en") for i in expected]  # R24: explicit lang
        assert all(i["category"] == "Antibiotic"
                   for i in rx.cb_drug._items)
        # Back to All restores the full list.
        rx.cat_var.set("All")
        rx.on_category()
        assert len(rx.cb_drug["values"]) == len(list_medications())
        # A freshly built tab is filtered from the start too.
        root2, rx2 = _build("en")
        assert rx2 is not None
        try:
            assert rx2.cb_drug._items == list_by_category(
                rx2.cat_var.get())
        finally:
            root2.destroy()
    finally:
        root.destroy()


def test_rx_add_item_still_works():
    fid = _seed_patient()
    root, rx = _build("en")
    if rx is None:
        _cleanup(fid)
        print("SKIP test_rx_add_item_still_works (no display)")
        return
    try:
        rx.cat_var.set("Antibiotic")
        rx.on_category()
        rx.drug_var.set(display(list_by_category("Antibiotic")[0], "en"))  # R24: explicit lang
        rx.add_item()
        assert len(rx.items) == 1
        assert rx.items[0]["frequency"] == "3x daily"
        assert len(rx.tree.get_children()) == 1
    finally:
        root.destroy()
        _cleanup(fid)
