"""Round 14 wheel audit (native sweep, part 2): a native Treeview
(the fixture used to be the clinical notes section's tree; that
section was REMOVED in round 21 item 5, so the fixture is now a
plain equivalent Treeview) and the login window's last-login list.
Companion to tests/test_wheel_native.py.
"""
import tkinter as tk
from tkinter import ttk

from src.ui.login import LoginWindow


def _tree_section(parent):
    """Plain frame holding one native ttk.Treeview (3 columns) --
    the wheel fixture that replaces the removed notes section."""
    sec = tk.Frame(parent)
    tr = ttk.Treeview(sec, columns=("date", "author", "text"),
                      show="headings", height=6)
    tr.pack(fill="both", expand=True)
    return sec


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


def test_notes_tree_and_login_list():
    root = _root(900, 600)
    if root is None:
        print("SKIP test_notes_tree_and_login_list (no display)")
        return
    try:
        sec = _tree_section(root)
        sec.pack(fill="both", expand=True)
        root.update()
        tr = next(w for w in _walk(sec) if isinstance(w, ttk.Treeview))
        _fill_tree(tr, 40, 3)
        root.update()
        _wheel_moves(root, tr, tr.yview, "notes tree")
        sec.destroy()
        root.withdraw()
        win = LoginWindow(root, lang="en")
        root.update()
        # 30 rows like refresh_last_logins() builds them, with the same
        # per-label bindings the real list uses.
        for w in win._ll_inner.winfo_children():
            w.destroy()
        for i in range(30):
            lbl = tk.Label(win._ll_inner, text=f"user{i:02d} — 2026-11-09 10:{i:02d}")
            lbl.pack(anchor="w")
            lbl.bind("<MouseWheel>", win._ll_wheel)
            lbl.bind("<Button-4>", win._ll_wheel)
            lbl.bind("<Button-5>", win._ll_wheel)
        root.update()
        assert win._ll_canvas.yview()[1] < 1.0, "last-login list not scrollable"
        lbl = win._ll_inner.winfo_children()[0]
        _wheel_moves(root, lbl, win._ll_canvas.yview, "last-login list")
        win.destroy()
    finally:
        root.destroy()
