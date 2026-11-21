"""Settings storage section (round 16): clinic name + reports/scans
folders; round 30 adds the editable centre logo row. <200 lines.

Setting keys (EXACT): clinic_name ("" = hidden on reports),
reports_dir / scans_dir ("" = the app default folders REPORTS /
SCANS), centre_logo (stored logo filename in DATA_DIR, R30).
Pickers + logo buttons save IMMEDIATELY; existing files are NOT
moved automatically. Strings: strings_r16_settings.py +
strings_r30_logo.py; _s() falls back to t() first.
"""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from src.config.settings import REPORTS, SCANS
from src.config.strings import t
from src.config.strings_r16_settings import EN as _EN16, AR as _AR16
from src.config.strings_r30_logo import EN as _EN30, AR as _AR30
from src.reports.centre_logo import clear_logo, get_logo_path, set_logo
from src.config.theme import current
from src.models.database import get_setting, set_setting
from src.ui.rounded import rounded_button
from src.ui.rounded_frame import RoundedFrame
from src.ui.rounded_widgets import RoundedEntry


def _s(key, lang):
    """t() when merged, else this round's own EN/AR dicts."""
    v = t(key, lang)
    if v != key:
        return v
    d30 = _AR30 if lang == "ar" else _EN30
    if key in d30:
        return d30[key]
    return (_AR16 if lang == "ar" else _EN16).get(key, key)


def resolve_reports_dir():
    """Effective reports folder: custom reports_dir or the default."""
    p = (get_setting("reports_dir", "") or "").strip()
    return Path(p) if p else REPORTS


def resolve_scans_dir():
    """Effective scans folder: custom scans_dir or the default."""
    p = (get_setting("scans_dir", "") or "").strip()
    return Path(p) if p else SCANS


def _lang(tab):
    return getattr(tab, "lang", "en") or "en"


def _refresh_labels(tab):
    if hasattr(tab, "_storage_reports_lbl"):
        tab._storage_reports_lbl.config(text=_s("settings.storage_current", _lang(tab)).format(path=resolve_reports_dir()))
    if hasattr(tab, "_storage_scans_lbl"):
        tab._storage_scans_lbl.config(text=_s("settings.storage_current", _lang(tab)).format(path=resolve_scans_dir()))


def pick_reports_dir(tab):
    """Folder picker: stores reports_dir at once, updates the label."""
    dest = filedialog.askdirectory(parent=tab, title=_s("settings.reports_dir", _lang(tab)),
                                   initialdir=str(resolve_reports_dir()))
    if not dest:
        return
    tab.reports_dir_var.set(dest)
    set_setting("reports_dir", dest)
    _refresh_labels(tab)


def pick_scans_dir(tab):
    """Folder picker: stores scans_dir at once, updates the label."""
    dest = filedialog.askdirectory(parent=tab, title=_s("settings.scans_dir", _lang(tab)),
                                   initialdir=str(resolve_scans_dir()))
    if not dest:
        return
    tab.scans_dir_var.set(dest)
    set_setting("scans_dir", dest)
    _refresh_labels(tab)


def reset_reports_dir(tab):
    """Back to the default reports folder (empty reports_dir)."""
    tab.reports_dir_var.set("")
    set_setting("reports_dir", "")
    _refresh_labels(tab)


def reset_scans_dir(tab):
    """Back to the default scans folder (empty scans_dir)."""
    tab.scans_dir_var.set("")
    set_setting("scans_dir", "")
    _refresh_labels(tab)


def refresh_logo_preview(tab):
    """Show the stored logo thumbnail, or the 'No logo' text; the
    Add/Change button label follows whether a logo is set (R30)."""
    if not hasattr(tab, "_logo_preview"):
        return
    lang = _lang(tab)
    path = get_logo_path()
    if hasattr(tab, "_logo_btn"):
        tab._logo_btn.config(text=_s("settings.logo_change" if path else "settings.logo_add", lang))
    if path is None:
        tab._logo_photo = None
        tab._logo_preview.config(image="", text=_s("settings.logo_none", lang))
        return
    try:
        from PIL import Image, ImageTk
        im = Image.open(path)
        im.thumbnail((120, 44))
        tab._logo_photo = ImageTk.PhotoImage(im)
        tab._logo_preview.config(image=tab._logo_photo, text="")
    except Exception:
        tab._logo_photo = None
        tab._logo_preview.config(image="", text=path.name)


def pick_logo(tab):
    """File picker: validate + store the logo at once (R30). An
    invalid image shows a bilingual error and stores NOTHING."""
    dest = filedialog.askopenfilename(
        parent=tab, title=_s("settings.logo_pick_title", _lang(tab)),
        filetypes=[("Images", "*.png *.jpg *.jpeg"), ("PNG", "*.png"),
                   ("JPEG", "*.jpg *.jpeg")])
    if not dest:
        return
    try:
        set_logo(dest)
    except ValueError:
        messagebox.showerror(_s("settings.logo_invalid_title", _lang(tab)),
                             _s("settings.logo_invalid", _lang(tab)))
        return
    refresh_logo_preview(tab)


def remove_logo(tab):
    """Remove the stored logo file + setting at once (R30)."""
    clear_logo()
    refresh_logo_preview(tab)


def save_storage(tab):
    """Persist the clinic name (folders are already saved by pickers)."""
    set_setting("clinic_name", tab.clinic_name_var.get().strip())
    set_setting("reports_dir", tab.reports_dir_var.get().strip())
    set_setting("scans_dir", tab.scans_dir_var.get().strip())
    _refresh_labels(tab)
    messagebox.showinfo(t("settings.saved_title", _lang(tab)), _s("settings.storage_saved", _lang(tab)))


def attach_storage_section(body, tab):
    """Build the section into the Settings body; vars live on `tab` so
    the pickers, the Save button and the tests all share them."""
    th = current()
    lang = _lang(tab)
    frm = RoundedFrame(body, bg=th["panel"], border=th["border"],
                       title=_s("settings.storage_frame", lang), title_fg=th["text"])
    frm.pack(fill="x", padx=10, pady=8)
    tab.storage_wrap = frm  # R21 item 10: SettingsTab hides this for non-settings-admins
    frm = frm.inner
    tk.Label(frm, text=_s("settings.clinic_name", lang), bg=th["panel"], fg=th["text"]).grid(row=0, column=0, padx=6, pady=4, sticky="w")
    tab.clinic_name_var = tk.StringVar(tab, value=get_setting("clinic_name", "") or "")
    RoundedEntry(frm, textvariable=tab.clinic_name_var, width=40).grid(row=0, column=1, padx=4, pady=4, sticky="w")
    tk.Label(frm, text=_s("settings.clinic_name_hint", lang), bg=th["panel"], fg=th["muted"]).grid(row=1, column=0, columnspan=4, padx=6, sticky="w")
    tk.Label(frm, text=_s("settings.logo_label", lang), bg=th["panel"], fg=th["text"]).grid(row=2, column=0, padx=6, pady=4, sticky="w")
    tab._logo_preview = tk.Label(frm, text="", bg=th["panel"], fg=th["muted"])
    tab._logo_preview.grid(row=2, column=1, padx=4, pady=4, sticky="w")
    tab._logo_btn = rounded_button(frm, text=_s("settings.logo_add", lang), bg=th["accent"],
                                   command=lambda: pick_logo(tab))
    tab._logo_btn.grid(row=2, column=2, padx=4, pady=4)
    rounded_button(frm, text=_s("settings.logo_remove", lang), bg=th["panel"], fg=th["text"],
                   command=lambda: remove_logo(tab)).grid(row=2, column=3, padx=4, pady=4)
    refresh_logo_preview(tab)
    tab.reports_dir_var = tk.StringVar(tab, value=get_setting("reports_dir", "") or "")
    tab.scans_dir_var = tk.StringVar(tab, value=get_setting("scans_dir", "") or "")
    for row, key, pick, reset in ((3, "settings.reports_dir", pick_reports_dir, reset_reports_dir),
                                  (4, "settings.scans_dir", pick_scans_dir, reset_scans_dir)):
        tk.Label(frm, text=_s(key, lang), bg=th["panel"], fg=th["text"]).grid(row=row, column=0, padx=6, pady=4, sticky="w")
        _lbl = tk.Label(frm, text="", bg=th["panel"], fg=th["muted"], wraplength=420, justify="left")
        _lbl.grid(row=row, column=1, padx=4, pady=4, sticky="w")
        if row == 3:
            tab._storage_reports_lbl = _lbl
        else:
            tab._storage_scans_lbl = _lbl
        rounded_button(frm, text=_s("settings.choose_folder", lang), bg=th["accent"],
                       command=lambda p=pick: p(tab)).grid(row=row, column=2, padx=4, pady=4)
        rounded_button(frm, text=_s("settings.use_default", lang), bg=th["panel"], fg=th["text"],
                       command=lambda r=reset: r(tab)).grid(row=row, column=3, padx=4, pady=4)
    _refresh_labels(tab)
    tk.Label(frm, text=_s("settings.storage_note", lang), bg=th["panel"], fg=th["muted"],
             wraplength=760, justify="left").grid(row=5, column=0, columnspan=4, padx=6, pady=4, sticky="w")
    rounded_button(frm, text=_s("settings.storage_save", lang), bg=th["accent"],
                   command=lambda: save_storage(tab)).grid(row=6, column=0, padx=6, pady=(4, 6), sticky="w")
