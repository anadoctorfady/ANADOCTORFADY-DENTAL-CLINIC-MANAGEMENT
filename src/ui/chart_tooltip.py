"""Round 23 item 3: treated-tooth procedure text for the chart.

Round 16 gave treated teeth a persistent tick + accent border
(chart_status.treated_teeth, from the procedures / diagnoses
tables' comma-joined tooth_number). This module adds the TEXT
behind that mark, so what was done on a tooth is readable at a
glance without opening another screen:

- tooth_history(fid, tooth): ALL saved entries for that tooth
  (procedures.procedure_done + diagnoses.diagnosis whose
  tooth_number list contains the tooth), newest first. The
  tooltip and the popup both show ALL entries (not just the
  latest) -- a tooth's full history is usually short, and the
  latest-only view would hide earlier work.
- tooltip_text / popup_text: the formatted surfaces (header +
  one "date - text" line per entry; diagnoses are prefixed).
- ToothTooltip: one reusable hover Toplevel per chart.
- open_history_popup: the click surface -- a small Toplevel
  listing that tooth's entries with dates and a Close button.

Click design (documented choice): a plain click on a tooth must
keep its round-16/17 job (toggle selection + insert the number
into the four clinical fields), so the history popup opens on
DOUBLE-click on a treated tooth, or on a single click on its
tick / count badge (those labels are not part of the toggle
binding). Both call DentalChartFrame.show_tooth_history().
<200 lines."""
import tkinter as tk

from src.config.theme import current
from src.ui.rounded import rounded_button
from src.ui.rounded_lists import RoundedText
from src.models.database import get_connection

_SOURCES = (("procedures", "procedure_done", "procedure"),
            ("diagnoses", "diagnosis", "diagnosis"))
_L = {  # bilingual literals (this module owns no strings file)
    "en": {"title": "Tooth {n} - treatment history",
           "none": "No recorded procedures for this tooth.",
           "diag": "[Diagnosis] ", "close": "Close"},
    "ar": {"title": "السن {n} - سجل العلاج",
           "none": "لا توجد إجراءات مسجلة لهذا السن.",
           "diag": "[تشخيص] ", "close": "إغلاق"},
}


def _lang(lang):
    return _L.get(lang) or _L["en"]


def tooth_history(patient_file, tooth):
    """All saved procedure/diagnosis entries for ONE tooth,
    newest first: [{date, text, kind}], kind procedure|diagnosis.
    A row counts when `tooth` is in its comma-joined tooth_number
    list (exact token match, so tooth 1 never matches 11/16)."""
    tooth = str(tooth)
    if not patient_file or not tooth:
        return []
    out = []
    try:
        conn = get_connection(); cur = conn.cursor()
        for table, col, kind in _SOURCES:
            cur.execute(f"SELECT id, visit_date, tooth_number, {col} "
                        f"FROM {table} WHERE patient_file=?",
                        (patient_file,))
            for rid, date, raw, text in cur.fetchall():
                teeth = [n.strip() for n in str(raw or "").split(",")]
                if tooth in teeth and str(text or "").strip():
                    out.append({"id": rid, "date": str(date or ""),
                                "text": str(text).strip(), "kind": kind})
        conn.close()
    except Exception:
        return []
    out.sort(key=lambda e: (e["date"], e["id"]), reverse=True)
    return out


def treated_details(patient_file):
    """{tooth: [entries newest first]} for every treated tooth of
    this patient ({} when the patient has none) -- the chart's
    per-tooth text source for tooltips, badges and popups."""
    if not patient_file:
        return {}
    details = {}
    try:
        conn = get_connection(); cur = conn.cursor()
        teeth = set()
        for table, _col, _kind in _SOURCES:
            cur.execute(f"SELECT tooth_number FROM {table} "
                        "WHERE patient_file=?", (patient_file,))
            for (raw,) in cur.fetchall():
                teeth.update(n.strip() for n in str(raw or "").split(",")
                             if n.strip())
        conn.close()
    except Exception:
        return {}
    for tooth in sorted(teeth):
        entries = tooth_history(patient_file, tooth)
        if entries:
            details[tooth] = entries
    return details


def format_history(tooth, entries, lang="en"):
    """Header + one 'date - text' line per entry (ALL entries)."""
    s = _lang(lang)
    lines = [s["title"].format(n=tooth)]
    if not entries:
        lines.append(s["none"])
    for e in entries:
        prefix = s["diag"] if e.get("kind") == "diagnosis" else ""
        lines.append(f"{e.get('date', '')} - {prefix}{e.get('text', '')}")
    return "\n".join(lines)


def tooltip_text(patient_file, tooth, lang="en"):
    """Hover-tooltip content: the tooth's full procedure history."""
    return format_history(tooth, tooth_history(patient_file, tooth), lang)


def popup_text(patient_file, tooth, lang="en"):
    """Click-popup content: same full history as the tooltip."""
    return format_history(tooth, tooth_history(patient_file, tooth), lang)


class ToothTooltip:
    """One reusable hover tooltip Toplevel (chart-owned)."""

    def __init__(self, master):
        self.master = master
        self.win = None

    def show(self, x, y, text):
        self.hide()
        th = current()
        try:
            win = tk.Toplevel(self.master)
        except Exception:
            return
        win.overrideredirect(True)
        win.geometry(f"+{int(x) + 14}+{int(y) + 18}")
        tk.Label(win, text=text, bg=th["panel"], fg=th["text"],
                 justify="left", relief="solid", borderwidth=1,
                 font=("Segoe UI", 9), padx=8, pady=6).pack()
        self.win = win

    def hide(self):
        if self.win is not None:
            try:
                self.win.destroy()
            except Exception:
                pass
            self.win = None


def open_history_popup(parent, tooth, entries, lang="en"):
    """Small popup listing one tooth's procedures with dates.
    Returns the Toplevel (None when there is nothing to show)."""
    if not entries:
        return None
    s = _lang(lang)
    th = current()
    win = tk.Toplevel(parent)
    win.title(s["title"].format(n=tooth))
    win.configure(bg=th["bg"])
    # Rounded wrappers only (round-13/21 rule: no bare tk.Text /
    # tk.Button in src/ui -- test_rounded_all_static guards it).
    txt = RoundedText(win, width=52, height=min(max(len(entries) + 2, 4), 14),
                      bg=th["panel"], fg=th["text"], font=("Segoe UI", 10),
                      wrap="word")
    txt.pack(fill="both", expand=True, padx=10, pady=10)
    txt.insert("1.0", format_history(tooth, entries, lang))
    txt.configure(state="disabled")
    rounded_button(win, text=s["close"], command=win.destroy,
                   bg=th["card"], fg=th["text"]).pack(pady=(0, 10))
    return win
