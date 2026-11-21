"""Add a new drug dialog (Item 6, 2026-11-08; fixed round 16, 2026-11-11).

Owner's question was "where do I add a drug name/composition" - there
was no such place. Now the prescription section has an "Add drug /
إضافة دواء" control that opens this dialog: scientific (generic) name,
Arabic name, brand (EN/AR), category, dosage form + strength
(composition). Saved persistently to src/data/user_medications.json
via medications.add_user_medication, so the drug appears in the drug
search alongside the 315 seed drugs and survives restarts. Seed drugs
are never edited or deleted from here.

Round 16 fixes: (1) the dialog was CLIPPED at the bottom -- its
content needs ~536px but the window was fixed at 480px, cutting the
Save/Cancel buttons. The body is now scrollable and the window is
sized to its content (capped at screen height), so nothing is ever
cut off. (2) The CATEGORY selector now comes BEFORE the drug name
fields, so picking a category narrows the search first."""
import tkinter as tk
from tkinter import ttk, messagebox
from src.config.theme import current
from src.ui.rounded import rounded_button
from src.ui.rounded_widgets import RoundedEntry; from src.ui.rounded_lists import RoundedCombobox
from src.ui.wheel_scroll import bind_canvas_wheel
from src.config.strings import t
from src.config.strings_r30_drug import r30_t
from src.models.database import get_setting
from src.utils.medications import add_user_medication, categories
from src.utils.drug_classes import ordered_class_tokens
from src.ui.searchable_picker import SearchablePicker

# Field key -> strings key; labels are resolved via t() at build time.
FIELDS = (("generic_en", "dlg.ad_f_generic_en"),
          ("generic_ar", "dlg.ad_f_generic_ar"),
          ("brand_en", "dlg.ad_f_brand_en"),
          ("brand_ar", "dlg.ad_f_brand_ar"),
          ("form", "dlg.ad_f_form"),
          ("strength", "dlg.ad_f_strength"))

def open_add_drug_dialog(parent, on_saved=None, lang=None):
    """Toplevel form; on_saved (optional) is called after a successful
    save so the prescription drug list can refresh at once."""
    lang = lang or get_setting("language", "en") or "en"
    th = current()
    win = tk.Toplevel(parent)
    win.title(t("dlg.ad_title", lang))
    win.configure(bg=th["bg"])
    # Scrollable body (round 16): content is taller than a fixed window.
    canvas = tk.Canvas(win, bg=th["bg"], highlightthickness=0)
    sb = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    body = tk.Frame(canvas, bg=th["bg"])
    canvas.create_window((0, 0), window=body, anchor="nw")
    body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    bind_canvas_wheel(canvas)
    tk.Label(body, text=t("dlg.ad_title", lang), bg=th["bg"], fg=th["accent"],
             font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=8)
    tk.Label(body, text=t("dlg.ad_note", lang),
             bg=th["bg"], fg=th["muted"]).pack(anchor="w", padx=10)
    # Category FIRST (round 16): pick the category, then the drug.
    tk.Label(body, text=t("dlg.ad_category", lang), bg=th["bg"], fg=th["text"]).pack(anchor="w", padx=10, pady=(6, 0))
    cat_var = tk.StringVar(value="Other")
    cats = [c for c in categories() if c != "All"] or ["Other"]
    cat_combo = RoundedCombobox(body, textvariable=cat_var, values=cats, width=30,
                 state="readonly")
    cat_combo.pack(anchor="w", padx=10)
    # Round 30 (item 3a): pharmacological CLASS picker -- the alert
    # engines (drug-drug / drug-disease / allergy) all key on the
    # record's `class` token, which this dialog never collected, so
    # user drugs silently got NO class-based alerts. Tokens come
    # from utils.drug_classes (medications data + legacy CLASSES);
    # the chosen category's classes sort FIRST (the category only
    # orders the list -- it is never used as a matching key).
    # Empty (the "(No class)" row) is allowed; the note under the
    # picker states what that means.
    none_labels = {r30_t("dlg.ad_class_none", "en"),
                   r30_t("dlg.ad_class_none", "ar")}
    def _class_disp(it):
        return r30_t("dlg.ad_class_none", lang) if not it["class"] else it["class"]
    def _class_items():
        return [{"class": ""}] + [{"class": tok}
                for tok in ordered_class_tokens(cat_var.get())]
    tk.Label(body, text=r30_t("dlg.ad_class", lang), bg=th["bg"],
             fg=th["text"]).pack(anchor="w", padx=10, pady=(6, 0))
    class_var = tk.StringVar(value=r30_t("dlg.ad_class_none", lang))
    class_picker = SearchablePicker(body, _class_items(), _class_disp,
                                    textvariable=class_var, width=30, lang=lang)
    class_picker.pack(anchor="w", padx=10)
    tk.Label(body, text=r30_t("dlg.ad_class_note", lang), bg=th["bg"],
             fg=th["muted"], wraplength=420, justify="left").pack(
                 anchor="w", padx=10)
    def _on_category(_e=None):
        # Re-order only: every token stays listed; the new
        # category's classes move to the top.
        class_picker._items = _class_items()
        class_picker._set_values([_class_disp(i)
                                  for i in class_picker._items])
    cat_combo.bind("<<ComboboxSelected>>", _on_category, add="+")
    entries = {}
    for key, label_key in FIELDS:
        tk.Label(body, text=t(label_key, lang), bg=th["bg"], fg=th["text"]).pack(anchor="w", padx=10, pady=(6, 0))
        e = RoundedEntry(body, width=46)
        e.pack(anchor="w", padx=10)
        entries[key] = e

    def save():
        item = {k: e.get().strip() for k, e in entries.items()}
        item["category"] = cat_var.get()
        # The picker variable holds the DISPLAY string; the stored
        # token is verbatim ("" for the "(No class)" row).
        chosen = class_var.get().strip()
        item["class"] = "" if chosen in none_labels else chosen
        ok, msg = add_user_medication(item, lang=lang)
        if not ok:
            messagebox.showerror(t("dlg.ad_error_title", lang), msg)
            return
        messagebox.showinfo(t("dlg.ad_added_title", lang), msg)
        win.destroy()
        if on_saved:
            on_saved()

    btns = tk.Frame(body, bg=th["bg"])
    btns.pack(fill="x", padx=10, pady=14)
    save_btn = rounded_button(btns, text=t("dlg.ad_save", lang), bg="#7A3F16", fg="white",
              relief="flat", command=save)
    save_btn.pack(side="left", padx=2)
    rounded_button(btns, text=t("dlg.ad_cancel", lang), relief="flat",
              command=win.destroy).pack(side="left", padx=2)
    # Size to content (never clip), capped at the screen height; the
    # scrollbar covers anything taller than the screen.
    win.update_idletasks()
    h = min(body.winfo_reqheight() + 8, win.winfo_screenheight() - 60)
    win.geometry(f"460x{h}")
    win.update_idletasks()
    win._ad_body = body; win._ad_entries = entries
    win._ad_cat_combo = cat_combo; win._ad_save_btn = save_btn
    win._ad_class_picker = class_picker; win._ad_class_var = class_var
    win._ad_cat_var = cat_var
    entries["generic_en"].focus_set()
    return win
