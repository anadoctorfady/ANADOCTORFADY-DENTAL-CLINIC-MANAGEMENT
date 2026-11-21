"""Round 16 worker E: clinic_name/reports_dir/scans_dir settings,
storage section UI (EN + AR), scans upload honoring scans_dir, and the
no-hardcoded-white rule. Users-tab layout: test_users_layout_r16.py."""
import contextlib
import tempfile
from pathlib import Path

import src.models.backup_validate as BV
import src.models.database as DBmod
from src.models.database import init_db, get_connection, get_setting, set_setting

ROOT = Path(__file__).resolve().parent.parent
_TMP = Path(tempfile.mkdtemp(prefix="settings_r16_"))


@contextlib.contextmanager
def isolated_db():
    """Temp DB (same pattern as test_settings_bundle): the gate DB is shared, so tests must not depend on it."""
    db_path = _TMP / "iso_clinic.db"
    for suf in ("", "-wal", "-shm"):
        q = Path(str(db_path) + suf)
        if q.exists():
            q.unlink()
    old_db, old_bv = DBmod.DB, BV.DB
    DBmod.DB, BV.DB = db_path, db_path
    try:
        init_db()
        yield
    finally:
        DBmod.DB, BV.DB = old_db, old_bv


def _tk():
    try:
        import tkinter as tk
        return tk.Tk()
    except Exception:
        return None


class _StubApp:
    lang = "en"

    def print_pdf(self, bilingual=False):
        return None

    def _rebuild(self):
        return None


def test_storage_settings_roundtrip():
    """Persist via set/get_setting. NOTE: init_db seeds
    clinic_name="" (database.py:116, round-16 integration: empty =
    no clinic name shown); reports_dir/scans_dir have no seed.""" 
    with isolated_db():
        assert get_setting("clinic_name", "FALLBACK") == ""
        for key in ("reports_dir", "scans_dir"):
            assert get_setting(key, "") in ("", None)
        set_setting("clinic_name", "عيادة النور")
        set_setting("reports_dir", "/tmp/r16_reports")
        set_setting("scans_dir", "/tmp/r16_scans")
        assert get_setting("clinic_name", "") == "عيادة النور"
        assert get_setting("reports_dir", "") == "/tmp/r16_reports"
        assert get_setting("scans_dir", "") == "/tmp/r16_scans"
        # Back to empty = hidden again.
        set_setting("clinic_name", "")
        assert get_setting("clinic_name", "") == ""


def test_resolve_dirs_default_and_custom():
    """Empty/whitespace dirs resolve to the app defaults; a set value resolves to exactly that folder."""
    from src.config.settings import REPORTS, SCANS
    from src.ui.settings_storage_ui import resolve_reports_dir, resolve_scans_dir
    with isolated_db():
        assert resolve_reports_dir() == REPORTS
        assert resolve_scans_dir() == SCANS
        set_setting("reports_dir", "/tmp/r16_reports")
        set_setting("scans_dir", "/tmp/r16_scans")
        assert resolve_reports_dir() == Path("/tmp/r16_reports")
        assert resolve_scans_dir() == Path("/tmp/r16_scans")
        set_setting("reports_dir", "   ")
        set_setting("scans_dir", "")
        assert resolve_reports_dir() == REPORTS
        assert resolve_scans_dir() == SCANS


def test_scans_upload_uses_custom_dir():
    """upload_image copies into <scans_dir>/<patient_file>/ and registers
    that path in patient_scans when scans_dir is set."""
    from PIL import Image
    from src.ui import scans_tab
    with isolated_db():
        # patient_scans.patient_id is a FK to patients(file_number).
        conn = get_connection()
        conn.execute("INSERT INTO patients(file_number, first_name, father_name, grand_name, last_name, full_name) VALUES(?,?,?,?,?,?)",
                     (424242, "Scan", "Test", "", "Patient", "Scan Test Patient"))
        conn.commit(); conn.close()
        custom = _TMP / "my_scans"
        set_setting("scans_dir", str(custom))
        src_file = _TMP / "pano.png"
        Image.new("RGB", (10, 10), (200, 200, 200)).save(src_file)
        # ROUND-25 SUPERSESSION: askopenfilenames (tuple) + summary showinfo stubbed.
        old_ask, old_info = scans_tab.filedialog.askopenfilenames, scans_tab.messagebox.showinfo
        scans_tab.filedialog.askopenfilenames = lambda *a, **k: (str(src_file),)
        scans_tab.messagebox.showinfo = lambda *a, **k: None
        try:
            saved = scans_tab.upload_image(None, 424242, current_user="fady", description="r16", lang="en")
        finally:
            scans_tab.filedialog.askopenfilenames, scans_tab.messagebox.showinfo = old_ask, old_info
        assert saved is not None, "upload returned None"
        assert Path(saved).parent == custom / "424242", saved
        assert Path(saved).exists()
        conn = get_connection()
        row = conn.execute("SELECT file_path FROM patient_scans WHERE patient_id=?",
                           (424242,)).fetchone()
        conn.close()
        assert row and row[0] == saved
        Path(saved).unlink()
        conn = get_connection()
        conn.execute("DELETE FROM patient_scans WHERE patient_id=?", (424242,))
        conn.execute("DELETE FROM patients WHERE file_number=?", (424242,))
        conn.commit(); conn.close()


def _labels_under(widget):
    """All tk.Label texts in a widget subtree."""
    import tkinter as tk
    out = []
    for w in widget.winfo_children():
        if isinstance(w, tk.Label):
            out.append(w.cget("text"))
        out.extend(_labels_under(w))
    return out


def _build_settings(lang):
    from src.ui.settings_ui import SettingsTab
    root = _tk()
    if root is None:
        return None, None
    root.withdraw()
    app = _StubApp(); app.lang = lang
    return SettingsTab(root, app), root


def test_settings_storage_section_gui():
    """Storage section builds in EN + AR: clinic-name entry, folder
    pickers that store the paths, Default buttons, 'NOT moved' note."""
    import src.ui.settings_storage_ui as SS
    for lang, note in (("en", "NOT moved"), ("ar", "لا تُنقل")):
        with isolated_db():
            tab, root = _build_settings(lang)
            if tab is None:
                print("SKIP test_settings_storage_section_gui (no display)")
                return
            try:
                assert hasattr(tab, "clinic_name_var")
                assert hasattr(tab, "reports_dir_var")
                assert hasattr(tab, "scans_dir_var")
                labels = _labels_under(tab.body)
                assert any(note in t for t in labels), labels
                # Folder picker stores the path (askdirectory stubbed).
                picked = str(_TMP / f"picked_{lang}")
                old_ask = SS.filedialog.askdirectory
                SS.filedialog.askdirectory = lambda *a, **k: picked
                try:
                    SS.pick_reports_dir(tab)
                finally:
                    SS.filedialog.askdirectory = old_ask
                assert get_setting("reports_dir", "") == picked
                assert picked in tab._storage_reports_lbl.cget("text")
                # Default button clears it back to the app default.
                SS.reset_reports_dir(tab)
                assert get_setting("reports_dir", "") == ""
                # Clinic name saves via the Save button (info stubbed).
                old_info = SS.messagebox.showinfo
                SS.messagebox.showinfo = lambda *a, **k: None
                try:
                    tab.clinic_name_var.set("عيادة النور" if lang == "ar" else "Noor Clinic")
                    SS.save_storage(tab)
                finally:
                    SS.messagebox.showinfo = old_info
                assert get_setting("clinic_name", "") == tab.clinic_name_var.get()
            finally:
                try:
                    root.destroy()
                except Exception:
                    pass


def test_no_hardcoded_white_in_new_modules():
    """Round-16 rule: my new files use theme tokens only — no white
    literal anywhere in them."""
    for name in ("src/config/strings_r16_settings.py",
                 "src/ui/settings_storage_ui.py", "src/ui/tree_scroll.py"):
        src = (ROOT / name).read_text(encoding="utf-8")
        assert "white" not in src.lower(), name
        assert "#FFFFFF" not in src, name


