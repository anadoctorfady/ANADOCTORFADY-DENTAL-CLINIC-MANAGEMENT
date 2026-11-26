"""Round 14 wheel audit: native-scroll sweep over the remaining
scrollable surfaces. R56: trees/lists that live INSIDE a scroll
page now scroll the PAGE (the global page-scroll rule); only
surfaces in NO scroll page keep their native self-scroll (the
delegate's fallback). These tests pin both halves: in-page trees
move the page, dialog/standalone lists still move themselves.
GUI tests skip gracefully when no display is available.
"""
import tkinter as tk
from tkinter import ttk

from src.ui.appointments import AppointmentsTab
from src.ui.attendance_view import open_attendance_view
from src.ui.finance import FinanceTab
from src.ui.login import LoginWindow
from src.ui.phrase_picker import open_template_picker
from src.ui.scans_tab import build_scans_section
from src.ui.settings_sync_guide import open_linking_guide
from src.ui.template_manager import open_template_manager
from src.ui.users_tab import UsersTab
from src.ui.wheel_scroll import install_page_wheel, page_canvas_for
from src.utils.finance_gate import FinanceGate


class _Stub:
    lang = "en"
    current_patient = None
    current_user = "fady"
    current_role = "admin"
    finance_gate = None


def _root(w=1380, h=700):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.deiconify()
    root.geometry(f"{w}x{h}")
    root.update()
    return root


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def _fill_tree(tree, n=120, cols=3):
    for i in range(n):
        tree.insert("", "end", values=tuple(f"r{i}c{j}" for j in range(cols)))


def _wheel_moves(root, widget, view, label):
    """Down (MouseWheel + Button-5) then up (MouseWheel + Button-4)."""
    assert view()[1] < 1.0, f"{label} not scrollable in test setup"
    before = view()
    widget.event_generate("<MouseWheel>", delta=-120)
    root.update()
    assert view()[0] > before[0], f"{label}: MouseWheel down did not scroll"
    widget.event_generate("<Button-5>")
    root.update()
    assert view()[0] > before[0], f"{label}: Button-5 did not scroll"
    mid = view()
    widget.event_generate("<MouseWheel>", delta=120)
    root.update()
    assert view()[0] < mid[0], f"{label}: MouseWheel up did not scroll back"
    widget.event_generate("<Button-4>")
    root.update()
    assert view()[0] < mid[0], f"{label}: Button-4 did not scroll back"


def _wheel_moves_page(root, widget, page, label):
    """R56: down (MouseWheel + Button-5) then up (MouseWheel +
    Button-4) over an in-page widget: the PAGE must move every
    time; the widget itself must not move at all."""
    assert page.yview()[1] < 1.0, f"{label}: page not scrollable"
    own0 = widget.yview()
    before = page.yview()
    widget.event_generate("<MouseWheel>", delta=-120)
    root.update()
    assert page.yview()[0] > before[0], \
        f"{label}: MouseWheel down did not scroll page"
    assert widget.yview() == own0, f"{label}: wheel moved the widget"
    widget.event_generate("<Button-5>")
    root.update()
    assert page.yview()[0] > before[0], \
        f"{label}: Button-5 did not scroll page"
    mid = page.yview()
    widget.event_generate("<MouseWheel>", delta=120)
    root.update()
    assert page.yview()[0] < mid[0], \
        f"{label}: MouseWheel up did not scroll page back"
    widget.event_generate("<Button-4>")
    root.update()
    assert page.yview()[0] < mid[0], \
        f"{label}: Button-4 did not scroll page back"
    assert widget.yview() == own0, f"{label}: wheel-up moved the widget"


def test_finance_trees():
    root = _root()
    if root is None:
        print("SKIP test_finance_trees (no display)")
        return
    try:
        install_page_wheel(root)  # R56: the App installs this once
        app = _Stub()
        app.finance_gate = FinanceGate(verify_fn=lambda u, p: True)
        tab = FinanceTab(root, app)
        tab.pack(fill="both", expand=True)
        root.update()
        tab.e_gate_user.delete(0, tk.END)
        tab.e_gate_user.insert(0, "fady")
        tab.e_gate_pass.delete(0, tk.END)
        tab.e_gate_pass.insert(0, "x")
        tab._try_unlock()
        assert tab.gate.is_unlocked
        nb = next(w for w in _walk(tab) if isinstance(w, ttk.Notebook))
        for attr, label in (("tree_exp", "finance expenses"),
                            ("tree_lab", "finance lab"),
                            ("tree_debt", "finance debts"),
                            ("tree_centers", "finance centers")):
            tr = getattr(tab, attr)
            for tab_id in nb.tabs():
                if tr in list(_walk(nb.nametowidget(tab_id))):
                    nb.select(tab_id)
                    break
            _fill_tree(tr, 120, 4)
            root.update()
            # R56: in-page trees scroll the Finance page, not
            # themselves (round-14 native self-scroll superseded).
            page = page_canvas_for(tr)
            assert page is not None, f"{label}: tree has no page"
            _wheel_moves_page(root, tr, page, label)
    finally:
        root.destroy()


def test_appointments_tree_and_slots():
    root = _root()
    if root is None:
        print("SKIP test_appointments_tree_and_slots (no display)")
        return
    try:
        install_page_wheel(root)  # R56: the App installs this once
        tab = AppointmentsTab(root, _Stub())
        tab.pack(fill="both", expand=True)
        root.update()
        _fill_tree(tab.tree, 120, 6)
        root.update()
        # R56: the appointments tree + slots list scroll the
        # Appointments page, not themselves.
        page = page_canvas_for(tab.tree)
        assert page is not None, "appointments tree has no page"
        _wheel_moves_page(root, tab.tree, page, "appointments tree")
        _wheel_moves_page(root, tab.lb_slots.widget, page,
                          "appointments slots")
    finally:
        root.destroy()


def test_scans_attendance_users_trees():
    root = _root()
    if root is None:
        print("SKIP test_scans_attendance_users_trees (no display)")
        return
    try:
        install_page_wheel(root)  # R56: the App installs this once
        # R27 SUPERSESSION: the scans Treeview is now a thumbnail
        # GRID. In the real app the grid sits inside the clinical
        # page's scroll canvas, so the wheel over a tile scrolls
        # that canvas (wheel_scroll scoped handler). Reproduce the
        # real host: canvas + bind_canvas_wheel + a full grid.
        from src.ui.wheel_scroll import bind_canvas_wheel
        canvas = tk.Canvas(root, width=600, height=400)
        canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        sec = build_scans_section(inner, _Stub(), 1, "fady", "admin")
        sec.pack(fill="both", expand=True)
        grid = sec.thumb_grid
        grid.set_items([{"key": i, "name": f"s{i}.png", "sub": "",
                         "path": f"/nonexistent/s{i}.png",
                         "kind": "image"} for i in range(40)])
        inner.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
        root.update()
        bind_canvas_wheel(canvas)
        _wheel_moves(root, grid.tiles[0], canvas.yview, "scans grid page canvas")
        canvas.destroy()
        win = open_attendance_view(root, "admin", lang="en")
        root.update()
        tr = next(w for w in _walk(win) if isinstance(w, ttk.Treeview))
        _fill_tree(tr, 120, 4)
        root.update()
        # R56: the attendance dialog has NO scroll page, so the
        # delegate falls back to the native self-scroll.
        _wheel_moves(root, tr, tr.yview, "attendance tree")
        win.destroy()
        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True)
        tab = UsersTab(nb, _Stub())
        nb.add(tab, text="Users")
        root.update()
        _fill_tree(tab.tree, 60, 3)
        root.update()
        # R56: the Users tree lives in the Users scroll page, so
        # its wheel scrolls the page, not the tree.
        _wheel_moves_page(root, tab.tree, tab._scroll, "users tree")
    finally:
        root.destroy()


def test_template_phrase_listboxes_and_guide():
    root = _root(700, 600)
    if root is None:
        print("SKIP test_template_phrase_listboxes_and_guide (no display)")
        return
    try:
        # R56: these dialogs have NO scroll page, so the delegate
        # falls back to the native self-scroll -- install the real
        # policy and pin the fallback, not the uninstalled default.
        install_page_wheel(root)
        win = open_template_manager(root, "fady", lang="en")
        root.update()
        lb = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
        assert lb.yview()[1] < 1.0, "template list not scrollable in setup"
        _wheel_moves(root, lb, lb.yview, "template manager listbox")
        win.destroy()
        win = open_template_picker(root, "complaint", tk.Text(root),
                                   current_user="fady", lang="en")
        root.update()
        lb = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
        assert lb.yview()[1] < 1.0, "phrase list not scrollable in setup"
        _wheel_moves(root, lb, lb.yview, "phrase picker listbox")
        win.destroy()
        win = open_linking_guide(root)
        root.update()
        tx = next(w for w in _walk(win) if isinstance(w, tk.Text))
        assert tx.yview()[1] < 1.0, "linking guide not scrollable in setup"
        _wheel_moves(root, tx, tx.yview, "linking guide text")
        win.destroy()
    finally:
        root.destroy()


