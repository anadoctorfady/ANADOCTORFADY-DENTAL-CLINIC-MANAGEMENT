"""Round 21 item 11: language toggle speed at realistic volume.

Seeds 200 patients with visits, payments and appointments, then
times App._toggle_lang() both ways: each must stay under the
standing 3s regression threshold (measured on this Linux/Xvfb VM:
~2.7s per toggle BEFORE the round-21 optimisations, ~0.7-1.1s
after -- Windows numbers will differ; the structural wins are
what carry over). The optimisations pinned here:
- RoundedButton font measurements are cached module-wide
  (rounded._MEASURE_CACHE): rebuilds re-measure the same labels
  hundreds of times.
- The appointments calendar renders ONCE per load (begin/end
  batch around set_marked + set_day_status).
- The patient list computes debtors with ONE grouped query
  (models.finance.debtor_files), not patient_totals() per row;
  debtor_files() must agree with patient_totals() per patient.
"""
import time

from tests.test_templates_edit import isolated_db


def _seed_200():
    from src.models.database import get_connection
    conn = get_connection(); cur = conn.cursor()
    for i in range(200):
        cur.execute("INSERT INTO patients(first_name,father_name,"
                    "grand_name,last_name,full_name,birth_date_greg,"
                    "mobile1) VALUES(?,?,?,?,?,?,?)",
                    (f"Pat{i}", "Father", "Grand", "Family",
                     f"Pat{i} Father Grand Family", "1990-05-15",
                     f"0955{i:06d}"))
        fid = cur.lastrowid
        for v in range(2):
            d = f"2026-10-{10 + v:02d}"
            cur.execute("INSERT INTO diagnoses(patient_file,"
                        "visit_date,tooth_number,diagnosis) "
                        "VALUES(?,?,?,?)", (fid, d, "16", "Caries"))
            cur.execute("INSERT INTO financials(patient_file,"
                        "visit_date,tooth_number,total_cost,"
                        "paid_amount,remaining,currency,doctor,"
                        "entered_by) VALUES(?,?,?,?,?,?,?,?,?)",
                        (fid, d, "16", 1000, 400 if v else 1000,
                         600 if v else 0, "SYP", "fady", "fady"))
        cur.execute("INSERT INTO appointments(patient_file,"
                    "appointment_date,appointment_time,reason,status)"
                    " VALUES(?,?,?,?,?)", (fid, "2026-11-20", "10:00",
                                           "Check", "قادم"))
    conn.commit(); conn.close()


def test_debtor_files_matches_patient_totals():
    from src.models.finance import debtor_files, patient_totals
    with isolated_db():
        _seed_200()
        owing = debtor_files()
        expect = set()
        from src.models.database import get_connection
        conn = get_connection()
        fids = [r[0] for r in conn.execute(
            "SELECT file_number FROM patients")]
        conn.close()
        for fid in fids:
            if patient_totals(fid)["remaining"] > 0:
                expect.add(fid)
        assert owing == expect and len(owing) == 200


def test_calendar_batching_renders_once():
    import tkinter as tk
    from src.ui.calendar_grid import MonthCalendar
    with isolated_db():
        root = tk.Tk(); root.withdraw()
        try:
            cal = MonthCalendar(root)
            calls = []
            orig = cal._render
            cal._render = lambda: (calls.append(1), orig())
            cal.begin_batch()
            cal.set_marked(set()); cal.set_day_status({})
            assert not calls, "rendered inside the batch"
            cal.end_batch()
            assert len(calls) == 1, calls
        finally:
            root.destroy()


def test_toggle_fast_with_200_patients():
    from tkinter import messagebox
    from src.ui.shell import App
    from tests.test_r18_info_panel_visible import _login
    with isolated_db():
        _seed_200()
        messagebox.showinfo = lambda *a, **k: None
        app = App()
        try:
            _login(app)
            app.deiconify(); app.geometry("1380x1000"); app.update()
            app.search_var.set("Pat"); app.load_patients(); app.update()
            assert len(app.tree.get_children("")) >= 190
            for _ in range(2):
                t0 = time.perf_counter()
                app._toggle_lang(); app.update()
                dt = time.perf_counter() - t0
                assert dt < 3.0, f"language toggle took {dt:.2f}s"
        finally:
            app.destroy()
