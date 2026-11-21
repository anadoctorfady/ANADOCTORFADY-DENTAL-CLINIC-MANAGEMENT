"""Patient panels on the clinical page (round 15+). Round 23
(item 2b): the Recent Payments panel is REMOVED -- the History
trees now carry each session's Total / Paid / Remaining
(clinical_history.py / history_money.py) and its row-click
payment-detail dialog migrated onto History rows (double-click).
Only Therapeutic Procedures is still built (MAIN_PANELS), in
the MAIN SCROLL FLOW under History. The Health panel is
superseded by the pinned header's Health lines and the Rx
summary panel by the shell column's Prescriptions section.
PANELS keeps all four entries as the colour catalogue and the
format_* / last_payments helpers stay (data tests use them);
build_panels() takes a `kinds` subset and refresh_panels()
fills only built panels. Each built panel: a BROWN header bar
(#7A3F16, white text) and a body in the iOS27 colour family
(table_colors), a DIFFERENT colour per panel.
refresh_right_panels() (round-16 contract) is the canonical
refresh entry point; headers collapse / expand on click
(clinical_panel_interact). Empty states show a bilingual
"none" message and never crash on nulls. <200 lines."""
import tkinter as tk
from src.config.strings_r16_clinical import r16_t
from src.config.theme import current, is_dark, RADIUS_PANEL
from src.models.database import get_connection, init_db
from src.models.interactions import parse_list
from src.models.prescriptions import get_prescription_items, list_prescriptions
from src.ui.clinical_proc_panel import format_procedures, recent_procedures
from src.ui.clinical_table_style import BROWN_HEADER, r15_t, table_colors
from src.ui.rounded_frame import RoundedFrame
from src.ui.rounded_lists import RoundedText

PANELS = (("meds", "r15.panels.meds_title", "complaint"),
          ("payments", "r15.panels.payments_title", "symptom"),
          ("procedures", "r15.panels.proc_title", "diagnosis"),
          ("rx", "r15.panels.rx_title", "procedure"))
PANEL_LIMIT = 4
# Panels built in the app (main scroll flow): round 23 removed
# "payments", round 24 removed "procedures" (unified table now).
MAIN_PANELS = ()


def meds_allergies(patient):
    """Meds/allergies lists from the patient row; nulls -> []."""
    p = patient or {}
    return {"medicines": parse_list(p.get("current_medications") or ""),
            "allergies": parse_list(p.get("allergies") or "")}


def diseases_list(patient):
    """Diseases from the patient row; missing / empty -> []."""
    return parse_list((patient or {}).get("diseases") or "")


def last_payments(patient_file, limit=PANEL_LIMIT):
    """Most recent `limit` financial rows for one patient: date, tooth,
    paid + total in base currency. No rows / null -> []."""
    if not patient_file:
        return []
    init_db(); from src.models.finance_totals import conv_sql; from src.models.currency import default_currency; _b = default_currency()
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute(f"""SELECT visit_date, tooth_number,
            {conv_sql("paid_syp", "paid_amount")}, {conv_sql("total_syp", "total_cost")}
            FROM financials WHERE patient_file=? ORDER BY id DESC LIMIT ?""",
                    (_b, _b, _b, _b, patient_file, limit))
        rows = [{"date": r[0] or "", "tooth": r[1] or "",
                 "paid": float(r[2] or 0), "total": float(r[3] or 0)}
                for r in cur.fetchall()]
    except Exception:
        rows = []
    conn.close()
    return rows


def recent_prescriptions(patient_file, limit=PANEL_LIMIT):
    """Most recent `limit` prescriptions for one patient: id, date,
    doctor, drug generic names. No rows / null file -> []."""
    if not patient_file:
        return []
    out = []
    try:
        for rx in list_prescriptions(patient_file)[:limit]:
            drugs = [i.get("generic") or ""
                     for i in get_prescription_items(rx["id"])]
            out.append({"id": rx["id"], "date": rx.get("date") or "",
                        "doctor": rx.get("doctor") or "",
                        "drugs": [d for d in drugs if d]})
    except Exception:
        return []
    return out


def format_meds(data, lang, diseases=None):
    """Medicines + allergies lines; with `diseases` given, a Diseases
    line is added first (None keeps the old two-line output)."""
    none = r15_t("r15.panels.none", lang)
    meds = ", ".join(data["medicines"]) if data["medicines"] else none
    alg = ", ".join(data["allergies"]) if data["allergies"] else none
    lines = [f"{r15_t('r15.panels.meds_label', lang)} {meds}",
             f"{r15_t('r15.panels.allergies_label', lang)} {alg}"]
    if diseases is not None:
        dis = ", ".join(diseases) if diseases else none
        lines.insert(0, f"{r16_t('r16.panels.diseases_label', lang)} {dis}")
    return lines


def format_payments(rows, lang):
    """One line per payment: date -- what it was for -- amount paid."""
    if not rows:
        return [r15_t("r15.panels.none_payments", lang)]
    out = []
    for r in rows:
        what = (r15_t("r15.panels.tooth_fmt", lang).format(teeth=r["tooth"])
                if r["tooth"] else r15_t("r15.panels.visit", lang))
        out.append(r15_t("r15.panels.paid_fmt", lang).format(
            date=r["date"] or "—", what=what, amt=f"{r['paid']:g}"))
    return out


def format_rx(rows, lang):
    """One line per prescription: #id, date, doctor, drug names."""
    if not rows:
        return [r15_t("r15.panels.none_rx", lang)]
    return [r15_t("r15.panels.rx_fmt", lang).format(
        pid=r["id"], date=r["date"] or "—", doctor=r["doctor"] or "—",
        drugs=", ".join(r["drugs"]) or r15_t("r15.panels.none", lang))
        for r in rows]


def build_panels(tab, parent, kinds=MAIN_PANELS):
    """Create the `kinds` panels (round 23 default: procedures
    only). Sets tab.panel_texts / tab.panel_frames; fills them
    for the current patient (or the no-patient message)."""
    lang = getattr(tab.app, "lang", "en")
    dark = is_dark()
    tab.panel_texts = {}
    tab.panel_frames = {}
    for key, title_key, colour_kind in PANELS:
        if key not in kinds:
            continue
        cols = table_colors(colour_kind, dark)
        frm = RoundedFrame(parent, bg=cols["bg"], border=current()["border"], radius=RADIUS_PANEL)
        frm.pack(fill="x", pady=4)
        tab.panel_frames[key] = frm
        hdr = tk.Frame(frm.inner, bg=BROWN_HEADER)
        hdr.pack(fill="x")
        tk.Label(hdr, text=r15_t(title_key, lang), bg=BROWN_HEADER, fg="white",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=3)
        body = RoundedText(frm.inner, height=3, wrap="word", bg=cols["bg"],
                           fg=cols["body_fg"], font=("Segoe UI", 9), state="disabled")
        body.pack(fill="x", padx=6, pady=4)
        tab.panel_texts[key] = body
    tab._panels_fid = "unfilled"  # sentinel: first refresh always fills
    refresh_panels(tab)
    from src.ui.clinical_panel_interact import attach_panel_interactions
    attach_panel_interactions(tab)


def refresh_right_panels(tab):
    """Canonical entry point (round 16 contract): re-read the current
    patient's panels and repopulate them. The Rx worker calls this
    from the Rx save path."""
    refresh_panels(tab, force=True)


def refresh_panels(tab, force=False):
    """Rewrite the built panel bodies for tab.app.current_patient.
    Skips when the file_number is unchanged unless force=True.
    Also stores tab._panel_rows (clicked row -> its record)."""
    if not getattr(tab, "panel_texts", None):
        return
    lang = getattr(tab.app, "lang", "en")
    patient = getattr(tab.app, "current_patient", None) or {}
    fid = patient.get("file_number")
    if not force and fid == getattr(tab, "_panels_fid", None):
        return
    tab._panels_fid = fid
    if not fid:
        no = r15_t("r15.panels.no_patient", lang)
        lines = {k: [no] for k in tab.panel_texts}
        tab._panel_rows = {"payments": [], "rx": [], "procedures": []}
    else:
        ma = meds_allergies(patient)
        dis = diseases_list(patient)
        meds_lines = (format_meds(ma, lang, diseases=dis)
                      if (ma["medicines"] or ma["allergies"] or dis)
                      else [r15_t("r15.panels.none_meds", lang)])
        pays = last_payments(fid); rxs = recent_prescriptions(fid)
        procs = recent_procedures(fid)
        tab._panel_rows = {"payments": pays, "rx": rxs, "procedures": procs}
        lines = {"meds": meds_lines, "payments": format_payments(pays, lang),
                 "procedures": format_procedures(procs, lang),
                 "rx": format_rx(rxs, lang)}
    for key, ls in lines.items():
        body = tab.panel_texts.get(key)
        if body is None:
            continue  # round 22: panel not built in this layout
        body.configure(state="normal")
        body.delete("1.0", tk.END)
        body.insert("1.0", "\n".join(ls))
        body.configure(state="disabled")
