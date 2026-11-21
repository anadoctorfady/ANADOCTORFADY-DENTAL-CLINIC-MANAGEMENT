"""Round 19 (item 11): refer patient to another doctor. Model:
referrals table via the late-schema ensure pattern (idempotent);
add/list newest first. Dialog (real GUI, gate env): internal save,
external save (external wins), no-doctor error, Templates picker
('referral') inserting EN-only text in EN mode. Display: referral
in the clinical history tree + history_rows data. No-patient:
dialog refuses, Refer disabled. GUI tests skip with no display."""
import re
import tkinter as tk
from src.models.database import (get_connection, get_setting,
                                 init_db, set_setting)
from src.models.referrals import add_referral, list_referrals
from src.ui.clinical_referrals import history_rows
from tests.test_clinical_save_gate import _build_tab
from tests.test_r18_patient_edit_delete import _patch_msgs, _row
from tests.test_r18_search_phone import _cleanup, _seed

_AR_RE = re.compile(r"[؀-ۿ]")
SEED_EN = "Referred to another doctor to continue treatment"
def _cleanup_refs(*fids):
    conn = get_connection(); cur = conn.cursor()
    for fid in fids:
        cur.execute("DELETE FROM referrals WHERE patient_id=?", (fid,))
    conn.commit(); conn.close(); _cleanup(*fids)
class _App:
    """Stub app surface for the refer dialog / info panel."""
    def __init__(self, patient=None, lang="en"):
        self.lang = lang; self.current_role = "doctor"
        self.current_user = "fady"; self.current_patient = patient
        self.refreshed = 0
    def refresh_clinical(self): self.refreshed += 1
    def load_patients(self): pass
def _tk():
    try:
        root = tk.Tk(); root.withdraw(); return root
    except tk.TclError:
        return None
def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)
def test_schema_idempotent_and_columns():
    init_db(); init_db()  # idempotent
    conn = get_connection(); cols = [r[1] for r in conn.execute("PRAGMA table_info(referrals)")]; conn.close()
    assert cols == ["id", "patient_id", "from_user", "to_doctor",
                    "note", "created_at"], cols
def test_model_add_and_list_newest_first():
    init_db()
    fid = _seed("R19Mod", "R19Dad", "R19Gpa", "R19Fam")
    try:
        assert add_referral(fid, "fady", "", "x") is None
        assert add_referral(None, "fady", "dr_a", "x") is None
        assert list_referrals(None) == []
        r1 = add_referral(fid, "fady", "dr_internal", "first note")
        r2 = add_referral(fid, "nurse1", "Dr External", "second note")
        assert r1 and r2 and r2 > r1
        rows = list_referrals(fid)
        assert [r["id"] for r in rows] == [r2, r1]  # newest first
        assert rows[0]["to_doctor"] == "Dr External"
        assert rows[0]["from_user"] == "nurse1"
        assert rows[1]["note"] == "first note"
        assert rows[0]["created_at"]  # stamped, defaults to now
        assert list_referrals(999999) == []
    finally:
        _cleanup_refs(fid)
def test_dialog_internal_doctor_save():
    root = _tk()
    if root is None:
        print("SKIP dialog_internal (no display)"); return
    fid = _seed("R19In", "R19Dad", "R19Gpa", "R19Fam")
    from src.ui.refer_dialog import open_refer_dialog
    app = _App(patient=_row(fid)); caps, restore = _patch_msgs()
    try:
        win = open_refer_dialog(app, parent=root)
        assert win is not None and win.patient_id == fid
        root.update_idletasks()
        assert "fady" in list(win.cb_doctor.cget("values"))
        win.doctor_var.set("fady")
        win.note_text.insert("1.0", "Please evaluate implants")
        assert win.save() is True
        root.update_idletasks()
        # R24 SUPERSEDES R19 auto-close (`assert not win.winfo_exists()`).
        assert win.winfo_exists() and str(win.btn_print.cget("state")) == "normal"
        assert not caps["error"], caps["error"]
        rows = list_referrals(fid)
        assert len(rows) == 1 and rows[0]["to_doctor"] == "fady" and win.saved_referral_id == rows[0]["id"]  # R24: stays open to print
        assert rows[0]["from_user"] == "fady"  # logged-in username
        assert rows[0]["note"] == "Please evaluate implants"
        assert app.refreshed >= 1  # history refresh requested
    finally:
        restore(); root.destroy(); _cleanup_refs(fid)
def test_dialog_external_name_save_and_no_doctor_error():
    root = _tk()
    if root is None:
        print("SKIP dialog_external (no display)"); return
    fid = _seed("R19Ex", "R19Dad", "R19Gpa", "R19Fam")
    from src.ui.refer_dialog import open_refer_dialog
    app = _App(patient=_row(fid)); caps, restore = _patch_msgs()
    try:
        win = open_refer_dialog(app, parent=root)
        root.update_idletasks()
        win.doctor_var.set("")  # no doctor -> error, stays open
        assert win.save() is False
        assert caps["error"] and win.winfo_exists()
        assert list_referrals(fid) == []
        win.ext_check.invoke()  # external mode: combobox disabled
        root.update_idletasks()
        assert "disabled" in tuple(win.cb_doctor.state())
        win.ext_entry.insert(0, "Dr. Sami Haddad")
        win.note_text.insert("1.0", "External ortho opinion")
        assert win.chosen_doctor() == "Dr. Sami Haddad"  # ext wins
        assert win.save() is True
        rows = list_referrals(fid)
        assert len(rows) == 1 and rows[0]["to_doctor"] == "Dr. Sami Haddad"
        assert rows[0]["from_user"] == "fady"
    finally:
        restore(); root.destroy(); _cleanup_refs(fid)
def test_dialog_template_insert_single_language():
    root = _tk()
    if root is None:
        print("SKIP dialog_template (no display)"); return
    fid = _seed("R19Tpl", "R19Dad", "R19Gpa", "R19Fam")
    from src.ui.phrase_picker import open_template_picker
    from src.ui.refer_dialog import open_refer_dialog
    prev = get_setting("language", "en"); set_setting("language", "en")
    try:
        win = open_refer_dialog(_App(patient=_row(fid)), parent=root)
        root.update_idletasks()
        picker = open_template_picker(win, "referral", win.note_text,
                                      "fady", lang="en")
        root.update_idletasks()
        box = next(w for w in _walk(picker) if isinstance(w, tk.Listbox))
        rows = box.get(0, tk.END)
        assert rows, "no referral templates (R19-A seeds missing?)"
        assert not any(_AR_RE.search(r) for r in rows), rows[:3]
        idx = next(i for i, r in enumerate(rows) if SEED_EN.upper() in r)
        box.selection_set(idx)
        ins = next(w for w in _walk(picker) if isinstance(w, tk.Button)
                   and str(w.cget("text")).startswith("Insert"))
        ins.invoke(); root.update_idletasks()
        inserted = win.note_text.get("1.0", tk.END).strip()
        # EN templates insert in ALL CAPS (round 18 rule), EN only.
        assert inserted == SEED_EN.upper(), inserted
        assert not _AR_RE.search(inserted)
        win.destroy()
    finally:
        set_setting("language", prev or "en")
        root.destroy(); _cleanup_refs(fid)
def test_referral_shows_in_history_display():
    init_db()
    fid = _seed("R19Hist", "R19Dad", "R19Gpa", "R19Fam")
    try:
        add_referral(fid, "fady", "dr_hist", "Needs implant consult")
        rows = history_rows(fid)
        assert len(rows) == 1
        date, to_d, from_u, note = rows[0]
        assert to_d == "dr_hist" and from_u == "fady"
        assert note == "Needs implant consult" and len(date) == 10
        root, tab = _build_tab(fid)
        if tab is None:
            print("SKIP history tree (no display)"); return
        try:
            tab.load(fid); root.update_idletasks()
            vals = [tab.tree_ref.item(i, "values")
                    for i in tab.tree_ref.get_children()]
            assert any(v[1] == "dr_hist" and
                       v[3] == "Needs implant consult" for v in vals), vals
            tab.clear(); root.update_idletasks()
            assert tab.tree_ref.get_children() == ()
        finally:
            root.destroy()
    finally:
        _cleanup_refs(fid)
def test_no_patient_handled():
    root = _tk()
    if root is None:
        print("SKIP no_patient (no display)"); return
    from src.ui.patient_info import PatientInfoPanel
    from src.ui.refer_dialog import open_refer_dialog
    try:
        assert open_refer_dialog(_App(patient=None), parent=root) is None
        panel = PatientInfoPanel(root, _App(patient=None))
        panel.pack(); root.update_idletasks()
        assert str(panel.refer_btn.cget("state")) == "disabled"
        panel._refer()  # no-op, must not raise or open anything
        root.update_idletasks()
        assert not [w for w in root.winfo_children()
                    if isinstance(w, tk.Toplevel)]
        fid = _seed("R19Pan", "R19Dad", "R19Gpa", "R19Fam")
        try:
            panel.refresh(_row(fid))
            assert str(panel.refer_btn.cget("state")) == "normal"
            panel.refresh(None)
            assert str(panel.refer_btn.cget("state")) == "disabled"
        finally:
            _cleanup_refs(fid)
    finally:
        root.destroy()
