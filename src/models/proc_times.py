"""Batched first-procedure lookup for attendance (Round 51).

attendance_batch used to run one SQL query per (patient, day)
pair -- ~500 queries for one appointments-board load, ~1000 with
the duplicate day_attendance pass. first_proc_map answers for a
whole set of pairs with a handful of chunked queries instead
(files x days, chunked by 400 bind variables each) and takes the
minimum in Python: for every requested (patient_file, date)
pair, the earliest procedures.created_at that day that parses
via the caller's proc_dt -- exactly the single-pair semantics.
"""
_CHUNK = 400


def first_proc_map(cur, todo_values, proc_dt):
    """{(file_number, 'YYYY-MM-DD'): earliest procedure datetime}
    for the requested pairs; pairs without a parseable procedure
    that day are absent from the result. todo_values items are
    (file_number, date_str, appointment_dt) triples as built by
    attendance_batch (the appointment time is not needed here)."""
    pairs = {(f, d) for f, d, _a in todo_values}
    if not pairs:
        return {}
    files = sorted({f for f, _d in pairs})
    days = sorted({d for _f, d in pairs})
    best = {}
    for i in range(0, len(files), _CHUNK):
        fpart = files[i:i + _CHUNK]
        fph = ",".join("?" * len(fpart))
        for j in range(0, len(days), _CHUNK):
            dpart = days[j:j + _CHUNK]
            dph = ",".join("?" * len(dpart))
            cur.execute(
                "SELECT patient_file, created_at FROM procedures"
                f" WHERE patient_file IN ({fph})"
                f" AND substr(created_at,1,10) IN ({dph})",
                (*fpart, *dpart))
            for f, ca in cur.fetchall():
                key = (f, str(ca)[:10])
                if key not in pairs:
                    continue
                dt = proc_dt(ca)
                if dt is not None and (key not in best
                                       or dt < best[key]):
                    best[key] = dt
    return best
