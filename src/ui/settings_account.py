"""Settings account actions (Item 12 wave): Rename User + Change Password.

Lives here, not settings_ui.py, because that file is at the 200-line
limit. Functions take the SettingsTab instance (`tab`) and use its
entry widgets (tab.rn_old / rn_new / rn_pw / pw_old / pw_new / pw_conf).
Policy (owner): every user changes ONLY their own password; only the
admin may change another user's password, and only via the server API;
a username can be changed only by the admin.
"""
from tkinter import messagebox

from src.config.strings import t
from src.models.database import get_setting
from src.utils.auth import change, get_current_role, get_current_user, rename_user, verify


def _L(tab):
    """Active language of the Settings tab (set at build time)."""
    return getattr(tab, "lang", None) or getattr(getattr(tab, "app", None), "lang", "en") or "en"


def rename_user_ui(tab):
    user, role = get_current_user(), get_current_role()
    old, new, pw = tab.rn_old.get().strip(), tab.rn_new.get().strip(), tab.rn_pw.get()
    if not user or role != "admin":
        return messagebox.showerror(t("settings.rename_title", _L(tab)), t("settings.rename_admin_only_msg", _L(tab)))
    if not verify(user, pw):
        return messagebox.showerror(t("settings.rename_title", _L(tab)), t("settings.rename_wrong_pw", _L(tab)))
    ok, msg = rename_user(user, role, old, new)
    if not ok:
        return messagebox.showerror(t("settings.rename_title", _L(tab)), msg)
    url = (get_setting("sync_server_url", "") or "").strip()
    if not url:
        return messagebox.showinfo(t("settings.rename_title", _L(tab)), t("settings.rename_local", _L(tab)))
    from src.models.sync import SyncClient
    cl = SyncClient(url)
    ok_login, _ = cl.login(user, pw)
    if not ok_login:
        return messagebox.showinfo(t("settings.rename_title", _L(tab)), t("settings.rename_local_server_fail_login", _L(tab)))
    ok_srv, err = cl.rename_user(old, new)
    if ok_srv:
        messagebox.showinfo(t("settings.rename_title", _L(tab)), t("settings.rename_both", _L(tab)))
    else:
        messagebox.showinfo(t("settings.rename_title", _L(tab)), t("settings.rename_server_failed", _L(tab)).format(err=err))


def change_password(tab):
    user = get_current_user()
    old, new, conf = tab.pw_old.get(), tab.pw_new.get(), tab.pw_conf.get()
    if not user:
        return messagebox.showerror(t("settings.pw_title", _L(tab)), t("settings.pw_not_logged", _L(tab)))
    if len(new) < 4:
        return messagebox.showerror(t("settings.pw_title", _L(tab)), t("settings.pw_too_short", _L(tab)))
    if new != conf:
        return messagebox.showerror(t("settings.pw_title", _L(tab)), t("settings.pw_mismatch", _L(tab)))
    ok, msg = change(user, old, user, new)
    if not ok:
        return messagebox.showerror(t("settings.pw_title", _L(tab)), msg)
    url = (get_setting("sync_server_url", "") or "").strip()
    if not url:
        return messagebox.showinfo(t("settings.pw_title", _L(tab)), t("settings.pw_local", _L(tab)))
    from src.models.sync import SyncClient
    cl = SyncClient(url)
    ok_login, _ = cl.login(user, old)
    if not ok_login:
        return messagebox.showinfo(t("settings.pw_title", _L(tab)), t("settings.pw_local_server_fail", _L(tab)))
    ok_srv, err = cl.change_password(old, new)
    if ok_srv:
        messagebox.showinfo(t("settings.pw_title", _L(tab)), t("settings.pw_both", _L(tab)))
    else:
        messagebox.showinfo(t("settings.pw_title", _L(tab)), t("settings.pw_server_failed", _L(tab)).format(err=err))
