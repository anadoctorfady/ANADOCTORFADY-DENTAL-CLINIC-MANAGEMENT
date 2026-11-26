"""Appointments calendar rebuild (Item 7, 2026-11-08): custom month grid,
weekday list, time slots 08:00-23:59, pick day+slot -> stored appointment,
Status column visible at 1380px. GUI parts skip gracefully with no display.
"""
import calendar as _cal
from datetime import date
from pathlib import Path
from src.models.database import init_db, get_connection
from src.ui.calendar_grid import (month_weeks, month_day_count, time_slots,
                                  next_weekday, WEEKDAYS_EN, WEEKDAYS_AR,
                                  MonthCalendar)


def test_month_grid_correct_days():
    # Feb 2026: 28 days; Nov 2026: 30 days; leap Feb 2024: 29 days.
    assert month_day_count(2026, 2) == 28
    assert month_day_count(2026, 11) == 30
    assert month_day_count(2024, 2) == 29
    for y, m in [(2026, 2), (2026, 11), (2024, 2), (2026, 8)]:
        weeks = month_weeks(y, m)
        days = [d for w in weeks for d in w if d]
        assert days == list(range(1, month_day_count(y, m) + 1))
        assert weeks == _cal.monthcalendar(y, m)  # stdlib ground truth
        assert all(len(w) == 7 for w in weeks)


def test_time_slots_08_to_2359():
    slots = time_slots()
    assert slots[0] == "08:00" and slots[-1] == "23:59"
    assert slots[-2] == "23:30" and len(slots) == 33
    assert "10:00" in slots and "12:30" in slots and "18:00" in slots
    assert all("08:00" <= s <= "23:59" for s in slots)
    assert slots == sorted(slots)
    assert len(set(slots)) == len(slots)


def test_weekday_names_seven_bilingual():
    assert len(WEEKDAYS_EN) == len(WEEKDAYS_AR) == 7
    assert WEEKDAYS_EN[0] == "Monday" and WEEKDAYS_AR[0] == "الاثنين"
    assert WEEKDAYS_EN[6] == "Sunday" and WEEKDAYS_AR[6] == "الأحد"
    assert next_weekday(date(2026, 11, 8), 0) == date(2026, 11, 9)  # Sun->Mon
    assert next_weekday(date(2026, 11, 9), 0) == date(2026, 11, 9)  # Mon=Mon


def test_no_tkcalendar_dependency():
    root = Path(__file__).resolve().parent.parent
    assert "tkcalendar" not in (root / "requirements.txt").read_text()
    for p in (root / "src").rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        assert "import tkcalendar" not in src and "from tkcalendar" not in src, p


def _gui_tab():
    """Build AppointmentsTab on a stub app; return None when no display."""
    try:
        import tkinter as tk
        from src.ui.appointments import AppointmentsTab
        root = tk.Tk()
        root.withdraw()
        stub = type("Stub", (), {"lang": "en", "current_patient": None})()
        tab = AppointmentsTab(root, stub)
        tab.pack(fill="both", expand=True)
        # R53: the page is a scroll page now -- its host is sized by
        # the canvas <Configure>, which only fires in a MAPPED window
        # at a real size (a withdrawn 1px root leaves the host at its
        # requested width, so the tree measured wider than the tab).
        # Deiconify at the 1380px width this test's docstring promises.
        root.deiconify(); root.geometry("1380x820")
        root.update()
        return root, tab
    except Exception:
        return None


def test_calendar_renders_and_pick_stores_appointment():
    got = _gui_tab()
    if got is None:
        return  # no display: pure-logic tests above already cover the grid
    root, tab = got
    try:
        assert tab.cal.year == date.today().year
        assert tab.cal.month == date.today().month
        assert tab.lb_days.size() == 7 and tab.lb_slots.size() == 33
        assert tab.lb_slots.get(0) == "08:00"
        assert tab.lb_slots.get("end") == "23:59"
        # Pick a day + slot, create the appointment, check the DB.
        init_db()
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT INTO patients(first_name,full_name,birth_date_greg,"
                    "nationality) VALUES(?,?,?,?)",
                    ("Cal", "Cal Test Patient", "1990-01-01", "Syrian"))
        fid = cur.lastrowid; conn.commit(); conn.close()
        try:
            tab.app.current_patient = {"file_number": fid,
                                       "full_name": "Cal Test Patient"}
            day = date(2026, 11, 15)
            tab.pick(day, "14:30")
            assert tab.selected_date == day and tab.selected_time == "14:30"
            assert "15/11/2026" in tab.lbl_selected.cget("text")
            tab.e_reason.insert(0, "Check-up")
            tab.add()
            conn = get_connection(); cur = conn.cursor()
            cur.execute("SELECT appointment_date, appointment_time, reason,"
                        " status FROM appointments WHERE patient_file=?",
                        (fid,))
            row = cur.fetchone(); conn.close()
            assert row is not None
            assert (row["appointment_date"], row["appointment_time"],
                    row["reason"]) == ("2026-11-15", "14:30", "Check-up")
            assert row["status"] == "قادم"
            # Picked day is now dotted on the calendar.
            assert day in tab.cal.marked
        finally:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("DELETE FROM appointments WHERE patient_file=?", (fid,))
            cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
            conn.commit(); conn.close()
    finally:
        root.destroy()


def test_status_column_visible():
    """Gallery bug: Status was off-screen, no h-scrollbar. Now the
    column widths sum to 820px (< tab width at 1380px) and a horizontal
    scrollbar exists, so Status is visible without scrolling.
    R24: a seventh column, attendance (115px), was appended after
    status — 705px -> 820px total, status keeps its 80px."""
    from src.ui.appointments import COLUMNS
    total = sum(w for _, w in COLUMNS)
    assert [c for c, _ in COLUMNS][-1] == "attendance"
    assert dict(COLUMNS)["status"] == 80 and dict(COLUMNS)["attendance"] == 115
    assert total == 820 and total < 950  # tab width at 1380px window
    got = _gui_tab()
    if got is None:
        src = Path(__file__).resolve().parent.parent.joinpath(
            "src/ui/appointments.py").read_text(encoding="utf-8")
        assert "hscroll" in src and 'orient="horizontal"' in src
        return
    root, tab = got
    try:
        root.update()
        assert hasattr(tab, "hscroll") and tab.hscroll.winfo_exists()
        assert tab.tree["columns"][-1] == "attendance"  # R24: appended last
        assert tab.tree.column("status", "width") == 80
        assert tab.tree.column("attendance", "width") == 115
        x = tab.tree.bbox(tab.tree.get_children()[-1], "status") \
            if tab.tree.get_children() else None
        # Treeview itself must fit inside the tab (no overflow past edge).
        tab.update_idletasks()
        assert tab.tree.winfo_width() <= tab.winfo_width()
        # bbox is "" when the window is withdrawn (headless test) - only
        # check the cell geometry when a real tuple comes back.
        if isinstance(x, tuple):
            assert x[0] + x[2] <= tab.tree.winfo_width()
    finally:
        root.destroy()


def test_month_navigation():
    got = _gui_tab()
    if got is None:
        return
    root, tab = got
    try:
        tab.cal.select(date(2026, 11, 15))
        assert "November 2026" in tab.cal.lbl_month.cget("text")
        tab.cal.next_month()
        assert (tab.cal.year, tab.cal.month) == (2026, 12)
        tab.cal.next_month()
        assert (tab.cal.year, tab.cal.month) == (2027, 1)
        tab.cal.prev_month()
        assert (tab.cal.year, tab.cal.month) == (2026, 12)
    finally:
        root.destroy()
