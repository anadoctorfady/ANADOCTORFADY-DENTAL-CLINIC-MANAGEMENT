"""Patient info panel -- round 22: the PINNED HEADER of the
clinical tab.

Rounds 18-21 this was a narrow vertical block in the shell's
far-left column (the single patient-info display since round 20,
with the alert strips and the Edit / Delete / Refer buttons).
Round 22 (owner redesign): the panel moves INTO the clinical
tab as a fixed header at the very top of the main area, packed
OUTSIDE the tab's scroll canvas, so the personal info, the
Health lines (diseases / current medications / allergies) and
both alert strips stay visible while the chart and everything
under it scrolls away. The shell's left column keeps only
search + patient list + prescriptions.

Layout (wide, compact, target ~150px tall): a heading row (name
+ file number), then three side-by-side blocks -- personal
lines A (father / grandfather / birth / family), personal lines
B (mobiles / emergency / address / nationality) and the Health
block (per-line labels + alert strips) -- then the buttons row.
In Arabic the blocks pack from the right (RTL mirror).

Colour rules carried from round 21: the NAME is red when the
patient owes money (remaining > 0); the Diseases and Allergies
lines are red whenever non-empty (the medications line is NOT
red). Delete is ADMIN-ONLY and SOFT (patient_delete). With no
patient open every line is cleared, the strips hide, the name
shows the neutral panel title as a placeholder, and all three
buttons are disabled -- no stale data ever (rounds 17/21
patient-isolation rules). The joined text of all lines is
available via info_text().
"""
import tkinter as tk

from src.config.strings_r18_patients import tr
from src.config.strings_r19_referral import tr as _tr19
from src.config.theme import current, credit_color, debt_red, is_dark
from src.ui import patient_alerts as _alerts
from src.ui.patient_delete import can_delete, confirm_and_delete
from src.ui.rounded import rounded_button

# (label key, patient-row key) in display order.
_FIELDS = (("patient_info.name", "full_name"),
           ("patient_info.father", "father_name"),
           ("patient_info.grandfather", "grand_name"),
           ("patient_info.family", "last_name"),
           ("patient_info.mobile1", "mobile1"),
           ("patient_info.mobile2", "mobile2"),
           ("patient_info.emergency", "emergency_phone"),
           ("patient_info.address", "address"),
           ("patient_info.nationality", "nationality"),
           ("patient_info.diseases", "diseases"),
           ("patient_info.meds", "current_medications"),
           ("patient_info.allergies", "allergies"))
_A_KEYS = _FIELDS[1:3]    # father, grandfather (+ birth, family in refresh)
_B_KEYS = _FIELDS[4:9]    # mobile1, mobile2, emergency, address, nationality
_HEALTH_KEYS = _FIELDS[9:]


def _birth_text(row, lang):
    """Birth line value: DD/MM/YYYY when parseable + Hijri date
    RE-DERIVED from the Gregorian value in `lang` via format_hijri_date
    (never the stored birth_date_hijri string) + age text."""
    raw = row.get("birth_date_greg") or ""
    birth, hijri = raw, ""
    try:
        from src.utils.hijri_age import format_birth_date, format_hijri_date
        birth = format_birth_date(birth)
        hijri = format_hijri_date(raw, lang)
    except Exception:
        pass
    age = tr("patient_info.age_fmt", lang).format(
        y=row.get("age_years") or 0, m=row.get("age_months") or 0,
        d=row.get("age_days") or 0)
    return f"{birth or '—'} ({age})" + (f" — {hijri}" if hijri else "")


class PatientInfoPanel(tk.Frame):
    def __init__(self, parent, app):
        th = current()
        super().__init__(parent, bg=th["panel"])
        self.app = app
        self.lang = getattr(app, "lang", "en")
        self._fid = None
        self._red = debt_red(is_dark())
        side = "right" if self.lang == "ar" else "left"  # RTL mirror
        btn_side = "left" if self.lang == "ar" else "right"
        head = tk.Frame(self, bg=th["panel"]); head.pack(fill="x", padx=8, pady=(4, 0))
        self._name_lbl = tk.Label(head, text="", bg=th["panel"], fg=th["text"],
                                  font=("Segoe UI", 11, "bold"), anchor="w")
        self._name_lbl.pack(side=side)
        self._file_lbl = tk.Label(head, text="", bg=th["panel"], fg=th["muted"],
                                  font=("Segoe UI", 10, "bold"), anchor="w")
        self._file_lbl.pack(side=side, padx=8)
        # Round 22 compactness: the buttons ride in the heading row
        # (opposite side), keeping the header ~150px tall.
        btns = tk.Frame(head, bg=th["panel"]); btns.pack(side=btn_side)
        self._btns = btns
        cols = tk.Frame(self, bg=th["panel"]); cols.pack(fill="x", padx=8)
        mk = dict(bg=th["panel"], fg=th["text"], font=("Segoe UI", 9),
                  justify="left", anchor="nw")
        self._body_a = tk.Label(cols, text="", **mk)
        self._body_a.pack(side=side, anchor="n")
        self._body_b = tk.Label(cols, text="", **mk)
        self._body_b.pack(side=side, anchor="n", padx=14)
        health = tk.Frame(cols, bg=th["panel"]); health.pack(side=side, anchor="n")
        self._health_lbls = {}
        for _k, _c in _HEALTH_KEYS:
            _lbl = tk.Label(health, text="", wraplength=430, **mk)
            _lbl.pack(fill="x"); self._health_lbls[_c] = _lbl
        # Alert strips (red allergy/meds, amber unpaid balance) sit
        # in the Health block, under the health lines.
        self.alert_strip = _alerts.make_alert_strip(health)
        self.alert_strip.config(bg=th["panel"])
        for _l in (self.alert_strip.lbl_health, self.alert_strip.lbl_balance,
                   self.alert_strip.lbl_credit):  # R38: credit strip too
            _l.config(wraplength=400, anchor="w")
        self.edit_btn = rounded_button(
            btns, text=tr("patient.edit_btn", self.lang), bg=th["accent"],
            fg="white", font=("Segoe UI", 9, "bold"), padx=12, command=self._edit)
        self.edit_btn.pack(side=side, padx=(0, 6))
        self.delete_btn = rounded_button(
            btns, text=tr("patient.delete_btn", self.lang), bg="#B3261E",
            fg="white", font=("Segoe UI", 9, "bold"), padx=12, command=self._delete)
        self.delete_btn.pack(side=side, padx=(0, 6))
        self.refer_btn = rounded_button(
            btns, text=_tr19("refer.btn", self.lang), bg=th["card"],
            fg=th["text"], font=("Segoe UI", 9, "bold"), padx=12, command=self._refer)
        self.refer_btn.pack(side=side)
        self.refresh(None)

    def _line(self, key, col, patient):
        return f"{tr(key, self.lang)}: {patient.get(col) or '—'}"

    def info_text(self):
        """All header lines joined (file + name + body + health)."""
        parts = [self._file_lbl.cget("text"), self._name_lbl.cget("text"),
                 self._body_a.cget("text"), self._body_b.cget("text")]
        parts += [l.cget("text") for l in self._health_lbls.values()]
        return "\n".join(p for p in parts if p)

    def refresh(self, patient):
        """Rebuild the header for `patient` (a row dict) or clear it
        when None (neutral placeholder, buttons disabled). Delete is
        enabled only for the admin role. The name is red when the
        patient owes money; Diseases / Allergies lines are red when
        non-empty; the alert strips refresh with the panel."""
        self._fid = patient["file_number"] if patient else None
        alerts = _alerts.refresh_alert_strip(self.alert_strip, patient, self.lang) or []
        th = current()
        if not patient:
            self._name_lbl.config(text=tr("patient_info.title", self.lang),
                                  fg=th["text"])
            self._file_lbl.config(text="")
            self._body_a.config(text=""); self._body_b.config(text="")
            for _lbl in self._health_lbls.values():
                _lbl.config(text="", fg=th["text"])
            self.edit_btn.config(state="disabled")
            self.delete_btn.config(state="disabled")
            self.refer_btn.config(state="disabled")
            return
        owes = any(kind == "balance" for kind, _msg in alerts)  # R31: reuse the strip's alerts (was: a 2nd patient_alerts() -> 2nd patient_totals())
        credit = any(kind == "credit" for kind, _msg in alerts)  # R38
        _fg = self._red if owes else (credit_color(is_dark()) if credit else th["text"])
        self._name_lbl.config(text=self._line(*_FIELDS[0], patient), fg=_fg)
        self._file_lbl.config(text=f"#{patient['file_number']}")
        a = [self._line(k, c, patient) for k, c in _A_KEYS]
        a.append(f"{tr('patient_info.birth', self.lang)}: "
                 f"{_birth_text(patient, self.lang)}")
        a.append(self._line(*_FIELDS[3], patient))
        self._body_a.config(text="\n".join(a))
        self._body_b.config(text="\n".join(
            self._line(k, c, patient) for k, c in _B_KEYS))
        for k, c in _HEALTH_KEYS:
            red = c in ("diseases", "allergies") and bool(
                (patient.get(c) or "").strip())
            self._health_lbls[c].config(
                text=self._line(k, c, patient),
                fg=self._red if red else th["text"])
        self.edit_btn.config(state="normal")
        self.refer_btn.config(state="normal")
        self.delete_btn.config(
            state="normal" if can_delete(self.app) else "disabled")

    def _refer(self):
        """Open the refer dialog for the open patient (no-op when
        none is open, like _edit / _delete)."""
        if self._fid is None:
            return
        from src.ui.refer_dialog import open_refer_dialog
        open_refer_dialog(self.app)

    def _edit(self):
        if self._fid is None:
            return
        from src.ui.patient_dialog import open_edit_patient_dialog
        open_edit_patient_dialog(self.app, self._fid)

    def _delete(self):
        """Admin-only soft delete (patient_delete.confirm_and_delete)."""
        confirm_and_delete(self)
