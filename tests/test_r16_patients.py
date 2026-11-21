"""Round 16 worker A (patients): diseases field + form lifecycle
(round 17: the form lives only in the modal dialog -- always visible,
no collapse, no chart; see the two lifecycle tests below).

Helpers (_attempt etc.) are shared by test_r16_patients_search and
test_r16_patients_dup. Exercises the REAL PatientForm.save().
Seeded rows are cleaned up. GUI tests skip with no display; run
with DISPLAY=:98 under Xvfb. NOTE: run_tests.py must gain the three
test_r16_patients* names in its TESTS list (coordinator merge).
"""
import tkinter as tk
import tkinter.messagebox as _mb

from src.config.strings import EN as _STR_EN, AR as _STR_AR
from src.config.strings_r16_patients import EN as _R16_EN, AR as _R16_AR
_STR_EN.update(_R16_EN); _STR_AR.update(_R16_AR)
from src.models.database import get_connection, init_db
from src.models.patients import save_patient_record
from src.ui.patient_form import PatientForm

BIRTH = "15/05/1990"


class _FakeApp:
    lang = "en"

    def __init__(self, lang="en", patient=None):
        self.lang = lang; self.current_patient = patient
        self.loaded = 0; self.selected = None
    def on_teeth_select(self, teeth, typ):
        pass
    def print_pdf(self):
        pass
    def load_patients(self):
        self.loaded += 1
    def select_patient(self, fid):
        self.selected = fid


def _patch_msgs(ask_answer=False):
    caps = {"error": [], "info": [], "ask": [], "ask_answer": ask_answer}
    orig = (_mb.showerror, _mb.showinfo, _mb.askyesno)
    _mb.showerror = lambda *a, **k: caps["error"].append(a)
    _mb.showinfo = lambda *a, **k: caps["info"].append(a)
    _mb.askyesno = lambda *a, **k: caps["ask"].append(a) or caps["ask_answer"]
    return caps, lambda: [setattr(_mb, n, f)
                          for n, f in zip(("showerror", "showinfo", "askyesno"), orig)]


def _set(entry, val):
    entry.delete(0, tk.END)
    if val:
        entry.insert(0, val)


def _count():
    conn = get_connection(); n = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]; conn.close(); return n


def _row(fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE file_number=?", (fid,))
    r = cur.fetchone(); row = dict(r) if r else None; conn.close(); return row


def _cleanup(fid):
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
        conn.commit(); conn.close()
    except Exception:
        pass


def _seed(first, father, last, grand="", birth="1990-05-15", m1="",
          m2="", em="", diseases=""):
    return save_patient_record({
        "first_name": first, "father_name": father, "grand_name": grand, "last_name": last,
        "full_name": " ".join(p for p in (first, father, grand, last) if p),
        "birth_date_greg": birth, "birth_date_hijri": "", "age_years": 0, "age_months": 0,
        "age_days": 0, "age_total_days": 0, "age_hijri_years": 0, "age_hijri_months": 0,
        "age_hijri_days": 0, "mobile1": m1, "mobile2": m2, "emergency_phone": em,
        "address": "", "nationality": "Syrian", "current_medications": "",
        "allergies": "", "diseases": diseases})


def _attempt(first, father, grand, last, birth=BIRTH, lang="en",
             patient=None, fill_row=None, diseases="", ask_answer=False,
             m1="", m2="", em=""):
    """Build the real form (via the "+ New Patient" flow), fill it,
    call save(), return the outcome (None when there is no display)."""
    init_db(); before = _count()
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw()
    app = _FakeApp(lang, patient)
    form = PatientForm(root, app); form.pack(); root.update_idletasks()
    caps, restore = _patch_msgs(ask_answer)
    try:
        if fill_row is not None:
            form.fill(fill_row); _set(form.e_diseases, diseases)
        else:
            form.show_new()
            _set(form.e_first, first); _set(form.e_father, father)
            _set(form.e_grand, grand); _set(form.e_last, last)
            _set(form.e_birth, birth); _set(form.e_m1, m1)
            _set(form.e_m2, m2); _set(form.e_em, em)
            _set(form.e_diseases, diseases)
        form.save(); root.update_idletasks()
        return {"errors": [a[1] for a in caps["error"]], "infos": caps["info"],
                "ask": caps["ask"], "selected": app.selected, "loaded": app.loaded,
                "before": before, "after": _count(), "collapsed": form._collapsed}
    finally:
        restore(); root.destroy()


def _cols():
    c = get_connection(); cols = [r[1] for r in c.execute("PRAGMA table_info(patients)").fetchall()]; c.close(); return cols


def test_migration_adds_diseases_column():
    """A pre-round-16 DB (no diseases column) gains it via init_db(),
    idempotently, without losing a saved diseases value."""
    init_db(); assert "diseases" in _cols()
    conn = get_connection()
    conn.execute("ALTER TABLE patients DROP COLUMN diseases")
    conn.commit(); conn.close()
    assert "diseases" not in _cols()
    init_db(); assert "diseases" in _cols()
    fid = _seed("R16Mig", "R16Dad", "R16Fam", diseases="Diabetes")
    try:
        assert _row(fid)["diseases"] == "Diabetes"
        init_db(); init_db()  # second run: still there, value kept
        assert "diseases" in _cols()
        assert _row(fid)["diseases"] == "Diabetes"
    finally:
        _cleanup(fid)


def test_diseases_save_persists_and_reloads():
    """Diseases typed on the form is stored and comes back in fill()."""
    got = _attempt("R16Dis", "R16Dad", "", "R16Fam",
                   diseases="Diabetes, Hypertension")
    if got is None:
        print("SKIP test_diseases_save_persists_and_reloads (no display)"); return
    fid = got["selected"]
    try:
        assert not got["errors"], got["errors"]
        assert fid is not None
        assert _row(fid)["diseases"] == "Diabetes, Hypertension", _row(fid)
        root = tk.Tk(); root.withdraw()
        form = PatientForm(root, _FakeApp()); form.pack(); root.update_idletasks()
        try:
            form.fill(_row(fid))
            assert form.e_diseases.get() == "Diabetes, Hypertension"
        finally:
            root.destroy()
    finally:
        if fid: _cleanup(fid)


def test_form_visible_immediately_no_placeholder_no_chart():
    """Round 17: the form exists only inside the modal new-patient
    dialog, so it is visible immediately -- no collapsed placeholder,
    no '+ New Patient' placeholder button, and NO dental chart."""
    init_db()
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_form_visible_immediately_no_placeholder_no_chart (no display)"); return
    root.withdraw()
    form = PatientForm(root, _FakeApp()); form.pack(); root.update_idletasks()
    try:
        assert form._collapsed is False
        assert form._canvas.winfo_manager() == "pack"
        assert not hasattr(form, "_placeholder")
        assert not hasattr(form, "chart")
    finally:
        root.destroy()


def test_form_save_opens_patient_without_collapse():
    """Round 17: after a successful save the form does NOT collapse
    (in the dialog, the dialog closes via on_saved instead); the app
    is asked to load + select the new patient."""
    got = _attempt("R16Col", "R16Dad", "", "R16Fam")
    if got is None:
        print("SKIP test_form_save_opens_patient_without_collapse (no display)"); return
    try:
        assert not got["errors"], got["errors"]
        assert got["selected"] is not None
        assert got["loaded"] >= 1
        assert got["collapsed"] is False, "form collapsed after save (round 17: dialog closes instead)"
    finally:
        if got["selected"]: _cleanup(got["selected"])


