"""Round 16 worker E: Users tab layout — narrow wheel-scrollable
users table (2-3 names), fully visible permissions tree, narrower
create form. EN + AR. GUI tests skip gracefully with no display."""
from pathlib import Path

from src.models.database import get_connection
from tests.test_settings_storage_r16 import _TMP, _tk, isolated_db


def _entry_width(widget):
    """Width of the tk.Entry inside a RoundedEntry wrapper."""
    import tkinter as tk
    for w in widget.winfo_children():
        if isinstance(w, tk.Entry):
            return int(w.cget("width"))
    return None


def _build_users(lang="en"):
    import tkinter as tk
    from tkinter import ttk
    root = _tk()
    if root is None:
        return None, None, None
    root.withdraw()
    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)
    from src.ui.users_tab import UsersTab

    class _App:
        pass
    app = _App()
    app.lang = lang
    tab = UsersTab(nb, app)
    nb.add(tab, text="users")
    return tab, nb, root


def test_users_layout_gui():
    """Users table is narrow (2-3 names, height 3, wheel-scrollable),
    the permissions tree is fully visible (every row has a bbox and
    sits on screen), and the create form is narrower than before."""
    from src.utils.auth import set_current_user
    with isolated_db():
        # 20 seeded users + fady = 21 rows: more than fit even when
        # the tree stretches to the permissions panel's height, so
        # the wheel genuinely has something to scroll.
        _seeded = [f"r16u{i:02d}" for i in range(1, 21)]
        conn = get_connection()
        cur = conn.cursor()
        for u in _seeded:
            cur.execute("INSERT OR IGNORE INTO users(username,password_hash,role) VALUES(?,?,?)",
                        (u, "x", "doctor"))
        conn.commit()
        conn.close()
        tab, nb, root = _build_users("en")
        if tab is None:
            print("SKIP test_users_layout_gui (no display)")
            return
        try:
            set_current_user("fady")  # admin
            tab.refresh()
            assert nb.tab(tab, "state") == "normal"
            nb.select(tab)
            root.geometry("1200x800")
            root.deiconify()
            root.update_idletasks()
            root.update()
            # Narrow table: fixed columns 110+70+80, 3 visible rows.
            widths = [int(tab.tree.column(c, "width")) for c in ("user", "role", "center")]
            assert widths == [110, 70, 80], widths
            assert sum(widths) <= 300
            assert int(tab.tree.cget("height")) == 3
            assert tab.tree.winfo_width() <= 300, tab.tree.winfo_width()
            # Vertical scrollbar present and mapped.
            assert hasattr(tab.tree, "_v_scrollbar")
            assert tab.tree._v_scrollbar.winfo_ismapped()
            # R56: no per-widget wheel binding anymore -- the ONE
            # central class binding (installed by the App at
            # startup; installed here explicitly, this tab is
            # built bare) owns Treeview/Listbox wheels.
            from src.ui.wheel_scroll import install_page_wheel
            install_page_wheel(root)
            for ev in ("<Button-4>", "<Button-5>", "<MouseWheel>"):
                assert root.bind_class("Treeview", ev), \
                    f"no class wheel binding for {ev}"
            assert not tab.tree.bind("<Button-4>"), \
                "stale per-widget wheel binding"
            # R56: the wheel goes to whatever can scroll -- the
            # Users page when it overflows, the tree itself when
            # the page fits (the fallback). The page is borderline
            # at 1200x800 (region 764 vs 771px viewport in EN;
            # a saved AR language makes it overflow), so pin
            # BOTH branches instead of assuming one.
            assert len(tab.tree.get_children()) == 21
            assert tab.tree.yview()[0] == 0.0
            page_moves = tab._scroll.yview() != (0.0, 1.0)
            page0, tree0 = tab._scroll.yview(), tab.tree.yview()
            tab.tree.event_generate("<Button-5>")
            root.update_idletasks()
            if page_moves:
                assert tab._scroll.yview()[0] > page0[0], \
                    "wheel did not scroll the Users page"
                assert tab.tree.yview() == tree0, \
                    "wheel moved the tree instead of the page"
                mid = tab._scroll.yview()
                tab.tree.event_generate("<Button-4>")
                root.update_idletasks()
                assert tab._scroll.yview()[0] < mid[0], \
                    "wheel-up did not scroll the page back"
            else:
                assert tab.tree.yview()[0] > 0.0, tab.tree.yview()
                tab.tree.event_generate("<Button-4>")
                root.update_idletasks()
                assert tab.tree.yview()[0] == 0.0, tab.tree.yview()
            # Permissions tree: every row visible, nothing clipped.
            assert int(tab.perm_tree.cget("height")) == 16
            for iid in tab.perm_tree.get_children(""):
                assert tab.perm_tree.bbox(iid), f"group row {iid} not visible"
                for child in tab.perm_tree.get_children(iid):
                    assert tab.perm_tree.bbox(child), f"perm row {child} not visible"
            assert tab.perm_tree.winfo_width() > tab.tree.winfo_width()
            bottom = tab.perm_tree.winfo_rooty() + tab.perm_tree.winfo_height()
            assert bottom <= root.winfo_rooty() + root.winfo_height(), "perm tree runs off screen"
            # Create form narrower than the old width-18 entries.
            assert _entry_width(tab.e_name) == 12
            assert _entry_width(tab.e_pw) == 12
            assert _entry_width(tab.e_center) == 12
            assert _entry_width(tab.e_admin_pw) == 12
        finally:
            set_current_user("fady")
            conn = get_connection()
            conn.execute("DELETE FROM users WHERE username LIKE 'r16u%'")
            conn.commit()
            conn.close()
            try:
                root.destroy()
            except Exception:
                pass


def test_users_layout_ar_gui():
    """Same layout checks in Arabic: the permissions tree stays fully
    visible (no row clipped) with the longer Arabic labels."""
    from src.utils.auth import set_current_user
    with isolated_db():
        tab, nb, root = _build_users("ar")
        if tab is None:
            print("SKIP test_users_layout_ar_gui (no display)")
            return
        try:
            set_current_user("fady")
            tab.refresh()
            nb.select(tab)
            root.geometry("1200x800")
            root.deiconify()
            root.update_idletasks()
            root.update()
            for iid in tab.perm_tree.get_children(""):
                assert tab.perm_tree.bbox(iid), f"group row {iid} not visible (ar)"
                for child in tab.perm_tree.get_children(iid):
                    assert tab.perm_tree.bbox(child), f"perm row {child} not visible (ar)"
            assert tab.perm_tree.winfo_width() > tab.tree.winfo_width()
        finally:
            set_current_user("fady")
            try:
                root.destroy()
            except Exception:
                pass
