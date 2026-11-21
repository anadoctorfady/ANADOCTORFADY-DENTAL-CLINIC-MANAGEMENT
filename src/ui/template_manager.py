"""Template manager dialog (Job 2, 2026-11-09). <200 lines.

Works on the COMBINED pool for one category at a time (complaint /
symptom / diagnosis / procedure). Every row shows ONE language only
(the EFFECTIVE template language, R31). Seed edits are stored as
overrides in src/data/user_templates.json (specialties.json is never
touched). Round 21: hiding is REMOVED - Delete works for EVERY
template and "Restore built-in templates" restores factory state.
A live search row filters by the visible text. Edited seeds show ✎."""
import tkinter as tk
from tkinter import ttk, messagebox
from src.config.theme import current
from src.config.strings import t
from src.models.database import get_setting
from src.models.database import get_connection
from src.models import specialty_templates as tpl
from src.models.phrases import search_text_matches
from src.ui.phrase_picker import _CAT
from src.ui.rounded import rounded_button
from src.ui.rounded_widgets import RoundedEntry
from src.ui.rounded_lists import RoundedCombobox, RoundedListbox; from src.ui.zebra import zebra_listbox
try:
    from src.config.strings_r15_templates import EN as _R15_EN, AR as _R15_AR
except ImportError:
    _R15_EN, _R15_AR = {}, {}
CATS = ("complaint", "symptom", "diagnosis", "procedure")

def _r15(key, lang, fallback_key):
    """Round-15/21 string: prefer strings_r15_templates; fall back."""
    d = _R15_AR if lang == "ar" else _R15_EN
    return d.get(key) or t(fallback_key, lang)

def open_template_manager(parent, current_user, lang=None):
    lang = lang or get_setting("language", "en") or "en"
    tl = tpl.resolve_template_lang()
    win = tk.Toplevel(parent)
    th = current()
    win.configure(bg=th["bg"])
    win.title(t("dlg.tm_title", lang))
    win.geometry("640x560")
    top = tk.Frame(win, bg=th["bg"])
    top.pack(fill="x", padx=8, pady=6)
    tk.Label(top, text=t("dlg.tm_category", lang), bg=th["bg"], fg=th["text"]).pack(side="left")
    # Explicit master (win): a bare StringVar can bind to a DIFFERENT root.
    cat_var = tk.StringVar(win, value="complaint")
    RoundedCombobox(top, textvariable=cat_var, values=list(CATS),
                 state="readonly", width=14, bg=th["bg"]).pack(side="left", padx=4)
    # Round 31: three-way template-language selector (same persisted
    # template_lang setting as Settings; applies on selection).
    tk.Label(top, text=t("tpl_settings_lang", lang), bg=th["bg"], fg=th["text"]).pack(side="left", padx=(8, 2))
    modes = {"app": t("tpl_lang_auto", lang), "ar": "العربية", "en": "English"}
    mode_var = tk.StringVar(win, value=modes[tpl.template_lang_mode()])
    mode_cb = RoundedCombobox(top, textvariable=mode_var, values=[modes["app"], "العربية", "English"],
                 state="readonly", width=16, bg=th["bg"]); mode_cb.pack(side="left", padx=4)
    win.template_mode_var, win.template_mode_combo = mode_var, mode_cb
    # Round 21: search row - live filtering plus an explicit Search button.
    srow = tk.Frame(win, bg=th["bg"])
    srow.pack(fill="x", padx=8, pady=2)
    tk.Label(srow, text=t("dlg.pp_search", lang), bg=th["bg"], fg=th["text"]).pack(side="left")
    e_search = RoundedEntry(srow, width=44, bg=th["bg"])
    e_search.pack(side="left", padx=4)
    rounded_button(srow, text=_r15("tpl_search", lang, "dlg.pp_search"), relief="flat",
                   command=lambda: refresh()).pack(side="left", padx=2)
    box = RoundedListbox(win, font=("Segoe UI", 10), height=12, bg=th["bg"], fg=th["text"])  # R15: list bg = app MAIN colour
    box.pack(fill="both", expand=True, padx=8, pady=4)
    state = {"rows": []}

    def refresh(_e=None):
        conn = get_connection()
        try:
            rows = tpl.effective_pool(conn, cat_var.get(), tl)
        finally:
            conn.close()
        q = e_search.get()
        state["rows"] = [r for r in rows if search_text_matches(r["text"], q)]
        box.delete(0, tk.END)
        for r in state["rows"]:
            mark = t("tpl_edited_mark", lang) if r.get("edited") else ""
            box.insert(tk.END, mark + r["text"])
        zebra_listbox(box)  # R21 item 6
    def _sel():
        sel = box.curselection()
        return state["rows"][sel[0]] if sel else None
    def _need_row():
        r = _sel()
        if not r:
            messagebox.showwarning(t("dlg.tm_empty_title", lang), t("tpl_select_first", lang))
        return r
    def add():
        text = e_txt.get().strip()
        if not text:
            messagebox.showwarning(t("dlg.tm_empty_title", lang), t("dlg.tm_empty_msg", lang))
            return
        conn = get_connection()
        try:
            tpl.add_template(conn, "general", _CAT.get(cat_var.get(), cat_var.get()),
                             text if tl == "en" else "", text if tl == "ar" else "",
                             created_by=current_user)
        finally:
            conn.close()
        e_txt.delete(0, tk.END)
        refresh()
    def edit():
        r = _need_row()
        if not r:
            return
        text = e_txt.get().strip()
        if not text:
            messagebox.showwarning(t("dlg.tm_empty_title", lang), t("dlg.tm_empty_msg", lang))
            return
        if r.get("is_custom"):
            conn = get_connection()
            try:
                tpl.update_template(conn, r["id"], **({"text_ar": text} if tl == "ar" else {"text_en": text}))
            finally:
                conn.close()
        else:
            # Seed edit -> override for this language side only.
            tpl.set_seed_override(r["category"], r["seed_en"], r["seed_ar"],
                                  **({"new_ar": text} if tl == "ar" else {"new_en": text}))
        refresh()
    def delete():
        r = _need_row()
        if not r:
            return
        if r.get("is_custom"):
            if not messagebox.askyesno(t("dlg.tm_delete_title", lang), t("dlg.tm_delete_confirm", lang)):
                return
            conn = get_connection()
            try:
                tpl.delete_template(conn, r["id"])
            finally:
                conn.close()
        else:
            # Round 21: seed delete = tombstone (Restore brings it back).
            if not messagebox.askyesno(_r15("tpl_delete_seed_title", lang, "dlg.tm_delete_title"),
                                       _r15("tpl_delete_seed_confirm", lang, "dlg.tm_delete_confirm")):
                return
            tpl.delete_seed(r["category"], r["seed_en"], r["seed_ar"])
        refresh()
    def restore_builtins():
        # Round 21: category-level restore clears edits + tombstones.
        if not tpl.restore_builtin_templates(cat_var.get()):
            messagebox.showinfo(t("dlg.tm_title", lang), t("tpl_nothing_to_restore", lang))
            return
        refresh()
    def _fill(_e=None):
        r = _sel()
        if r:
            e_txt.delete(0, tk.END)
            # R18: edit box gets the RAW stored side, never the caps display text.
            e_txt.insert(0, (r.get("ar") if tl == "ar" else r.get("en")) or r["text"])
    frm = tk.Frame(win, bg=th["bg"])
    frm.pack(fill="x", padx=8, pady=4)
    tk.Label(frm, text=t("tpl_edit_text", lang), bg=th["bg"], fg=th["text"]).pack(side="left")
    e_txt = RoundedEntry(frm, width=52, bg=th["bg"])
    e_txt.pack(side="left", padx=2)
    btns = tk.Frame(win, bg=th["bg"])
    btns.pack(fill="x", padx=8, pady=4)
    for txt, cmd in ((t("dlg.tm_add", lang), add), (t("dlg.tm_edit", lang), edit),
                     (t("dlg.tm_delete", lang), delete),
                     (_r15("tpl_restore_builtins", lang, "tpl_restore"), restore_builtins)):
        rounded_button(btns, text=txt, relief="flat", command=cmd).pack(side="left", padx=2)
    # Round 15: right-click context menu (same actions as the buttons).
    def _ctx_add():
        e_txt.delete(0, tk.END)
        e_txt.focus_set()
    def _ctx_edit():
        r = _need_row()
        if not r:
            return
        e_txt.delete(0, tk.END)
        e_txt.insert(0, (r.get("ar") if tl == "ar" else r.get("en")) or r["text"])  # R18: raw, not caps
        e_txt.focus_set()
        # NB: no select_range() - it would clear the listbox selection.
    ctx = tk.Menu(win, tearoff=0, bg=th["bg"], fg=th["text"],
                  activebackground=th["border"], activeforeground=th["text"])
    ctx.add_command(label=_r15("tpl_ctx_edit", lang, "dlg.tm_edit"), command=_ctx_edit)
    ctx.add_command(label=_r15("tpl_ctx_delete", lang, "dlg.tm_delete"), command=delete)
    ctx.add_separator()
    ctx.add_command(label=_r15("tpl_ctx_add_new", lang, "dlg.tm_add"), command=_ctx_add)
    def _popup(e):
        idx = box.nearest(e.y)
        if 0 <= idx < box.size():
            bb = box.bbox(idx)
            if bb and bb[1] <= e.y <= bb[1] + bb[3]:
                box.selection_clear(0, tk.END)
                box.selection_set(idx)
                _fill()
        ctx.post(e.x_root, e.y_root)
    box.bind("<Button-3>", _popup)
    win._r15_ctx_menu = ctx
    def _mode_changed(_e=None):
        nonlocal tl; tpl.set_template_lang_mode({v: k for k, v in modes.items()}.get(mode_var.get(), "app")); tl = tpl.effective_template_lang(); refresh()
    mode_cb.combo.bind("<<ComboboxSelected>>", _mode_changed)
    top.winfo_children()[1].bind("<<ComboboxSelected>>", refresh)
    e_search.bind("<KeyRelease>", refresh)
    box.bind("<<ListboxSelect>>", _fill)
    refresh()
    return win
