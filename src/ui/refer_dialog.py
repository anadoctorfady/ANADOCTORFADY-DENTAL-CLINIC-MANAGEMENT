"""Round 19 (item 11): "Refer patient" dialog. <200 lines.

Opened from the patient info block for the CURRENTLY OPEN patient
(returns None, opens nothing, when no patient is open). Two doctor
modes, made unambiguous by an "external" checkbox (the pattern
used elsewhere in the app for mode switches):

- INTERNAL (checkbox off): a combobox of the clinic's doctors --
  users with role doctor/admin, from src.utils.auth.list_doctors().
- EXTERNAL (checkbox on): the combobox is disabled and a free-text
  entry for the outside doctor's name is enabled.

MODE RULE: the external name wins whenever the external checkbox
is on; otherwise the combobox selection is used. On save the
external entry must be non-empty in external mode, the combobox
must have a selection in internal mode -- otherwise a bilingual
error (app language only) and the dialog stays open.

The note is a Text field with a Templates button opening the
existing phrase picker for category 'referral' (app language
only, appends; the 'referral' seeds land with sibling job R19-A).
Free text is allowed; note = template, free text, or both. The
date defaults to today (created_at is stamped by the model).

On save: referrals.add_referral(patient_id, from_user = the
logged-in username, to_doctor, note); clinical history refreshes
at once. Round 24 (item 1): the dialog STAYS OPEN after a save --
Print (disabled before any save) is enabled and opens the print
preview for win.saved_referral_id; a status label confirms the
save and Cancel becomes Close (closing refreshes clinical too).
The dialog object carries .doctor_var / .ext_check / .ext_entry /
.note_text / .patient_id / .save() / .btn_print for tests.
"""
import tkinter as tk
from tkinter import messagebox

from src.config.strings_r19_referral import tr
from src.config.theme import current
from src.models.referrals import add_referral
from src.ui.phrase_picker import open_template_picker
from src.ui.rounded import rounded_button
from src.ui.rounded_lists import RoundedCombobox, RoundedText
from src.ui.rounded_widgets import RoundedEntry

REFERRAL_CATEGORY = "referral"


def open_refer_dialog(app, parent=None):
    """Open the refer dialog for app.current_patient. Returns the
    Toplevel, or None when no patient is open."""
    patient = getattr(app, "current_patient", None)
    if not patient:
        return None
    fid = patient.get("file_number")
    lang = getattr(app, "lang", "en")
    th = current()
    parent = parent if parent is not None else app
    win = tk.Toplevel(parent)
    win.title(tr("refer.title", lang).format(
        patient=patient.get("full_name") or f"#{fid}"))
    win.configure(bg=th["bg"])
    win.transient(parent)
    win.patient_id = fid
    win.lang = lang

    def _print_saved():
        rid = getattr(win, "saved_referral_id", None)
        if not rid: return
        from src.reports.print_preview import open_referral_preview
        open_referral_preview(app, rid, parent=win)

    def _close():
        if getattr(win, "saved_referral_id", None):
            try: app.refresh_clinical()
            except Exception: pass
        win.destroy()

    # Round 21 (item 7): the buttons frame is packed FIRST with
    # side="bottom" so it ALWAYS claims its height (the round-19
    # layout packed it last and the Save button was clipped off
    # on DPI-scaled Windows builds). The window is sized from its
    # content (capped to the screen), never a fixed geometry.
    btns = tk.Frame(win, bg=th["bg"])
    btns.pack(side="bottom", fill="x", padx=12, pady=(0, 10))
    win.btn_save = rounded_button(btns, text=tr("refer.save_btn", lang),
                   bg=th["accent"], fg="white",
                   font=("Segoe UI", 10, "bold"),
                   command=lambda: win.save())
    win.btn_save.pack(side="left")
    win.btn_print = rounded_button(btns, text=tr("refer.print_btn", lang),
                    bg=th["card"], fg=th["text"], state="disabled",
                    command=_print_saved)
    win.btn_print.pack(side="left", padx=(8, 0))
    win.lbl_saved = tk.Label(btns, text="", bg=th["bg"], fg=th["accent"],
                             font=("Segoe UI", 9, "bold"))
    win.lbl_saved.pack(side="left", padx=(8, 0))
    win.btn_cancel = rounded_button(btns, text=tr("refer.cancel_btn", lang),
                    bg=th["card"], fg=th["text"], command=_close)
    win.btn_cancel.pack(side="right")

    body = tk.Frame(win, bg=th["bg"])
    body.pack(fill="both", expand=True, padx=12, pady=10)

    tk.Label(body, text=tr("refer.internal", lang), bg=th["bg"],
             fg=th["text"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
    from src.utils.auth import list_doctors
    win.doctor_var = tk.StringVar(win)  # master=win: a bare Var binds to the default root, which a destroyed earlier App leaves dead
    doctors = list_doctors()
    win.cb_doctor = RoundedCombobox(body, textvariable=win.doctor_var,
                                    values=doctors, width=30,
                                    state="readonly", bg=th["bg"])
    win.cb_doctor.pack(anchor="w", pady=(2, 6))
    if doctors:
        win.doctor_var.set(doctors[0])

    win.ext_var = tk.BooleanVar(win, value=False)  # master=win, as above
    win.ext_check = tk.Checkbutton(
        body, text=tr("refer.external_check", lang),
        variable=win.ext_var, bg=th["bg"], fg=th["text"],
        activebackground=th["bg"], selectcolor=th["panel"],
        font=("Segoe UI", 10, "bold"))
    win.ext_check.pack(anchor="w")
    tk.Label(body, text=tr("refer.external_name", lang), bg=th["bg"],
             fg=th["text"]).pack(anchor="w")
    win.ext_entry = RoundedEntry(body, width=34, bg=th["bg"])
    win.ext_entry.pack(anchor="w", fill="x", pady=(2, 6))
    win.ext_entry.config(state="disabled")

    def _sync_mode():
        ext = bool(win.ext_var.get())
        win.cb_doctor.config(state="disabled" if ext else "readonly")
        win.ext_entry.config(state="normal" if ext else "disabled")
    win.ext_check.config(command=_sync_mode)
    _sync_mode()

    note_head = tk.Frame(body, bg=th["bg"])
    note_head.pack(fill="x")
    tk.Label(note_head, text=tr("refer.note", lang), bg=th["bg"],
             fg=th["text"], font=("Segoe UI", 10, "bold")).pack(side="left")
    win.btn_templates = rounded_button(note_head, text=tr("refer.templates_btn", lang),
                   bg=th["card"], fg=th["text"],
                   command=lambda: open_template_picker(
                       win, REFERRAL_CATEGORY, win.note_text,
                       getattr(app, "current_user", None),
                       lang=lang))
    win.btn_templates.pack(side="right")
    win.note_text = RoundedText(body, height=5, font=("Segoe UI", 10),
                                wrap="word")  # R19 item 7: rounded, not square tk.Text
    win.note_text.pack(fill="both", expand=True, pady=(2, 6))

    def chosen_doctor():
        """The mode rule: external wins when its checkbox is on."""
        if win.ext_var.get():
            return win.ext_entry.get().strip()
        return (win.doctor_var.get() or "").strip()

    def save():
        doctor = chosen_doctor()
        if not doctor:
            messagebox.showerror(tr("refer.error_title", lang),
                                 tr("refer.no_doctor", lang))
            return False
        note = win.note_text.get("1.0", tk.END).strip()
        rid = add_referral(fid, getattr(app, "current_user", "") or "",
                           doctor, note)
        if rid is None:
            messagebox.showerror(tr("refer.error_title", lang),
                                 tr("refer.no_doctor", lang))
            return False
        win.saved_referral_id = rid
        # Round 24 (item 1): the dialog STAYS OPEN after a save --
        # enable Print for this referral and confirm the save in
        # the status label; Cancel becomes Close. Clinical still
        # refreshes at once, exactly as the round-19 save did.
        win.btn_print.config(state="normal")
        win.lbl_saved.config(text=tr("refer.saved_status", lang))
        win.btn_cancel.config(text=tr("refer.close_btn", lang))
        try:
            app.refresh_clinical()
        except Exception:
            pass
        return True

    win.save = save
    win.chosen_doctor = chosen_doctor
    win.saved_referral_id = None
    # R21 item 7: size the window from its content (never smaller
    # than the old 520x380, never taller than the screen allows).
    win.update_idletasks()
    _w = max(520, win.winfo_reqwidth())
    _h = max(380, min(win.winfo_reqheight(), win.winfo_screenheight() - 60))
    win.geometry(f"{_w}x{_h}")
    win.minsize(420, 300)
    try:
        win.grab_set()
    except Exception:
        pass
    win.focus_set()
    return win
