"""Round 24 (item 1): referral printing. PDF (EN + AR): patient
name + file number, referring doctor, referred-to (internal and
external), note incl. template text, clinic header, app name
exactly once in the footer, NO sadaqah sentence (same forbidden
strings as test_r23_pdf_no_sadaqah), filename
ANADOCTORFADY_REFERRAL_<patient>_<date>.pdf. Empty note + sparse
patient must not crash. GUI (skips without a display): dialog
Print disabled before save / enabled after, dialog stays open;
section Print disabled with no selection / enabled on selection."""
import re, shutil, subprocess, tempfile, tkinter as tk
from pathlib import Path
from src.models.database import (get_connection, get_setting,
                                 init_db, set_setting)
from src.models.referrals import add_referral, get_referral
from src.reports.referral_pdf import (build_referral_pdf, referral_data,
                                      referral_preview_lines)
from src.utils.arabic import ar
from src.utils.helpers import sanitize
from tests.test_r18_patient_edit_delete import _patch_msgs, _row
from tests.test_r18_search_phone import _cleanup, _seed
from tests.test_r19_referrals import _App
from tests.test_r23_pdf_no_sadaqah import _assert_clean
try:
    import arabic_reshaper
except ImportError:
    arabic_reshaper = None
APP_LINE = "ANADOCTORFADY DENTAL CLINIC MANAGEMENT"
CLINIC = "Smile Clinic R24"
_TMP = Path(tempfile.mkdtemp(prefix="r24_refpdf_"))
NOTE = ("Referred to another doctor to continue treatment. "
        "Please evaluate implants.")
def _cleanup_refs(*fids):
    conn = get_connection(); cur = conn.cursor()
    for fid in fids:
        ids = [r[0] for r in cur.execute("SELECT id FROM referrals WHERE patient_id=?", (fid,))]
        for rid in ids:
            cur.execute("DELETE FROM sync_queue WHERE table_name='referrals' AND record_id=?", (f"referrals:{rid}",))
        cur.execute("DELETE FROM referrals WHERE patient_id=?", (fid,))
    conn.commit(); conn.close(); _cleanup(*fids)
class _clinic:
    """Set the clinic_name setting for a block; restore it after."""
    def __enter__(self):
        self.prev = get_setting("clinic_name", ""); set_setting("clinic_name", CLINIC)
    def __exit__(self, *a): set_setting("clinic_name", self.prev or "")
def _pdf_text(path):
    if not shutil.which("pdftotext"): return None
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout
def _ar_in(txt, s):
    """Arabic `s` as extracted PDF text may hold it: logical, reshaped, or reshaped + bidi (utils.arabic.ar)."""
    cands = {s, ar(s)}
    if arabic_reshaper: cands.add(arabic_reshaper.reshape(s))
    return any(c and c in txt for c in cands)
def _check_pdf(path, pat, ref):
    txt = _pdf_text(path)
    if txt is None:
        print("SKIP pdf text (no pdftotext)"); return None
    _assert_clean(txt)  # no sadaqah sentence, EN or AR
    assert txt.count(APP_LINE) == 1, txt[:300]
    assert CLINIC in txt and str(pat["file_number"]) in txt
    assert ref["from_user"] in txt  # Latin username extracts in EN+AR
    return txt
def test_get_referral_and_data():
    init_db(); fid = _seed("R24Get", "R24Dad", "R24Gpa", "R24Fam")
    try:
        rid = add_referral(fid, "fady", "dr_who", "note one")
        ref = get_referral(rid)
        assert ref and ref["id"] == rid and ref["to_doctor"] == "dr_who"
        assert get_referral(999999) is None and get_referral(None) is None
        pat, ref2 = referral_data(rid)
        assert pat["file_number"] == fid and ref2["id"] == rid
        assert referral_data(999999) is None
    finally: _cleanup_refs(fid)
def test_referral_pdf_en_internal_and_external():
    init_db(); fid = _seed("R24En", "R24Dad", "R24Gpa", "R24Fam"); pat = _row(fid)
    try:
        with _clinic():
            for sub, to_d in (("int", "doc_internal"), ("ext", "Dr. Sami Haddad")):
                rid = add_referral(fid, "fady", to_d, NOTE); ref = get_referral(rid)
                out = build_referral_pdf(pat, ref, lang="en", out_path=_TMP / sub)
                name = Path(out).name
                assert name == f"ANADOCTORFADY_REFERRAL_{sanitize(pat['full_name'])}_{ref['created_at'][:10]}.pdf", name
                txt = _check_pdf(out, pat, ref)
                if txt is None: continue
                assert pat["full_name"] in txt and to_d in txt
                assert NOTE in txt and "Patient Referral" in txt
    finally: _cleanup_refs(fid)
def test_referral_pdf_ar():
    init_db(); fid = _seed("R24Ar", "R24Dad", "R24Gpa", "R24Fam"); pat = _row(fid)
    try:
        with _clinic():
            rid = add_referral(fid, "fady", "Dr. Sami Haddad", NOTE); ref = get_referral(rid)
            txt = _check_pdf(build_referral_pdf(pat, ref, lang="ar", out_path=_TMP / "ar1"), pat, ref)
            if txt is not None:
                # Latin values are Helvetica-wrapped in AR docs (_av): they extract as Latin.
                assert "Dr. Sami Haddad" in txt and NOTE in txt
                assert _ar_in(txt, "تحويل مريض")  # the AR title
            # No "د." prefix: pdftotext isolates the Latin period (PDF is fine).
            rid2 = add_referral(fid, "fady", "سامي حداد", "يرجى تقييم زراعة الأسنان")
            out2 = build_referral_pdf(pat, get_referral(rid2), lang="ar", out_path=_TMP / "ar2")
            txt2 = _pdf_text(out2)
            if txt2 is not None:
                _assert_clean(txt2); assert txt2.count(APP_LINE) == 1
                assert _ar_in(txt2, "سامي حداد"), "AR to_doctor"
                assert _ar_in(txt2, "يرجى تقييم زراعة الأسنان"), "AR note"
    finally: _cleanup_refs(fid)
def test_referral_pdf_empty_note_sparse_patient():
    init_db(); fid = _seed("R24Sparse", "R24Dad", "R24Gpa", "R24Fam")
    try:
        rid = add_referral(fid, "fady", "dr_empty", ""); ref = get_referral(rid)
        assert ref["note"] == ""
        sparse = {"file_number": fid}  # no name / optional fields
        for lang in ("en", "ar"):
            out = build_referral_pdf(sparse, ref, lang=lang, out_path=_TMP / f"sparse_{lang}")
            assert Path(out).exists() and Path(out).stat().st_size > 0
        txt = _pdf_text(build_referral_pdf(sparse, ref, lang="en", out_path=_TMP / "sparse_en2"))
        if txt is not None:
            assert "No note recorded." in txt and txt.count(APP_LINE) == 1
        ghost = {"id": 999, "patient_id": 424242, "from_user": "fady", "to_doctor": "dr_x",
                 "note": "", "created_at": "2026-11-17 10:00:00"}
        assert Path(build_referral_pdf({}, ghost, lang="en", out_path=_TMP / "ghost")).exists()
    finally: _cleanup_refs(fid)
def test_referral_preview_lines_en_ar():
    ref = {"id": 5, "patient_id": 321, "from_user": "fady", "to_doctor": "Dr. Sami Haddad",
           "note": NOTE, "created_at": "2026-11-17 09:15:00"}
    pat = {"file_number": 321, "full_name": "Preview Patient"}
    with _clinic():
        for lang in ("en", "ar"):
            lines = referral_preview_lines(pat, ref, lang); joined = "\n".join(lines)
            _assert_clean(joined)
            assert lines[0] == CLINIC and lines[-1] == APP_LINE and joined.count(APP_LINE) == 1
            assert "Dr. Sami Haddad" in joined and "321" in joined
    en = "\n".join(referral_preview_lines(pat, ref, "en", clinic_name=""))
    assert "Patient Referral" in en and NOTE in en
    ar_lines = "\n".join(referral_preview_lines(pat, ref, "ar", clinic_name=""))
    assert "تحويل مريض" in ar_lines  # logical Arabic in preview lines
def _tk():
    try:
        root = tk.Tk(); root.withdraw(); return root
    except tk.TclError: return None
def test_dialog_print_button_lifecycle():
    root = _tk()
    if root is None:
        print("SKIP dialog print (no display)"); return
    fid = _seed("R24Dlg", "R24Dad", "R24Gpa", "R24Fam")
    from src.reports.print_preview import PrintPreview
    from src.ui.refer_dialog import open_refer_dialog
    app = _App(patient=_row(fid)); caps, restore = _patch_msgs()
    try:
        win = open_refer_dialog(app, parent=root); root.update_idletasks()
        assert str(win.btn_print.cget("state")) == "disabled"  # before any save
        assert win.lbl_saved.cget("text") == ""
        win.doctor_var.set("fady"); win.note_text.insert("1.0", "Print me please")
        assert win.save() is True
        root.update_idletasks()
        assert win.winfo_exists()  # R24: stays open after save
        assert str(win.btn_print.cget("state")) == "normal"
        assert win.lbl_saved.cget("text") != ""
        assert str(win.btn_cancel.cget("text")) == "Close"
        rid = win.saved_referral_id
        assert rid and get_referral(rid)["note"] == "Print me please"
        assert not caps["error"], caps["error"]
        win.btn_print.invoke(); root.update_idletasks(); root.update()  # opens the preview
        prevs = [w for w in win.winfo_children() if isinstance(w, PrintPreview)]
        assert prevs, "referral preview did not open"
        prev = prevs[0]; assert prev.pdf_path and Path(prev.pdf_path).exists()
        assert re.match(r"ANADOCTORFADY_REFERRAL_.+_\d{4}-\d{2}-\d{2}\.pdf", Path(prev.pdf_path).name)
        prev.destroy()
        win.btn_cancel.invoke(); root.update_idletasks()  # Close after a save
        assert not win.winfo_exists() and app.refreshed >= 1
    finally: restore(); root.destroy(); _cleanup_refs(fid)
def test_section_print_button_selection():
    from tests.test_clinical_save_gate import _build_tab
    fid = _seed("R24Sec", "R24Dad", "R24Gpa", "R24Fam")
    try:
        rid = add_referral(fid, "fady", "dr_section", "Section note")
        root, tab = _build_tab(fid)
        if tab is None:
            print("SKIP section print (no display)"); return
        try:
            from src.ui.clinical_referrals import (print_selected_referral,
                                                   refresh_referrals, selected_referral)
            tab.load(fid); root.update_idletasks()
            assert str(tab.btn_ref_print.cget("state")) == "disabled"  # no selection
            row = tab._ref_rows["ref0"]
            assert isinstance(row, dict) and row["id"] == rid  # R24: full dict
            tab.tree_ref.selection_set("ref0"); root.update_idletasks(); root.update()
            assert str(tab.btn_ref_print.cget("state")) == "normal"
            assert selected_referral(tab)["id"] == rid
            prev = print_selected_referral(tab)
            assert prev is not None and prev.pdf_path and Path(prev.pdf_path).exists()
            prev.destroy()
            refresh_referrals(tab, None); root.update_idletasks()  # clears: Print disables
            assert tab.tree_ref.get_children() == ()
            assert str(tab.btn_ref_print.cget("state")) == "disabled"
            assert print_selected_referral(tab) is None
        finally: root.destroy()
    finally: _cleanup_refs(fid)
