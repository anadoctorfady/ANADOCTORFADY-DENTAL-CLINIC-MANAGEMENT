"""Round 43: the per-place Arabic | English template-language
toggle shared by the template picker dialog and the Template
Manager. Two small buttons whose labels are the language names
themselves (the Template Manager's round-31 convention); the
active one wears the picker accent pair. State lives in
models.field_lang (persisted per category) -- this widget only
reflects and sets it. <200 lines."""
import tkinter as tk

from src.config.theme import current
from src.models.field_lang import (field_template_lang,
                                   set_field_template_lang)
from src.ui.rounded import rounded_button

_ON = {"bg": "#7A3F16", "fg": "white"}  # the picker accent pair


def build_lang_toggle(parent, get_category, on_change):
    """Build the toggle inside `parent`. get_category() -> the
    place's category (fixed for the picker, variable for the
    manager); on_change(lang) fires after a press. Returns
    (frame, refresh): refresh() re-marks the active button after
    the category or the global default changed."""
    th = current()
    frame = tk.Frame(parent, bg=parent.cget("bg"))
    btns = {}

    def _mark():
        active = field_template_lang(get_category())
        for code, b in btns.items():
            b.configure(**(_ON if code == active else
                           {"bg": th["card"], "fg": th["text"]}))

    def _press(code):
        set_field_template_lang(get_category(), code)
        _mark()
        on_change(code)

    for code, label in (("ar", "عربي"), ("en", "English")):
        # R53: padx=6 (not the 12 default) -- the pair must fit the Template Manager's 640px dialog with full text; at padx=12 the "English" button was squeezed 15px and its text clipped (the old fit depended on that clip).
        b = rounded_button(frame, text=label, relief="flat", padx=6,
                           command=lambda c=code: _press(c))
        b.pack(side="left", padx=1)
        btns[code] = b
    frame.lang_buttons = btns  # for tests
    _mark()
    return frame, _mark
