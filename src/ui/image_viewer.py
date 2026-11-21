"""Large in-app viewers for patient files (round 27; round 38
adds zoom + rotate controls to the image viewer).

open_image_viewer: a Toplevel titled with the file's SAVED NAME
(never its storage path). Round 38 (owner): toolbar with zoom in /
zoom out / fit and rotate left / right (90° steps). Zooming scales
the DISPLAY only — the file is never touched, so quality is
inherently preserved. Rotation is shown immediately; on close
(button, Esc or the window X) a rotated image asks bilingually
whether to SAVE the rotation into the file (image_save: exact
transpose; PNG lossless, JPEG q100 4:4:4) or DISCARD it (file left
byte-identical). on_saved fires after a save so the host refreshes
its thumbnail grid (thumbs are keyed by path+mtime+size).
open_detail_viewer: same shell for non-image files (.dcm / 3D /
other): no zoom/rotate controls there (round 38 scope)."""
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageTk

from src.config.strings import t
from src.config.strings_r38 import r38_t
from src.config.theme import current
from src.models.scans import preview_available
from src.ui.image_save import rotate_image, save_rotated
from src.ui.rounded import rounded_button

ZOOM_STEP = 1.25
ZOOM_MIN, ZOOM_MAX = 0.2, 8.0


def _shell(parent, name, lang):
    th = current()
    win = tk.Toplevel(parent)
    win.title(name)
    win.configure(bg=th["panel"])
    win.viewer_name = name
    return win, th


def _close_btn(win, th, lang, command=None):
    rounded_button(win, text=t("viewer.close", lang), bg=th["accent"],
                   fg="white", command=command or win.destroy).pack(pady=(0, 10))


def open_image_viewer(parent, path, name, lang="en", on_saved=None):
    """Large view of one image file with zoom/rotate controls.
    Returns the Toplevel (or a detail viewer when the file cannot
    be rendered as an image)."""
    try:
        with Image.open(path) as im:
            im.load()
            img = im.copy()
    except Exception:
        _ok, msg = preview_available(path, lang)
        return open_detail_viewer(parent, name, msg, lang)
    win, th = _shell(parent, name, lang)
    maxw = max(200, win.winfo_screenwidth() - 80)
    maxh = max(200, win.winfo_screenheight() - 260)
    state = {"rotation": 0, "zoom": 1.0}
    win.viewer_path = path
    win.viewer_rotation = 0
    win.viewer_zoom = 1.0

    bar = tk.Frame(win, bg=th["panel"]); bar.pack(fill="x", padx=10, pady=(10, 0))
    canvas = tk.Canvas(win, bg=th["panel"], highlightthickness=0,
                       width=min(maxw, 900), height=min(maxh, 620))
    sb_y = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
    sb_x = tk.Scrollbar(win, orient="horizontal", command=canvas.xview)
    canvas.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)
    sb_y.pack(side="right", fill="y"); sb_x.pack(side="bottom", fill="x")
    canvas.pack(side="top", fill="both", expand=True, padx=10, pady=10)

    def _render():
        disp = rotate_image(img, state["rotation"])
        w, h = disp.size
        fit = min(maxw / w, maxh / h, 1.0)
        scale = fit * state["zoom"]
        if scale != 1.0:
            disp = disp.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                               Image.LANCZOS)
        photo = ImageTk.PhotoImage(disp, master=win)
        win.viewer_photo = photo
        win.viewer_size = (photo.width(), photo.height())
        cw = max(canvas.winfo_width(), photo.width())
        ch = max(canvas.winfo_height(), photo.height())
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, image=photo)
        canvas.configure(scrollregion=(0, 0, cw, ch))
        win.viewer_rotation = state["rotation"]
        win.viewer_zoom = state["zoom"]

    def _zoom(factor):
        state["zoom"] = min(ZOOM_MAX, max(ZOOM_MIN, state["zoom"] * factor))
        _render()

    def _rotate(step):
        state["rotation"] = (state["rotation"] + step) % 360
        _render()

    def _fit():
        state["zoom"] = 1.0
        _render()

    def _wheel(e):
        _zoom(ZOOM_STEP if (getattr(e, "delta", 0) > 0 or getattr(e, "num", 0) == 4)
              else 1 / ZOOM_STEP)
        return "break"

    for txt, cmd in ((r38_t("viewer.zoom_out", lang), lambda: _zoom(1 / ZOOM_STEP)),
                     (r38_t("viewer.zoom_in", lang), lambda: _zoom(ZOOM_STEP)),
                     (r38_t("viewer.fit", lang), _fit),
                     (r38_t("viewer.rotate_left", lang), lambda: _rotate(-90)),
                     (r38_t("viewer.rotate_right", lang), lambda: _rotate(90))):
        rounded_button(bar, text=txt, bg=th["card"], fg=th["text"],
                       command=cmd).pack(side="left", padx=2)
    win.viewer_zoom_in = lambda: _zoom(ZOOM_STEP)   # test hooks
    win.viewer_zoom_out = lambda: _zoom(1 / ZOOM_STEP)
    win.viewer_rotate = _rotate
    for _ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        canvas.bind(_ev, _wheel)

    def _request_close():
        if state["rotation"] % 360:
            if messagebox.askyesno(r38_t("viewer.save_title", lang),
                                   r38_t("viewer.save_msg", lang), parent=win):
                try:
                    save_rotated(path, img, state["rotation"])
                    if on_saved is not None:
                        on_saved()
                except Exception:
                    pass
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", _request_close)
    win.bind("<Escape>", lambda _e: _request_close())
    _close_btn(win, th, lang, command=_request_close)
    win.update_idletasks()
    _render()
    return win


def open_detail_viewer(parent, name, text, lang="en"):
    """In-app detail view for a non-image file (metadata text)."""
    win, th = _shell(parent, name, lang)
    win.detail_text = text
    win.bind("<Escape>", lambda _e: win.destroy())
    tk.Label(win, text=text, bg=th["panel"], fg=th["text"],
             font=("Segoe UI", 10), wraplength=560, justify="left",
             padx=14, pady=12).pack()
    _close_btn(win, th, lang)
    return win
