"""Round 21 items 3 + 6 + 9: dark-mode tables take the cost
boxes' treatment, zebra striping on the multi-row tables, and
clearly visible entry borders.

Item 3: the clinical finance section in dark mode uses the Total
cost box's dark background (#92400E) with the boxes' light label
colours; light mode unchanged (TABLE tint).
Item 6: zebra tag pairs configured from theme.zebra_colors and
applied (zebra tag FIRST, so meaning tags keep precedence) on the
patient list, clinical history/finance trees, appointments and
the finance expenses tree.
Item 9: _RoundedBorder defaults to the FIELD_BORDER token at
2px (3px accent on focus); token contrast vs the panel >= 3:1.
"""
import tkinter as tk
from tkinter import ttk

from tests.test_templates_edit import isolated_db
from src.config import theme
from src.config.theme import (current, is_dark, zebra_colors,
                              field_border)
from src.ui.clinical_table_style import contrast_ratio
from src.ui.zebra import zebra_tree


def _root():
    r = tk.Tk(); r.withdraw(); return r


def test_zebra_and_border_tokens_contrast():
    for dark in (False, True):
        even, odd = zebra_colors(dark)
        assert even != odd
        fg = "#F5F0EB" if dark else "#2C241D"
        for bg in (even, odd):
            assert contrast_ratio(fg, bg) >= 4.5, (dark, bg)
        panel = theme.DARK["panel"] if dark else theme.LIGHT["panel"]
        assert contrast_ratio(field_border(dark), panel) >= 3.0
    # Dark zebra lives in the cost-box family: warm (R>G>B) and
    # darker than the Total box colour itself (large-area tone).
    from src.ui.clinical_table_style import luminance
    for bg in zebra_colors(True):
        r, g, b = (int(bg[i:i + 2], 16) for i in (1, 3, 5))
        assert r > g > b, bg
        assert luminance(bg) < luminance("#92400E")


def test_zebra_tree_tagging():
    with isolated_db():
        root = _root()
        try:
            tr = ttk.Treeview(root, columns=("a",))
            for i in range(4):
                tr.insert("", "end", values=(i,))
            zebra_tree(tr)
            kids = tr.get_children("")
            tags = [tr.item(k, "tags") for k in kids]
            assert tags[0][0] == "zebra0" and tags[1][0] == "zebra1"
            assert tags[2][0] == "zebra0" and tags[3][0] == "zebra1"
            even, odd = zebra_colors(is_dark())
            got0 = str(tr.tag_configure("zebra0", "background")).lower()
            got1 = str(tr.tag_configure("zebra1", "background")).lower()
            assert got0 == even.lower() and got1 == odd.lower()
            # Meaning tags keep precedence: zebra goes FIRST.
            tr.item(kids[0], tags=("zebra0", "debt"))
            zebra_tree(tr)
            assert tr.item(kids[0], "tags") == ("zebra0", "debt")
        finally:
            root.destroy()


def test_dark_finance_section_matches_cost_box():
    from src.models.database import set_setting
    from src.ui.clinical_currency import _box  # R40: BOXES moved here
    from tests.test_clinical_save_gate import _stub_app
    from src.ui.clinical import ClinicalTab
    with isolated_db():
        set_setting("theme_mode", "dark")
        root = _root()
        try:
            tab = ClinicalTab(root, _stub_app())
            root.update_idletasks()
            box_bg, box_fg = _box("total")
            assert box_bg == "#92400E"
            # R40: no finance section anymore — the balance band
            # inside the money strip carries the treatment.
            assert tab._cur_break_frame.cget("bg") == box_bg
            # R38: the Remaining label is gone; the balance line
            # (lbl_pat_totals, zero state) carries the section
            # bg + light fg in its place.
            assert tab.lbl_pat_totals.cget("bg") == box_bg
            assert tab.lbl_pat_totals.cget("fg") == box_fg
            assert contrast_ratio(box_fg, box_bg) >= 4.5
        finally:
            root.destroy()
            set_setting("theme_mode", "light")


def test_light_finance_section_unchanged():
    from src.models.database import set_setting
    from src.config.theme import TABLE
    from tests.test_clinical_save_gate import _stub_app
    from src.ui.clinical import ClinicalTab
    with isolated_db():
        set_setting("theme_mode", "light")
        root = _root()
        try:
            tab = ClinicalTab(root, _stub_app())
            # R40: the balance band (was: the finance section frame).
            assert tab._cur_break_frame.cget("bg") == TABLE["finance"]
        finally:
            root.destroy()


def test_field_border_on_widgets():
    from src.models.database import set_setting
    from src.ui.rounded_widgets import RoundedEntry
    from src.ui.rounded_lists import RoundedText
    with isolated_db():
        for mode_name in ("light", "dark"):
            set_setting("theme_mode", mode_name)
            root = _root()
            try:
                e = RoundedEntry(root, width=10)
                e.pack(); root.deiconify(); root.geometry("300x120")
                root.update()
                assert e._border == field_border(mode_name == "dark")
                assert e._border != current()["border"]
                txt = RoundedText(root, width=20, height=3)
                assert txt._border == e._border
                # Focus drawing path runs and re-renders.
                e._draw(e._focus_border)
                assert e._size[2] == e._focus_border
                e._draw(None)
                assert e._size[2] is None
            finally:
                root.destroy()
        set_setting("theme_mode", "light")


def test_zebra_applied_in_app():
    """End-to-end on the real App: patient list, clinical trees,
    appointments and finance expenses all carry zebra tags."""
    from tests.test_r18_info_panel_visible import _login
    from src.ui.shell import App
    from src.models.database import get_connection, save_financial
    from src.models.finance import add_expense
    with isolated_db():
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO patients(first_name,father_name,"
                    "grand_name,last_name,full_name,birth_date_greg,"
                    "mobile1) VALUES('Ahmed','Mohammed','Ali','Hassan',"
                    "'Ahmed Mohammed Ali Hassan','1990-05-15','0944')")
        cur.execute("INSERT INTO diagnoses(patient_file,visit_date,"
                    "tooth_number,diagnosis) VALUES(1,'2026-11-01',"
                    "'16','Caries')")
        cur.execute("INSERT INTO appointments(patient_file,"
                    "appointment_date,appointment_time,reason,status)"
                    " VALUES(1,'2026-11-20','10:00','Check','قادم')")
        conn.commit(); conn.close()
        save_financial(1, "", 1000, 400, "2026-11-01", "SYP", None,
                       "2026-11-01", "SYP", doctor="fady",
                       entered_by="fady")
        add_expense("2026-11-02", "Supplies", "Gauze", 500)
        app = App()
        try:
            _login(app)
            app.deiconify(); app.geometry("1380x1000"); app.update()
            app.search_var.set("Ahmed"); app.load_patients(); app.update()
            kids = app.tree.get_children("")
            assert kids, "patient rows expected"
            for i, k in enumerate(kids):
                assert app.tree.item(k, "tags")[0] == f"zebra{i % 2}"
            app.select_patient(1); app.update()
            ct = app.clinical
            # R24: tree_diag is gone; the unified tree carries it.
            # R40: the two money lists wear VIVID rotation, not zebra.
            for tree in (ct.tree_fin, ct.tree_history):
                rows = tree.get_children("")
                assert rows, "clinical rows expected"
                for i, k in enumerate(rows):
                    assert tree.item(k, "tags")[0] == f"vivid{i % 5}"
            app.notebook.select(app.appt); app.update()
            rows = app.appt.tree.get_children("")
            assert rows, "appointment rows expected"
            for i, k in enumerate(rows):
                assert app.appt.tree.item(k, "tags")[0] == f"zebra{i % 2}"
            assert app.fin.gate.try_unlock("fady", "1234")
            app.fin.load(); app.update()
            rows = app.fin.tree_exp.get_children("")
            assert rows, "expense rows expected"
            for i, k in enumerate(rows):
                assert app.fin.tree_exp.item(k, "tags")[0] == f"zebra{i % 2}"
        finally:
            app.destroy()
