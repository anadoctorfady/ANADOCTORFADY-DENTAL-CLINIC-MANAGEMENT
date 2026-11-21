"""Expense category icon picker (Round 24, Item 5).

Replaces the Finance-tab expense CATEGORY dropdown with six
selectable icon buttons (glyph + localized label, beside each other).
The STORED value is unchanged: .get() always returns the exact
English literal the old RoundedCombobox saved ("Rent", "Electricity",
"Materials", "Maintenance", "Salary", "Other"), so
models.finance.add_expense() and every existing row keep working
byte-identically. Only the DISPLAYED label is localized, via the
fin.exp_cat_* keys in strings_ops.py, read at build time (the whole
UI rebuilds on a language toggle, so no live re-translation is
needed).

Contract (drop-in for the combobox cell in finance.py):
    picker.get()        -> selected stored value (always exactly one)
    picker.set(value)   -> select programmatically (unknown = ignored)
Default selection is "Materials", same as the old combobox.

Colours come from finance_current() so both themes work:
  selected   bg=sel_bg, fg=sel_fg, bold
             light #FFFFFF on #7A3F16 = 8.23:1, dark #241A12 on
             vivid amber #F59E0B = 7.94:1 (R31: the dark accent
             #E07B39 caps at 5.73:1 with any fg, so the selected
             chip alone uses the brighter sel pair)
  unselected bg=card,   fg=text
             light #2C241D on #EFE7D8 = 12.41:1, dark #F5F0EB on
             #332C28 = 12.11:1
R31 ROOT CAUSE of the owner's "selected chip unreadable" report:
RoundedButton.configure() stored fg/font in _fg/_font but never
applied them to the widget (only the PIL background re-rendered),
so the selected chip kept the UNSELECTED label colour -- rendered
pixels measured #2C241D on #7A3F16 = 1.85:1 (light) and #F5F0EB
on #E07B39 = 2.63:1 (dark). Fixed in rounded.py _sync(), which
now re-applies fg/font/activeforeground on every configure.
Buttons are RoundedButton (never plain tk.Button: the rounded-finance
test pins that) and are plain click targets -- no focus bindings, so
the finance gate's focus handling is untouched.
"""
import tkinter as tk
from src.config.theme import finance_current
from src.config.strings import t
from src.ui.rounded import rounded_button

# (stored value, glyph, string key) -- stored value NEVER translated.
CATEGORIES = (
    ("Rent", "🏠", "fin.exp_cat_rent"),
    ("Electricity", "💡", "fin.exp_cat_electricity"),
    ("Materials", "🧰", "fin.exp_cat_materials"),
    ("Maintenance", "🔧", "fin.exp_cat_maintenance"),
    ("Salary", "💰", "fin.exp_cat_salary"),
    ("Other", "📦", "fin.exp_cat_other"),
)
VALUES = tuple(c[0] for c in CATEGORIES)
GLYPHS = {c[0]: c[1] for c in CATEGORIES}
DEFAULT = "Materials"

_FONT = ("Segoe UI", 9)
_FONT_BOLD = ("Segoe UI", 9, "bold")


class ExpenseIconPicker(tk.Frame):
    """Six icon toggle-buttons in a 3x2 grid; exactly one selected."""

    def __init__(self, parent, lang="en", th=None, default=DEFAULT):
        th = th or finance_current()
        self._th = th
        self.lang = lang or "en"
        super().__init__(parent, bg=th["panel"])
        self._value = default if default in VALUES else DEFAULT
        self.buttons = {}  # stored value -> RoundedButton
        self.labels = {}   # stored value -> localized label shown
        for i, (value, glyph, key) in enumerate(CATEGORIES):
            label = t(key, self.lang)
            self.labels[value] = label
            btn = rounded_button(
                self, text=f"{glyph} {label}",
                bg=th["card"], fg=th["text"], font=_FONT,
                command=lambda v=value: self._select(v))
            btn.grid(row=i // 3, column=i % 3, padx=3, pady=3,
                     sticky="ew")
            self.buttons[value] = btn
        for c in range(3):
            self.grid_columnconfigure(c, weight=1, uniform="expcat")
        self._apply_styles()

    # -- combobox-compatible contract --------------------------------
    def get(self):
        """The selected STORED value (English literal)."""
        return self._value

    def set(self, value):
        """Select `value` programmatically; unknown values ignored
        (the picker always keeps exactly one selection)."""
        if value in VALUES:
            self._select(value)

    # -- internals ----------------------------------------------------
    def _select(self, value):
        # Clicking the already-selected button keeps it selected:
        # there is no deselect / no-selection state.
        self._value = value
        self._apply_styles()

    def _apply_styles(self):
        th = self._th
        for value, btn in self.buttons.items():
            if value == self._value:
                btn.configure(bg=th.get("sel_bg", th["accent"]),
                              fg=th.get("sel_fg", th["btn_text"]),
                              font=_FONT_BOLD)
            else:
                btn.configure(bg=th["card"], fg=th["text"], font=_FONT)


def build_expense_picker(parent, lang="en", th=None):
    """Builder form: returns the picker (a tk.Frame subclass)."""
    return ExpenseIconPicker(parent, lang=lang, th=th)
