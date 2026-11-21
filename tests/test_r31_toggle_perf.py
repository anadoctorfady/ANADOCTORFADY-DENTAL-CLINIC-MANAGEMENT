"""Round 31 item 2: toggle speed -- the duplicate patient load is gone.

Profile on the 500-patient seed (Linux/Xvfb, this VM; Windows will
differ): a toggle with a patient open took ~3.5-4.3s. cProfile showed
App.on_select ran TWICE per rebuild -- select_patient() calls it
directly AND its selection_set() queues a <<TreeviewSelect>> that
called it again -- and PatientInfoPanel.refresh computed
patient_alerts() twice (two patient_totals() DB round-trips).
Round 31 fixes, all behaviour-neutral:
- shell.select_patient arms App._tree_select_echo; the tree's
  <<TreeviewSelect>> handler (App._on_tree_select, bound in
  shell_left) swallows that ONE echo for the SAME row. A genuine
  click (no echo armed, or a different row) always loads.
- App.on_select no longer refreshes the info panel a second time
  (clinical.load already refreshed it for the same patient).
- patient_alerts.refresh_alert_strip returns its alerts and
  PatientInfoPanel.refresh reuses them for the red-name check
  instead of calling patient_alerts() again.
After: ~1.75-1.9s per toggle on the 500 seed (~2x). The remaining
hotspot is the DB layer (init_db ~52ms + settings-cache reloads in
src/models/database.py), outside this item's file scope.
The 3s assertions below are the standing gate threshold (slow CI);
the structural pins are the on_select call counts + correctness.
"""
import statistics
import time

from tests.test_r21_toggle_perf import _seed_200
from tests.test_templates_edit import isolated_db


def _build_app():
    from tkinter import messagebox
    from src.ui.shell import App
    from tests.test_r18_info_panel_visible import _login
    messagebox.showinfo = lambda *a, **k: None
    app = App()
    _login(app)
    app.deiconify(); app.geometry("1380x1000"); app.update()
    app.search_var.set("Pat"); app.load_patients(); app.update()
    assert len(app.tree.get_children("")) >= 190
    return app


def test_programmatic_select_loads_patient_once():
    with isolated_db():
        _seed_200()
        app = _build_app()
        try:
            calls = []
            orig = app.on_select
            app.on_select = lambda: (calls.append(1), orig())
            kids = app.tree.get_children("")
            fid = int(app.tree.item(kids[0], "values")[0])
            app.select_patient(fid); app.update()  # update delivers the event
            assert len(calls) == 1, f"on_select ran {len(calls)}x for one select"
            assert app.current_patient["file_number"] == fid
            assert int(app.clinical.patient_id) == fid
            # A genuine user click (selection_set with NO echo armed)
            # still loads exactly once.
            calls.clear()
            fid2 = int(app.tree.item(kids[1], "values")[0])
            app.tree.selection_set(kids[1]); app.update()
            assert len(calls) == 1, f"click ran on_select {len(calls)}x"
            assert app.current_patient["file_number"] == fid2
            assert int(app.clinical.patient_id) == fid2
        finally:
            app.destroy()


def test_both_toggles_fast_and_correct_with_patient_open():
    from src.config.strings import t
    from src.config.theme import current, mode
    with isolated_db():
        _seed_200()
        app = _build_app()
        try:
            kids = app.tree.get_children("")
            fid = int(app.tree.item(kids[0], "values")[0])
            app.select_patient(fid); app.update()
            for _ in range(2):  # warm-ups (prime the image cache)
                app._toggle_lang(); app.update()
                app._toggle_theme(); app.update()
            lang0, mode0 = app.lang, mode()
            lang_runs, theme_runs = [], []
            for _ in range(3):
                t0 = time.perf_counter()
                app._toggle_lang(); app.update()
                lang_runs.append(time.perf_counter() - t0)
            assert app.lang != lang0  # odd count: really flipped
            assert app.notebook.tab(app.clinical, "text") == \
                t("shell.tab_clinical", app.lang)
            for _ in range(3):
                t0 = time.perf_counter()
                app._toggle_theme(); app.update()
                theme_runs.append(time.perf_counter() - t0)
            assert mode() != mode0
            assert app.cget("bg") == current()["bg"]
            btn = t("shell.theme_light" if mode() == "dark"
                    else "shell.theme_dark", app.lang)
            assert app.theme_btn.cget("text") == btn
            # The open patient survived every rebuild, fully loaded.
            assert app.current_patient["file_number"] == fid
            assert int(app.clinical.patient_id) == fid
            assert statistics.median(lang_runs) < 3.0, lang_runs
            assert statistics.median(theme_runs) < 3.0, theme_runs
        finally:
            app.destroy()


def test_finance_gate_still_locked_after_toggle_then_unlocks():
    from src.models.finance import add_expense
    with isolated_db():
        _seed_200()
        add_expense("2026-11-01", "Rent", "r31 gate check", 500)
        app = _build_app()
        try:
            app._toggle_lang(); app.update()  # rebuild incl. Finance tab
            app.notebook.select(app.fin); app.update()
            # Locked gate first: nothing revealed, load still deferred.
            assert not app.fin.gate.is_unlocked
            assert app.fin._lock.place_info(), "lock view not shown"
            assert not app.fin.tree_exp.get_children()
            # Real unlock path (gate user + password) reveals the data.
            app.fin.e_gate_user.delete(0, "end")
            app.fin.e_gate_user.insert(0, "fady")
            app.fin.e_gate_pass.insert(0, "1234")
            app.fin._try_unlock(); app.update()
            assert app.fin.gate.is_unlocked
            assert len(app.fin.tree_exp.get_children()) == 1
            assert app.fin.cards["Total Expenses"].cget("text") != "0.00"
        finally:
            app.destroy()
