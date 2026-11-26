"""Settings: reports dir, cloud, change login, backup. <200 lines.
Scrollable (Canvas + scrollbar, Item 12) so every section — including
Change Password at the bottom — is reachable. Statistics have NO UI
here (Item 10): silent/automatic only. Backup/Restore accept .bak.
Round 21 (item 10): the ADMIN sections (sync/server, storage/clinic
name, backup/restore, default currency, rename user) require the
settings.manage permission (admin by default, or admin-granted);
personal sections (theme, own password) stay available to all."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from src.config.theme import current, mode, RADIUS_FIELD
from src.config.strings import t
from src.config.settings import REPORTS, BACKUPS, get_theme_mode, set_theme_mode, get_default_currency, set_default_currency
from src.models.currency import LABELS
from src.utils.currencies import (list_currencies, display as cur_display,
    display_for_code, code_for)
from src.ui.currency_picker import CurrencyPicker  # R25 item 5: searchable popup picker (was SearchableCombobox, whose typed filter never opened)
from src.models.database import get_setting, set_setting
from src.models.backup_validate import restore_backup_safe, export_backup
from src.ui.settings_sync_guide import open_linking_guide; from src.ui.settings_storage_ui import attach_storage_section
from src.ui.settings_account import change_password, rename_user_ui
from src.utils.auth import get_current_role, get_current_user; from src.ui import settings_sections as _sections
from src.ui.login import LoginWindow
from src.ui.sync_now_ui import attach_sync_button
from src.ui.rounded import rounded_button
from src.ui.rounded_frame import RoundedFrame
from src.ui.rounded_widgets import RoundedEntry; from src.ui.rounded_lists import RoundedCombobox
from src.ui.wheel_scroll import bind_canvas_wheel
class SettingsTab(tk.Frame):
    def __init__(self, parent, app, **kw):
        th = current(); super().__init__(parent, bg=th["bg"], **kw)
        self.app = app
        self.lang = getattr(app, "lang", "en") or "en"
        # Scrollable wrapper: canvas + scrollbar + inner frame (without
        # it the bottom sections fell below the window, unreachable).
        self._canvas = tk.Canvas(self, bg=th["bg"], highlightthickness=0)
        _sb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=_sb.set)
        _sb.pack(side="right", fill="y"); self._canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(self._canvas, bg=th["bg"])
        self._win_id = self._canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfigure(self._win_id, width=e.width))
        # Scoped wheel (round 14): bind_canvas_wheel scopes it here --
        # the old unscoped bind_all stole the wheel app-wide.
        bind_canvas_wheel(self._canvas)
        self.body = body
        self._frm_wrap = RoundedFrame(body, bg=th["panel"], border=th["border"]); self._frm_wrap.pack(fill="x", padx=10, pady=8); frm = self._frm_wrap.inner
        tk.Label(frm, text=t("settings.title", self.lang), bg=th["panel"], fg=th["accent"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=6)
        tk.Label(frm, text=t("settings.reports_folder", self.lang).format(path=REPORTS), bg=th["panel"], fg=th["text"]).pack(anchor="w", padx=10)
        # Dark Mode + Default currency (doctor's choice, any country)
        pref = tk.Frame(frm, bg=th["panel"]); pref.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(pref, text=t("settings.theme", self.lang), bg=th["panel"], fg=th["text"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)
        # Explicit master (self) on the vars below: a bare StringVar
        # binds to the process default root, which can be a different
        # or destroyed interpreter in a multi-root process.
        self.theme_var = tk.StringVar(self, value=get_theme_mode())
        self._theme_combo = RoundedCombobox(pref, textvariable=self.theme_var, values=["light", "dark"], width=8, state="readonly"); self._theme_combo.pack(side="left", padx=4)
        self._cur_label = tk.Label(pref, text=t("settings.default_currency", self.lang), bg=th["panel"], fg=th["text"], font=("Segoe UI", 9, "bold")); self._cur_label.pack(side="left", padx=8)
        self.cur_var = tk.StringVar(self, value=display_for_code(get_default_currency(), self.lang))
        _cur_wrap = RoundedFrame(pref, bg=th["panel"], border=th["border"], radius=RADIUS_FIELD, pad=2); self.cb_cur = CurrencyPicker(_cur_wrap.inner, items=list_currencies(), display_fn=lambda it: cur_display(it, self.lang), textvariable=self.cur_var, width=22, lang=self.lang); self.cb_cur.pack(fill="both", expand=True); _cur_wrap.pack(side="left", padx=4); self._cur_wrap = _cur_wrap
        # Apply button on its own row (one row clipped it, shot 13).
        pref2 = tk.Frame(frm, bg=th["panel"]); pref2.pack(fill="x", padx=10, pady=(2, 6)); self._pref2 = pref2
        self._cur_hint = tk.Label(pref2, text=t("settings.base_hint", self.lang), bg=th["panel"], fg=th["muted"]); self._cur_hint.pack(side="left", padx=4)
        self.apply_btn = rounded_button(pref2, text=t("settings.apply", self.lang), bg=th["accent"], fg="white", relief="flat", command=self.apply_prefs)
        self.apply_btn.pack(side="left", padx=8)
        # Multi-device sync (Phase 4): server URL + center id.
        self._sync_wrap = RoundedFrame(body, bg=th["panel"], border=th["border"], title=t("settings.sync_frame", self.lang), title_fg=th["text"]); self._sync_wrap.pack(fill="x", padx=10, pady=8); sync = self._sync_wrap.inner
        tk.Label(sync, text=t("settings.sync_url", self.lang), bg=th["panel"], fg=th["text"]).pack(anchor="w")
        self.sync_url_var = tk.StringVar(self, value=get_setting("sync_server_url", "") or "")
        RoundedEntry(sync, textvariable=self.sync_url_var, width=60).pack(anchor="w", padx=4, pady=2)
        tk.Label(sync, text=t("settings.center_id", self.lang), bg=th["panel"], fg=th["text"]).pack(anchor="w")
        self.sync_center_var = tk.StringVar(self, value=get_setting("sync_center_id", "main") or "main")
        RoundedEntry(sync, textvariable=self.sync_center_var, width=20).pack(anchor="w", padx=4, pady=2)
        tk.Label(sync, text=t("settings.sync_empty", self.lang),
                 bg=th["panel"], fg=th["muted"]).pack(anchor="w")
        rounded_button(sync, text=t("settings.save_sync", self.lang), bg=th["accent"], fg="white", relief="flat",
                  command=self.save_sync).pack(anchor="w", pady=4)
        attach_sync_button(sync, self); attach_storage_section(body, self); from src.ui.settings_whatsapp import build_whatsapp_frame; build_whatsapp_frame(body, self)  # R16 storage + R49 B WhatsApp frame, packed after sync
        rounded_button(sync, text=t("settings.guide_btn", self.lang), bg="#5E5CE6", fg="white", relief="flat",
                  command=lambda: open_linking_guide(self)).pack(anchor="w", pady=4)
        # Templates (round 31): the doctor CHOOSES the template language
        # (app | العربية | English), persisted as template_lang
        # (app|ar|en); pickers read it at open time, no restart needed.
        self._tf_wrap = RoundedFrame(body, bg=th["panel"], border=th["border"], title=t("tpl_settings_frame", self.lang), title_fg=th["text"]); self._tf_wrap.pack(fill="x", padx=10, pady=8); tf = self._tf_wrap.inner
        self._tpl_map = {"app": t("tpl_lang_auto", self.lang), "en": "English", "ar": "العربية"}
        self._tpl_rev = {v: k for k, v in self._tpl_map.items()}
        tk.Label(tf, text=t("tpl_settings_lang", self.lang), bg=th["panel"], fg=th["text"]).pack(side="left")
        _tpl_mode = get_setting("template_lang", "app") or "app"
        self.tpl_lang_var = tk.StringVar(self, value=self._tpl_map.get(_tpl_mode if _tpl_mode in ("ar", "en") else "app"))
        self._tpl_cb = RoundedCombobox(tf, textvariable=self.tpl_lang_var, values=list(self._tpl_map.values()),
                     width=22, state="readonly"); self._tpl_cb.pack(side="left", padx=4)
        self._tpl_cb.combo.bind("<<ComboboxSelected>>", lambda _e: self.save_tpl_lang(silent=True))
        rounded_button(tf, text=t("tpl_settings_save", self.lang), relief="flat", command=self.save_tpl_lang).pack(side="left", padx=4)
        # Two rows of two: one row of four clipped the 4th button (13ar).
        brow1 = tk.Frame(frm, bg=th["panel"]); brow1.pack(fill="x", padx=10, pady=(8, 0)); self._brow1 = brow1
        brow2 = tk.Frame(frm, bg=th["panel"]); brow2.pack(fill="x", padx=10, pady=(0, 8))
        rounded_button(brow1, text=t("settings.backup", self.lang), bg=th["accent"], fg="white", relief="flat", command=self.do_backup).pack(side="left", padx=(0, 4))
        rounded_button(brow1, text=t("settings.restore", self.lang), bg=th["muted"], fg="white", relief="flat", command=self.do_restore).pack(side="left", padx=4)
        rounded_button(brow2, text=t("settings.print_pdf", self.lang), bg="#5E5CE6", fg="white", relief="flat", command=lambda: app.print_pdf()).pack(side="left", padx=(0, 4))
        rounded_button(brow2, text=t("settings.bilingual_pdf", self.lang), bg=th["accent"], fg="white", relief="flat", command=lambda: app.print_pdf(bilingual=True)).pack(side="left", padx=4)
        # Username rule (owner): a username cannot be changed except by
        # the admin. Built by refresh_role_sections() (rebuilt after
        # login; at startup the role is still the default "doctor").
        self._rn_wrap = RoundedFrame(body, bg=th["panel"], border=th["border"], title=t("settings.rename_frame", self.lang), title_fg=th["text"])
        self._rn_wrap.pack(fill="x", padx=10, pady=8)
        self.rn = self._rn_wrap.inner  # rebuild in refresh_role_sections() destroys only .inner children, the rounded shell survives
        self.rn_old = self.rn_new = self.rn_pw = None
        self.refresh_role_sections()
        # Change Password (self only - policy: nobody changes another user's
        # password except the admin, and only via the server API).
        pf = RoundedFrame(body, bg=th["panel"], border=th["border"], title=t("settings.pw_frame", self.lang), title_fg=th["text"]); pf.pack(fill="x", padx=10, pady=8); pf = pf.inner
        self.pw_old = RoundedEntry(pf, width=14, show="•"); self.pw_old.grid(row=0, column=1, padx=4)
        self.pw_new = RoundedEntry(pf, width=14, show="•"); self.pw_new.grid(row=0, column=3, padx=4)
        self.pw_conf = RoundedEntry(pf, width=14, show="•"); self.pw_conf.grid(row=1, column=1, padx=4)
        for (r, c, txt) in [(0, 0, t("settings.pw_old", self.lang)), (0, 2, t("settings.pw_new", self.lang)), (1, 0, t("settings.pw_confirm", self.lang))]:
            tk.Label(pf, text=txt, bg=th["panel"], fg=th["text"]).grid(row=r, column=c, padx=6, pady=4)
        tk.Label(pf, text=t("settings.pw_note", self.lang),
                 bg=th["panel"], fg=th["muted"]).grid(row=2, column=0, columnspan=5, sticky="w", padx=6, pady=(2, 0))
        rounded_button(pf, text=t("settings.pw_change", self.lang), bg=th["accent"], fg="white", relief="flat",
                  command=lambda: change_password(self)).grid(row=0, column=4, rowspan=2, padx=8, sticky="ns")
        # About lives in its own tab now (Item 13) - one short line here.
        tk.Label(body, text=t("settings.about_line", self.lang),
                 bg=th["bg"], fg=th["muted"], wraplength=800, justify="left").pack(fill="x", padx=10, pady=8)
    def refresh_role_sections(self):
        """Rebuild the Rename User section + toggle the admin sections
        for the CURRENT user (round 21 item 10: gated by the
        settings.manage permission, not the raw role; the gating
        helpers live in settings_sections.py). Called at build time
        and after every login (App._on_login): the tab is built
        before login, when the role is still the default "doctor".
        Without the permission the admin sections are hidden and
        the rename refs are cleared to None; a settings.manage
        delegate who is not admin sees the note only -- renaming
        itself stays root-only (owner's username rule, enforced
        again in the model)."""
        can = _sections.can_settings_admin()
        _sections.toggle_admin_sections(self, can)
        for w in self.rn.winfo_children():
            w.destroy()
        th = current()
        tk.Label(self.rn, text=t("settings.rename_note_all", self.lang),
                 bg=th["panel"], fg=th["muted"], wraplength=800, justify="right").grid(row=0, column=0, columnspan=5, sticky="w", padx=6)
        if not can or get_current_role() != "admin":
            self.rn_old = self.rn_new = self.rn_pw = None
            if can:
                tk.Label(self.rn, text=t("settings.rename_admin_only", self.lang),
                         bg=th["panel"], fg="#EF4444").grid(row=1, column=0, columnspan=5, sticky="w", padx=6)
            return
        self.rn_old = RoundedEntry(self.rn, width=14); self.rn_old.grid(row=1, column=1, padx=4)
        self.rn_new = RoundedEntry(self.rn, width=14); self.rn_new.grid(row=1, column=3, padx=4)
        self.rn_pw = RoundedEntry(self.rn, width=14, show="•"); self.rn_pw.grid(row=2, column=1, padx=4)
        for (r, c, txt) in [(1, 0, t("settings.rename_old", self.lang)), (1, 2, t("settings.rename_new", self.lang)), (2, 0, t("settings.rename_pw", self.lang))]:
            tk.Label(self.rn, text=txt, bg=th["panel"], fg=th["text"]).grid(row=r, column=c, padx=6, pady=4)
        tk.Label(self.rn, text=t("settings.rename_hint", self.lang),
                 bg=th["panel"], fg=th["muted"]).grid(row=2, column=3, padx=6)
        # Rename button on its own row: the 5-column grid (labels +
        # entries + button) is wider than the pane in Arabic and the
        # button was clipped at the right edge (shot 13ar, +111px).
        rounded_button(self.rn, text=t("settings.rename_btn", self.lang), bg="#EF4444", fg="white", relief="flat",
                  command=lambda: rename_user_ui(self)).grid(row=3, column=0, columnspan=2, padx=6, pady=(4, 2), sticky="w")
    def save_sync(self):
        set_setting("sync_server_url", self.sync_url_var.get().strip())
        set_setting("sync_center_id", self.sync_center_var.get().strip() or "main")
        messagebox.showinfo(t("settings.saved_title", self.lang), t("settings.sync_saved", self.lang))
    def save_tpl_lang(self, silent=False):
        set_setting("template_lang", self._tpl_rev.get(self.tpl_lang_var.get(), "app"))
        if not silent: messagebox.showinfo(t("settings.saved_title", self.lang), t("tpl_settings_saved", self.lang))
    def apply_prefs(self):
        set_theme_mode(self.theme_var.get())
        _code = code_for(self.cur_var.get())
        # R21 item 10: the default currency is a settings-admin
        # choice; the theme (personal) always applies.
        if _sections.can_settings_admin():
            set_default_currency(_code)
        messagebox.showinfo(t("settings.saved_title", self.lang), t("settings.theme_saved", self.lang).format(theme=self.theme_var.get(), code=_code, label=LABELS.get(_code)))
        if hasattr(self.app, "_rebuild"):
            self.app._rebuild()
    def do_backup(self):
        dest = filedialog.asksaveasfilename(initialdir=str(BACKUPS), defaultextension=".bak",
            filetypes=[(t("settings.ft_backup", self.lang), "*.bak"), (t("settings.ft_db", self.lang), "*.db")])
        if not dest:
            return
        try:
            out = export_backup(dest); messagebox.showinfo(t("settings.backup_title", self.lang), t("settings.backup_created", self.lang).format(path=out))
        except Exception as e:
            messagebox.showerror(t("settings.err_title", self.lang), str(e))
    def do_restore(self):
        def go(_u):
            f = filedialog.askopenfilename(initialdir=str(BACKUPS),
                filetypes=[(t("settings.ft_backup_short", self.lang), "*.bak *.db"), (t("settings.ft_dump", self.lang), "*.sql"), (t("settings.ft_all", self.lang), "*.*")])
            if not f:
                return
            ok, msg, auto = restore_backup_safe(f, lang=self.lang)
            if not ok:
                return messagebox.showerror(t("settings.restore_refused", self.lang), msg)
            messagebox.showinfo(t("settings.restore_title", self.lang), msg + ("\n" + t("settings.restore_prev", self.lang).format(path=auto) if auto else ""))
            if hasattr(self.app, "_rebuild"):
                self.app._rebuild()  # show the restored data, no restart needed
        LoginWindow(self, lang=self.app.lang, on_success=go, title_extra=" - Restore Auth")
