"""Round 15 clinical-table style (2026-11-10).

The four clinical tables (complaint / symptoms / diagnosis /
procedures) live in the app's MAIN iOS27 colour family (violet /
magenta / coral / teal) with PROGRESSIVE darkening: each table's
background is darker (lower relative luminance) than the previous
one, in light mode and in dark mode alike. Every text pair on every
table is >= 4.5:1 (WCAG) -- see tests/test_clinical_tables_r15.py,
which asserts the luminance order and every ratio from these exact
values, so change a colour only with the test.

Light mode: pale tints, dark text (#2C241D) + a deep title colour
per table (also the Add-button fill, white on it). Dark mode: deep
saturated fills, near-white text (#F5F0EB) + white titles (the Add
button reuses the table fill, white on it).

Also here: r15_t() (round-15 strings, same fallback pattern as
template_manager._r15), the clipboard bind shared by the tables,
the internal-wheel bind that makes a compact (height=2) field scroll
INSIDE itself instead of scrolling the page, and build_field_row()
(the compact field + small notes field + picker button row).
<200 lines."""
import tkinter as tk
from tkinter import ttk
from src.config.strings import t
from src.config.theme import current, is_dark
from src.ui.clipboard_picker import bind_clipboard_picker
from src.ui.phrase_picker import attach_picker_button
from src.ui.rounded_lists import RoundedText

try:
    from src.config.strings_r15_clinical import EN as _R15_EN, AR as _R15_AR
except ImportError:
    _R15_EN, _R15_AR = {}, {}

ORDER = ("complaint", "symptom", "diagnosis", "procedure")
# (background, title colour) per table, in display order.
_LIGHT = {"complaint": ("#EDE9FE", "#4C1D95"), "symptom": ("#FBCFE8", "#9D174D"),
          "diagnosis": ("#FDBA74", "#7C2D12"), "procedure": ("#2DD4BF", "#134E4A")}
_DARK = {"complaint": ("#6D28D9", "#FFFFFF"), "symptom": ("#9D174D", "#FFFFFF"),
         "diagnosis": ("#7C2D12", "#FFFFFF"), "procedure": ("#042F2E", "#FFFFFF")}
BODY_LIGHT, BODY_DARK = "#2C241D", "#F5F0EB"
BROWN_HEADER = "#7A3F16"  # reference Overview-panel header brown; white on it is 8.23:1


def table_colors(kind, dark=False):
    """{"bg","title_fg","body_fg","btn_bg"} for one table kind."""
    bg, title = (_DARK if dark else _LIGHT)[kind]
    return {"bg": bg, "title_fg": title,
            "body_fg": BODY_DARK if dark else BODY_LIGHT,
            "btn_bg": bg if dark else title}


def luminance(hexcol):
    """Relative luminance of a #RRGGBB colour (WCAG)."""
    r, g, b = (int(str(hexcol)[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg, bg):
    """WCAG contrast ratio between two #RRGGBB colours."""
    a, b = luminance(fg), luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def r15_t(key, lang="en"):
    """Round-15 string: prefer strings_r15_clinical (the coordinator
    wires it into t() later); fall back to t() meanwhile."""
    d = _R15_AR if lang == "ar" else _R15_EN
    return d.get(key) or t(key, lang)


def bind_field(tab, widget, name):
    """Clipboard multi-paste binding + registry entry for a field."""
    bind_clipboard_picker(widget)
    tab.clipboard_fields[name] = widget


def bind_inner_wheel(widget):
    """Wheel over a compact field scrolls the field ITSELF, never the
    page: the handler scrolls the inner Text and returns "break", so
    neither Tk's class binding nor the page canvas's bind_all handler
    (wheel_scroll.py) also scrolls. Bound on the inner tk.Text -- the
    widget actually under the pointer (RoundedText is a Frame around
    it). Works for <MouseWheel> (Windows) and <Button-4/5> (X11)."""
    inner = getattr(widget, "widget", None) or getattr(widget, "_inner", None) or widget

    def _scroll(event):
        if getattr(event, "num", None) in (4, 5):
            steps = -1 if event.num == 4 else 1
        elif getattr(event, "delta", 0):
            steps = -1 if event.delta > 0 else 1
        else:
            return
        try:
            inner.yview_scroll(steps, "units")
        except Exception:
            pass
        return "break"

    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        try:
            inner.bind(seq, _scroll)
        except Exception:
            pass


def build_field_row(tab, frm, kind, widget_attr, label, height=2):
    """One compact labelled field on a coloured table: the main Text
    (height 2 -- about half the old 3-line fields) on the left with
    its own thin scrollbar, a SMALL notes Text beside it on the
    right, and the template picker button in the header row. The
    Text backgrounds ARE the table colour (not white), so the table
    reads as one coloured surface. Returns the main Text widget."""
    th = current()
    lang = getattr(tab.app, "lang", "en")
    bg = frm["bg"]
    cols = table_colors(kind, is_dark())
    hdr = tk.Frame(frm, bg=bg)
    hdr.pack(fill="x", padx=4, pady=(2, 0))
    tk.Label(hdr, text=label, bg=bg, fg=cols["title_fg"],
             font=("Segoe UI", 9, "bold")).pack(side="left")
    row = tk.Frame(frm, bg=bg)
    row.pack(fill="x", padx=4, pady=1)
    txt = RoundedText(row, height=height, font=("Segoe UI", 10), wrap="word",
                      bg=bg, fg=cols["body_fg"])
    txt.pack(side="left", fill="both", expand=True)
    sb = ttk.Scrollbar(row, orient="vertical", command=txt.yview)
    sb.pack(side="left", fill="y")
    txt.configure(yscrollcommand=sb.set)
    setattr(tab, widget_attr, txt)
    bind_field(tab, txt, kind)
    bind_inner_wheel(txt)
    note_frm = tk.Frame(row, bg=bg)
    note_frm.pack(side="right", fill="y", padx=(6, 0))
    tk.Label(note_frm, text=t("savegate.note", lang), bg=bg, fg=cols["title_fg"],
             font=("Segoe UI", 8)).pack(anchor="w")
    note = RoundedText(note_frm, height=height, width=18, font=("Segoe UI", 9),
                       wrap="word", bg=bg, fg=cols["body_fg"])
    note.pack(fill="y")
    setattr(tab, f"{widget_attr}_note", note)
    bind_field(tab, note, f"{kind}_note")
    bind_inner_wheel(note)
    btn = attach_picker_button(hdr, kind, txt, tab.current_user)
    # Round 19: tables are quarter-width (one row of four), so the
    # picker button is ICON-ONLY here - the full "📋 Templates"
    # text (90px) + the field label would clip past the table edge
    # at the real app width. Same button, same picker command.
    btn.config(text="📋", padx=6)
    btn.pack(side="right", padx=2)
    tab.picker_buttons[kind] = btn
    return txt


# Round 19 (items 3 + 7): stacked-section colours for the clinical
# RIGHT area (history / referrals) and the patient-info block.
# Every section frame colour is CLEARLY different from the app
# background and panel in BOTH themes (asserted programmatically
# in tests/test_r19_layout.py: colour != bg and != panel), and
# neighbouring sections never share a colour.
STACK_LIGHT = {"history": "#FFEDD5", "referrals": "#DBEAFE",
               "info": "#E8DCC4"}
STACK_DARK = {"history": "#7C2D12", "referrals": "#1E3A5F",
              "info": "#3E2723"}


def stack_color(name, dark=False):
    """Background colour for a stacked clinical section / info block."""
    return (STACK_DARK if dark else STACK_LIGHT)[name]


def distinct_from_bg(color, dark=False):
    """True when `color` differs from the app bg AND panel tokens
    of the requested theme (item 7's programmatic frame check)."""
    from src.config.theme import tokens
    th = tokens(dark)
    return str(color).upper() not in (th["bg"].upper(), th["panel"].upper())
