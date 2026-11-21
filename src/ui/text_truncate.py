"""Ellipsis truncation for single-line labels (Round 13, item 4).

A tk.Label whose wrapped lines are wider than the space pack gives it
gets its text centred and clipped on BOTH edges (seen on the clinical
patient panel: 'Ahmed Mohammed Ali Hassan' lost its 'A' and its 'Ali'
at 11pt bold, wraplength 180, 160px of label). Truncating to the
space the label actually has keeps one clean line, never wider than
the panel. Pure function of (text, font, max width) so the gate can
exercise it without a window.
"""
from tkinter import font as tkfont


def ellipsize(widget, text, max_width, font=None):
    """Return `text` shortened with '…' to fit `max_width` px, measured
    with `widget`'s font (or `font`). Text that already fits, and a
    non-positive width, come back unchanged."""
    if not text or max_width is None or max_width <= 0:
        return text
    f = tkfont.Font(root=widget, font=font or widget.cget("font"))
    if f.measure(text) <= max_width:
        return text
    ell = "…"
    if f.measure(ell) > max_width:
        return ell
    lo, hi = 0, len(text)
    while lo < hi:  # longest prefix that still fits with the ellipsis
        mid = (lo + hi + 1) // 2
        if f.measure(text[:mid] + ell) <= max_width:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo].rstrip() + ell if lo else ell
