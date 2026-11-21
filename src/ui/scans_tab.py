"""Scans section: CBCT (.dcm) + intraoral 3D (.stl/.ply/.obj) + 2D
images, shown as a THUMBNAIL GRID (round 27): one tile per file --
thumbnail + saved name; single click selects, double click opens
the large in-app viewer (images) or the detail view (.dcm / 3D).
HONEST LIMITS (shown in the UI): only 2D images render inside the
app; 3D scans and CBCT volumes open their metadata here and the
file itself via Open externally. Delete is enabled only for
admin/doctor roles (role passed in, no permissions import).
The grid never displays a storage path (round-25 rule). <200 lines."""
import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from src.config.settings import SCANS
from src.config.strings import t
from src.config.theme import current
from src.models.database import get_connection
from src.models.scans import (IMAGE_EXTS, MESH_EXTS, delete_scan, ensure_tables,
                              list_scans, preview_available, register_scan,
                              scan_info)
from src.ui.image_viewer import open_detail_viewer, open_image_viewer
from src.ui.rounded import rounded_button
from src.ui.rounded_widgets import RoundedEntry
from src.ui.settings_storage_ui import resolve_scans_dir
from src.ui.thumb_grid import ThumbGrid, kind_for

FILETYPES = [("scans.ft_scans", "*.dcm *.stl *.ply *.obj *.png *.jpg *.jpeg "
              "*.bmp *.webp *.tiff"), ("scans.ft_all", "*.*")]


def _scan_type(path):
    ext = Path(path).suffix.lower()
    return ("cbct" if ext == ".dcm" else "intraoral" if ext in MESH_EXTS
            else "image2d" if ext in IMAGE_EXTS else "other")


def _open_external(path, lang="en"):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606 - user-chosen local file
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        messagebox.showerror(t("scans.open_failed", lang), str(e))


def upload_image(parent, patient_file, current_user="", description="", lang="en"):
    """Importable upload entry point (Job 7a contract for Agent A: the
    clinical patient panel calls this). Round 25: MULTI-file dialog ->
    the batch logic in scans_upload_multi copies + registers EACH file
    (per-file failure isolation, one summary messagebox). Returns the
    last saved path (str) or None when cancelled / no patient / none
    saved, so clinical_image.open_add_image keeps working unchanged."""
    if patient_file is None:
        messagebox.showwarning(t("scans.no_patient_title", lang),
                               t("scans.no_patient_msg", lang), parent=parent)
        return None
    chosen = filedialog.askopenfilenames(
        parent=parent,
        filetypes=[(t(k, lang), pat) for k, pat in FILETYPES])
    if not chosen:
        return None
    if isinstance(chosen, (str, Path)):
        chosen = (chosen,)
    from src.ui.scans_upload_multi import upload_files
    return upload_files(parent, patient_file, chosen, current_user,
                        description, lang)


def build_scans_section(parent, app, patient_id, current_user, role):
    """Returns the Frame. Wire into clinical.py as:
    build_scans_section(parent, app, patient_file_number, current_user, role)."""
    th = current()
    lang = getattr(app, "lang", "en")
    frame = tk.Frame(parent, bg=th["panel"], highlightthickness=1,
                     highlightbackground=th["border"])
    tk.Label(frame, text=t("scans.title", lang), bg=th["panel"], fg=th["accent"],
             font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 0))
    tk.Label(frame, text=t("scans.note", lang), bg=th["panel"], fg=th["muted"], font=("Segoe UI", 9),
             justify="left", wraplength=640).pack(anchor="w", padx=10, pady=4)
    # Job 7a: the upload button sits at the TOP, next to the patient
    # context, visible without scrolling (pinned by test_scans_upload).
    top = tk.Frame(frame, bg=th["panel"])
    top.pack(fill="x", padx=10, pady=(6, 2))
    _name = (getattr(app, "current_patient", None) or {}).get("full_name", "")
    ctx = t("scan.patient", lang).format(name=_name or "—", fid=patient_id) if patient_id is not None else t("scan.no_patient", lang)
    tk.Label(top, text=ctx, bg=th["panel"], fg=th["text"],
             font=("Segoe UI", 10, "bold")).pack(side="left")
    state = {"scans": {}}
    row = tk.Frame(frame, bg=th["panel"])
    row.pack(fill="x", padx=10, pady=4)
    tk.Label(row, text=t("scans.desc", lang), bg=th["panel"], fg=th["text"]).pack(side="left")
    e_desc = RoundedEntry(row, width=32)
    e_desc.pack(side="left", padx=6)

    def open_item(item):
        rec = item["rec"]
        if item["kind"] == "image":
            return open_image_viewer(frame, rec["file_path"], item["name"], lang,
                                     on_saved=lambda: refresh())  # R38: rotate-save refresh
        info = scan_info(rec["file_path"])
        _ok, msg = preview_available(rec["file_path"])
        return open_detail_viewer(frame, item["name"],
                                  f"{info['detail']}\n{msg}", lang)

    grid = ThumbGrid(frame, lang=lang, on_open=open_item)
    grid.pack(fill="both", expand=True, padx=10, pady=4)
    frame.thumb_grid = grid

    def refresh():
        state["scans"] = {}
        items = []
        if patient_id is not None:
            conn = get_connection()
            ensure_tables(conn)
            for r in list_scans(conn, patient_id):
                state["scans"][str(r["id"])] = r
                items.append({"key": r["id"], "rec": r,
                              "name": Path(r["file_path"]).name,
                              "sub": (r["upload_date"] or "")[:10],
                              "path": r["file_path"],
                              "kind": kind_for(r["file_path"])})
            conn.close()
        grid.set_items(items)

    def upload():
        if upload_image(frame, patient_id, current_user, e_desc.get().strip(), lang=lang):
            e_desc.delete(0, "end")
            refresh()

    btn_top = rounded_button(top, text=t("scan.add_image", lang), bg=th["accent"], fg="white",
                        font=("Segoe UI", 11, "bold"), padx=14, pady=6, command=upload)
    btn_top.pack(side="right")
    frame.btn_upload_top = btn_top

    def _selected_rec():
        item = grid.selected
        return item["rec"] if item else None

    def delete_selected():
        rec = _selected_rec()
        if not rec:
            return
        if not messagebox.askyesno(t("scans.delete_title", lang),
                                   t("scans.delete_msg", lang).format(file=Path(rec['file_path']).name)):
            return
        conn = get_connection()
        delete_scan(conn, rec["id"])
        conn.close()
        try:
            Path(rec["file_path"]).unlink(missing_ok=True)
        except Exception:
            pass
        refresh()

    def open_selected():
        rec = _selected_rec()
        if rec:
            _open_external(rec["file_path"], lang)
        else:
            messagebox.showinfo(t("scans.select_title", lang), t("scans.select_msg", lang))

    btns = tk.Frame(frame, bg=th["panel"])
    btns.pack(fill="x", padx=10, pady=(0, 8))
    rounded_button(btns, text=t("scans.upload", lang), bg=th["accent"], fg="white",
              command=upload).pack(side="left", padx=4)
    rounded_button(btns, text=t("scans.open_ext", lang), bg=th["card"], fg=th["text"],
              command=open_selected).pack(side="left", padx=4)
    frame.btn_delete = rounded_button(btns, text=t("scans.delete", lang), bg=th["card"], fg=th["text"], command=delete_selected,
              state="normal" if (role or "") in ("admin", "doctor")
              else "disabled")
    frame.btn_delete.pack(side="left", padx=4)
    refresh()
    return frame
