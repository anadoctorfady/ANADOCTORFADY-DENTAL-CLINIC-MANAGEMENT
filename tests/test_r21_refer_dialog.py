"""Round 21 (item 7) regression: the Refer-patient dialog must
show BOTH the Templates button and the Save button at small
window sizes, in EN and AR.

Owner report (installed round-20 build, Windows): the dialog
showed NO ready templates and NO Save button. Round 19's layout
packed the buttons frame LAST, after the expanding body, in a
fixed 520x380 window -- with DPI-scaled fonts the content's
requested height exceeds the window and the last-packed frame
is clipped away (the note area, carrying the Templates button,
is squeezed with it). The fix packs the buttons first with
side="bottom" and sizes the window from its content.

This test opens the dialog on 1380x820 and 1280x720 roots, EN
and AR, and asserts both controls are mapped, viewable and
fully inside the dialog; it also forces the dialog SMALLER
than its requested size and asserts both survive the squeeze.
Skips gracefully without a display."""
import tkinter as tk

from tests.test_r19_referrals import _App, _row


def _tk(w, h):
    try:
        root = tk.Tk()
    except Exception:
        return None
    root.geometry(f"{w}x{h}")
    root.update()
    return root


def _inside(win, w):
    top = w.winfo_rooty() - win.winfo_rooty()
    left = w.winfo_rootx() - win.winfo_rootx()
    return (0 <= top and top + w.winfo_height() <= win.winfo_height()
            and 0 <= left and left + w.winfo_width() <= win.winfo_width())


def _check(win, root, label):
    root.update(); win.update_idletasks(); win.update()
    for btn, name in ((win.btn_templates, "templates"),
                      (win.btn_save, "save")):
        assert btn.winfo_ismapped(), (label, name, "unmapped")
        assert btn.winfo_viewable(), (label, name, "not viewable")
        assert btn.winfo_width() >= btn.winfo_reqwidth() - 2, (label, name, "clipped width")
        assert _inside(win, btn), (label, name, "outside dialog")


def test_refer_dialog_buttons_viewable_small_sizes_en_ar():
    from src.ui.refer_dialog import open_refer_dialog
    for geo in ((1380, 820), (1280, 720)):
        for lang in ("en", "ar"):
            root = _tk(*geo)
            if root is None:
                print("SKIP refer dialog (no display)"); return
            try:
                app = _App(patient=_row(1), lang=lang)
                win = open_refer_dialog(app, parent=root)
                assert win is not None
                _check(win, root, f"{geo} {lang}")
                # The squeeze: force the dialog below its requested
                # height -- buttons-first packing must protect both.
                win.geometry("520x300")
                _check(win, root, f"{geo} {lang} squeezed")
                win.destroy()
            finally:
                root.destroy()
