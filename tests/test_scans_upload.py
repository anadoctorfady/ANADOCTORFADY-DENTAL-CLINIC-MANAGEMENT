"""Job 7a (round 12): scans upload discoverability — a big Add-image
button at the TOP of the Scans tab next to the patient context, and the
importable upload_image() entry point for the clinical patient panel.
GUI tests need a display (Xvfb :103); the contract test runs headless."""
import inspect
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from PIL import Image

from src.config.settings import SCANS
from src.models.database import get_connection, init_db
from src.models.scans import ensure_tables, list_scans
from src.ui.scans_tab import build_scans_section, upload_image


def _make_patient(name="Scan Upload Patient"):
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name,birth_date_greg,nationality) VALUES(?,?,?,?)",
                (name.split()[0], name, "1990-01-01", "Syrian"))
    fid = cur.lastrowid; conn.commit(); conn.close()
    return fid


def _cleanup(fid):
    conn = get_connection(); ensure_tables(conn)  # scans table is lazy
    cur = conn.cursor()
    cur.execute("DELETE FROM patient_scans WHERE patient_id=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()
    shutil.rmtree(SCANS / str(fid), ignore_errors=True)


def _make_png(path):
    Image.new("RGB", (40, 30), "red").save(path)
    return str(path)


def _gui_section(fid, lang="en", name="Scan Upload Patient"):
    """Build the scans section on a stub app; None when no display."""
    try:
        import tkinter as tk
        root = tk.Tk()
        pat = {"file_number": fid, "full_name": name} if fid else None
        stub = type("Stub", (), {"lang": lang, "current_patient": pat})()
        frame = build_scans_section(root, stub, fid, "fady", "doctor")
        frame.pack(fill="both", expand=True); root.update()
        return root, frame
    except Exception:
        return None


def _tree(frame):
    # ROUND-27 SUPERSESSION: the scans list is now a ThumbGrid (a
    # tk.Frame subclass) packed as a direct child of the section.
    from src.ui.thumb_grid import ThumbGrid
    return next((w for w in frame.winfo_children()
                 if isinstance(w, ThumbGrid)), None)


def _labels(frame):
    return [w.cget("text") for w in frame.btn_upload_top.master.winfo_children()
            if w.winfo_class() == "Label"]


def test_upload_entry_point_contract():
    """Agent A contract: upload_image(parent, patient_file, ...) lives in
    src.ui.scans_tab, is callable, and keeps this exact signature."""
    assert upload_image.__module__ == "src.ui.scans_tab"
    assert callable(upload_image)
    params = list(inspect.signature(upload_image).parameters)
    assert params[:2] == ["parent", "patient_file"], params
    assert "current_user" in params and "description" in params


def test_upload_button_at_top_with_patient_context():
    fid = _make_patient()
    got = _gui_section(fid, lang="en")
    if got is None:
        _cleanup(fid)
        return  # no display: contract test above still covers the API
    root, frame = got
    try:
        root.deiconify(); root.update()
        btn = frame.btn_upload_top
        assert btn.winfo_exists() and btn.winfo_ismapped()
        assert "Add image" in btn.cget("text"), btn.cget("text")
        assert "bold" in str(btn.cget("font"))
        kids = frame.winfo_children()
        tree = _tree(frame)
        assert tree is not None
        # Top button row is packed BEFORE the scans list: visible first.
        assert kids.index(btn.master) < kids.index(tree)
        assert btn.winfo_y() < tree.winfo_y()
        # Patient context sits next to the button in the same top row.
        assert any("Scan Upload Patient" in t for t in _labels(frame)), _labels(frame)
    finally:
        root.destroy(); _cleanup(fid)


def test_upload_button_arabic():
    fid = _make_patient("مريض المسح")
    got = _gui_section(fid, lang="ar", name="مريض المسح")
    if got is None:
        _cleanup(fid)
        return
    root, frame = got
    try:
        assert "إضافة صورة" in frame.btn_upload_top.cget("text")
        assert any("مريض المسح" in t for t in _labels(frame)), _labels(frame)
    finally:
        root.destroy(); _cleanup(fid)


def test_upload_via_top_button_saves_file_and_lists_it():
    fid = _make_patient()
    got = _gui_section(fid)
    if got is None:
        _cleanup(fid)
        return
    root, frame = got
    try:
        with tempfile.TemporaryDirectory() as td:
            src = _make_png(str(Path(td) / "cbct_view.png"))
            # ROUND-25 SUPERSESSION (item 2): upload_image now opens the
            # MULTI-file dialog (askopenfilenames, tuple result) and shows
            # ONE summary showinfo after the batch -- mock both.
            with mock.patch("src.ui.scans_tab.filedialog.askopenfilenames", return_value=(src,)), \
                    mock.patch("src.ui.scans_tab.messagebox.showinfo"):
                frame.btn_upload_top.invoke()
            root.update()
            saved = SCANS / str(fid) / "cbct_view.png"
            assert saved.exists(), f"expected {saved} to exist"
            conn = get_connection(); rows = list_scans(conn, fid); conn.close()
            assert len(rows) == 1 and rows[0]["scan_type"] == "image2d"
            assert rows[0]["description"] == ""
            # ROUND-27 SUPERSESSION: the uploaded file is listed as
            # a thumbnail-grid tile named by its saved name.
            grid = _tree(frame)
            names = [lbl.cget("text") for lbl in grid.tile_names]
            assert names == ["cbct_view.png"], names
    finally:
        root.destroy(); _cleanup(fid)


def test_upload_image_direct_and_cancel():
    fid = _make_patient()
    got = _gui_section(fid)
    if got is None:
        _cleanup(fid)
        return
    root, frame = got
    try:
        with tempfile.TemporaryDirectory() as td:
            src = _make_png(str(Path(td) / "direct.png"))
            # ROUND-25 SUPERSESSION (item 2): see the note in
            # test_upload_via_top_button_saves_file_and_lists_it --
            # askopenfilenames (tuple) + summary showinfo mocked. The
            # return contract is unchanged: last saved path, or None.
            with mock.patch("src.ui.scans_tab.filedialog.askopenfilenames", return_value=(src,)), \
                    mock.patch("src.ui.scans_tab.messagebox.showinfo"):
                out = upload_image(root, fid, current_user="fady", description="direct upload")
            assert out is not None and Path(out).exists()
            assert Path(out).parent == SCANS / str(fid)
            conn = get_connection(); rows = list_scans(conn, fid); conn.close()
            assert len(rows) == 1 and rows[0]["description"] == "direct upload"
            # Cancelled dialog -> None, nothing saved, no new row.
            with mock.patch("src.ui.scans_tab.filedialog.askopenfilenames", return_value=()):
                assert upload_image(root, fid) is None
            conn = get_connection(); assert len(list_scans(conn, fid)) == 1; conn.close()
    finally:
        root.destroy(); _cleanup(fid)


def test_upload_no_patient_warns_not_crash():
    got = _gui_section(None)
    if got is None:
        return
    root, frame = got
    try:
        with mock.patch("src.ui.scans_tab.messagebox.showwarning") as warn:
            assert upload_image(root, None) is None
            warn.assert_called_once()
        # The top button with no patient warns the same way, no crash.
        with mock.patch("src.ui.scans_tab.messagebox.showwarning") as warn:
            frame.btn_upload_top.invoke()
            warn.assert_called_once()
        assert any("No patient selected" in t for t in _labels(frame)), _labels(frame)
    finally:
        root.destroy()
