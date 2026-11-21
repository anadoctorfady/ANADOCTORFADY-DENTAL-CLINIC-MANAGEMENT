"""Round 16 integration (W2-B): App.print_pdf goes through the print
preview (not a bare save).

Clicking Print PDF with a patient selected must open the preview
window (Print / Save PDF / Cancel + language choice) and must NOT
write a PDF into the reports folder by itself. The bilingual direct
path is covered by test_toggle_speed (print_pdf(bilingual=True)).
GUI test under xvfb; skips with no display. Runs against the gate
DB copy (ANADOCTORFADY_DATA_DIR), never the live DB.
"""
import tkinter as tk
from pathlib import Path

from src.config.settings import REPORTS
from src.models.database import get_connection, init_db
from src.ui.shell import App


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def test_app_print_pdf_opens_preview_not_bare_save():
    try:
        probe = tk.Tk()
    except tk.TclError:
        return  # no display: skip GUI check
    probe.destroy()
    import tkinter.messagebox as mb
    old_info, old_err = mb.showinfo, mb.showerror
    mb.showinfo = lambda *a, **k: None
    mb.showerror = lambda *a, **k: None
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name,birth_date_greg,"
                "nationality) VALUES(?,?,?,?)",
                ("Preview", "Preview Shell Patient", "1990-01-01", "Syrian"))
    fid = cur.lastrowid
    conn.commit()
    conn.close()
    before = set(Path(REPORTS).glob("ANADOCTORFADY_Preview*"))
    app = App()
    app._logged_in = True  # login window not shown yet (after(100))
    try:
        app.load_patients()
        app.select_patient(fid)
        assert app.current_patient
        assert app.current_patient["file_number"] == fid
        app.print_pdf()
        app.update_idletasks()
        previews = [w for w in _walk(app)
                    if isinstance(w, tk.Toplevel)
                    and "Print Preview" in w.title()]
        assert previews, "Print PDF did not open the preview window"
        win = previews[0]
        btns = {str(w.cget("text")) for w in _walk(win)
                if isinstance(w, tk.Button)}
        assert {"Print", "Save PDF", "Cancel"} <= btns, btns
        # No bare save: the preview generates into a temp folder.
        after = set(Path(REPORTS).glob("ANADOCTORFADY_Preview*"))
        assert after == before, "Print PDF saved a PDF without asking"
        win.destroy()
        app.update_idletasks()
    finally:
        mb.showinfo, mb.showerror = old_info, old_err
        try:
            app.destroy()
        except Exception:
            pass
