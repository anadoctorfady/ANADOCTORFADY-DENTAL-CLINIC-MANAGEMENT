"""Round 55 (C) adherence MODEL tests (no display needed).

Seeded cases: 9101 green (3 attended; a 4th older appointment
proves only the last 3 count), 9102 amber (2 attended + 1 late),
9103 red (1 missed), 9104 no appointments at all. The stored
appointment status is never overwritten by the computation.
"""
from datetime import datetime

from src.models.adherence import (COLOURS, adherence_colour,
                                   adherence_for_files, last3_appointments,
                                   reminder_line)
from src.ui.vivid_rows import PALETTE

NOW = datetime(2026, 11, 25, 12, 0)
DATES = ("2026-11-20", "2026-11-18", "2026-11-16")
BASE = {"first_name": "R55", "father_name": "R55Dad",
        "grand_name": "R55Gpa", "last_name": "R55Fam",
        "birth_date_greg": "1980-03-10", "birth_date_hijri": "",
        "age_years": 45, "age_months": 9, "age_days": 3,
        "age_total_days": 0, "mobile1": "+962791234569", "mobile2": "",
        "emergency_phone": "+962791234570",
        "address": "1 Test Road, Amman, Jordan", "nationality": "Jordanian",
        "current_medications": "Metformin 500 mg",
        "allergies": "Penicillin, Sulfa",
        "diseases": ("DIABETES MELLITUS, HYPERTENSION, ASTHMA, EPILEPSY, "
                     "RHEUMATOID ARTHRITIS, OSTEOPOROSIS")}


def _lum(hexcol):
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(fg, bg):
    a, b = _lum(fg), _lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _seed_adherence():
    from src.models.database import get_connection
    conn = get_connection(); cur = conn.cursor()
    for fid, name in ((9101, "R55 Green"), (9102, "R55 Amber"),
                      (9103, "R55 Red"), (9104, "R55 None")):
        row = dict(BASE, file_number=fid, full_name=name)
        cur.execute(f"INSERT OR REPLACE INTO patients({', '.join(row)})"
                    f" VALUES({', '.join('?' * len(row))})",
                    tuple(row.values()))
    for fid, procs in (
            (9101, {"2026-11-20": "10:15", "2026-11-18": "10:30",
                    "2026-11-16": "09:50", "2026-11-14": "10:10"}),
            (9102, {"2026-11-20": "10:15", "2026-11-18": "12:30",
                    "2026-11-16": "10:05"}),
            (9103, {"2026-11-20": "10:15", "2026-11-16": "10:05"})):
        # Every patient gets all 3 appointments; procedures only
        # where listed (9103 has NO procedure on 2026-11-18: the
        # missed one). 9101 gets a 4th older appointment too.
        dates = sorted(set(DATES) | ({"2026-11-14"} if fid == 9101 else set()),
                       reverse=True)
        for d in dates:
            cur.execute("INSERT INTO appointments(patient_file,"
                        "appointment_date,appointment_time,reason,status,"
                        "created_at) VALUES(?,?,?,?,?,?)",
                        (fid, d, "10:00", "Check", "قادم", "2026-10-01T09:00:00"))
            if d in procs:
                cur.execute("INSERT INTO procedures(patient_file,visit_date,"
                            "tooth_number,procedure_done,created_at)"
                            " VALUES(?,?,?,?,?)",
                            (fid, d, "11", "Filling", f"{d}T{procs[d]}:00"))
    conn.commit(); conn.close()


def _cleanup(fids=(9101, 9102, 9103, 9104, 9105)):
    from src.models.database import get_connection
    conn = get_connection()
    for fid in fids:
        conn.execute("DELETE FROM procedures WHERE patient_file=?", (fid,))
        conn.execute("DELETE FROM appointments WHERE patient_file=?", (fid,))
        conn.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()


def test_r55_adherence_model():
    _seed_adherence()
    try:
        e1 = last3_appointments(9101, now=NOW)
        assert [d for d, _s in e1] == list(DATES), e1  # 11-14 excluded
        assert [s for _d, s in e1] == ["attended"] * 3, e1
        assert adherence_colour([s for _d, s in e1]) == "green"
        e2 = last3_appointments(9102, now=NOW)
        assert [s for _d, s in e2] == ["attended", "late", "attended"], e2
        assert adherence_colour([s for _d, s in e2]) == "amber"
        e3 = last3_appointments(9103, now=NOW)
        assert [s for _d, s in e3] == ["attended", "absent", "attended"], e3
        assert adherence_colour([s for _d, s in e3]) == "red"
        assert last3_appointments(9104, now=NOW) == []
        assert adherence_colour([]) is None
        assert adherence_colour([None, None]) is None
        assert adherence_colour(["attended", "late"]) == "amber"
        got = adherence_for_files([9101, 9102, 9103, 9104], now=NOW)
        assert got[9101][0] == "green" and got[9102][0] == "amber"
        assert got[9103][0] == "red" and got[9104][0] is None
        assert got[9104][1] == []
        line = reminder_line(e1, "en")
        assert "2026-11-20 Attended" in line and "2026-11-16 Attended" in line
        assert "2026-11-20 حضر" in reminder_line(e1, "ar")
        # Stored status is never overwritten by the computation.
        from src.models.database import get_connection
        conn = get_connection()
        assert conn.execute("SELECT DISTINCT status FROM appointments"
                            " WHERE patient_file IN (9101,9102,9103)"
                            ).fetchall()[0][0] == "قادم"
        conn.close()
    finally:
        _cleanup()


def test_r55_adherence_colours_readable():
    """One colour set for both themes: >= 4.5:1 on the light list
    background AND on every pastel row background the list
    actually paints (the name sits on a pastel row)."""
    from src.config.theme import LIGHT
    for name, hexcol in COLOURS.items():
        assert _ratio(hexcol, LIGHT["list_bg"]) >= 4.5, (name, hexcol)
        for bg in PALETTE:
            assert _ratio(hexcol, bg) >= 4.5, (name, hexcol, bg)
