"""Round 18 items 5 + 6 + 1 (UI), superseded by rounds 19/21/22
and ROUND 24 (items 2+6). Notes row + Save live in the input block
under the one-row input tables (no tab.sticky_bar). R22: the chart
is FIRST in the scroll flow with a PINNED patient header above the
canvas, so visibility checks scroll to the input block first.
ROUND 24: the input block gains the session money row (date/
tooth/Total/Paid/Remaining) between the notes row and the Save
row ("Save session"); right_inner order: chart -> input block ->
unified history -> finance -> Add-image -> notebook -> referrals;
panels section + diagnosis/procedures sub-tabs REMOVED. R21: no
notes_holder / notes_section. The notes field keeps its Templates
button and the four legacy note aliases (= txt_visit_note). A
visit still saves via the Save button; history loads with or
without a patient. GUI tests skip with no display."""
import tkinter as tk
from unittest import mock

from src.config.strings_r18_clinical import r18_t
from src.models.database import set_setting
from src.ui import clinical_tables
from src.ui.clinical import ClinicalTab
from tests.test_clinical_save_gate import (
    _cleanup, _count, _fill, _seed_patient, _stub_app)

NOTE_ALIASES = ("txt_complaint_note", "txt_sym_note", "txt_diagnosis_note", "txt_procedure_note")

def _build(fid=None, lang="en"):
    """Real ClinicalTab in a shown 1380x1000 root, or (None, None)."""
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.geometry("1380x1000")
    set_setting("language", lang)
    app = _stub_app({"file_number": fid} if fid else None, lang=lang)
    try:
        tab = ClinicalTab(root, app)
        tab.pack(fill="both", expand=True)
        root.update_idletasks(); root.update()
        return root, tab
    except Exception:
        root.destroy()
        raise

def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)

def _check_input_block_visible(root, tab, lang):
    # Round-18 sticky bar superseded (round 19 item 3); round 22
    # supersedes "input block FIRST at yview 0": scroll to it first.
    assert not hasattr(tab, "sticky_bar")
    assert tab.input_block.master is tab.right_inner
    canvas = tab.right_inner.master
    assert isinstance(canvas, tk.Canvas)
    frac = tab.input_block.winfo_y() / max(1, tab.right_inner.winfo_height())
    canvas.yview_moveto(frac)
    root.update()
    slaves = tab.input_block.pack_slaves()
    # R24: the session money row sits between notes and Save.
    assert slaves == [tab.sections_grid, tab.visit_note_row,
                      tab.sess_money_row, tab.save_row], slaves
    assert tab.visit_note_row.master is tab.input_block
    assert tab.save_row.master is tab.input_block
    for w in (tab.btn_save_visit, tab.txt_visit_note):
        assert w.winfo_viewable(), (lang, w)
        assert w.winfo_height() >= w.winfo_reqheight(), (
            lang, w.winfo_height(), w.winfo_reqheight())
        bottom = w.winfo_rooty() - root.winfo_rooty() + w.winfo_height()
        assert bottom <= root.winfo_height(), (lang, bottom)
    # Save sits DIRECTLY under the notes row, under the tables row.
    assert tab.btn_save_visit.winfo_rooty() > tab.txt_visit_note.winfo_rooty()
    assert tab.txt_visit_note.winfo_rooty() > tab.sections_grid.winfo_rooty()

def test_input_block_visible_en():
    root, tab = _build()
    if tab is None:
        print("SKIP test_input_block_visible_en (no display)")
        return
    try:
        _check_input_block_visible(root, tab, "en")
        assert tab.btn_save_visit.cget("text") == "Save session"
    finally:
        root.destroy()

def test_input_block_visible_ar():
    root, tab = _build(lang="ar")
    if tab is None:
        print("SKIP test_input_block_visible_ar (no display)")
        return
    try:
        _check_input_block_visible(root, tab, "ar")
        assert tab.btn_save_visit.cget("text") == "حفظ الجلسة"
    finally:
        set_setting("language", "en")
        root.destroy()

def test_history_pack_order_and_tabs():
    root, tab = _build()
    if tab is None:
        print("SKIP test_history_pack_order_and_tabs (no display)")
        return
    try:
        inner = tab.right_inner
        slaves = inner.pack_slaves()
        # ROUND-24 SUPERSESSION: no panels section; the unified
        # history section is followed by finance, the notebook and
        # the standalone Rx section at the END.
        assert not hasattr(tab, "panels_section")
        seq = (tab.history_section, tab.fin_section,
               tab.history_nb, tab.rx_section)
        order = [slaves.index(w) for w in seq]
        assert order == sorted(order) and len(set(order)) == len(order), order
        assert not hasattr(tab, "notes_holder")  # R21 item 5: removed
        assert not hasattr(tab, "notes_section")
        # Same story geometrically: increasing tops, fixed scroll.
        tops = [w.winfo_rooty() for w in seq]
        assert tops == sorted(tops) and len(set(tops)) == len(tops), tops
        # Headed section: heading label + the ONE unified tree.
        headings = [w.cget("text") for w in _walk(tab.history_section)
                    if isinstance(w, tk.Label)]
        assert r18_t("r18.clinical.history_heading", "en") in headings
        assert not hasattr(tab, "history_top_nb")
        assert tuple(tab.tree_history["columns"]) == (
            "date", "tooth", "complaint", "symptom", "diagnosis",
            "procedure", "total", "paid", "remain")
        bottom_tabs = [tab.history_nb.tab(i, "text").strip()
                       for i in tab.history_nb.tabs()]
        assert bottom_tabs == ["Payments review", "X-Rays", "Scans"], bottom_tabs  # R38: Financial tab renamed to the payments review
        # The finance-history tree is NOT inside the history section.
        assert tab.tree_fin.master is not tab.tree_history.master
    finally:
        root.destroy()

def test_notes_templates_button_and_aliases():
    root, tab = _build()
    if tab is None:
        print("SKIP test_notes_templates_button_and_aliases (no display)")
        return
    try:
        btn = tab.notes_templates_btn
        assert btn.master is tab.visit_note_row
        assert set(tab.picker_buttons) == {"complaint", "symptom", "diagnosis", "procedure"}
        # Order in the notes row: notes field, then Templates.
        assert tab.txt_visit_note.winfo_rootx() < btn.winfo_rootx()
        # Save visit is in its OWN row directly under the notes row.
        assert tab.btn_save_visit.master is tab.save_row
        assert tab.save_row.master is tab.input_block
        assert tab.btn_save_visit.winfo_rooty() > tab.txt_visit_note.winfo_rooty()
        for attr in NOTE_ALIASES:
            assert getattr(tab, attr) is tab.txt_visit_note, attr
        assert tab.clipboard_fields["visit_note"] is tab.txt_visit_note
        # The button really opens the phrase picker for "note".
        btn.invoke()
        root.update_idletasks()
        tops = [w for w in _walk(root) if isinstance(w, tk.Toplevel)]
        assert tops and "note" in tops[0].title(), [t.title() for t in tops]
        tops[0].destroy()
    finally:
        root.destroy()

def test_visit_saves_and_history_loads_with_and_without_patient():
    fid = _seed_patient()
    root, tab = _build(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_visit_saves_and_history (no display)")
        return
    try:
        _fill(tab)
        tab.txt_visit_note.insert("1.0", "review in one week")
        with mock.patch.object(clinical_tables.messagebox,
                               "showerror") as err:
            tab.btn_save_visit.invoke()
        assert not err.called, f"save failed: {err.call_args}"
        assert _count("complaints", fid) == 1
        assert _count("diagnoses", fid) == 1
        assert _count("procedures", fid) == 1
        tab.load(fid)
        root.update_idletasks()
        # R24: ONE unified row for the saved session + its buttons.
        assert len(tab.tree_history.get_children()) == 1
        assert tab.btn_sess_edit is not None
        # No patient: load(None) clears every tree without error.
        tab.load(None)
        root.update_idletasks()
        for tr in (tab.tree_history, tab.tree_fin):
            assert tr.get_children() == ()
        # R27: the X-Ray tree is now the thumbnail grid; it clears too.
        assert tab.xray_grid.tiles == []
    finally:
        root.destroy()
        _cleanup(fid)
        try:  # drop the visit rows this test saved
            from src.models.database import get_connection
            conn = get_connection(); cur = conn.cursor()
            for tbl in ("complaints", "diagnoses", "procedures"):
                cur.execute(f"DELETE FROM {tbl} WHERE patient_file=?", (fid,))
            conn.commit(); conn.close()
        except Exception:
            pass
