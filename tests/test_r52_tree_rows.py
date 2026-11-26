"""Round 52, Section B: every ttk tree style must fit the Arabic
font -- the R51 Amiri raise touched only the base "Treeview"
style, while theme.tree_style(), vivid_rows.ensure_vivid_style()
and paper_bg.apply_treeview_paper() pinned rowheight=24 (and the
Segoe UI font) on their named styles, so Arabic rows clipped in
the patient list, the vivid clinical tables and any tab tree
whose style call re-ran. All configurers now take the row height
and font from amiri.tree_rowheight()/tree_font(); this test pins
that for both languages. R56: Amiri was REVERTED -- the styles
are Segoe UI in both languages, and the Arabic rowheight is the
MEASURED Arabic linespace + 8 (amiri.arabic_linespace), never a
literal 24.
"""
import tkinter as tk
from tkinter import ttk

from tests.test_r16_print import isolated_db


def _setup(root, lang):
    from src.models.database import set_setting
    set_setting("language", lang)
    from src.config import theme as theme_mod
    theme_mod.set_mode("light") if hasattr(theme_mod, "set_mode") \
        else None
    from src.config.theme import tree_style
    from src.ui.vivid_rows import ensure_vivid_style
    from src.ui.paper_bg import apply_treeview_paper
    from src.config.theme import current
    tree_style("Probe")
    ensure_vivid_style()
    style = ttk.Style(root)
    apply_treeview_paper(style, current())
    return style


def test_arabic_styles_fit_measured_arabic_line():
    """R56: Segoe UI everywhere, and every style's rowheight is
    the measured Arabic linespace + 8 (no literal 24, no Amiri)."""
    from src.ui import amiri
    root = tk.Tk(); root.withdraw()
    try:
        with isolated_db():
            style = _setup(root, "ar")
            need = amiri.arabic_linespace(9, root)
            for name in ("Treeview", "Paper.Treeview",
                         "Vivid.Treeview", "Probe.Treeview"):
                rh = int(style.lookup(name, "rowheight") or 0)
                assert rh >= need, (name, rh, need)
                assert rh == amiri.tree_rowheight(), (name, rh)
                assert rh == max(24, need + 8), (name, rh, need)
                fam = str(style.lookup(name, "font"))
                # Spec string, not a Font object: Tk resolves the
                # family at construction, so cget/actual report
                # the Linux substitute "Noto Sans" for "Segoe UI".
                assert "Segoe UI" in fam, (name, fam)
            from src.models.database import set_setting
            set_setting("language", "en")
    finally:
        root.destroy()


def test_english_styles_unchanged():
    root = tk.Tk(); root.withdraw()
    try:
        with isolated_db():
            style = _setup(root, "en")
            for name in ("Treeview", "Paper.Treeview",
                         "Vivid.Treeview", "Probe.Treeview"):
                rh = int(style.lookup(name, "rowheight") or 0)
                assert rh == 24, (name, rh)
    finally:
        root.destroy()


def run():
    test_arabic_styles_fit_measured_arabic_line()
    test_english_styles_unchanged()


if __name__ == "__main__":
    run()
    print("test_r52_tree_rows OK")
