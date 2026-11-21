"""Job 3 (round 12): clinical layout + save gate + 24h-rule data.

(a) Notes persist with the visit (complaints.notes /
    symptoms_notes, diagnoses.notes, procedures.notes). Round 17:
    the four per-field note entries are ONE visit-notes entry
    (txt_visit_note); its text lands in ALL of those columns.
(b) Saving is BLOCKED until ALL FOUR fields are filled (complaint,
    symptoms, diagnosis, procedure): the bilingual error names the
    missing field(s) and nothing is saved.
(c) Every insert records author (logged-in user) + created_at.
    (d) History Edit/Delete buttons: see test_clinical_history_edit.py.

GUI tests skip gracefully when no display is available; run with
DISPLAY=:99 under Xvfb. DB tests run against the isolated copy
(ANADOCTORFADY_DATA_DIR) and clean up their seeded rows.
"""
import tkinter as tk
from unittest import mock

from src.models.database import get_connection, init_db
from src.ui import clinical_tables
from src.ui.clinical import ClinicalTab


def _stub_app(patient=None, lang="en"):
    class FakeApp:
        current_patient = patient
        current_user = "dr_fady"
        current_role = "doctor"

        def chart_teeth(self):
            return []

        def refresh_clinical(self):
            pass

    FakeApp.lang = lang
    return FakeApp()


def _seed_patient():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,father_name,grand_name,"
                "last_name,full_name,birth_date_greg) "
                "VALUES(?,?,?,?,?,?)",
                ("Gate", "Father", "Grand", "Last",
                 "Gate Father Grand Last", "1990-05-15"))
    fid = cur.lastrowid
    conn.commit(); conn.close()
    return fid


def _cleanup(fid):
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
        conn.commit(); conn.close()
    except Exception:
        pass


def _build_tab(fid, lang="en"):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.withdraw()
    app = _stub_app({"file_number": fid}, lang=lang)
    try:
        tab = ClinicalTab(root, app)
        tab.pack()
        root.update_idletasks()
        return root, tab
    except Exception:
        root.destroy()
        raise


def _fill(tab, complaint="Toothache", symptom="Pain on chewing",
          diagnosis="Pulpitis", procedure="Root canal"):
    for widget, value in ((tab.txt_complaint, complaint),
                          (tab.txt_sym, symptom),
                          (tab.txt_diagnosis, diagnosis),
                          (tab.txt_procedure, procedure)):
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)


def _count(table, fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE patient_file=?", (fid,))
    n = cur.fetchone()[0]
    conn.close()
    return n


def test_save_blocked_names_missing_fields():
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_save_blocked_names_missing_fields (no display)")
        return
    try:
        _fill(tab, complaint="Toothache", symptom="", diagnosis="", procedure="")
        with mock.patch.object(clinical_tables.messagebox, "showerror") as err:
            clinical_tables.add(tab, "complaint")
        assert err.called, "blocked save showed no error"
        msg = err.call_args[0][1]
        for name in ("Symptoms", "Diagnosis", "Procedure"):
            assert name in msg, f"missing field not named: {name} in {msg!r}"
        assert "Complaint" not in msg, "filled field wrongly named missing"
        assert _count("complaints", fid) == 0, "blocked save wrote a row"
    finally:
        root.destroy()
        _cleanup(fid)


def test_save_blocked_message_arabic():
    fid = _seed_patient()
    root, tab = _build_tab(fid, lang="ar")
    if tab is None:
        _cleanup(fid)
        print("SKIP test_save_blocked_message_arabic (no display)")
        return
    try:
        _fill(tab, complaint="", symptom="", diagnosis="Pulpitis", procedure="")
        with mock.patch.object(clinical_tables.messagebox, "showerror") as err:
            clinical_tables.add(tab, "diagnosis")
        assert err.called
        msg = err.call_args[0][1]
        for name in ("الشكوى", "الأعراض", "الإجراء"):
            assert name in msg, f"missing field not named in AR: {name} in {msg!r}"
        assert _count("diagnoses", fid) == 0
    finally:
        root.destroy()
        _cleanup(fid)


def test_full_visit_saves_notes_author_created_at():
    fid = _seed_patient()
    root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid)
        print("SKIP test_full_visit_saves_notes_author_created_at (no display)")
        return
    try:
        _fill(tab)
        # Round 17: ONE visit note, written to every notes column.
        tab.txt_visit_note.insert("1.0", "visit note")
        with mock.patch.object(clinical_tables.messagebox, "showerror") as err:
            clinical_tables.add(tab, "complaint")
            clinical_tables.add(tab, "diagnosis")
            clinical_tables.add(tab, "procedure")
        assert not err.called, f"full visit should save, got: {err.call_args}"
        conn = get_connection(); cur = conn.cursor()
        row = cur.execute("SELECT * FROM complaints WHERE patient_file=?",
                          (fid,)).fetchone()
        assert row["notes"] == "visit note", dict(row)
        assert row["symptoms_notes"] == "visit note", dict(row)
        assert row["symptoms"] == "Pain on chewing", dict(row)
        assert row["author"] == "dr_fady", dict(row)
        assert row["created_at"], dict(row)
        row = cur.execute("SELECT * FROM diagnoses WHERE patient_file=?",
                          (fid,)).fetchone()
        assert row["notes"] == "visit note", dict(row)
        assert row["author"] == "dr_fady" and row["created_at"], dict(row)
        row = cur.execute("SELECT * FROM procedures WHERE patient_file=?",
                          (fid,)).fetchone()
        assert row["notes"] == "visit note", dict(row)
        assert row["author"] == "dr_fady" and row["created_at"], dict(row)
        conn.close()
        # Saved fields (and the visit note) are cleared for the next visit.
        assert tab.txt_complaint.get("1.0", tk.END).strip() == ""
        assert tab.txt_visit_note.get("1.0", tk.END).strip() == ""
        assert tab.txt_sym.get("1.0", tk.END).strip() == ""
    finally:
        root.destroy()
        _cleanup(fid)
