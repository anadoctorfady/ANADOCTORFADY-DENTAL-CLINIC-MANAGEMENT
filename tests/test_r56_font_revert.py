"""Round 56 Section A: Amiri REVERTED (owner's decision, 2026-11-25).

The Arabic UI is back to the pre-round-51 font: Segoe UI in BOTH
languages; Arabic glyphs render through the system's normal
fallback. Pins:
- Amiri registration is disabled: _register_private() is False
  and amiri_available() is False on every machine -- even on
  this dev box, where Amiri IS installed system-wide, so the
  revert is unconditional and the dev box renders what his
  Windows machine renders.
- The bundled Amiri TTFs + OFL.txt are GONE from assets/fonts/
  (only the Noto PDF fonts remain).
- With the app in Arabic, no widget font, no ttk style font and
  no patient-list row tag is Amiri; everything is Segoe UI.
- The guard: in Arabic mode every tree style's rowheight is the
  MEASURED Arabic linespace + 8 (amiri.tree_rowheight()), never a
  literal 24; in English it stays 24. The rendered Arabic sample
  fits inside the row with margin (its canvas bbox height is at
  most rowheight - 4).
- Toggling AR -> EN leaves Segoe UI everywhere (no stale Amiri
  styles, no stale rowheight). PDFs keep Noto (pinned elsewhere).
"""
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import ttk
from unittest import mock

from src.ui import amiri

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def test_registration_disabled_even_when_amiri_installed():
    try:
        probe = tk.Tk(); probe.destroy()
    except Exception:
        print("SKIP (no display)")
        return
    assert amiri._register_private() is False
    root = tk.Tk(); root.withdraw()
    try:
        # The dev box HAS Amiri system-wide -- the revert must
        # still answer False (unconditional, not availability-based).
        assert "Amiri" in tkfont.families(root), "Amiri not installed here"
        assert amiri.amiri_available(root) is False
    finally:
        root.destroy()


def test_amiri_files_removed_noto_stays():
    assert not (FONTS / "Amiri-Regular.ttf").exists()
    assert not (FONTS / "Amiri-Bold.ttf").exists()
    assert not (FONTS / "OFL.txt").exists()
    for name in ("NotoNaskhArabic-Regular.ttf",
                 "NotoNaskhArabic-Bold.ttf"):
        assert (FONTS / name).exists(), name


def _families_in_tree(widget, acc):
    # Pin the REQUESTED family from the font SPEC STRING itself.
    # A Font object is useless here: Tk resolves the family at
    # construction, so both cget("family") and actual() report the
    # Linux substitute ("Noto Sans") for the requested "Segoe UI".
    # The spec string (e.g. '{Segoe UI} 9') is what the app asked
    # for -- that is the contract; what the OS substitutes when
    # rendering is the platform's business.
    try:
        spec = widget.cget("font")
    except Exception:
        spec = None
    if spec:
        acc.add(str(spec))
    for ch in widget.winfo_children():
        _families_in_tree(ch, acc)
    return acc


def test_arabic_ui_is_segoe_everywhere():
    try:
        probe = tk.Tk(); probe.destroy()
    except Exception:
        print("SKIP test_r56_font_revert GUI (no display)")
        return
    from src.ui.shell import App
    import src.ui.shell as shell_mod
    app = App()
    try:
        with mock.patch.object(shell_mod.messagebox, "showinfo"):
            if app.lang != "ar":
                app._toggle_lang()  # -> Arabic: rebuild
            app.update()
            assert app.lang == "ar"
            fams = _families_in_tree(app, set())
            assert not any("Amiri" in s for s in fams), fams
            style = ttk.Style(app)
            # The spec string, not a Font object: '{Segoe UI} 9'
            # is the requested family (see _families_in_tree).
            fam = str(style.lookup("Treeview", "font"))
            assert "Segoe UI" in fam, fam
            # Guard: rowheight = measured Arabic linespace + 8.
            need = amiri.arabic_linespace(9, app)
            rh = int(style.lookup("Treeview", "rowheight"))
            assert rh == max(24, need + 8), (rh, need)
            assert rh == amiri.tree_rowheight(), (rh, need)
            tag_font = app.tree.tag_configure("name_0", "font")
            assert "Segoe UI" in str(tag_font), tag_font
            # The rendered Arabic sample fits inside the row.
            cv = tk.Canvas(app, width=16, height=16)
            item = cv.create_text(0, 0, text="العربية 123",
                                  font=("Segoe UI", 9), anchor="nw")
            bb = cv.bbox(item)
            cv.destroy()
            assert bb and bb[3] - bb[1] <= rh - 4, (bb, rh)
            app._toggle_lang()  # -> English
            app.update()
            assert app.lang == "en"
            fams = _families_in_tree(app, set())
            assert not any("Amiri" in s for s in fams), fams
            assert int(style.lookup("Treeview", "rowheight")) == 24
    finally:
        app.destroy()


def test_english_rowheight_stays_24():
    from tests.test_r16_print import isolated_db
    from src.models.database import set_setting
    try:
        root = tk.Tk(); root.withdraw()
    except Exception:
        print("SKIP (no display)")
        return
    try:
        with isolated_db():
            set_setting("language", "en")
            assert amiri.tree_rowheight() == 24
            assert amiri.tree_font() == ("Segoe UI", 9)
    finally:
        root.destroy()


def run():
    test_registration_disabled_even_when_amiri_installed()
    test_amiri_files_removed_noto_stays()
    test_arabic_ui_is_segoe_everywhere()
    test_english_rowheight_stays_24()
    print("PASS test_r56_font_revert")
