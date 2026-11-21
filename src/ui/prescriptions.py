"""Prescriptions tab: searchable drugs, live interaction alerts
(colored), save ALWAYS to patient file, print PDF. <180 lines."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from src.config.strings import t
from src.config.theme import current, tree_style
from src.models.database import get_connection
from src.models.interactions import (check_interactions, parse_list,
    SEVERITY_COLORS, DISCLAIMER_EN, DISCLAIMER_AR)
from src.models.drug_diseases import check_drug_diseases  # R28: drug-disease dimension
from src.models.prescriptions import (save_prescription, list_prescriptions,
    get_prescription_items, get_prescription)
from src.utils.medications import (list_medications, display, generic_for,
    get_medication, list_by_category, categories)
from src.ui.add_drug import open_add_drug_dialog  # R26 audit: the SearchableCombobox import here was dead -- the drug control is built in rx_form.py (now a SearchablePicker)
from src.config.strings_r16_rx import rx16_t; from src.ui.rx_print import print_rx_preview, refresh_panels_after_save
from src.config.strings_r30_drug import r30_t; from src.utils.drug_classes import is_unclassified_user_drug
from src.ui import rx_form as _form
from src.ui.rounded import rounded_button
from src.ui.rounded_frame import RoundedFrame
from src.ui.rounded_widgets import RoundedEntry; from src.ui.rounded_lists import RoundedCombobox, rounded_tree; from src.ui.zebra import zebra_tree

class PrescriptionsTab(tk.Frame):
    def __init__(self, parent, app, **kw):
        # Round 22: narrow=True in the shell's left column (~370px);
        # wraps labels + shrinks trees to fit (_apply_narrow).
        self.narrow = bool(kw.pop("narrow", False))
        th = current(); super().__init__(parent, bg=th["bg"], **kw)
        self.app = app; self.lang = getattr(app, "lang", "en"); self.items = []; self.alerts = []; self.has_severe = False
        top = RoundedFrame(self, bg=th["panel"], border=th["border"]); top.pack(fill="x", padx=8, pady=6); top = top.inner
        tk.Label(top, text=t("rx.title", self.lang), bg=th["panel"],
                 fg=th["accent"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=8, pady=4)
        self.lbl_disclaimer = tk.Label(top, text=f"⚠ {DISCLAIMER_AR if self.lang == 'ar' else DISCLAIMER_EN}", bg=th["panel"],
                 fg="#D97706", font=("Segoe UI", 8), justify="left")
        self.lbl_disclaimer.pack(anchor="w", padx=8)
        self.lbl_meds = tk.Label(top, text="", bg=th["panel"], fg=th["muted"],
                                 font=("Segoe UI", 9), wraplength=900, justify="left")
        self.lbl_meds.pack(anchor="w", padx=8, pady=2)
        # Round 18 item 4: entry form (category first, then the
        # category-filtered drug, then dose/frequency/days fitting
        # at full width) lives in rx_form.py (200-line cap).
        _form.build_rx_form(self)
        self.alert_box = tk.Label(self, text="", bg=th["bg"], fg="#DC2626",
            font=("Segoe UI", 10, "bold"), wraplength=1000, justify="left")
        self.alert_box.pack(fill="x", padx=10, pady=2)
        self.ack_var = tk.BooleanVar(value=False)
        self.ack = tk.Checkbutton(self, text=t("rx.ack", self.lang),
            variable=self.ack_var, bg=th["bg"], fg="#DC2626",
            font=("Segoe UI", 9, "bold"))
        self.tree = rounded_tree(self, columns=("drug", "dose", "freq", "days", "inst"),
                                 height=6, style=tree_style("Prescriptions"), pack={"fill": "x", "padx": 8, "pady": 4})
        for c, key in [("drug", "rx.drug"), ("dose", "rx.dose"), ("freq", "rx.frequency"),
                     ("days", "rx.days"), ("inst", "rx.instructions")]:
            self.tree.heading(c, text=t(key, self.lang))
        bar = tk.Frame(self, bg=th["bg"]); bar.pack(fill="x", padx=8, pady=4)
        self.e_notes = RoundedEntry(bar, width=28); self.e_notes.insert(0, "")
        tk.Label(bar, text=t("rx.notes", self.lang), bg=th["bg"], fg=th["text"]).pack(side="left")
        self.e_notes.pack(side="left", padx=4)
        rounded_button(bar, text=t("rx.save", self.lang), bg="#059669", fg="white",
                  relief="flat", command=self.save).pack(side="left", padx=6)
        tk.Label(bar, text=t("rx.saved_note", self.lang),
                 bg=th["bg"], fg=th["muted"], font=("Segoe UI", 8)).pack(side="left")
        hist = RoundedFrame(self, bg=th["panel"], border=th["border"], title=t("rx.history", self.lang), title_fg=th["accent"]); hist.pack(fill="both", expand=True, padx=8, pady=6); hist = hist.inner
        self.tree_hist = rounded_tree(hist, columns=("id", "date", "doctor", "drugs"),
                                      height=6, style=tree_style("Prescriptions"), pack={"fill": "both", "expand": True, "padx": 4, "pady": 4})
        for c, key in [("id", "rx.col_id"), ("date", "rx.col_date"), ("doctor", "rx.col_doctor"), ("drugs", "rx.col_drugs")]:
            self.tree_hist.heading(c, text=t(key, self.lang))
        # Round 19 (item 3e): BOTH print buttons on their OWN row
        # under the history tree (the old side="right" packing
        # clipped them past the visible edge).
        prow = tk.Frame(hist, bg=th["panel"]); prow.pack(fill="x", pady=(0, 4)); self.print_btn_row = prow
        rounded_button(prow, text=t("rx.print_selected", self.lang), bg="#5E5CE6", fg="white",
                  relief="flat", command=self.print_selected).pack(side="left", padx=6, pady=4)
        self.print_direct_btn = rounded_button(prow, text=rx16_t("rx.print_direct", self.lang), bg="#5E5CE6", fg="white", relief="flat", command=lambda: print_rx_preview(self)); self.print_direct_btn.pack(side="left", padx=6, pady=4)
        if self.narrow:
            self._apply_narrow()
    def _apply_narrow(self):
        """Round 22: fit the shell's ~370px column: wrap long labels
        (anchor="w" -- center anchor clips both sides), shrink trees."""
        for lbl in (self.lbl_disclaimer, self.lbl_meds, self.alert_box):
            lbl.config(wraplength=300, anchor="w")
        self.ack.config(wraplength=300, justify="left")
        for col, w in (("drug", 102), ("dose", 46), ("freq", 68),
                       ("days", 34), ("inst", 70)):
            self.tree.column(col, width=w, minwidth=30)
        for col, w in (("id", 30), ("date", 74), ("doctor", 66), ("drugs", 166)):
            self.tree_hist.column(col, width=w, minwidth=26)
        try:
            self.e_notes.widget.config(width=13)
        except Exception:
            pass
    def open_add_drug(self):
        """Add a new drug (name + composition) - saved persistently, then
        the drug search list refreshes so the new drug can be picked."""
        open_add_drug_dialog(self, on_saved=self._refresh_drugs)

    def _refresh_drugs(self):
        items = list_by_category(self.cat_var.get())
        self.cb_drug._items = items
        self.cb_drug._all = [display(i, self.lang) for i in items]
        self.cb_drug._set_values(self.cb_drug._all)
        self.drug_var.set("")

    def _patient(self):
        return self.app.current_patient or {}
    def _meds_allergies(self):
        p = self._patient()
        return parse_list(p.get("current_medications", "")), parse_list(p.get("allergies", ""))
    def on_category(self, _e=None):
        items = list_by_category(self.cat_var.get())
        self.cb_drug._items = items
        self.cb_drug._all = [display(i, self.lang) for i in items]
        self.cb_drug._set_values(self.cb_drug._all)
        self.drug_var.set("")
    def on_drug(self, _e=None):
        self._check(generic_for(self.drug_var.get())); _form.fill_dose(self)  # R23: Dose <- stored strength
    def _check(self, generic):
        if not generic:
            return
        meds, allergies = self._meds_allergies()
        prescribed = [i["generic"] for i in self.items]
        self.alerts = check_interactions(generic, meds, allergies, prescribed)
        # R28: third dimension -- the drug vs the patient's DISEASES
        # (new drug_diseases layer), merged + re-sorted by severity;
        # a severe disease alert gates saving via the same ack path.
        self.alerts += check_drug_diseases(generic, self._patient().get("diseases", ""))
        _ord = {"severe": 0, "moderate": 1, "mild": 2}
        self.alerts.sort(key=lambda a: _ord.get(a["severity"], 9))
        self.has_severe = any(a["severity"] == "severe" for a in self.alerts)
        if not self.alerts:
            unc = is_unclassified_user_drug(generic)  # R30 3c: an unclassified user drug gets NO green all-clear -- its class-keyed checks never ran
            self.alert_box.config(text=r30_t("rx.unclassified_info", self.lang) if unc else t("rx.no_interaction", self.lang), fg="#D97706" if unc else "#059669", bg=current()["bg"])
            self.ack.pack_forget(); return
        lang = self.app.lang
        lines = []
        for a in self.alerts:
            fg, bg = SEVERITY_COLORS[a["severity"]]
            lines.append(f"[{a['severity'].upper()}] "
                         f"{a['message_ar'] if lang == 'ar' else a['message_en']}")
        self.alert_box.config(text="\n".join(lines), fg=SEVERITY_COLORS[self.alerts[0]["severity"]][0])
        if self.has_severe:
            self.ack.pack(fill="x", padx=10)
        else:
            self.ack.pack_forget()
    def add_item(self):
        generic = generic_for(self.drug_var.get())
        if not generic:
            messagebox.showerror(t("rx.error", self.lang), t("rx.select_drug", self.lang)); return
        self._check(generic)
        if self.has_severe:
            messagebox.showwarning(t("rx.severe_title", self.lang),
                t("rx.severe_msg", self.lang))
        _med = get_medication(generic)  # R24: stored brand = canonical brand_en by lookup (AR display has no "(Brand)" to parse)
        item = {"generic": generic, "brand": str(_med.get("brand_en", "") or "") if _med else "",
                "dose": self.e_dose.get().strip(), "frequency": self.freq_var.get(),
                "duration_days": self.e_dur.get().strip(),
                "instructions": self.e_inst.get().strip()}
        self.items.append(item)
        self.tree.insert("", "end", values=(generic, item["dose"], item["frequency"],
                                            item["duration_days"], item["instructions"]))
        zebra_tree(self.tree)  # R21 item 6: composed-items list stripes too
        self.drug_var.set(""); self.e_inst.delete(0, tk.END)
    def save(self):
        if not self._patient():
            messagebox.showwarning(t("rx.select_title", self.lang), t("rx.select_patient", self.lang)); return
        if not self.items:
            messagebox.showerror(t("rx.error", self.lang), t("rx.no_drugs", self.lang)); return
        if self.has_severe and not self.ack_var.get():
            messagebox.showerror(t("rx.confirm_title", self.lang),
                t("rx.confirm_msg", self.lang))
            return
        pid = save_prescription(self._patient()["file_number"], self.items,
            self.e_notes.get().strip(), self.app.current_user,
            [a for a in self.alerts])
        self.items = []; self.alerts = []; self.has_severe = False
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.ack_var.set(False); self.ack.pack_forget()
        self.alert_box.config(text="")
        self.load(self._patient()["file_number"])
        refresh_panels_after_save(self)  # round 16: saved Rx must appear in the right-side panel at once
        messagebox.showinfo(t("rx.saved_title", self.lang), t("rx.saved_msg", self.lang).format(pid=pid))
    def print_selected(self):
        # Round 25: SAME preview flow as the direct-print button
        # (rx_print.print_rx_preview, which warns when nothing is
        # selected). The old direct build saved silently and showed
        # the FULL storage path in its "Saved:" dialog -- storage
        # paths must never appear in the UI.
        print_rx_preview(self)
    def load(self, fid):
        meds, allergies = self._meds_allergies()
        self.lbl_meds.config(text=t("rx.current_meds", self.lang).format(meds=', '.join(meds) or '—', allergies=', '.join(allergies) or '—'))
        for i in self.tree_hist.get_children():
            self.tree_hist.delete(i)
        for rx in list_prescriptions(fid):
            drugs = ", ".join(i["generic"] for i in get_prescription_items(rx["id"]))
            self.tree_hist.insert("", "end", values=(rx["id"], rx["date"], rx["doctor"], drugs))
        zebra_tree(self.tree_hist)  # R21 item 6
