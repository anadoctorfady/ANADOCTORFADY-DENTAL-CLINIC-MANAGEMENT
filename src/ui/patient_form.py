"""Patient form: 4-part name, Hijri age, auto file #. <200 lines.

Round 16: Diseases field; saving goes through
patients.save_patient_record(), which refuses a duplicate (same
first + father + family name) naming the file number.
Round 17: the form exists ONLY inside the modal new-patient dialog
(src/ui/patient_dialog.py) -- it is not hosted in the notebook any
more, and it contains NO dental chart (a new patient has no file
yet). `on_saved(fid)` (dialog mode) replaces the old collapse: the
dialog closes and opens the saved patient; without it, save falls
back to load_patients() + select_patient() on the app.
"""
import tkinter as tk
from tkinter import messagebox
from src.config.strings import t
from src.config.strings_r16_patients import tr as _tr16
from src.config.theme import current, is_dark, is_dark, RADIUS_FIELD
from src.utils.nationalities import (list_nationalities, display,
    display_for, nationality_en_for, default_nationality_display)
from src.ui.searchable_picker import SearchablePicker  # R26: popup picker (was SearchableCombobox, whose typed filter never opened)
from src.utils.hijri_age import (get_all_ages, parse_birth_date,
    parse_birth_date_lenient, format_birth_date, format_hijri_date, invalid_birth_msg)
from src.models.patients import save_patient_record, DuplicatePatientError
from src.ui import patient_alerts as _alerts; from src.ui import patient_diseases as _dis; from src.ui import patient_allergies as _alg; from src.ui import patient_medications as _med
from src.ui.wheel_scroll import bind_canvas_wheel; from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame
from src.ui.rounded_widgets import RoundedEntry
from src.ui.paper_bg import attach_paper_bg; from src.ui.panel_paper import attach_panel_paper, tinted_avg_hex
class PatientForm(tk.Frame):
    def __init__(self, parent, app, on_saved=None, **kw):
        th = current(); super().__init__(parent, bg=th["bg"], **kw)
        _pb = th["patient_bg"] if is_dark() else tinted_avg_hex(th["patient_bg"], 0.25)
        self.app = app; self.lang = getattr(app, "lang", "en")
        self.on_saved = on_saved  # round 17: dialog close/open hook
        self._collapsed = False  # compat flag: the form is always shown now
        self._canvas = tk.Canvas(self, bg=th["bg"], highlightthickness=0)
        vsb = tk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._vsb = vsb
        frm = tk.Frame(self._canvas, bg=th["bg"])
        frm.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._frm_win = self._canvas.create_window((0, 0), window=frm, anchor="nw")
        # Inner frame tracks the canvas width (else it stays ~740px wide).
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfigure(self._frm_win, width=e.width))
        self._canvas.configure(yscrollcommand=vsb.set)
        bind_canvas_wheel(self._canvas)
        self._canvas.pack(side="left", fill="both", expand=True); vsb.pack(side="right", fill="y"); attach_paper_bg(frm)
        hdr = RoundedFrame(frm, bg=th["panel"], border=th["border"]); hdr.pack(fill="x", padx=10, pady=8); hdr = hdr.inner
        self.lbl_file = tk.Label(hdr, text=t("patient.file_none", self.lang), bg=th["panel"], fg=th["accent"], font=("Segoe UI", 12, "bold"))
        self.lbl_file.pack(side="left", padx=10, pady=8)
        rounded_button(hdr, text=t("patient.save", self.lang), bg=th["accent"], fg="white", font=("Segoe UI", 10, "bold"), padx=16, command=self.save).pack(side="right", padx=6, pady=6)
        rounded_button(hdr, text=t("patient.print_pdf", self.lang), bg="#5E5CE6", fg="white", command=lambda: app.print_pdf()).pack(side="right", pady=6)
        # Job 4: red/amber alert strip (allergy/meds, unpaid balance).
        self.alert_strip = _alerts.make_alert_strip(frm)
        # Warm Sand + light brown patient details (user: #E8DCC4)
        form = RoundedFrame(frm, bg=th["patient_bg"], border=th["border"]); form.pack(fill="x", padx=10, pady=4); form = form.inner; attach_panel_paper(form, th["patient_bg"], 0.25)
        form.columnconfigure(1, weight=1); form.columnconfigure(3, weight=1)
        self.e_first = RoundedEntry(form, font=("Tahoma", 10), justify="right")
        self.e_father = RoundedEntry(form, font=("Tahoma", 10), justify="right")
        self.e_grand = RoundedEntry(form, font=("Tahoma", 10), justify="right")
        self.e_last = RoundedEntry(form, font=("Tahoma", 10), justify="right")
        self.e_birth = RoundedEntry(form, font=("Segoe UI", 10))
        self.e_birth.bind("<FocusOut>", self.on_birth, add="+")
        # Value labels: dark mode uses the text token (12.21:1).
        _val_h = th["text"] if is_dark() else th["accent"]
        _val_a = th["text"] if is_dark() else th["muted"]
        self.lbl_hijri = tk.Label(form, text="—", bg=_pb, fg=_val_h)
        self.lbl_age = tk.Label(form, text="—", bg=_pb, fg=_val_a)
        self.lbl_age_h = tk.Label(form, text="—", bg=_pb, fg=_val_a)
        self.e_m1 = RoundedEntry(form, font=("Segoe UI", 10))
        self.e_m2 = RoundedEntry(form, font=("Segoe UI", 10))
        self.e_em = RoundedEntry(form, font=("Segoe UI", 10))
        self.e_addr = RoundedEntry(form, font=("Tahoma", 10), justify="right")
        self.e_meds = RoundedEntry(form, font=("Segoe UI", 10)); self.btn_meds_templates = _med.make_medications_button(form, self.e_meds, self.lang)
        self.e_allergies = RoundedEntry(form, font=("Segoe UI", 10)); self.btn_allergy_templates = _alg.make_allergies_button(form, self.e_allergies, self.lang)
        self.e_diseases = RoundedEntry(form, font=("Segoe UI", 10)); self.btn_diseases_templates = _dis.make_diseases_button(form, self.e_diseases, self.lang)
        self.nat = tk.StringVar(value=default_nationality_display(self.lang))
        _nat_wrap = RoundedFrame(form, bg=th["panel"], border=th["border"], radius=RADIUS_FIELD, pad=2); self.e_nat = SearchablePicker(_nat_wrap.inner, list_nationalities(), lambda it: display(it, self.lang), textvariable=self.nat, lang=self.lang); self.e_nat.pack(fill="both", expand=True)
        rows = [(0, t("patient.first_name", self.lang), self.e_first, t("patient.father", self.lang), self.e_father),
                (1, t("patient.grandfather", self.lang), self.e_grand, t("patient.last_family", self.lang), self.e_last)]
        for r, l1, w1, l2, w2 in rows:
            tk.Label(form, text=l1, bg=_pb, fg=th["text"], font=("Segoe UI", 9, "bold")).grid(row=r, column=0, sticky="w", padx=10, pady=5)
            w1.grid(row=r, column=1, sticky="ew", padx=6, pady=5)
            tk.Label(form, text=l2, bg=_pb, fg=th["text"], font=("Segoe UI", 9, "bold")).grid(row=r, column=2, sticky="w", padx=10, pady=5)
            w2.grid(row=r, column=3, sticky="ew", padx=6, pady=5)
        def _lab(txt, r, c):
            tk.Label(form, text=txt, bg=_pb, fg=th["text"], font=("Segoe UI", 9, "bold")).grid(row=r, column=c, sticky="w", padx=10, pady=5)
        _lab(t("patient.birth", self.lang), 2, 0); self.e_birth.grid(row=2, column=1, sticky="ew", padx=6, pady=5)
        _lab(t("patient.hijri_date", self.lang), 2, 2); self.lbl_hijri.grid(row=2, column=3, sticky="w", padx=6)
        _lab(t("patient.age_greg", self.lang), 3, 0); self.lbl_age.grid(row=3, column=1, sticky="w", padx=6)
        _lab(t("patient.age_hijri", self.lang), 3, 2); self.lbl_age_h.grid(row=3, column=3, sticky="w", padx=6)
        _lab(t("patient.mobile1", self.lang), 4, 0); self.e_m1.grid(row=4, column=1, sticky="ew", padx=6, pady=5)
        _lab(t("patient.mobile2", self.lang), 4, 2); self.e_m2.grid(row=4, column=3, sticky="ew", padx=6, pady=5)
        _lab(t("patient.emergency", self.lang), 5, 0); self.e_em.grid(row=5, column=1, sticky="ew", padx=6, pady=5)
        _lab(t("patient.nationality", self.lang), 5, 2); _nat_wrap.grid(row=5, column=3, sticky="ew", padx=6, pady=5)
        _lab(t("patient.address", self.lang), 6, 0); self.e_addr.grid(row=6, column=1, sticky="ew", padx=6, pady=5, columnspan=3)
        _lab(t("patient.meds", self.lang), 7, 0); self.e_meds.grid(row=7, column=1, sticky="ew", padx=6, pady=5, columnspan=2); self.btn_meds_templates.grid(row=7, column=3, sticky="ew", padx=6, pady=5)
        _lab(t("patient.allergies", self.lang), 8, 0); self.e_allergies.grid(row=8, column=1, sticky="ew", padx=6, pady=5, columnspan=2); self.btn_allergy_templates.grid(row=8, column=3, sticky="ew", padx=6, pady=5)
        _lab(_tr16("patient.diseases", self.lang), 9, 0); self.e_diseases.grid(row=9, column=1, sticky="ew", padx=6, pady=5, columnspan=2); self.btn_diseases_templates.grid(row=9, column=3, sticky="ew", padx=6, pady=5)
        # Round 17: NO dental chart here (a new patient has no file yet).
    def show_form(self):
        """Compat shim: the form is always visible (round 17)."""
        self._collapsed = False
    def collapse_form(self):
        """Compat shim: nothing collapses any more (round 17); in the
        dialog, a successful save closes the dialog via on_saved."""
        self._collapsed = False
    def show_new(self):
        """Blank new-patient form: clear, focus first name."""
        self.app.current_patient = None; self.clear()
        self.lbl_file.config(text=t("shell.new_file", self.lang)); self.e_first.focus_set()
    def on_birth(self, _e=None):
        s = self.e_birth.get().strip()
        if not s:
            return
        try:
            bd = parse_birth_date_lenient(s)
            info = get_all_ages(s, lang=self.lang); g, h = info["greg_age"], info["hijri_age"]
            self.e_birth.delete(0, tk.END); self.e_birth.insert(0, format_birth_date(bd))
            self.lbl_age.config(text=t("patient.age_greg_fmt", self.lang).format(y=g['years'], m=g['months'], d=g['days'], total=g['total_days']))
            self.lbl_hijri.config(text=info["hijri_formatted"])
            self.lbl_age_h.config(text=t("patient.age_fmt", self.lang).format(y=h['years'], m=h['months'], d=h['days']))
            self._age = info
        except Exception:
            pass
    def clear(self):
        for w in [self.e_first, self.e_father, self.e_grand, self.e_last,
                  self.e_birth, self.e_m1, self.e_m2, self.e_em, self.e_addr,
                  self.e_meds, self.e_allergies, self.e_diseases]:
            w.delete(0, tk.END)
        self.nat.set(default_nationality_display(self.lang)); self.lbl_hijri.config(text="—")
        self.lbl_age.config(text="—"); self.lbl_age_h.config(text="—")
        _alerts.refresh_alert_strip(self.alert_strip, None, self.lang)
    def fill(self, row):
        self.clear()
        for e, k in [(self.e_first, "first_name"), (self.e_father, "father_name"),
                     (self.e_grand, "grand_name"), (self.e_last, "last_name"),
                     (self.e_birth, "birth_date_greg"), (self.e_m1, "mobile1"),
                     (self.e_m2, "mobile2"), (self.e_em, "emergency_phone"),
                     (self.e_addr, "address")]:
            # DB stores ISO YYYY-MM-DD; the form always shows DD/MM/YYYY.
            if k == "birth_date_greg":
                try: e.insert(0, format_birth_date(row[k] or ""))
                except Exception: e.insert(0, row[k] or "")
            else: e.insert(0, row[k] or "")
        self.nat.set(display_for(row["nationality"] or "Syrian", self.lang))
        self.e_meds.insert(0, row.get("current_medications") or "")
        self.e_allergies.insert(0, row.get("allergies") or "")
        self.e_diseases.insert(0, row.get("diseases") or "")
        self.lbl_file.config(text=t("patient.file_number", self.lang).format(n=row['file_number']))
        self.lbl_hijri.config(text=format_hijri_date(row["birth_date_greg"], self.lang))
        _alerts.refresh_alert_strip(self.alert_strip, row, self.lang)
        self.lbl_age.config(text=t("patient.age_fmt", self.lang).format(y=row['age_years'], m=row['age_months'], d=row['age_days']))
        self.lbl_age_h.config(text=t("patient.age_fmt", self.lang).format(y=row['age_hijri_years'], m=row['age_hijri_months'], d=row['age_hijri_days']))
    def save(self):
        first, father = self.e_first.get().strip(), self.e_father.get().strip()
        grand, last = self.e_grand.get().strip(), self.e_last.get().strip()
        # Round 15: grandfather is OPTIONAL -- only first, father and
        # last are required. The error names the missing field(s).
        missing = [t(k, self.lang) for k, v in (("patient.first_name", first), ("patient.father", father), ("patient.last_family", last)) if not v]
        if missing:
            messagebox.showerror(t("patient.error", self.lang), t("patient.err_names_missing", self.lang).format(fields=", ".join(missing))); return
        birth_display = self.e_birth.get().strip()
        if not birth_display:
            messagebox.showerror(t("patient.error", self.lang), t("patient.err_birth", self.lang)); return
        try:
            birth = parse_birth_date_lenient(birth_display).isoformat()  # DB stays ISO
            info = get_all_ages(birth_display, lang=self.lang); g, h = info["greg_age"], info["hijri_age"]
        except Exception:
            messagebox.showerror(t("patient.error", self.lang), invalid_birth_msg(self.lang)); return
        full = " ".join(p for p in (first, father, grand, last) if p)
        data = {"first_name": first, "father_name": father, "grand_name": grand, "last_name": last,
            "full_name": full, "birth_date_greg": birth, "birth_date_hijri": info["hijri_formatted"],
            "age_years": g["years"], "age_months": g["months"], "age_days": g["days"],
            "age_total_days": g["total_days"], "age_hijri_years": h["years"],
            "age_hijri_months": h["months"], "age_hijri_days": h["days"],
            "mobile1": self.e_m1.get().strip(), "mobile2": self.e_m2.get().strip(),
            "emergency_phone": self.e_em.get().strip(), "address": self.e_addr.get().strip(),
            "nationality": nationality_en_for(self.nat.get()),
            "current_medications": self.e_meds.get().strip(), "allergies": self.e_allergies.get().strip(),
            "diseases": self.e_diseases.get().strip()}
        cur_p = self.app.current_patient
        try:
            fid = save_patient_record(data, current_file=cur_p["file_number"] if cur_p else None)
        except DuplicatePatientError as e:
            msg = _tr16("patient.err_duplicate", self.lang).format(fid=e.file_number)
            if messagebox.askyesno(_tr16("patient.dup_title", self.lang),
                    msg + "\n" + _tr16("patient.dup_open", self.lang).format(fid=e.file_number)):
                self.app.current_patient = {"file_number": e.file_number}
                self._open_saved(e.file_number)
            return
        self.app.current_patient = {"file_number": fid}
        self.lbl_file.config(text=t("patient.file_number", self.lang).format(n=fid))
        messagebox.showinfo(t("patient.saved", self.lang), t("patient.saved_msg", self.lang).format(fid=fid))
        self._open_saved(fid)
    def _open_saved(self, fid):
        """Round 17: in the modal dialog, on_saved closes the dialog
        (it then loads + selects the patient); standalone, do it here."""
        if self.on_saved is not None:
            self.on_saved(fid)
        else:
            self.app.load_patients(); self.app.select_patient(fid)
