"""Round 52 (Sections D + E): the centre-identity fields of the
Settings storage section -- clinic name, centre MOBILE (the
centre_phone key, relabelled, never renamed), centre landline,
centre address, default nationality, and the regional Arabic
month-names choice. Round 54, Section F adds a SECOND mobile
(centre_mobile2) directly under the first mobile. Split out of
settings_storage_ui.py to keep every file <= 200 lines; vars
live on `tab` exactly as before, so save/tests/pickers share them.
"""
import tkinter as tk

from src.config.strings import t
from src.config.strings_r16_settings import EN as _EN16, AR as _AR16
from src.config.strings_r30_logo import EN as _EN30, AR as _AR30
from src.config.month_names import valid_set
from src.models.database import get_setting, set_setting
from src.ui.rounded_widgets import RoundedEntry
from src.ui.rounded_lists import RoundedCombobox
from src.ui.searchable_picker import SearchablePicker
from src.utils.nationalities import (display, display_for,
                                     nationality_en_for,
                                     list_nationalities)

MONTH_KEYS = ("levant", "egypt_gulf", "maghreb")


def _s(key, lang):
    """t() when merged, else this round's own EN/AR dicts."""
    v = t(key, lang)
    if v != key:
        return v
    d30 = _AR30 if lang == "ar" else _EN30
    if key in d30:
        return d30[key]
    return (_AR16 if lang == "ar" else _EN16).get(key, key)


def _lang(tab):
    return getattr(tab, "lang", "en") or "en"


def attach_centre_fields(frm, tab):
    """Grid rows 0..7 of the storage frame (clinic identity)."""
    lang = _lang(tab)
    from src.config.theme import current
    th = current()
    tk.Label(frm, text=_s("settings.clinic_name", lang), bg=th["panel"], fg=th["text"]).grid(row=0, column=0, padx=6, pady=4, sticky="w")
    tab.clinic_name_var = tk.StringVar(tab, value=get_setting("clinic_name", "") or "")
    RoundedEntry(frm, textvariable=tab.clinic_name_var, width=40).grid(row=0, column=1, padx=4, pady=4, sticky="w")
    tk.Label(frm, text=_s("settings.clinic_name_hint", lang), bg=th["panel"], fg=th["muted"]).grid(row=1, column=0, columnspan=4, padx=6, sticky="w")
    tk.Label(frm, text=_s("settings.centre_phone", lang), bg=th["panel"], fg=th["text"]).grid(row=2, column=0, padx=6, pady=4, sticky="w")
    tab.centre_phone_var = tk.StringVar(tab, value=get_setting("centre_phone", "") or "")
    RoundedEntry(frm, textvariable=tab.centre_phone_var, width=40).grid(row=2, column=1, padx=4, pady=4, sticky="w")
    tk.Label(frm, text=_s("settings.centre_mobile2", lang), bg=th["panel"], fg=th["text"]).grid(row=3, column=0, padx=6, pady=4, sticky="w")
    tab.centre_mobile2_var = tk.StringVar(tab, value=get_setting("centre_mobile2", "") or "")
    RoundedEntry(frm, textvariable=tab.centre_mobile2_var, width=40).grid(row=3, column=1, padx=4, pady=4, sticky="w")
    tk.Label(frm, text=_s("settings.centre_landline", lang), bg=th["panel"], fg=th["text"]).grid(row=4, column=0, padx=6, pady=4, sticky="w")
    tab.centre_landline_var = tk.StringVar(tab, value=get_setting("centre_landline", "") or "")
    RoundedEntry(frm, textvariable=tab.centre_landline_var, width=40).grid(row=4, column=1, padx=4, pady=4, sticky="w")
    tk.Label(frm, text=_s("settings.centre_address", lang), bg=th["panel"], fg=th["text"]).grid(row=5, column=0, padx=6, pady=4, sticky="w")
    tab.centre_address_var = tk.StringVar(tab, value=get_setting("centre_address", "") or "")
    RoundedEntry(frm, textvariable=tab.centre_address_var, width=56).grid(row=5, column=1, columnspan=3, padx=4, pady=4, sticky="w")
    tk.Label(frm, text=_s("settings.default_nationality", lang), bg=th["panel"], fg=th["text"]).grid(row=6, column=0, padx=6, pady=4, sticky="w")
    tab.default_nationality_var = tk.StringVar(tab, value=display_for(get_setting("default_nationality", "") or "Syrian", lang))
    SearchablePicker(frm, list_nationalities(), lambda it: display(it, lang), textvariable=tab.default_nationality_var, lang=lang).grid(row=6, column=1, padx=4, pady=4, sticky="w")
    tk.Label(frm, text=_s("settings.ar_month_names", lang), bg=th["panel"], fg=th["text"]).grid(row=7, column=0, padx=6, pady=4, sticky="w")
    tab.ar_month_names_var = tk.StringVar(
        tab, value=_s(f"settings.ar_month_{valid_set(get_setting('ar_month_names', 'levant') or 'levant')}", lang))
    RoundedCombobox(frm, width=16, state="readonly",
                    values=[_s(f"settings.ar_month_{k}", lang)
                            for k in MONTH_KEYS],
                    textvariable=tab.ar_month_names_var).grid(
                        row=7, column=1, padx=4, pady=4, sticky="w")


def save_centre_fields(tab):
    """Persist the centre-identity fields (called by save_storage)."""
    set_setting("clinic_name", tab.clinic_name_var.get().strip())
    set_setting("centre_phone", tab.centre_phone_var.get().strip())
    set_setting("centre_mobile2", tab.centre_mobile2_var.get().strip())
    set_setting("centre_landline", tab.centre_landline_var.get().strip())
    set_setting("centre_address", tab.centre_address_var.get().strip())
    lang = _lang(tab)
    picked = tab.ar_month_names_var.get()
    for key in MONTH_KEYS:
        if picked == _s(f"settings.ar_month_{key}", lang):
            set_setting("ar_month_names", key)
            break
    set_setting("default_nationality",
                nationality_en_for(tab.default_nationality_var.get()))
