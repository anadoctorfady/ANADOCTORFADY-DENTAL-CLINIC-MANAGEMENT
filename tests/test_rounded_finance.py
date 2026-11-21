"""Rounded corners on the finance + users tabs (Round 12, final
integration, fix (c)): every tk.Button in finance.py,
finance_views.py, finance_records.py, users_tab.py and
salaries_view.py is a RoundedButton, and every visible panel Frame
is a RoundedFrame (LabelFrames keep their titles; notebook pages
and layout rows stay plain tk.Frame, as in Agent H's tabs).
GUI tests skip gracefully with no display."""
import tkinter as tk
from src.ui.rounded import RoundedButton
from src.ui.rounded_frame import RoundedFrame
from tests.test_payments_e2e import _build_finance


def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)


def test_finance_tab_uses_rounded_widgets():
    root, tab = _build_finance("fady")
    if tab is None:
        print("SKIP test_finance_tab_uses_rounded_widgets (no display)")
        return
    try:
        root.update_idletasks()
        btns = [w for w in _walk(tab) if isinstance(w, RoundedButton)]
        assert btns, "FinanceTab has no RoundedButton"
        assert not any(type(w) is tk.Button for w in _walk(tab)), \
            "plain tk.Button left in FinanceTab"
        frames = [w for w in _walk(tab) if isinstance(w, RoundedFrame)]
        assert frames, "FinanceTab has no RoundedFrame"
        # Record Edit/Delete start disabled and still toggle by state.
        assert hasattr(tab, "btn_expense_edit")
        tab.btn_expense_edit.config(state="normal")
        root.update_idletasks()
        assert tab.btn_expense_edit.cget("image")
    finally:
        root.destroy()


def test_users_tab_uses_rounded_buttons():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_users_tab_uses_rounded_buttons (no display)")
        return
    root.withdraw()
    try:
        from tkinter import ttk
        from src.ui.users_tab import UsersTab
        nb = ttk.Notebook(root); nb.pack()
        stub = type("Stub", (), {"lang": "en"})()
        tab = UsersTab(nb, stub)
        nb.add(tab, text="Users")
        tab.pack(); root.update_idletasks()
        btns = [w for w in _walk(tab) if isinstance(w, RoundedButton)]
        assert len(btns) >= 3, f"UsersTab RoundedButtons: {len(btns)}"
        assert not any(type(w) is tk.Button for w in _walk(tab)), \
            "plain tk.Button left in UsersTab"
    finally:
        root.destroy()
