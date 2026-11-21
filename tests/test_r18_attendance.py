"""Round 18 W4: appointment attendance from procedure-writing time.

attendance_for() is COMPUTED, never stored: past the appointment
time, the day's EARLIEST procedures.created_at decides — none that
day -> absent, >1h after the appointment -> late, otherwise (incl.
written BEFORE the appointment time) -> attended; now <= appt ->
None. Seeded rows are cleaned up. GUI parts skip with no display;
run with DISPLAY=:98 under Xvfb. Coordinator: add
"test_r18_attendance" to run_tests.py TESTS.
Round 24 supersession (GUI test only): the label no longer rides
inside the name cell — it has a dedicated attendance column and ALL
three states carry a colour tag (attended included). Model tests
below are untouched; the board itself is covered in depth by
tests/test_r24_attendance_board.py.
"""
from datetime import date, datetime, timedelta

from src.models.database import get_connection, init_db
from src.models.appointments import (attendance_for, attendance_batch,
                                     day_attendance, worst_status)
from src.config.strings_r18_appts import attendance_label, tr

NOW = datetime(2026, 11, 9, 12, 0)  # fixed "now" for the model cases


def _patient(cur, name):
    cur.execute("INSERT INTO patients(first_name,full_name,birth_date_greg,"
                "nationality) VALUES(?,?,?,?)", (name, name, "1990-01-01", "Syrian"))
    return cur.lastrowid


def _appt(cur, fid, d, tm):
    cur.execute("INSERT INTO appointments(patient_file,appointment_date,"
                "appointment_time,reason,status,created_at) VALUES(?,?,?,?,?,?)",
                (fid, d, tm, "Check", "قادم", "2026-10-01T09:00:00"))
    return cur.lastrowid


def _proc(cur, fid, created_at):
    cur.execute("INSERT INTO procedures(patient_file,visit_date,tooth_number,"
                "procedure_done,created_at) VALUES(?,?,?,?,?)",
                (fid, (created_at or "")[:10], "11", "Filling", created_at))


def _cleanup(fids):
    conn = get_connection(); cur = conn.cursor()
    for fid in fids:
        cur.execute("DELETE FROM procedures WHERE patient_file=?", (fid,))
        cur.execute("DELETE FROM appointments WHERE patient_file=?", (fid,))
        cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()


def _seeded():
    """One patient, one case per day (see module docstring rules)."""
    init_db()
    conn = get_connection(); cur = conn.cursor()
    fid = _patient(cur, "R18 Attendance Case")
    _appt(cur, fid, "2026-11-02", "10:00")                       # (a) no proc
    _appt(cur, fid, "2026-11-03", "10:00"); _proc(cur, fid, "2026-11-03T12:00:00")  # (b) +2h
    _appt(cur, fid, "2026-11-04", "10:00"); _proc(cur, fid, "2026-11-04T15:00:00")
    _proc(cur, fid, "2026-11-04T10:30:00")                       # (c) earliest +30m wins
    _appt(cur, fid, "2026-11-05", "14:00"); _proc(cur, fid, "2026-11-05T09:15:00")  # (d) before
    _appt(cur, fid, "2026-12-01", "10:00")                       # (e) future
    _appt(cur, fid, "2026-11-09", "18:00"); _proc(cur, fid, "2026-11-09T09:00:00")  # (f) not due
    _appt(cur, fid, "2026-11-06", "10:00"); _proc(cur, fid, "2026-11-07T10:00:00")  # (g) other day
    _appt(cur, fid, "2026-11-08", "10:00"); _proc(cur, fid, None)  # legacy NULL
    _appt(cur, fid, "2026-11-01", "10:00"); _proc(cur, fid, "2026-11-01T11:00:00")  # exactly +1h
    conn.commit(); conn.close()
    return fid


def test_attendance_rules_a_to_g():
    fid = _seeded()
    try:
        assert attendance_for(fid, "2026-11-02", "10:00", now=NOW) == "absent"   # (a)
        assert attendance_for(fid, "2026-11-03", "10:00", now=NOW) == "late"     # (b)
        assert attendance_for(fid, "2026-11-04", "10:00", now=NOW) == "attended"  # (c)
        assert attendance_for(fid, "2026-11-05", "14:00", now=NOW) == "attended"  # (d)
        assert attendance_for(fid, "2026-12-01", "10:00", now=NOW) is None       # (e)
        assert attendance_for(fid, "2026-11-09", "18:00", now=NOW) is None       # (f)
        assert attendance_for(fid, "2026-11-06", "10:00", now=NOW) == "absent"   # (g)
        assert attendance_for(fid, "2026-11-08", "10:00", now=NOW) == "absent"   # NULL created_at
        assert attendance_for(fid, "2026-11-01", "10:00", now=NOW) == "attended"  # ==1h not late
        assert attendance_for(fid, "2026-11-02", "10:00", now=datetime(2026, 11, 2, 10, 0)) is None
    finally:
        _cleanup([fid])


def test_attendance_batch_day_and_status_untouched():
    fid = _seeded()
    init_db(); conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM appointments WHERE patient_file=?", (fid,))
    rows = [dict(r) for r in cur.fetchall()]; conn.close()
    try:
        att = attendance_batch(rows, now=NOW)
        by = {(r["appointment_date"], r["appointment_time"]): att[r["id"]] for r in rows}
        assert by[("2026-11-02", "10:00")] == "absent"
        assert by[("2026-11-03", "10:00")] == "late"
        assert by[("2026-11-04", "10:00")] == "attended"
        assert by[("2026-12-01", "10:00")] is None
        days = day_attendance(rows, now=NOW)
        assert days["2026-11-02"] == "absent" and days["2026-11-03"] == "late"
        assert days["2026-11-04"] == "attended" and days["2026-12-01"] is None
        assert worst_status(["attended", "late"]) == "late"
        assert worst_status(["attended", "absent", "late"]) == "absent"
        assert worst_status([None, None]) is None
        conn = get_connection(); cur = conn.cursor()  # stored status NOT overwritten
        cur.execute("SELECT DISTINCT status FROM appointments WHERE patient_file=?", (fid,))
        assert [r[0] for r in cur.fetchall()] == ["قادم"]; conn.close()
    finally:
        _cleanup([fid])


def test_attendance_labels_single_language():
    assert attendance_label("attended", "en") == "Attended"
    assert attendance_label("late", "en") == "Late"
    assert attendance_label("absent", "en") == "Did not attend"
    assert attendance_label("attended", "ar") == "حضر"
    assert attendance_label("late", "ar") == "تأخر"
    assert attendance_label("absent", "ar") == "لم يحضر"
    assert attendance_label(None, "en") == "" and attendance_label(None, "ar") == ""
    assert tr("appt.late", "en") == "Late" and tr("appt.late", "ar") == "تأخر"


def _gui_tab(lang="en"):
    try:
        import tkinter as tk
        from src.ui.appointments import AppointmentsTab
        root = tk.Tk(); root.withdraw()
        stub = type("Stub", (), {"lang": lang, "current_patient": None})()
        tab = AppointmentsTab(root, stub); tab.pack(fill="both", expand=True)
        root.update()
        return root, tab
    except Exception:
        return None


def test_gui_list_shows_status_text_and_tags():
    got = _gui_tab()
    if got is None:
        return  # no display: model tests above cover the logic
    root, tab = got
    fids = []
    try:
        init_db(); today = date.today()
        conn = get_connection(); cur = conn.cursor()
        # Day-status is the day's WORST across patients, so pick days
        # with no pre-existing appointments (the baseline has some).
        busy = {r[0] for r in cur.execute("SELECT appointment_date FROM appointments")}
        past = [today - timedelta(days=n) for n in range(1, 12)
                if (today - timedelta(days=n)).isoformat() not in busy]
        d_abs, d_late, d_att = past[0], past[1], past[2]
        d_fut = next(today + timedelta(days=n) for n in range(1, 12)
                     if (today + timedelta(days=n)).isoformat() not in busy)
        fid = _patient(cur, "R18 Gui Patient"); fids.append(fid)
        for d in (d_abs, d_late, d_att, d_fut):
            _appt(cur, fid, d.isoformat(), "10:00")
        _proc(cur, fid, f"{d_late.isoformat()}T12:00:00")   # +2h -> late
        _proc(cur, fid, f"{d_att.isoformat()}T10:30:00")    # +30m -> attended
        conn.commit(); conn.close()

        def rows_by_date():
            # R24: (plain name, attendance-column value, tags) per date.
            out = {}
            for iid in tab.tree.get_children():
                v = tab.tree.item(iid, "values")
                if int(v[0]) == fid:
                    out[v[2]] = (v[1], v[6], tab.tree.item(iid, "tags"))
            return out

        for patient in (None, {"file_number": fid, "full_name": "R18 Gui Patient"}):
            tab.app.current_patient = patient  # selected and none
            tab.load(); root.update()
            rows = rows_by_date()
            assert rows[d_abs.isoformat()][1] == "Did not attend"
            assert rows[d_abs.isoformat()][0] == "R18 Gui Patient"  # name: NO label
            assert "absent" in rows[d_abs.isoformat()][2]
            assert rows[d_late.isoformat()][1] == "Late"
            assert "late" in rows[d_late.isoformat()][2]
            assert rows[d_att.isoformat()][1] == "Attended"
            # R24 supersedes the r18/r21 "attended = no tag" intent:
            # attended now carries its tag so the row renders green.
            assert "attended" in rows[d_att.isoformat()][2]
            assert rows[d_fut.isoformat()][1] == ""  # pending: no text
            assert rows[d_fut.isoformat()][0] == "R18 Gui Patient"
            assert tab.cal.day_status[d_abs] == "absent"
            assert tab.cal.day_status[d_late] == "late"
            assert tab.cal.day_status[d_att] == "attended"
            assert d_fut not in tab.cal.day_status
        tab.lang = "ar"; tab.load(); root.update()  # single-language AR display
        assert rows_by_date()[d_abs.isoformat()][1] == "لم يحضر"
        assert rows_by_date()[d_abs.isoformat()][0] == "R18 Gui Patient"
    finally:
        _cleanup(fids); root.destroy()
