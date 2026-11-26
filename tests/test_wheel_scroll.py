"""Job 1 (round 12): mouse-wheel scrolling regression.

Before the fix only settings_ui.py bound the wheel (bind_all,
unscoped). The clinical page, patient form and clipboard picker
canvases had NO wheel binding - only dragging the scrollbar worked.
Now bind_canvas_wheel() scopes the wheel to each canvas: it scrolls
when the pointer is over the canvas or a non-scrollable child, and
never hijacks Text/Listbox widgets that need their own scrolling.

GUI tests skip gracefully when no display is available; run with
DISPLAY=:99 under Xvfb.
"""
import tkinter as tk

from src.models.clipboard_history import add_clip
from src.ui.clinical import ClinicalTab
from src.ui.clipboard_picker import open_clipboard_picker
from src.ui.patient_form import PatientForm


def _stub_app():
    class FakeApp:
        lang = "en"
        current_patient = None
        current_user = "fady"
        current_role = "admin"

        def chart_teeth(self):
            return []

        def refresh_clinical(self):
            pass

        def on_teeth_select(self, teeth, typ):
            pass

        def print_pdf(self):
            pass

    return FakeApp()


def _canvas_for(widget):
    """Walk up the widget tree until a tk.Canvas is found."""
    w = widget
    while w is not None:
        if isinstance(w, tk.Canvas):
            return w
        parent = w.winfo_parent()
        if not parent:
            return None
        w = w.nametowidget(parent)
    return None


def _walk(widget):
    yield widget
    for ch in widget.winfo_children():
        yield from _walk(ch)


def _build_tab():
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.withdraw()
    # Deiconify (not withdraw): a withdrawn root stays 1x1, so the
    # canvas would have no height and nothing to scroll. Under Xvfb
    # mapping the window is fine.
    root.deiconify()
    root.geometry("1380x900")
    try:
        tab = ClinicalTab(root, _stub_app())
        tab.pack(fill="both", expand=True)
        root.update()
        return root, tab
    except Exception:
        root.destroy()
        raise


def test_wheel_scrolls_clinical_page():
    root, tab = _build_tab()
    if tab is None:
        print("SKIP test_wheel_scrolls_clinical_page (no display)")
        return
    try:
        # Round 19: the input tables sit in a FIXED block (no canvas);
        # the clinical page's scrollable area is the stacked-sections
        # canvas under it, anchored here by the history section.
        canvas = _canvas_for(tab.history_section)
        assert canvas is not None
        assert canvas.yview()[1] < 1.0, "clinical page not scrollable in test setup"
        # Round 22: the panels moved INTO the main scroll flow and
        # shared the history canvas. ROUND-24 SUPERSESSION: the
        # panels are REMOVED; the anchor is now the unified session
        # tree inside the history section -- same canvas.
        panel_canvas = _canvas_for(tab.tree_history)
        assert panel_canvas is not None and panel_canvas is canvas
        # Wheel over a NON-scrollable child (the history section
        # frame): the canvas must scroll down.
        section = tab.history_section
        before = canvas.yview()[0]
        section.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert canvas.yview()[0] > before, "MouseWheel did not scroll clinical page"
        # Linux/X11 Button-4 scrolls back up.
        before = canvas.yview()[0]
        section.event_generate("<Button-4>")
        root.update()
        assert canvas.yview()[0] < before, "Button-4 did not scroll clinical page up"
        # R56: wheel over a Text moves the TEXT when its content
        # overflows; when it fits, the wheel moves the page.
        tab.txt_complaint.delete("1.0", "end")
        tab.txt_complaint.insert("1.0", "\n".join(
            f"line {i}" for i in range(30)))
        root.update()
        assert tab.txt_complaint.yview() != (0.0, 1.0), \
            "complaint field not overflowing in setup"
        before = canvas.yview()
        tab.txt_complaint.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert canvas.yview() == before, \
            "wheel over overflowing Text hijacked the canvas"
        tab.txt_complaint.delete("1.0", "end")
        root.update()
        before = canvas.yview()[0]
        tab.txt_complaint.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert canvas.yview()[0] > before, \
            "wheel over fitting Text did not scroll page"
    finally:
        root.destroy()


def test_wheel_scrolls_patient_form():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_wheel_scrolls_patient_form (no display)")
        return
    root.withdraw()
    root.deiconify()  # real geometry needed: see _build_tab
    # Round 17: the form has no dental chart any more, so at 800x500
    # its content fits the viewport and nothing can scroll; a shorter
    # window makes the form genuinely overflow again.
    root.geometry("800x320")
    try:
        form = PatientForm(root, _stub_app())
        form.pack(fill="both", expand=True)
        form.show_form()  # round 17: compat shim (form is always visible)
        root.update()
        canvas = _canvas_for(form.e_first)
        assert canvas is not None
        assert canvas.yview()[1] < 1.0, "patient form not scrollable in test setup"
        before = canvas.yview()[0]
        form.lbl_hijri.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert canvas.yview()[0] > before, "MouseWheel did not scroll patient form"
    finally:
        root.destroy()


def test_wheel_scrolls_clipboard_picker():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_wheel_scrolls_clipboard_picker (no display)")
        return
    root.withdraw()
    try:
        for i in range(25):
            add_clip(f"clip item {i:02d} for wheel test")
        win = open_clipboard_picker(root)
        root.update()
        canvas = next((w for w in _walk(win) if isinstance(w, tk.Canvas)), None)
        assert canvas is not None
        assert canvas.yview()[1] < 1.0, "picker list not scrollable in test setup"
        check = next((w for w in _walk(win) if isinstance(w, tk.Checkbutton)), None)
        assert check is not None
        before = canvas.yview()[0]
        check.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert canvas.yview()[0] > before, "MouseWheel did not scroll picker"
        win.destroy()
    finally:
        root.destroy()
