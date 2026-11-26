"""Round 49 section B: Settings frame for WhatsApp reminders.

Built by build_whatsapp_frame(body, tab) from settings_ui (one
hook line, next to attach_storage_section). Vars live on `tab`
like the storage section's, so a language-toggle rebuild simply
recreates the frame from the saved settings. The wa_* values are
per-device credentials: saved via set_setting only, never synced
(models/sync.py refuses settings rows - see models/whatsapp.py).
"""
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog

from src.config.strings import t
from src.config.theme import current
from src.config.whatsapp_guide import guide_text
from src.models import whatsapp as wa
from src.models import whatsapp_send
from src.ui.rounded import rounded_button
from src.ui.rounded_frame import RoundedFrame
from src.ui.rounded_lists import RoundedCombobox
from src.ui.rounded_widgets import RoundedEntry


def _s(tab, key):
    return t(key, getattr(tab, "lang", "en") or "en")


def _save(tab):
    wa.save_config(tab.wa_enabled_var.get(), tab.wa_number_var.get(),
                   tab.wa_phone_id_var.get(), tab.wa_token_var.get(),
                   tab.wa_template_var.get(), tab.wa_lang_var.get())
    messagebox.showinfo(_s(tab, "wa.frame_title"), _s(tab, "wa.saved"),
                        parent=tab)


def _send_test(tab):
    cfg = wa.get_config()
    if not (cfg["phone_number_id"] and cfg["token"] and cfg["template_name"]):
        # Also accept the values still sitting unsaved in the entries.
        wa.save_config(tab.wa_enabled_var.get(), tab.wa_number_var.get(),
                       tab.wa_phone_id_var.get(), tab.wa_token_var.get(),
                       tab.wa_template_var.get(), tab.wa_lang_var.get())
        cfg = wa.get_config()
    if not (cfg["phone_number_id"] and cfg["token"] and cfg["template_name"]):
        messagebox.showwarning(_s(tab, "wa.test_title"),
                               _s(tab, "wa.not_configured"), parent=tab)
        return
    dest = simpledialog.askstring(_s(tab, "wa.test_title"),
                                  _s(tab, "wa.test_prompt"), parent=tab)
    if not dest:
        return
    ok, detail = whatsapp_send.send_test(dest)
    if ok:
        messagebox.showinfo(_s(tab, "wa.test_title"),
                            _s(tab, "wa.test_ok"), parent=tab)
    else:
        messagebox.showerror(_s(tab, "wa.test_title"),
                             _s(tab, "wa.test_fail").format(detail=detail),
                             parent=tab)


def open_guide(tab):
    """Scrollable bilingual setup-guide dialog (text is data in
    src/config/whatsapp_guide.py; Meta UI labels stay English)."""
    lang = getattr(tab, "lang", "en") or "en"
    th = current()
    win = tk.Toplevel(tab)
    win.title(_s(tab, "wa.guide_title"))
    win.geometry("720x640")
    win.configure(bg=th["bg"])
    wrap = RoundedFrame(win, bg=th["panel"], border=th["border"])
    wrap.pack(fill="both", expand=True, padx=10, pady=10)
    txt = scrolledtext.ScrolledText(wrap.inner, wrap="word", width=84,
                                    height=34, bg=th["panel"], fg=th["text"],
                                    font=("Segoe UI", 10), relief="flat")
    txt.pack(fill="both", expand=True, padx=6, pady=6)
    txt.insert("1.0", guide_text(lang))
    txt.configure(state="disabled")
    tab.wa_guide_win = win  # gallery/tests reach the open dialog here
    return win


def build_whatsapp_frame(parent, app):
    """The WhatsApp reminders frame. `app` is the Settings tab
    (vars are stored on it, matching settings_storage_ui)."""
    tab = app
    th = current()
    lang = getattr(tab, "lang", "en") or "en"
    cfg = wa.get_config()
    wrap = RoundedFrame(parent, bg=th["panel"], border=th["border"],
                        title=_s(tab, "wa.frame_title"), title_fg=th["text"])
    wrap.pack(fill="x", padx=10, pady=8)
    tab.wa_wrap = wrap
    frm = wrap.inner
    tab.wa_enabled_var = tk.BooleanVar(tab, value=cfg["enabled"])
    tk.Checkbutton(frm, text=_s(tab, "wa.enabled"),
                   variable=tab.wa_enabled_var, bg=th["panel"],
                   fg=th["text"], activebackground=th["panel"],
                   selectcolor=th["panel"]).grid(
                       row=0, column=0, columnspan=4, padx=6, pady=4,
                       sticky="w")
    tab.wa_number_var = tk.StringVar(tab, value=cfg["number"])
    tab.wa_phone_id_var = tk.StringVar(tab, value=cfg["phone_number_id"])
    tab.wa_token_var = tk.StringVar(tab, value=cfg["token"])
    tab.wa_template_var = tk.StringVar(tab, value=cfg["template_name"])
    tab.wa_lang_var = tk.StringVar(tab, value=cfg["template_lang"])
    rows = (("wa.number", tab.wa_number_var, 44, None),
            ("wa.phone_id", tab.wa_phone_id_var, 44, None),
            ("wa.token", tab.wa_token_var, 44, "*"),
            ("wa.template", tab.wa_template_var, 30, None))
    for i, (key, var, width, show) in enumerate(rows, start=1):
        tk.Label(frm, text=_s(tab, key), bg=th["panel"],
                 fg=th["text"]).grid(row=i, column=0, padx=6, pady=3,
                                      sticky="w")
        RoundedEntry(frm, textvariable=var, width=width,
                     show=show).grid(row=i, column=1, padx=4, pady=3,
                                     sticky="w")
    r = len(rows) + 1
    tk.Label(frm, text=_s(tab, "wa.template_lang"), bg=th["panel"],
             fg=th["text"]).grid(row=r, column=0, padx=6, pady=3, sticky="w")
    RoundedCombobox(frm, textvariable=tab.wa_lang_var,
                    values=["en", "ar"], width=8,
                    state="readonly").grid(row=r, column=1, padx=4, pady=3,
                                           sticky="w")
    tk.Label(frm, text=_s(tab, "wa.hint"), bg=th["panel"], fg=th["muted"],
             wraplength=760, justify="left").grid(
                 row=r + 1, column=0, columnspan=4, padx=6, pady=(2, 0),
                 sticky="w")
    btns = tk.Frame(frm, bg=th["panel"])
    btns.grid(row=r + 2, column=0, columnspan=4, padx=6, pady=6, sticky="w")
    rounded_button(btns, text=_s(tab, "wa.guide_btn"), bg="#5E5CE6",
                   fg="white", relief="flat",
                   command=lambda: open_guide(tab)).pack(side="left", padx=4)
    rounded_button(btns, text=_s(tab, "wa.test_btn"), relief="flat",
                   command=lambda: _send_test(tab)).pack(side="left", padx=4)
    rounded_button(btns, text=_s(tab, "wa.save_btn"), bg=th["accent"],
                   fg="white", relief="flat",
                   command=lambda: _save(tab)).pack(side="left", padx=4)
    return wrap
