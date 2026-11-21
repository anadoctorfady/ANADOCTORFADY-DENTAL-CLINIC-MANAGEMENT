"""Round 25 (item 2): multi-file scan upload batch logic.

Extracted from scans_tab.upload_image (that file is at the 200-line
limit): copies EACH chosen file into the patient scans folder and
registers it, with per-file failure isolation. Files whose extension
is not a known scan/image type (not in IMAGE_EXTS / MESH_EXTS and
not .dcm) are skipped with a reason instead of being registered as
"other". After the batch ONE summary messagebox is shown in the app
language. Returns the last successfully saved path (str) or None."""
import shutil
from pathlib import Path
from tkinter import messagebox

from src.config.strings import t
from src.models.database import get_connection
from src.models.scans import (IMAGE_EXTS, MESH_EXTS, ensure_tables,
                              register_scan)
from src.ui.settings_storage_ui import resolve_scans_dir


def scan_type(path):
    ext = Path(path).suffix.lower()
    return ("cbct" if ext == ".dcm" else "intraoral" if ext in MESH_EXTS
            else "image2d" if ext in IMAGE_EXTS else "other")


def is_supported(path):
    ext = Path(path).suffix.lower()
    return ext == ".dcm" or ext in MESH_EXTS or ext in IMAGE_EXTS


def upload_files(parent, patient_file, sources, current_user="",
                 description="", lang="en"):
    """Copy + register every file in `sources`. One bad file never
    blocks the rest. Shows one summary messagebox when the batch was
    not cancelled (sources non-empty). Returns last saved path/None."""
    dest_dir = resolve_scans_dir() / str(patient_file)
    dest_dir.mkdir(parents=True, exist_ok=True)
    added, skipped = [], []
    conn = get_connection()
    ensure_tables(conn)
    try:
        for src in sources:
            name = Path(src).name
            if not is_supported(src):
                skipped.append(f"{name}: {t('scans.skip_unsupported', lang)}")
                continue
            try:
                target, n = dest_dir / name, 1
                while target.exists():
                    target = dest_dir / f"{Path(src).stem}_{n}{Path(src).suffix}"
                    n += 1
                shutil.copy2(src, target)
                register_scan(conn, patient_file, scan_type(src),
                              str(target), (description or "").strip(),
                              current_user or "")
                added.append(str(target))
            except Exception:
                skipped.append(f"{name}: {t('scans.skip_failed', lang)}")
    finally:
        conn.close()
    msg = t("scans.added_summary", lang).format(n=len(added))
    if skipped:
        msg += t("scans.skipped_part", lang).format(
            m=len(skipped), reasons="; ".join(skipped))
    messagebox.showinfo(t("scans.summary_title", lang), msg, parent=parent)
    return added[-1] if added else None
