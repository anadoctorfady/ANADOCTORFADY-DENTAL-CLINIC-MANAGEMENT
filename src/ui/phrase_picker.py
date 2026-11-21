"""Template picker for the clinical tab (Item 5, 2026-11-08). <200 lines.

No specialty picker any more: every field gets a SMALL picker button
beside it that opens one dialog over the COMBINED pool - reusable
phrases (phrases_seed.json + auto-learned) + seed phrases from ALL 8
specialties (specialties.json) + custom templates. The doctor can also
type free text in the field or save the current text as a new template.
The multi-select clipboard picker (Ctrl+Shift+V) is untouched and stays
silent in the clinical UI (no button / hint mentions it there)."""
import tkinter as tk
from tkinter import ttk, messagebox
from src.config.theme import current
from src.config.strings import t
from src.models.database import get_setting
from src.models.phrases import search_phrases, save_phrase, toggle_favorite, search_text_matches; from src.ui.zebra import zebra_listbox
from src.models import specialty_templates as tpl
from src.models.database import get_connection
from src.models.clipboard_history import add_clip, list_clips, clear_clips
from src.ui.rounded import rounded_button
from src.ui.rounded_widgets import RoundedEntry; from src.ui.rounded_lists import RoundedCombobox, RoundedListbox
_CAT = {"symptom": "symptoms", "procedure": "procedures",
        "symptoms": "symptoms", "procedures": "procedures",
        "complaint": "complaint", "diagnosis": "diagnosis"}

def combined_templates(category, query="", lang=None):
    """Combined pool for one field: [{text, display, favorite}].
    Reusable phrases first (favorites on top), then the all-specialties
    seed pool (overrides applied, deleted dropped), then custom
    templates. Every row shows ONE language only (the EFFECTIVE
    template language — round 31: tpl.effective_template_lang(),
    the doctor's template_lang choice, default = app language);
    `text` is what gets inserted. Deduped by text (R21 normalizer)."""
    lang = lang or tpl.effective_template_lang()
    out, seen = [], set()

    def _add(text, display, fav=False):
        key = (display or text or "").strip().lower()
        if text and key not in seen:
            seen.add(key)
            out.append({"text": text, "display": display or text, "favorite": fav})
    for r in search_phrases(category, query, limit=50, lang=lang):
        _add(r["text"], r["text"], bool(r.get("is_favorite")))
    try:
        conn = get_connection()
        try:
            rows = tpl.effective_pool(conn, category, lang)
        finally:
            conn.close()
        for r in rows:
            if not search_text_matches(r["text"], query):
                continue
            _add(r["text"], r["text"])
    except Exception:
        pass
    return out

def _insert(widget, text, mode):
    if mode == "Replace":
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
    else:
        cur = widget.get("1.0", tk.END).strip()
        widget.insert(tk.END, ("" if not cur else "\n") + text)
_CAT_AR = {"complaint": "dlg.cat_complaint", "symptom": "dlg.cat_symptom", "disease": "dlg.cat_disease",
            "symptoms": "dlg.cat_symptom", "diagnosis": "dlg.cat_diagnosis", "referral": "dlg.cat_referral",
            "allergy": "dlg.cat_allergy", "procedure": "dlg.cat_procedure", "procedures": "dlg.cat_procedure"}


def open_template_picker(parent, category, text_widget, current_user=None, lang=None):
    """Small dialog: search the combined pool, pick a template to insert
    (Append / Replace), or save the field's current text as a template."""
    lang = lang or get_setting("language", "en") or "en"
    tl = tpl.effective_template_lang()
    th = current()
    win = tk.Toplevel(parent)
    win.title(t("dlg.pp_title", lang).format(
        category=t(_CAT_AR[category], lang) if category in _CAT_AR else category))
    win.geometry("560x420")
    win.configure(bg=th["bg"])
    # Round 15: heading uses text (not accent) for contrast (13.56:1).
    tk.Label(win, text=t("dlg.pp_heading", lang),
             bg=th["bg"], fg=th["text"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=8, pady=6)
    top = tk.Frame(win, bg=th["bg"])
    top.pack(fill="x", padx=8, pady=2)
    tk.Label(top, text=t("dlg.pp_search", lang), bg=th["bg"], fg=th["text"]).pack(side="left")
    search = RoundedEntry(top, width=30, bg=th["bg"])
    search.pack(side="left", padx=4)
    # Round 21: explicit Search button (owner expects one) + live KeyRelease filtering below.
    rounded_button(top, text=t("tpl_search", lang), relief="flat", command=lambda: refresh()).pack(side="left", padx=2)
    mode = RoundedCombobox(top, values=["Append", "Replace"], width=7, state="readonly", bg=th["bg"])
    mode.set("Append")
    mode.pack(side="left", padx=4)
    # Round 15: list background is the app MAIN colour (th["bg"]).
    box = RoundedListbox(win, height=14, font=("Segoe UI", 10), bg=th["bg"], fg=th["text"])
    box.pack(fill="both", expand=True, padx=8, pady=4)
    state = {"rows": []}

    def refresh(_e=None):
        state["rows"] = combined_templates(category, search.get(), tl)
        box.delete(0, tk.END)
        for r in state["rows"]:
            box.insert(tk.END, ("⭐ " if r["favorite"] else "") + r["display"])
        zebra_listbox(box)  # R21 item 6

    def insert_sel(_e=None):
        sel = box.curselection()
        if not sel:
            return
        _insert(text_widget, state["rows"][sel[0]]["text"], mode.get())
        win.destroy()

    def save_current():
        txt = text_widget.get("1.0", tk.END).strip()
        if len(txt) < 3:
            messagebox.showwarning(t("dlg.tm_empty_title", lang), t("dlg.pp_empty_msg", lang))
            return
        save_phrase(category, txt)
        try:
            conn = get_connection()
            try:
                # Saved in the template language only (one language per template).
                en, ar = (txt, "") if tl == "en" else ("", txt)
                tpl.add_template(conn, "general", _CAT.get(category, category),
                                 en, ar, created_by=current_user or "")
            finally:
                conn.close()
        except Exception:
            pass
        refresh()
        messagebox.showinfo(t("dlg.pp_saved_title", lang), t("dlg.pp_saved_msg", lang))

    def fav():
        sel = box.curselection()
        if not sel:
            return
        rows = search_phrases(category, state["rows"][sel[0]]["text"], limit=5)
        if rows:
            toggle_favorite(rows[0]["id"])
        refresh()
    search.bind("<KeyRelease>", refresh)
    box.bind("<Double-Button-1>", insert_sel)
    btns = tk.Frame(win, bg=th["bg"])
    btns.pack(fill="x", padx=8, pady=6)
    rounded_button(btns, text=t("dlg.pp_insert", lang), bg="#7A3F16", fg="white",
              relief="flat", command=insert_sel).pack(side="left", padx=2)
    rounded_button(btns, text=t("dlg.pp_save_template", lang), relief="flat",
              command=save_current).pack(side="left", padx=2)
    rounded_button(btns, text=t("dlg.pp_favorite", lang), relief="flat",
              command=fav).pack(side="left", padx=2)
    rounded_button(btns, text=t("dlg.pp_close", lang), relief="flat",
              command=win.destroy).pack(side="right", padx=2)
    refresh()
    return win

def attach_picker_button(parent, category, text_widget, current_user=None):
    """The SMALL picker button that sits beside a clinical field."""
    btn = rounded_button(parent, text=t("dlg.pp_picker_btn", get_setting("language", "en") or "en"), relief="flat",
                    command=lambda: open_template_picker(parent, category, text_widget, current_user))
    return btn

def show_clipboard_panel(root, get_target=None, lang=None):
    """Clipdiary-like panel: last 20 clips, click to paste into focused field.
    Polls the system clipboard every 2s while open (so text copied in
    Clipdiary / any program appears here automatically)."""
    lang = lang or get_setting("language", "en") or "en"
    win = tk.Toplevel(root); th = current(); win.configure(bg=th["bg"]); win.title(t("dlg.pp_clip_title", lang))
    win.geometry("520x380")
    box = RoundedListbox(win, font=("Segoe UI", 10), bg=th["bg"], fg=th["text"]); box.pack(fill="both", expand=True, padx=6, pady=6)
    state = {"rows": [], "last_sys": "", "open": True}
    def refresh():
        state["rows"] = list_clips(20); box.delete(0, tk.END)
        for r in state["rows"]:
            box.insert(tk.END, r["text"].replace("\n", " ")[:90])
        zebra_listbox(box)  # R24 audit: clipboard panel was missing zebra
    def paste(_e=None):
        sel = box.curselection()
        if not sel: return
        text = state["rows"][sel[0]]["text"]
        w = root.focus_get()
        if isinstance(w, tk.Text): _insert(w, text, "Append")
        elif isinstance(w, tk.Entry): w.insert(tk.END, text)
        elif get_target: _insert(get_target(), text, "Append")
        else:
            try: root.clipboard_clear(); root.clipboard_append(text)
            except Exception: pass
    def poll():
        if not state["open"]: return
        try:
            cur = root.clipboard_get()
            if cur and cur != state["last_sys"]:
                state["last_sys"] = cur; add_clip(cur); refresh()
        except Exception: pass
        win.after(2000, poll)
    box.bind("<<ListboxSelect>>", paste)
    box.bind("<Double-Button-1>", paste)
    rounded_button(win, text=t("dlg.pp_clip_clear", lang), command=lambda: (clear_clips(), refresh())).pack(side="left", padx=6, pady=4)
    rounded_button(win, text=t("dlg.pp_clip_refresh", lang), command=refresh).pack(side="left", padx=6, pady=4)
    win.protocol("WM_DELETE_WINDOW", lambda: (state.update(open=False), win.destroy()))
    refresh(); poll()
    return win
