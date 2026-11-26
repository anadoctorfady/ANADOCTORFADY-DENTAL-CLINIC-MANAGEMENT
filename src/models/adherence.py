"""Appointment adherence (Round 55, Section C).

DISPLAY ONLY: colours the patient's name in the patient list from
the attendance of their LAST 3 APPOINTMENTS, and builds the small
reminder line shown in the clinical header strip. Attendance
semantics are NOT changed here -- every status comes from the
existing computation (src/models/appointments.attendance_batch:
attended / late >1h / did not attend, from the earliest procedure
created_at that day; stored status is never overwritten).

Rule: last 3 past appointments all attended = GREEN name; any late
= AMBER; any missed = RED; fewer than 3 on file = use the ones
that exist (1-2); no (past) appointments at all = None (default
name colour, no signal). "Last 3" = the 3 most recent appointments
whose time has passed; future appointments carry no attendance
yet, so they are not counted.

Colours are ONE set for both themes (like the vivid palette):
dark shades that read >= 4.5:1 on the pastel row backgrounds the
list actually paints (pinned in test_r55_header_adherence).
"""
from datetime import datetime

from src.models.appointments import attendance_batch

GREEN, AMBER, RED = "#166534", "#92400E", "#991B1B"
COLOURS = {"green": GREEN, "amber": AMBER, "red": RED}


def adherence_colour(statuses):
    """'green' | 'amber' | 'red' | None for a list of computed
    statuses (None entries = unparseable/pending, ignored)."""
    got = [s for s in (statuses or []) if s in ("attended", "late", "absent")]
    if not got:
        return None
    if "absent" in got:
        return "red"
    if "late" in got:
        return "amber"
    return "green"


def _past(items, now):
    """[(date, time, id)] of `items` whose appointment time has
    passed, newest first."""
    out = []
    for it in items:
        try:
            dt = datetime.fromisoformat(
                f"{str(it['appointment_date'])[:10]}T"
                f"{str(it['appointment_time'])[:5]}")
        except (KeyError, TypeError, ValueError):
            continue
        if dt <= now:
            out.append((str(it["appointment_date"])[:10],
                        str(it["appointment_time"])[:5],
                        it.get("id"), dt))
    out.sort(key=lambda r: r[3], reverse=True)
    return out


def last3_appointments(patient_file, now=None):
    """[(date_str, status)] for one patient's last 3 past
    appointments, newest first; [] when there are none."""
    now = now or datetime.now()
    from src.models.database import get_connection
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, appointment_date, appointment_time FROM appointments"
            " WHERE patient_file=? ORDER BY appointment_date DESC,"
            " appointment_time DESC", (patient_file,)).fetchall()
    finally:
        conn.close()
    past = _past([dict(r) for r in rows], now)[:3]
    if not past:
        return []
    items = [{"id": i, "patient_file": patient_file,
              "appointment_date": d, "appointment_time": t}
             for d, t, i, _dt in past]
    got = attendance_batch(items, now=now)
    return [(d, got.get(i if i is not None else
                        (patient_file, d, t))) for d, t, i, _dt in past]


def adherence_for_files(file_numbers, now=None):
    """{file_number: (colour_or_None, [(date, status), ...])} for
    many patients in ONE appointments query + ONE attendance
    batch (load_patients lists up to 500 rows)."""
    now = now or datetime.now()
    files = [f for f in dict.fromkeys(file_numbers or []) if f is not None]
    if not files:
        return {}
    from src.models.database import get_connection
    conn = get_connection()
    try:
        ph = ",".join("?" * len(files))
        rows = conn.execute(
            "SELECT id, patient_file, appointment_date, appointment_time"
            f" FROM appointments WHERE patient_file IN ({ph})"
            " ORDER BY appointment_date DESC, appointment_time DESC",
            tuple(files)).fetchall()
    finally:
        conn.close()
    by_file = {}
    for r in rows:
        by_file.setdefault(r["patient_file"], []).append(dict(r))
    items, keys = [], {}
    for fid, rows_f in by_file.items():
        for d, t, i, _dt in _past(rows_f, now)[:3]:
            item = {"id": i, "patient_file": fid,
                    "appointment_date": d, "appointment_time": t}
            items.append(item)
            keys.setdefault(fid, []).append((d, i if i is not None else
                                            (fid, d, t)))
    got = attendance_batch(items, now=now) if items else {}
    out = {}
    for fid in files:
        entries = [(d, got.get(k)) for d, k in keys.get(fid, [])]
        out[fid] = (adherence_colour([s for _d, s in entries]), entries)
    return out


def reminder_line(entries, lang="en"):
    """'2026-11-20 Attended · 2026-11-13 Late' for the header
    strip's adherence cell; '' when there are no entries."""
    if not entries:
        return ""
    from src.config.strings_r18_appts import attendance_label
    parts = []
    for d, s in entries:
        label = attendance_label(s, lang)
        parts.append(f"{d} {label}" if label else str(d))
    return " · ".join(parts)
