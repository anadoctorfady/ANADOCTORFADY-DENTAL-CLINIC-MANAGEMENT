"""Dental chart: AI photorealistic tooth PNGs. <200 lines.

Teeth are AI-generated PNGs in assets/teeth/ (permanent + deciduous;
48x96 RGBA, transparent); if they cannot load, the chart falls back
to tooth-glyph buttons, never crashing. Click a tooth to select /
deselect it. Display order is the clinical view facing the patient:
upper 18..11 | 21..28, lower 48..41 | 31..38 (deciduous 55..51 |
61..65, 85..81 | 71..75); images follow FDI number. Round 15:
upper-jaw images are flipped vertically at load (tooth_image.py)
and every surface uses the MAIN background th["bg"]. Round 16: a
treated tooth keeps a persistent tick + accent border. Round 23
(item 3): a treated tooth also shows a count badge (xN = saved
entries), a HOVER TOOLTIP with its full procedure history and a
history POPUP on double-click / tick-badge click (chart_tooltip +
chart_status glue); a plain click keeps toggling the selection."""
import tkinter as tk
from pathlib import Path

from src.config.strings import t
from src.config.strings_r16_clinical import r16_t
from src.config.theme import current, is_dark, RADIUS_ICON; from src.ui.rounded_frame import RoundedFrame; from src.ui import chart_jaw as _jaw  # R41
from src.ui import chart_status as _status
from src.ui.chart_tooltip import ToothTooltip, format_history
from src.ui.tooth_image import load_tooth_images
from src.ui.tooth_map import display_order, tooth_image_name, tooth_type_for
from src.ui.wheel_scroll import bind_canvas_wheel
from src.utils.helpers import PERMANENT, DECIDUOUS

TEETH_DIR = Path(__file__).resolve().parents[2] / "assets" / "teeth"
TOOTH_GLYPH = "🦷"  # fallback only, when the PNG assets cannot load


def _title_fg(th):
    """Title colour: darker brown #7A3F16 in light mode (7.36:1 on
    the main bg); the dark accent passes as-is."""
    return th["accent"] if is_dark() else "#7A3F16"


class DentalChartFrame(tk.Frame):
    def __init__(self, parent, lang="en", on_select=None, **kw):
        th = current()
        super().__init__(parent, bg=th["bg"], **kw)
        self.lang, self.on_select = lang, on_select
        self.selected = set()
        self.treated = set()  # round 16: teeth with a recorded procedure
        self.treated_details = {}  # round 23: tooth -> [history entries]
        self._tip = ToothTooltip(self)  # round 23: hover tooltip surface
        self._history_win = None  # round 23: open history popup, if any
        self.tooth_cells = {}   # FDI number -> cell frame (for tests)
        self.tooth_type = tk.StringVar(value="دائم")
        self._images = self._load_images()
        hdr = tk.Frame(self, bg=th["bg"]); hdr.pack(fill="x", padx=8, pady=6)
        tk.Label(hdr, text=t("chart.title", self.lang), bg=th["bg"], fg=_title_fg(th), font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Radiobutton(hdr, text=t("chart.permanent", self.lang), variable=self.tooth_type, value="دائم",
                       bg=th["bg"], fg=th["text"], command=self.refresh).pack(side="left", padx=10)
        tk.Radiobutton(hdr, text=t("chart.deciduous", self.lang), variable=self.tooth_type, value="لبني",
                       bg=th["bg"], fg=th["text"], command=self.refresh).pack(side="left")
        _jaw.build_buttons(self, hdr)  # R41 item 3: all / upper / lower shortcuts
        # Scrollable area: canvas stretches the inner frame to its width.
        self._canvas = tk.Canvas(self, bg=th["bg"], highlightthickness=0)
        self._hsb = tk.Scrollbar(self, orient="horizontal", command=self._canvas.xview)
        self._canvas.configure(xscrollcommand=self._hsb.set)
        self._canvas.pack(fill="both", expand=True, padx=6, pady=(0, 2))
        self._hsb.pack(fill="x", padx=6, pady=(0, 4))
        self.area = tk.Frame(self._canvas, bg=th["bg"])
        self._canvas.create_window((0, 0), window=self.area, anchor="nw", tags="inner")
        self.area.bind("<Configure>", self._fit); self._canvas.bind("<Configure>", self._fit)
        bind_canvas_wheel(self._canvas, orient="horizontal")  # round 14: wheel scrolls the jaw
        self.refresh()

    def _load_images(self):
        """All 52 tooth PhotoImages ({} on failure: glyph fallback)."""
        return load_tooth_images(self, TEETH_DIR)

    def _fit(self, _e=None):
        """Stretch inner frame to canvas width, or scroll if wider."""
        try:
            req = self.area.winfo_reqwidth()
            w = max(self._canvas.winfo_width(), req)
            if self._canvas.itemcget("inner", "width") != str(w):
                self._canvas.itemconfigure("inner", width=w)
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        except Exception:
            pass

    def _tooth_cell(self, grid, col, n):
        """One clickable tooth cell: image (or glyph fallback) + number.
        A treated tooth keeps its number label exactly as the number,
        and gains an accent border + a tick + (round 23) a count badge
        below the number, in _title_fg / the selection fg (>= 4.5:1)."""
        th = current()
        sel = n in self.selected; treated = n in self.treated
        bg = th["accent"] if sel else th["bg"]
        fg = ("white" if not is_dark() else "#241A12") if sel else th["text"]  # selected: readable on accent
        cell = RoundedFrame(grid, bg=bg, border=th["accent"] if (sel or treated) else th["border"], radius=RADIUS_ICON, pad=1)
        cell.grid(row=0, column=col, padx=1, pady=2, sticky="ew")
        img_name = tooth_image_name(n)
        if img_name and img_name in self._images:
            pic = tk.Label(cell.inner, image=self._images[img_name], bg=bg)
        else:  # graceful fallback: glyph button look, same selection
            pic = tk.Label(cell.inner, text=TOOTH_GLYPH, bg=bg, fg=fg, font=("Segoe UI", 16))
        pic.pack(pady=(2, 0))
        num = tk.Label(cell.inner, text=n, bg=bg, fg=fg, font=("Segoe UI", 8, "bold"))
        num.pack(pady=(0, 2))
        widgets = [cell, cell.inner, pic, num]
        if treated:
            tick_fg = fg if sel else _title_fg(th)
            mark = tk.Frame(cell.inner, bg=bg); mark.pack(pady=(0, 2))
            tick = tk.Label(mark, text="✓", bg=bg, fg=tick_fg, font=("Segoe UI", 8, "bold")); tick.pack(side="left")
            widgets += [mark, tick]
            entries = self.treated_details.get(n) or []
            if entries:  # round 23: persistent count badge, e.g. x2
                badge = tk.Label(mark, text=f"×{len(entries)}", bg=bg, fg=tick_fg, font=("Segoe UI", 8, "bold"))
                badge.pack(side="left"); widgets.append(badge)
                badge.bind("<Button-1>", lambda _e, nn=n: self.show_tooth_history(nn))
            # Tick click = history popup (NOT a toggle: the tick is
            # deliberately outside the toggle bind list below).
            tick.bind("<Button-1>", lambda _e, nn=n: self.show_tooth_history(nn))
            _status.bind_treated_cell(self, widgets, n)  # hover tip + double-click
        for w in (cell, cell.inner, pic, num):
            w.bind("<Button-1>", lambda _e, nn=n: self.toggle(nn))
        self.tooth_cells[n] = cell

    def tooltip_text_for(self, n):
        """Tooltip text the chart shows for tooth `n` ('' if untreated)."""
        entries = self.treated_details.get(str(n)) or []
        return format_history(str(n), entries, self.lang) if entries else ""

    def show_tooth_history(self, n):
        """Click surface: popup with tooth `n`'s procedures + dates."""
        return _status.open_chart_history(self, str(n))

    def refresh(self):
        self._tip.hide()  # round 23: no tooltip may outlive its cell
        for w in self.area.winfo_children():
            w.destroy()
        self.tooth_cells = {}
        th = current()
        nums = PERMANENT if self.tooth_type.get() == "دائم" else DECIDUOUS

        def jaw(title, ns, jaw_name):
            frm = RoundedFrame(self.area, bg=th["bg"], border=th["border"], title=title, title_fg=_title_fg(th)); frm.pack(fill="x", pady=4); frm = frm.inner
            grid = tk.Frame(frm, bg=th["bg"]); grid.pack(fill="x")
            ordered = display_order(ns, jaw_name); half = len(ordered) // 2
            for i, n in enumerate(ordered):
                col = i + (1 if i >= half else 0)  # column `half` = midline gap
                grid.columnconfigure(col, weight=1, uniform="tooth")
                self._tooth_cell(grid, col, n)
            grid.columnconfigure(half, minsize=10)

        if self.tooth_type.get() == "دائم":
            jaw(t("chart.upper_jaw", self.lang), nums[0:16], "upper")
            jaw(t("chart.lower_jaw", self.lang), nums[16:32], "lower")
        else:
            jaw(t("chart.upper_deciduous", self.lang), nums[0:10], "upper")
            jaw(t("chart.lower_deciduous", self.lang), nums[10:20], "lower")
        sel = ", ".join(sorted(self.selected)) if self.selected else t("chart.none", self.lang)
        tk.Label(self.area, text=t("chart.selected_fmt", self.lang).format(sel=sel), bg=th["bg"], fg=th["muted"]).pack(pady=4)
        tk.Label(self.area, text=r16_t("r16.chart.legend", self.lang), bg=th["bg"], fg=th["muted"]).pack(pady=(0, 4))  # round 16 legend
        self.area.update_idletasks(); self._canvas.configure(height=self.area.winfo_reqheight())

    def toggle(self, n):
        self.selected.discard(n) if n in self.selected else self.selected.add(n)
        self.refresh()
        if self.on_select:
            self.on_select(sorted(self.selected), self.tooth_type.get())

    def set_selection(self, teeth, typ="دائم"):
        # No-op when nothing changed (avoids rebuilding all cells).
        teeth = set(teeth or [])
        if teeth == self.selected and typ == self.tooth_type.get(): return
        self.selected = teeth; self.tooth_type.set(typ); self.refresh()

    def set_treated(self, teeth):
        """Teeth with a recorded procedure/diagnosis for this patient
        (tick + accent border; no-op when unchanged). Round 23:
        details for teeth no longer treated are dropped, so stale
        tooltip/popup text can never survive a patient switch."""
        teeth = set(teeth or [])
        self.treated_details = {n: e for n, e in self.treated_details.items() if n in teeth}
        if teeth == self.treated: return
        self.treated = teeth; self.refresh()

    def set_treated_details(self, details):
        """Round 23: set treated teeth WITH history entries
        ({tooth: [entries]}), replaced atomically -- an empty map
        (patient with no procedures / clear()) removes every mark,
        badge, tooltip and popup text of the previous patient."""
        details = {str(n): list(e) for n, e in (details or {}).items() if e}
        if details == self.treated_details and set(details) == self.treated: return
        self.treated_details = details; self.treated = set(details); self.refresh()

    def get_treated_details(self):
        return {n: list(e) for n, e in self.treated_details.items()}

    def get_treated(self):
        return sorted(self.treated)

    def get_selection(self):
        return sorted(self.selected), self.tooth_type.get()
