"""Round 24: Cancel-edit + Delete for unified-table sessions
(split from clinical_session_edit.py for the line cap).

Delete gates (see clinical_session_edit for the full matrix):
the clinical 24h rule must pass for every kind in the session,
and a session WITH money attached additionally needs the
finance.edit_amounts permission -- without it the delete is
refused with a bilingual explanation BEFORE any confirmation.
The delete itself is session_money.delete_session_rows (one
transaction; a same-date complaints row shared with another
session survives). Deletes are local-only, like the existing
finance/clinical delete paths. <200 lines."""
from tkinter import messagebox
from src.config.strings import t
from src.config.strings_r24_session import sess_t
from src.models import session_money as _sm
from src.ui import clinical_history as _hist
from src.ui import clinical_session_edit as _edit
from src.ui import clinical_session_entry as _entry


def cancel_edit(tab):
    """Leave edit mode without saving; the entry area resets."""
    tab._editing_session = None
    tab._edit_currency = None
    tab._edit_rate = None
    _edit.set_editing_ui(tab, None)
    _entry.clear_entry(tab)
    _edit.sync_edit_buttons(tab)


def delete_selected(tab, session=None):
    """Delete the selected session after confirmation. Returns
    True when rows were deleted."""
    lang = getattr(tab.app, "lang", "en")
    session = session or _hist.selected_session(tab)
    if session is None:
        messagebox.showwarning(t("clinical.select_title", lang), sess_t("sess.select_first", lang))
        return False
    ok, reason = _edit.session_editable(tab, session)
    if not ok:
        messagebox.showwarning(t("savegate.not_allowed_title", lang), reason or "")
        return False
    if _edit.session_has_money(session) and not _edit.can_edit_money(tab):
        messagebox.showerror(sess_t("sess.delete_title", lang), sess_t("sess.delete_money_denied", lang))
        return False
    if not messagebox.askyesno(sess_t("sess.delete_title", lang), sess_t("sess.delete_confirm", lang)):
        return False
    fid = (getattr(tab.app, "current_patient", None) or {}).get("file_number")
    if not fid:
        return False
    _sm.delete_session_rows(fid, session)
    if getattr(tab, "_editing_session", None) is session:
        cancel_edit(tab)
    after_change(tab, fid)
    return True


def after_change(tab, fid):
    """Refresh the clinical view after a session change (the app's
    refresh also reloads appointments attendance)."""
    try:
        tab.load(fid)
    except Exception:
        pass
    try:
        tab.app.refresh_clinical()
    except Exception:
        pass
    _edit.sync_edit_buttons(tab)
