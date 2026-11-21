"""X-Ray section: multi-file add (round 25) + thumbnail grid (R27).

add_xrays(): askopenfilenames -> one `xrays` row per successfully
copied file, per-file failure isolation, one summary messagebox in
the app language, then the same refresh the old single-file code
did. Round 27: build_xray_section() replaces the round-25 tree +
preview pane with a ThumbGrid of the patient's X-Ray files (tile =
thumbnail + saved name; double-click opens the large viewer, or
the detail view for non-images). Delete (admin/doctor, with
confirmation) mirrors the Scans section: DB row + stored file.
Nothing in this section ever displays a storage path."""
import shutil
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

from src.config.settings import XRAYS
from src.config.strings import t
from src.config.theme import current
from src.models.database import get_connection
from src.models.scans import preview_available, scan_info
from src.ui.image_viewer import open_detail_viewer, open_image_viewer
from src.ui.rounded import rounded_button
from src.ui.thumb_grid import ThumbGrid, kind_for


def add_xrays(tab):
    """Multi-file replacement for the old single-file add_xray."""
    if not tab._need():
        return
    lang = getattr(tab.app, "lang", "en")
    chosen = filedialog.askopenfilenames(filetypes=[
        (t("clinical.ft_images", lang), "*.png *.jpg *.jpeg *.bmp *.webp"),
        (t("clinical.ft_all", lang), "*.*")])
    if not chosen:
        return
    if isinstance(chosen, (str, Path)):
        chosen = (chosen,)
    fid = tab.app.current_patient["file_number"]
    dest = XRAYS / str(fid)
    dest.mkdir(parents=True, exist_ok=True)
    added, skipped = 0, []
    conn = get_connection()
    cur = conn.cursor()
    try:
        for f in chosen:
            name = Path(f).name
            try:
                target = dest / name
                shutil.copy2(f, target)
                cur.execute(
                    "INSERT INTO xrays(patient_file,file_path,description,"
                    "upload_date) VALUES(?,?,?,?)",
                    (fid, str(target), "", datetime.now().isoformat()))
                added += 1
            except Exception:
                skipped.append(
                    f"{name}: {t('clinical.xray_skip_failed', lang)}")
        conn.commit()
    finally:
        conn.close()
    msg = t("clinical.xray_added_summary", lang).format(n=added)
    if skipped:
        msg += t("clinical.xray_skipped_part", lang).format(
            m=len(skipped), reasons="; ".join(skipped))
    messagebox.showinfo(t("clinical.xray_summary_title", lang), msg,
                        parent=tab)
    tab.app.refresh_clinical()


def xray_items(fid):
    """Grid items for one patient's X-Ray rows (newest first)."""
    if fid is None:
        return []
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM xrays WHERE patient_file=? "
                "ORDER BY upload_date DESC", (fid,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    items = []
    for r in rows:
        sub = (r["upload_date"] or "")[:10]
        if r["description"]:
            sub = f"{sub} · {r['description']}" if sub else r["description"]
        items.append({"key": r["id"], "name": Path(r["file_path"]).name,
                      "sub": sub, "path": r["file_path"],
                      "kind": kind_for(r["file_path"])})
    return items


def refresh_xray_grid(tab, fid):
    grid = getattr(tab, "xray_grid", None)
    if grid is not None:
        grid.set_items(xray_items(fid))


def open_xray_item(tab, item):
    """Double-click: images open large; other kinds open detail."""
    lang = getattr(tab.app, "lang", "en")
    if item["kind"] == "image":
        return open_image_viewer(tab, item["path"], item["name"], lang,
                                 on_saved=lambda: refresh_xray_grid(tab, tab.patient_id))  # R38: rotate-save refresh
    info = scan_info(item["path"])
    _ok, msg = preview_available(item["path"])
    return open_detail_viewer(tab, item["name"],
                              f"{info['detail']}\n{msg}", lang)


def delete_selected_xray(tab):
    """Delete the selected tile's X-Ray (row + file), with the
    Scans-style confirmation. Button is role-gated at build time."""
    grid = getattr(tab, "xray_grid", None)
    item = grid.selected if grid is not None else None
    if not item:
        return
    lang = getattr(tab.app, "lang", "en")
    if not messagebox.askyesno(
            t("clinical.xray_delete_title", lang),
            t("clinical.xray_delete_msg", lang).format(file=item["name"]),
            parent=tab):
        return
    conn = get_connection()
    conn.execute("DELETE FROM xrays WHERE id=?", (item["key"],))
    conn.commit()
    conn.close()
    try:
        Path(item["path"]).unlink(missing_ok=True)
    except Exception:
        pass
    tab.app.refresh_clinical()


def build_xray_section(tab, parent):
    """Add/Delete button bar + the thumbnail grid for notebook f4."""
    th = current()
    lang = getattr(tab.app, "lang", "en")
    bar = tk.Frame(parent, bg=th["panel"])
    bar.pack(fill="x", padx=6, pady=4)
    rounded_button(bar, text=t("clinical.add_xray", lang),
                   bg=th["accent"], fg="white",
                   command=tab.add_xray).pack(side="left")
    btn = rounded_button(
        bar, text=t("clinical.xray_delete", lang), bg=th["card"],
        fg=th["text"], command=lambda: delete_selected_xray(tab),
        state="normal" if tab.current_role in ("admin", "doctor")
        else "disabled")
    btn.pack(side="left", padx=4)
    tab.btn_xray_delete = btn
    grid = ThumbGrid(parent, lang=lang,
                     on_open=lambda it: open_xray_item(tab, it))
    grid.pack(fill="both", expand=True, padx=4, pady=4)
    tab.xray_grid = grid
    return grid
