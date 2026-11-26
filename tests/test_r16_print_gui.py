"""Round 16 worker C: print-preview window (GUI).

Shares fixtures (PATIENT, _make_pdf, _TMP) with tests/test_r16_print.py.
Skips gracefully with no display.
"""
import inspect
from pathlib import Path

from tests.test_r16_print import PATIENT, _TMP, _make_pdf


def _tk():
    try:
        import tkinter as tk
        return tk.Tk()
    except Exception:
        return None


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)

def test_preview_contract_signature():
    from src.reports.print_preview import show_print_preview
    params = list(inspect.signature(show_print_preview).parameters)
    assert params[:4] == ["parent", "title", "build_pdf_fn", "lang"]


def _tk():
    try:
        import tkinter as tk
        return tk.Tk()
    except Exception:
        return None


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def test_preview_window_print_save_cancel():
    import tkinter as tk
    from src.reports.print_preview import show_print_preview
    from src.reports.report_text import patient_preview_lines
    root = _tk()
    if root is None:
        print("SKIP test_preview_window (no display)")
        return
    # Do NOT withdraw: a withdrawn root leaves the transient preview
    # unmapped (1x1, not viewable) and the visibility assertion below
    # would fail for the wrong reason. Xvfb maps it fine.
    root.geometry("900x700+0+0")
    import tkinter.messagebox as mb
    seen = []
    old_info, old_warn = mb.showinfo, mb.showwarning
    mb.showinfo = lambda *a, **k: seen.append(("info", a))
    mb.showwarning = lambda *a, **k: seen.append(("warn", a))
    try:
        def build(lang):
            return _make_pdf(out_dir=_TMP, language=lang)
        win = show_print_preview(
            root, "Test Patient", build, "en",
            preview_text=lambda lang: patient_preview_lines(
                PATIENT, language=lang))
        root.update_idletasks()
        btns = {str(w.cget("text")): w for w in _walk(win)
                if isinstance(w, tk.Button)}
        assert "Print" in btns and "Save PDF" in btns and "Cancel" in btns
        # Regression: the expanding text frame once squeezed the
        # button row to 1px — buttons must actually be visible.
        assert all(b.winfo_viewable() and b.winfo_height() > 20
                   for b in btns.values())
        body = next(w for w in _walk(win) if isinstance(w, tk.Text))
        assert "Diseases: Diabetes, Hypertension" in body.get("1.0", tk.END)
        assert "1 page" in win.info.cget("text")
        # Language override regenerates the report in Arabic.
        win.lang_var.set("ar")
        win._on_lang()
        root.update_idletasks()
        assert "الأمراض:" in body.get("1.0", tk.END)
        # Print with no printer here: warning, window stays open.
        btns["Print"].invoke()
        root.update_idletasks()
        assert win.winfo_exists()
        assert any(k == "warn" for k, _ in seen)
        btns["Cancel"].invoke()
        root.update_idletasks()
        assert not win.winfo_exists()
    finally:
        mb.showinfo, mb.showwarning = old_info, old_warn
        root.destroy()


def test_preview_window_without_preview_text():
    import tkinter as tk
    from src.reports.print_preview import show_print_preview
    root = _tk()
    if root is None:
        print("SKIP test_preview_window_without_preview_text (no display)")
        return
    root.geometry("900x700+0+0")
    try:
        win = show_print_preview(root, "Test Patient",
                                 lambda lang: _make_pdf(out_dir=_TMP,
                                                        language=lang),
                                 "en")
        root.update_idletasks()
        assert win.winfo_exists()
        assert win.info.cget("text") != ""
        win.destroy()
        root.update_idletasks()
    finally:
        root.destroy()


def test_open_patient_preview_end_to_end():
    """The shell wiring helper: seeded patient in an isolated DB,
    fake app = the Tk root; the preview opens with that patient's
    data (diseases included) and Cancel closes it."""
    import tkinter as tk
    from src.models.database import get_connection
    from src.reports.print_preview import open_patient_preview
    from tests.test_r16_print import isolated_db
    root = _tk()
    if root is None:
        print("SKIP test_open_patient_preview_end_to_end (no display)")
        return
    root.geometry("900x700+0+0")
    try:
        with isolated_db():
            conn = get_connection()
            conn.execute(
                "INSERT INTO patients(file_number, full_name,"
                " birth_date_greg, birth_date_hijri, age_years,"
                " age_months, age_days, nationality, mobile1, mobile2,"
                " emergency_phone, address, created_at, diseases)"
                " VALUES(77, 'Test Patient', '1990-05-15',"
                " '20 Shawwal 1410', 36, 5, 21, 'Syrian', '0791234567',"
                " '', '0799888777', 'Damascus', '2026-11-05',"
                " 'Diabetes, Hypertension')")
            conn.commit()
            conn.close()
            root.current_patient = {"file_number": 77}
            root.chart_teeth = lambda: ["36"]
            root.lang = "en"
            root.current_user = "fady"
            win = open_patient_preview(root)
            root.update_idletasks()
            body = next(w for w in _walk(win) if isinstance(w, tk.Text))
            assert "Diseases: Diabetes, Hypertension" in body.get("1.0", tk.END)
            assert "Test Patient" in body.get("1.0", tk.END)
            win.destroy()
            root.update_idletasks()
    finally:
        root.destroy()
