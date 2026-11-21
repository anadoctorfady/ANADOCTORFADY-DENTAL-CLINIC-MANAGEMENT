"""Round 22 regression (2 of 2): shell column + main-flow order.

Companion to tests/test_r22_layout.py (the pinned header). Pins
round-22 parts B + C: the shell's far-left column keeps ONLY
search + patient list + the Prescriptions section (compose +
history + Print, reachable by scrolling at 1380x820, EN + AR),
and the main scroll flow order is chart -> input tables ->
History -> panels -> finance -> scans notebook, with the Rx
section NOT in the flow. Round 23 supersession (item 2b): the
Recent Payments panel was REMOVED, so the only built panel in
the flow is now Therapeutic Procedures.
Full-App tests: isolated gate copy only; skips with no display."""
import tkinter as tk

from tests.test_r22_layout import _boot, _chain, _inside, _ready


def test_shell_column_and_main_flow_placement():
    if not _ready():
        return
    app = _boot("1380x1000")
    try:
        tab = app.clinical
        # C: the Rx section lives in the shell host, under the list.
        assert tab.rx_section.master is app.rx_host
        assert app.rx_host in _chain(tab.rx_section)
        slaves = app.left_inner.pack_slaves()
        tf = app.tree.master.master  # tree -> tf.inner -> tf frame
        assert slaves.index(tf) < slaves.index(app.rx_host)
        # C: NO patient info panel anywhere in the shell column.
        from src.ui.patient_info import PatientInfoPanel
        stack = [app.left_inner]
        while stack:
            cur = stack.pop()
            assert not isinstance(cur, PatientInfoPanel)
            stack.extend(cur.winfo_children())
        assert not hasattr(app, "panels_host")
        # B: ROUND-24 SUPERSESSION: NO summary panels exist in the
        # main flow (procedures panel removed with the unified
        # table); the flow is chart -> input block -> unified
        # history section -> finance section -> notebook.
        assert not hasattr(tab, "panel_frames")
        assert not hasattr(tab, "panels_section")
        order = tab.right_inner.pack_slaves()
        seq = [tab.chart, tab.input_block, tab.history_section,
               tab.fin_section, tab.history_nb]  # R28: fin_section = pack slave
        idx = [order.index(w) for w in seq]
        assert idx == sorted(idx), idx
        assert tab.rx_section not in order  # it lives in the shell
    finally:
        app.destroy()


def _scroll_widget_to_top(app, widget):
    """Scroll the shell column so `widget` sits at its top (its y
    within left_inner, accumulated up the master chain)."""
    y = 0
    w = widget
    while w is not None and w is not app.left_inner:
        y += w.winfo_y(); w = w.master
    inner_h = max(1, app.left_inner.winfo_height())
    app.left_canvas.yview_moveto(y / inner_h)
    app.update_idletasks(); app.update()


def test_rx_panel_reachable_at_820_en_ar():
    if not _ready():
        return
    from src.models.database import set_setting
    for lang in ("en", "ar"):
        set_setting("language", lang)
        app = _boot("1380x820")
        try:
            assert app.lang == lang
            rx = app.clinical.rx_section
            # Compose controls reachable by scrolling the column.
            _scroll_widget_to_top(app, rx)
            for wdg in (rx.cb_cat, rx.cb_drug, rx.e_dose, rx.cb_freq):
                assert wdg.winfo_viewable(), (lang, wdg)
                assert _inside(app, wdg), (lang, wdg)
            # History + Print row reachable at the column bottom.
            app.left_canvas.yview_moveto(1.0); app.update()
            assert rx.tree_hist.winfo_viewable(), lang
            for btn in rx.print_btn_row.winfo_children():
                assert btn.winfo_viewable(), (lang, btn)
                assert _inside(app, btn), (lang, btn)
            app.left_canvas.yview_moveto(0.0); app.update()
            assert _inside(app, app.tree), lang
        finally:
            app.destroy()
    set_setting("language", "en")
