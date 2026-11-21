"""Round 19 (items 3 + 7) + round 20 layout, STANDALONE build,
updated to ROUND 22 (supersedes the rounds 19-21 layout pinned
here before) and ROUND 24 (items 2+6). No left column / mid_paned
/ `left_inner`. A PINNED HEADER (`tab.header_panel`, registered
as `app.info_panel`) is packed in the tab OUTSIDE the scroll
canvas; it carries personal info, Health lines, both alert
strips and Edit/Delete/Refer; the tab has NO alert_strip /
lbl_pat_name / patient_header_frame. ONE scroll canvas;
`mid_paned is None`, `left_col is None`, `right_col is tab`;
pack order: chart, input_block, history_section (the UNIFIED
session table), fin_frame.master, Add-image row, history_nb,
referrals, rx_section (standalone). ROUND 24: the panels section
is REMOVED entirely (no panel_frames / panel_texts -- procedures
content lives in the unified tree's procedure column); the "rx"
summary panel is superseded by the full Rx section (`tree_hist`
rows); `rx_print_row` / `btn_rx_print_*` are REMOVED (the Rx
section has its OWN print row). The chart is FIRST, so tests
scroll to the input block first. Item 7 unchanged."""
import tkinter as tk
from src.config.theme import TABLE, current, is_dark
from src.models.database import get_connection, set_setting
from src.ui.clinical import ClinicalTab
from src.ui.clinical_table_style import distinct_from_bg, stack_color, table_colors
from src.ui.patient_info import PatientInfoPanel
from tests.test_clinical_panels import _cleanup, _seed_patient, _seed_payment, _seed_rx
from tests.test_clinical_save_gate import _stub_app

KINDS = ("complaint", "symptom", "diagnosis", "procedure")

def _build(geo="1380x1000", lang="en", patient=None):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.geometry(geo); set_setting("language", lang)
    try:
        tab = ClinicalTab(root, _stub_app(patient, lang=lang))
        tab.pack(fill="both", expand=True); root.update_idletasks(); root.update()
        return root, tab
    except Exception: root.destroy(); raise

def _chain(w):
    out = []
    while w is not None: out.append(w); w = w.master
    return out

def _scroll_to_input(root, tab):
    """R22: chart is first in the flow; scroll to the input block."""
    canvas = tab.right_inner.master
    frac = tab.input_block.winfo_y() / max(1, tab.right_inner.winfo_height()); canvas.yview_moveto(frac); root.update()

def test_frame_colours_distinct_from_bg_both_themes():
    """Item 7, pure data: table/PANELS/stacked colours never use
    the app bg/panel colour; neighbours never share a colour."""
    for dark in (False, True):
        for kind in KINDS:
            assert distinct_from_bg(table_colors(kind, dark)["bg"], dark), (dark, kind)
        assert distinct_from_bg(TABLE["finance"], dark)
        for name in ("history", "referrals", "info"):
            assert distinct_from_bg(stack_color(name, dark), dark), (dark, name)
        # R24: PANELS is empty (panels removed) -- the per-kind
        # table colours above are the panel-colour check now.
        cols = [stack_color(n, dark) for n in ("history", "referrals", "info")]; assert len(set(cols)) == 3, (dark, cols)

def _check_input_visible(root, tab, lang, geo):
    _scroll_to_input(root, tab)
    widgets = [tab.table_frames[k] for k in KINDS] + [tab.txt_visit_note, tab.notes_templates_btn, tab.btn_save_visit]
    for w in widgets:
        assert w.winfo_viewable(), (lang, geo, w)
        assert w.winfo_height() >= w.winfo_reqheight(), (lang, geo, w)
        top = w.winfo_rooty() - root.winfo_rooty()
        assert 0 <= top and top + w.winfo_height() <= root.winfo_height(), (lang, geo, w, top)
    tops = [tab.table_frames[k].winfo_rooty() for k in KINDS]; assert max(tops) - min(tops) < 5, (lang, geo, tops)  # ONE row
    xs = [tab.table_frames[k].winfo_rootx() for k in KINDS]
    # Round 23: EN ascending, AR DESCENDING in KINDS order.
    want = sorted(xs) if lang == "en" else sorted(xs, reverse=True)
    assert xs == want and len(set(xs)) == 4, (lang, geo, xs)
    assert tab.btn_save_visit.winfo_rooty() > tab.sections_grid.winfo_rooty()
    assert not hasattr(tab, "sticky_bar")

def test_input_row_visible_en_ar_both_sizes():
    for geo in ("1380x1000", "1380x820"):
        for lang in ("en", "ar"):
            root, tab = _build(geo, lang)
            if tab is None:
                print(f"SKIP input_row {geo} {lang} (no display)"); return
            try:
                _check_input_visible(root, tab, lang, geo)
                assert tab.btn_save_visit.cget("text") == ("Save session" if lang == "en" else "حفظ الجلسة")
            finally:
                root.destroy()
    set_setting("language", "en")

def test_standalone_structure_header_and_panels():
    """Round 22 structure (supersedes the 19/20/21 left-column
    test): pinned header, panels in right_inner after History."""
    root, tab = _build()
    if tab is None:
        print("SKIP standalone_structure (no display)"); return
    try:
        assert tab.mid_paned is None and tab.left_col is None
        assert tab.right_col is tab and not hasattr(tab, "left_inner")
        slaves = tab.right_inner.pack_slaves()
        assert slaves[0] is tab.chart and slaves[1] is tab.input_block
        # ROUND-24 SUPERSESSION: no panels section at all; the
        # unified history section follows the input block directly.
        assert not hasattr(tab, "panels_section")
        assert not hasattr(tab, "panel_frames")
        assert not hasattr(tab, "panel_texts")
        assert slaves.index(tab.history_section) > slaves.index(tab.input_block)
        assert tab.history_section in _chain(tab.tree_history)
        assert tab.right_inner in _chain(tab.tree_history)
        hdr = tab.header_panel  # pinned: in the tab, NOT the canvas
        assert isinstance(hdr, PatientInfoPanel) and hdr.master is tab
        assert tab.main_canvas not in _chain(hdr) and tab.app.info_panel is hdr
        for btn in (hdr.edit_btn, hdr.delete_btn, hdr.refer_btn):
            assert btn is not None and hdr in _chain(btn)
        for attr in ("left_info_frame", "clin_info_panel", "patient_header_frame",
                     "lbl_pat_name", "lbl_pat_meta", "alert_strip"):
            assert not hasattr(tab, attr), attr  # info lives in the header only
    finally:
        root.destroy()

def _check_rx_buttons(root, tab, lang, geo):
    # Round 22: clinical_left print row REMOVED; Rx section's own row.
    for attr in ("rx_print_row", "btn_rx_print_selected", "btn_rx_print_preview"):
        assert not hasattr(tab, attr), (lang, geo, attr)
    assert tab.rx_section.print_direct_btn.master is tab.rx_section.print_btn_row
    assert tab.rx_section.print_direct_btn in tab.rx_section.print_btn_row.winfo_children()
    # Scroll MAIN canvas to bottom: print buttons inside, below tree.
    tab.main_canvas.yview_moveto(1.0); root.update()
    assert tab.rx_section.print_btn_row.winfo_rooty() > tab.rx_section.tree_hist.winfo_rooty(), (lang, geo)
    btns = tab.rx_section.print_btn_row.winfo_children(); assert len(btns) == 2, (lang, geo, btns)
    for btn in btns:
        assert btn.winfo_viewable(), (lang, geo, btn)
        assert btn.winfo_width() >= btn.winfo_reqwidth(), (lang, geo)
        left = btn.winfo_rootx() - root.winfo_rootx()
        assert 0 <= left and left + btn.winfo_width() <= root.winfo_width(), (lang, geo, left)
        top = btn.winfo_rooty() - root.winfo_rooty()
        assert 0 <= top and top + btn.winfo_height() <= root.winfo_height(), (lang, geo, top)

def test_rx_print_buttons_inside_window_en_ar_both_sizes():
    for geo in ("1380x1000", "1380x820"):
        for lang in ("en", "ar"):
            root, tab = _build(geo, lang)
            if tab is None:
                print(f"SKIP rx_buttons {geo} {lang} (no display)"); return
            try:
                _check_rx_buttons(root, tab, lang, geo)
            finally:
                root.destroy()
    set_setting("language", "en")

def test_panels_header_rx_content_and_everything_reachable():
    fid = _seed_patient("Amoxicillin 500 mg", "Penicillin")
    try:
        _seed_payment(fid, "2026-11-01", "16", 50000, 80000)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO procedures(patient_file,visit_date,tooth_number,procedure_done) VALUES(?,?,?,?)",
                    (fid, "2026-11-02", "16", "Root canal"))
        conn.commit(); conn.close()
        _seed_rx(fid, "fady", ["Amoxicillin"])
        patient = {"file_number": fid, "full_name": "R15 Panel Test", "mobile1": "", "birth_date_greg": "1990-01-01",
                   "current_medications": "Amoxicillin 500 mg", "allergies": "Penicillin"}
        root, tab = _build(patient=patient)
        if tab is None:
            print("SKIP panels_header_rx_content (no display)"); return
        try:
            tab.load(fid); root.update()
            # R38: tree_fin is the PAYMENTS REVIEW — the seeded
            # payment shows as a Session row: amount + balance
            # 30,000.00 (no tooth column in the review).
            fin_vals = [str(v) for i in tab.tree_fin.get_children() for v in tab.tree_fin.item(i, "values")]
            assert any("50000" in v for v in fin_vals), fin_vals
            assert any("30,000.00" in v for v in fin_vals), fin_vals
            assert any(v == "Session" for v in fin_vals), fin_vals
            # R24: procedure text is the unified tree's column value.
            hist_vals = [str(v) for i in tab.tree_history.get_children() for v in tab.tree_history.item(i, "values")]
            assert any("Root canal" in v for v in hist_vals), hist_vals
            # R22: Health lines live in the pinned header; Rx are tree rows.
            assert "Penicillin" in tab.header_panel.info_text()
            rows = [tab.rx_section.tree_hist.item(i, "values") for i in tab.rx_section.tree_hist.get_children()]
            assert "Amoxicillin" in " ".join(str(v) for r in rows for v in r), rows
            # R24: tree_diag/tree_proc/history_top_nb are REMOVED;
            # the unified tree_history replaces them.
            # R27: tree_xray is REMOVED; xray_grid (thumbnail grid)
            # replaces it in the same notebook slot.
            for attr in ("tree_history", "tree_fin", "xray_grid", "tree_ref", "rx_section", "fin_frame", "scans_frame", "ref_section", "history_section", "history_nb"):
                assert getattr(tab, attr, None) is not None, attr
            for attr in ("tree_diag", "tree_proc", "history_top_nb"):
                assert not hasattr(tab, attr), attr
            assert not hasattr(tab, "notes_section")  # R21 item 5: removed
            tabs = [tab.history_nb.tab(i, "text").strip() for i in tab.history_nb.tabs()]
            assert tabs == ["Payments review", "X-Rays", "Scans"], tabs  # R38 rename
        finally:
            root.destroy()
    finally:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM procedures WHERE patient_file=?", (fid,)); conn.commit(); conn.close()
        _cleanup(fid)
