"""Round 25 item 5: genuinely searchable currency picker.
Root cause: SearchableCombobox's <KeyRelease> only rewrote its
values list and NEVER opened the popdown, so typing showed no
results (the Finance selector was a readonly RoundedCombobox:
no typing at all). Modelled on category_picker.CategoryPicker:
read-only rounded display; clicking opens a popup whose FILTER
ENTRY has focus -- typing narrows the list VISIBLY by code / EN
name / AR name via searchable.filter_list (items mode) or ranked
substring (values mode: Finance 'All currencies' + codes).
First letter works: 'd' lists D-currencies first. Selecting a
row sets the bound variable EXACTLY as the old control did and
fires <<ComboboxSelected>>, so code_for() round-trips and host
calc/refresh handlers still run. .widget is the picker itself,
so legacy .widget["values"]/.bind call sites keep working."""
import tkinter as tk
from tkinter import font as tkfont
from src.config.strings import t
from src.config.theme import current, field_border, is_dark
from src.ui.rounded_widgets import _RoundedBorder, RoundedEntry
from src.ui.rounded_lists import RoundedListbox
from src.ui.zebra import zebra_listbox
from src.utils.searchable import filter_list
VISIBLE_ROWS = 15; _FONT = ("Segoe UI", 10); _PAD = 40  # popup list rows / font / width slack
class CurrencyPicker(_RoundedBorder):
    """Searchable currency display + filter popup picker."""
    def __init__(self, parent, textvariable=None, values=None, items=None,
                 display_fn=None, width=None, on_select=None, font=None,
                 lang="en", **kw):
        th = current()
        self._items = list(items) if items is not None else None
        self._display_fn = display_fn or (lambda it: str(it))
        self._values = [self._display_fn(i) for i in self._items] if self._items is not None else list(values or [])
        self._filtered = list(self._values)
        self._var = textvariable; self._on_select = on_select
        self._font_spec = font or _FONT; self.lang = lang or "en"
        self._sel_handlers = []
        self.popup = None; self.popup_listbox = None; self.popup_entry = None
        self.popup_width = 0; self.popup_visible_rows = 0
        self._popup_root = None; self._root_bind_id = None; self._esc_bind_id = None
        super().__init__(parent, field_bg=th["panel"], **kw)
        inner = tk.Frame(self, bg=self._field_bg)
        self._label = tk.Label(inner, textvariable=textvariable, bg=self._field_bg, fg=th["text"], font=self._font_spec, anchor="w", cursor="hand2")
        if width is not None: self._label.configure(width=width)
        self._label.pack(side="left", fill="x", expand=True)
        self._arrow = tk.Label(inner, text="▾", bg=self._field_bg, fg=th["text"], font=self._font_spec, cursor="hand2"); self._arrow.pack(side="right")
        self._attach(inner); self.widget = self  # .widget compat (see header)
        self._click_parts = (inner, self._label, self._arrow)
        for w in self._click_parts:
            w.bind("<Button-1>", lambda _e: self.toggle_popup(), add="+"); w.bind("<Down>", lambda _e: self.open_popup(), add="+")
            w.bind("<Return>", lambda _e: self.open_popup(), add="+"); w.bind("<space>", lambda _e: self.open_popup(), add="+")
            w.bind("<Key>", self._on_control_key, add="+")
        tk.Frame.bind(self, "<Destroy>", self._on_destroy, add="+")
    @property
    def values(self): return list(self._values)  # all displays, unfiltered
    @values.setter
    def values(self, vals):
        self._items = None; self._values = list(vals or []); self._filtered = list(self._values)
    def get(self): return self._var.get() if self._var is not None else self._label.cget("text")
    def set(self, value):
        if self._var is not None: self._var.set(value)
        else: self._label.configure(text=value)
    def cget(self, key):
        if key == "values": return tuple(self._values)
        if key == "textvariable": return str(self._var) if self._var is not None else ""
        return super().cget(key)
    def configure(self, cnf=None, **kw):
        merged = dict(cnf) if isinstance(cnf, dict) else {}; merged.update(kw)
        if "values" in merged: self.values = merged.pop("values")
        if "items" in merged:
            self._items = list(merged.pop("items") or []); self._values = [self._display_fn(i) for i in self._items]; self._filtered = list(self._values)
        if "textvariable" in merged:
            self._var = merged.pop("textvariable")
            self._label.configure(textvariable=self._var)
        return super().configure(merged) if merged else None
    config = configure
    def bind(self, sequence=None, func=None, add=None):
        """<<ComboboxSelected>> handlers are stored for select_value()."""
        if func is None: return tk.Frame.bind(self, sequence)
        if sequence == "<<ComboboxSelected>>":
            self.__dict__.setdefault("_sel_handlers", []).append(func); return ""
        result = tk.Frame.bind(self, sequence, func, add)
        for w in getattr(self, "_click_parts", ()):
            try: w.bind(sequence, func, add)
            except Exception: pass
        return result  # frame + clickable parts
    def filtered_values(self, query):
        """The displays a query would show (no popup needed)."""
        if self._items is not None:
            fields = list(self._items[0].keys()) if self._items else []
            return [self._display_fn(i) for i in filter_list(self._items, query, fields)]
        hits = filter_list([{"_s": v} for v in self._values], query, ["_s"])
        return [h["_s"] for h in hits]
    def visible_values(self):
        """Popup contents when open, else the last filter result."""
        if self.popup_listbox is not None:
            return [self.popup_listbox.get(i) for i in range(self.popup_listbox.size())]
        return list(self._filtered)
    def set_filter(self, query):
        """Open the popup (if needed) and narrow it to `query`."""
        if self.popup is None: self.open_popup()
        if self.popup_entry is not None:
            self.popup_entry.delete(0, tk.END)
            if query: self.popup_entry.insert(0, query)
        self._apply_filter(); return self.visible_values()
    def _apply_filter(self):
        q = ""
        if self.popup_entry is not None:
            try: q = self.popup_entry.get()
            except Exception: q = ""
        self._filtered = self.filtered_values(q)
        lb = self.popup_listbox
        if lb is None: return
        lb.delete(0, tk.END)
        for v in self._filtered: lb.insert(tk.END, v)
        zebra_listbox(lb)
        if self.get() in self._filtered:
            idx = self._filtered.index(self.get()); lb.selection_set(idx); lb.activate(idx); lb.see(idx)
        elif self._filtered: lb.selection_set(0); lb.activate(0)
    def _on_control_key(self, event):
        """Printable key on the closed control: type-ahead open."""
        ch = getattr(event, "char", "") or ""
        if ch and ch.isprintable() and len(ch) == 1:
            self.open_popup()
            if self.popup_entry is not None:
                self.popup_entry.insert(tk.END, ch); self._apply_filter()
            return "break"
        return None
    def toggle_popup(self): self.close_popup() if self.popup is not None else self.open_popup()
    def open_popup(self):
        self.close_popup()
        if not self._values: return None
        th = current(); root = self.winfo_toplevel()
        win = tk.Toplevel(root); win.overrideredirect(True)
        win.configure(bg=field_border(is_dark()))
        body = tk.Frame(win, bg=th["panel"]); body.pack(fill="both", expand=True, padx=1, pady=1)
        top = tk.Frame(body, bg=th["panel"]); top.pack(fill="x", padx=4, pady=4)
        tk.Label(top, text=t("tpl_search", self.lang), bg=th["panel"], fg=th["text"], font=self._font_spec).pack(side="left", padx=(0, 4))
        self.popup_entry = RoundedEntry(top, font=self._font_spec)
        self.popup_entry.pack(side="left", fill="x", expand=True)
        self.popup_entry.bind("<KeyRelease>", lambda _e: self._apply_filter(), add="+"); self.popup_entry.bind("<Down>", self._entry_down, add="+"); self.popup_entry.bind("<Return>", lambda _e: self._pick_current(), add="+")
        list_fr = tk.Frame(body, bg=th["panel"]); list_fr.pack(fill="both", expand=True)
        rows = min(len(self._values), VISIBLE_ROWS)
        box = RoundedListbox(list_fr, height=rows, font=self._font_spec, bg=th["bg"], fg=th["text"])
        box.pack(side="left", fill="both", expand=True)
        lb = box.listbox; lb.configure(activestyle="none")
        scroll = tk.Scrollbar(list_fr, orient="vertical", command=lb.yview)
        scroll.pack(side="right", fill="y"); lb.configure(yscrollcommand=scroll.set)
        self.popup, self.popup_listbox = win, lb; self._apply_filter()
        fnt = tkfont.Font(root=self, font=self._font_spec); text_w = max(fnt.measure(v) for v in self._values)
        win.update_idletasks(); width = max(self.winfo_width(), text_w + scroll.winfo_reqwidth() + _PAD)
        height = max(win.winfo_reqheight(), 1); sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        x = min(max(self.winfo_rootx(), 0), max(sw - width - 2, 0)); y = self.winfo_rooty() + self.winfo_height()
        if y + height > sh: y = self.winfo_rooty() - height
        y = min(max(y, 0), max(sh - height, 0))
        win.geometry(f"{int(width)}x{int(height)}+{int(x)}+{int(y)}"); win.update_idletasks()
        self.popup_width, self.popup_visible_rows = int(width), rows
        lb.bind("<ButtonRelease-1>", self._pick_current, add="+"); lb.bind("<Double-Button-1>", self._pick_current, add="+")
        lb.bind("<Return>", self._pick_current, add="+"); lb.bind("<Escape>", lambda _e: self.close_popup(), add="+")
        win.bind("<Escape>", lambda _e: self.close_popup(), add="+")
        self._popup_root = root
        self._root_bind_id = root.bind("<Button-1>", self._on_root_click, add="+")
        self._esc_bind_id = win.bind_all("<Escape>", lambda _e: self.close_popup(), add="+")
        self.popup_entry.focus_force()  # typing filters at once
        return win
    def _entry_down(self, _e=None):
        if self.popup_listbox is not None:
            self.popup_listbox.focus_force()
            if self._filtered: self.popup_listbox.selection_set(0); self.popup_listbox.activate(0)
        return "break"
    def close_popup(self):
        if self._esc_bind_id:
            try: self.unbind_all("<Escape>", self._esc_bind_id)
            except Exception: pass
            self._esc_bind_id = None
        if self._popup_root is not None and self._root_bind_id:
            try: self._popup_root.unbind("<Button-1>", self._root_bind_id)
            except Exception: pass
        self._popup_root, self._root_bind_id = None, None
        if self.popup is not None:
            try: self.popup.destroy()
            except Exception: pass
        self.popup, self.popup_listbox, self.popup_entry = None, None, None
    def _on_root_click(self, event):
        if self.popup is None: return
        w = event.widget
        while w is not None:
            if w is self.popup or w is self: return
            w = getattr(w, "master", None)
        self.close_popup()  # click-outside: selection unchanged
    def _pick_current(self, _e=None):
        if self.popup_listbox is None: return
        sel = self.popup_listbox.curselection()
        if sel and sel[0] < len(self._filtered): self.select_value(self._filtered[sel[0]])
    def select_value(self, value):
        """Selection path: set var, close, fire <<ComboboxSelected>>."""
        self.set(value); self.close_popup()
        if self._on_select is not None: self._on_select()
        for handler in list(getattr(self, "_sel_handlers", [])): handler(None)
    def _on_destroy(self, event):
        if event.widget is self: self.close_popup()  # popup never outlives its host
