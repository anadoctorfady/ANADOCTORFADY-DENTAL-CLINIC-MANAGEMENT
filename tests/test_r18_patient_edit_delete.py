"""Round 18 worker W2: patient Edit in a modal dialog (edit mode).

Migration adds patients.deleted; open_edit_patient_dialog() reuses
PatientForm.fill/save -- updates the SAME file, the duplicate
check excludes self, diseases/meds/allergies persist -- and
returns None for a soft-deleted or missing patient. The delete
tests live in tests.test_r18_patient_delete (helpers _row /
_count / _patch_msgs / _StubApp below are shared with it).
GUI tests skip with no display; run with DISPLAY=:98 under Xvfb.
"""
import tkinter as tk
import tkinter.messagebox as _mb
from types import SimpleNamespace

from src.models.database import get_connection, init_db
from src.models.patients import search_patients, soft_delete_patient
from tests.test_r18_search_phone import _cleanup, _ids, _seed


def _row(fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE file_number=?", (fid,))
    r = cur.fetchone(); row = dict(r) if r else None; conn.close()
    return row


def _count(table, fid):
    conn = get_connection()
    n = conn.execute(f"SELECT COUNT(*) FROM {table} "
                     "WHERE patient_file=?", (fid,)).fetchone()[0]
    conn.close(); return n


def _patch_msgs(ask=True):
    caps = {"error": [], "info": [], "warn": [], "ask": [], "ask_answer": ask}
    orig = (_mb.showerror, _mb.showinfo, _mb.showwarning, _mb.askyesno)
    _mb.showerror = lambda *a, **k: caps["error"].append(a)
    _mb.showinfo = lambda *a, **k: caps["info"].append(a)
    _mb.showwarning = lambda *a, **k: caps["warn"].append(a)
    _mb.askyesno = lambda *a, **k: caps["ask"].append(a) or caps["ask_answer"]

    def restore():
        (_mb.showerror, _mb.showinfo, _mb.showwarning, _mb.askyesno) = orig
    return caps, restore


def test_migration_adds_deleted_column():
    init_db(); init_db()  # idempotent
    conn = get_connection()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(patients)")]
    conn.close(); assert "deleted" in cols


class _StubApp:
    """Minimal app surface for PatientForm / dialog / info panel."""

    def __init__(self, role="admin", lang="en"):
        self.lang = lang; self.current_role = role
        self.current_patient = None; self.loaded = 0; self.selected = None
        self.clinical = SimpleNamespace(clear=lambda: None)
        self.appt = SimpleNamespace(load=lambda: None)

    def load_patients(self): self.loaded += 1
    def select_patient(self, fid): self.selected = fid
    def print_pdf(self): pass


def _set(entry, val):
    entry.delete(0, tk.END)
    if val: entry.insert(0, val)


def test_edit_dialog_updates_and_persists():
    """Real edit dialog: fill shows the patient; saving with the
    name UNCHANGED does not trip the duplicate check (self
    excluded); edits persist into the SAME file; dialog closes."""
    init_db()
    fid = _seed("R18Ed", "R18Dad", "R18Gpa", "R18Fam", m1="0912000444")
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        _cleanup(fid); print("SKIP edit_dialog (no display)"); return
    from src.ui.patient_dialog import open_edit_patient_dialog
    app = _StubApp(); caps, restore = _patch_msgs()
    try:
        win = open_edit_patient_dialog(app, fid, parent=root)
        assert win is not None; root.update_idletasks()
        form = win.form
        assert form.e_first.get() == "R18Ed"
        assert form.e_grand.get() == "R18Gpa"
        form.save()  # unchanged name: no duplicate error, still saves
        root.update_idletasks()
        assert not caps["error"], caps["error"]
        assert not win.winfo_exists(), "dialog stayed open after save"
        win = open_edit_patient_dialog(app, fid, parent=root); form = win.form
        _set(form.e_first, "R18Ed2"); _set(form.e_m1, "0999888777")
        _set(form.e_diseases, "Diabetes"); _set(form.e_meds, "Metformin")
        _set(form.e_allergies, "Penicillin"); _set(form.e_addr, "Damascus")
        form.save(); root.update_idletasks()
        assert not caps["error"], caps["error"]
        assert not win.winfo_exists()
        assert app.selected == fid and app.loaded >= 1
        row = _row(fid)
        assert row["first_name"] == "R18Ed2", row
        assert row["full_name"].startswith("R18Ed2 R18Dad"), row
        assert row["mobile1"] == "0999888777"
        assert row["diseases"] == "Diabetes"
        assert row["current_medications"] == "Metformin"
        assert row["allergies"] == "Penicillin"
        assert row["address"] == "Damascus"
        assert fid in _ids(search_patients(phone="+963999888777"))
    finally:
        restore(); root.destroy(); _cleanup(fid)


def test_edit_dialog_none_for_deleted():
    """Edit dialog returns None (opens nothing) for a soft-deleted
    or missing patient."""
    init_db()
    fid = _seed("R18Gone", "R18Dad", "R18Gpa", "R18Fam")
    soft_delete_patient(fid)
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        _cleanup(fid); print("SKIP edit_dialog_none (no display)"); return
    from src.ui.patient_dialog import open_edit_patient_dialog
    try:
        assert open_edit_patient_dialog(_StubApp(), fid, parent=root) is None
        assert open_edit_patient_dialog(_StubApp(), 999999, parent=root) is None
    finally:
        root.destroy(); _cleanup(fid)
