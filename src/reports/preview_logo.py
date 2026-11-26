"""Round 57, Section B: centre logo in the print preview window.

The four PDFs already embed the logo (round 30), but every print
preview renders PLAIN TEXT only (print_preview._lines / the
*_preview_lines helpers), so a set logo never showed in the window
the owner actually looks at -- his prescription preview showed the
plain centred name/contact lines with no logo, although the logo
was set. preview_logo_label() packs one centred logo image above
the preview text when a logo is set, and packs nothing (returning
None) when unset, so the no-logo preview is unchanged. <200 lines.
"""
import tkinter as tk

from src.reports.centre_logo import get_logo_path

MAX_W, MAX_H = 160, 64  # thumbnail box; aspect preserved


def preview_logo_label(parent):
    """Centred logo image label packed into `parent`, or None when
    no centre logo is set / the file cannot be read as an image.
    The PhotoImage is kept on the label itself (lbl.image) so Tk
    does not garbage-collect it. The label's bg matches the parent
    window so the image sits on the preview background."""
    path = get_logo_path()
    if path is None:
        return None
    try:
        from PIL import Image, ImageTk
        im = Image.open(path)
        im.thumbnail((MAX_W, MAX_H))
        photo = ImageTk.PhotoImage(im)
    except Exception:
        return None
    lbl = tk.Label(parent, image=photo, bg=parent.cget("bg"))
    lbl.image = photo
    lbl.pack(fill="x", padx=12, pady=(2, 0))
    return lbl
