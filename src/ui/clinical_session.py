"""Round 24 (items 2 + 6): the UNIFIED clinical table builder.

One component replaces the four separate input tables + the
History tree / Diagnosis-Procedures sub-trees + the Therapeutic
Procedures panel in the Clinical tab's main flow:

- ENTRY AREA (top): the four clinical text fields, built by
  clinical_tables.build_sections into tab.input_block -- the
  widget names txt_complaint / txt_sym / txt_diagnosis /
  txt_procedure / txt_visit_note are UNCHANGED, so chart tooth
  insertion, Templates/phrase buttons, clipboard-history binding
  and draft clearing keep working exactly as before -- plus the
  session money row (tab.sess_money_row: Date / Tooth / Total /
  Paid / Remaining-live) and the Save row (tab.btn_save_visit,
  repacked UNDER the money row; its command routes through
  clinical_tables.add -> clinical_session_save.save_session).
- RECORD ROWS (below): tab.tree_history (clinical_history: one
  row per session from history_money.session_rows, language-
  ordered columns, zebra-striped) + Edit / Delete / Cancel bar.

Entry helpers: clinical_session_entry. Save: clinical_session_
save (+ _store). Edit/delete: clinical_session_edit / _delete.
<200 lines."""
import tkinter as tk
from datetime import datetime
from src.config.strings import t
from src.config.strings_r18_clinical import r18_t
from src.config.strings_r24_session import sess_t
from src.config.theme import current, is_dark
from src.ui import clinical_history as _hist
from src.ui import clinical_tables as _tables
from src.ui import clinical_session_entry as _entry
from src.ui.clinical_table_style import stack_color
from src.ui.clipboard_picker import bind_clipboard_picker
from src.ui.rounded import rounded_button
from src.ui.rounded_widgets import RoundedEntry


def build_unified(tab, parent):
    """Build the unified table into the tab's scroll flow: the
    entry block (tab.input_block, a direct child of `parent`)
    followed by the records section (tab.history_section)."""
    th = current()
    lang = getattr(tab.app, "lang", "en")
    tab._editing_session = None
    tab.on_session_dblclick = lambda: _start_edit(tab)
    block = tk.Frame(parent, bg=th["bg"]); block.pack(fill="x")
    tab.input_block = block
    _tables.build_sections(tab, block)
    _build_money_row(tab, block)
    # The Save row was packed by build_sections directly under the
    # notes row; repack it UNDER the money row so the entry reads
    # fields -> notes -> money -> Save session (owner's order).
    try:
        tab.save_row.pack_forget()
        tab.save_row.pack(fill="x", padx=3, pady=(0, 1))
    except Exception:
        pass
    try:
        tab.btn_save_visit.config(text=sess_t("sess.save", lang))
    except Exception:
        pass
    _build_records(tab, parent)
    return block


def _start_edit(tab):
    from src.ui import clinical_session_edit as _edit
    return _edit.start_edit(tab)


def _build_money_row(tab, parent):
    """Date / Tooth / Total / Paid / Remaining-live row of the
    entry area (tab.e_sess_date, tab.e_sess_tooth, tab.e_sess_
    total, tab.e_sess_paid, tab.lbl_sess_remain)."""
    th = current(); lang = getattr(tab.app, "lang", "en"); bg = parent["bg"]
    row = tk.Frame(parent, bg=bg); row.pack(fill="x", padx=3, pady=(1, 1))
    tab.sess_money_row = row
    f9 = ("Segoe UI", 9); f9b = ("Segoe UI", 9, "bold")

    def _lab(text):
        tk.Label(row, text=text, bg=bg, fg=th["text"], font=f9).pack(side="left", padx=(6, 2))

    _lab(t("clinical.col_date", lang))
    tab.e_sess_date = RoundedEntry(row, width=10, font=f9b, justify="center")
    tab.e_sess_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
    tab.e_sess_date.pack(side="left", padx=2)
    _lab(t("clinical.col_tooth", lang))
    tab.e_sess_tooth = RoundedEntry(row, width=8, font=f9b, justify="center")
    tab.e_sess_tooth.pack(side="left", padx=2)
    _lab(t("clinical.total", lang))
    tab.e_sess_total = RoundedEntry(row, width=8, font=f9b, justify="center")
    tab.e_sess_total.insert(0, "0"); tab.e_sess_total.pack(side="left", padx=2)
    _lab(t("clinical.paid", lang))
    tab.e_sess_paid = RoundedEntry(row, width=8, font=f9b, justify="center")
    tab.e_sess_paid.insert(0, "0"); tab.e_sess_paid.pack(side="left", padx=2)
    _lab(t("clinical.remaining", lang))
    tab.lbl_sess_remain = tk.Label(row, text="0.00", bg=bg, fg=th["text"], font=("Segoe UI", 10, "bold"), width=9)
    tab.lbl_sess_remain.pack(side="left", padx=2)
    tab.lbl_money_lock = tk.Label(row, text="", bg=bg, fg="#991B1B", font=("Segoe UI", 8))
    tab.lbl_money_lock.pack(side="left", padx=4)
    for e in (tab.e_sess_total, tab.e_sess_paid):
        e.bind("<KeyRelease>", lambda _e: _entry.update_sess_remaining(tab))
    for name, w in (("sess_date", tab.e_sess_date), ("sess_tooth", tab.e_sess_tooth),
                    ("sess_total", tab.e_sess_total), ("sess_paid", tab.e_sess_paid)):
        bind_clipboard_picker(w); tab.clipboard_fields[name] = w
    return row


def _build_records(tab, parent):
    """Records section: heading + the session tree (tab.tree_
    history) + Edit / Delete / Cancel bar + status/editing labels."""
    from src.ui import clinical_session_edit as _edit
    from src.ui import clinical_session_delete as _del
    th = current(); lang = getattr(tab.app, "lang", "en")
    bg = stack_color("history", is_dark())
    section = tk.Frame(parent, bg=bg); section.pack(fill="x", pady=4)
    tab.history_section = section; tab.unified_section = section
    tk.Label(section, text=r18_t("r18.clinical.history_heading", lang), bg=bg, fg=th["accent"],
             font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=4, pady=(2, 2))
    _hist.build_history_tree(tab, section)
    bar = tk.Frame(section, bg=bg); bar.pack(fill="x", padx=4, pady=(0, 4))
    tab.sess_bar = bar
    tab.btn_sess_edit = rounded_button(bar, text=sess_t("sess.edit", lang), bg=th["card"], fg=th["text"],
                                       state="disabled", command=lambda: _edit.start_edit(tab))
    tab.btn_sess_edit.pack(side="left", padx=2)
    tab.btn_sess_delete = rounded_button(bar, text=sess_t("sess.delete", lang), bg=th["card"], fg=th["text"],
                                         state="disabled", command=lambda: _del.delete_selected(tab))
    tab.btn_sess_delete.pack(side="left", padx=2)
    tab.btn_sess_cancel = rounded_button(bar, text=sess_t("sess.cancel_edit", lang), bg=th["card"],
                                         fg=th["text"], command=lambda: _del.cancel_edit(tab))
    # Packed only while editing (clinical_session_edit.set_editing_ui).
    tab.sess_status = tk.Label(bar, text="", bg=bg, fg="#991B1B", font=("Segoe UI", 9))
    tab.sess_status.pack(side="right", padx=4)
    tab.lbl_editing = tk.Label(section, text="", bg=bg, fg=th["accent"], font=("Segoe UI", 9, "bold"))
    tab.lbl_editing.pack(anchor="w", padx=6)
    tab.tree_history.bind("<<TreeviewSelect>>", lambda _e: _edit.sync_edit_buttons(tab), add="+")
    return section
