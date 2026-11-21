"""Patient PDF via the print preview (round 16; round 25).

Every Print PDF -- including the Settings "Bilingual PDF" button --
goes through src.reports.print_preview: the preview builds the
report into a temp folder and its own Print / Save PDF actions
finish the job. Round 25: this module used to be the last direct
path (build + save at once, then a "Saved:" dialog showing the
FULL storage path); storage paths must never appear in the UI,
so it now opens the preview like every other document. Kept out
of shell.py so the shell stays <=200 lines.
"""
import tempfile

from src.models.database import get_connection
from src.reports.pdf_report import create_patient_pdf


def print_pdf_direct(app, bilingual=False):
    """Open the patient-report print preview for app.current_patient.

    The build callback hands create_patient_pdf a temp folder, so
    the preview's Print / Save PDF actions work on the built file
    and nothing is saved (or shown) before the user chooses. A
    bilingual report always builds in the app language's bilingual
    layout; a single-language one in the preview's chosen language.
    The preview text is the single-language rendering. Returns the
    preview window, or None when no patient is open."""
    if not getattr(app, "current_patient", None):
        return None
    fid = app.current_patient["file_number"]
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patients WHERE file_number=?", (fid,))
    pat = dict(cur.fetchone())

    def all_rows(tbl):
        cur.execute(f"SELECT * FROM {tbl} WHERE patient_file=?", (fid,))
        return [dict(r) for r in cur.fetchall()]

    data = {k: all_rows(k) for k in
            ["complaints", "diagnoses", "procedures", "financials", "xrays"]}
    conn.close()
    from src.reports.print_preview import show_print_preview
    from src.reports.report_text import patient_preview_lines
    tmp = tempfile.mkdtemp(prefix="anadoctorfady_preview_")
    teeth = app.chart_teeth()

    def build(lang):
        return create_patient_pdf(
            pat, data["complaints"], data["diagnoses"], data["procedures"],
            data["financials"], data["xrays"],
            language=app.lang if bilingual else lang, bilingual=bilingual,
            user_name=app.current_user, tooth_selection=teeth, out_dir=tmp)

    def lines(lang):
        return patient_preview_lines(
            pat, data["complaints"], data["diagnoses"], data["procedures"],
            data["financials"], data["xrays"], language=lang,
            tooth_selection=teeth)

    return show_print_preview(app, pat.get("full_name", ""), build,
                              getattr(app, "lang", "en"), preview_text=lines)
