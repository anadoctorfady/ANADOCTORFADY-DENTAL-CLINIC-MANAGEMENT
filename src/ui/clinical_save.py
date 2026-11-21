"""Round 16 item 9: ONE save button for the four clinical inputs.

Replaces the per-table Add buttons (see clinical_tables.add, now a
thin wrapper over save_all). The all-four-filled gate stays: a field
counts as filled when it has text OR a row was saved today. Every
filled input is saved in one visit row set (complaint+symptoms share
one complaints row; diagnosis / procedure get their own rows, with
the selected teeth + author + created_at, as before).

This also fixes the "text required" bug (round 16): the old
add(tab, "complaint") read ONLY txt_complaint, but the symptom
table's Add button was wired to that same kind -- so text typed in
the Symptoms box was invisible to the save handler, which reported
"Text required!" even though text had been entered. save_all reads
each field from its own widget, so text in ANY of the four boxes is
seen; a symptoms-only second save of the day now saves a symptoms
row instead of erroring.

Round 17 (item 6): the four per-field note entries are ONE visit-
notes entry (tab.txt_visit_note, built by clinical_save_row). It
is NOT part of the all-four-filled gate: an empty note never blocks
a save. When present, its text is written to EVERY saved row's
existing notes column - complaints.notes AND complaints.
symptoms_notes (the complaints row carries both), diagnoses.notes,
procedures.notes - so history display and the 24h edit flow see
exactly the same columns as before.
"""
from datetime import datetime

from src.config.strings import t
from src.models.database import get_connection
from src.models.phrases import save_phrase


def _visit_note(tab):
    """The single visit-notes text ("" when the widget is absent).
    Falls back to the legacy per-field note name - in the real UI
    both names alias the same widget (clinical_save_row)."""
    from src.ui import clinical_tables as _ct
    w = getattr(tab, "txt_visit_note", None)
    if w is not None:
        return _ct._text(tab, "txt_visit_note")
    return _ct._text(tab, "txt_complaint_note")


def _clear_visit_note(tab):
    """Empty the visit-notes entry after a save (explicit, in
    addition to the alias clearing clinical_tables._clear does)."""
    w = getattr(tab, "txt_visit_note", None)
    if w is not None:
        try:
            w.delete("1.0", "end")
        except Exception:
            pass


def save_all(tab):
    """Save every filled clinical input for the current patient.
    Returns True when the visit was saved (or nothing new was left
    to save); False when blocked (no patient / missing fields)."""
    if not tab._need():
        return False
    # Helpers live in clinical_tables; imported lazily so the two
    # modules never form a top-level cycle (and so the gate error
    # goes through clinical_tables.messagebox, which the tests patch).
    from src.ui import clinical_tables as _ct
    lang = getattr(tab.app, "lang", "en")
    missing = _ct.missing_fields(tab)
    if missing:
        names = ", ".join(t(_ct.FIELD_KEYS[k], lang) for k in missing)
        _ct.messagebox.showerror(t("savegate.title", lang),
                                 t("savegate.missing", lang).format(fields=names))
        return False
    texts = {key: _ct._text(tab, attr) for key, attr, _t in _ct.FIELDS}
    if not any(texts.values()):
        return True  # everything already saved today; nothing new
    # Round 17: ONE visit note for the whole visit (never gated on).
    # Read once, before any _clear() below wipes the widget.
    visit_note = _visit_note(tab)
    fid = tab.app.current_patient["file_number"]
    d = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().isoformat()
    author = (getattr(tab, "current_user", None)
              or getattr(tab.app, "current_user", None) or "fady")
    teeth = ",".join(tab.app.chart_teeth())
    conn = get_connection(); cur = conn.cursor()
    saved = set()
    if texts["complaint"] or texts["symptom"]:
        cur.execute("INSERT INTO complaints(patient_file,visit_date,complaint,"
                    "symptoms,notes,symptoms_notes,author,created_at) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (fid, d, texts["complaint"], texts["symptom"],
                     visit_note, visit_note, author, now))
        saved.add("complaint")
    for kind in ("diagnosis", "procedure"):
        if not texts[kind]:
            continue
        table, col = _ct.TABLES[kind]
        cur.execute(f"INSERT INTO {table}(patient_file,visit_date,tooth_number,"
                    f"{col},notes,author,created_at) VALUES(?,?,?,?,?,?,?)",
                    (fid, d, teeth, texts[kind],
                     visit_note, author, now))
        saved.add(kind)
    conn.commit(); conn.close()
    if "complaint" in saved:
        if texts["complaint"]:
            save_phrase("complaint", texts["complaint"])
        if texts["symptom"]:
            save_phrase("symptom", texts["symptom"])
    if "procedure" in saved:
        save_phrase("service", texts["procedure"])
    for kind in saved:
        _ct._clear(tab, kind)
    _clear_visit_note(tab)
    tab.app.refresh_clinical()
    return True
