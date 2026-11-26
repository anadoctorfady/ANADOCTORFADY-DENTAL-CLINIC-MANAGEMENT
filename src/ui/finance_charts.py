"""Canvas bar-chart helpers for the Statistics view (Round 49 G).

Plain tk.Canvas drawing, no new dependencies. Colours cycle the
vivid PALETTE (src/ui/vivid_rows.py) with its dark TEXT_ON_VIVID on
the bars; all other text uses the finance theme tokens, so charts
read correctly in light AND dark. An empty item list draws the
localised "No data in this period" message and nothing else.

R51 overlap fix: the row pitch used to be squeezed to fit a fixed
96px canvas (min 13px -- BELOW the ~16px line height of the label
font, so rows and letters collided, exactly as the owner saw).
Now the pitch comes from the MEASURED font linespace (+ padding,
hard minimum 20px), each canvas is resized to its content height
(the Statistics page scrolls when the total exceeds the window),
labels are ellipsised to their measured column width instead of
being cut at a fixed character count, and the page redraws on
width changes (finance_stats binds <Configure>).

R52: the owner STILL saw overlap on Windows in Arabic mode. Root
cause (then): the labels were drawn in "Segoe UI", which has NO
Arabic glyphs -- Windows font fallback substitutes taller Arabic
glyphs whose real height exceeds Segoe UI's measured linespace,
so glyphs collided while every metric said they should not. Fix
by construction: the caller passes the family the labels are
drawn in (Amiri for Arabic -- native Arabic glyphs, truthful
metrics), ALL text items use the very Font objects that were
measured (never a separate font string), and the pitch is that
font's measured linespace + 8. R56: Amiri was REVERTED by the
owner (its linespace made the whole Arabic UI taller) -- labels
are drawn in Segoe UI again, pitch measured from that same font,
and the R55 flattening of multi-line labels (the overlap cause
that actually reproduced) stays; test_r52_charts_scaling asserts
with canvas bboxes that no two rows' text intersects at tk
scaling 1.0/1.25/1.5 in English and Arabic.
"""
import tkinter.font as tkfont

from src.ui.vivid_rows import PALETTE, TEXT_ON_VIVID

_TOP = 8
_MIN_PITCH = 22


def _fmt(value):
    return f"{float(value):,.2f}"


def chart_family(tab):
    """R56: Segoe UI in both languages -- the Amiri branch was
    removed with the revert (amiri_available() is always False
    now). `tab` is any widget of the stats page (language from
    its lang/app attributes, the finance_stats._L rule); kept
    as the callers' seam so the family stays single-sourced."""
    return "Segoe UI"


def _ellipsize(font, text, max_px):
    """Shorten `text` with a trailing ellipsis until it measures
    at most max_px wide in `font` (never a mid-word hard cut)."""
    text = str(text)
    if font.measure(text) <= max_px:
        return text
    while text and font.measure(text + "…") > max_px:
        text = text[:-1]
    return (text + "…") if text else "…"


def draw_hbars(canvas, items, empty_msg, th, fmt=None, family="Segoe UI"):
    """Horizontal bars for [(label, value)]; returns items drawn.
    `fmt` formats the value label (default: money format). `family`
    is the font family labels are DRAWN in -- the pitch is measured
    from that same font object, so rows cannot overlap.

    R55: labels are flattened to ONE line first. A procedure text
    comes from a multi-line entry field, so a label could carry a
    newline ("Temporary filling\\n26, 25, 24, 23, 22"); canvas text
    then renders 2 lines tall, centred on the row, and overlaps
    the rows above and below -- exactly what the owner saw on his
    machine. Flattening (the statistics grouping does the same)
    keeps every label inside its own pitch."""
    fmt = fmt or _fmt
    items = [(" ".join(str(label).split()), value) for label, value in items]
    canvas.delete("all")
    w = max(canvas.winfo_width(), 400)
    canvas.configure(bg=th["panel"])
    # Fonts bind to the CANVAS's interpreter (root=canvas): an
    # unbound Font measures on the default root, whose tk scaling
    # can differ from the canvas's (R52 gate finding).
    font = tkfont.Font(root=canvas, font=(family, 9))
    bold = tkfont.Font(root=canvas, font=(family, 9, "bold"))
    if not items:
        canvas.configure(height=44)
        canvas.create_text(w // 2, 22, text=empty_msg,
                           fill=th["muted"], font=(family, 10))
        return 0
    pitch = max(font.metrics("linespace") + 8, _MIN_PITCH)
    canvas.configure(height=_TOP + pitch * len(items) + 4)
    # Label column sized to the widest label, capped so bars keep
    # at least half the width; value column sized to the widest
    # formatted value. Both measured, never guessed.
    left = min(max(font.measure(str(l)) for l, _v in items) + 16,
               max(w * 2 // 5, 120))
    right = max(bold.measure(fmt(v)) for _l, v in items) + 14
    plot_w = max(w - left - right, 60)
    peak = max(float(v) for _l, v in items) or 1.0
    barh = pitch - 6
    for i, (label, value) in enumerate(items):
        y = _TOP + i * pitch
        cy = y + pitch // 2
        canvas.create_text(left - 8, cy, anchor="e", fill=th["text"],
                           font=font,
                           text=_ellipsize(font, label, left - 16))
        bw = max(int(plot_w * float(value) / peak), 2) if value else 0
        if bw:
            canvas.create_rectangle(left, y + 3, left + bw,
                                    y + 3 + barh,
                                    fill=PALETTE[i % len(PALETTE)],
                                    outline="")
        vtxt = fmt(value)
        if left + bw + 6 + bold.measure(vtxt) <= w - 2:
            canvas.create_text(left + bw + 6, cy, text=vtxt,
                               anchor="w", fill=th["text"], font=bold)
        elif bw > bold.measure(vtxt) + 12:  # no room after the bar:
            canvas.create_text(left + bw - 6, cy, text=vtxt,  # inside it
                               anchor="e", fill=TEXT_ON_VIVID, font=bold)
    return len(items)


def draw_income_vs_expenses(canvas, summary, labels, empty_msg, th,
                            family="Segoe UI"):
    """Three exact-figure rows (Income / Expenses / Net) with bars.
    `labels` = (income, expenses, net) display names. The figures are
    drawn as text beside each bar — exact, not bar-estimated."""
    items = [(labels[0], summary["income"]),
             (labels[1], summary["expenses_total"]),
             (labels[2], summary["net"])]
    if not any(v for _l, v in items):
        return draw_hbars(canvas, [], empty_msg, th, family=family)
    return draw_hbars(canvas, items, empty_msg, th, family=family)


def draw_monthly(canvas, series, empty_msg, th, family="Segoe UI"):
    """Grouped vertical bars: [(yyyy-mm, income, expenses)] — two
    bars per month (income = palette[0], expenses = palette[1]),
    month + both exact values labelled under each group."""
    canvas.delete("all")
    w = max(canvas.winfo_width(), 400)
    canvas.configure(bg=th["panel"])
    vfont = tkfont.Font(root=canvas, font=(family, 7))
    mfont = tkfont.Font(root=canvas, font=(family, 8))
    if not series or not any(inc or exp for _m, inc, exp in series):
        canvas.create_text(w // 2, 30, text=empty_msg,
                           fill=th["muted"], font=(family, 10))
        return 0
    # R52: the label block under the axis is sized from the MEASURED
    # linespaces (at tk scaling 1.5 the old fixed 42px block clipped
    # the month labels against the canvas edge).
    label_block = max(42, vfont.metrics("linespace")
                      + mfont.metrics("linespace") + 14)
    height = max(int(canvas.cget("height")), 10 + 48 + label_block)
    canvas.configure(height=height)
    base_y, top = height - label_block, 10
    peak = max(max(float(i), float(e)) for _m, i, e in series) or 1.0
    slot = max((w - 40) // max(len(series), 1), 40)
    bw = min(slot // 3, 26)
    for i, (ym, inc, exp) in enumerate(series):
        x = 30 + i * slot
        for j, (val, col) in enumerate(((inc, PALETTE[0]),
                                        (exp, PALETTE[1]))):
            bh = int((base_y - top) * float(val) / peak) if val else 0
            if bh:
                canvas.create_rectangle(x + j * (bw + 3), base_y - bh,
                                        x + j * (bw + 3) + bw, base_y,
                                        fill=col, outline="")
            canvas.create_text(x + j * (bw + 3) + bw // 2, base_y + 6,
                               text=_fmt(val), anchor="n",
                               fill=th["text"], font=vfont)
        canvas.create_text(x + bw, base_y + 8 + vfont.metrics("linespace"),
                           text=ym, anchor="n",
                           fill=th["muted"], font=mfont)
    canvas.create_line(20, base_y, w - 10, base_y, fill=th["border"])
    return len(series)
