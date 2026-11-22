"""The session tree of the UNIFIED clinical table (R23 tree,
R24 home: clinical_session._build_records).

One row per visit session (patient + date + treated tooth set)
showing the four clinical fields AND that session's Total / Paid
/ Remaining (src.models.history_money: financial rows matched on
patient + visit_date + exact tooth set, summed; no matching row
-> blank money cells). Round 24: the Diagnosis / Procedures
sub-trees are GONE -- this tree IS the record list, with Edit /
Delete on its rows (clinical_session_edit / _delete); the
Remaining cell DISPLAYS max(Total - Paid, 0) (a session's raw
remaining can go negative when it settles earlier debt).

Column order (item 1): date + tooth stay fixed at the start;
the clinical columns follow the app language -- EN left-to-right
complaint, symptom, diagnosis, procedure; AR left-to-right
procedure, diagnosis, symptom, complaint, so reading from the
RIGHT gives complaint -> symptoms -> diagnosis -> procedure.
Total / Paid / Remaining always come after the clinical columns.
The tree is built at tab-build time from the app language (the
UI is rebuilt on language toggle), so the order is per-language
by construction.

The Recent Payments panel was removed in round 23 (its content
is these money columns now); its one unique behaviour -- click a
payment to see its detail -- is migrated here: double-clicking a
History row WITH money opens the same payment-detail dialog the
panel used (r16.panels.payment_detail_* strings). <200 lines."""
import tkinter as tk
from tkinter import ttk, messagebox

from src.config.strings import t
from src.config.strings_r16_clinical import r16_t
from src.config.theme import current, RADIUS_TABLE
from src.models.history_money import session_rows
from src.ui.clinical_table_style import r15_t
from src.ui.rounded_frame import RoundedFrame
from src.ui.vivid_rows import ensure_vivid_style, vivid_tree  # R40

CLINICAL_COLS = ("complaint", "symptom", "diagnosis", "procedure")
COL_KEYS = {"date": "clinical.col_date", "tooth": "clinical.col_tooth",
            "complaint": "clinical.complaint_label",
            "symptom": "clinical.symptoms_label",
            "diagnosis": "clinical.col_diag",
            "procedure": "clinical.col_proc",
            "total": "clinical.col_total", "paid": "clinical.col_paid",
            "remain": "clinical.col_remain"}
WIDTHS = {"date": 90, "tooth": 60, "complaint": 200, "symptom": 200,
          "diagnosis": 200, "procedure": 200, "total": 100,
          "paid": 100, "remain": 100}
_VALUE_KEY = {"remain": "remaining"}  # column id -> session dict key


def clinical_display_order(lang):
    """Clinical kinds in on-screen left-to-right order for `lang`:
    EN keeps complaint..procedure; AR reverses it so complaint is
    rightmost (round 23 item 1, shared by tables + History)."""
    return CLINICAL_COLS if lang != "ar" else tuple(reversed(CLINICAL_COLS))


def history_columns(lang):
    """Full History column order for `lang`: date, tooth, the
    clinical columns in language order, then total/paid/remain."""
    return ("date", "tooth") + clinical_display_order(lang) + \
        ("total", "paid", "remain")


def _fmt(value):
    """Money cell: None (no matching financial row) -> blank."""
    return "" if value is None else float(value)


def flat_cell(value):
    """Display form of a text cell (R41 item 4): line breaks in the
    stored clinical text become ' | ' (the separator session_rows
    already joins with). A Treeview row is ONE fixed-height line,
    so a raw newline left only the first line readable — the rest
    clipped (X11) or spilling over the rows below with the row
    colour/selection painting only the first line (owner's Windows
    report). Stored data is NOT changed: Edit reloads the full
    multi-line text, and reports print it as written."""
    if not isinstance(value, str) or ("\n" not in value and "\r" not in value):
        return value
    parts = [p.strip() for p in value.replace("\r\n", "\n")
             .replace("\r", "\n").split("\n")]
    return " | ".join(p for p in parts if p)


def money_values(mmap, row):
    """(total, paid, remaining) cell values for one diagnoses /
    procedures row dict, from a history_money.money_map: the
    session's summed money, or blanks when no financial row
    matches this row's date + tooth set (round 23 item 2a -- the
    per-kind history trees show the same money as the unified
    History tree)."""
    from src.models.history_money import parse_teeth
    m = mmap.get((row.get("visit_date") or "",
                  parse_teeth(row.get("tooth_number"))))
    return (m["total"], m["paid"], m["remaining"]) if m else ("", "", "")


def build_history_tree(tab, parent):
    """Create tab.tree_history (+ tab.history_columns, the column
    order it was built with) inside the History section."""
    th = current()
    lang = getattr(tab.app, "lang", "en")
    cols = history_columns(lang)
    tab.history_columns = cols
    wrap = RoundedFrame(parent, bg=th["panel"], border=th["border"], radius=RADIUS_TABLE)
    wrap.pack(fill="x", padx=4, pady=2)
    # R40 item 2: the session table wears the vivid rotating rows.
    tree = ttk.Treeview(wrap.inner, columns=cols, show="headings", height=5,
                        style=ensure_vivid_style())
    for c in cols:
        tree.heading(c, text=t(COL_KEYS[c], lang))
        tree.column(c, width=WIDTHS.get(c, 120), minwidth=50,
                    stretch=c in CLINICAL_COLS)
    tree.pack(fill="both", expand=True)
    tab.tree_history = tree
    tab._history_sessions = []
    # Round 24: double-click loads the session into the entry area
    # for editing when the tab provides the hook (the unified
    # table does); the R23 payment-detail dialog stays the
    # fallback for hook-less hosts.
    def _dbl(_e=None):
        hook = getattr(tab, "on_session_dblclick", None)
        if hook is not None:
            return hook()
        return show_history_payment_detail(tab)
    tree.bind("<Double-1>", _dbl)
    return tree


def refresh_history(tab, fid):
    """Refill tab.tree_history for patient `fid` (None clears it).
    Stores the session dicts on tab._history_sessions in display
    order, so a selected row maps back to its session/money."""
    tree = getattr(tab, "tree_history", None)
    if tree is None:
        return
    for i in tree.get_children():
        tree.delete(i)
    tab._history_sessions = session_rows(fid)
    cols = getattr(tab, "history_columns", None) or \
        history_columns(getattr(tab.app, "lang", "en"))
    for idx, s in enumerate(tab._history_sessions):
        values = []
        for c in cols:
            if c == "remain":
                # R24 display rule: max(Total - Paid, 0); blank when
                # the session has no financial row at all.
                values.append("" if s["total"] is None else
                              _fmt(max(float(s["total"]) - float(s["paid"] or 0), 0.0)))
            elif c in ("total", "paid"):
                values.append(_fmt(s[_VALUE_KEY.get(c, c)]))
            else:
                values.append(s[_VALUE_KEY.get(c, c)])
        tree.insert("", "end", iid=f"hist{idx}",
                    values=tuple(flat_cell(v) for v in values))
    vivid_tree(tree)  # R40 item 2: vivid rotation (was R21 zebra)


def selected_session(tab):
    """The session dict of the selected History row, or None."""
    tree = getattr(tab, "tree_history", None)
    if tree is None:
        return None
    sel = tree.selection()
    if not sel:
        return None
    try:
        return tab._history_sessions[int(str(sel[0]).replace("hist", ""))]
    except Exception:
        return None


def show_history_payment_detail(tab):
    """Migrated Recent-Payments behaviour (round 23 item 2b):
    the payment-detail dialog for the selected session's money.
    Rows without money (no matching financial row) do nothing.
    Returns True when a dialog was shown."""
    s = selected_session(tab)
    if not s or s.get("total") is None:
        return False
    lang = getattr(tab.app, "lang", "en")
    what = (r15_t("r15.panels.tooth_fmt", lang).format(teeth=s["tooth"])
            if s["tooth"] else r15_t("r15.panels.visit", lang))
    text = r16_t("r16.panels.payment_detail_fmt", lang).format(
        date=s["date"] or "—", what=what,
        paid=f"{s['paid']:g}", total=f"{s['total']:g}")
    messagebox.showinfo(r16_t("r16.panels.payment_detail_title", lang), text)
    return True
