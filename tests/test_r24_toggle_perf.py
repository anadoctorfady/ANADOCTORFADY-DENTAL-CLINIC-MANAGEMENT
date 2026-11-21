"""Round 24 item 8: BOTH toggles fast AND correct at seed scale.

Extends the round-21 language-only perf regression (which stays in
test_r21_toggle_perf.py) to the theme toggle, first profiled in
round 24 (BEFORE, pre-round-24 code: language median 0.92s, theme
0.80s; current tree before this item: 0.66s / 0.68s; after: ~0.4s
each - Linux/Xvfb structural numbers, not Windows timings). Pinned:
PhotoImages for rounded buttons / frames / field borders and the
paper backgrounds are cached across rebuilds on the toplevel
(src/ui/image_cache.py), keyed by every render parameter; the shell
builds AppointmentsTab / FinanceTab with defer_load=True (loads
wait for first show; explicit load() stays safe before first show;
Finance's gate untouched - a deferred load still refuses locked).
A fast-but-wrong rebuild must FAIL: the new language (tab label) /
new theme (root bg + mode) are asserted after the toggles."""
import statistics
import time
from types import SimpleNamespace

from tests.test_r21_toggle_perf import _seed_200
from tests.test_templates_edit import isolated_db

def test_both_toggles_fast_and_correct_with_200_patients():
    from tkinter import messagebox
    from src.config.strings import t
    from src.config.theme import current, mode
    from src.ui.shell import App
    from tests.test_r18_info_panel_visible import _login
    with isolated_db():
        _seed_200()
        messagebox.showinfo = lambda *a, **k: None
        app = App()
        try:
            _login(app)
            app.deiconify(); app.geometry("1380x1000"); app.update()
            app.search_var.set("Pat"); app.load_patients(); app.update()
            assert len(app.tree.get_children("")) >= 190
            for _ in range(2):  # warm-ups (also prime the image cache)
                app._toggle_lang(); app.update()
                app._toggle_theme(); app.update()
            lang0, mode0 = app.lang, mode()
            lang_runs, theme_runs = [], []
            for _ in range(3):
                t0 = time.perf_counter()
                app._toggle_lang(); app.update()
                lang_runs.append(time.perf_counter() - t0)
            assert app.lang != lang0  # odd count: language really flipped
            tab0 = app.notebook.tab(app.clinical, "text")
            assert tab0 == t("shell.tab_clinical", app.lang), tab0
            for _ in range(3):
                t0 = time.perf_counter()
                app._toggle_theme(); app.update()
                theme_runs.append(time.perf_counter() - t0)
            assert mode() != mode0  # theme really flipped
            assert app.cget("bg") == current()["bg"]
            btn = t("shell.theme_light" if mode() == "dark" else "shell.theme_dark", app.lang)
            assert app.theme_btn.cget("text") == btn
            assert statistics.median(lang_runs) < 3.0, lang_runs
            assert statistics.median(theme_runs) < 3.0, theme_runs
        finally:
            app.destroy()

def test_cached_photo_reuse_and_key_separation():
    import tkinter as tk
    from PIL import Image
    from src.ui.image_cache import cache_size, cached_photo
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return  # no display
    try:
        calls = []
        def make(rgb):
            def _m():
                calls.append(rgb)
                return Image.new("RGBA", (10, 6), rgb)
            return _m
        a = cached_photo(root, ("rounded", 10, 6, 2, "#FF0000", None), make((255, 0, 0, 255)))
        b = cached_photo(root, ("rounded", 10, 6, 2, "#FF0000", None), make((255, 0, 0, 255)))
        assert a is b and len(calls) == 1  # second call: no re-render
        c = cached_photo(root, ("rounded", 10, 6, 2, "#00FF00", None), make((0, 255, 0, 255)))
        assert c is not a and len(calls) == 2  # new colour: new image
        d = cached_photo(root, ("rounded", 12, 6, 2, "#FF0000", None), make((255, 0, 0, 255)))
        assert d is not a and cache_size(root) == 3  # new size: new entry
    finally:
        root.destroy()

def test_rounded_button_images_survive_widget_rebuild():
    import tkinter as tk
    from src.ui.rounded import RoundedButton
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    try:
        b1 = RoundedButton(root, text="Save", bg="#A85F33", fg="white")
        img1 = b1._images["normal"]
        b1.destroy()  # a toggle destroys every widget...
        b2 = RoundedButton(root, text="Save", bg="#A85F33", fg="white")
        assert b2._images["normal"] is img1  # ...but not the image
        b3 = RoundedButton(root, text="Save", bg="#065F46", fg="white")
        assert b3._images["normal"] is not img1  # other colour: other image
    finally:
        root.destroy()

def test_button_configure_after_cache_eviction():
    """Regression (found by test_r21_dark_zebra on the first R24 run):
    a day button re-configured AFTER its displayed image's cache entry
    was evicted died with TclError 'image doesn't exist' - the previous
    set must stay alive until _sync() repoints the widget."""
    import tkinter as tk
    from src.ui.rounded import RoundedButton
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        return
    try:
        b = RoundedButton(root, text="1", bg="#123456", fg="white",
                          padx=2, pady=2, radius=6)
        b.pack(); root.update()
        cache = getattr(root, "_r24_photo_cache", None)
        assert cache is not None and len(cache) >= 4
        cache.clear()  # eviction storm: cache no longer holds the images
        b.config(text="20 \u2022", state="normal")  # must not raise
        b.config(bg="#991B1B", fg="white"); root.update()
        assert b.cget("text") == "20 \u2022"
    finally:
        root.destroy()


def test_paper_tiled_image_cached_per_size():
    from src.ui.paper_bg import tiled_image
    a = tiled_image(300, 200)
    assert tiled_image(300, 200) is a
    assert tiled_image(301, 200) is not a


def test_appointments_deferred_load_and_load_before_show():
    import tkinter as tk
    from src.models.database import get_connection, init_db
    from src.ui.appointments import AppointmentsTab
    with isolated_db():
        init_db()
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO patients(first_name,full_name,birth_date_greg,"
                    "nationality) VALUES(?,?,?,?)",
                    ("Def", "Deferred Patient", "1990-01-01", "Syrian"))
        fid = cur.lastrowid
        cur.execute("INSERT INTO appointments(patient_file,appointment_date,"
                    "appointment_time,reason,status,created_at) VALUES(?,?,?,?,?,?)",
                    (fid, "2026-11-20", "10:00", "Check", "قادم", "2026-11-01T09:00:00"))
        conn.commit(); conn.close()
        try:
            root = tk.Tk(); root.withdraw()
        except tk.TclError:
            return
        try:
            stub = SimpleNamespace(lang="en", current_patient=None)
            tab = AppointmentsTab(root, stub, defer_load=True)
            tab.pack(fill="both", expand=True); root.update()
            assert tab._needs_load and not tab.tree.get_children()
            tab.load()  # explicit load BEFORE first show: safe + complete
            assert not tab._needs_load and len(tab.tree.get_children()) == 1
            tab2 = AppointmentsTab(root, stub, defer_load=True)
            tab2.pack(fill="both", expand=True)
            root.deiconify(); root.update()  # Map fires -> deferred load runs
            assert not tab2._needs_load and len(tab2.tree.get_children()) == 1
        finally:
            root.destroy()


def test_finance_deferred_load_respects_gate():
    import tkinter as tk
    from src.models.finance import add_expense
    from src.ui.finance import FinanceTab
    from src.utils.finance_gate import FinanceGate
    with isolated_db():
        try:
            root = tk.Tk(); root.withdraw()
        except tk.TclError:
            return
        try:
            add_expense("2026-11-01", "Rent", "deferred check", 500)
            stub = SimpleNamespace(lang="en", current_user="fady",
                                   current_role="admin", current_patient=None,
                                   finance_gate=None)
            tab = FinanceTab(tk.Frame(root), stub, defer_load=True)
            root.update_idletasks()
            assert tab._needs_load and not tab.tree_exp.get_children()
            tab.load()  # locked gate: still refuses, reveals nothing
            assert not tab.tree_exp.get_children()
            tab.gate = FinanceGate(verify_fn=lambda u, p: True)
            assert tab.gate.try_unlock("fady", "x")
            tab._on_map(SimpleNamespace(widget=tab))  # first show, unlocked
            assert not tab._needs_load and len(tab.tree_exp.get_children()) == 1
            assert tab.cards["Total Expenses"].cget("text") != "0.00"
        finally:
            root.destroy()
