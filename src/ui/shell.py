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
from src.models.telemetry import maybe_send_async; from src.ui import update_ui as _update_ui; from src.models.whatsapp_send import start_checker as _wa_start
from src.ui.about_tab import AboutTab; from src.ui.paper_bg import attach_paper_bg as _paper, apply_treeview_paper as _tree_paper; from src.ui.zebra import zebra_tree
from src.utils.logo import photo

def _owes(fid):
    """Round 21 item 1: True when remaining > 0 (red "debt" tag)."""
    try: return patient_totals(fid)["remaining"] > 0
    except Exception: return False

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self._lazy_tabs = {}  # R51: heavy tabs register here in _main, build on first use (lazy_tabs.py)
        self._icon_img = photo(self, 32)  # main-window icon (kept on self: Tk GC guard)
        if self._icon_img is not None: self.iconphoto(False, self._icon_img)
        init_db()
        self.lang = get_setting("language", "en") or "en"
        self.current_patient = None; self.current_user = "fady"; self.current_role = "doctor"; self._tree_select_echo = None
        th = current()
        self.title("ANADOCTORFADY DENTAL CLINIC MANAGEMENT")
        self.geometry("1380x820"); self.minsize(1200, 700)
        self.configure(bg=th["bg"]); _paper(self)  # paper texture, light mode only
        # PRIVACY: login created FIRST, then root withdrawn (a Toplevel created while the root is normal stays mapped after withdraw()).
        self._show_login(); self.withdraw()
        self.update()  # R51: paint the login BEFORE the heavy tab build below (it used to appear only after every tab was built)
        from src.ui import amiri as _amiri_note; _amiri_note.note_build_family(self)  # R56: no-op since the Amiri revert (Segoe UI both languages)
        self._topbar(); self._main(); self.load_patients(); from src.ui import amiri as _amiri; _amiri.apply_ui_fonts(self); self.after(800, self._telemetry_silent)
    def __getattr__(self, name):  # R51: a lazy tab builds on first attribute access (tests and cross-tab calls use app.fin / app.appt / ...)
        if name in (self.__dict__.get("_lazy_tabs") or {}):
            from src.ui import lazy_tabs as _lt; return _lt.build(self, name)
        raise AttributeError(name)
    def _show_login(self): LoginWindow(self, lang=self.lang, on_success=self._on_login)
    def _telemetry_silent(self):
        """Silent automatic stats (owner's decision): no dialog, no ask."""
        try: maybe_send_async(); _update_ui.maybe_check_async(self); _wa_start()  # R44 update check + R49 WA reminder checker ride the same hook
        except Exception: pass  # telemetry must never break startup
    def _on_login(self, u):
        self.current_user = u; self._logged_in = True; self.deiconify(); self.title("ANADOCTORFADY DENTAL CLINIC MANAGEMENT"); self._user_lbl.config(text=f"| {u}")
        try: from src.utils.auth import set_current_user as _s; self.current_role = _s(u)
        except Exception: pass
        if hasattr(self, "clinical"): self.clinical.current_user, self.clinical.current_role = u, self.current_role  # R24 fix: tabs are built pre-login with the default role; propagate the real one (was: admin treated as doctor by clinical edit/finance checks until a rebuild)
        if "settings" in self.__dict__: self.settings.refresh_role_sections()  # R51: only when already built -- a lazy SettingsTab built later reads the login role in its own __init__
        if "users" in self.__dict__: self.users.refresh(); self.info_panel.refresh(self.current_patient) if getattr(self, "info_panel", None) else None
        if getattr(self, "_att_btn", None): self._att_btn.pack(side="right", padx=8, pady=8) if self.current_role == "admin" else self._att_btn.pack_forget()
    def _logout(self):
        from src.models.attendance import record_for_user
        try: self.fin.relock(); record_for_user(self.current_user, "out")  # local, offline-safe
        except Exception: pass  # relock must never break logout
        # Round 17: no patient stays open across logout -- clear every clinical surface.
        self.current_patient = None
        try: self.clinical.clear(); self.appt.load(); self.info_panel.refresh(None)
        except Exception: pass
        LoginWindow(self, lang=self.lang, on_success=self._on_login)  # login first, then hide root (same Tk ordering rule as startup)
        self.withdraw()  # hide patient data again until next login
    def _open_attendance(self): from src.ui.attendance_view import open_attendance_view; open_attendance_view(self, self.current_role)
    def _topbar(self):
        th = current()
        bar = self._topbar_frame = tk.Frame(self, bg=th["header1"], height=48); bar.pack(fill="x"); bar.pack_propagate(False)
        self._logo_img = photo(bar, 40, name="logo_corner.png")  # transparent corner logo on the header bg (no black square)
        if self._logo_img is not None:
            tk.Label(bar, image=self._logo_img, bg=th["header1"]).pack(side="left", padx=(8, 0), pady=4)
        tk.Label(bar, text=" ANADOCTORFADY DENTAL CLINIC MANAGEMENT ", bg=th["header1"], fg="white",
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=10)
        self._user_lbl = tk.Label(bar, text=f"| {self.current_user}" if getattr(self, "_logged_in", False) else t("shell.user_default", self.lang), bg=th["header1"], fg="white"); self._user_lbl.pack(side="left")
        _pill_fg = th["header1"] if mode() == "light" else th["text"]  # header pills: violet on sand (light) / light on dark panel
        self.theme_btn = rounded_button(bar, text=t("shell.theme_dark", self.lang) if mode() == "light" else t("shell.theme_light", self.lang), bg=th["panel"], fg=_pill_fg, command=self._toggle_theme); self.theme_btn.pack(side="right", padx=8, pady=8)
        rounded_button(bar, text="عربي / EN", bg=th["panel"], fg=_pill_fg, command=self._toggle_lang).pack(side="right", padx=8, pady=8)
        self._att_btn = rounded_button(bar, text=t("shell.attendance", self.lang), bg=th["panel"], fg=_pill_fg, command=self._open_attendance)
        if self.current_role == "admin": self._att_btn.pack(side="right", padx=8, pady=8)
        rounded_button(bar, text=t("shell.logout", self.lang), bg=th["header2"], fg="white",
                  command=self._logout).pack(side="right", pady=8); _update_ui.attach(self)  # R44: re-show the update notice after a rebuild
        # R53: the bar must fit its tallest child -- pills need linespace+12 image height plus 16px of pady, the title its own linespace. The fixed 48px bar used to allocate the (R56-reverted) Amiri pills only 32px, and _on_resize then shrank their images under the text.
        _bh = max([c.winfo_reqheight() + (16 if c.winfo_class() == "Button" else 0) for c in bar.winfo_children()], default=0)
        bar.config(height=max(48, _bh))
    def _toggle_theme(self):
        """Switch light/dark instantly: persist, rebuild all frames."""
        set_theme_mode("dark" if mode() == "light" else "light"); self._rebuild()
    def _rebuild(self):
        from src.ui import amiri as _amiri_note; _amiri_note.note_build_family(self)  # R56: no-op since the Amiri revert (lang already flipped by _toggle_lang)
        fid = self.current_patient["file_number"] if self.current_patient else None
        for w in self.winfo_children(): w.destroy()
        self.configure(bg=current()["bg"]); _paper(self)  # re-tile paper after rebuild
        self._topbar(); self._main(); self.load_patients()
        if fid: self.select_patient(fid)
        from src.ui import amiri as _amiri; _amiri.apply_ui_fonts(self)  # R56: no-op since the Amiri revert (after every rebuild)
    def _toggle_lang(self):
        self.lang = "ar" if self.lang == "en" else "en"; set_setting("language", self.lang); self._rebuild()
        messagebox.showinfo(t("shell.lang_title", self.lang), t("shell.lang_switched", self.lang))
    def _main(self):
        th = current()
        paned = tk.PanedWindow(self, bg=th["bg"], sashwidth=6, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=6, pady=6)
        left = RoundedFrame(paned, bg=th["list_bg"], border=th["border"]); paned.add(left, width=380); left = left.inner
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except Exception: pass
        _tree_paper(style, th)  # global Treeview + paper patient list, light only
        from src.ui import shell_left as _shell_left  # R21 item 2: the far-left column is built by shell_left
        _shell_left.build_left_column(self, left)
        right = tk.Frame(paned, bg=th["bg"]); paned.add(right)
        nb = ttk.Notebook(right); nb.pack(fill="both", expand=True)
        self.notebook = nb  # round 17: no Patients tab -- the patient form lives only in the modal dialog
        self.clinical = ClinicalTab(nb, self); nb.add(self.clinical, text=t("shell.tab_clinical", self.lang))
        from src.ui import lazy_tabs as _lt  # R51: the other tabs build lazily -- placeholders keep notebook order/titles
        for _n in ("appt", "fin", "settings", "users", "about"): self.__dict__.pop(_n, None)  # drop tabs built into the previous notebook (rebuild)
        self._lazy_tabs = {}
        for _n, _c, _k, _kw in (("appt", AppointmentsTab, "shell.tab_appointments", {"defer_load": True}), ("fin", FinanceTab, "shell.tab_finances", {"defer_load": True}), ("settings", SettingsTab, "shell.tab_settings", {}), ("users", UsersTab, "shell.tab_users", {}), ("about", AboutTab, "shell.tab_about", {})):
            _lt.register(self, nb, _n, _c, t(_k, self.lang), th["bg"], **_kw)
        nb.bind("<<NotebookTabChanged>>", self._on_tab_changed); from src.ui.wheel_scroll import install_page_wheel; install_page_wheel(self)  # R52: no after_idle build chain -- lazy tabs build on first open/access only (R56: + ONE central Treeview/Listbox wheel policy -- page scroll -- for the whole app)
    def _on_tab_changed(self, _event=None):  # R24 item 4: opening Appointments reloads it (fresh attendance board)
        try:
            from src.ui import lazy_tabs as _lt; _lt.ensure_selected(self)  # R51: build a lazy tab when its page is opened
            if "appt" not in (getattr(self, "_lazy_tabs", None) or {}) and self.notebook.select() == str(self.appt): self.appt.load()  # R52: naming self.appt while it is still a lazy placeholder would BUILD it on every tab change (even the notebook's first layout) -- the pending registry, not __dict__, is the built test (attribute holders without __dict__ entries count as built)
        except Exception: pass
    def chart_teeth(self): return self.clinical.chart.get_selection()[0]
    def new_patient(self):
        """Round 17: clear the open patient everywhere, then open the new-patient form as a MODAL dialog."""
        self.current_patient = None
        try: self.clinical.clear(); self.info_panel.refresh(None)
        except Exception: pass
        self.appt.load()  # quick-book now shows "no patient"
        from src.ui.patient_dialog import open_new_patient_dialog
        dlg = open_new_patient_dialog(self)
        from src.ui import amiri as _amiri; _amiri.apply_ui_fonts(self, root=dlg)  # R56: no-op since the Amiri revert
        return dlg
    def load_patients(self):
        from src.ui.amiri import row_font as _rf  # R56: Segoe UI row tags (Amiri reverted)
        q = self.search_var.get().strip() if hasattr(self, "search_var") else ""; crit = self.adv_search.get_criteria() if getattr(self, "adv_search", None) else {}  # Round 16: search-only list; criteria = quick box + advanced panel
        cur_p = self.current_patient or {}; rows = search_patients(q=q or None, current_file=cur_p.get("file_number"), **crit)
        for i in self.tree.get_children(): self.tree.delete(i)
        palette = name_colors(mode() == "dark")
        for idx, c in enumerate(palette): self.tree.tag_configure(f"name_{idx}", foreground=c, font=_rf(self, 9, "bold"))
        self.tree.tag_configure("debt", foreground=debt_red(mode() == "dark"), font=_rf(self, 9, "bold"))  # R21 item 1: "debt" tag AFTER the palette tags (last tag wins) -> red name
        # R55 (Section C): adherence name colours, one batched query
        # for the whole list; configured after "debt" so a signal beats the palette and debt red (adherence_tags).
        from src.ui import adherence_tags as _at
        _at.configure(self.tree, _rf(self, 9, "bold")); _adh = _at.colours_for([r["file_number"] for r in rows])
        owing = debtor_files()  # R21 item 11: one grouped query, not one totals call per row
        for i, r in enumerate(rows):
            tags = [f"name_{i % len(palette)}"] + (["debt"] if r["file_number"] in owing else []) + ([f"adh_{_adh[r['file_number']]}"] if _adh.get(r["file_number"]) else [])
            self.tree.insert("", "end", values=(r["file_number"], r["full_name"], r["mobile1"] or ""), tags=tuple(tags))
        zebra_tree(self.tree)  # R21 item 6 (zebra tag first: name/debt fg keep precedence)
    def select_patient(self, fid):
        for iid in self.tree.get_children():
            if str(self.tree.item(iid, "values")[0]) == str(fid):
                self._tree_select_echo = str(fid); self.tree.selection_set(iid); self.tree.see(iid); self.on_select(); return
        r = fetch_list_row(fid)  # Round 16: search-only list may not hold this patient -- fetch the row
        if r:
            from src.ui.adherence_tags import colour_for as _adh1; _colour = _adh1(r["file_number"])
            tags = ("name_0", "debt") if _owes(r["file_number"]) else ("name_0",)
            tags = tags + ((f"adh_{_colour}",) if _colour else ())
            self.tree.insert("", "end", values=(r["file_number"], r["full_name"], r["mobile1"] or ""), tags=tags); iid = self.tree.get_children()[-1]
            zebra_tree(self.tree)  # R24 zebra audit: this insert path skipped striping
            self._tree_select_echo = str(fid); self.tree.selection_set(iid); self.tree.see(iid); self.on_select()
    def _on_tree_select(self):
        # R31: swallow the <<TreeviewSelect>> echo of select_patient()'s own selection_set (it calls on_select itself); genuine clicks load.
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
        conn.close(); self.clinical.load(fid)
        if "appt" not in (getattr(self, "_lazy_tabs", None) or {}):  # Job 8: quick-book state. R52: refresh Appointments only when built AND its page is on screen -- a hidden tab reloads when opened (_on_tab_changed), and merely naming self.appt here used to BUILD the lazy tab on every patient select.
            try:
                if self.notebook.select() == str(self.appt): self.appt.load()
            except Exception: pass  # R31: clinical.load already refreshed the info panel for this patient -- no 2nd refresh here.
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
            from src.ui.print_pdf_direct import print_pdf_direct; return print_pdf_direct(self, bilingual=True)
        # Round 16: every other Print PDF goes through the preview; nothing is saved until the user chooses.
        from src.reports.print_preview import open_patient_preview; return open_patient_preview(self)
