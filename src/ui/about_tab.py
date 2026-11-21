"""Dedicated About tab (Item 13, 2026-11-08). <200 lines.

A real tab in the main notebook (not a section inside Settings):
bilingual About text - free app, ongoing charity (sadaqah) for Doctor
Fady Abdulkafy Dadoush, his parents, wife and children - plus the
WhatsApp-only contact line and button. Text is reused from
src/config/settings.py (ABOUT_EN / ABOUT_AR / WHATSAPP / WA_URL)."""
import tkinter as tk
import webbrowser
from src.config.theme import current
from src.config.strings import t
from src.config.settings import ABOUT_EN, ABOUT_AR, WHATSAPP, WA_URL, CLINIC
from src.ui.rounded import rounded_button

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
        tk.Label(self, text=ABOUT_EN, bg=th["bg"], fg=th["text"],
                 font=("Segoe UI", 11), wraplength=700, justify="center").pack(pady=12, padx=20)
        tk.Label(self, text=ABOUT_AR, bg=th["bg"], fg=th["text"],
                 font=("Segoe UI", 12), wraplength=700, justify="center").pack(pady=4, padx=20)
        tk.Label(self, text=t("about.contact", self.lang),
                 bg=th["bg"], fg=th["muted"], font=("Segoe UI", 10)).pack(pady=(16, 4))
        rounded_button(self, text=t("about.whatsapp_btn", self.lang).format(number=WHATSAPP), bg="#25D366", fg="white",
                  font=("Segoe UI", 11, "bold"),
                  command=lambda: webbrowser.open(WA_URL)).pack(pady=6)
