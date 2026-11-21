"""Sync Now button for the Settings sync frame. <200 lines.

Lives here (not settings_ui.py) because that file is at 198/200 lines.
Password is asked EVERY sync in a masked prompt and NEVER saved or
stored: the login flow passes only the username on success, so the
session has no password to reuse. Refused pushes stay queued and retry
later (sync_now behaviour); server-side role filtering already applies.
"""
import tkinter as tk
from tkinter import messagebox
from src.config.theme import current
from src.ui.rounded import rounded_button
from src.ui.rounded_widgets import RoundedEntry
from src.config.strings import t
from src.models.database import get_connection, get_setting
from src.models.sync import sync_now
from src.utils.auth import get_current_user


def _lang(lang=None):
    return lang or get_setting("language", "en") or "en"


def prompt_password(parent, username, lang=None):
    """Modal masked password prompt. -> password str, or None on cancel.

    Same masked-entry pattern as the finance re-auth gate / Users tab
    admin password field (Entry show="•"). The value lives only in a
    local variable and is never written anywhere.
    """
    th = current(); lang = _lang(lang)
    result = {"password": None}
    win = tk.Toplevel(parent)
    win.title(t("dlg.sync_password_title", lang))
    win.configure(bg=th["bg"]); win.transient(parent); win.grab_set()
    win.resizable(False, False)
    tk.Label(win, text=t("dlg.sync_prompt", lang).format(username=username),
             bg=th["bg"], fg=th["text"], justify="left").pack(padx=14, pady=(12, 6))
    entry = RoundedEntry(win, width=24, show="•")
    entry.pack(padx=14, pady=4); entry.focus_set()

    def _ok():
        result["password"] = entry.get(); win.destroy()

    def _cancel():
        win.destroy()

    row = tk.Frame(win, bg=th["bg"]); row.pack(pady=(4, 12))
    rounded_button(row, text=t("dlg.sync_btn", lang), bg=th["accent"], fg="white",
              relief="flat", command=_ok).pack(side="left", padx=6)
    rounded_button(row, text=t("dlg.sync_cancel", lang), bg=th["muted"], fg="white",
              relief="flat", command=_cancel).pack(side="left", padx=6)
    win.bind("<Return>", lambda e: _ok())
    win.bind("<Escape>", lambda e: _cancel())
    parent.wait_window(win)
    return result["password"]


def format_result(res, lang=None):
    """One-line summary of a sync_now() result dict, in `lang`
    (default: the saved language). English mode keeps the exact
    bilingual wording the old code produced."""
    lang = _lang(lang)
    if res.get("offline"):
        return t("dlg.sync_offline", lang)
    if not res.get("login"):
        return t("dlg.sync_login_failed", lang)
    pull = res.get("pull") or {}
    msg = t("dlg.sync_done", lang).format(
        push=res.get("push") or 0, patients=pull.get("patients", 0),
        visits=pull.get("visits", 0), financials=pull.get("financials", 0),
        employees=pull.get("employees", 0))
    errs = res.get("errors") or []
    if errs:
        msg += " — " + "; ".join(str(e) for e in errs)
    return msg


def do_sync_now(settings_tab, sync_fn=sync_now, prompt_fn=prompt_password, lang=None):
    """Run one sync. Returns (status, bilingual message, result dict).

    status: ok | offline | login_failed | not_logged_in | cancelled.
    GUI-free except the password prompt (injectable, so tests can stub
    both the prompt and sync_fn without a display or a real server).
    The password is a local only — it drops out of scope on return.
    """
    lang = _lang(lang)
    user = get_current_user()
    if not user:
        return "not_logged_in", t("dlg.sync_not_logged_in", lang), None
    url = (settings_tab.sync_url_var.get() or "").strip()
    center = (settings_tab.sync_center_var.get() or "").strip() or "main"
    if not url:
        res = {"offline": True, "login": False, "push": None, "pull": None,
               "errors": ["no server URL"]}
        return "offline", format_result(res, lang), res
    password = prompt_fn(settings_tab, user)
    if password is None:
        return "cancelled", t("dlg.sync_cancelled", lang), None
    conn = get_connection()
    try:
        res = sync_fn(conn, url, user, password, center)
    finally:
        conn.close()
    if res.get("offline"):
        return "offline", format_result(res, lang), res
    if not res.get("login"):
        return "login_failed", format_result(res, lang), res
    return "ok", format_result(res, lang), res


def _on_click(settings_tab):
    """Button callback: run the sync, then show the result."""
    status, msg, _res = do_sync_now(settings_tab)
    if status == "cancelled":
        return
    if status == "ok":
        messagebox.showinfo(t("dlg.sync_title", _lang()), msg)
    else:
        messagebox.showerror(t("dlg.sync_title", _lang()), msg)


def attach_sync_button(sync_frame, settings_tab):
    """Create the Sync Now button inside the Settings sync frame.

    Reads URL + center from the tab's sync_url_var / sync_center_var
    at click time, so edits take effect without re-saving first.
    """
    th = current()
    btn = rounded_button(sync_frame, text=t("dlg.sync_now_btn", _lang()),
                    bg=th["accent"], fg="white", relief="flat",
                    command=lambda: _on_click(settings_tab))
    btn.pack(anchor="w", pady=4)
    settings_tab.sync_now_btn = btn
    return btn
