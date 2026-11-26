"""Round 27: thumbnail grids for X-Rays + Scans replace the
round-25 list+preview. Tiles carry the SAVED NAME only (no paths);
single click selects; double click opens the large viewer (images)
or the detail view (.dcm); delete follows the existing role rules.
GUI tests skip without a display; dialogs/messageboxes are mocked
with real tiny PIL files, as in test_r25_scans_multi."""
import contextlib, shutil, tempfile, tkinter as tk
from pathlib import Path
from tkinter import filedialog as _fd, messagebox as _mb
from unittest import mock
from PIL import Image
from src.config.settings import SCANS, XRAYS
from src.config.theme import zebra_colors
from src.models.database import get_connection, init_db, set_setting
from src.models.scans import ensure_tables, list_scans, register_scan
from src.ui.clinical import ClinicalTab
from src.ui.scans_tab import build_scans_section

def _mk(name="R27 Grid Patient"):
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

def _png(path, size=(40, 30)):
    Image.new("RGB", size, "teal").save(path); return str(path)

def _root():
    try:
        # NOT withdrawn: generated <Button-1> events do not dispatch
        # to bindings on a withdrawn root (proven in round 27).
        root = tk.Tk(); root.deiconify(); root.geometry("1200x800+0+0")
        root.update(); return root
    except tk.TclError:
        return None

@contextlib.contextmanager
def _multi(paths):
    with mock.patch.object(_fd, "askopenfilenames", return_value=tuple(paths)), \
            mock.patch.object(_mb, "showinfo", lambda *a, **k: None):
        yield

def _tops(w):
    out = [w] if isinstance(w, tk.Toplevel) else []
    for ch in w.winfo_children():
        out.extend(_tops(ch))
    return out

def _click(grid, i, double=False):
    tile = grid.tiles[i]
    if not double:
        tile.event_generate("<Button-1>")
        return
    # This Tk build refuses event_generate("<Double-Button-1>")
    # ("Double modifier not allowed"), so a synthetic double-click
    # cannot be dispatched. Assert the REAL binding is registered on
    # the tile, then drive the exact handler it calls (grid._open).
    assert tile.bind("<Double-Button-1>"), "tile has no double-click binding"
    grid._open(grid.items[i])

class _App:
    def __init__(self, patient, lang="en", role="admin"):
        self.lang = lang; self.current_user = "fady"
        self.current_role = role; self.current_patient = patient
    def chart_teeth(self): return []
    def refresh_clinical(self): pass

def _tab(fid, lang="en", role="admin"):
    root = _root()
    if root is None: return None, None
    patient = {"file_number": fid, "full_name": "R27 Grid Patient", "mobile1": "",
               "birth_date_greg": "1990-01-01", "current_medications": "", "allergies": ""}
    tab = ClinicalTab(root, _App(patient, lang, role))
    tab.pack(fill="both", expand=True); root.update_idletasks()
    tab.app.refresh_clinical = lambda: tab.load(fid)
    tab.load(fid); root.update_idletasks(); return root, tab

def _show_xray_page(tab, root):
    """Select the notebook page holding the X-Ray grid (generated
    click events only dispatch to mapped widgets)."""
    tab.history_nb.select(tab.xray_grid.master)
    root.update_idletasks(); root.update()

def _add_xrays(tab, root, names_sizes):
    with tempfile.TemporaryDirectory() as td:
        srcs = [_png(str(Path(td) / n), s) for n, s in names_sizes]
        with _multi(srcs):
            tab.add_xray()
    root.update_idletasks(); tab.load(tab.patient_id); root.update_idletasks()

def test_xray_grid_tiles_names_no_paths():
    fid = _mk(); root, tab = _tab(fid)
    if tab is None: _cleanup(fid); print("SKIP r27 xray grid"); return
    try:
        _add_xrays(tab, root, [("xa.png", (40, 30)), ("xb.png", (50, 40))])
        grid = tab.xray_grid
        assert len(grid.tiles) == 2, len(grid.tiles)
        names = {lbl.cget("text") for lbl in grid.tile_names}
        assert names == {"xa.png", "xb.png"}, names
        for n in names:
            assert "/" not in n and "\\" not in n and ":" not in n, n
    finally: root.destroy(); _cleanup(fid)

def test_xray_select_delete_and_nurse_blocked():
    fid = _mk(); root, tab = _tab(fid)
    if tab is None: _cleanup(fid); print("SKIP r27 xray delete"); return
    try:
        _add_xrays(tab, root, [("xa.png", (40, 30)), ("xb.png", (50, 40))])
        grid = tab.xray_grid
        _show_xray_page(tab, root)
        _click(grid, 0); root.update()
        assert grid.selected and grid.selected["name"] in ("xa.png", "xb.png")
        with mock.patch.object(_mb, "askyesno", return_value=True):
            tab.btn_xray_delete.invoke()
        root.update_idletasks()
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM xrays WHERE patient_file=?", (fid,))
        left = cur.fetchone()[0]; conn.close()
        assert left == 1, left
        assert len(grid.tiles) == 1, len(grid.tiles)
    finally: root.destroy(); _cleanup(fid)
    root2, tab2 = _tab(_mk(), role="nurse")
    if tab2 is not None:
        try: assert str(tab2.btn_xray_delete.cget("state")) == "disabled"
        finally: root2.destroy(); _cleanup(tab2.patient_id)

def test_xray_double_click_large_viewer():
    fid = _mk(); root, tab = _tab(fid)
    if tab is None: _cleanup(fid); print("SKIP r27 viewer"); return
    try:
        _add_xrays(tab, root, [("small.png", (40, 30)), ("big.png", (2400, 1800))])
        grid = tab.xray_grid
        by_name = {it["name"]: i for i, it in enumerate(grid.items)}
        _click(grid, by_name["small.png"], double=True); root.update()
        wins = [w for w in _tops(root) if getattr(w, "viewer_name", "") == "small.png"]
        assert wins, "no viewer for small.png"
        assert wins[0].viewer_size == (40, 30), wins[0].viewer_size  # natural size
        assert wins[0].title() == "small.png"
        wins[0].destroy()
        _click(grid, by_name["big.png"], double=True); root.update()
        wins = [w for w in _tops(root) if getattr(w, "viewer_name", "") == "big.png"]
        assert wins, "no viewer for big.png"
        w, h = wins[0].viewer_size
        assert w <= root.winfo_screenwidth() - 80 and h <= root.winfo_screenheight() - 170
        assert abs(w / h - 2400 / 1800) < 0.02, (w, h)  # aspect preserved
    finally: root.destroy(); _cleanup(fid)

def _scans_section(fid, lang="en", role="doctor"):
    root = _root()
    if root is None: return None, None
    stub = type("Stub", (), {"lang": lang, "current_patient":
                             {"file_number": fid, "full_name": "R27 Grid Patient"}})()
    frame = build_scans_section(root, stub, fid, "fady", role)
    frame.pack(fill="both", expand=True); root.update()
    return root, frame

def _seed_scan(fid, src_name, scan_type="image2d", size=(40, 30)):
    dest = SCANS / str(fid); dest.mkdir(parents=True, exist_ok=True)
    saved = dest / src_name
    if scan_type == "image2d":
        _png(str(saved), size)
    else:
        saved.write_bytes(b"\x00" * 200)
    conn = get_connection(); ensure_tables(conn)
    register_scan(conn, fid, scan_type, str(saved), "", "fady"); conn.close()
    return saved

def test_scans_grid_dcm_detail_and_delete():
    fid = _mk(); _seed_scan(fid, "view.png"); dcm = _seed_scan(fid, "study.dcm", "cbct")
    root, frame = _scans_section(fid)
    if frame is None: _cleanup(fid); print("SKIP r27 scans grid"); return
    try:
        grid = frame.thumb_grid
        assert len(grid.tiles) == 2, len(grid.tiles)
        names = {lbl.cget("text") for lbl in grid.tile_names}
        assert names == {"view.png", "study.dcm"}, names
        by_name = {it["name"]: i for i, it in enumerate(grid.items)}
        tile = grid.tiles[by_name["study.dcm"]]
        def _texts(w):
            out = []
            if w.winfo_class() == "Label":
                out.append(w.cget("text"))
            for c in w.winfo_children():
                out.extend(_texts(c))
            return out
        assert "DICOM" in _texts(tile), _texts(tile)
        _click(grid, by_name["study.dcm"], double=True); root.update()
        wins = [w for w in _tops(root) if getattr(w, "viewer_name", "") == "study.dcm"]
        assert wins, "no detail view for study.dcm"
        assert ("DICOM" in wins[0].detail_text or "pydicom" in wins[0].detail_text), wins[0].detail_text
        assert str(dcm) not in wins[0].detail_text  # no storage path
        wins[0].destroy()
        _click(grid, by_name["view.png"]); root.update()
        assert grid.selected["name"] == "view.png"
        with mock.patch.object(_mb, "askyesno", return_value=True):
            frame.btn_delete.invoke()
        root.update()
        conn = get_connection(); rows = list_scans(conn, fid); conn.close()
        assert len(rows) == 1 and rows[0]["scan_type"] == "cbct", rows
        assert len(grid.tiles) == 1
    finally: root.destroy(); _cleanup(fid)

def test_empty_state_both_languages_and_dark_tiles():
    fid = _mk(); root, tab = _tab(fid)
    if tab is None: _cleanup(fid); print("SKIP r27 empty"); return
    try:
        assert tab.xray_grid.tiles == []
        assert tab.xray_grid.empty_label.cget("text") == "No images yet"
    finally: root.destroy()
    root2, frame2 = _scans_section(fid, lang="ar")
    if frame2 is not None:
        try: assert frame2.thumb_grid.empty_label.cget("text") == "لا توجد صور بعد"
        finally: root2.destroy()
    set_setting("theme_mode", "dark")
    try:
        _seed_scan(fid, "d1.png"); _seed_scan(fid, "d2.png")
        root3, frame3 = _scans_section(fid)
        if frame3 is not None:
            try:
                # R43 re-pin: tiles rotate the vivid palette (was zebra pair).
                from src.ui.vivid_rows import PALETTE
                bgs = [str(tl.cget("bg")).lower() for tl in frame3.thumb_grid.tiles]
                assert bgs == [PALETTE[0].lower(), PALETTE[1].lower()], bgs
            finally: root3.destroy()
    finally:
        set_setting("theme_mode", "light"); _cleanup(fid)
