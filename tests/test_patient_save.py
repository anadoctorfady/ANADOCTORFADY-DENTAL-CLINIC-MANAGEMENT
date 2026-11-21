"""Round 15: patient-save bug -- grandfather is OPTIONAL.

Regression tests for the confirmed bug in PatientForm.save():
`if not all([first, father, grand, last])` refused to save any new
patient without a grandfather name, so such a patient never got a
file number. Now only first + father + last are required, full_name
joins only the non-empty parts, and a missing required name is
refused with a message NAMING the missing field(s).

All tests exercise the REAL PatientForm.save() handler (not a
helper). The new strings module is merged into t() here exactly as
strings.py will do once the coordinator wires it. GUI tests skip
gracefully with no display; run with DISPLAY=:98 under Xvfb.
Seeded rows are cleaned up.
"""
import tkinter as tk
import tkinter.messagebox as _mb

from src.config.strings import EN as _STR_EN, AR as _STR_AR
from src.config.strings_r15_patient import EN as _R15_EN, AR as _R15_AR
_STR_EN.update(_R15_EN); _STR_AR.update(_R15_AR)
from src.models.database import get_connection, init_db
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


def _patch_msgs():
    caps = {"error": [], "info": []}
    orig = (_mb.showerror, _mb.showinfo)
    _mb.showerror = lambda *a, **k: caps["error"].append(a)
    _mb.showinfo = lambda *a, **k: caps["info"].append(a)
    return caps, lambda: [setattr(_mb, n, f)
                          for n, f in zip(("showerror", "showinfo"), orig)]


def _set(entry, val):
    entry.delete(0, tk.END)
    if val:
        entry.insert(0, val)


def _count():
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
    conn.close(); return n


def _row(fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE file_number=?", (fid,))
    row = dict(cur.fetchone()); conn.close(); return row


def _cleanup(fid):
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
        conn.commit(); conn.close()
    except Exception:
        pass


def _attempt(first, father, grand, last, birth=BIRTH, lang="en",
             patient=None, fill_row=None):
    """Build the real form, fill it, call save(), return the outcome
    (None when there is no display -- caller then SKIPs)."""
    init_db(); before = _count()
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw()
    app = _FakeApp(lang, patient)
    form = PatientForm(root, app); form.pack(); root.update_idletasks()
    caps, restore = _patch_msgs()
    try:
        if fill_row is not None:
            form.fill(fill_row)
        else:
            _set(form.e_first, first); _set(form.e_father, father)
            _set(form.e_grand, grand); _set(form.e_last, last)
            _set(form.e_birth, birth)
        form.save(); root.update_idletasks()
        return {"errors": [a[1] for a in caps["error"]],
                "infos": caps["info"], "selected": app.selected,
                "before": before, "after": _count()}
    finally:
        restore(); root.destroy()


def _refused(first, father, grand, last, needle, birth=BIRTH, lang="en"):
    """Save must be refused, name `needle`, and insert no row."""
    got = _attempt(first, father, grand, last, birth=birth, lang=lang)
    if got is None:
        return None
    assert got["errors"], "save was not refused"
    assert needle in got["errors"][0], got["errors"]
    assert got["after"] == got["before"], "refused save inserted a row"
    assert got["selected"] is None
    return got


def test_save_empty_grandfather_succeeds():
    """(a)+(d) Empty grandfather saves, gets a file number, and the stored
    full_name has no double space: 'Sami Mohammed Hassan' (r16: must not match live file #1)."""
    got = _attempt("Sami", "Mohammed", "", "Hassan")
    if got is None:
        print("SKIP test_save_empty_grandfather_succeeds (no display)"); return
    fid = got["selected"]
    try:
        assert not got["errors"], got["errors"]
        assert fid is not None, "no file number assigned"
        assert got["after"] == got["before"] + 1
        row = _row(fid)
        assert row["full_name"] == "Sami Mohammed Hassan", row["full_name"]
        assert "  " not in row["full_name"]
        assert row["grand_name"] == ""
        assert got["infos"], "no saved confirmation shown"
    finally:
        if fid: _cleanup(fid)


def test_save_empty_first_refused_naming_field():
    """(b) Empty first name is refused; the error names 'First Name'."""
    got = _refused("", "Mohammed", "", "Hassan", "First Name")
    if got is None:
        print("SKIP test_save_empty_first_refused_naming_field (no display)")


def test_save_empty_last_refused_naming_field():
    """(c) Empty last name is refused; the error names the last name."""
    got = _refused("Ahmed", "Mohammed", "", "", "Last")
    if got is None:
        print("SKIP test_save_empty_last_refused_naming_field (no display)")


def test_save_empty_father_refused_naming_field():
    """Empty father name is refused; the error names 'Father'."""
    got = _refused("Ahmed", "", "Saeed", "Hassan", "Father")
    if got is None:
        print("SKIP test_save_empty_father_refused_naming_field (no display)")


def test_save_missing_fields_named_in_arabic():
    """Missing first + last names are both named in Arabic."""
    got = _attempt("", "Mohammed", "", "", lang="ar")
    if got is None:
        print("SKIP test_save_missing_fields_named_in_arabic (no display)"); return
    assert got["errors"], "empty names were not refused (ar)"
    msg = got["errors"][0]
    assert "الاسم الأول" in msg, msg
    assert "الكنية" in msg, msg
    assert got["after"] == got["before"]


def test_save_empty_birth_date_refused():
    """Empty birth date is still refused (pre-existing rule, kept)."""
    got = _refused("Ahmed", "Mohammed", "", "Hassan", "Birth date", birth="")
    if got is None:
        print("SKIP test_save_empty_birth_date_refused (no display)")


def test_existing_four_name_patient_full_name_unchanged():
    """(e) A patient seeded with all four names keeps the identical
    stored full_name after re-saving through the real form."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,father_name,grand_name,"
                "last_name,full_name,birth_date_greg) VALUES(?,?,?,?,?,?)",
                ("Khaled", "Omar", "Saeed", "Nasser",
                 "Khaled Omar Saeed Nasser", "1990-05-15"))
    fid = cur.lastrowid; conn.commit(); conn.close()
    before = _row(fid)["full_name"]
    assert before == "Khaled Omar Saeed Nasser", before
    got = _attempt("", "", "", "", patient={"file_number": fid},
                   fill_row=_row(fid))
    if got is None:
        _cleanup(fid)
        print("SKIP test_existing_four_name_patient_full_name_unchanged (no display)"); return
    try:
        assert not got["errors"], got["errors"]
        assert got["selected"] == fid
        assert _row(fid)["full_name"] == before, _row(fid)
    finally:
        _cleanup(fid)
