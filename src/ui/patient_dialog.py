"""Round 17 item 7: "+ New Patient" as a MODAL dialog. <200 lines.

The new-patient entry form exists ONLY here: pressing "+ New
Patient" opens this tk.Toplevel (transient + grab_set) over whatever
tab is current -- no tab navigation, and no PatientForm is hosted
permanently anywhere. The form itself contains no dental chart
(item 1: a new patient has no file yet).

On a successful save the dialog closes and the new patient becomes
current and opens (load_patients + select_patient, so the Clinical
tab loads him). PatientForm's duplicate handling routes through the
same close-and-open path when the user chooses to open the existing
file; declining keeps the dialog open.
"""
import tkinter as tk

from src.config.strings import t
from src.config.strings_r18_patients import tr as _tr18
from src.config.theme import current
from src.models.patients import fetch_patient
from src.ui.patient_form import PatientForm
from src.ui.rounded import rounded_button


def open_new_patient_dialog(app, parent=None):
    """Open the modal new-patient dialog over `parent` (default: the
    app window). Returns the Toplevel (its .form is the PatientForm).
    The caller (shell.new_patient) has already cleared the current
    patient and the clinical tab, so nothing of the previous patient
    shows behind or inside the dialog."""
    lang = getattr(app, "lang", "en")
    th = current()
    parent = parent if parent is not None else app
    win = tk.Toplevel(parent)
    win.title(t("shell.new_patient", lang))
    win.configure(bg=th["bg"])
    win.geometry("860x640")
    win.transient(parent)

    def _saved(fid):
        # Close FIRST, then open the patient in the main window (the
        # modal grab must be gone before the clinical tab loads him).
        try:
            win.grab_release()
        except Exception:
            pass
        win.destroy()
        app.load_patients()
        app.select_patient(fid)

    form = PatientForm(win, app, on_saved=_saved)
    form.pack(fill="both", expand=True)
    win.form = form
    bar = tk.Frame(win, bg=th["bg"])
    bar.pack(fill="x", padx=10, pady=(0, 10))
    rounded_button(bar, text=t("dlg.sync_cancel", lang), bg=th["card"],
                   fg=th["text"], command=win.destroy).pack(side="right", padx=4)
    form.show_new()
    win.grab_set()
    win.focus_set()
    try:
        form.e_first.focus_set()
    except Exception:
        pass
    return win


def open_edit_patient_dialog(app, file_number, parent=None):
    """Round 18: open the patient form in EDIT mode as a modal
    dialog for an existing patient (the shell info block's Edit
    button). Reuses PatientForm + fill(): the form's save updates
    when app.current_patient is this patient (set here), and its
    duplicate check excludes this file, so keeping the same name
    is fine while taking another patient's name is refused.
    Returns the Toplevel (its .form is the PatientForm), or None
    when the patient does not exist / is soft-deleted. On a
    successful save the dialog closes and the app reloads the
    list + re-selects the patient (info block and clinical tab
    refresh through App.on_select)."""
    row = fetch_patient(file_number)
    if row is None:
        return None
    lang = getattr(app, "lang", "en")
    th = current()
    parent = parent if parent is not None else app
    win = tk.Toplevel(parent)
    win.title(_tr18("patient.edit_title", lang).format(fid=file_number))
    win.configure(bg=th["bg"])
    win.geometry("860x640")
    win.transient(parent)

    def _saved(fid):
        try:
            win.grab_release()
        except Exception:
            pass
        win.destroy()
        app.load_patients()
        app.select_patient(fid)

    form = PatientForm(win, app, on_saved=_saved)
    form.pack(fill="both", expand=True)
    win.form = form
    bar = tk.Frame(win, bg=th["bg"])
    bar.pack(fill="x", padx=10, pady=(0, 10))
    rounded_button(bar, text=t("dlg.sync_cancel", lang), bg=th["card"],
                   fg=th["text"], command=win.destroy).pack(side="right", padx=4)
    # Edit mode: the patient being edited becomes current BEFORE
    # fill/save, so save_patient_record updates this file.
    app.current_patient = row
    form.fill(row)
    win.grab_set()
    win.focus_set()
    return win
