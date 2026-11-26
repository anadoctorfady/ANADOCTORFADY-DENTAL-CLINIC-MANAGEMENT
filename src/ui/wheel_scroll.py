"""Mouse-wheel scrolling for canvas pages (round 12; fixed round 14).

Round 14 root cause: bind_canvas_wheel() called canvas.bind_all()
WITHOUT add="+", and Tk's bind REPLACES the previous "all" binding --
only the last-registered canvas ever scrolled. Now every registration
uses add="+", and each handler stays scoped to its own canvas subtree.
Windows (<MouseWheel>) and Linux/X11 (<Button-4>/<Button-5>).

ROUND 56 -- GLOBAL PAGE SCROLL (owner's ask): the wheel must move the
CURRENT page even when the pointer is over a table with rows in it.
Bound ONCE in install_page_wheel() (the App calls it at startup).
The delegate is a CLASS binding replacing Tk's default
Treeview/Listbox wheel binding, returning "break" so nothing
double-scrolls. It scrolls the CONTAINING page (deepest registered
canvas in the widget's ancestor chain); when the widget lives in no
page, or the page itself cannot scroll (it fits), the widget scrolls
itself instead -- so the wheel is never swallowed. Text fields keep
their own wheel when their content overflows; when it fits, the
wheel scrolls the page. Tile grids, the calendar grid and the dental
chart are non-scrollable children of their page canvas, so the page
handler scrolls the page over them (the chart's old horizontal wheel
binding was removed; the jaw still scrolls via its scrollbar).

Usage: bind_canvas_wheel(canvas) once per scroll page;
install_page_wheel(root) once per app.
"""
import tkinter as tk
from tkinter import ttk

_REGISTRY = []  # [[canvas, orient]] -- live registered canvases


def _is_scrollable(widget):
    """Widgets that own their own vertical scrolling."""
    if isinstance(widget, (tk.Text, tk.Listbox, ttk.Treeview)):
        return True
    # Rounded wrappers are Frames around the real widget: a wheel
    # event on the wrapper must still count as one over its inner
    # Text/Listbox, or the canvas steals it.
    inner = getattr(widget, "_inner", None)
    return isinstance(inner, (tk.Text, tk.Listbox, ttk.Treeview))


def _text_overflows(widget):
    """True when the tk.Text behind `widget` (itself, or its _inner)
    has more content than its viewport (its own wheel must win)."""
    text = widget if isinstance(widget, tk.Text) else getattr(
        widget, "_inner", None)
    if not isinstance(text, tk.Text):
        return False
    try:
        first, last = text.yview()
        return first > 0.0 or last < 1.0
    except Exception:
        return False


def _steps(event):
    """Wheel direction as +/-1 unit, or None when there is no wheel."""
    if getattr(event, "num", None) in (4, 5):
        return -1 if event.num == 4 else 1
    delta = getattr(event, "delta", 0)
    if delta:
        return -1 if delta > 0 else 1
    return None


def _contains(canvas, widget):
    """True when `widget` is `canvas` or lives inside it."""
    try:
        prefix, path = str(canvas), str(widget)
    except Exception:
        return False
    return path == prefix or path.startswith(prefix + ".")


def page_canvas_for(widget):
    """Deepest live registered canvas containing `widget`, or None
    when it lives in no scroll page (deepest wins, no double-scroll)."""
    best = None
    for other, _o in _REGISTRY:
        try:
            if other.winfo_exists() and _contains(other, widget):
                if best is None or len(str(other)) > len(str(best)):
                    best = other
        except Exception:
            continue
    return best


def _orient_of(canvas):
    for other, orient in _REGISTRY:
        if other is canvas:
            return orient
    return "vertical"


def _page_can_scroll(page):
    # True when the page has content beyond its viewport in its
    # own orientation (view != (0.0, 1.0)).
    try:
        v = page.xview() if _orient_of(page) == "horizontal" else page.yview()
        return v != (0.0, 1.0)
    except Exception:
        return False


def _delegate_wheel(event):
    """R56 class-binding handler for Treeview/Listbox wheels:
    scroll the containing page when it can scroll, else the
    widget itself (no page, or a page that fits), then "break"."""
    try:
        w = event.widget
    except Exception:
        return "break"
    steps = _steps(event)
    if steps is None:
        return "break"
    page = page_canvas_for(w)
    try:
        if page is not None and _page_can_scroll(page):
            if _orient_of(page) == "horizontal":
                page.xview_scroll(steps, "units")
            else:
                page.yview_scroll(steps, "units")
        else:
            w.yview_scroll(steps, "units")
    except Exception:
        pass
    return "break"


def install_page_wheel(root):
    """R56: install the ONE central Treeview/Listbox wheel policy
    for the whole app (call once, at startup -- the App does):
    replaces Tk's default class bindings for <MouseWheel> /
    <Button-4> / <Button-5> with the delegate. Idempotent."""
    for cls in ("Treeview", "Listbox"):
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            root.bind_class(cls, ev, _delegate_wheel)
    return True


def bind_canvas_wheel(canvas, orient="vertical"):
    """Register `canvas` for scoped wheel scrolling (add="+"
    handlers, each scoped to its own subtree; <Destroy>
    unregisters). R56: Treeview/Listbox wheels never reach here
    (the class delegate "break"s first); an overflowing Text
    keeps its own wheel, a fitting Text scrolls the page."""
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
        if not _contains(canvas, w):
            return  # only this canvas's own subtree
        # R56: Treeview/Listbox wheels are owned by the class
        # delegate (or the native binding when never installed).
        if isinstance(w, (ttk.Treeview, tk.Listbox)):
            return
        if _is_scrollable(w) and _text_overflows(w):
            return  # overflowing Text keeps its own wheel; a
        # fitting field falls through and scrolls the page.
        # Deepest registered canvas containing the pointer wins.
        for other, _o in _REGISTRY:
            if (other is not canvas and other.winfo_exists()
                    and _contains(other, w)
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
    # handler of every canvas registered before it (Tk bind semantics).
    canvas.bind_all("<MouseWheel>", _wheel, add="+")
    canvas.bind_all("<Button-4>", _wheel, add="+")
    canvas.bind_all("<Button-5>", _wheel, add="+")
    return _wheel
