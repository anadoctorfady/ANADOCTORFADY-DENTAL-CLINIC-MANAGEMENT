"""Round 55 (D): (a) Statistics top-treatments charts must not
overlap when procedure labels carry NEWLINES (the owner's
"Temporary filling" / "26, 25, 24, 23, 22" overlap: a multi-line
label renders 2 lines tall inside one row pitch); (b) the AR
Base line must use LRM (U+200E), not the LRI/PDI isolates
(U+2066..U+2069) that rendered as visible marks under Windows
Segoe UI -- order preserved, no visible marks.
"""
import tkinter as tk

from src.config.strings import t
from src.ui import finance_charts as ch
from src.config.theme import LIGHT

ITEMS = [
    ("Temporary filling\n26, 25, 24, 23, 22", 26),
    ("علاج عصب (جذور) 41\nحشوة", 18),
    ("Composite filling 11, 21", 15),
    ("Scaling and polishing", 11),
    ("علاج عصب (جذور) 36, 37 مع حشوة مؤقتة", 12),
    ("Temporary filling 26, 25, 24, 23, 22", 6),
]


def _overlaps(cv):
    texts = [(cv.bbox(i), cv.itemcget(i, "text")) for i in cv.find_all()
             if cv.type(i) == "text"]
    bad = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a, b = texts[i][0], texts[j][0]
            if a and b and a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                bad.append((texts[i][1][:30], texts[j][1][:30]))
    return texts, bad


def test_r55_chart_multiline_labels_no_overlap():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP test_r55_chart_multiline_labels_no_overlap (no display)")
        return
    root.withdraw()
    try:
        for scale in (1.0, 1.25, 1.5):
            root.tk.call("tk", "scaling", scale)
            for fam in ("Segoe UI", "Amiri"):
                cv = tk.Canvas(root, width=1500, height=400)
                cv.pack(); root.update()
                ch.draw_hbars(cv, ITEMS, "No data", LIGHT,
                              fmt=lambda v: f"{int(v)}", family=fam)
                root.update()
                texts, bad = _overlaps(cv)
                assert not bad, (scale, fam, bad)
                assert all("\n" not in txt for _bb, txt in texts), texts
                assert any("Temporary filling 26, 25, 24, 23, 22" in txt
                           for _bb, txt in texts), texts
                cv.destroy()
    finally:
        root.destroy()


def test_r55_chart_grouping_flattens_newlines():
    """The same treatment typed with / without a newline is ONE
    chart group (count 2), with a single-line display label."""
    from src.models.database import get_connection, init_db
    from src.models.statistics import top_treatments_by_count
    init_db()
    conn = get_connection()
    try:
        conn.execute("INSERT OR REPLACE INTO patients(file_number,"
                     "first_name,full_name) VALUES(?,?,?)",
                     (9201, "R55", "R55 Chart"))
        for d, proc in (("2026-11-10", "Temporary filling\n26, 25"),
                        ("2026-11-11", "Temporary filling 26, 25")):
            conn.execute("INSERT INTO procedures(patient_file,visit_date,"
                         "tooth_number,procedure_done,created_at)"
                         " VALUES(?,?,?,?,?)",
                         (9201, d, "26", proc, f"{d}T10:00:00"))
        conn.commit()
        rows = top_treatments_by_count("2026-11-01", "2026-11-30")
        match = [r for r in rows if "Temporary filling" in r[0]]
        assert len(match) == 1, rows
        assert match[0][0] == "Temporary filling 26, 25", match
        assert match[0][1] == 2, match
    finally:
        conn.execute("DELETE FROM procedures WHERE patient_file=9201")
        conn.execute("DELETE FROM patients WHERE file_number=9201")
        conn.commit(); conn.close()


def test_r55_base_line_lrm():
    """AR Base line: LRM around every Latin run, no LRI/PDI
    anywhere; the owner's figures in logical order."""
    ar = t("fin.usd_equiv", "ar")
    assert "\u200e" in ar and "\u2066" not in ar and "\u2069" not in ar, ar
    txt = ar.format(base="SYP", inc=266.07, net=22.14, rate=140)
    plain = txt.replace("\u200e", "")
    assert plain == ("الأساس: SYP  •  ≈ $266.07 دخل / $22.14 صافي بسعر 140 SYP"), plain
    assert plain.index("صافي بسعر") < plain.index("140"), plain
    assert plain.index("140") < plain.rindex("SYP"), plain
    note = t("fincur.raw_note", "ar").format(cur="SYP")
    assert "\u200eSYP\u200e" in note and "\u2066" not in note, note
    from src.utils.arabic import bidi_isolate
    assert bidi_isolate("SYP") == "\u200eSYP\u200e"
    assert t("fin.usd_set_rate", "ar").count("\u200e") == 2
    assert "\u2066" not in t("fin.usd_set_rate", "ar")
