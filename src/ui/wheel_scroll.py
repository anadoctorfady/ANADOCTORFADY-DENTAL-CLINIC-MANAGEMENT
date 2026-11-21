"""Mouse-wheel scrolling for canvas pages (Job 1, round 12; fixed round 14).

ROOT CAUSE (round 14 audit): the round-12 helper called
``canvas.bind_all(...)`` WITHOUT ``add="+"`` — and Tk's ``bind`` REPLACES
the previous "all" binding for that event. Every canvas that registered
stole the wheel from every canvas registered before it. In the real app
the build order is PatientForm -> ClinicalTab -> SettingsTab, so the
SettingsTab handler (itself unscoped) was the only one left alive: the
wheel over the clinical page / patient form did nothing at all, and
after the clipboard picker closed, its dead handler stayed registered
and NO canvas scrolled until a rebuild. That is the owner's "the mouse
does not move the long list".

Fix: every registration now uses ``bind_all(..., add="+")`` so handlers
ACCUMULATE instead of replacing each other, and each handler is still
scoped — it scrolls only when the pointer is over its own canvas (or a
non-scrollable child), and never hijacks Text / Listbox / Treeview
widgets, which need the wheel for their own content. A registry keeps
the live canvases so a canvas nested inside another registered canvas
yields to the deeper one (no double-scroll). Works on Windows
(<MouseWheel>, event.delta) and Linux/X11 (<Button-4>/<Button-5>).

Usage: bind_canvas_wheel(canvas) once, after the canvas exists.
orient="horizontal" scrolls xview (dental chart: no vertical content).
"""
import tkinter as tk
from tkinter import ttk

_REGISTRY = []  # [[canvas, orient]] — live registered canvases


def _is_scrollable(widget):
    """Widgets that own their own vertical scrolling."""
    if isinstance(widget, (tk.Text, tk.Listbox, ttk.Treeview)):
        return True
    # Rounded wrappers (round 13) are Frames around the real widget:
    # a wheel event generated on the wrapper must still count as a
    # wheel over its inner Text/Listbox, or the canvas steals it.
    inner = getattr(widget, "_inner", None)
    return isinstance(inner, (tk.Text, tk.Listbox, ttk.Treeview))


def _steps(event):
    """Wheel direction as +/-1 unit, or None when there is no wheel."""
    if getattr(event, "num", None) in (4, 5):
        return -1 if event.num == 4 else 1
    delta = getattr(event, "delta", 0)
    if delta:
        return -1 if delta > 0 else 1
    return None


def bind_canvas_wheel(canvas, orient="vertical"):
    """Register `canvas` for scoped wheel scrolling.

    Safe to call for any number of canvases, in any order, in any tab:
    handlers accumulate (add="+") and each one only fires for its own
    subtree. A destroyed canvas unregisters itself via <Destroy>.
    """
    entry = [canvas, orient]
    _REGISTRY.append(entry)

    def _forget(_event, _entry=entry):
        try:
            _REGISTRY.remove(_entry)
        except ValueError:
            pass

    canvas.bind("<Destroy>", _forget, add="+")
    prefix = str(canvas)

    def _wheel(event):
        try:
            if not canvas.winfo_exists():
                return
            w = event.widget
        except Exception:
            return
        # Only when the pointer is over this canvas or its contents.
        # (The inner frame is a canvas window item whose parent IS the
        # canvas, so its descendants' paths start with the canvas path.)
        if not str(w).startswith(prefix):
            return
        if _is_scrollable(w):
            return  # let the Text/Listbox/Treeview scroll itself
        # Deepest registered canvas containing the pointer wins, so a
        # nested canvas never double-scrolls its parent as well.
        for other, _o in _REGISTRY:
            if (other is not canvas and other.winfo_exists()
                    and str(w).startswith(str(other))
                    and len(str(other)) > len(prefix)):
                return
        steps = _steps(event)
        if steps is None:
            return
        try:
            if orient == "horizontal":
                canvas.xview_scroll(steps, "units")
            else:
                canvas.yview_scroll(steps, "units")
        except Exception:
            pass

    # add="+": WITHOUT it, this bind_all call would REPLACE the wheel
    # handler of every canvas registered before it (Tk bind semantics)
    # and only the last-registered canvas would ever scroll.
    canvas.bind_all("<MouseWheel>", _wheel, add="+")
    canvas.bind_all("<Button-4>", _wheel, add="+")
    canvas.bind_all("<Button-5>", _wheel, add="+")
    return _wheel
