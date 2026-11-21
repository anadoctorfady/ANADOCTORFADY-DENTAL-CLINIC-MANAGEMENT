"""Edit / delete for clinical history rows (Job 3d, round 12).

The 24h rule lives in src/models/edit_rules.py: admin always; the
author doctor within 24h of created_at; after 24h admin only. Legacy
rows (author None) may be edited by any doctor within 24h. The
row's created_at falls back to its visit_date when NULL (old rows).

Edit keeps the ORIGINAL created_at, so editing never restarts the
24h window. Both actions re-check the rule at click time (a row can
age past 24h while the page is open).
"""
from tkinter import messagebox, simpledialog

from src.config.strings import t
from src.models.database import get_connection
from src.models.edit_rules import block_reason, can_delete, can_edit

COLS = {"diagnoses": "diagnosis", "procedures": "procedure_done"}


def row_allowed(tab, row, delete=False):
    """(may_edit, reason_or_None) for one history row dict."""
    lang = getattr(tab.app, "lang", "en")
    created = row.get("created_at") or row.get("visit_date")
    check = can_delete if delete else can_edit
    ok = check(tab.current_role, row.get("author"), created,
               username=tab.current_user)
    return ok, None if ok else block_reason(lang)


def edit_history_row(tab, table, row):
    """Edit one diagnoses/procedures row in place. Returns True if saved."""
    lang = getattr(tab.app, "lang", "en")
    ok, reason = row_allowed(tab, row)
    if not ok:
        messagebox.showwarning(t("savegate.not_allowed_title", lang), reason)
        return False
    col = COLS[table]
    prompt_key = ("clinical.diagnosis_label" if table == "diagnoses"
                  else "clinical.procedure_label")
    new = simpledialog.askstring(t("savegate.edit_title", lang),
                                 t(prompt_key, lang),
                                 initialvalue=row.get(col, ""), parent=tab)
    if new is None or not new.strip():
        return False
    conn = get_connection(); cur = conn.cursor()
    cur.execute(f"UPDATE {table} SET {col}=? WHERE id=?",
                (new.strip(), row["id"]))
    conn.commit(); conn.close()
    tab.app.refresh_clinical()
    return True


def delete_history_row(tab, table, row):
    """Delete one diagnoses/procedures row after confirmation."""
    lang = getattr(tab.app, "lang", "en")
    ok, reason = row_allowed(tab, row, delete=True)
    if not ok:
        messagebox.showwarning(t("savegate.not_allowed_title", lang), reason)
        return False
    if not messagebox.askyesno(t("savegate.delete", lang),
                               t("savegate.delete_confirm", lang)):
        return False
    conn = get_connection(); cur = conn.cursor()
    cur.execute(f"DELETE FROM {table} WHERE id=?", (row["id"],))
    conn.commit(); conn.close()
    tab.app.refresh_clinical()
    return True
