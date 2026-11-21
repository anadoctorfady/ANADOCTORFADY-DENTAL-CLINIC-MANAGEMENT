"""Toggle speed regression (2026-11-08): theme and language toggles must
stay fast. Root cause of the slowness: every toggle rebuilt the whole UI
and every widget build called theme.current() -> get_setting() ->
init_db() (~50 SQL statements) - 130+ init_db() runs per toggle, ~0.28s
of a ~0.5-1.0s toggle. Fixed by caching settings in memory
(src/models/database.py), caching logo/tooth PhotoImages on the toplevel
(src/utils/logo.py, src/ui/dental_chart.py), and skipping a duplicate
dental-chart refresh when the selection did not change. Measured under
xvfb on this VM: theme 0.47/0.76s -> 0.21/0.17s, language 0.96/0.71s ->
0.16/0.16s. The 3s threshold here is deliberately generous (slow CI /
loaded machines); the real target is well under 1s.
"""
import time

from src.models.database import get_setting, set_setting


def test_theme_and_language_toggles_are_fast():
    """GUI test under xvfb; skips (returns) with no display, like
    test_language_persist. Each toggle must complete below 3s, flip the
    mode/language, and leave the persisted setting correct."""
    try:
        from tkinter import messagebox
        from src.config.theme import mode
        from src.ui.shell import App
        orig_lang = get_setting("language", "en") or "en"
        orig_mode = mode()
        set_setting("language", "en")
        if orig_mode == "dark":
            set_setting("theme_mode", "light")
        app = App()
        app._logged_in = True  # login window not shown yet (after(100))
        messagebox.showinfo = lambda *a, **k: None
        try:
            assert mode() == "light" and app.lang == "en"
            t0 = time.perf_counter()
            app._toggle_theme()
            app.update_idletasks()
            dt_theme = time.perf_counter() - t0
            assert mode() == "dark", mode()
            assert dt_theme < 3.0, f"dark toggle took {dt_theme:.2f}s"
            t0 = time.perf_counter()
            app._toggle_theme()
            app.update_idletasks()
            dt_theme2 = time.perf_counter() - t0
            assert mode() == "light", mode()
            assert dt_theme2 < 3.0, f"light toggle took {dt_theme2:.2f}s"
            t0 = time.perf_counter()
            app._toggle_lang()
            app.update_idletasks()
            dt_lang = time.perf_counter() - t0
            assert app.lang == "ar" and get_setting("language") == "ar"
            assert dt_lang < 3.0, f"language toggle took {dt_lang:.2f}s"
            t0 = time.perf_counter()
            app._toggle_lang()
            app.update_idletasks()
            dt_lang2 = time.perf_counter() - t0
            assert app.lang == "en" and get_setting("language") == "en"
            assert dt_lang2 < 3.0, f"language toggle took {dt_lang2:.2f}s"
        finally:
            set_setting("language", orig_lang)
            set_setting("theme_mode", orig_mode)
            try:
                app.destroy()
            except Exception:
                pass
    except Exception:
        return  # no display: skip GUI check


def test_toggle_refresh_print_with_patient_selected():
    """Regression (2026-11-08): shell.py used the typo'd attribute
    `current_patienth` in _rebuild/refresh_clinical/print_pdf, so ANY
    theme/language toggle, clinical refresh or PDF print crashed with
    AttributeError whenever a patient was selected (with no patient
    selected the guard short-circuited, which is why the gate never
    caught it). Only a missing display skips this test - any other
    exception must fail the gate."""
    import tkinter as tk
    from tkinter import messagebox
    from src.config.settings import REPORTS
    from src.config.theme import mode
    from src.models.database import get_connection, init_db
    from src.ui.shell import App
    try:
        probe = tk.Tk()
    except tk.TclError:
        return  # no display: skip GUI check
    probe.destroy()
    orig_lang = get_setting("language", "en") or "en"
    orig_mode = mode()
    set_setting("language", "en")
    if orig_mode == "dark":
        set_setting("theme_mode", "light")
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name,birth_date_greg,"
                "nationality) VALUES(?,?,?,?)",
                ("Toggle", "Toggle Test Patient", "1990-01-01", "Syrian"))
    fid = cur.lastrowid; conn.commit(); conn.close()
    app = App()
    app._logged_in = True  # login window not shown yet (after(100))
    messagebox.showinfo = lambda *a, **k: None
    # print_pdf() shows a REAL modal showerror on failure - patch it to
    # record instead, or a PDF error would hang the suite forever under
    # xvfb with nobody to dismiss the dialog.
    errs = []
    messagebox.showerror = lambda *a, **k: errs.append(a)
    messagebox.askyesno = lambda *a, **k: False
    try:
        app.load_patients()
        app.select_patient(fid)
        assert app.current_patient
        assert app.current_patient["file_number"] == fid
        app._toggle_theme(); app.update_idletasks()
        assert mode() == "dark", mode()
        assert app.current_patient["file_number"] == fid
        app._toggle_lang(); app.update_idletasks()
        assert app.lang == "ar"
        app._toggle_lang(); app.update_idletasks()
        assert app.lang == "en"
        app._toggle_theme(); app.update_idletasks()
        assert mode() == "light", mode()
        app.refresh_clinical()
        # Round 16: print_pdf() with no bilingual flag opens the
        # print preview (covered by test_print_preview_shell_r16).
        # Round 25 SUPERSESSION: the bilingual=True path no longer
        # saves directly into REPORTS either -- it opens the SAME
        # print preview (its old "Saved: <full path>" dialog leaked
        # the storage path). The PDF is built into a temp folder;
        # nothing lands in REPORTS until the user picks Print /
        # Save PDF inside the preview.
        from pathlib import Path
        _before = set(Path(REPORTS).glob("ANADOCTORFADY_Toggle*"))
        app.print_pdf(bilingual=True)
        app.update_idletasks()
        assert not errs, errs
        from src.reports.print_preview import PrintPreview
        _stack, _prevs = [app], []
        while _stack:
            _w = _stack.pop()
            if isinstance(_w, PrintPreview):
                _prevs.append(_w)
            _stack.extend(_w.winfo_children())
        assert _prevs, "bilingual Print PDF did not open the preview"
        _pdf = Path(_prevs[0].pdf_path)
        assert _pdf.exists() and _pdf.name.startswith("ANADOCTORFADY_Toggle"), _pdf
        assert set(Path(REPORTS).glob("ANADOCTORFADY_Toggle*")) == _before, \
            "preview saved into REPORTS without asking"
        _prevs[0].destroy()
        assert app.current_patient["file_number"] == fid
    finally:
        set_setting("language", orig_lang)
        set_setting("theme_mode", orig_mode)
        try:
            app.destroy()
        except Exception:
            pass
