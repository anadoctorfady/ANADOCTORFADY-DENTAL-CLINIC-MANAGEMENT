"""Round 25 (items 2+3): multi-file scan / X-Ray add, bare file names
in the X-Ray tree, in-app previews with NO paths in the UI. GUI tests
skip without a display. filedialog.askopenfilenames is mocked with
real tiny PIL PNGs; messagebox functions are recording no-ops (the
batch summary must be shown exactly once)."""
import contextlib, shutil, tempfile, tkinter as tk
from pathlib import Path
from tkinter import filedialog as _fd, messagebox as _mb
from unittest import mock
from PIL import Image
from src.config.settings import SCANS, XRAYS
from src.models.database import get_connection, init_db
from src.models.scans import ensure_tables, list_scans, register_scan
from src.ui.clinical import ClinicalTab
from src.ui.scans_tab import build_scans_section, upload_image

def _make_patient(name="R25 Multi Patient"):
    init_db(); conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name,birth_date_greg,nationality) VALUES(?,?,?,?)",
                (name.split()[0], name, "1990-01-01", "Syrian"))
    fid = cur.lastrowid; conn.commit(); conn.close(); return fid

def _cleanup(fid):
    conn = get_connection(); ensure_tables(conn); cur = conn.cursor()
    cur.execute("DELETE FROM patient_scans WHERE patient_id=?", (fid,))
    cur.execute("DELETE FROM xrays WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()
    shutil.rmtree(SCANS / str(fid), ignore_errors=True)
    shutil.rmtree(XRAYS / str(fid), ignore_errors=True)

def _png(path):
    Image.new("RGB", (40, 30), "teal").save(path); return str(path)

@contextlib.contextmanager
def _record_msgbox():
    calls = {"info": [], "warning": [], "error": []}
    def rec(kind): return lambda *a, **k: calls[kind].append(a)
    with mock.patch.object(_mb, "showinfo", rec("info")), \
            mock.patch.object(_mb, "showwarning", rec("warning")), \
            mock.patch.object(_mb, "showerror", rec("error")):
        yield calls

@contextlib.contextmanager
def _mock_multi(paths):
    with mock.patch.object(_fd, "askopenfilenames", return_value=tuple(paths)):
        yield

def _root():
    try:
        root = tk.Tk(); root.withdraw(); return root
    except tk.TclError:
        return None

def test_scans_multi_upload_three_pngs():
    fid = _make_patient(); root = _root()
    if root is None:
        _cleanup(fid); print("SKIP multi scans (no display)"); return
    try:
        with tempfile.TemporaryDirectory() as td:
            srcs = [_png(str(Path(td) / f"s{i}.png")) for i in range(3)]
            with _record_msgbox() as calls, _mock_multi(srcs):
                out = upload_image(root, fid, current_user="fady")
            assert out is not None and Path(out).exists()
            conn = get_connection(); rows = list_scans(conn, fid); conn.close()
            assert len(rows) == 3, rows
            assert all(r["scan_type"] == "image2d" for r in rows)
            assert len(calls["info"]) == 1, calls  # ONE summary only
            assert "Added 3" in calls["info"][0][1], calls["info"]
    finally:
        root.destroy(); _cleanup(fid)

def test_scans_multi_mixed_skips_unsupported():
    fid = _make_patient(); root = _root()
    if root is None:
        _cleanup(fid); print("SKIP mixed scans (no display)"); return
    try:
        with tempfile.TemporaryDirectory() as td:
            good = [_png(str(Path(td) / "a.png")), _png(str(Path(td) / "b.png"))]
            bad = Path(td) / "notes.xyz"; bad.write_bytes(b"junk")
            with _record_msgbox() as calls, _mock_multi(good + [str(bad)]):
                out = upload_image(root, fid, current_user="fady")
            assert out is not None
            conn = get_connection(); rows = list_scans(conn, fid); conn.close()
            assert len(rows) == 2, rows  # .xyz skipped, rest saved
            assert len(calls["info"]) == 1, calls
            msg = calls["info"][0][1]
            assert "Added 2" in msg and "Skipped 1" in msg, msg
            assert "notes.xyz" in msg and "unsupported" in msg, msg
    finally:
        root.destroy(); _cleanup(fid)

class _FakeApp:
    def __init__(self, patient):
        self.lang = "en"; self.current_user = "fady"
        self.current_role = "admin"; self.current_patient = patient
    def chart_teeth(self): return []
    def refresh_clinical(self): pass

def _build_tab(fid):
    root = _root()
    if root is None: return None, None
    patient = {"file_number": fid, "full_name": "R25 Multi Patient", "mobile1": "",
               "birth_date_greg": "1990-01-01", "current_medications": "", "allergies": ""}
    tab = ClinicalTab(root, _FakeApp(patient))
    tab.pack(fill="both", expand=True); root.update_idletasks()
    tab.load(fid); root.update_idletasks(); return root, tab

def _add_two_xrays(tab, root):
    with tempfile.TemporaryDirectory() as td:
        srcs = [_png(str(Path(td) / "xa.png")), _png(str(Path(td) / "xb.png"))]
        with _record_msgbox() as calls, _mock_multi(srcs):
            tab.add_xray()
        root.update_idletasks()
        assert len(calls["info"]) == 1, calls  # ONE summary only
        assert "Added 2" in calls["info"][0][1], calls["info"]

def _xray_rows(fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM xrays WHERE patient_file=?", (fid,))
    rows = [dict(r) for r in cur.fetchall()]; conn.close(); return rows

def test_xray_multi_upload_bare_filenames():
    fid = _make_patient(); root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid); print("SKIP xray multi (no display)"); return
    try:
        _add_two_xrays(tab, root)
        assert len(_xray_rows(fid)) == 2, _xray_rows(fid)
        tab.load(fid); root.update_idletasks()  # what refresh_clinical does
        # ROUND-27 SUPERSESSION (thumbnail grid): the X-Ray tree is
        # replaced by tab.xray_grid. Equivalent assertions: exactly
        # the two saved files appear as tiles, named by their SAVED
        # NAME only -- no path separators / drive patterns anywhere.
        grid = tab.xray_grid
        assert len(grid.tiles) == 2, len(grid.tiles)
        names = {lbl.cget("text") for lbl in grid.tile_names}
        assert names == {"xa.png", "xb.png"}, names
        for n in names:
            assert "/" not in n and "\\" not in n and ":" not in n, n
    finally:
        root.destroy(); _cleanup(fid)

def test_xray_preview_shows_image():
    fid = _make_patient(); root, tab = _build_tab(fid)
    if tab is None:
        _cleanup(fid); print("SKIP xray preview (no display)"); return
    try:
        _add_two_xrays(tab, root)
        tab.load(fid); root.update_idletasks()
        # ROUND-27 SUPERSESSION: the under-list preview pane is gone;
        # opening a tile (the double-click handler) shows the image
        # LARGE in the viewer, titled with the saved name only.
        grid = tab.xray_grid
        assert grid.tiles[0].bind("<Double-Button-1>")
        grid._open(grid.items[0]); root.update()
        def _tops(w):
            out = [w] if isinstance(w, tk.Toplevel) else []
            for ch in w.winfo_children():
                out.extend(_tops(ch))
            return out
        wins = [w for w in _tops(root)
                if getattr(w, "viewer_name", "") in ("xa.png", "xb.png")]
        assert wins, "double-click opened no viewer"
        assert wins[0].viewer_photo is not None
        assert "/" not in wins[0].title() and "\\" not in wins[0].title()
    finally:
        root.destroy(); _cleanup(fid)

def test_scans_preview_shows_image():
    fid = _make_patient(); root = _root()
    if root is None:
        _cleanup(fid); print("SKIP scans preview (no display)"); return
    try:
        with tempfile.TemporaryDirectory() as td:
            dest = SCANS / str(fid); dest.mkdir(parents=True, exist_ok=True)
            saved = dest / "preview.png"
            shutil.copy2(_png(str(Path(td) / "preview.png")), saved)
            conn = get_connection(); ensure_tables(conn)
            register_scan(conn, fid, "image2d", str(saved), "", "fady"); conn.close()
            stub = type("Stub", (), {"lang": "en", "current_patient":
                                     {"file_number": fid, "full_name": "R25 Multi Patient"}})()
            frame = build_scans_section(root, stub, fid, "fady", "doctor")
            frame.pack(fill="both", expand=True); root.update()
            # ROUND-27 SUPERSESSION: the scans tree + preview pane are
            # replaced by frame.thumb_grid; opening the tile shows
            # the image LARGE in the viewer (title = saved name).
            grid = frame.thumb_grid
            assert len(grid.tiles) == 1, len(grid.tiles)
            assert grid.tile_names[0].cget("text") == "preview.png"
            grid._open(grid.items[0]); root.update()
            def _tops(w):
                out = [w] if isinstance(w, tk.Toplevel) else []
                for ch in w.winfo_children():
                    out.extend(_tops(ch))
                return out
            wins = [w for w in _tops(root)
                    if getattr(w, "viewer_name", "") == "preview.png"]
            assert wins and wins[0].viewer_photo is not None, "no viewer image"
    finally:
        root.destroy(); _cleanup(fid)
