"""Job 4 (round 12), part 2: alert strip on the patient form + Add image.

Split out of test_patient_alerts.py (200-line limit). Shares its
helpers via import. Covers:
  - the red/amber strip on PatientForm.fill() / .clear();
  - the clinical "Add image" button: visible on the patient panel and
    switches the history notebook to the Scans tab.

GUI tests skip gracefully when no display is available; run with
DISPLAY=:99 under Xvfb. Seeded rows are cleaned up.
"""
import tkinter as tk

from src.ui.clinical import ClinicalTab
from src.ui.patient_form import PatientForm
from tests.test_patient_alerts import _cleanup, _row, _seed, _stub_app
def test_alert_strip_patient_form():
    fid_a = _seed(allergies="Penicillin", meds="Aspirin")
    fid_c = _seed()
    try:
        root = tk.Tk()
    except tk.TclError:
        _cleanup(fid_a); _cleanup(fid_c)
        print("SKIP test_alert_strip_patient_form (no display)")
        return
    root.withdraw()
    try:
        form = PatientForm(root, _stub_app())
        form.pack()
        root.update()
        assert hasattr(form, "alert_strip")
        form.fill(_row(fid_a))
        root.update()
        assert form.alert_strip.winfo_manager() == "pack", "form allergy strip not shown"
        assert "Penicillin" in form.alert_strip.lbl_health.cget("text")
        form.fill(_row(fid_c))
        root.update()
        assert form.alert_strip.winfo_manager() == "", "clean patient shows strip"
        form.clear()
        root.update()
        assert form.alert_strip.winfo_manager() == ""
    finally:
        root.destroy()
        _cleanup(fid_a); _cleanup(fid_c)


def test_add_image_button_visible_and_selects_scans():
    fid = _seed()
    try:
        root = tk.Tk()
    except tk.TclError:
        _cleanup(fid)
        print("SKIP test_add_image_button_visible (no display)")
        return
    root.withdraw()
    root.geometry("1380x900")
    try:
        app = _stub_app({"file_number": fid})
        tab = ClinicalTab(root, app)
        tab.pack(fill="both", expand=True)
        root.update()
        tab.load(fid)
        root.update()
        assert tab.btn_add_image.winfo_manager() == "pack", "Add image button not visible"
        assert "image" in tab.btn_add_image.cget("text").lower() or \
            "صورة" in tab.btn_add_image.cget("text")
        # Clicking with no file chosen (dialog cancelled) must still
        # land the user on the Scans tab.
        from unittest import mock
        import src.ui.scans_tab as scans_tab
        # ROUND-25 SUPERSESSION (item 2): the upload dialog is now the
        # multi-file askopenfilenames; a cancel returns an empty tuple.
        with mock.patch.object(scans_tab.filedialog, "askopenfilenames",
                               return_value=()):
            tab.btn_add_image.invoke()
        root.update()
        assert tab.history_nb.select() == str(tab.scans_frame), \
            "Add image did not switch to the Scans tab"
    finally:
        root.destroy()
        _cleanup(fid)


def test_add_image_button_uploads_via_entry_point():
    """Job 7b: the panel button calls scans_tab.upload_image() directly
    (Agent E contract) - a chosen file is copied into scans/<fid>/
    and registered, and the notebook stays on the Scans tab."""
    import tempfile
    from pathlib import Path
    from unittest import mock

    from PIL import Image

    import src.ui.scans_tab as scans_tab
    from src.models.database import get_connection
    from src.models.scans import list_scans

    fid = _seed()
    try:
        root = tk.Tk()
    except tk.TclError:
        _cleanup(fid)
        print("SKIP test_add_image_button_uploads (no display)")
        return
    root.withdraw()
    root.geometry("1380x900")
    try:
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "tooth.png"
            Image.new("RGB", (60, 40), "white").save(src)
            app = _stub_app({"file_number": fid})
            tab = ClinicalTab(root, app)
            tab.pack(fill="both", expand=True)
            root.update()
            tab.load(fid)
            root.update()
            # ROUND-25 SUPERSESSION (item 2): askopenfilenames returns
            # a tuple, and the batch ends with ONE summary showinfo
            # (mocked here so the test does not block on a modal).
            with mock.patch.object(scans_tab.filedialog, "askopenfilenames",
                                   return_value=(str(src),)), \
                    mock.patch.object(scans_tab.messagebox, "showinfo",
                                      lambda *a, **k: None):
                tab.btn_add_image.invoke()
            root.update()
            conn = get_connection()
            rows = list_scans(conn, fid)
            conn.close()
            assert len(rows) == 1, f"scan not registered: {rows}"
            assert Path(rows[0]["file_path"]).exists(), rows[0]["file_path"]
            assert Path(rows[0]["file_path"]).parent.name == str(fid)
            assert tab.history_nb.select() == str(tab.scans_frame), \
                "after upload the notebook left the Scans tab"
    finally:
        root.destroy()
        _cleanup(fid)
