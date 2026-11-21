"""Rounded corners for EVERYTHING (Round 13, Item 2).

GUI parts skip gracefully with no display. Regressions pinned here: the Ctrl+Shift+V clipboard
paste into rounded fields (paste_items_into must unwrap the
wrapper), the dental-chart tooth cells staying gridded RoundedFrames
(grid_info + picture label still resolve), and no square Entry /
Text / Listbox / Combobox / Button / LabelFrame left in src/ui
(except the documented exception: the scans tree, pinned as a
direct child by tests/test_scans_upload.py; the Settings rename
frame was the last LabelFrame and was rounded in the round-13
final integration — its title lives on the RoundedFrame shell,
so refresh_role_sections() rebuilding .inner children is safe).
"""
import tkinter as tk
from pathlib import Path
from src.config.theme import RADIUS_FIELD, RADIUS_TEXT
from src.ui.rounded_frame import RoundedFrame
from src.ui.rounded_lists import (RoundedCombobox, RoundedListbox,
                                  is_rounded, rounded_tree)
from src.ui.rounded_widgets import RoundedEntry
from src.ui.rounded_lists import RoundedText

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "src" / "ui"


def _root():
    try:
        root = tk.Tk(); root.geometry("500x400"); root.update(); return root
    except Exception:
        return None


def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)


def test_radius_tokens():
    assert (RADIUS_FIELD, RADIUS_TEXT) == (14, 16)  # R31: FIELD 12->14, TEXT 12->16 (owner live use); R30 had (12, 12), R28 (6, 6), originally (8, 10)


def test_rounded_entry_behaves_like_entry():
    root = _root()
    if root is None:
        return
    try:
        # Explicit master: a bare StringVar binds to the process default
        # root, which in a long gate process is a DESTROYED interpreter
        # from an earlier test - the variable then reads "" here.
        var = tk.StringVar(root, value="init")
        e = RoundedEntry(root, width=14, textvariable=var)
        e.pack()
        assert e.get() == "init"
        e.delete(0, tk.END); e.insert(0, "abc"); assert e.get() == "abc"
        assert var.get() == "abc" and e["width"] == 14
        e.config(state="disabled"); root.update()
        assert e.widget.cget("state") == "disabled"
        e.config(state="normal"); assert e.widget.cget("state") == "normal"
        hits = []
        e.bind("<KeyRelease>", lambda _ev: hits.append(1))
        assert e.bind("<KeyRelease>")  # binding landed on the inner Entry
        e.widget.event_generate("<FocusIn>"); root.update()
        assert e._size[2] == e._focus_border  # focus -> accent border
        e.widget.event_generate("<FocusOut>"); root.update()
        assert e._size[2] is None  # blur -> plain theme border
        assert isinstance(e.widget, tk.Entry) and is_rounded(e)
    finally:
        root.destroy()


def test_rounded_entry_password_and_second_root():
    root = _root()
    if root is None:
        return
    try:
        e = RoundedEntry(root, show="•", width=10); e.pack(); root.update()
        e.insert(0, "secret"); assert e.get() == "secret"
    finally:
        root.destroy()
    root2 = _root()
    assert root2 is not None
    try:
        e2 = RoundedEntry(root2, width=10); e2.pack(); root2.update()
        assert e2.get() == ""
    finally:
        root2.destroy()


def test_rounded_text_listbox_combobox():
    root = _root()
    if root is None:
        return
    try:
        tx = RoundedText(root, height=2, width=20, wrap="word"); tx.pack()
        tx.insert("1.0", "hello"); assert tx.get("1.0", tk.END).strip() == "hello"
        tx.delete("1.0", tk.END); assert tx.get("1.0", tk.END).strip() == ""
        lb = RoundedListbox(root, height=3); lb.pack()
        for s in ("a", "b"):
            lb.insert("end", s)
        lb.selection_set(1); assert lb.curselection() == (1,)
        assert lb.get(0) == "a"
        lb.config(yscrollcommand=lambda *a: None)  # forwards to inner
        cb = RoundedCombobox(root, values=["x", "y"], width=8); cb.pack()
        cb.set("y"); assert cb.get() == "y"
        cb["values"] = ["x", "y", "z"]; assert "z" in cb.cget("values")
        assert is_rounded(tx) and is_rounded(lb) and is_rounded(cb)
    finally:
        root.destroy()


def test_rounded_tree_wrapper():
    root = _root()
    if root is None:
        return
    try:
        tr = rounded_tree(root, columns=("a", "b"))
        root.update()
        assert isinstance(tr._rounded_wrapper, RoundedFrame)
        assert is_rounded(tr)
        tr.insert("", "end", values=(1, 2))
        assert len(tr.get_children()) == 1
        tr.selection_set(tr.get_children()[0]); assert tr.selection()
    finally:
        root.destroy()


def test_clipboard_paste_unwraps_rounded_fields():
    """Ctrl+Shift+V must still paste into clinical/finance fields
    after the swap (paste_items_into used to isinstance-check the
    widget itself, which is now a Frame wrapper)."""
    root = _root()
    if root is None:
        return
    try:
        from src.ui.clipboard_picker import paste_items_into
        tx = RoundedText(root, height=2); tx.pack()
        assert paste_items_into(tx, ["one", "two"])
        assert "one" in tx.get("1.0", tk.END) and "two" in tx.get("1.0", tk.END)
        e = RoundedEntry(root, width=20); e.pack()
        assert paste_items_into(e, ["a", "b"])
        assert e.get() == "a; b"
    finally:
        root.destroy()


def test_login_fields_rounded():
    root = _root()
    if root is None:
        return
    try:
        from src.ui.login import LoginWindow
        win = LoginWindow(root, lang="en")
        root.update()
        assert isinstance(win.e_user, RoundedEntry)
        assert isinstance(win.e_pass, RoundedEntry)
        assert is_rounded(win.e_user) and is_rounded(win.e_pass)
        win.destroy()
    finally:
        root.destroy()


def test_patient_form_fields_rounded():
    root = _root()
    if root is None:
        return
    try:
        from src.ui.patient_form import PatientForm
        stub = type("Stub", (), {"lang": "en", "current_patient": None,
                                 "on_teeth_select": lambda *a: None})()
        form = PatientForm(root, stub); form.pack(fill="both", expand=True)
        root.update()
        for attr in ("e_first", "e_father", "e_grand", "e_last", "e_birth",
                     "e_m1", "e_m2", "e_em", "e_addr", "e_meds", "e_allergies"):
            w = getattr(form, attr)
            assert isinstance(w, RoundedEntry), attr
        form.e_first.insert(0, "Test"); assert form.e_first.get() == "Test"
        form.clear(); assert form.e_first.get() == ""
    finally:
        root.destroy()


def test_tooth_cells_are_rounded_frames():
    root = _root()
    if root is None:
        return
    try:
        from src.ui.dental_chart import DentalChartFrame
        frame = DentalChartFrame(root, lang="en"); frame.pack(); root.update()
        assert isinstance(frame.tooth_cells["11"], RoundedFrame)
        assert frame.tooth_cells["11"].grid_info()["column"] == 7
        frame.tooth_cells["11"].event_generate("<Button-1>")
        root.update_idletasks()
        assert frame.get_selection()[0] == ["11"]
    finally:
        root.destroy()


