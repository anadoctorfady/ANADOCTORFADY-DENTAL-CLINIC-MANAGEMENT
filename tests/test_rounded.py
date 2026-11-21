"""Rounded corners (Round 12, Item B). GUI parts skip gracefully with
no display; pure-PIL tests always run. Regressions: shade("white"),
fill="x" button swell, PhotoImages dying across Tk roots."""
import tkinter as tk
from tkinter import ttk
from src.config.theme import (DARK, GRADIENT, LIGHT, RADIUS_BTN,
                              RADIUS_CARD, RADIUS_PANEL, RADIUS_TABLE)
from src.ui.rounded import (RoundedButton, blend, gradient_pil, hex_to_rgb,
                            rounded_button, rounded_pil, shade)
from src.ui.rounded_frame import RoundedFrame

def _root():
    """A mapped Tk root (withdrawn windows never get real geometry),
    or None when no display is available."""
    try:
        root = tk.Tk(); root.geometry("500x400"); root.update(); return root
    except Exception:
        return None

def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)

def test_hex_to_rgb_named_and_hex():
    assert hex_to_rgb("white") == (255, 255, 255) and hex_to_rgb("#7C3AED") == (124, 58, 237)

def test_shade_named_colour_regression():
    # Gate 2026-11-09: shade("white") raised ValueError 'wh' and broke
    # every screen with a white button (shell top bar).
    assert shade("white", 1.0) == "#FFFFFF"
    assert shade("white", 0.92) == "#EAEAEA"  # 255 * 0.92 = 234.6 -> 234
    assert shade("#A85F33", 0.5) == "#542F19"

def test_blend_midpoint():
    assert blend("#FFFFFF", "#000000", 0.5) == "#7F7F7F" and blend("#A85F33", "#A85F33", 0.5) == "#A85F33"

def test_rounded_pil_transparent_corners():
    im = rounded_pil(40, 30, 10, "#A85F33", "#E3D8CC")
    assert im.getpixel((0, 0))[3] == 0  # corner fully transparent
    assert im.getpixel((39, 29))[3] == 0
    assert im.getpixel((20, 15))[3] == 255
    assert im.getpixel((20, 15))[:3] == (168, 95, 51)
    assert im.getpixel((20, 0))[:3] == (227, 216, 204)  # border on edge

def test_gradient_pil_ends_and_corners():
    im = gradient_pil(90, 30, 8)
    assert im.getpixel((0, 0))[3] == 0
    assert im.getpixel((45, 15))[3] == 255
    assert im.getpixel((0, 15))[:3] == hex_to_rgb(GRADIENT[0])
    assert im.getpixel((89, 15))[:3] == hex_to_rgb(GRADIENT[-1])

def test_radius_tokens():
    assert (RADIUS_BTN, RADIUS_CARD, RADIUS_PANEL, RADIUS_TABLE) == (12, 16, 16, 16)  # R31: TABLE 12->16 (owner live use); R30 had (12, 16, 16, 12), R28 (6, 8, 8, 6), originally (8, 12, 12, 10)
    assert all(1 <= r <= 24 for r in (RADIUS_BTN, RADIUS_CARD, RADIUS_PANEL, RADIUS_TABLE))

def test_rounded_button_builds_clicks_and_states():
    root = _root()
    if root is None:
        return
    try:
        hits = []
        b = rounded_button(root, text="Save", bg="#A85F33", fg="white",
                           command=lambda: hits.append(1))
        b.pack(); root.update()
        assert b.cget("image") and b.cget("text") == "Save"
        b.invoke(); assert hits == [1]
        normal_img = b.cget("image")
        b.config(state="disabled"); root.update()
        disabled_img = b.cget("image")
        assert disabled_img != normal_img  # disabled variant
        b.config(state="normal"); root.update()
        assert b.cget("image") == normal_img  # back to normal variant
        b.config(text="Saved"); root.update()  # rename re-renders (new width)
        assert b.cget("text") == "Saved" and b.cget("image")
        b._on_enter(); b._on_press(); b._on_release(); b._on_leave()
    finally:
        root.destroy()

def test_rounded_button_white_bg_and_gradient():
    root = _root()
    if root is None:
        return
    try:
        b = rounded_button(root, text="EN", bg="white", fg="#7C3AED")
        b.pack(); root.update()
        assert b.cget("image")
        g = rounded_button(root, text="Go", gradient=True)
        g.pack(); root.update()
        assert g.cget("image")
        g._on_enter(); g._on_leave()
    finally:
        root.destroy()

def test_rounded_button_stretch_regression():
    # A fill="x" button must NOT swell (before the inset fix it grew
    # 32px -> 280px tall and squeezed the rest of the window away).
    root = _root()
    if root is None:
        return
    try:
        root.geometry("400x300")
        b = rounded_button(root, text="New Patient", bg="#A85F33", fg="white")
        b.pack(fill="x", padx=10, pady=10)
        tk.Frame(root, bg="white").pack(fill="both", expand=True)
        root.update(); root.update_idletasks(); root.update()
        assert b.winfo_width() > 300 and b.winfo_height() < 60, (
            b.winfo_width(), b.winfo_height())
    finally:
        root.destroy()

def test_rounded_button_survives_second_root():
    # Gate 2026-11-09: a bare PhotoImage binds to _default_root, which
    # still points at a DESTROYED root, so the next App() died with
    # TclError: image "pyimageNNN" doesn't exist.
    root1 = _root()
    if root1 is None:
        return
    try:
        b1 = rounded_button(root1, text="One", bg="#A85F33", fg="white")
        b1.pack(); root1.update()
    finally:
        root1.destroy()
    root2 = _root()
    assert root2 is not None
    try:
        b2 = rounded_button(root2, text="Two", bg="#A85F33", fg="white")
        b2.pack(); root2.update()
        b2.invoke()
        assert b2.cget("image")
    finally:
        root2.destroy()

def test_rounded_frame_both_themes():
    root = _root()
    if root is None:
        return
    try:
        for toks in (LIGHT, DARK):
            f = RoundedFrame(root, bg=toks["panel"], border=toks["border"])
            f.pack(fill="both", expand=True)
            tk.Label(f.inner, text="hi", bg=toks["panel"]).pack()
            root.update()
            assert f.inner.winfo_exists() and f.winfo_height() > 10
            f.destroy()
    finally:
        root.destroy()

def test_wrapped_tree_rows_selected_and_empty():
    root = _root()
    if root is None:
        return
    try:
        wrap = RoundedFrame(root, bg=LIGHT["panel"], border=LIGHT["border"])
        wrap.pack(fill="both", expand=True)
        tree = ttk.Treeview(wrap.inner, columns=("a", "b"), show="headings")
        tree.heading("a", text="A"); tree.heading("b", text="B")
        tree.pack(fill="both", expand=True)
        for i in range(30):
            tree.insert("", "end", values=(i, f"row {i}"))
        root.update()
        assert len(tree.get_children()) == 30
        tree.selection_set(tree.get_children()[0])
        assert tree.selection()
        tree.yview_moveto(0.5); root.update()  # stays scrollable
        assert tree.winfo_height() > 10
        empty = ttk.Treeview(wrap.inner, columns=("a",), show="headings")
        empty.pack(fill="x")
        root.update()
        assert len(empty.get_children()) == 0
    finally:
        root.destroy()

def test_appointments_tab_uses_rounded_widgets():
    root = _root()
    if root is None:
        return
    try:
        from src.ui.appointments import AppointmentsTab
        stub = type("Stub", (), {"lang": "en", "current_patient": None})()
        tab = AppointmentsTab(root, stub)
        tab.pack(fill="both", expand=True); root.update()
        assert isinstance(tab.tree.master.master, RoundedFrame)
        assert any(isinstance(w, RoundedButton) for w in _walk(tab))
    finally:
        root.destroy()

def test_about_tab_whatsapp_button_rounded():
    root = _root()
    if root is None:
        return
    try:
        from src.ui.about_tab import AboutTab
        stub = type("Stub", (), {"lang": "en"})()
        tab = AboutTab(root, stub)
        tab.pack(fill="both", expand=True); root.update()
        btns = [w for w in _walk(tab) if isinstance(w, RoundedButton)]
        assert btns and "963944234456" in btns[0].cget("text")
    finally:
        root.destroy()
