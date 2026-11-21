"""Prescription entry form layout (round 18 item 4). <200 lines.

Split out of prescriptions.py (200-line cap). The doctor asked for
CATEGORY FIRST, then the drug list filtered by it, and reported the
FREQUENCY control clipped (the old two-row grid measured 1168px of
requested width inside a ~665px section: the frequency combobox
ended ~58px past the frame's right edge).

Layout (one packed row per step, in order):
  row 0: Category label + popup picker (its own row, first)
  row 1: Drug label + searchable combobox (fills the row)
  row 2: Dose / Frequency / Days -- every control sized to fit at
         full requested width (frequency width derives from its
         longest value, not a guessed 10)
  row 3: Instructions (fills the row)
  row 4: Add Drug / Add new drug buttons
The drug list is filtered by the selected category FROM THE START
(apply_category runs at build time), not only after a category
click. Widget attributes land on the PrescriptionsTab instance
(cb_cat / cat_var / cb_drug / drug_var / e_dose / cb_freq /
freq_var / e_dur / e_inst / add_drug_btn / rx_form_frame), so the
tab's existing handlers keep working unchanged."""
import tkinter as tk

from src.config.strings import t
from src.config.theme import current, RADIUS_FIELD
from src.utils.medications import (categories, display, generic_for,
    list_by_category, strength_for)
from src.ui.searchable_picker import SearchablePicker  # R26: popup picker (was SearchableCombobox, whose typed filter never opened)
from src.ui.category_picker import CategoryPicker
from src.ui.rounded import rounded_button
from src.ui.rounded_frame import RoundedFrame
from src.ui.rounded_widgets import RoundedEntry
from src.ui.rounded_lists import RoundedCombobox

FREQUENCIES = ["1x daily", "2x daily", "3x daily", "4x daily",
               "Every 6h", "Every 8h", "Every 12h", "As needed"]
# Sized to the longest value + room for the dropdown arrow, in both
# UI languages (the frequency values themselves are stored strings).
FREQ_WIDTH = max(len(v) for v in FREQUENCIES) + 3
CAT_WIDTH = max(len(c) for c in categories()) + 2


def apply_category(tab):
    """Refresh the drug combobox so it lists ONLY the selected
    category's drugs (all drugs when category is "All")."""
    items = list_by_category(tab.cat_var.get())
    tab.cb_drug._items = items
    # R24 item 7: picker rows in the tab's ONE language.
    tab.cb_drug._all = [display(i, getattr(tab, "lang", None))
                        for i in items]
    tab.cb_drug._set_values(tab.cb_drug._all)


def fill_dose(tab):
    """Round 23 wiring: a drug selection auto-fills the Dose entry
    with the drug's stored strength (Amoxicillin -> "500 mg",
    Ceftriaxone -> "1 g", Tobramycin -> "0.3%"). The entry stays
    fully editable afterwards -- this only sets the starting value.
    A drug with NO stored strength leaves the entry exactly as the
    user left it (a typed dose is never cleared)."""
    strength = strength_for(generic_for(tab.drug_var.get()))
    dose = getattr(tab, "e_dose", None)
    if strength and dose is not None:
        dose.delete(0, tk.END)
        dose.insert(0, strength)


def _label(parent, key, lang, th):
    return tk.Label(parent, text=t(key, lang), bg=th["bg"],
                    fg=th["text"], font=("Segoe UI", 9, "bold"))


def build_rx_form(tab):
    """Build the Rx entry form inside the PrescriptionsTab `tab`."""
    th = current()
    lang = tab.lang
    frm = tk.Frame(tab, bg=th["bg"])
    frm.pack(fill="x", padx=8, pady=4)
    tab.rx_form_frame = frm
    # Row 0: category FIRST, on its own row.
    row = tk.Frame(frm, bg=th["bg"]); row.pack(fill="x", pady=2)
    _label(row, "rx.category", lang, th).pack(side="left", padx=3)
    tab.cat_var = tk.StringVar(value="All")
    # R24 item 9: custom popup picker, NOT a stock combobox -- the
    # combobox dropdown clipped long category names and showed
    # only 10 of 36 values (see category_picker.py).
    tab.cb_cat = CategoryPicker(row, textvariable=tab.cat_var,
                                width=CAT_WIDTH, values=categories())
    tab.cb_cat.pack(side="left", padx=3)
    tab.cb_cat.bind("<<ComboboxSelected>>", tab.on_category)
    # Row 1: drug, filtered by the category above.
    row = tk.Frame(frm, bg=th["bg"]); row.pack(fill="x", pady=2)
    _label(row, "rx.drug", lang, th).pack(side="left", padx=3)
    wrap = RoundedFrame(row, bg=th["bg"], border=th["border"],
                        radius=RADIUS_FIELD, pad=2)
    wrap.pack(side="left", fill="x", expand=True, padx=3)
    tab.drug_var = tk.StringVar()
    tab.cb_drug = SearchablePicker(wrap.inner, list_by_category("All"),
                                   lambda it: display(it, lang),
                                   textvariable=tab.drug_var,
                                   width=24, lang=lang)
    tab.cb_drug.pack(fill="both", expand=True)
    tab.cb_drug.bind("<<ComboboxSelected>>", tab.on_drug)
    # Row 2: dose / frequency / days -- all fit at full reqwidth.
    # Round 22 narrow mode (shell column): slimmer dose/days entries
    # so the row still fits ~370px without clipping the days entry.
    narrow = getattr(tab, "narrow", False)
    row = tk.Frame(frm, bg=th["bg"]); row.pack(fill="x", pady=2)
    _label(row, "rx.dose", lang, th).pack(side="left", padx=3)
    tab.e_dose = RoundedEntry(row, width=7 if narrow else 9)
    tab.e_dose.insert(0, "500 mg")
    tab.e_dose.pack(side="left", padx=3)
    _label(row, "rx.frequency", lang, th).pack(side="left", padx=3)
    tab.freq_var = tk.StringVar(value="3x daily")
    tab.cb_freq = RoundedCombobox(row, textvariable=tab.freq_var,
                                  width=FREQ_WIDTH, values=FREQUENCIES)
    tab.cb_freq.pack(side="left", padx=3)
    if not narrow:
        _label(row, "rx.days", lang, th).pack(side="left", padx=3)
        tab.e_dur = RoundedEntry(row, width=6)
        tab.e_dur.insert(0, "5")
        tab.e_dur.pack(side="left", padx=3)
    # Row 3: instructions, filling the row. Round 22 narrow mode:
    # Days rides at the start of this row (row 2 would clip it at
    # the shell column's ~370px width).
    row = tk.Frame(frm, bg=th["bg"]); row.pack(fill="x", pady=2)
    if narrow:
        _label(row, "rx.days", lang, th).pack(side="left", padx=3)
        tab.e_dur = RoundedEntry(row, width=4)
        tab.e_dur.insert(0, "5")
        tab.e_dur.pack(side="left", padx=3)
    _label(row, "rx.instructions", lang, th).pack(side="left", padx=3)
    tab.e_inst = RoundedEntry(row, width=28)
    tab.e_inst.pack(side="left", fill="x", expand=True, padx=3)
    # Row 4: add buttons.
    row = tk.Frame(frm, bg=th["bg"]); row.pack(fill="x", pady=2)
    rounded_button(row, text=t("rx.add_drug", lang), bg=th["accent"],
                   fg="white", relief="flat",
                   command=tab.add_item).pack(side="left", padx=3)
    tab.add_drug_btn = rounded_button(
        row, text=t("rx.add_new_drug", lang), bg="#7A3F16", fg="white",
        relief="flat", command=tab.open_add_drug)
    tab.add_drug_btn.pack(side="left", padx=3)
    apply_category(tab)  # drug list filtered from the start
    return frm
