"""Patient info panel -- round 22: the PINNED HEADER of the
clinical tab, packed OUTSIDE the tab's scroll canvas.

Round 55 (owner correction of the round-54 tall narrow card):
the header is a short WIDE STRIP -- EXACTLY 3 ROWS x 5 columns
across the FULL main area (grid + colours in header_strip.py),
holding everything the old card had (name + file, age, birth,
Hijri, both mobiles, emergency, address, nationality, diseases,
meds, allergies, balance) plus the round-55 adherence reminder
(last 3 appointments). Father / grandfather / family stay
REMOVED. Empty fields show --; long lists wrap inside their cell
without breaking the 3-row grid. Alert strips sit UNDER the
grid, shown only when the patient has an alert (round-20 pin).
Edit / Delete / Refer stay beside Manage templates (round 54). The NAME is red when the patient owes money (round 21); Diseases / Allergies are red when non-empty. The adherence colour colours the NAME only in the patient LIST and the adherence cell's own text here -- never the header name.
Delete is ADMIN-ONLY and SOFT. No patient = cleared lines, hidden strips, placeholder name, disabled buttons (rounds 17/21).
"""
import tkinter as tk
from src.config.strings_r18_patients import tr
from src.config.strings_r19_referral import tr as _tr19
from src.config.theme import current, credit_color, debt_red
from src.ui import patient_alerts as _alerts
from src.ui.patient_delete import can_delete, confirm_and_delete
from src.ui.rounded import rounded_button
from src.ui.vivid_rows import PALETTE, TEXT_ON_VIVID

# (label key, patient-row key). Father / grandfather / family
# stay in the tuple (other surfaces may read them) but are NOT
# displayed in this header.
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
_PERS_KEYS = _FIELDS[4:9]  # mobile1, mobile2, emergency, address, nationality
_HEALTH_KEYS = _FIELDS[9:]
from src.ui.header_strip import _GRID, birth_lines, cell_bg


class PatientInfoPanel(tk.Frame):
    def __init__(self, parent, app, action_host=None):
        th = current(); super().__init__(parent, bg=th["panel"])
        self.app = app; self.lang = getattr(app, "lang", "en"); self._fid = None
        # Round 55: the strip cells are pastel in BOTH themes, so the alert red is ALWAYS the light-mode (dark) red -- the dark-mode #F87171 measures ~2:1 on pastel, and dark theme text ~1.2:1 (shot 240 caught it).
        self._red = debt_red(False)
        # R54: Edit / Delete / Refer live beside Manage templates in
        # the Clinical tab's top bar (action_host); without a host
        # they ride in a heading row above the strip (standalone).
        if action_host is not None:
            btns = action_host
        else:
            btns = tk.Frame(self, bg=th["panel"]); btns.pack(fill="x", padx=8, pady=(2, 0))
        self._btns = btns
        grid = tk.Frame(self, bg=th["panel"]); grid.pack(fill="x", padx=4, pady=2)
        self._grid = grid
        for c in range(5):
            grid.columnconfigure(c, weight=1)
        self._cells, self._cell_lbls, self._health_lbls = {}, {}, {}
        for r, c, span, key, col, kind in _GRID:
            bg = cell_bg(r, c)
            cell = tk.Frame(grid, bg=bg)
            cell.grid(row=r, column=c, columnspan=span, sticky="nsew", padx=2, pady=2)
            lbl = tk.Label(cell, text="", bg=bg, fg=TEXT_ON_VIVID,
                           font=("Segoe UI", 10, "bold") if kind == "name" else ("Segoe UI", 9),
                           wraplength=200, justify="left", anchor="nw")
            lbl.pack(fill="both", expand=True, padx=6, pady=4)
            self._cells[(r, c)] = cell
            self._cell_lbls[kind if col is None else col] = lbl
            if kind == "name":
                self._name_lbl = lbl
            if col in ("diseases", "current_medications", "allergies"):
                self._health_lbls[col] = lbl
        grid.bind("<Configure>", lambda _e: self._fit_wrap())
        # Alert strips (red allergy/meds, amber balance, teal
        # credit) sit UNDER the 3-row grid, shown only when this
        # patient has an alert (round-20 pin).
        self.alert_strip = _alerts.make_alert_strip(self)
        for _l in (self.alert_strip.lbl_health, self.alert_strip.lbl_balance,
                   self.alert_strip.lbl_credit):
            _l.config(wraplength=400, anchor="w")
        _bside = "right" if action_host is not None else "left"
        self.edit_btn = rounded_button(btns, text=tr("patient.edit_btn", self.lang), bg=th["accent"], fg="white", font=("Segoe UI", 9, "bold"), padx=12, command=self._edit)
        self.edit_btn.pack(side=_bside, padx=(0, 6))
        self.delete_btn = rounded_button(btns, text=tr("patient.delete_btn", self.lang), bg="#B3261E", fg="white", font=("Segoe UI", 9, "bold"), padx=12, command=self._delete)
        self.delete_btn.pack(side=_bside, padx=(0, 6))
        self.refer_btn = rounded_button(btns, text=_tr19("refer.btn", self.lang), bg=th["card"], fg=th["text"], font=("Segoe UI", 9, "bold"), padx=12, command=self._refer)
        self.refer_btn.pack(side=_bside)
        self.refresh(None)

    def _fit_wrap(self):
        """Refit every cell label's wraplength to its cell width
        (minus padding) so long values wrap at word boundaries
        inside the cell at any window width, never mid-word."""
        for (r, c), cell in self._cells.items():
            if cell.winfo_width() <= 20:
                continue
            for _r, _c, _s, _k, col, kind in _GRID:
                if _r == r and _c == c:
                    self._cell_lbls[kind if col is None else col].config(
                        wraplength=max(60, cell.winfo_width() - 12))

    def _line(self, key, col, patient):
        return f"{tr(key, self.lang)}: {patient.get(col) or '—'}"

    def info_text(self):
        """All header lines joined (grid order)."""
        return "\n".join(lbl.cget("text") for lbl in self._cell_lbls.values() if lbl.cget("text"))

    def _balance_text(self, fid):
        """(text, fg) for the Balance cell from the outstanding
        remaining: amount when owed (red), Credit when the clinic
        owes the patient, -- when settled."""
        try:
            from src.models.finance import patient_totals
            rem = patient_totals(fid)["remaining"]
        except Exception:
            rem = 0
        if rem and rem > 0:
            return f"{rem:,.2f}", self._red
        if rem and rem < 0:
            return f"Credit {abs(rem):,.2f}", TEXT_ON_VIVID
        return "—", TEXT_ON_VIVID

    def _adherence_text(self, fid):
        """(text, fg) for the Adherence cell: the last 3
        appointments (date + attended/late/missed) in the
        adherence colour, or -- when there are none."""
        try:
            from src.models.adherence import (COLOURS, adherence_colour,
                                              last3_appointments, reminder_line)
            entries = last3_appointments(fid)
            colour = adherence_colour([s for _d, s in entries])
            line = reminder_line(entries, self.lang)
            return line or "—", COLOURS[colour] if colour else TEXT_ON_VIVID
        except Exception:
            return "—", TEXT_ON_VIVID

    def refresh(self, patient):
        """Rebuild the strip for `patient` (a row dict) or clear it
        when None (neutral placeholder, buttons disabled). The name
        is red when the patient owes money; Diseases / Allergies
        lines are red when non-empty; the alert strips refresh
        with the panel."""
        self._fid = patient["file_number"] if patient else None
        alerts = _alerts.refresh_alert_strip(self.alert_strip, patient, self.lang) or []
        if not patient:
            self._name_lbl.config(text=tr("patient_info.title", self.lang),
                                  fg=TEXT_ON_VIVID)
            for kind, lbl in self._cell_lbls.items():
                if kind != "full_name":
                    lbl.config(text="", fg=TEXT_ON_VIVID)
            self.edit_btn.config(state="disabled"); self.delete_btn.config(state="disabled"); self.refer_btn.config(state="disabled")
            return
        owes = any(kind == "balance" for kind, _msg in alerts)
        credit = any(kind == "credit" for kind, _msg in alerts)
        # Round 55: the name sits on a pastel cell in both themes -- foregrounds are the light-mode (dark) variants, never dark theme text / dark-mode alert red.
        _fg = self._red if owes else (credit_color(False) if credit else TEXT_ON_VIVID)
        self._name_lbl.config(text=f"{tr('patient_info.name', self.lang)}: {patient.get('full_name') or '—'}  #{patient['file_number']}", fg=_fg)
        age, birth, hijri = birth_lines(patient, self.lang)
        for kind, key, val in (("age", "patient_info.age", age), ("birth", "patient_info.birth_date", birth), ("hijri", "patient_info.hijri", hijri)):
            self._cell_lbls[kind].config(text=f"{tr(key, self.lang)}: {val}", fg=TEXT_ON_VIVID)
        for key, col in _PERS_KEYS:
            self._cell_lbls[col].config(text=self._line(key, col, patient), fg=TEXT_ON_VIVID)
        for k, c in _HEALTH_KEYS:
            red = c in ("diseases", "allergies") and bool((patient.get(c) or "").strip())
            self._health_lbls[c].config(text=self._line(k, c, patient), fg=self._red if red else TEXT_ON_VIVID)
        bal, bfg = self._balance_text(patient["file_number"])
        self._cell_lbls["balance"].config(text=f"{tr('patient_info.balance', self.lang)}: {bal}", fg=bfg)
        line, afg = self._adherence_text(patient["file_number"])
        self._cell_lbls["adherence"].config(text=f"{tr('patient_info.adherence', self.lang)}: {line}", fg=afg)
        self.edit_btn.config(state="normal"); self.refer_btn.config(state="normal")
        self.delete_btn.config(state="normal" if can_delete(self.app) else "disabled")

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
