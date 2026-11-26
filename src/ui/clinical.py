"""Clinical tab (Item 5 redesign, 2026-11-08). <200 lines.

Round 22 (owner redesign): the tab opens with a PINNED HEADER
(patient_info.PatientInfoPanel: personal info + Health lines +
both alert strips) packed OUTSIDE the scroll canvas, so it
stays visible while the main area scrolls (R54: the Edit /
Delete / Refer buttons moved to the top bar, by Manage
templates; the header itself is a narrow card).
The scroll flow below it, in order: dental chart, the UNIFIED
clinical table (round 24, clinical_session.build_unified: entry
area + session record rows with Edit / Delete -- replacing the
separate input tables, History + Diagnosis/Procedures trees and
the Therapeutic Procedures panel), the Add-image row, and the
finance-history / xray / scans notebook + referrals. (Round 40:
the old separate finance section is gone — its money strip lives
inside the unified entry; ONE payment place.) The
Prescriptions section is built into the SHELL's far-left column
(app.rx_host: compose + history + Print under the patient list);
standalone construction without a shell host keeps it at the end
of the scroll flow instead. The shell passes app.info_panel =
this header so every shell refresh keeps working. Round 21: the
"(Optional)" patient-notes section is REMOVED (the templated
visit Notes is the only notes surface). Round 17: load() resets
chart + drafts."""
import tkinter as tk
from tkinter import messagebox
from src.config.strings import t
from src.config.theme import current
from src.ui import clinical_tables as _tables; from src.ui import clinical_panels as _panels
from src.ui import clinical_session as _session
from src.ui import clinical_finance_actions as _fina
from src.ui import clinical_lists as _lists; from src.ui import clinical_left as _left
from src.ui import clinical_image as _image
from src.ui import chart_status as _chart_status
from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame
from src.ui.dental_chart import DentalChartFrame
from src.ui.patient_info import PatientInfoPanel
from src.ui.template_manager import open_template_manager
from src.ui.paper_bg import attach_paper_bg; from src.ui.panel_paper import attach_panel_paper
from src.ui.prescriptions import PrescriptionsTab
from src.ui.clipboard_picker import CLIPBOARD_BINDING, bind_clipboard_picker, open_clipboard_picker, paste_items_into
from src.models.database import get_connection

# Round 21: the scrollable-wrapper helper moved to clinical_left
# (scrollable_frame) to keep this file in budget.
_scrollable = _left.scrollable_frame

class ClinicalTab(tk.Frame):
    def __init__(self, parent, app, current_user=None, current_role=None, **kw):
        th = current(); super().__init__(parent, bg=th["bg"], **kw)
        self.app = app
        self.lang = getattr(app, "lang", "en")
        self.current_user = current_user or getattr(app, "current_user", None) or "fady"
        self.current_role = current_role or getattr(app, "current_role", None) or "admin"
        self.patient_id = None
        self.clipboard_fields = {}  # name -> Text/Entry with Ctrl+Shift+V
        self.scans_frame = None
        bar = tk.Frame(self, bg=th["bg"]); bar.pack(fill="x", padx=8, pady=(6, 2)); attach_paper_bg(bar)
        tk.Label(bar, text=t("clinical.title", self.lang), bg=th["bg"], fg=th["accent"], font=("Segoe UI", 11, "bold")).pack(side="left", padx=4)
        rounded_button(bar, text=t("clinical.manage_templates", self.lang), bg=th["card"], fg=th["text"], padx=16, command=lambda: open_template_manager(self, self.current_user)).pack(side="right", padx=(4, 16))
        # Round 22: PINNED header -- patient info + Health + alert
        # strips + Edit/Delete/Refer, packed BEFORE the scroll
        # canvas so it never scrolls away. Registered as
        # app.info_panel: the shell's refresh calls (select /
        # logout / new patient / login) keep landing here.
        self.header_panel = PatientInfoPanel(self, app, action_host=bar)
        # R55: the 3-row strip spans the FULL main area (fill="x") -- the round-54 narrow card is gone; the chart moves up.
        self.header_panel.pack(fill="x", padx=8, pady=(2, 4))
        app.info_panel = self.header_panel
        self.mid_paned = None; self.left_col = None; self.right_col = self
        inner = _scrollable(self); attach_paper_bg(inner)
        self.right_inner = inner
        self.main_canvas = inner.master
        # Scroll flow: chart first (it scrolls away; the header does not).
        self.chart = DentalChartFrame(inner, lang=getattr(app, "lang", "en"), on_select=self._on_chart_select); self.chart.pack(fill="x", padx=8, pady=2)
        self.chart.on_jaw_clear = lambda teeth: _chart_status.remove_teeth_from_fields(self, teeth)  # R43: jaw toggle-off scrubs the fields
        # Round 24: ONE unified clinical table after the chart
        # (entry area + session records; sets self.input_block).
        _session.build_unified(self, inner)
        # Round 40: no separate finance section — the money strip
        # (currency/doctor/note/invoice/balance) lives INSIDE the
        # unified entry (clinical_money_strip); one payment place.
        _left.build_add_image(self, inner)
        _lists.build_notebook(self, inner)
        # Prescriptions: into the shell's left column when the shell
        # provided a host (app.rx_host); standalone builds keep the
        # section at the end of the scroll flow.
        rx_host = getattr(app, "rx_host", None)
        if rx_host is not None:
            self.rx_section = PrescriptionsTab(rx_host, self.app, narrow=True); self.rx_section.pack(fill="x")
        else:
            self.rx_section = PrescriptionsTab(inner, self.app); self.rx_section.pack(fill="x", pady=4)
        self.rx = self.rx_section  # compat alias
        self.bind_all(CLIPBOARD_BINDING, lambda _e: self.show_clips())

    def open_add_image(self): _image.open_add_image(self)

    def _refresh_patient_panel(self):
        """Refresh the main-flow panels and the PINNED HEADER
        (app.info_panel -- this tab's own header since round 22;
        the shell's refresh calls land on the same object) so its
        info + alert strips stay fresh when this tab reloads."""
        _panels.refresh_panels(self)
        panel = getattr(self.app, "info_panel", None)
        if panel is not None:
            panel.refresh(getattr(self.app, "current_patient", None))

    def _on_chart_select(self, teeth, _typ):
        _w = getattr(self, "e_sess_tooth", None)  # R24: entry tooth follows the chart (R38: the payment entry has no tooth box)
        _w = getattr(self, "e_sess_tooth", None)  # R24: entry tooth follows the chart
        if _w is not None and str(_w.cget("state")) != "disabled":
            _w.delete(0, tk.END); _w.insert(0, ",".join(teeth))
        _chart_status.insert_selected_teeth(self, teeth)  # round 17: into ALL four fields

    def _need(self):
        if not self.app.current_patient:
            messagebox.showwarning(t("clinical.select_title", self.lang), t("clinical.select_patient", self.lang)); return False
        return True

    def show_clips(self): open_clipboard_picker(self, self._paste_clips)

    def _paste_clips(self, items):
        try:
            focused = self.winfo_toplevel().focus_get()
        except Exception:
            focused = None
        if not paste_items_into(focused, items):
            paste_items_into(getattr(self, "txt_complaint", None), items)

    def show_clipboard_picker(self, on_paste=None): open_clipboard_picker(self, on_paste or self._paste_clips)

    def add(self, kind): _tables.add(self, kind)

    def add_xray(self): _lists.add_xray(self)

    def calc(self, _e=None): _fina.calc(self)

    def cur_code(self): return _fina.cur_code(self)

    def _rate_label(self): _fina.rate_label(self)

    def _clear_drafts(self):
        """Drop unsaved drafts: the 4 entry fields + their notes + Rx items."""
        # Round 24: a patient switch abandons any session edit in progress.
        if getattr(self, "_editing_session", None) is not None:
            self._editing_session = None
            try:
                from src.ui.clinical_session_edit import set_editing_ui as _su; _su(self, None)
            except Exception:
                pass
        for attr in ("txt_complaint", "txt_sym", "txt_diagnosis", "txt_procedure"):
            for suf in ("", "_note"):
                w = getattr(self, attr + suf, None)
                if w is not None: w.delete("1.0", tk.END)
        rx = getattr(self, "rx_section", None)
        if rx is not None:
            rx.items, rx.alerts, rx.has_severe = [], [], False
            for i in rx.tree.get_children(): rx.tree.delete(i)
            rx.alert_box.config(text=""); rx.e_notes.delete(0, tk.END)

    def clear(self):
        """Round 17: reset EVERY surface to the no-patient state (draft
        fields, chart selection + treated markers, right panels, finance
        row, history, scans, notes, Rx). Called when the current patient
        is cleared (new-patient dialog opens, logout)."""
        self._clear_drafts()
        _lists.load(self, None)  # history trees + scans + notes; patient_id=None
        try: self.rx_section.load(None)
        except Exception: pass
        _note = getattr(self, "e_pay_note", None)
        if _note is not None: _note.delete(0, tk.END)
        try:  # R24: unified entry money + date reset too
            from src.ui.clinical_session_entry import clear_entry as _ce; _ce(self)
        except Exception:
            pass
        try: self.calc()
        except Exception: pass
        self.chart.set_selection([], self.chart.tooth_type.get()); self.chart.set_treated([])
        self._refresh_patient_panel(); _panels.refresh_panels(self, force=True)

    def load(self, fid):
        if self.patient_id is not None and self.patient_id != fid:
            self._clear_drafts()  # round 17: a previous patient's drafts never carry over
        _lists.load(self, fid)
        _fina.load_costs(self, fid)  # this patient's real totals (not 0)
        self.rx_section.load(fid)
        self._refresh_patient_panel()
        _panels.refresh_panels(self, force=True)  # procedures may have changed
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("SELECT tooth_number, tooth_type FROM teeth_records WHERE patient_file=?", (fid,))
            tr = cur.fetchall(); conn.close()
            # Round 17 fix: ALWAYS set the selection (empty when this
            # patient has no rows) -- the old `if tr:` left the previous
            # patient's selection on the chart.
            teeth = [r["tooth_number"] for r in tr]
            self.chart.set_selection(teeth, tr[0]["tooth_type"] if tr else self.chart.tooth_type.get())
        except Exception:
            pass
        _chart_status.refresh_chart_status(self)  # round 16: treated markers
