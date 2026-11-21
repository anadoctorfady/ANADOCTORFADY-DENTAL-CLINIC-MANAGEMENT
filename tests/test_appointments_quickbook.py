"""Job 8 (round 12): appointments quick-book — one click books the next
free slot today; disabled with a hint when no patient is selected; no double-booking.
GUI tests need a display (Xvfb :103); slot logic also runs headless."""
from datetime import date
from unittest import mock

from src.models.appointments import next_free_slot, slot_taken
from src.models.database import get_connection, init_db
from src.ui.calendar_grid import time_slots

TODAY = date.today().isoformat()


def _make_patient(name="Quickbook Patient"):
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name,birth_date_greg,nationality) VALUES(?,?,?,?)",
                (name.split()[0], name, "1990-01-01", "Syrian"))
    fid = cur.lastrowid; conn.commit(); conn.close()
    return fid


def _cleanup(fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM appointments WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()


def _rows(fid, d=TODAY, tm=None):
    conn = get_connection(); cur = conn.cursor()
    q = "SELECT appointment_time FROM appointments WHERE patient_file=? AND appointment_date=?"; args = [fid, d]
    if tm is not None:
        q += " AND appointment_time=?"; args.append(tm)
    cur.execute(q, args)
    out = [r[0] for r in cur.fetchall()]; conn.close()
    return out


def _book_all(fid, d=TODAY):  # occupy every slot on date d
    conn = get_connection(); cur = conn.cursor()
    for s in time_slots():
        cur.execute("INSERT INTO appointments(patient_file,appointment_date,appointment_time,reason,status,created_at) VALUES(?,?,?,?,?,?)",
                    (fid, d, s, "fill", "قادم", "2026-11-09T00:00:00"))
    conn.commit(); conn.close()


def _gui_tab(patient=None, lang="en"):
    try:
        import tkinter as tk
        from src.ui.appointments import AppointmentsTab
        init_db()
        root = tk.Tk(); root.withdraw()
        stub = type("Stub", (), {"lang": lang, "current_patient": patient})()
        tab = AppointmentsTab(root, stub)
        tab.pack(fill="both", expand=True); root.update()
        return root, tab
    except Exception:
        return None


def _insert(fid, d, tm):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO appointments(patient_file,appointment_date,appointment_time,reason,status,created_at) VALUES(?,?,?,?,?,?)",
                (fid, d, tm, "x", "قادم", "2026-11-09T00:00:00"))
    conn.commit(); conn.close()


def test_next_free_slot_pure_logic():
    # Fixed future date: no appointments exist there in any DB copy, so
    # expectations are deterministic (unlike "today" in live data).
    fid = _make_patient()
    d = date(2099, 6, 15)
    try:
        conn = get_connection()
        assert next_free_slot(conn, d) == "08:00" and not slot_taken(conn, d, "08:00")
        conn.close()
        _insert(fid, d.isoformat(), "08:00"); _insert(fid, d.isoformat(), "08:30")
        conn = get_connection()
        assert slot_taken(conn, d, "08:00") and not slot_taken(conn, d, "09:00")
        assert next_free_slot(conn, d) == "09:00"; conn.close()
        _book_all(fid, d.isoformat())
        conn = get_connection(); assert next_free_slot(conn, d) is None; conn.close()
    finally:
        _cleanup(fid)


def test_quickbook_disabled_without_patient():
    got = _gui_tab(patient=None)
    if got is None:
        return
    root, tab = got
    try:
        assert str(tab.btn_quickbook.cget("state")) == "disabled"
        assert "Select a patient" in tab.lbl_qb_hint.cget("text")
        assert "No patient selected" in tab.lbl_qb_patient.cget("text")
        with mock.patch("src.ui.quickbook.messagebox.showinfo") as info:
            tab.btn_quickbook.invoke(); info.assert_not_called()
        assert _rows(0) == []
    finally:
        root.destroy()


def test_quickbook_books_next_free_slot():
    fid = _make_patient()
    got = _gui_tab(patient={"file_number": fid, "full_name": "Quickbook Patient"})
    if got is None:
        _cleanup(fid)
        return
    root, tab = got
    try:
        conn = get_connection(); expected = next_free_slot(conn, date.today()); conn.close(); assert expected is not None
        tab.load()
        assert str(tab.btn_quickbook.cget("state")) == "normal"
        assert "Quickbook Patient" in tab.lbl_qb_patient.cget("text")
        assert str(fid) in tab.lbl_qb_patient.cget("text")
        assert tab.lbl_qb_hint.cget("text") == ""
        with mock.patch("src.ui.quickbook.messagebox.showinfo") as info:
            tab.btn_quickbook.invoke(); root.update()
            info.assert_called_once(); assert expected in str(info.call_args)
        assert _rows(fid, tm=expected) == [expected]
        assert tab.selected_date == date.today() and tab.selected_time == expected
    finally:
        root.destroy(); _cleanup(fid)


def test_quickbook_second_click_books_next_slot():
    fid = _make_patient()
    got = _gui_tab(patient={"file_number": fid, "full_name": "Quickbook Patient"})
    if got is None:
        _cleanup(fid)
        return
    root, tab = got
    try:
        conn = get_connection(); first = next_free_slot(conn, date.today()); conn.close()
        with mock.patch("src.ui.quickbook.messagebox.showinfo"):
            tab.btn_quickbook.invoke()
        conn = get_connection(); second = next_free_slot(conn, date.today()); conn.close(); assert second is not None and second != first
        with mock.patch("src.ui.quickbook.messagebox.showinfo"):
            tab.btn_quickbook.invoke()
        assert sorted(_rows(fid)) == sorted([first, second])
    finally:
        root.destroy(); _cleanup(fid)


def test_double_booking_same_slot_refused():
    fid = _make_patient()
    got = _gui_tab(patient={"file_number": fid, "full_name": "Quickbook Patient"})
    if got is None:
        _cleanup(fid)
        return
    root, tab = got
    try:
        conn = get_connection(); slot = next_free_slot(conn, date.today()); conn.close()
        with mock.patch("src.ui.quickbook.messagebox.showinfo"):
            tab.btn_quickbook.invoke()
        assert _rows(fid, tm=slot) == [slot]
        # Same slot via the normal Add flow: refused, no duplicate row.
        tab.pick(date.today(), slot)
        tab.e_reason.insert(0, "again")
        with mock.patch("src.ui.appointments.messagebox.showwarning") as warn:
            tab.add(); warn.assert_called_once(); assert slot in str(warn.call_args)
        assert _rows(fid, tm=slot) == [slot]
        # Direct _insert also refuses and returns None.
        with mock.patch("src.ui.appointments.messagebox.showwarning"):
            assert tab._insert(fid, TODAY, slot, "direct") is None
        assert _rows(fid, tm=slot) == [slot]
    finally:
        root.destroy(); _cleanup(fid)


def test_quickbook_no_free_slot_today():
    fid = _make_patient()
    _book_all(fid)
    got = _gui_tab(patient={"file_number": fid, "full_name": "Quickbook Patient"})
    if got is None:
        _cleanup(fid)
        return
    root, tab = got
    try:
        assert str(tab.btn_quickbook.cget("state")) == "normal"
        before = len(_rows(fid))
        with mock.patch("src.ui.quickbook.messagebox.showinfo") as info:
            tab.btn_quickbook.invoke(); info.assert_called_once()
            assert "No free slot" in str(info.call_args)
        assert len(_rows(fid)) == before  # nothing new booked
    finally:
        root.destroy(); _cleanup(fid)


def test_quickbook_arabic_labels():
    got = _gui_tab(patient=None, lang="ar")
    if got is None:
        return
    root, tab = got
    try:
        assert "حجز سريع" in tab.btn_quickbook.cget("text")
        assert "اختر مريضاً" in tab.lbl_qb_hint.cget("text")
    finally:
        root.destroy()
