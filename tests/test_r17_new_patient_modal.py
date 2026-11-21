"""Round 17 item 7: "+ New Patient" opens the entry form as a MODAL
dialog; the form is not hosted anywhere permanently.

- shell._main no longer creates a PatientForm or a Patients tab.
- new_patient() opens a tk.Toplevel (grabbed) over the current view
  from ANY tab, with NO tab navigation, and clears the previously
  open patient (clinical chart included) as it opens.
- A successful save closes the dialog, creates the patient, and the
  new patient becomes current + opens (clinical tab loads him).
- Duplicate handling works from the dialog: declining the "open
  existing?" prompt keeps the dialog open; accepting closes it and
  opens the existing file.

GUI tests skip gracefully with no display; run with DISPLAY=:98
against an isolated ANADOCTORFADY_DATA_DIR copy. Seeded rows are
cleaned up."""
import tkinter as tk
import tkinter.messagebox as _mb

from src.models.database import get_connection, init_db
from src.models.patients import save_patient_record


def _make_app():
    """Real App under Xvfb, logged in, login window dismissed;
    None when there is no display."""
    init_db()
    try:
        from src.ui.shell import App
        app = App()
    except Exception:
        return None
    try:
        app._on_login("fady")
        from src.ui.login import LoginWindow
        for w in list(app.winfo_children()):
            if isinstance(w, LoginWindow):
                w.destroy()
        app.deiconify(); app.update()
        return app
    except Exception:
        try: app.destroy()
        except Exception: pass
        raise


def _patch_msgs(ask_answer=False):
    caps = {"error": [], "info": [], "ask": [], "ask_answer": ask_answer}
    orig = (_mb.showerror, _mb.showinfo, _mb.askyesno)
    _mb.showerror = lambda *a, **k: caps["error"].append(a)
    _mb.showinfo = lambda *a, **k: caps["info"].append(a)
    _mb.askyesno = lambda *a, **k: caps["ask"].append(a) or caps["ask_answer"]
    return caps, lambda: [setattr(_mb, n, f) for n, f in
                          zip(("showerror", "showinfo", "askyesno"), orig)]


def _set(entry, val):
    entry.delete(0, tk.END)
    if val:
        entry.insert(0, val)


def _fill(form, first, father, last, birth="15/05/1990"):
    _set(form.e_first, first); _set(form.e_father, father)
    _set(form.e_last, last); _set(form.e_birth, birth)


def _cleanup(fid):
    if not fid:
        return
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
        conn.commit(); conn.close()
    except Exception:
        pass


def _count_names(first, father, last):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM patients WHERE first_name=? AND "
                "father_name=? AND last_name=?", (first, father, last))
    n = cur.fetchone()[0]; conn.close(); return n


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def test_no_permanent_patient_form_in_notebook():
    app = _make_app()
    if app is None:
        print("SKIP test_no_permanent_patient_form_in_notebook (no display)"); return
    try:
        from src.ui.patient_form import PatientForm
        assert not hasattr(app, "form"), "shell still hosts a permanent form"
        tab_texts = [app.notebook.tab(i, "text")
                     for i in range(len(app.notebook.tabs()))]
        from src.config.strings import t
        assert t("shell.tab_patients", app.lang) not in tab_texts, tab_texts
        assert not any(isinstance(w, PatientForm)
                       for w in _walk(app.notebook))
        assert app.chart_teeth() == app.clinical.chart.get_selection()[0]
    finally:
        app.destroy()


def test_new_patient_opens_modal_without_tab_switch():
    app = _make_app()
    if app is None:
        print("SKIP test_new_patient_opens_modal_without_tab_switch (no display)"); return
    win = None
    try:
        app.notebook.select(app.appt); app.update()
        before = app.notebook.select()
        app.clinical.chart.set_treated(["16"])  # stale markers of a prior patient
        win = app.new_patient(); app.update()
        assert win is not None and win.winfo_exists()
        assert isinstance(win, tk.Toplevel)
        assert win.grab_status() is not None, "dialog is not modal (no grab)"
        assert app.notebook.select() == before, "opening the dialog switched tabs"
        from src.ui.dental_chart import DentalChartFrame
        from src.ui.patient_form import PatientForm
        assert isinstance(win.form, PatientForm)
        assert not any(isinstance(w, DentalChartFrame) for w in _walk(win)), \
            "dialog contains a dental chart"
        assert app.current_patient is None
        assert app.clinical.chart.get_treated() == [], \
            "previous patient's treated markers survived dialog open"
        win.destroy(); win = None
    finally:
        if win is not None:
            try: win.destroy()
            except Exception: pass
        app.destroy()


def test_dialog_save_creates_closes_and_opens_patient():
    app = _make_app()
    if app is None:
        print("SKIP test_dialog_save_creates_closes_and_opens_patient (no display)"); return
    fid = None
    caps, restore = _patch_msgs()
    try:
        win = app.new_patient(); app.update()
        _fill(win.form, "R17Modal", "R17Dad", "R17Fam")
        win.form.save(); app.update()
        assert not caps["error"], caps["error"]
        assert not win.winfo_exists(), "dialog did not close after save"
        assert app.current_patient is not None
        fid = app.current_patient["file_number"]
        assert _count_names("R17Modal", "R17Dad", "R17Fam") == 1
        # patient_id comes from the Treeview values in the shell flow,
        # so it is the fid as a string there.
        assert str(app.clinical.patient_id) == str(fid), "clinical tab did not load him"
        # Round 20: the name shows in the shell's far-left info panel (R21: info_text() joins its per-line labels).
        assert "R17Modal" in app.info_panel.info_text()
    finally:
        restore(); app.destroy(); _cleanup(fid)


def test_dialog_duplicate_decline_then_open_existing():
    app = _make_app()
    if app is None:
        print("SKIP test_dialog_duplicate_decline_then_open_existing (no display)"); return
    fid = save_patient_record({
        "first_name": "R17Dup", "father_name": "R17Dad", "grand_name": "",
        "last_name": "R17Fam", "full_name": "R17Dup R17Dad R17Fam",
        "birth_date_greg": "1990-05-15", "birth_date_hijri": "",
        "age_years": 0, "age_months": 0, "age_days": 0, "age_total_days": 0,
        "age_hijri_years": 0, "age_hijri_months": 0, "age_hijri_days": 0,
        "mobile1": "", "mobile2": "", "emergency_phone": "", "address": "",
        "nationality": "Syrian", "current_medications": "", "allergies": "",
        "diseases": ""})
    win = None
    try:
        caps, restore = _patch_msgs(ask_answer=False)
        try:
            win = app.new_patient(); app.update()
            _fill(win.form, "R17Dup", "R17Dad", "R17Fam", birth="01/01/2001")
            win.form.save(); app.update()
            assert caps["ask"], "duplicate prompt not shown from the dialog"
            assert str(fid) in caps["ask"][0][1], caps["ask"]
            assert win.winfo_exists(), "declining closed the dialog"
            assert _count_names("R17Dup", "R17Dad", "R17Fam") == 1
            caps["ask_answer"] = True
            win.form.save(); app.update()
            assert not win.winfo_exists(), "accepting did not close the dialog"
            win = None
            assert app.current_patient["file_number"] == fid
            assert _count_names("R17Dup", "R17Dad", "R17Fam") == 1
        finally:
            restore()
    finally:
        if win is not None:
            try: win.destroy()
            except Exception: pass
        app.destroy(); _cleanup(fid)
