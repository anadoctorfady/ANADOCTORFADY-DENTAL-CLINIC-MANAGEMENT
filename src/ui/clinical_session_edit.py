"""Round 24: Edit for unified-table session rows + the permission
checks behind Edit/Delete (delete itself: clinical_session_delete).

PERMISSIONS (standing rules, non-negotiable):
- Clinical edit/delete follows edit_rules.check_record per kind
  present (from the session's meta tuples + visit_date fallback):
  admin always; author doctor within 24h; legacy author-less rows
  any doctor within 24h; nurses never.
- MONEY additionally needs finance.edit_amounts (has_perm: admin
  by default, or a grant). Without it the money boxes load LOCKED
  and saving touches clinical text only; Delete of a session WITH
  money is refused (see _delete).
Edit identity: the tooth stays FIXED in edit mode (its entry box
is disabled). Round 49 (Section F): the DATE box is disabled too
for everyone EXCEPT admin — date editing is admin-only, layered
on top of the 24h rule (see change_session_date). <200 lines."""
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from src.config.strings import t
from src.config.strings_r24_session import sess_t
from src.models.edit_rules import can_edit_date, check_record, valid_date
from src.models.permissions import has_perm
from src.ui import clinical_history as _hist
from src.ui import clinical_session_entry as _entry

_KINDS = (("complaint", "complaints_id"), ("diagnosis", "diagnosis_ids"),
          ("procedure", "procedure_ids"))


def can_edit_money(tab):
    """True when the current user holds finance.edit_amounts."""
    return has_perm(getattr(tab, "current_user", ""), "finance.edit_amounts",
                    getattr(tab, "current_role", None))


def session_has_money(session):
    return bool(session and session.get("financial_ids"))


def session_editable(tab, session):
    """(ok, reason_or_None): every clinical kind present in the
    session must pass the 24h rule for the current user."""
    if not session:
        return False, None
    lang = getattr(tab.app, "lang", "en")
    role = getattr(tab, "current_role", None); user = getattr(tab, "current_user", None)
    meta = session.get("meta") or {}
    checked = False
    for kind, idkey in _KINDS:
        present = session.get(idkey) is not None if kind == "complaint" else bool(session.get(idkey))
        if not present:
            continue
        checked = True
        m = meta.get(kind) or (None, None)
        ok, reason = check_record(role, user, m[0], m[1], fallback_date=session.get("date"), lang=lang)
        if not ok:
            return False, reason
    return (True, None) if checked else (False, None)


def sync_edit_buttons(tab):
    """Enable/disable Edit + Delete for the current selection and
    explain (status label) when an action is not available."""
    btn_e = getattr(tab, "btn_sess_edit", None)
    if btn_e is None:
        return
    btn_d = getattr(tab, "btn_sess_delete", None); status = getattr(tab, "sess_status", None)
    lang = getattr(tab.app, "lang", "en")
    session = _hist.selected_session(tab)
    if getattr(tab, "_editing_session", None) is not None or session is None:
        btn_e.config(state="disabled")
        if btn_d is not None:
            btn_d.config(state="disabled")
        if status is not None:
            status.config(text="")
        return
    ok, reason = session_editable(tab, session)
    btn_e.config(state="normal" if ok else "disabled")
    money_block = session_has_money(session) and not can_edit_money(tab)
    if btn_d is not None:
        btn_d.config(state="normal" if ok and not money_block else "disabled")
    if status is not None:
        status.config(text=(reason or "") if not ok else
                      sess_t("sess.money_locked", lang) if money_block else "")


def start_edit(tab, session=None):
    """Load the selected session into the entry area (edit mode).
    Returns True when edit mode was entered."""
    lang = getattr(tab.app, "lang", "en")
    session = session or _hist.selected_session(tab)
    if session is None:
        messagebox.showwarning(t("clinical.select_title", lang), sess_t("sess.select_first", lang))
        return False
    ok, reason = session_editable(tab, session)
    if not ok:
        messagebox.showwarning(t("savegate.not_allowed_title", lang), reason or sess_t("sess.select_first", lang))
        return False
    _entry.set_entry_text(tab, "txt_complaint", session.get("complaint") or "")
    _entry.set_entry_text(tab, "txt_sym", session.get("symptom") or "")
    _entry.set_entry_text(tab, "txt_diagnosis", session.get("diagnosis") or "")
    _entry.set_entry_text(tab, "txt_procedure", session.get("procedure") or "")
    _entry.set_entry_text(tab, "txt_visit_note", _entry.session_note(session))
    tot, paid, cur_code, rate = _entry.session_raw_money(session)
    tab._edit_currency = cur_code; tab._edit_rate = rate; tab._editing_session = session
    if getattr(tab, "e_sess_date", None) is not None:
        tab.e_sess_date.delete(0, tk.END); tab.e_sess_date.insert(0, session.get("date") or "")
    if getattr(tab, "e_sess_tooth", None) is not None:
        tab.e_sess_tooth.delete(0, tk.END); tab.e_sess_tooth.insert(0, session.get("tooth_raw") or "")
    _entry.set_money(tab, tot, paid)
    set_editing_ui(tab, session)
    sync_edit_buttons(tab)
    return True


def set_editing_ui(tab, session):
    """Editing-state visuals: editing label, Cancel button, date +
    tooth boxes disabled (identity fixed), money boxes locked when
    the user lacks finance.edit_amounts."""
    lang = getattr(tab.app, "lang", "en")
    editing = session is not None
    lbl = getattr(tab, "lbl_editing", None)
    if lbl is not None:
        if not editing:
            lbl.config(text="")
        elif session.get("tooth_raw"):
            lbl.config(text=sess_t("sess.editing", lang).format(date=session.get("date") or "—", tooth=session["tooth_raw"]))
        else:
            lbl.config(text=sess_t("sess.editing_notooth", lang).format(date=session.get("date") or "—"))
    btn = getattr(tab, "btn_sess_cancel", None)
    if btn is not None:
        if editing:
            btn.pack(side="left", padx=2)
        else:
            btn.pack_forget()
    state = "disabled" if editing else "normal"
    # R49 F: in edit mode the DATE opens only for admin; tooth fixed.
    dstate = "normal" if editing and can_edit_date(
        getattr(tab, "current_role", None)) else state
    for attr, st in (("e_sess_date", dstate), ("e_sess_tooth", state)):
        w = getattr(tab, attr, None)
        if w is not None:
            try:
                w.config(state=st)
            except Exception:
                pass
    locked = editing and not can_edit_money(tab)
    mstate = "disabled" if locked else "normal"
    for attr in ("e_sess_total", "e_sess_paid"):
        w = getattr(tab, attr, None)
        if w is not None:
            try:
                w.config(state=mstate)
            except Exception:
                pass
    lock_lbl = getattr(tab, "lbl_money_lock", None)
    if lock_lbl is not None:
        lock_lbl.config(text="🔒 " + sess_t("sess.money_locked", lang) if locked else "")


def change_session_date(fid, session, new_date, role):
    """R49 F: move a session to `new_date` — ADMIN ONLY (guard for
    the store/save path; layered on the 24h rule). Moves the
    session's own diagnoses / procedures / financial rows, plus
    the visit complaints row when no other session stays on the
    old date; bumps updated_at on every moved row and queues the
    financial rows for sync. session["date"] is updated in place,
    so replace_session_money lands on the NEW date. True on a
    move, False when unchanged. ValueError: bad date.
    PermissionError: not admin (nothing is touched)."""
    from src.models.database import get_connection, init_db
    from src.models.finance_sync import queue_synced_row
    old = session.get("date") or ""
    if new_date == old:
        return False
    if not valid_date(new_date):
        raise ValueError("session date must be a real YYYY-MM-DD date")
    if not can_edit_date(role):
        raise PermissionError("Only the admin may change a session date")
    init_db(); now = datetime.now().isoformat()
    conn = get_connection(); cur = conn.cursor()
    try:
        own = set(session.get("diagnosis_ids") or ()) | set(session.get("procedure_ids") or ())
        others = sum(1 for tb in ("diagnoses", "procedures")
                     for r in cur.execute(f"SELECT id FROM {tb} WHERE patient_file=? AND visit_date=?", (fid, old)) if r[0] not in own)
        groups = (("diagnoses", "diagnosis_ids"), ("procedures", "procedure_ids"), ("financials", "financial_ids"))
        for tb, idkey in groups:
            for rid in session.get(idkey) or ():
                cur.execute(f"UPDATE {tb} SET visit_date=?, updated_at=? WHERE id=? AND patient_file=?", (new_date, now, rid, fid))
                if tb == "financials":
                    queue_synced_row(conn, "financials", rid)
        if session.get("complaints_id") and others == 0:
            cur.execute("UPDATE complaints SET visit_date=?, updated_at=? WHERE patient_file=? AND visit_date=?", (new_date, now, fid, old))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally: conn.close()
    session["date"] = new_date
    return True
