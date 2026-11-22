"""Round 41 — owner feedback on the round-40 build (2026-11-22).

Item 3: chart jaw-selection buttons (all / upper / lower) for
the permanent AND deciduous charts, feeding a multi-tooth
session save through the chart's own selection model.
Item 4 (REGRESSION, owner's unreadable-rows report): a session
whose procedure text contains line breaks (typed in the real
Text widget) must show in the History table as ONE readable
line (' | '-joined, full text), vivid tag on the row, and a
click/selection must not blank it. The STORED text keeps its
line breaks — the fix is display-only (clinical_history.
flat_cell), so Edit still reloads the text as written.
Item 5 (owner report: a pure advance was missing from the
Payments review): driven through the REAL single entry form —
the standalone row appears in the review with the correct
running balance. NOTE: the reported defect did NOT reproduce
in the round-41 reproduction matrix (full app, EN + AR, fresh
patient and patient with history, incl. a back-dated advance);
this test pins the correct behaviour. See REVIEW.md round 41.
Item 7: the review's Currency column is LAST.
"""
import tkinter as tk

from src.models.database import get_connection
from src.models.finance import patient_totals
from src.ui.dental_chart import DentalChartFrame
from src.utils.helpers import PERMANENT, DECIDUOUS
from tests.test_payments_e2e import (TODAY, _seed_users, _seed_patient,
                                     _rows, _cleanup, _patch_msgs,
                                     _build_clinical)

UPPER_P = set(PERMANENT[:16]); LOWER_P = set(PERMANENT[16:])
UPPER_D = set(DECIDUOUS[:10]); LOWER_D = set(DECIDUOUS[10:])
PROC_MULTI = ("Root canal treatment started\n"
              "Access cavity opened, canals located\n"
              "Working length determined, irrigation done")
PROC_FLAT = ("Root canal treatment started | "
             "Access cavity opened, canals located | "
             "Working length determined, irrigation done")


def _chart(lang="en"):
    root = tk.Tk(); root.withdraw()
    got = []
    chart = DentalChartFrame(root, lang=lang,
                             on_select=lambda s, ty: got.append((s, ty)))
    root.update_idletasks()
    return root, chart, got


def test_chart_jaw_buttons_both_charts():
    root, chart, got = _chart()
    try:
        assert set(chart.jaw_buttons) == {"all", "upper", "lower"}
        assert chart.jaw_buttons["all"].cget("text") == "Select all teeth"
        chart.jaw_buttons["upper"].invoke()
        assert chart.selected == UPPER_P and len(got[-1][0]) == 16
        chart.jaw_buttons["lower"].invoke()
        assert chart.selected == LOWER_P
        chart.jaw_buttons["all"].invoke()
        assert chart.selected == UPPER_P | LOWER_P
        chart.tooth_type.set("لبني"); chart.refresh()
        chart.jaw_buttons["upper"].invoke()
        assert chart.selected == UPPER_D
        chart.jaw_buttons["lower"].invoke()
        assert chart.selected == LOWER_D
        chart.jaw_buttons["all"].invoke()
        assert chart.selected == UPPER_D | LOWER_D
    finally:
        root.destroy()
    root, chart, _got = _chart(lang="ar")
    try:  # language purity: Arabic labels in the Arabic chart
        assert chart.jaw_buttons["all"].cget("text") == "اختيار كل الأسنان"
        assert chart.jaw_buttons["upper"].cget("text") == "الفك العلوي فقط"
        assert chart.jaw_buttons["lower"].cget("text") == "الفك السفلي فقط"
    finally:
        root.destroy()


def _fill_texts(tab, proc="Filling"):
    for w, txt in ((tab.txt_complaint, "Pain"), (tab.txt_sym, "Sharp"),
                   (tab.txt_diagnosis, "Caries"),
                   (tab.txt_procedure, proc)):
        w.delete("1.0", tk.END); w.insert("1.0", txt)


def test_jaw_selection_feeds_session_save():
    _seed_users(); fid = _seed_patient("R41 JawSave")
    try:
        caps, restore = _patch_msgs()
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None:
            restore(); return
        try:
            # The shell's real wiring (shell.py: chart_teeth reads
            # the clinical tab's chart selection).
            tab.app.chart_teeth = lambda: tab.chart.get_selection()[0]
            tab.chart.jaw_buttons["upper"].invoke(); root.update_idletasks()
            _fill_texts(tab)
            from src.ui import clinical_session_entry as _entry
            _entry.set_money(tab, 100, 40)
            tab.btn_save_visit.invoke(); root.update_idletasks()
            assert not caps["error"], caps
            conn = get_connection()
            row = conn.execute("SELECT tooth_number FROM diagnoses "
                               "WHERE patient_file=?", (fid,)).fetchone()
            conn.close()
            assert row and set(row[0].split(",")) == UPPER_P, row
            assert patient_totals(fid)["paid"] == 40.0
        finally:
            root.destroy(); restore()
    finally:
        _cleanup(fid)


def test_history_row_multiline_text_readable():
    _seed_users(); fid = _seed_patient("R41 MultiLine")
    try:
        caps, restore = _patch_msgs()
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None:
            restore(); return
        try:
            tab.app.chart_teeth = lambda: []
            tab.e_sess_tooth.delete(0, tk.END)
            tab.e_sess_tooth.insert(0, "16,36")
            _fill_texts(tab, proc=PROC_MULTI)
            from src.ui import clinical_session_entry as _entry
            _entry.set_money(tab, 1000, 400)
            tab.btn_save_visit.invoke(); root.update_idletasks()
            assert not caps["error"], caps
            tree = tab.tree_history
            kids = tree.get_children("")
            assert len(kids) == 1
            vals = tree.item(kids[0], "values")
            assert all("\n" not in str(v) and "\r" not in str(v)
                       for v in vals), vals
            cols = list(tab.history_columns)
            assert vals[cols.index("procedure")] == PROC_FLAT, vals
            assert vals[cols.index("tooth")] == "16,36"
            assert tree.item(kids[0], "tags")[0].startswith("vivid")
            # A click / selection must not blank the writing.
            tree.selection_set(kids[0]); root.update_idletasks()
            assert tree.selection() == (kids[0],)
            assert tree.item(kids[0], "values") == vals
            # Stored data keeps the line breaks (display-only fix).
            conn = get_connection()
            raw = conn.execute("SELECT procedure_done FROM procedures "
                               "WHERE patient_file=?", (fid,)).fetchone()[0]
            conn.close()
            assert raw.strip() == PROC_MULTI, repr(raw)
        finally:
            root.destroy(); restore()
    finally:
        conn = get_connection()
        for tbl in ("diagnoses", "procedures", "complaints"):
            conn.execute(f"DELETE FROM {tbl} WHERE patient_file=?", (fid,))
        conn.commit(); conn.close()
        _cleanup(fid)


def test_pure_advance_appears_in_review_currency_last():
    _seed_users(); fid = _seed_patient("R41 Advance")
    try:
        caps, restore = _patch_msgs()
        root, tab = _build_clinical("doc_x", "doctor", fid)
        if tab is None:
            restore(); return
        try:
            from src.ui import clinical_session_entry as _entry
            from src.ui.clinical_payments_review import FIN_COLS
            tab.app.chart_teeth = lambda: []
            tab.e_sess_tooth.delete(0, tk.END)
            _entry.set_money(tab, 0, 500)
            tab.btn_save_visit.invoke(); root.update_idletasks()
            assert not caps["error"], caps
            assert patient_totals(fid)["remaining"] == -500.0
            assert tuple(tab.tree_fin["columns"]) == FIN_COLS
            assert FIN_COLS[-1] == "currency", FIN_COLS
            kids = tab.tree_fin.get_children("")
            assert len(kids) == 1, [tab.tree_fin.item(k, "values")
                                    for k in kids]
            vals = tab.tree_fin.item(kids[0], "values")
            assert vals[0] == TODAY and vals[1] == "500", vals
            assert vals[4] == "-500.00", vals  # Balance after
            assert vals[6] == "SYP", vals     # Currency, LAST column
            assert tab._hist_rows["tree_fin"][kids[0]]["row_kind"] == "payment"
        finally:
            root.destroy(); restore()
    finally:
        _cleanup(fid)
