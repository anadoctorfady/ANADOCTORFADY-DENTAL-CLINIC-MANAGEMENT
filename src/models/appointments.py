"""Appointment booking helpers (Job 8, round 12): free-slot search and
double-booking guard. Pure DB logic, no tkinter. <200 lines.
Round 17: status is STORED as Arabic ('قادم'), translated AT DISPLAY
via translate_status() — storage never changes. Round 18 (W4):
attendance is COMPUTED at display from the first procedure-writing
time that day (procedures.created_at, round12)."""
from datetime import date, datetime, timedelta

from src.ui.calendar_grid import time_slots

# Stored status -> (EN display, AR display). Storage stays as-is
# ('قادم'); unknown values pass through unchanged (patient data).
_STATUS_LABELS = {
    "قادم": ("Upcoming", "قادم"), "upcoming": ("Upcoming", "قادم"),
    "تم": ("Completed", "تم"), "مكتمل": ("Completed", "مكتمل"),
    "completed": ("Completed", "تم"), "done": ("Completed", "تم"),
    "ملغي": ("Cancelled", "ملغي"), "ملغى": ("Cancelled", "ملغى"),
    "cancelled": ("Cancelled", "ملغي"), "canceled": ("Cancelled", "ملغي"),
    "حضر": ("Attended", "حضر"), "attended": ("Attended", "حضر"),
    "لم يحضر": ("No-show", "لم يحضر"), "no-show": ("No-show", "لم يحضر"),
    "no show": ("No-show", "لم يحضر"),
}


def _app_lang(lang):
    if lang in ("en", "ar"):
        return lang
    try:
        from src.models.database import get_setting
        return "ar" if (get_setting("language", "en") or "en") == "ar" else "en"
    except Exception:
        return "en"


def translate_status(stored, lang=None):
    """Display form of a stored status in ONE language (app lang if None)."""
    pair = _STATUS_LABELS.get((stored or "").strip().lower())
    if pair is None:
        pair = _STATUS_LABELS.get((stored or "").strip())
    if pair is None:
        return stored or ""
    return pair[1] if _app_lang(lang) == "ar" else pair[0]


def booked_times(conn, d):
    """Set of booked \"HH:MM\" strings on date d (date or ISO string)."""
    d = d.isoformat() if hasattr(d, "isoformat") else str(d)
    cur = conn.cursor(); cur.execute(
        "SELECT appointment_time FROM appointments WHERE appointment_date=?", (d,))
    return {r[0] for r in cur.fetchall()}


def slot_taken(conn, d, tm):
    """True when time tm on date d is already booked (any patient)."""
    return tm in booked_times(conn, d)


def next_free_slot(conn, d=None):
    """First free clinic slot on date d (default today), scanning
    08:00-23:59 in order. Returns None when every slot is taken."""
    d = d or date.today()
    taken = booked_times(conn, d)
    return next((s for s in time_slots() if s not in taken), None)


# --- Round 18: attendance from procedure-writing time -----------------
_LATE_AFTER = timedelta(hours=1)
_WORST = {None: 0, "attended": 1, "late": 2, "absent": 3}


def _appt_dt(date_str, time_str):
    """Appointment datetime from 'YYYY-MM-DD' + 'HH:MM', else None."""
    try:
        return datetime.fromisoformat(f"{str(date_str)[:10]}T{str(time_str)[:5]}")
    except (TypeError, ValueError):
        return None


def _proc_dt(value):
    """Parse a procedures.created_at value, else None. Legacy rows
    with NULL / unparseable created_at count as NO procedure."""
    if not value:
        return None
    txt = str(value).strip()
    try:
        return datetime.fromisoformat(txt)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(txt, fmt)
        except ValueError:
            continue
    return None


def _has_created_at(cur):
    try:
        cur.execute("PRAGMA table_info(procedures)")
        return any(r[1] == "created_at" for r in cur.fetchall())
    except Exception:
        return False


def _first_proc_dt(cur, patient_file, date_str, has_col=True):
    """Earliest parseable procedures.created_at that day, else None."""
    if not has_col: return None
    cur.execute("SELECT created_at FROM procedures WHERE patient_file=?"
                " AND substr(created_at,1,10)=?", (patient_file, date_str))
    first = None
    for (raw,) in cur.fetchall():
        dt = _proc_dt(raw)
        if dt is not None and (first is None or dt < first):
            first = dt
    return first


def _classify(appt_dt, first_dt, now):
    if appt_dt is None or now <= appt_dt:
        return None  # pending: future, not-yet-due, or unparseable
    if first_dt is None:
        return "absent"
    # Written before the appointment time still counts as attended.
    return "late" if first_dt - appt_dt > _LATE_AFTER else "attended"


def _key(it):
    """Batch key: the row id when present, else the identity triple."""
    return it["id"] if it.get("id") is not None else (
        it["patient_file"], it["appointment_date"], it["appointment_time"])


def attendance_for(patient_file, date_str, time_str, now=None):
    """'attended'|'late'|'absent'|None for one appointment (now is
    injectable for tests; past the appt time: no procedure that day
    -> absent, first procedure >1h after -> late, else attended)."""
    now = now or datetime.now()
    appt_dt = _appt_dt(date_str, time_str)
    if appt_dt is None or now <= appt_dt:
        return None
    from src.models.database import get_connection
    conn = get_connection()
    try:
        cur = conn.cursor()
        first = _first_proc_dt(cur, patient_file, str(date_str)[:10], _has_created_at(cur))
    finally:
        conn.close()
    return _classify(appt_dt, first, now)


def attendance_batch(items, now=None):
    """{key: status} for many appointments in ONE connection, first
    procedure fetched once per distinct day (R51 batch fetch)."""
    now = now or datetime.now()
    items = [dict(it) for it in items]  # also accepts sqlite3.Row
    out, todo = {}, {}
    for it in items:
        key = _key(it)
        appt_dt = _appt_dt(it["appointment_date"], it["appointment_time"])
        if appt_dt is None or now <= appt_dt:
            out[key] = None
        else:
            todo[key] = (it["patient_file"], str(it["appointment_date"])[:10],
                         appt_dt)
    if todo:
        from src.models.database import get_connection
        from src.models.proc_times import first_proc_map
        conn = get_connection()
        try:
            cur = conn.cursor()
            first = first_proc_map(cur, todo.values(), _proc_dt) if _has_created_at(cur) else {}
            for key, (pf, dstr, appt_dt) in todo.items():
                out[key] = _classify(appt_dt, first.get((pf, dstr)), now)
        finally:
            conn.close()
    return out


def worst_status(statuses):
    """Worst of an iterable of statuses: absent > late > attended."""
    best = None
    for s in statuses:
        if _WORST.get(s, 0) > _WORST.get(best, 0):
            best = s
    return best


def day_attendance(items, now=None, per_item=None):
    """{'YYYY-MM-DD': worst status or None} per day in `items`
    (same mapping shape as attendance_batch) — for calendar tinting.
    R51: `per_item` reuses a caller's attendance_batch result
    instead of paying for the identical batch a second time."""
    items = [dict(it) for it in items]
    if per_item is None:
        per_item = attendance_batch(items, now=now)
    by_day = {}
    for it in items:
        dstr = str(it["appointment_date"])[:10]
        by_day[dstr] = worst_status([by_day.get(dstr), per_item.get(_key(it))])
    return by_day
