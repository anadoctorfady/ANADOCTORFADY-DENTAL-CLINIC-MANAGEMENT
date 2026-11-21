"""Round 23 (item 1): language-direction order of the four
clinical input tables and of the History clinical columns.

EN: complaint -> symptoms -> diagnosis -> procedure reads
LEFT to RIGHT (grid columns 0..3, History columns in that
order). AR: the same reading order runs from the RIGHT --
complaint is rightmost (grid column 3), procedure leftmost
(column 0); the History tree's clinical columns are reversed
the same way, date/tooth stay first and Total/Paid/Remaining
stay after the clinical columns. The Diagnosis/Procedures
notebook tabs follow the same order. GUI tests skip with no
display."""
import tkinter as tk

from src.models.database import set_setting
from src.ui.clinical import ClinicalTab
from src.ui.clinical_history import history_columns
from src.ui.clinical_table_style import ORDER
from tests.test_clinical_save_gate import _stub_app

KINDS = ("complaint", "symptom", "diagnosis", "procedure")


def _build(lang):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.geometry("1380x1000")
    set_setting("language", lang)
    tab = ClinicalTab(root, _stub_app(None, lang=lang))
    tab.pack(fill="both", expand=True)
    root.update_idletasks(); root.update()
    return root, tab


def _grid_col(tab, kind):
    return int(tab.table_frames[kind].grid_info()["column"])


def test_input_table_order_english():
    root, tab = _build("en")
    if tab is None:
        print("SKIP r23 input order EN (no display)"); return
    try:
        assert tab.table_order == ORDER
        assert [_grid_col(tab, k) for k in KINDS] == [0, 1, 2, 3]
        xs = [tab.table_frames[k].winfo_rootx() for k in KINDS]
        assert xs == sorted(xs) and len(set(xs)) == 4, xs
    finally:
        root.destroy()


def test_input_table_order_arabic():
    root, tab = _build("ar")
    if tab is None:
        print("SKIP r23 input order AR (no display)"); return
    try:
        # Left-to-right on screen: procedure, diagnosis, symptom,
        # complaint -- complaint RIGHTMOST (reads first in AR).
        assert tab.table_order == tuple(reversed(ORDER))
        assert [_grid_col(tab, k) for k in KINDS] == [3, 2, 1, 0]
        xs = {k: tab.table_frames[k].winfo_rootx() for k in KINDS}
        assert xs["complaint"] > xs["symptom"] > xs["diagnosis"] \
            > xs["procedure"], xs
    finally:
        root.destroy()
        set_setting("language", "en")


def test_history_column_order_pure():
    """No display needed: the column-order contract itself."""
    en = history_columns("en")
    assert en == ("date", "tooth", "complaint", "symptom",
                  "diagnosis", "procedure", "total", "paid", "remain"), en
    ar = history_columns("ar")
    assert ar == ("date", "tooth", "procedure", "diagnosis",
                  "symptom", "complaint", "total", "paid", "remain"), ar
    for cols in (en, ar):
        assert cols[:2] == ("date", "tooth")  # fixed position
        assert cols[-3:] == ("total", "paid", "remain")  # money last


def test_history_column_order_gui_both_languages():
    for lang, clinical in (("en", KINDS),
                           ("ar", tuple(reversed(KINDS)))):
        root, tab = _build(lang)
        if tab is None:
            print(f"SKIP r23 history order GUI {lang} (no display)")
            return
        try:
            cols = tuple(tab.tree_history["columns"])
            assert cols == history_columns(lang), (lang, cols)
            assert cols[2:6] == clinical, (lang, cols)
            assert tab.history_columns == cols
            # Headings are the language's own labels, per column.
            assert tab.tree_history.heading("complaint", "text") == \
                ("Complaint" if lang == "en" else "الشكوى")
            assert tab.tree_history.heading("procedure", "text") == \
                ("Proc" if lang == "en" else "الإجراء")
            # ROUND-24 SUPERSESSION (items 2+6): the Diagnosis /
            # Procedures sub-trees + their notebook are REMOVED --
            # the unified tree above is the only record list, and
            # its clinical columns already assert the order.
            assert not hasattr(tab, "tree_diag")
            assert not hasattr(tab, "tree_proc")
            assert not hasattr(tab, "history_top_nb")
        finally:
            root.destroy()
    set_setting("language", "en")
