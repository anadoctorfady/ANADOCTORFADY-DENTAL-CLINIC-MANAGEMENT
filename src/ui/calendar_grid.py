"""Month calendar grid + time slots for Appointments. No new dependency:
uses only stdlib `calendar` + tkinter (tkcalendar deliberately avoided -
one more dependency + Win7-era wheel risk for a 7x6 button grid).
<200 lines."""
import calendar
import tkinter as tk
from datetime import date, timedelta
from src.ui.rounded import rounded_button
from src.ui.rounded_frame import RoundedFrame
from src.config.theme import RADIUS_PANEL, RADIUS_BTN

WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday",
               "Friday", "Saturday", "Sunday"]
WEEKDAYS_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس",
               "الجمعة", "السبت", "الأحد"]
WEEKDAYS_SHORT_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WEEKDAYS_SHORT_AR = ["اثن", "ثلا", "أرب", "خمي", "جمع", "سبت", "أحد"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]
MONTHS_AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو",
             "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
# Round 18 (W4): day-cell tint by the day's WORST computed attendance
# (absent > late > attended). Round 24: tints STRENGTHENED (the pale
# round-18 washes were hard to spot against the panel) + a light
# attended tint added. (bg, fg) per mode — every fg >= 4.5:1 on its
# bg (worst 6.26:1, dark late); each bg is a saturated family colour.
DAY_TINTS = {
    False: {"absent": ("#FCA5A5", "#2C241D"), "late": ("#FCD34D", "#2C241D"), "attended": ("#A7F3D0", "#2C241D")},
    True: {"absent": ("#991B1B", "#F5F0EB"), "late": ("#92400E", "#F5F0EB"), "attended": ("#14532D", "#F5F0EB")},
}


def month_weeks(year, month):
    """Weeks of a month as lists of 7 ints (0 = day of another month)."""
    return calendar.monthcalendar(year, month)


def month_day_count(year, month):
    return calendar.monthrange(year, month)[1]


def time_slots():
    """Clinic slots 08:00-23:59: every 30 min 08:00..23:30 + final 23:59."""
    slots, h, m = [], 8, 0
    while (h, m) <= (23, 30):
        slots.append(f"{h:02d}:{m:02d}")
        m += 30
        if m == 60:
            h, m = h + 1, 0
    slots.append("23:59")
    return slots


def next_weekday(from_date, weekday):
    """Next date on/after from_date whose weekday() == weekday (Mon=0)."""
    d = from_date
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d


class MonthCalendar(RoundedFrame):
    """Full month grid (Mon-first). Click a day -> on_select(date)."""

    def __init__(self, parent, on_select=None, lang="en", **kw):
        from src.config.theme import current, is_dark
        self.t = current()
        self._dark = is_dark()
        self.day_status = {}  # date -> worst attendance status (round 18)
        super().__init__(parent, bg=self.t["panel"], border=self.t["border"],
                         radius=RADIUS_PANEL, **kw)
        self.on_select, self.lang = on_select, lang
        today = date.today()
        self.year, self.month, self.selected = today.year, today.month, today
        self.marked = set()  # dates with appointments -> dotted
        self._suspend = 0; self._dirty = False  # R21 item 11: render batching
        self._day_btns = {}
        hdr = tk.Frame(self.inner, bg=self.t["panel"])
        hdr.pack(fill="x", padx=6, pady=(6, 2))
        rounded_button(hdr, text="◀", bg=self.t["card"], fg=self.t["text"],
                  padx=6, pady=2, command=self.prev_month).pack(side="left")
        self.lbl_month = tk.Label(hdr, bg=self.t["panel"], fg=self.t["accent"],
                                  font=("Segoe UI", 11, "bold"))
        self.lbl_month.pack(side="left", expand=True)
        rounded_button(hdr, text="▶", bg=self.t["card"], fg=self.t["text"],
                  padx=6, pady=2, command=self.next_month).pack(side="right")
        grid = tk.Frame(self.inner, bg=self.t["panel"])
        grid.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        short = WEEKDAYS_SHORT_AR if lang == "ar" else WEEKDAYS_SHORT_EN
        for c, name in enumerate(short):
            tk.Label(grid, text=name, bg=self.t["panel"], fg=self.t["muted"],
                     font=("Segoe UI", 9, "bold")).grid(row=0, column=c,
                                                        sticky="ew", pady=2)
            grid.columnconfigure(c, weight=1)
        for r in range(6):
            for c in range(7):
                b = rounded_button(grid, font=("Segoe UI", 10),
                              bg=self.t["panel"], fg=self.t["text"], padx=2, pady=2, radius=RADIUS_BTN,
                              command=lambda r=r, c=c: self._click(r, c))
                b.grid(row=r + 1, column=c, sticky="nsew", padx=1, pady=1)
                grid.rowconfigure(r + 1, weight=1)
                self._day_btns[(r, c)] = b
        self._render()

    def month_label(self):
        m = MONTHS_AR[self.month - 1] if self.lang == "ar" \
            else MONTHS_EN[self.month - 1]
        return f"{m} {self.year}"

    def prev_month(self):
        self.month -= 1
        if self.month == 0:
            self.month, self.year = 12, self.year - 1
        self._render()

    def next_month(self):
        self.month += 1
        if self.month == 13:
            self.month, self.year = 1, self.year + 1
        self._render()

    def select(self, d):
        """Jump to d's month and select it (also fires on_select)."""
        self.year, self.month, self.selected = d.year, d.month, d
        self._render()
        if self.on_select:
            self.on_select(d)

    def _render_soon(self):
        """Render now, or (inside a batch) once at end_batch()."""
        if self._suspend: self._dirty = True
        else: self._render()

    def begin_batch(self):
        self._suspend += 1

    def end_batch(self):
        self._suspend = max(0, self._suspend - 1)
        if not self._suspend and self._dirty:
            self._dirty = False; self._render()

    def set_marked(self, dates):
        self.marked = set(dates)
        self._render_soon()

    def set_day_status(self, mapping):
        """{date | 'YYYY-MM-DD': 'absent'|'late'|'attended'|None} —
        the day's WORST attendance (caller computes it, e.g. via
        models.appointments.day_attendance). Round 24: all three
        states tint (attended = green family); pending keeps normal."""
        from src.config.theme import is_dark
        self._dark = is_dark()
        self.day_status = {}
        for k, v in dict(mapping or {}).items():
            try:
                d = k if hasattr(k, "isoformat") else date.fromisoformat(str(k)[:10])
            except Exception:
                continue
            if v in ("absent", "late", "attended"):
                self.day_status[d] = v
        self._render_soon()

    def _click(self, r, c):
        weeks = month_weeks(self.year, self.month)
        if r < len(weeks) and weeks[r][c]:
            self.select(date(self.year, self.month, weeks[r][c]))

    def _render(self):
        self.lbl_month.config(text=self.month_label())
        weeks = month_weeks(self.year, self.month)
        today = date.today()
        for r in range(6):
            for c in range(7):
                b, day = self._day_btns[(r, c)], \
                    weeks[r][c] if r < len(weeks) else 0
                if not day:
                    b.config(text="", state="disabled",
                             bg=self.t["panel"])
                    continue
                d = date(self.year, self.month, day)
                b.config(text=f"{day} •" if d in self.marked else str(day),
                         state="normal")
                tint = DAY_TINTS[bool(getattr(self, "_dark", False))].get(
                    self.day_status.get(d))
                if d == self.selected:
                    b.config(bg=self.t["accent"], fg="white")
                elif tint:  # absent red / late amber / attended green
                    b.config(bg=tint[0], fg=tint[1])
                elif d == today:
                    b.config(bg=self.t["card"], fg=self.t["accent"])
                else:
                    b.config(bg=self.t["panel"], fg=self.t["text"])
