"""Appointments tab: month calendar (right), weekdays (left),
time slots 08:00-23:59, booking form, appointments table. <200 lines.
Custom grid in calendar_grid.py - no tkcalendar dependency. Round 24:
attendance has its OWN column (round 18 appended it to the name cell,
where a long name pushed it past the column edge - invisible);
all three states are coloured via row tags (see load() / ATT_FG)."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from src.config.theme import current, tree_style, is_dark; from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame; from src.ui.rounded_widgets import RoundedEntry; from src.ui.rounded_lists import RoundedListbox; from src.ui.zebra import zebra_tree, zebra_listbox as _zebra_lb
from src.config.strings import t; from src.config.strings_r18_appts import attendance_label
from src.models.database import get_connection
from src.models.appointments import translate_status, attendance_batch, day_attendance
from src.ui.calendar_grid import (MonthCalendar, time_slots,
                                  WEEKDAYS_EN, WEEKDAYS_AR, next_weekday)
from src.ui.quickbook import attach_quickbook, refresh_quickbook

COLUMNS = [("file", 55), ("name", 170), ("date", 95), ("time", 65),
           ("reason", 240), ("status", 80), ("attendance", 115)]
# Headings are single-language via t("appt.col_<id>") in _table().
# Attendance tag foregrounds (finance-vetted hues): >=4.5:1 on the tree panel AND both zebra backgrounds, both modes.
ATT_FG = {False: {"absent": "#991B1B", "late": "#9A3412", "attended": "#065F46"}, True: {"absent": "#F87171", "late": "#FB923C", "attended": "#34D399"}}


class AppointmentsTab(tk.Frame):
    def __init__(self, parent, app, **kw):
        th = current(); _defer = kw.pop("defer_load", False); super().__init__(parent, bg=th["bg"], **kw)
        self.app = app; self._needs_load = _defer  # R24 item 8: shell defers the data load
        self.lang = getattr(app, "lang", "en") or "en"
        self.selected_date = date.today()
        self.selected_time = "10:00"
        top = RoundedFrame(self, bg=th["panel"], border=th["border"])
        top.pack(fill="x", padx=10, pady=(8, 4)); top = top.inner
        tk.Label(top, text=t("appt.title", self.lang), bg=th["panel"], fg=th["accent"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=10, pady=8)
        self.lbl_patient = tk.Label(top, text="", bg=th["panel"],
                                    fg=th["muted"])
        self.lbl_patient.pack(side="right", padx=10)
        mid = tk.Frame(self, bg=th["bg"])
        mid.pack(fill="x", padx=10, pady=4)
        self._weekday_frame(mid, th)
        self._slot_frame(mid, th)
        self.cal = MonthCalendar(mid, on_select=self._on_pick_day, lang=self.lang)
        self.cal.pack(side="right", fill="both", expand=True, padx=(4, 0))
        self._booking_row(th); self._table(th)
        # R24 item 8: defer_load (shell only) waits for first Map; explicit load() stays safe anytime.
        if _defer: self.bind("<Map>", lambda _e: self.load() if self._needs_load else None, add="+")
        else: self.load()

    def _weekday_frame(self, mid, th):
        """Days of the week on the LEFT: click one -> next such day."""
        f = RoundedFrame(mid, bg=th["panel"], border=th["border"])
        f.pack(side="left", fill="y", padx=(0, 4)); f = f.inner
        tk.Label(f, text=t("appt.days", self.lang), bg=th["panel"], fg=th["accent"],
                 font=("Segoe UI", 10, "bold")).pack(pady=(6, 2))
        names = WEEKDAYS_AR if self.lang == "ar" else WEEKDAYS_EN
        self.lb_days = RoundedListbox(f, height=7, width=16, bg=th["panel"],
                                  fg=th["text"], selectbackground=th["accent"],
                                  selectforeground="white", font=("Segoe UI", 10))
        for n in names: self.lb_days.insert("end", n)
        _zebra_lb(self.lb_days); self.lb_days.pack(padx=6, pady=(0, 6))  # R24 zebra audit
        self.lb_days.selection_set(date.today().weekday())
        self.lb_days.bind("<<ListboxSelect>>", self._on_weekday)

    def _slot_frame(self, mid, th):
        """Time slots 08:00-23:59 in the middle (30-min steps + 23:59)."""
        f = RoundedFrame(mid, bg=th["panel"], border=th["border"])
        f.pack(side="left", fill="y", padx=(0, 4)); f = f.inner
        tk.Label(f, text=t("appt.time", self.lang), bg=th["panel"], fg=th["accent"],
                 font=("Segoe UI", 10, "bold")).pack(pady=(6, 2))
        self.lb_slots = RoundedListbox(f, height=8, width=9, bg=th["panel"],
                                   fg=th["text"], selectbackground=th["accent"],
                                   selectforeground="white", font=("Segoe UI", 10))
        self.slots = time_slots()
        for s in self.slots: self.lb_slots.insert("end", s)
        _zebra_lb(self.lb_slots); self.lb_slots.pack(side="left", padx=(2, 0), pady=(0, 6))  # R24 zebra audit
        sb = tk.Scrollbar(f, orient="vertical", command=self.lb_slots.yview)
        sb.pack(side="right", fill="y", pady=(0, 6))
        self.lb_slots.config(yscrollcommand=sb.set)
        self.lb_slots.selection_set(self.slots.index(self.selected_time))
        self.lb_slots.bind("<<ListboxSelect>>", self._on_pick_slot)

    def _booking_row(self, th):
        f = RoundedFrame(self, bg=th["panel"], border=th["border"])
        f.pack(fill="x", padx=10, pady=4); f = f.inner
        self.lbl_selected = tk.Label(f, bg=th["panel"], fg=th["text"],
                                     font=("Segoe UI", 10, "bold"))
        self.lbl_selected.pack(side="left", padx=8, pady=8)
        self._refresh_selected_label()
        tk.Label(f, text=t("appt.reason", self.lang), bg=th["panel"],
                 fg=th["text"]).pack(side="left", padx=4)
        self.e_reason = RoundedEntry(f, width=14)
        self.e_reason.pack(side="left", padx=4)
        rounded_button(f, text=t("appt.add", self.lang), bg=th["accent"],
                  fg="white", command=self.add).pack(side="left", padx=8)
        # Quick-book on its OWN row (round 13: one row squeezed it to 1px).
        f2 = RoundedFrame(self, bg=th["panel"], border=th["border"])
        f2.pack(fill="x", padx=10, pady=(0, 4)); f2 = f2.inner
        attach_quickbook(self, f2, th)

    def _table(self, th):
        frm = RoundedFrame(self, bg=th["panel"], border=th["border"])
        frm.pack(fill="both", expand=True, padx=10, pady=(4, 8)); frm = frm.inner
        cols = [c for c, _ in COLUMNS]
        self.tree = ttk.Treeview(frm, columns=cols, show="headings",
                                 style=tree_style("Appointments"))
        for c, w in COLUMNS:
            self.tree.heading(c, text=t(f"appt.col_{c}", self.lang))
            self.tree.column(c, width=w, minwidth=w, stretch=False)
        vsb = ttk.Scrollbar(frm, orient="vertical", command=self.tree.yview)
        self.hscroll = ttk.Scrollbar(frm, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set,
                            xscrollcommand=self.hscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew"); vsb.grid(row=0, column=1, sticky="ns")
        self.hscroll.grid(row=1, column=0, sticky="ew")
        frm.rowconfigure(0, weight=1); frm.columnconfigure(0, weight=1)

    def _refresh_selected_label(self):
        d = self.selected_date.strftime("%d/%m/%Y")
        self.lbl_selected.config(text=t("appt.selected", self.lang).format(d=d, time=self.selected_time))

    def _on_pick_day(self, d):
        self.selected_date = d
        self.lb_days.selection_clear(0, "end"); self.lb_days.selection_set(d.weekday())
        self._refresh_selected_label()

    def _on_weekday(self, _event=None):
        sel = self.lb_days.curselection()
        if not sel: return
        self.cal.select(next_weekday(date.today(), sel[0]))

    def _on_pick_slot(self, _event=None):
        sel = self.lb_slots.curselection()
        if sel:
            self.selected_time = self.slots[sel[0]]
            self._refresh_selected_label()

    def pick(self, d, time_str):
        """Programmatic pick (used by tests): day + time slot."""
        self.selected_time = time_str
        self.lb_slots.selection_clear(0, "end")
        if time_str in self.slots:
            self.lb_slots.selection_set(self.slots.index(time_str)); self.lb_slots.see(self.slots.index(time_str))
        self.cal.select(d)

    def add(self):
        if not self.app.current_patient:
            messagebox.showwarning(t("appt.warn_select_title", self.lang),
                                   t("appt.warn_select_patient", self.lang))
            return
        if self._insert(self.app.current_patient["file_number"],
                        self.selected_date.isoformat(), self.selected_time,
                        self.e_reason.get().strip() or t("appt.default_reason", self.lang)) is None:
            return  # slot already booked: _insert warned, nothing saved
        self.e_reason.delete(0, tk.END)
        self.load()

    def _insert(self, patient_file, d, tm, reason):
        """Insert one appointment. Returns the row id, or None (with a
        single-language warning) when that date+time slot is already booked."""
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date=?"
                    " AND appointment_time=?", (d, tm))
        if cur.fetchone()[0]:
            conn.close()
            messagebox.showwarning(t("appt.quickbook", self.lang),
                                   t("appt.slot_taken", self.lang).format(time=tm, date=d))
            return None
        cur.execute("INSERT INTO appointments(patient_file,appointment_date,"
                    "appointment_time,reason,status,created_at)"
                    " VALUES(?,?,?,?,?,?)",
                    (patient_file, d, tm, reason, "قادم",
                     datetime.now().isoformat()))
        conn.commit(); rid = cur.lastrowid; conn.close()
        return rid

    def load(self):
        self._needs_load = False; [self.tree.delete(i) for i in list(self.tree.get_children())]
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT a.*, p.full_name FROM appointments a LEFT JOIN"
                    " patients p ON a.patient_file=p.file_number"
                    " ORDER BY a.appointment_date DESC LIMIT 500")
        rows = [dict(r) for r in cur.fetchall()]; conn.close()
        att, days, marked = attendance_batch(rows), day_attendance(rows), set()
        fg = ATT_FG[is_dark()]
        for _s in ("absent", "late", "attended"): self.tree.tag_configure(_s, foreground=fg[_s])
        for r in rows:
            st = att.get(r["id"]); name = r["full_name"] or ""
            tags = (st,) if st in fg else ()
            self.tree.insert("", "end", values=(r["patient_file"], name,
                r["appointment_date"], r["appointment_time"], r["reason"], translate_status(r["status"], self.lang), attendance_label(st, self.lang)), tags=tags)
            try: marked.add(date.fromisoformat(str(r["appointment_date"])[:10]))
            except Exception: pass
        zebra_tree(self.tree)  # R21 item 6 (attendance fg tags keep precedence)
        self.cal.begin_batch()  # R21 item 11: one calendar render per load
        self.cal.set_marked(marked); self.cal.set_day_status(days)
        self.cal.end_batch()
        p = getattr(self.app, "current_patient", None)
        self.lbl_patient.config(text=t("appt.patient_prefix", self.lang).format(name=p["full_name"]) if p else t("appt.no_patient", self.lang))
        refresh_quickbook(self)
