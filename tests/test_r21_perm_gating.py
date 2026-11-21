"""Round 21 (item 10): Settings + Users gated by admin-granted
permissions (the round-12 permission tree).

- The Users tab requires `users.manage`: hidden for a doctor
  without the grant, visible after grant_perm, visible for admin.
- Settings admin sections (sync/server, storage, backup/restore
  row, default currency, rename frame) require `settings.manage`;
  the personal sections (theme combo, Change Password) are built
  for everyone. A settings.manage delegate who is not admin sees
  the sections but the rename FIELDS stay note-only (renaming is
  root-only by the owner's username rule).
- apply_prefs applies the default currency only with
  settings.manage; the theme always applies.
Grants are local-only (user_grants), as before.
GUI parts skip without a display."""
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

from src.models.permissions import grant_perm, has_perm, revoke_perm
from src.utils.auth import create_user, set_current_user
from tests.test_templates_edit import isolated_db


def _tk():
    try:
        return tk.Tk()
    except Exception:
        return None


def _make_users():
    create_user("admin", "doc21", "pass1234", "doctor")
    create_user("admin", "nurse21", "pass1234", "nurse")


def test_perm_defaults_and_grants():
    with isolated_db():
        _make_users()
        assert has_perm("fady", "users.manage", "admin")
        assert has_perm("fady", "settings.manage", "admin")
        assert not has_perm("doc21", "users.manage", "doctor")
        assert not has_perm("doc21", "settings.manage", "doctor")
        assert not has_perm("nurse21", "users.manage", "nurse")
        assert grant_perm("doc21", "users.manage")
        assert has_perm("doc21", "users.manage", "doctor")
        assert not has_perm("doc21", "settings.manage", "doctor")
        assert revoke_perm("doc21", "users.manage")
        assert not has_perm("doc21", "users.manage", "doctor")


def _users_tab(root):
    from src.ui.users_tab import UsersTab
    nb = ttk.Notebook(root); nb.pack(fill="both", expand=True)
    tab = UsersTab(nb, SimpleNamespace(lang="en"))
    nb.add(tab, text="Users")
    tab.refresh()
    root.update()
    return tab


def _settings_tab(root):
    from src.ui.settings_ui import SettingsTab
    tab = SettingsTab(root, SimpleNamespace(lang="en"))
    tab.pack(fill="both", expand=True)
    root.update()
    return tab


def test_users_tab_visibility_by_permission():
    root = _tk()
    if root is None:
        print("SKIP users tab gating (no display)"); return
    root.withdraw()
    try:
        with isolated_db():
            _make_users()
            set_current_user("doc21")  # doctor, no grant
            tab = _users_tab(root)
            assert not tab._shown(), "doctor without grant sees Users tab"
            grant_perm("doc21", "users.manage")
            tab.refresh(); root.update()
            assert tab._shown(), "granted doctor cannot see Users tab"
            revoke_perm("doc21", "users.manage")
            tab.refresh(); root.update()
            assert not tab._shown(), "revoked doctor still sees Users tab"
            set_current_user("fady")  # admin
            tab.refresh(); root.update()
            assert tab._shown(), "admin cannot see Users tab"
    finally:
        root.destroy()
        set_current_user("fady")


def test_settings_sections_by_permission():
    root = _tk()
    if root is None:
        print("SKIP settings gating (no display)"); return
    root.withdraw()
    try:
        with isolated_db():
            _make_users()
            set_current_user("doc21")  # doctor, no grant
            tab = _settings_tab(root)
            for w in (tab._sync_wrap, tab.storage_wrap, tab._rn_wrap,
                      tab._brow1, tab._cur_wrap):
                assert w.winfo_manager() != "pack", "admin section visible to plain doctor"
            assert tab.pw_old is not None  # personal: change password stays
            assert tab._theme_combo is not None  # personal: theme stays
            assert tab.rn_old is None
            grant_perm("doc21", "settings.manage")
            tab.refresh_role_sections(); root.update()
            for w in (tab._sync_wrap, tab.storage_wrap, tab._rn_wrap,
                      tab._brow1, tab._cur_wrap):
                assert w.winfo_manager() == "pack", "admin section hidden from granted doctor"
            assert tab.rn_old is None  # delegate: rename fields stay note-only
            set_current_user("fady")  # admin: everything, incl. rename fields
            tab.refresh_role_sections(); root.update()
            for w in (tab._sync_wrap, tab.storage_wrap, tab._rn_wrap,
                      tab._brow1, tab._cur_wrap):
                assert w.winfo_manager() == "pack", "admin section hidden from admin"
            assert tab.rn_old is not None
    finally:
        root.destroy()
        set_current_user("fady")


def test_apply_prefs_currency_gate():
    root = _tk()
    if root is None:
        print("SKIP apply_prefs gate (no display)"); return
    root.withdraw()
    from unittest import mock
    from src.config.settings import get_default_currency
    try:
        with isolated_db():
            _make_users()
            set_current_user("doc21")
            tab = _settings_tab(root)
            before = get_default_currency()
            tab.cur_var.set("EUR - Euro")
            with mock.patch("src.ui.settings_ui.messagebox.showinfo"):
                tab.apply_prefs()
            assert get_default_currency() == before, \
                "plain doctor changed the default currency"
            grant_perm("doc21", "settings.manage")
            with mock.patch("src.ui.settings_ui.messagebox.showinfo"):
                tab.apply_prefs()
            assert get_default_currency() == "EUR", \
                "granted doctor could not set the default currency"
    finally:
        root.destroy()
        set_current_user("fady")
