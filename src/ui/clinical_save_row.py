"""Clinical save row: per-field note removal + notes/save rows.

Split out of clinical_tables.py (200-line cap). Three jobs:

- drop_field_note(): build_field_row (clinical_table_style) still
  creates a small per-field notes widget beside each of the four
  fields. Round 17 removed them from the grid: the label + Text live
  in one small frame, so destroying that frame frees the full table
  width for the main field.

- build_sticky_bar(): round 18 (item 5) pinned a bar to the BOTTOM
  of the ClinicalTab. Round 19 (item 3) SUPERSEDES it: the notes +
  Save now live in the input block at the top of the right area,
  directly under the one-row tables. Kept only so older callers
  importing it do not break; ClinicalTab no longer calls it.

- build_save_row(): builds, INTO the input block (`parent`, the
  frame that also holds the one-row tables grid), the ONE visit-
  notes row (label + entry + its Templates button - the existing
  phrase picker over the "note" pool) and, DIRECTLY UNDER it, the
  Save row holding the single "Save visit" button. Both rows are
  at the top of the right area, reachable without scrolling. The
  note is part of the visit record but NOT required by the gate.

The note widget is a RoundedText (Text API) so clinical_save._text,
clinical_tables._clear and ClinicalTab._clear_drafts - which all
read/delete via "1.0"..END - work on it unchanged. It is exposed as
tab.txt_visit_note AND under the four legacy per-field note names
(txt_complaint_note / txt_sym_note / txt_diagnosis_note /
txt_procedure_note), all aliasing this ONE widget, so the existing
draft-clearing in clinical.py (which loops <field>_note on patient
switch / clear()) clears it without clinical.py changing.
<200 lines."""
import tkinter as tk

from src.config.strings import t
from src.config.strings_r16_clinical import r16_t
from src.config.theme import current
from src.ui.clinical_table_style import bind_field, bind_inner_wheel
from src.ui.paper_bg import attach_paper_bg
from src.ui.phrase_picker import attach_picker_button
from src.ui.rounded import rounded_button
from src.ui.rounded_lists import RoundedText

NOTE_ALIASES = ("txt_complaint_note", "txt_sym_note",
                "txt_diagnosis_note", "txt_procedure_note")


def drop_field_note(tab, kind, widget_attr):
    """Destroy the per-field notes frame build_field_row created
    for `widget_attr` and drop its attribute / clipboard registry
    entry, so nothing can read a destroyed widget. build_save_row
    later re-points the <field>_note attributes at the one visit-
    notes widget."""
    note = getattr(tab, f"{widget_attr}_note", None)
    if note is not None:
        try:
            note.master.destroy()
        except Exception:
            pass
        try:
            delattr(tab, f"{widget_attr}_note")
        except AttributeError:
            pass
    tab.clipboard_fields.pop(f"{kind}_note", None)


def build_sticky_bar(tab):
    """Create tab.sticky_bar: an empty bar pinned at the bottom of
    the ClinicalTab (pack side="bottom" BEFORE the PanedWindow is
    packed with expand, so it always keeps its strip). build_save_row
    fills it with the notes field + Templates + Save visit."""
    th = current()
    bar = tk.Frame(tab, bg=th["bg"])
    bar.pack(side="bottom", fill="x", padx=8, pady=(2, 6))
    attach_paper_bg(bar)
    tab.sticky_bar = bar
    return bar


def build_save_row(tab, parent, on_save):
    """Build the visit-notes row + the Save row (tab.btn_save_visit,
    command=on_save) into the input block `parent`, directly under
    the one-row tables grid (round 19 item 3). Notes row: label,
    the ONE visit-notes entry, Templates button. Save row under it:
    the single Save visit button, right-aligned."""
    lang = getattr(tab.app, "lang", "en")
    th = current()
    bg = parent["bg"]
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", padx=3, pady=(2, 1))
    tab.visit_note_row = row
    tk.Label(row, text=t("savegate.note", lang), bg=bg,
             fg=th["text"], font=("Segoe UI", 9, "bold")).pack(
                 side="left", padx=(2, 4))
    note = RoundedText(row, height=1, width=1, font=("Segoe UI", 10), wrap="word",
                       bg=th["card"], fg=th["text"])
    note.pack(side="left", fill="x", expand=True, padx=(0, 6))
    tab.txt_visit_note = note
    for attr in NOTE_ALIASES:
        setattr(tab, attr, note)
    bind_field(tab, note, "visit_note")
    bind_field(tab, note, "notes")  # R21 item 5: alias -- the visit Notes is the ONLY notes field now
    bind_inner_wheel(note)
    # Round 18 item 1 (UI): Templates button for the notes field,
    # at the right end of the notes row. Same picker the four
    # clinical fields use.
    btn = attach_picker_button(row, "note", note, tab.current_user)
    btn.pack(side="right")
    tab.notes_templates_btn = btn
    srow = tk.Frame(parent, bg=bg)
    srow.pack(fill="x", padx=3, pady=(0, 1))
    tab.save_row = srow
    tab.btn_save_visit = rounded_button(
        srow, text=r16_t("r16.save.visit", lang),
        bg=th["card"], fg=th["text"], command=on_save)
    tab.btn_save_visit.pack(side="right")
    return row
