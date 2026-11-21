"""Round 19 (item 3): data for the LEFT-column Therapeutic
Procedures panel. Split out of clinical_panels.py (200-line cap):
the left patient column shows the most recent procedures (what
was done) as a compact coloured panel, mirroring the payments /
prescriptions panels; the full procedures history tree stays in
the right area's history notebook. Pure data + formatting here,
so tests can check it without a display. <200 lines."""
from src.models.database import get_connection, init_db
from src.ui.clinical_table_style import r15_t

PANEL_LIMIT = 4


def recent_procedures(patient_file, limit=PANEL_LIMIT):
    """Most recent `limit` procedure rows for one patient: date,
    tooth, procedure text. No rows / null file -> []."""
    if not patient_file:
        return []
    init_db()
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("""SELECT visit_date, tooth_number, procedure_done
            FROM procedures WHERE patient_file=?
            ORDER BY id DESC LIMIT ?""", (patient_file, limit))
        rows = [{"date": r[0] or "", "tooth": r[1] or "",
                 "proc": r[2] or ""} for r in cur.fetchall()]
    except Exception:
        rows = []
    conn.close()
    return rows


def format_procedures(rows, lang):
    """One line per procedure: date -- tooth -- what was done."""
    if not rows:
        return [r15_t("r15.panels.none_proc", lang)]
    out = []
    for r in rows:
        what = (r15_t("r15.panels.tooth_fmt", lang).format(teeth=r["tooth"])
                if r["tooth"] else r15_t("r15.panels.visit", lang))
        out.append(r15_t("r15.panels.proc_fmt", lang).format(
            date=r["date"] or "—", what=what, proc=r["proc"] or "—"))
    return out
