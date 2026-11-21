"""Permission tree GUI tests (Round 12, Job 10): toggling in the
real tree writes user_grants, clicks toggle, non-admins never see
the tab/tree, deleting a user clears their grants. Model tests
live in tests/test_perm_tree.py. Skipped with no display; Xvfb."""
from src.models.permissions import grant_perm, get_user_grants
from src.utils.auth import set_current_user, get_current_role
from tests.test_perm_tree import _setup, _teardown


def _build_tab():
    """UsersTab in a notebook, or (None, None, None) with no display."""
    import tkinter as tk
    from tkinter import ttk
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None, None
    root.withdraw()
    nb = ttk.Notebook(root); nb.pack()
    from src.ui.users_tab import UsersTab
    tab = UsersTab(nb, app=None)
    nb.add(tab, text="  Users  ")
    return tab, nb, root


def _select_user(tab, name):
    for iid in tab.tree.get_children():
        if tab.tree.item(iid, "values")[0] == name:
            tab.tree.selection_set(iid)
            tab._load_perms()
            return iid
    raise AssertionError(f"{name} not in users tree")


def test_gui_tree_toggle_persists_and_marks():
    """Toggling a permission in the tree writes user_grants (re-read
    from the DB) and flips the ☐/☑ mark; toggling again removes it."""
    _setup()
    tab, nb, root = _build_tab()
    if tab is None:
        print("SKIP test_gui_tree_toggle_persists_and_marks (no display)")
        _teardown()
        return
    try:
        set_current_user("fady")  # admin
        tab.refresh()
        assert nb.tab(tab, "state") == "normal"
        _select_user(tab, "pt_nurse")
        assert "pt_nurse" in tab.perm_user_lbl.cget("text")
        iid = tab._perm_items["finance.view"]
        assert tab.perm_tree.item(iid, "text").startswith("☐")
        assert tab._toggle_perm("pt_nurse", "finance.view") is True
        assert "finance.view" in get_user_grants("pt_nurse")
        assert tab.perm_tree.item(iid, "text").startswith("☑")
        assert tab._toggle_perm("pt_nurse", "finance.view") is True
        assert "finance.view" not in get_user_grants("pt_nurse")
        assert tab.perm_tree.item(iid, "text").startswith("☐")
        # Group rows are all present and expandable parents.
        assert tab.perm_tree.get_children("g:clinical")
        assert tab.perm_tree.get_children("g:finance")
    finally:
        set_current_user("fady")
        try: root.destroy()
        except Exception: pass
        _teardown()


def test_gui_click_row_toggles_and_non_admin_cannot_see_tree():
    """A real (synthetic) click on a permission row toggles it; a
    non-admin never sees the tab/tree at all, and _toggle_perm
    refuses them even if called directly."""
    _setup()
    tab, nb, root = _build_tab()
    if tab is None:
        print("SKIP test_gui_click_row_toggles_and_non_admin_cannot_see_tree (no display)")
        _teardown()
        return
    try:
        set_current_user("fady")
        tab.refresh()
        _select_user(tab, "pt_doc")
        iid = tab._perm_items["users.manage"]
        # bbox() needs laid-out rows: show the window + tab first.
        nb.select(tab); tab.perm_tree.see(iid)
        root.deiconify(); root.update_idletasks()
        x, y, _w, _h = tab.perm_tree.bbox(iid)
        class _Ev: pass
        ev = _Ev(); ev.y = y + 2
        tab._on_perm_click(ev)  # click toggles ON
        assert "users.manage" in get_user_grants("pt_doc")
        assert tab.perm_tree.item(iid, "text").startswith("☑")
        tab._on_perm_click(ev)  # click again toggles OFF
        assert "users.manage" not in get_user_grants("pt_doc")
        # Non-admin: the whole tab (tree included) is hidden.
        set_current_user("pt_doc")
        assert get_current_role() == "doctor"
        tab.refresh()
        assert nb.tab(tab, "state") == "hidden"
        assert tab._toggle_perm("pt_doc", "users.manage") is False
        assert "users.manage" not in get_user_grants("pt_doc")
    finally:
        set_current_user("fady")
        try: root.destroy()
        except Exception: pass
        _teardown()


def test_gui_delete_user_clears_grants():
    """Deleting a user from the tab drops their grants, so a
    recreated same-name user starts with role defaults only."""
    _setup()
    tab, nb, root = _build_tab()
    if tab is None:
        print("SKIP test_gui_delete_user_clears_grants (no display)")
        _teardown()
        return
    import src.ui.users_tab as ut
    old_ask, old_info, old_err = ut.messagebox.askyesno, ut.messagebox.showinfo, ut.messagebox.showerror
    ut.messagebox.askyesno = lambda *a, **k: True
    ut.messagebox.showinfo = lambda *a, **k: None
    ut.messagebox.showerror = lambda *a, **k: None
    try:
        grant_perm("pt_nurse", "finance.view")
        set_current_user("fady")
        tab.refresh()
        _select_user(tab, "pt_nurse")
        tab.delete()
        assert "finance.view" not in get_user_grants("pt_nurse")
        assert not any(tab.tree.item(i, "values")[0] == "pt_nurse"
                       for i in tab.tree.get_children())
    finally:
        ut.messagebox.askyesno, ut.messagebox.showinfo, ut.messagebox.showerror = old_ask, old_info, old_err
        set_current_user("fady")
        try: root.destroy()
        except Exception: pass
        _teardown()
