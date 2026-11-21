"""Round 23 (item 8): a referral made by the NURSE does not appear.

Reproduction (isolated gate DB, DISPLAY=:98): as a nurse, the local
save + History display actually worked -- the row was written and
tree_ref showed it after refresh_clinical(). The broken layer was
SYNC: add_referral queued nothing, so the referral never left the
nurse's device and the receiving doctor (another device) never
saw it. These tests pin the nurse workflow end to end through the
REAL Refer dialog: nurse-authored internal referral is written,
visible in the patient's history data + real ClinicalTab tree,
AND queued for sync with author = the nurse.
GUI tests skip with no display."""
import json
import tkinter as tk

from src.models.database import get_connection, init_db
from src.models.referrals import list_referrals
from src.models.sync import pending_changes
from src.ui.clinical_referrals import history_rows
from src.utils.auth import hash_pw
from tests.test_r18_patient_edit_delete import _patch_msgs, _row
from tests.test_r18_search_phone import _cleanup, _seed

NURSE = "r23_nurse"


def _ensure_nurse():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users(username,password_hash,"
                "role,created_at) VALUES(?,?,?,datetime('now'))",
                (NURSE, hash_pw("nursepass"), "nurse"))
    conn.commit(); conn.close()


def _cleanup_refs(*fids):
    conn = get_connection(); cur = conn.cursor()
    for fid in fids:
        ids = [r[0] for r in cur.execute(
            "SELECT id FROM referrals WHERE patient_id=?", (fid,))]
        for rid in ids:
            cur.execute("DELETE FROM sync_queue WHERE table_name="
                        "'referrals' AND record_id=?",
                        (f"referrals:{rid}",))
        cur.execute("DELETE FROM referrals WHERE patient_id=?", (fid,))
    conn.commit(); conn.close(); _cleanup(*fids)


class _NurseApp:
    """Stub app surface for the refer dialog, logged in as nurse."""

    def __init__(self, patient=None):
        self.lang = "en"; self.current_role = "nurse"
        self.current_user = NURSE; self.current_patient = patient
        self.refreshed = 0

    def refresh_clinical(self): self.refreshed += 1
    def load_patients(self): pass


def _tk():
    try:
        root = tk.Tk(); root.withdraw(); return root
    except tk.TclError:
        return None


def test_nurse_dialog_internal_referral_written_and_queued():
    root = _tk()
    if root is None:
        print("SKIP nurse_dialog (no display)"); return
    _ensure_nurse()
    fid = _seed("R23Nu", "R23Dad", "R23Gpa", "R23Fam")
    from src.ui.refer_dialog import open_refer_dialog
    app = _NurseApp(patient=_row(fid)); caps, restore = _patch_msgs()
    try:
        win = open_refer_dialog(app, parent=root)
        assert win is not None and win.patient_id == fid
        root.update_idletasks()
        doctors = list(win.cb_doctor.cget("values"))
        assert doctors, "no internal doctors offered"
        assert NURSE not in doctors  # nurses are not treating doctors
        target = "doc2" if "doc2" in doctors else doctors[0]
        win.doctor_var.set(target)
        win.note_text.insert("1.0", "Nurse sends for implant consult")
        assert win.save() is True
        root.update_idletasks()
        assert not caps["error"], caps["error"]
        assert app.refreshed >= 1  # history refresh requested
        rows = list_referrals(fid)
        assert len(rows) == 1, rows
        row = rows[0]
        assert row["from_user"] == NURSE  # authored by the nurse
        assert row["to_doctor"] == target
        assert row["note"] == "Nurse sends for implant consult"
        # Visible in the patient's history data (what the tree shows).
        hist = history_rows(fid)
        assert len(hist) == 1 and hist[0][1] == target
        assert hist[0][2] == NURSE and hist[0][3] == row["note"]
        # R23 fix: the referral is QUEUED for sync (it was not
        # before, so it never reached the doctor's device).
        conn = get_connection()
        pend = [p for p in pending_changes(conn)
                if p["table_name"] == "referrals"
                and p["record_id"] == f"referrals:{row['id']}"]
        conn.close()
        assert len(pend) == 1, pend
        payload = json.loads(pend[0]["payload_json"])
        assert payload["patient_file"] == str(fid)
        assert payload["from_user"] == NURSE
        assert payload["author"] == NURSE
        assert payload["to_doctor"] == target
        assert payload["note"] == "Nurse sends for implant consult"
        assert payload["updated_at"] == payload["created_at"]
    finally:
        restore(); root.destroy(); _cleanup_refs(fid)


class _TabApp:
    """Stub app whose refresh_clinical reloads the real tab,
    exactly like the shell's refresh_clinical()."""

    lang = "en"

    def __init__(self, patient):
        self.current_patient = patient
        self.current_user = NURSE; self.current_role = "nurse"
        self.tab = None

    def chart_teeth(self): return []

    def refresh_clinical(self):
        if self.tab is not None and self.current_patient:
            self.tab.load(self.current_patient["file_number"])


def test_nurse_referral_visible_in_clinical_history_tree():
    root = _tk()
    if root is None:
        print("SKIP nurse_tree (no display)"); return
    _ensure_nurse()
    fid = _seed("R23Tree", "R23Dad", "R23Gpa", "R23Fam")
    from src.ui.clinical import ClinicalTab
    from src.ui.refer_dialog import open_refer_dialog
    app = _TabApp(_row(fid)); caps, restore = _patch_msgs()
    try:
        tab = ClinicalTab(root, app); tab.pack(); app.tab = tab
        root.update_idletasks(); tab.load(fid); root.update_idletasks()
        assert tab.tree_ref.get_children() == ()
        win = open_refer_dialog(app, parent=root)
        root.update_idletasks()
        target = list(win.cb_doctor.cget("values"))[0]
        win.doctor_var.set(target)
        win.note_text.insert("1.0", "Please see this patient today")
        assert win.save() is True
        root.update_idletasks()  # save -> refresh_clinical -> tab.load
        assert not caps["error"], caps["error"]
        vals = [tab.tree_ref.item(i, "values")
                for i in tab.tree_ref.get_children()]
        assert any(v[1] == target and v[2] == NURSE
                   and v[3] == "Please see this patient today"
                   for v in vals), vals
    finally:
        restore(); root.destroy(); _cleanup_refs(fid)
