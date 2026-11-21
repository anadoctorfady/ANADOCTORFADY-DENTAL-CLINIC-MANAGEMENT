"""Shell: topbar (iOS27 gradient), patient list, notebook. <200 lines."""
import tkinter as tk
from tkinter import ttk, messagebox
from src.config.theme import current, mode, name_colors, debt_red
from src.config.strings import t
from src.config.settings import set_theme_mode
from src.models.database import init_db, get_connection, get_setting, set_setting; from src.models.patients import search_patients, fetch_list_row
from src.models.finance import patient_totals, debtor_files
from src.ui.login import LoginWindow; from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame; from src.ui.rounded_widgets import RoundedEntry
from src.ui.users_tab import UsersTab
from src.ui.clinical import ClinicalTab
from src.ui.appointments import AppointmentsTab
from src.ui.finance import FinanceTab
from src.ui.settings_ui import SettingsTab
from src.models.telemetry import maybe_send_async
from src.ui.about_tab import AboutTab; from src.ui.paper_bg import attach_paper_bg as _paper, apply_treeview_paper as _tree_paper; from src.ui.zebra import zebra_tree
from src.utils.logo import photo

def _owes(fid):
    """Round 21 item 1: True when remaining > 0 (red "debt" tag)."""
    try:
        return patient_totals(fid)["remaining"] > 0
    except Exception:
        return False

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self._icon_img = photo(self, 32)  # main-window icon (kept on self: Tk GC guard)
        if self._icon_img is not None: self.iconphoto(False, self._icon_img)
        init_db()
        self.lang = get_setting("language", "en") or "en"
        self.current_patient = None; self.current_user = "fady"; self.current_role = "doctor"; self._tree_select_echo = None
        th = current()
        self.title("ANADOCTORFADY DENTAL CLINIC MANAGEMENT")
        self.geometry("1380x820"); self.minsize(1200, 700)
        self.configure(bg=th["bg"]); _paper(self)  # paper texture, light mode only
        # PRIVACY: login created FIRST, then root withdrawn — a Toplevel
        # created while the root is normal stays mapped after withdraw().
        self._show_login(); self.withdraw()
        self._topbar(); self._main(); self.load_patients(); self.after(800, self._telemetry_silent)
    def _show_login(self):
        LoginWindow(self, lang=self.lang, on_success=self._on_login)
    def _telemetry_silent(self):
        """Silent automatic stats (owner's decision): no dialog, no ask."""
        try:
            maybe_send_async()
        except Exception:
            pass  # telemetry must never break startup
    def _on_login(self, u):
        self.current_user = u; self._logged_in = True; self.deiconify(); self.title("ANADOCTORFADY DENTAL CLINIC MANAGEMENT"); self._user_lbl.config(text=f"| {u}")
        try: from src.utils.auth import set_current_user as _s; self.current_role = _s(u)
        except Exception: pass
        if hasattr(self, "clinical"): self.clinical.current_user, self.clinical.current_role = u, self.current_role  # R24 fix: tabs are built pre-login with the default role; propagate the real one (was: admin treated as doctor by clinical edit/finance checks until a rebuild)
        if hasattr(self, "settings"): self.settings.refresh_role_sections()
        if hasattr(self, "users"): self.users.refresh(); self.info_panel.refresh(self.current_patient) if getattr(self, "info_panel", None) else None
        if getattr(self, "_att_btn", None): self._att_btn.pack(side="right", padx=8, pady=8) if self.current_role == "admin" else self._att_btn.pack_forget()
    def _logout(self):
        from src.models.attendance import record_for_user
        try: self.fin.relock(); record_for_user(self.current_user, "out")  # local, offline-safe
        except Exception: pass  # relock must never break logout
        # Round 17: no patient stays open across logout -- clear every clinical surface.
        self.current_patient = None
        try: self.clinical.clear(); self.appt.load(); self.info_panel.refresh(None)
        except Exception: pass
        # Login first, then hide root (same Tk ordering rule as startup).
        LoginWindow(self, lang=self.lang, on_success=self._on_login)
        self.withdraw()  # hide patient data again until next login
    def _open_attendance(self):
        from src.ui.attendance_view import open_attendance_view
        open_attendance_view(self, self.current_role)
    def _topbar(self):
        th = current()
        bar = tk.Frame(self, bg=th["header1"], height=48); bar.pack(fill="x"); bar.pack_propagate(False)
        # Transparent corner logo on the header background (no black square).
        self._logo_img = photo(bar, 40, name="logo_corner.png")
        if self._logo_img is not None:
            tk.Label(bar, image=self._logo_img, bg=th["header1"]).pack(side="left", padx=(8, 0), pady=4)
        tk.Label(bar, text=" ANADOCTORFADY DENTAL CLINIC MANAGEMENT ", bg=th["header1"], fg="white",
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=10)
        self._user_lbl = tk.Label(bar, text=f"| {self.current_user}" if getattr(self, "_logged_in", False) else t("shell.user_default", self.lang), bg=th["header1"], fg="white"); self._user_lbl.pack(side="left")
        # Header pills: violet text on sand panel (light) / light text on dark panel.
        _pill_fg = th["header1"] if mode() == "light" else th["text"]
        self.theme_btn = rounded_button(bar, text=t("shell.theme_dark", self.lang) if mode() == "light" else t("shell.theme_light", self.lang), bg=th["panel"], fg=_pill_fg, command=self._toggle_theme)
        self.theme_btn.pack(side="right", padx=8, pady=8)
        rounded_button(bar, text="عربي / EN", bg=th["panel"], fg=_pill_fg, command=self._toggle_lang).pack(side="right", padx=8, pady=8)
        self._att_btn = rounded_button(bar, text=t("shell.attendance", self.lang), bg=th["panel"], fg=_pill_fg, command=self._open_attendance)
        if self.current_role == "admin": self._att_btn.pack(side="right", padx=8, pady=8)
        rounded_button(bar, text=t("shell.logout", self.lang), bg=th["header2"], fg="white",
                  command=self._logout).pack(side="right", pady=8)
    def _toggle_theme(self):
        """Switch light/dark instantly: persist, rebuild all frames."""
        set_theme_mode("dark" if mode() == "light" else "light")
        self._rebuild()
    def _rebuild(self):
        fid = self.current_patient["file_number"] if self.current_patient else None
        for w in self.winfo_children(): w.destroy()
        self.configure(bg=current()["bg"]); _paper(self)  # re-tile paper after rebuild
        self._topbar(); self._main(); self.load_patients()
        if fid: self.select_patient(fid)
    def _toggle_lang(self):
        self.lang = "ar" if self.lang == "en" else "en"
        set_setting("language", self.lang); self._rebuild()
        messagebox.showinfo(t("shell.lang_title", self.lang), t("shell.lang_switched", self.lang))
    def _main(self):
        th = current()
        paned = tk.PanedWindow(self, bg=th["bg"], sashwidth=6, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=6, pady=6)
        left = RoundedFrame(paned, bg=th["list_bg"], border=th["border"])
        paned.add(left, width=380); left = left.inner
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except Exception: pass
        _tree_paper(style, th)  # global Treeview + paper patient list, light only
        # R21 item 2: the far-left column is built by shell_left.
        from src.ui import shell_left as _shell_left
        _shell_left.build_left_column(self, left)
        right = tk.Frame(paned, bg=th["bg"]); paned.add(right)
        nb = ttk.Notebook(right); nb.pack(fill="both", expand=True)
        self.notebook = nb  # round 17: no Patients tab -- the patient form lives only in the modal dialog
        self.clinical = ClinicalTab(nb, self); nb.add(self.clinical, text=t("shell.tab_clinical", self.lang))
        self.appt = AppointmentsTab(nb, self, defer_load=True); nb.add(self.appt, text=t("shell.tab_appointments", self.lang))
        self.fin = FinanceTab(nb, self, defer_load=True); nb.add(self.fin, text=t("shell.tab_finances", self.lang))
        self.settings = SettingsTab(nb, self); nb.add(self.settings, text=t("shell.tab_settings", self.lang)); self.users = UsersTab(nb, self); nb.add(self.users, text=t("shell.tab_users", self.lang)); self.users.refresh()
        self.about = AboutTab(nb, self); nb.add(self.about, text=t("shell.tab_about", self.lang)); nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)
    def _on_tab_changed(self, _event=None):
        # R24 item 4: opening Appointments reloads it (fresh attendance board).
        try:
            if self.notebook.select() == str(self.appt): self.appt.load()
        except Exception: pass
    def chart_teeth(self): return self.clinical.chart.get_selection()[0]
    def new_patient(self):
        """Round 17: clear the open patient everywhere, then open the
        new-patient entry form as a MODAL dialog over the current view."""
        self.current_patient = None
        try: self.clinical.clear(); self.info_panel.refresh(None)
        except Exception: pass
        self.appt.load()  # quick-book now shows "no patient"
        from src.ui.patient_dialog import open_new_patient_dialog
        return open_new_patient_dialog(self)
    def load_patients(self):
        # Round 16: search-only list; criteria = quick box + advanced panel.
        q = self.search_var.get().strip() if hasattr(self, "search_var") else ""; crit = self.adv_search.get_criteria() if getattr(self, "adv_search", None) else {}
        cur_p = self.current_patient or {}; rows = search_patients(q=q or None, current_file=cur_p.get("file_number"), **crit)
        for i in self.tree.get_children(): self.tree.delete(i)
        palette = name_colors(mode() == "dark")
        for idx, c in enumerate(palette): self.tree.tag_configure(f"name_{idx}", foreground=c, font=("Segoe UI", 9, "bold"))
        # R21 item 1: remaining > 0 -> "debt" tag AFTER the palette tag (last tag wins) -> red name.
        self.tree.tag_configure("debt", foreground=debt_red(mode() == "dark"), font=("Segoe UI", 9, "bold"))
        owing = debtor_files()  # R21 item 11: one grouped query, not one totals call per row
        for i, r in enumerate(rows):
            tags = [f"name_{i % len(palette)}"] + (["debt"] if r["file_number"] in owing else [])
            self.tree.insert("", "end", values=(r["file_number"], r["full_name"], r["mobile1"] or ""), tags=tuple(tags))
        zebra_tree(self.tree)  # R21 item 6 (zebra tag first: name/debt fg keep precedence)
    def select_patient(self, fid):
        for iid in self.tree.get_children():
            if str(self.tree.item(iid, "values")[0]) == str(fid):
                self._tree_select_echo = str(fid); self.tree.selection_set(iid); self.tree.see(iid); self.on_select(); return
        # Round 16: search-only list may not hold this patient -- fetch the row.
        r = fetch_list_row(fid)
        if r:
            tags = ("name_0", "debt") if _owes(r["file_number"]) else ("name_0",)
            self.tree.insert("", "end", values=(r["file_number"], r["full_name"], r["mobile1"] or ""), tags=tags); iid = self.tree.get_children()[-1]
            zebra_tree(self.tree)  # R24 zebra audit: this insert path skipped striping
            self._tree_select_echo = str(fid); self.tree.selection_set(iid); self.tree.see(iid); self.on_select()
    def _on_tree_select(self):
        # R31: select_patient() arms _tree_select_echo, then calls on_select()
        # itself; the <<TreeviewSelect>> queued by its selection_set() is an
        # echo for the SAME row -- swallow it so a rebuild does not load the
        # patient twice. A genuine click (no echo / another row) always loads.
        echo = getattr(self, "_tree_select_echo", None); self._tree_select_echo = None
        if echo is not None and self.tree.selection() and str(self.tree.item(self.tree.selection()[0], "values")[0]) == echo: return
        self.on_select()
    def on_select(self):
        if not self.tree.selection(): return
        sel = self.tree.selection(); fid = self.tree.item(sel[0], "values")[0]
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT * FROM patients WHERE file_number=?", (fid,))
        row = cur.fetchone()
        if not row:
            conn.close(); return
        self.current_patient = dict(row)
        conn.close(); self.clinical.load(fid); self.appt.load()  # Job 8: quick-book state. R31: clinical.load already refreshed the info panel for this patient -- no 2nd refresh here.

    def refresh_clinical(self):
        if self.current_patient: self.clinical.load(self.current_patient["file_number"])
        self.fin.load(); self.fin.calc()
        try: self.appt.load()  # R24: a just-saved session flips attendance
        except Exception: pass
    def print_pdf(self, bilingual=None):
        if not self.current_patient:
            messagebox.showwarning(t("shell.pdf_select_title", self.lang), t("shell.pdf_select_first", self.lang)); return
        if bilingual is True:
            # Settings "Bilingual PDF": the one direct path left (no preview).
            from src.ui.print_pdf_direct import print_pdf_direct
            return print_pdf_direct(self, bilingual=True)
        # Round 16: every other Print PDF goes through the preview;
        # nothing is saved until the user chooses.
        from src.reports.print_preview import open_patient_preview
        open_patient_preview(self)
