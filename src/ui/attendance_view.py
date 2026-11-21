"""Attendance view (Phase 4): admin-only log of clock in/out times.
Reads the local attendance_log (synced later by the sync client)."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from src.config.theme import current, tree_style
from src.ui.rounded import rounded_button
from src.ui.rounded_widgets import RoundedEntry; from src.ui.rounded_lists import rounded_tree; from src.ui.zebra import zebra_tree
from src.config.strings import t
from src.models.database import get_setting
from src.models.database import get_connection
from src.models.attendance import list_attendance
def open_attendance_view(parent, current_user_role, lang=None):
    """Toplevel with date + user filters. Admin only; others get a message."""
    lang = lang or get_setting("language", "en") or "en"
    if (current_user_role or "doctor") != "admin":
        messagebox.showinfo(t("dlg.at_title", lang), t("dlg.at_admin_only_msg", lang))
        return None
    th = current()
    win = tk.Toplevel(parent)
    win.title(t("dlg.at_title", lang)); win.geometry("680x440")
    win.configure(bg=th["bg"])
    frm = tk.Frame(win, bg=th["panel"]); frm.pack(fill="x", padx=10, pady=8)
    tk.Label(frm, text=t("dlg.at_date", lang), bg=th["panel"], fg=th["text"]).pack(side="left", padx=4)
    e_date = RoundedEntry(frm, width=12); e_date.pack(side="left", padx=4)
    e_date.insert(0, date.today().isoformat())
    tk.Label(frm, text=t("dlg.at_user", lang), bg=th["panel"], fg=th["text"]).pack(side="left", padx=4)
    e_user = RoundedEntry(frm, width=14); e_user.pack(side="left", padx=4)
    tree = rounded_tree(win, columns=("user", "action", "time", "device"), style=tree_style("Attendance"), pack={"fill": "both", "expand": True, "padx": 10, "pady": 4})
    for c, h in [("user", t("dlg.at_head_user", lang)), ("action", t("dlg.at_head_action", lang)),
                  ("time", t("dlg.at_head_time", lang)), ("device", t("dlg.at_head_device", lang))]:
        tree.heading(c, text=h)
    tree.column("action", width=70, anchor="center")
    def refresh():
        for i in tree.get_children():
            tree.delete(i)
        conn = get_connection()
        try:
            rows = list_attendance(conn, username=e_user.get().strip() or None,
                                   date=e_date.get().strip() or None)
        finally:
            conn.close()
        for r in rows:
            tree.insert("", "end", values=(r["username"],
                t("dlg.at_in", lang) if r["action"] == "in" else t("dlg.at_out", lang),
                r["ts"], r.get("device_id") or ""))
        zebra_tree(tree)  # R21 item 6
    # Refresh on its OWN row: the date + user entries + button in one
    # row were wider than the dialog and the button was clipped at the
    # right edge (last gallery round). Own row = never clipped.
    btn_row = tk.Frame(win, bg=th["panel"]); btn_row.pack(fill="x", padx=10, pady=(0, 4), before=tree)
    rounded_button(btn_row, text=t("dlg.at_refresh", lang), bg=th["accent"], fg="white",
              relief="flat", command=refresh).pack(side="left", padx=4, pady=4)
    refresh()
    return win
