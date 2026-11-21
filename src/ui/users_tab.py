"""Users tab: user management (create / list / delete).
Local clinic.db first, then the sync server (POST /users) when a sync
URL is set. The tab is HIDDEN without the users.manage permission
(round 21 item 10: admin by default, or an admin-granted extra
permission from this tab's permission tree). Center is server-side
only - local rows are shown with this device's center. <200 lines."""
import tkinter as tk
from tkinter import ttk, messagebox
from src.config.theme import current; from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame; from src.ui.rounded_widgets import RoundedEntry; from src.ui.rounded_lists import RoundedCombobox, rounded_tree; from src.ui.tree_scroll import narrow_tree; from src.ui.zebra import zebra_tree
from src.config.strings import t
from src.models.database import get_setting
from src.models.permissions import (PERM_GROUPS, get_user_grants, grant_perm,
                                    revoke_perm, perm_label, clear_user_grants,
                                    has_perm)
from src.models.sync import SyncClient
from src.utils.auth import (create_user, delete_user, get_current_role,
                            get_current_user, list_users)
ROLES = ["doctor", "nurse", "admin"]
class UsersTab(tk.Frame):
    def __init__(self, parent, app, **kw):
        th = current(); super().__init__(parent, bg=th["bg"], **kw)
        self.app = app
        self.lang = getattr(app, "lang", "en") or "en"
        tk.Label(self, text=t("users.title", self.lang), bg=th["bg"], fg=th["accent"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Label(self, text=t("users.subtitle", self.lang),
                 bg=th["bg"], fg=th["muted"], justify="left").pack(anchor="w", padx=10)
        # Round 16: create form is NARROW (anchor="w", entries width 12) so the permissions tree gets the space.
        cf = RoundedFrame(self, bg=th["panel"], border=th["border"], title=t("users.create_frame", self.lang), title_fg=th["text"]); cf.pack(anchor="w", padx=10, pady=8); cf = cf.inner
        self.e_name = RoundedEntry(cf, width=12); self.e_name.grid(row=0, column=1, padx=4, pady=4)
        self.e_pw = RoundedEntry(cf, width=12, show="•"); self.e_pw.grid(row=0, column=3, padx=4, pady=4)
        self.role_var = tk.StringVar(value="doctor")
        RoundedCombobox(cf, textvariable=self.role_var, values=ROLES, width=8,
                     state="readonly").grid(row=1, column=1, padx=4, pady=4)
        self.e_center = RoundedEntry(cf, width=12)
        self.e_center.insert(0, get_setting("sync_center_id", "main") or "main")
        self.e_center.grid(row=1, column=3, padx=4, pady=4)
        self.e_admin_pw = RoundedEntry(cf, width=12, show="•")
        self.e_admin_pw.grid(row=2, column=1, padx=4, pady=4)
        for (r, c, txt) in [(0, 0, t("users.username", self.lang)), (0, 2, t("users.password", self.lang)),
                            (1, 0, t("users.role", self.lang)), (1, 2, t("users.center", self.lang)),
                            (2, 0, t("users.admin_pw", self.lang))]:
            tk.Label(cf, text=txt, bg=th["panel"], fg=th["text"]).grid(row=r, column=c, padx=6, pady=4, sticky="w")
        tk.Label(cf, text=t("users.admin_pw_note", self.lang),
                 bg=th["panel"], fg=th["muted"]).grid(row=2, column=2, columnspan=3, sticky="w", padx=6)
        rounded_button(cf, text=t("users.create_btn", self.lang), bg=th["accent"], fg="white", relief="flat",
                  command=self.create).grid(row=3, column=0, columnspan=2, pady=6, sticky="w", padx=6)
        # Round 16: list (narrow, 2-3 names + wheel) and permissions tree share one row — list docks left, tree takes the rest so it is fully visible, not clipped.
        mid = tk.Frame(self, bg=th["bg"]); mid.pack(fill="both", expand=True, padx=10, pady=8)
        lf = RoundedFrame(mid, bg=th["panel"], border=th["border"], title=t("users.list_frame", self.lang), title_fg=th["text"]); lf.pack(side="left", fill="y"); lf = lf.inner
        bf = tk.Frame(lf, bg=th["panel"]); bf.pack(side="bottom", fill="x", pady=(6, 0))
        rounded_button(bf, text=t("users.refresh", self.lang), bg=th["accent"], fg="white", relief="flat",
                  command=self._load).pack(side="left", padx=2)
        rounded_button(bf, text=t("users.delete", self.lang), bg="#EF4444", fg="white", relief="flat",
                  command=self.delete).pack(side="left", padx=6)
        self.tree = narrow_tree(lf, ("user", "role", "center"), 3, (110, 70, 80))
        self.tree.heading("user", text=t("users.col_user", self.lang)); self.tree.heading("role", text=t("users.col_role", self.lang)); self.tree.heading("center", text=t("users.col_center", self.lang))
        # Job 10: per-user extra-permission tree. Grants only ADD to
        # the role default, never remove it (permissions.has_perm).
        pf = RoundedFrame(mid, bg=th["panel"], border=th["border"], title=t("perm.title", self.lang), title_fg=th["text"]); pf.pack(side="left", fill="both", expand=True, padx=(10, 0)); pf = pf.inner
        self.perm_user_lbl = tk.Label(pf, text=t("perm.select_user", self.lang), bg=th["panel"], fg=th["muted"])
        self.perm_user_lbl.pack(anchor="w")
        self.perm_tree = rounded_tree(pf, show="tree", height=8, pack={"fill": "both", "expand": True, "pady": 4})
        self.perm_tree.bind("<Button-1>", self._on_perm_click)
        self.perm_note = tk.Label(pf, text=t("perm.subtitle", self.lang), bg=th["panel"], fg=th["muted"], wraplength=800, justify="left")
        self.perm_note.pack(anchor="w")
        self.note = tk.Label(self, text="", bg=th["bg"], fg=th["muted"], wraplength=800, justify="left")
        self.note.pack(anchor="w", padx=10, pady=4)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._load_perms())
        self._build_perm_tree()
        self.refresh()  # hides the tab at startup (role is "doctor" until login)
    def _build_perm_tree(self):
        """Group nodes (expandable) + one child per permission, marked
        ☐/☑. Tk has no native checkbox tree, so the mark is text."""
        self._perm_items = {}
        for group, perms in PERM_GROUPS:
            gid = f"g:{group}"
            self.perm_tree.insert("", "end", iid=gid, text=t(f"perm.group_{group}", self.lang), open=True)
            for key, _en, _ar in perms:
                iid = f"p:{key}"
                self._perm_items[key] = iid
                self.perm_tree.insert(gid, "end", iid=iid, text=f"☐ {perm_label(key, self.lang)}")
        # Round 16: tall enough for EVERY group + permission row, so
        # the tree is fully visible with no vertical scrolling at all.
        self.perm_tree.configure(height=len(self._perm_items) + len(PERM_GROUPS))
    def _perm_selected_user(self):
        sel = self.tree.selection()
        return self.tree.item(sel[0], "values")[0] if sel else None
    def _load_perms(self):
        """Re-mark every permission for the user selected above."""
        if not hasattr(self, "_perm_items"):
            return
        name = self._perm_selected_user()
        grants = get_user_grants(name) if name else set()
        self.perm_user_lbl.config(text=t("perm.user", self.lang).format(name=name) if name else t("perm.select_user", self.lang))
        for key, iid in self._perm_items.items():
            mark = "☑" if key in grants else "☐"
            self.perm_tree.item(iid, text=f"{mark} {perm_label(key, self.lang)}")
    def _toggle_perm(self, name, key):
        """Flip one extra grant for `name`; persists to user_grants.
        Grant EDITING stays admin-role-only in round 21 (a
        users.manage delegate manages users; only admin grants)."""
        if get_current_role() != "admin" or not name or key not in self._perm_items:
            return False
        if key in get_user_grants(name):
            revoke_perm(name, key)
        else:
            grant_perm(name, key)
        self._load_perms()
        self.perm_note.config(text=t("perm.saved", self.lang))
        return True
    def _on_perm_click(self, event):
        iid = self.perm_tree.identify_row(event.y)
        if not iid or not iid.startswith("p:"):
            return  # group row or empty space: expand/collapse only
        name = self._perm_selected_user()
        if name:
            self._toggle_perm(name, iid[2:])
    def _shown(self):
        """True if the tab is currently visible. (nb.tabs() also lists
        hidden tabs, so the tab's state is the reliable check.)"""
        try:
            return self.master.tab(self, "state") != "hidden"
        except tk.TclError:
            return False  # never added yet
    def refresh(self):
        """Show the tab + list only with users.manage (R21 item 10)."""
        nb = self.master
        if not has_perm(get_current_user(), "users.manage", get_current_role()):
            if self._shown(): nb.hide(self)
            return
        if not self._shown(): nb.add(self, text=t("users.tab", self.lang))
        self._load()
    def _load(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        center = get_setting("sync_center_id", "main") or "main"
        for u, r in list_users():
            self.tree.insert("", "end", values=(u, r, center))
        self._load_perms(); zebra_tree(self.tree)  # R21 item 6
    def _say(self, title, text, error=False):
        self.note.config(text=text, fg="#EF4444" if error else current()["muted"])
        (messagebox.showerror if error else messagebox.showinfo)(title, text)
    def _server_client(self):
        """Logged-in SyncClient, or (None, reason): no-url / no-password /
        login-failed. The admin password field is the server login."""
        url = (get_setting("sync_server_url", "") or "").strip()
        if not url: return None, "no-url"
        pw = self.e_admin_pw.get()
        if not pw: return None, "no-password"
        cl = SyncClient(url)
        ok, _ = cl.login(get_current_user(), pw)
        return (cl, None) if ok else (None, "login-failed")
    def create(self):
        if not has_perm(get_current_user(), "users.manage", get_current_role()):
            return self._say(t("users.title_users", self.lang), t("users.admin_only", self.lang), error=True)
        name = self.e_name.get().strip(); pw = self.e_pw.get()
        role = self.role_var.get() or "doctor"
        center = self.e_center.get().strip() or "main"
        ok, msg = create_user("admin", name, pw, role)
        if not ok:
            return self._say(t("users.create_title", self.lang), msg, error=True)
        self.e_pw.delete(0, tk.END); self._load()
        cl, why = self._server_client()
        if why == "no-url":
            return self._say(t("users.create_title", self.lang), t("users.created_local_nourl", self.lang).format(name=name, role=role))
        if why == "no-password":
            return self._say(t("users.create_title", self.lang), t("users.created_local_nopw", self.lang).format(name=name, role=role))
        if why == "login-failed":
            return self._say(t("users.create_title", self.lang), t("users.created_local_login", self.lang).format(name=name, role=role))
        ok_srv, err = cl.create_user(name, pw, role, center)
        if ok_srv:
            self._say(t("users.create_title", self.lang), t("users.created_both", self.lang).format(name=name, role=role))
        else:
            self._say(t("users.create_title", self.lang), t("users.created_server_failed", self.lang).format(name=name, role=role, err=err), error=True)
    def delete(self):
        if not has_perm(get_current_user(), "users.manage", get_current_role()):
            return self._say(t("users.title_users", self.lang), t("users.admin_only", self.lang), error=True)
        sel = self.tree.selection()
        if not sel:
            return self._say(t("users.title_users", self.lang), t("users.select_first", self.lang), error=True)
        name = self.tree.item(sel[0], "values")[0]
        if name == get_current_user():
            return self._say(t("users.delete_title", self.lang), t("users.cannot_self", self.lang), error=True)
        if not messagebox.askyesno(t("users.delete_title", self.lang), t("users.confirm_delete", self.lang).format(name=name)):
            return
        ok, msg = delete_user("admin", name)
        if not ok:
            return self._say(t("users.delete_title", self.lang), msg, error=True)
        clear_user_grants(name)  # a recreated same-name user starts clean
        self._load()
        cl, why = self._server_client()
        if why == "no-url":
            return self._say(t("users.delete_title", self.lang), t("users.deleted_local_nourl", self.lang).format(name=name))
        if why in ("no-password", "login-failed"):
            return self._say(t("users.delete_title", self.lang), t("users.deleted_local_server", self.lang).format(name=name, why=why))
        ok_srv, err = cl.delete_user(name)
        if ok_srv:
            self._say(t("users.delete_title", self.lang), t("users.deleted_both", self.lang).format(name=name))
        else:
            self._say(t("users.delete_title", self.lang), t("users.deleted_server_failed", self.lang).format(name=name, err=err), error=True)
