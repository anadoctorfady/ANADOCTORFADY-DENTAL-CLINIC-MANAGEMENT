"""Round 24 item 4: attendance must be VISIBLE on the appointments board.

Round 18 computed attendance correctly but appended the label to the
patient name inside the 170px name column: a long 4-part name alone
measures ~332px, so the label started ~354px in — past the clipped
cell edge — and attended rows had no colour at all. No refresh on tab
switch / clinical save either. Round 24: dedicated 115px attendance
column (plain name cell), row-tag foregrounds for ALL THREE states,
strengthened calendar tints, shell refresh triggers. GUI parts skip
with no display; run with DISPLAY=:100 under Xvfb. Coordinator: add
"test_r24_attendance_board" to run_tests.py TESTS.
"""
from datetime import date, timedelta

from src.models.database import get_connection, init_db

LONG_NAME = "Muhammad Abd Al-Rahman Al-Husseini Al-Shami"
LABELS = {"en": {"absent": "Did not attend", "late": "Late", "attended": "Attended"},
          "ar": {"absent": "لم يحضر", "late": "تأخر", "attended": "حضر"}}


def _seed():
    """One long-named patient: absent/late/attended on free past days + one future day."""
    init_db(); conn = get_connection(); cur = conn.cursor()
    busy = {r[0] for r in cur.execute("SELECT appointment_date FROM appointments")}
    today = date.today()
    past = [today - timedelta(days=n) for n in range(1, 40) if (today - timedelta(days=n)).isoformat() not in busy]
    fut = next(today + timedelta(days=n) for n in range(1, 40) if (today + timedelta(days=n)).isoformat() not in busy)
    days = {"absent": past[0], "late": past[1], "attended": past[2], "future": fut}
    cur.execute("INSERT INTO patients(first_name,full_name,birth_date_greg,"
                "nationality) VALUES(?,?,?,?)",
                ("Muhammad", LONG_NAME, "1990-01-01", "Syrian"))
    fid = cur.lastrowid
    for d in days.values():
        cur.execute("INSERT INTO appointments(patient_file,appointment_date,"
                    "appointment_time,reason,status,created_at) VALUES(?,?,?,?,?,?)",
                    (fid, d.isoformat(), "10:00", "Check", "قادم", "2026-10-01T09:00:00"))
    for key, ts in (("late", "T12:00:00"), ("attended", "T10:30:00")):
        d = days[key]
        cur.execute("INSERT INTO procedures(patient_file,visit_date,tooth_number,"
                    "procedure_done,created_at) VALUES(?,?,?,?,?)",
                    (fid, d.isoformat(), "11", "Filling", f"{d.isoformat()}{ts}"))
    conn.commit(); conn.close()
    return fid, days

def _cleanup(fid):
    conn = get_connection(); cur = conn.cursor()
    for tbl in ("procedures", "appointments"):
        cur.execute(f"DELETE FROM {tbl} WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()


def _gui_tab(lang="en", notebook=None):
    try:
        import tkinter as tk
        from src.ui.appointments import AppointmentsTab
        root = tk.Tk(); root.geometry("1380x820")
        stub = type("Stub", (), {"lang": lang, "current_patient": None})()
        tab = AppointmentsTab(notebook if notebook is not None else root, stub)
        if notebook is None: tab.pack(fill="both", expand=True)
        root.update()
        return root, tab
    except Exception:
        return None


def _rows(tab, fid):
    """{date_iso: (name, attendance, tags)} for one patient's rows."""
    idx = {c: i for i, c in enumerate(tab.tree["columns"])}
    out = {}
    for iid in tab.tree.get_children():
        v = tab.tree.item(iid, "values")
        if int(v[idx["file"]]) == fid:
            out[v[idx["date"]]] = (v[idx["name"]], v[idx["attendance"]],
                                   tab.tree.item(iid, "tags"))
    return out


def _check_board(tab, root, fid, days, lang):
    from src.config.theme import is_dark
    from src.ui.appointments import ATT_FG
    assert list(tab.tree["columns"])[-1] == "attendance"
    assert tab.tree.column("attendance", "width") == 115
    assert tab.tree.heading("attendance", "text") == ("الحضور" if lang == "ar" else "Attendance")
    for patient in (None, {"file_number": fid, "full_name": LONG_NAME}):
        tab.app.current_patient = patient  # selected and none: both load
        tab.load(); root.update()
        rows = _rows(tab, fid)
        for state in ("absent", "late", "attended"):
            name, att, tags = rows[days[state].isoformat()]
            assert att == LABELS[lang][state], (state, att)
            assert name == LONG_NAME  # plain name: NO label appended
            assert state in tags, (state, tags)
        name, att, tags = rows[days["future"].isoformat()]
        assert att == "" and name == LONG_NAME
        assert all(x.startswith("vivid") for x in tags)  # R43: vivid striping, no state tag
    fg = ATT_FG[is_dark()]  # configured tag foregrounds match ATT_FG
    for state in ("absent", "late", "attended"):
        got = tab.tree.tag_configure(state, "foreground")
        assert fg[state].lower() in repr(got).lower(), (state, got)


def test_board_column_values_tags_fg_en():
    got = _gui_tab("en")
    if got is None:
        return  # no display
    root, tab = got; fid, days = _seed()
    try:
        _check_board(tab, root, fid, days, "en")
    finally:
        _cleanup(fid); root.destroy()


def test_board_column_values_ar():
    got = _gui_tab("ar")
    if got is None:
        return
    root, tab = got; fid, days = _seed()
    try:
        _check_board(tab, root, fid, days, "ar")
    finally:
        _cleanup(fid); root.destroy()


def test_calendar_day_status_and_tint():
    got = _gui_tab("en")
    if got is None:
        return
    root, tab = got; fid, days = _seed()
    try:
        tab.load(); root.update()
        assert tab.cal.day_status[days["absent"]] == "absent"
        assert tab.cal.day_status[days["late"]] == "late"
        assert tab.cal.day_status[days["attended"]] == "attended"
        assert days["future"] not in tab.cal.day_status
        from calendar import monthrange
        from src.config.theme import is_dark; from src.ui.calendar_grid import DAY_TINTS, month_weeks
        d0 = days["absent"]
        plain = [date(d0.year, d0.month, n)
                 for n in range(1, monthrange(d0.year, d0.month)[1] + 1)
                 if date(d0.year, d0.month, n) not in tab.cal.day_status
                 and date(d0.year, d0.month, n) not in (date.today(), d0)]
        neutral, normal = plain[0], plain[1]  # neutral gets selected; normal stays plain
        tab.cal.select(neutral); root.update()  # render d0's month, d0 unselected
        weeks = month_weeks(tab.cal.year, tab.cal.month)
        btn = {weeks[r][c]: tab.cal._day_btns[(r, c)]
               for r in range(6) for c in range(7) if weeks[r][c]}
        tints = DAY_TINTS[is_dark()]
        for state in ("absent", "late", "attended"):
            d = days[state]
            if (d.year, d.month) == (tab.cal.year, tab.cal.month):
                assert btn[d.day]._bg == tints[state][0], (state, btn[d.day]._bg)
        assert btn[normal.day]._bg == tab.cal.t["panel"]  # normal day = panel
        assert btn[d0.day]._bg != btn[normal.day]._bg  # tint clearly differs
    finally:
        _cleanup(fid); root.destroy()


def test_refresh_via_shell_tab_changed_handler():
    """A procedure saved after the board was built flips absent ->
    attended through the shell's tab-changed refresh path (and the
    handler stays inert while another tab is selected)."""
    import inspect, tkinter as tk
    from tkinter import ttk
    from src.ui.shell import App
    assert "appt.load" in inspect.getsource(App.refresh_clinical)
    assert "<<NotebookTabChanged>>" in inspect.getsource(App._main)
    try:
        root = tk.Tk(); root.geometry("1380x820")
        nb = ttk.Notebook(root); nb.pack(fill="both", expand=True)
        from src.ui.appointments import AppointmentsTab
        stub = type("Stub", (), {"lang": "en", "current_patient": None})()
        tab = AppointmentsTab(nb, stub); nb.add(tab, text="Appointments")
        other = tk.Frame(nb); nb.add(other, text="Other")
        root.update()
    except Exception:
        return  # no display
    fid, days = _seed()
    try:
        tab.load(); root.update()
        assert _rows(tab, fid)[days["absent"].isoformat()][1] == "Did not attend"
        conn = get_connection(); cur = conn.cursor()  # the clinical save
        d = days["absent"]
        cur.execute("INSERT INTO procedures(patient_file,visit_date,tooth_number,"
                    "procedure_done,created_at) VALUES(?,?,?,?,?)",
                    (fid, d.isoformat(), "11", "Filling", f"{d.isoformat()}T10:30:00"))
        conn.commit(); conn.close()
        fake = type("Fake", (), {"notebook": nb, "appt": tab})()
        nb.select(other); root.update()
        App._on_tab_changed(fake)  # another tab selected: NO reload
        assert _rows(tab, fid)[d.isoformat()][1] == "Did not attend"
        nb.select(tab); root.update()
        App._on_tab_changed(fake)  # appointments tab: reload happens
        name, att, tags = _rows(tab, fid)[d.isoformat()]
        assert att == "Attended" and "attended" in tags
        tab.load(); root.update()  # plain load() reflects it too
        assert _rows(tab, fid)[d.isoformat()][1] == "Attended"
    finally:
        _cleanup(fid); root.destroy()
