"""Round 51 Section A: performance regression pins.

1) rounded_pil's fast path (1x body + 4x corner patches, reduce()
downscale) must stay pixel-identical to the full-supersample
render -- the corner antialiasing is a visual-identity feature
(R43), speed may not change a single pixel.
2) attendance_batch must keep attendance_for's exact per-pair
semantics while running a BOUNDED number of SQL statements
(pre-R51 it ran one query per (patient, day) pair -- ~2,000 per
appointments-board load at clinic scale).
3) The shell's lazy tabs: placeholders keep the notebook's order
and titles; a tab builds on first open or on attribute access
(R52: no idle chain -- it rebuilt every tab inside each toggle).
"""
from datetime import datetime

from src.models.database import get_connection, init_db
from src.models.appointments import attendance_for, attendance_batch
from src.ui import rounded_render as rr

NOW = datetime(2026, 11, 9, 12, 0)


def test_rounded_fast_path_pixel_identical():
    orig = rr._FAST_MIN_PIXELS
    try:
        for (w, h, r, f, b, bw) in (
                (800, 600, 24, "#F6F1E9", "#453D37", 2),
                (640, 480, 12, "#BAE6FD", "#7C3AED", 1),
                (500, 900, 16, "#26211E", None, 1)):
            rr._FAST_MIN_PIXELS = 10 ** 18
            ref = rr.rounded_pil(w, h, r, f, b, bw)
            rr._FAST_MIN_PIXELS = orig
            fast = rr.rounded_pil(w, h, r, f, b, bw)
            assert fast.size == ref.size
            pa, pb = fast.load(), ref.load()
            for y in range(0, h, 5):
                for x in range(0, w, 5):
                    assert pa[x, y] == pb[x, y], (w, h, x, y)
    finally:
        rr._FAST_MIN_PIXELS = orig


def _seed_batch(cur):
    fids = []
    for i in range(30):
        cur.execute("INSERT INTO patients(first_name,full_name,"
                    "birth_date_greg,nationality) VALUES(?,?,?,?)",
                    (f"P{i}", f"P{i}", "1990-01-01", "Syrian"))
        fids.append(cur.lastrowid)
    items = []
    for i, fid in enumerate(fids):
        for d in ("2026-11-08", "2026-11-09"):
            cur.execute("INSERT INTO appointments(patient_file,"
                        "appointment_date,appointment_time,reason,"
                        "status,created_at) VALUES(?,?,?,?,?,?)",
                        (fid, d, "09:00", "Check", "قادم",
                         "2026-10-01T09:00:00"))
            items.append({"id": cur.lastrowid, "patient_file": fid,
                          "appointment_date": d,
                          "appointment_time": "09:00",
                          "status": "قادم"})
        if i % 3 == 0:  # a procedure at 09:30 on the 8th: attended
            cur.execute("INSERT INTO procedures(patient_file,"
                        "visit_date,tooth_number,procedure_done,"
                        "created_at) VALUES(?,?,?,?,?)",
                        (fid, "2026-11-08", "11", "Filling",
                         "2026-11-08T09:30:00"))
        if i % 3 == 1:  # a procedure at 11:00 on the 9th: late
            cur.execute("INSERT INTO procedures(patient_file,"
                        "visit_date,tooth_number,procedure_done,"
                        "created_at) VALUES(?,?,?,?,?)",
                        (fid, "2026-11-09", "11", "Filling",
                         "2026-11-09T11:00:00"))
    return items


def test_attendance_batch_semantics_and_query_bound():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    items = _seed_batch(cur); conn.commit()
    try:
        batch = attendance_batch(items, now=NOW)
        for it in items:
            single = attendance_for(it["patient_file"],
                                    it["appointment_date"],
                                    it["appointment_time"], now=NOW)
            assert batch[it["id"]] == single, (it, batch[it["id"]],
                                               single)
        count = {"n": 0}
        conn.set_trace_callback(lambda _sql: count.__setitem__(
            "n", count["n"] + 1))
        try:
            attendance_batch(items, now=NOW)
        finally:
            conn.set_trace_callback(None)
        # 60 (patient, day) pairs: a handful of chunked statements,
        # never one per pair (the pre-R51 shape was ~120 here).
        assert count["n"] <= 12, count["n"]
    finally:
        ids = [it["id"] for it in items]
        cur.execute("DELETE FROM appointments WHERE id IN (%s)"
                    % ",".join("?" * len(ids)), ids)
        fids = sorted({it["patient_file"] for it in items})
        cur.execute("DELETE FROM procedures WHERE patient_file IN (%s)"
                    % ",".join("?" * len(fids)), fids)
        cur.execute("DELETE FROM patients WHERE file_number IN (%s)"
                    % ",".join("?" * len(fids)), fids)
        conn.commit(); conn.close()


def test_lazy_tabs_build_on_access_and_open():
    import tkinter as tk
    try:
        root = tk.Tk(); root.destroy()
    except Exception:
        return  # no display: GUI part skipped (gate runs under Xvfb)
    from src.ui.shell import App
    from src.ui.finance import FinanceTab
    from src.ui.appointments import AppointmentsTab
    app = App()
    try:
        texts = [app.notebook.tab(i, "text")
                 for i in range(len(app.notebook.tabs()))]
        assert len(texts) == 6 and all(texts), texts
        fin = app.fin  # attribute access builds on demand
        assert isinstance(fin, FinanceTab)
        assert "fin" in app.__dict__
        about = app.about  # the LAST tab: insert-at-end path
        assert app.notebook.index(about) == 5
        assert len(app.notebook.tabs()) == 6
        # R52 re-pin (was R51's idle chain): idle/update must NOT
        # build the remaining tabs -- the chain completing inside a
        # language/theme toggle's settle window was profiled waste
        # (198 SQL + every tab constructor per toggle). Tabs now
        # build on first open or first attribute access only.
        app.update()
        app.update()
        assert set(app._lazy_tabs) == {"appt", "settings", "users"}, \
            app._lazy_tabs.keys()
        ph = app._lazy_tabs["appt"][1]  # opening the page builds it
        app.notebook.select(str(ph))
        app._on_tab_changed()
        assert isinstance(app.appt, AppointmentsTab)
        assert "appt" not in app._lazy_tabs
        assert app.notebook.index(app.fin) == 2  # order preserved
    finally:
        app.destroy()


def run():
    test_rounded_fast_path_pixel_identical()
    test_attendance_batch_semantics_and_query_bound()
    test_lazy_tabs_build_on_access_and_open()
    print("PASS test_r51_perf")
