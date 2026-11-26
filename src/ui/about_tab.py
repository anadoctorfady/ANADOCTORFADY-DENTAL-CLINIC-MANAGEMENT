"""Dedicated About tab (Item 13, 2026-11-08). <200 lines.

A real tab in the main notebook (not a section inside Settings).
Round 52, Section F: EVERY text on this tab follows the ACTIVE
app language only -- never both languages together (owner's
request). The dedication exists per language in
src/config/settings.py (ABOUT_EN / ABOUT_AR) and only the active
one is shown; the subtitle, license block and contact line all go
through the i18n strings. ANADOCTORFADY itself is the app name,
not a language string, and stays as-is. The Telegram contact
button and number come from settings.py (TELEGRAM / TG_URL).
Round 42: a License section (title + name + one-line summary in
the app language) with a button opening the full license text in
a scrollable dialog -- the same text as the shipped LICENSE file
and the installer agreement page (that legal document is
bilingual by design and pinned verbatim; the dialog's own title
and Close button follow the app language)."""
import tkinter as tk
import webbrowser
from tkinter import scrolledtext
from src.config.theme import current, RADIUS_CARD
from src.config.strings import t
from src.config.settings import ABOUT_EN, ABOUT_AR, TELEGRAM, TG_URL, CLINIC
from src.config.license_text import LICENSE_TEXT
from src.ui.rounded import rounded_button
from src.ui.rounded_frame import RoundedFrame


def show_license_text(parent, lang="en"):
    """Scrollable dialog with the full bilingual license text
    (round 42). Returns the Toplevel. LICENSE_TEXT is identical to
    the shipped LICENSE file and installer/license_agreement.txt
    (pinned by tests/test_r42_license.py)."""
    th = current()
    win = tk.Toplevel(parent)
    win.title(t("about.license_title", lang))
    win.geometry("760x600")
    win.configure(bg=th["bg"])
    wrap = RoundedFrame(win, bg=th["panel"], border=th["border"], radius=RADIUS_CARD)
    wrap.pack(fill="both", expand=True, padx=10, pady=10)
    txt = scrolledtext.ScrolledText(wrap.inner, wrap="word", bg=th["panel"],
                                    fg=th["text"], font=("Segoe UI", 10))
    txt.pack(fill="both", expand=True)
    txt.insert("1.0", LICENSE_TEXT)
    txt.configure(state="disabled")
    rounded_button(win, text=t("about.license_close", lang), bg=th["accent"], fg="white",
                   command=win.destroy).pack(pady=(0, 10))
    return win


class AboutTab(tk.Frame):
    def __init__(self, parent, app, **kw):
        th = current()
        super().__init__(parent, bg=th["bg"], **kw)
        self.app = app
        self.lang = getattr(app, "lang", "en") or "en"
        from src.utils.logo import photo
        self._logo_img = photo(self, 120)
        if self._logo_img is not None:
            tk.Label(self, image=self._logo_img, bg=th["bg"]).pack(pady=(24, 4))
        tk.Label(self, text=CLINIC, bg=th["bg"], fg=th["accent"],
                 font=("Segoe UI", 16, "bold")).pack(pady=4)
        tk.Label(self, text=t("about.subtitle", self.lang),
                 bg=th["bg"], fg=th["text"], font=("Segoe UI", 11)).pack(pady=2)
        # R52 Section F: ONE dedication label, in the active
        # language only (was: ABOUT_EN and ABOUT_AR stacked).
        _about = ABOUT_AR if self.lang == "ar" else ABOUT_EN
        tk.Label(self, text=_about, bg=th["bg"], fg=th["text"],
                 font=("Segoe UI", 12 if self.lang == "ar" else 11),
                 wraplength=700, justify="center").pack(pady=12, padx=20)
        tk.Label(self, text=t("about.license_title", self.lang),
                 bg=th["bg"], fg=th["accent"], font=("Segoe UI", 12, "bold")).pack(pady=(16, 2))
        tk.Label(self, text=t("about.license_name", self.lang),
                 bg=th["bg"], fg=th["text"], font=("Segoe UI", 11, "bold")).pack(pady=2)
        tk.Label(self, text=t("about.license_summary", self.lang),
                 bg=th["bg"], fg=th["text"], font=("Segoe UI", 10),
                 wraplength=700, justify="center").pack(pady=2, padx=20)
        rounded_button(self, text=t("about.license_view", self.lang), bg=th["accent"], fg="white",
                       font=("Segoe UI", 10, "bold"),
                       command=lambda: show_license_text(self, self.lang)).pack(pady=4)
        tk.Label(self, text=t("about.contact", self.lang),
                 bg=th["bg"], fg=th["muted"], font=("Segoe UI", 10)).pack(pady=(16, 4))
        rounded_button(self, text=t("about.telegram_btn", self.lang).format(number=TELEGRAM), bg="#229ED9", fg="white",
                  font=("Segoe UI", 11, "bold"),
                  command=lambda: webbrowser.open(TG_URL)).pack(pady=6)
