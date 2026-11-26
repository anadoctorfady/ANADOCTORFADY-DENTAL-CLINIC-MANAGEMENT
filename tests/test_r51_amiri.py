"""Round 51 Section C: Amiri font pins.

Bundling: the TTFs are genuine TrueType files of a reasonable
size and the SIL OFL license ships verbatim beside them.
Behaviour: with the app language Arabic (and Amiri available),
the UI font family becomes Amiri -- widget fonts, the patient
list row tags and the ttk styles (with a Treeview row height
that fits Amiri's taller line); toggling back to English
restores the default styles and Segoe-built widgets. When Amiri
is unavailable the apply step is a graceful no-op. PDFs are out
of scope (they keep their embedded Noto font).
"""
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from unittest import mock

from src.ui import amiri

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def test_bundled_files_are_genuine_ttfs():
    for name, minimum in (("Amiri-Regular.ttf", 300_000),
                          ("Amiri-Bold.ttf", 300_000)):
        data = (FONTS / name).read_bytes()
        assert len(data) >= minimum, (name, len(data))
        assert data[:4] in (b"\x00\x01\x00\x00", b"true"), name
    lic = (FONTS / "OFL.txt").read_text(encoding="utf-8")
    assert "SIL Open Font License" in lic
    assert "Amiri Project Authors" in lic


def test_registration_fallback_never_crashes():
    # Non-Windows dev runs have no private-registration API; the
    # probe must simply answer (True only if the system has it).
    assert amiri._register_private() in (True, False)


def _families_in_tree(widget, acc):
    try:
        spec = widget.cget("font")
    except Exception:
        spec = None
    if spec:
        try:
            acc.add(tkfont.Font(font=spec).actual().get("family"))
        except Exception:
            pass
    for ch in widget.winfo_children():
        _families_in_tree(ch, acc)
    return acc


def test_arabic_ui_uses_amiri_and_english_restores():
    try:
        probe = tk.Tk(); probe.destroy()
    except Exception:
        print("SKIP test_r51_amiri GUI (no display)"); return
    from src.ui.shell import App
    import src.ui.shell as shell_mod
    app = App()
    try:
        if not amiri.amiri_available(app):
            print("SKIP amiri swap assertions (font unavailable)")
            return
        with mock.patch.object(shell_mod.messagebox, "showinfo"):
            app._toggle_lang()  # -> Arabic: rebuild + apply
            app.update()
            fams = _families_in_tree(app, set())
            assert "Amiri" in fams, fams
            assert "Segoe UI" not in fams, fams
            from tkinter import ttk
            style = ttk.Style(app)
            assert tkfont.Font(font=style.lookup(
                "TNotebook.Tab", "font")).actual()["family"] == "Amiri"
            ls = tkfont.Font(family="Amiri", size=9).metrics("linespace")
            assert int(style.lookup("Treeview", "rowheight")) >= ls + 8
            # Patient list row tags carry Amiri too.
            tag_font = app.tree.tag_configure("name_0", "font")
            assert tkfont.Font(font=tag_font).actual()["family"] == "Amiri"
            app._toggle_lang()  # -> English: styles restored
            app.update()
            assert tkfont.Font(font=style.lookup(
                "TNotebook.Tab", "font")).actual()["family"] != "Amiri"
            fams = _families_in_tree(app, set())
            assert "Amiri" not in fams, fams
    finally:
        app.destroy()


def run():
    test_bundled_files_are_genuine_ttfs()
    test_registration_fallback_never_crashes()
    test_arabic_ui_uses_amiri_and_english_restores()
    print("PASS test_r51_amiri")
