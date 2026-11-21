"""Patient soft-delete action for the Patient info panel.

Split out of patient_info.py in round 21 (that file hit the
200-line cap when the per-line labels landed). Admin-only SOFT
delete: the role is re-checked here (not only via the button
state), the model only sets patients.deleted=1 -- treatments,
financials, prescriptions and scans stay in the DB -- and the
open patient is then cleared everywhere, mirroring the panel's
own refresh + the shell's patient list reload.
<200 lines."""
import tkinter as tk
from tkinter import messagebox

from src.config.strings_r18_patients import tr
from src.models.patients import soft_delete_patient


def can_delete(app):
    """The delete role gate: ADMIN only (doctor / nurse refused)."""
    return getattr(app, "current_role", "") == "admin"


def confirm_and_delete(panel):
    """Ask (naming the patient), soft-delete, clear the UI."""
    if panel._fid is None:
        return
    if not can_delete(panel.app):
        messagebox.showwarning(
            tr("patient.delete_title", panel.lang),
            tr("patient.delete_admin_only", panel.lang))
        return
    patient = getattr(panel.app, "current_patient", None) or {}
    name = patient.get("full_name") or f"#{panel._fid}"
    if not messagebox.askyesno(
            tr("patient.delete_title", panel.lang),
            tr("patient.delete_confirm", panel.lang).format(name=name)):
        return
    fid = panel._fid
    if not soft_delete_patient(fid):
        return
    # Clear the open patient everywhere (clinical.clear pattern).
    panel.app.current_patient = None
    try:
        panel.app.clinical.clear()
    except Exception:
        pass
    try:
        panel.app.appt.load()
    except Exception:
        pass
    panel.refresh(None)
    panel.app.load_patients()
    messagebox.showinfo(
        tr("patient.delete_title", panel.lang),
        tr("patient.deleted_msg", panel.lang).format(name=name))
