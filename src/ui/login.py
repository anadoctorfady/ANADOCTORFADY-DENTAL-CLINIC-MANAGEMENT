"""Login window — layout B: logo on top, fields BELOW it. <120 lines."""
import tkinter as tk
from tkinter import messagebox
from src.config.theme import current
from src.ui.rounded import rounded_button
from src.ui.rounded_frame import RoundedFrame
from src.ui.rounded_widgets import RoundedEntry
from src.config.strings import t
from src.utils.auth import verify, set_current_user, record_login, get_all_last_logins
from src.utils.logo import photo
class LoginWindow(tk.Toplevel):
    def __init__(self, master, lang="en", on_success=None, title_extra=""):
        super().__init__(master)
        self.lang, self.on_success = lang, on_success
        self.title(t("login.title", lang) + title_extra)
        # Widened/taller (was 380x460) to fit the per-user last-login
        # list below the sign-in button; logo and fields unchanged.
        self.geometry("400x580"); self.resizable(False, False)
        # Center on screen: transient(master) used to do this, but it
        # also hid the login with the withdrawn root (see above).
        _sx = (self.winfo_screenwidth() - 400) // 2
        _sy = max(0, (self.winfo_screenheight() - 580) // 2)
        self.geometry(f"400x580+{_sx}+{_sy}")
        # Window icon: gold tooth + crown logo (same logo as assets/app.ico).
        # iconphoto (not iconbitmap) so it works on Windows + Linux.
        self._icon_img = photo(self, 32)
        if self._icon_img is not None:
            try:
                self.iconphoto(False, self._icon_img)
            except Exception:
                pass
        th = current(); self.configure(bg=th["bg"])
        # NOT transient(master): the root is withdrawn while login shows,
        # and Tk hides a transient window together with its master — the
        # login would never appear. grab_set() alone keeps it modal.
        self.grab_set(); self.result = False
        card = RoundedFrame(self, bg=th["panel"], border=th["border"])
        card.place(relx=.5, rely=.5, anchor="center", width=360, height=540); card = card.inner
        # ANADOCTORFADY logo (transparent, name baked in) on top, large.
        # Label bg is the card color — no black square behind the logo.
        # No separate name labels: the text is inside the logo image.
        self._logo_img = photo(card, 140)
        if self._logo_img is not None:
            tk.Label(card, image=self._logo_img, bg=th["panel"]).pack(pady=(12, 4))
        frm = tk.Frame(card, bg=th["panel"]); frm.pack(pady=8, padx=16, fill="x")
        tk.Label(frm, text=t("login.username", lang),
                 bg=th["panel"], fg=th["text"]).grid(row=0, column=0, sticky="w", pady=4)
        self.e_user = RoundedEntry(frm, font=("Segoe UI", 10))
        self.e_user.grid(row=0, column=1, sticky="ew", pady=4, padx=6)
        self.e_user.insert(0, "fady")
        tk.Label(frm, text=t("login.password", lang),
                 bg=th["panel"], fg=th["text"]).grid(row=1, column=0, sticky="w", pady=4)
        self.e_pass = RoundedEntry(frm, show="•", font=("Segoe UI", 10))
        self.e_pass.grid(row=1, column=1, sticky="ew", pady=4, padx=6)
        self.e_pass.insert(0, "1234")
        frm.columnconfigure(1, weight=1)
        rounded_button(card, text=t("login.signin", lang),
                  bg=th["accent"], fg="white", relief="flat", padx=16, pady=6,
                  font=("Segoe UI", 10, "bold"), command=self.do_login).pack(pady=8)
        # Per-user last-login list for THIS device (Item D): visible
        # BEFORE login, so the current person and other people who also
        # logged in on this device all see their last login at a glance.
        tk.Frame(card, bg=th["border"], height=1).pack(fill="x", padx=16, pady=(4, 6))
        tk.Label(card, text=t("loginlist_heading", lang), bg=th["panel"],
                 fg=th["text"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16)
        # Per-user last-login list for THIS device: shows EVERY user who
        # ever logged in here, most recent first, in a scrollable list
        # (no cap — the old 6-row cap hid users on shared devices).
        self._ll_frame = tk.Frame(card, bg=th["panel"])
        self._ll_frame.pack(fill="x", padx=16, pady=(2, 8))
        self._ll_canvas = tk.Canvas(self._ll_frame, bg=th["panel"],
                                    highlightthickness=0, height=96)
        self._ll_scroll = tk.Scrollbar(self._ll_frame, orient="vertical",
                                       command=self._ll_canvas.yview)
        self._ll_canvas.configure(yscrollcommand=self._ll_scroll.set)
        self._ll_inner = tk.Frame(self._ll_canvas, bg=th["panel"])
        self._ll_canvas.create_window((0, 0), window=self._ll_inner, anchor="nw")
        self._ll_inner.bind("<Configure>", lambda e: self._ll_canvas.configure(
            scrollregion=self._ll_canvas.bbox("all")))
        for w in (self._ll_canvas, self._ll_inner):
            w.bind("<MouseWheel>", self._ll_wheel)
            w.bind("<Button-4>", self._ll_wheel)
            w.bind("<Button-5>", self._ll_wheel)
        self._ll_scroll.pack(side="right", fill="y")
        self._ll_canvas.pack(side="left", fill="both", expand=True)
        self.refresh_last_logins()
        self.bind("<Return>", lambda e: self.do_login())
        self.e_pass.focus_set()
    def _ll_wheel(self, event):
        """Scroll the last-login list (wheel over canvas, frame or rows)."""
        if getattr(event, "num", None) == 4:
            self._ll_canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self._ll_canvas.yview_scroll(1, "units")
        elif getattr(event, "delta", 0):
            self._ll_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
    def refresh_last_logins(self):
        """Rebuild the on-window list from the local DB (most recent
        first). Called at open and whenever the list must refresh; a
        fresh LoginWindow re-reads, so the next login shows new times."""
        th = current()
        for w in self._ll_inner.winfo_children():
            w.destroy()
        rows = get_all_last_logins()
        if not rows:
            tk.Label(self._ll_inner, text=t("loginlist_empty", self.lang),
                     bg=th["panel"], fg=th["muted"],
                     font=("Segoe UI", 9)).pack(anchor="w")
            return
        for username, when in rows:  # ALL users — no cap
            when = str(when).replace("T", " ")[:16]
            lbl = tk.Label(self._ll_inner, text=f"{username} — {when}",
                           bg=th["panel"], fg=th["muted"],
                           font=("Segoe UI", 9))
            lbl.pack(anchor="w")
            lbl.bind("<MouseWheel>", self._ll_wheel)
            lbl.bind("<Button-4>", self._ll_wheel)
            lbl.bind("<Button-5>", self._ll_wheel)
    def do_login(self):
        u, p = self.e_user.get().strip(), self.e_pass.get().strip()
        if verify(u, p):
            self.result = True
            # Last login on THIS device: still recorded so the
            # per-user last-login list on the login window (the ONLY
            # place this info is shown, round 17 item 2) stays correct.
            # The post-login modal popup was removed by owner request.
            record_login(u)
            set_current_user(u)
            from src.models.attendance import record_for_user
            record_for_user(u, "in")  # never raises, never blocks login
            if self.on_success:
                self.on_success(u)
            self.destroy()
        else:
            messagebox.showerror(t("login.error_title", self.lang), t("login.invalid", self.lang))
