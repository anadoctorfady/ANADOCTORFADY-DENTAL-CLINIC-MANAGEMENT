"""Round 57, Section C: Current Medications Templates picker.

The patient form's Allergies and Diseases fields each have a
Templates button; Current Medications had none. This picker is
the medications equivalent, mirroring phrase_picker's shape:
a per-place Arabic | English toggle (field_lang category
"medication" -- its own persisted choice, else the global
template default), a live search over the 463-drug medications
data (utils.medications.search_medications, generic name first),
MULTI-select insert into the comma-separated field, and
Ctrl+C / Ctrl+V: copy the selection to the system clipboard AND
the clipboard history (so Ctrl+Shift+V recalls it), paste the
system clipboard into the field. Inserted text is the generic
name only, in the toggle's language -- the field stays a plain
comma-separated name list (generic_for() still resolves it for
the interaction checks); the listbox shows the full display
(generic + brand + form/strength) so look-alikes differ.
Light + dark via current(). <200 lines.
"""
import tkinter as tk

from src.config.strings import t
from src.config.theme import current
from src.models.clipboard_history import add_clip
from src.models.field_lang import field_template_lang
from src.ui.patient_diseases import EntryTextAdapter
from src.ui.rounded import rounded_button
from src.ui.rounded_lists import RoundedCombobox, RoundedListbox
from src.ui.rounded_widgets import RoundedEntry
from src.ui.zebra import zebra_listbox
from src.utils.medications import (display as med_display, generic_for,
                                   search_medications)

_CAT = {"en": "Medication", "ar": "الأدوية"}


def _name(item, lang):
    """Generic name of a drug row in the toggle's language."""
    if lang == "ar":
        return (str(item.get("generic_ar") or "").strip()
                or item.get("generic_en", ""))
    return item.get("generic_en", "")


def _append_names(adapter, names, mode):
    """Insert names (comma-separated) into the field; names already
    present (by canonical generic) are skipped, never duplicated.
    Returns True when anything was inserted."""
    cur = adapter.get().strip()
    existing = {generic_for(x).lower() for x in cur.split(",") if x.strip()}
    fresh = [n for n in dict.fromkeys(names)
             if n and generic_for(n).lower() not in existing]
    if not fresh:
        return False
    text = ", ".join(fresh)
    if mode == "Replace":
        adapter.delete("1.0", tk.END)
        adapter.insert("1.0", text)
    else:
        adapter.insert(tk.END, text)
    return True


def open_medication_picker(parent, entry, lang="en"):
    """Medication templates dialog over the meds entry. Returns the
    Toplevel; test hooks live on it (listbox/search/mode +
    insert_selected/copy_selected/paste_clipboard +
    field_lang_toggle)."""
    lang = "ar" if lang == "ar" else "en"
    adapter = EntryTextAdapter(entry)
    tl = {"v": field_template_lang("medication")}
    th = current()
    win = tk.Toplevel(parent)
    win.title(t("dlg.pp_title", lang).format(category=_CAT[lang]))
    win.geometry("560x460")  # R57: 420 clipped the button row on
    # Linux (14-row listbox + head + search + buttons > 420px).
    win.configure(bg=th["bg"])
    head = tk.Frame(win, bg=th["bg"])
    head.pack(fill="x", padx=8, pady=6)
    tk.Label(head, text=t("dlg.pp_heading", lang),
             bg=th["bg"], fg=th["text"],
             font=("Segoe UI", 10, "bold")).pack(side="left")
    from src.ui.template_lang_ui import build_lang_toggle
    _toggle, _mark = build_lang_toggle(
        head, lambda: "medication",
        lambda new: (tl.update(v=new), refresh()))
    _toggle.pack(side="right")
    win.field_lang_toggle = _toggle  # for tests
    top = tk.Frame(win, bg=th["bg"])
    top.pack(fill="x", padx=8, pady=2)
    tk.Label(top, text=t("dlg.pp_search", lang), bg=th["bg"],
             fg=th["text"]).pack(side="left")
    search = RoundedEntry(top, width=30, bg=th["bg"])
    search.pack(side="left", padx=4)
    rounded_button(top, text=t("tpl_search", lang), relief="flat",
                   command=lambda: refresh()).pack(side="left", padx=2)
    mode = RoundedCombobox(top, values=["Append", "Replace"], width=7,
                           state="readonly", bg=th["bg"])
    mode.set("Append")
    mode.pack(side="left", padx=4)
    box = RoundedListbox(win, height=14, font=("Segoe UI", 10),
                         bg=th["bg"], fg=th["text"])
    # RoundedListbox takes no selectmode kw (it would hit the Frame);
    # set multi-select on the inner Listbox directly.
    box.listbox.configure(selectmode=tk.MULTIPLE)
    box.pack(fill="both", expand=True, padx=8, pady=4)
    state = {"rows": []}

    def refresh(_e=None):
        state["rows"] = search_medications(search.get())
        box.delete(0, tk.END)
        for r in state["rows"]:
            box.insert(tk.END, med_display(r, tl["v"]))
        zebra_listbox(box)

    def insert_selected(_e=None):
        sel = box.curselection()
        if not sel:
            return False
        ok = _append_names(adapter,
                           [_name(state["rows"][i], tl["v"]) for i in sel],
                           mode.get())
        if ok:
            win.destroy()
            return "break"  # stop the Listbox class binding running after
        return False

    def copy_selected(_e=None):
        """Ctrl+C: selected generic names -> system clipboard AND
        the clipboard history (Ctrl+Shift+V recalls them). Returns
        "break": the Listbox class binding for <<Copy>> would
        otherwise run after this one and overwrite the clipboard
        with the selected row's DISPLAY text (generic + brand +
        form/strength) instead of the generic name."""
        sel = box.curselection()
        if not sel:
            return False
        text = ", ".join(_name(state["rows"][i], tl["v"]) for i in sel)
        try:
            win.clipboard_clear()
            win.clipboard_append(text)
        except Exception:
            pass
        add_clip(text)
        return "break"

    def paste_clipboard(_e=None):
        """Ctrl+V: system clipboard text -> the meds field
        (comma-separated append, or Replace per the mode)."""
        try:
            text = win.clipboard_get()
        except Exception:
            return False
        parts = [p.strip() for p in str(text or "").replace("\n", ",").split(",")]
        ok = _append_names(adapter, [p for p in parts if p], mode.get())
        return "break" if ok else False

    win.listbox = box
    win.search = search
    win.mode = mode
    win.insert_selected = insert_selected
    win.copy_selected = copy_selected
    win.paste_clipboard = paste_clipboard
    search.bind("<KeyRelease>", refresh)
    box.bind("<Double-Button-1>", insert_selected)
    # Copy/paste live on the listbox: binding them on the window
    # would hijack the search entry's own Ctrl+C / Ctrl+V.
    box.bind("<Control-c>", copy_selected)
    box.bind("<Control-C>", copy_selected)
    box.bind("<Control-v>", paste_clipboard)
    box.bind("<Control-V>", paste_clipboard)
    btns = tk.Frame(win, bg=th["bg"])
    btns.pack(fill="x", padx=8, pady=6)
    rounded_button(btns, text=t("dlg.pp_insert", lang), bg="#7A3F16",
                   fg="white", relief="flat",
                   command=insert_selected).pack(side="left", padx=2)
    rounded_button(btns, text=t("dlg.pp_copy", lang), relief="flat",
                   command=copy_selected).pack(side="left", padx=2)
    rounded_button(btns, text=t("dlg.pp_paste", lang), relief="flat",
                   command=paste_clipboard).pack(side="left", padx=2)
    rounded_button(btns, text=t("dlg.pp_close", lang), relief="flat",
                   command=win.destroy).pack(side="right", padx=2)
    refresh()
    return win
