"""Clipboard history picker with MULTI-SELECT (Phase 2).
open_clipboard_picker(parent, on_paste): Toplevel listing the newest
20 history items with Checkbuttons. "Paste selected" pastes the ticked
items in display (newest-first) order, one per line; "Paste all" pastes
every item. When on_paste is None the picker pastes into the focused
Text/Entry widget itself (Text: one item per line, Entry: "; "-joined).
bind_clipboard_picker(widget, ...) binds Ctrl+Shift+V on any field.
<150 lines."""
import tkinter as tk
from src.config.theme import current
from src.config.strings import t
from src.models.database import get_setting
from src.models.clipboard_history import (add_clip, clear_clips,
    get_history, list_clips, multi_paste)
from src.ui.wheel_scroll import bind_canvas_wheel
from src.ui.rounded import rounded_button
CLIPBOARD_BINDING = "<Control-Shift-V>"
def paste_items_into(widget, items):
    """Insert items into a widget: Text gets one item per line (appended),
    Entry gets them '; '-joined. Returns True if pasted."""
    text = multi_paste(items)
    if not text or widget is None:
        return False
    # Rounded wrappers (round 13) are Frames around the real widget:
    # unwrap to the inner Text/Entry before the isinstance checks.
    widget = getattr(widget, "_inner", None) or widget
    try:
        if isinstance(widget, tk.Text):
            cur = widget.get("1.0", tk.END).strip()
            widget.insert(tk.END, ("" if not cur else "\n") + text)
            return True
        if isinstance(widget, tk.Entry):
            widget.insert(tk.END, text.replace("\n", "; "))
            return True
    except Exception:
        return False
    return False
def _default_paste(root, items):
    """Paste into the focused Text/Entry, else onto the system clipboard."""
    w = None
    try:
        w = root.focus_get()
    except Exception:
        pass
    if not paste_items_into(w, items):
        try:
            root.clipboard_clear(); root.clipboard_append(multi_paste(items))
        except Exception:
            pass
def open_clipboard_picker(parent, on_paste=None, lang=None):
    """Multi-select clipboard picker. on_paste(items: list[str]) is called
    with the selected texts in display order; None = paste into the
    focused field (or the system clipboard as a fallback)."""
    lang = lang or get_setting("language", "en") or "en"
    try:
        root = parent.winfo_toplevel()
    except Exception:
        root = parent
    win = tk.Toplevel(root); th = current(); win.configure(bg=th["bg"])
    win.title(t("dlg.cp_title", lang))
    win.geometry("560x420")
    rows = list_clips(20)
    state = {"open": True, "last_sys": ""}
    vars_ = []
    body = tk.Frame(win, bg=th["bg"]); body.pack(fill="both", expand=True, padx=6, pady=6)
    tk.Label(body, text=t("dlg.cp_hint", lang),
             font=("Segoe UI", 9), fg=th["muted"], bg=th["bg"]).pack(anchor="w")
    canvas = tk.Canvas(body, bg=th["bg"], highlightthickness=0); scroll = tk.Scrollbar(body, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=th["bg"])
    inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scroll.set)
    bind_canvas_wheel(canvas)
    canvas.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    if not rows:
        tk.Label(inner, text=t("dlg.cp_empty", lang), bg=th["bg"],
                 fg=th["text"], font=("Segoe UI", 10)).pack(padx=8, pady=12)
    for r in rows:
        v = tk.BooleanVar(value=False); vars_.append(v)
        label = (r["text"] or "").replace("\n", " ⏎ ")[:100]
        tk.Checkbutton(inner, text=label, variable=v, anchor="w", bg=th["bg"],
                       fg=th["text"], font=("Segoe UI", 9)).pack(fill="x", anchor="w")
    def _selected():
        return [rows[i]["text"] for i, v in enumerate(vars_) if v.get()]
    def _paste(items):
        if not items:
            return
        if on_paste:
            on_paste(items)
        else:
            _default_paste(root, items)
        state["open"] = False; win.destroy()
    def _poll():
        if not state["open"]:
            return
        try:
            cur = root.clipboard_get()
            if cur and cur != state["last_sys"]:
                state["last_sys"] = cur; add_clip(cur)
        except Exception:
            pass
        win.after(2000, _poll)
    btns = tk.Frame(win, bg=th["bg"]); btns.pack(fill="x", padx=6, pady=6)
    rounded_button(btns, text=t("dlg.cp_paste_selected", lang), bg="#A85F33", fg="white",
              command=lambda: _paste(_selected())).pack(side="left", padx=2)
    rounded_button(btns, text=t("dlg.cp_paste_all", lang), bg=th["card"], fg=th["text"],
              command=lambda: _paste(get_history(20))).pack(side="left", padx=2)
    rounded_button(btns, text=t("dlg.cp_clear", lang), bg=th["card"], fg=th["text"],
              command=lambda: (clear_clips(), win.destroy(),
                               open_clipboard_picker(parent, on_paste, lang=lang))).pack(side="left", padx=2)
    rounded_button(btns, text=t("dlg.cp_cancel", lang), bg=th["card"], fg=th["text"],
              command=lambda: (state.update(open=False), win.destroy())).pack(side="right", padx=2)
    win.protocol("WM_DELETE_WINDOW", lambda: (state.update(open=False), win.destroy()))
    _poll()
    return win
def bind_clipboard_picker(widget, on_paste=None):
    """Bind Ctrl+Shift+V on one field to open the multi-select picker.
    on_paste=None pastes into that field (or the focused field)."""
    def _open(_e=None):
        if on_paste:
            open_clipboard_picker(widget, on_paste)
        else:
            open_clipboard_picker(widget, lambda items: paste_items_into(widget, items))
        return "break"
    widget.bind(CLIPBOARD_BINDING, _open)
    return _open
