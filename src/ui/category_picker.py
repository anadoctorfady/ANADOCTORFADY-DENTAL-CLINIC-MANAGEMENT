"""Round 24 item 9: medication-category picker for the Rx form.

Replaces the stock combobox whose dropdown was CLIPPED: its popdown
measured 169px wide (listbox 152px) against a 179px required width /
162px listbox requirement, and showed only 10 of the 36 values
("All" + 35 categories), so long names such as "Immunosuppressant"
were cut off mid-word -- worst in the narrow (~370px) shell Rx
column and under Windows DPI scaling. Contract (identical to the
old combobox's, see rx_form.py): the bound StringVar (tab.cat_var)
holds the selection; values are exactly categories(); picking one
sets the variable and fires the <<ComboboxSelected>> handlers
(tab.on_category re-filters the drugs); .get()/.set()/["values"]
behave as the combobox's did (.set() alone fires nothing).
The control is a read-only rounded display (value + arrow); its
popup Toplevel is sized from the LONGEST value's measured text
width + scrollbar + padding -- independent of the host column --
with min(len, 18) visible rows, positioned under the control and
clamped/flipped fully on screen. Esc and click-outside close it
without changing the selection. The list is a RoundedListbox."""
import tkinter as tk
from tkinter import font as tkfont
from src.config.theme import current, field_border, is_dark
from src.ui.rounded_widgets import _RoundedBorder
from src.ui.rounded_lists import RoundedListbox
from src.ui.zebra import zebra_listbox
VISIBLE_ROWS = 18
_FONT = ("Segoe UI", 10)
_PAD = 40  # list insets + rounded wrapper pads + border + slack


class CategoryPicker(_RoundedBorder):
    """Read-only category display + full-list popup picker."""

    def __init__(self, parent, textvariable=None, values=None,
                 width=None, on_select=None, font=None, **kw):
        th = current()
        self._values = list(values or []); self._var = textvariable
        self._on_select = on_select; self._font_spec = font or _FONT
        self._sel_handlers = []
        self.popup = None; self.popup_listbox = None
        self.popup_width = 0; self.popup_visible_rows = 0
        self._popup_root = None; self._root_bind_id = None; self._esc_bind_id = None
        super().__init__(parent, field_bg=th["panel"], **kw)
        inner = tk.Frame(self, bg=self._field_bg)
        self._label = tk.Label(inner, textvariable=textvariable, bg=self._field_bg,
            fg=th["text"], font=self._font_spec, anchor="w", cursor="hand2")
        if width is not None:
            self._label.configure(width=width)
        self._label.pack(side="left", fill="x", expand=True)
        self._arrow = tk.Label(inner, text="▾", bg=self._field_bg, fg=th["text"],
            font=self._font_spec, cursor="hand2")
        self._arrow.pack(side="right")
        self.widget = self._attach(inner)
        inner.configure(takefocus=1)
        self._click_parts = (inner, self._label, self._arrow)
        for w in self._click_parts:
            w.bind("<Button-1>", lambda _e: self.toggle_popup(), add="+")
            w.bind("<Down>", lambda _e: self.open_popup(), add="+")
            w.bind("<Return>", lambda _e: self.open_popup(), add="+")
            w.bind("<space>", lambda _e: self.open_popup(), add="+")
        tk.Frame.bind(self, "<Destroy>", self._on_destroy, add="+")

    @property
    def values(self):
        return list(self._values)

    @values.setter
    def values(self, vals):
        self._values = list(vals or [])

    def get(self):
        return self._var.get() if self._var is not None else self._label.cget("text")

    def set(self, value):
        if self._var is not None: self._var.set(value)
        else: self._label.configure(text=value)

    def cget(self, key):
        if key == "values": return tuple(self._values)
        if key == "textvariable": return str(self._var) if self._var is not None else ""
        return super().cget(key)

    def configure(self, cnf=None, **kw):
        merged = dict(cnf) if isinstance(cnf, dict) else {}
        merged.update(kw)
        if "values" in merged:
            self._values = list(merged.pop("values") or [])
        if "textvariable" in merged:
            self._var = merged.pop("textvariable")
            self._label.configure(textvariable=self._var)
        return super().configure(merged) if merged else None

    config = configure

    def bind(self, sequence=None, func=None, add=None):
        """<<ComboboxSelected>> handlers are stored and fired by
        select_value(); other sequences bind on the frame AND its
        clickable parts (a click lands on the label, not the frame)."""
        if func is None: return tk.Frame.bind(self, sequence)
        if sequence == "<<ComboboxSelected>>":
            self.__dict__.setdefault("_sel_handlers", []).append(func)
            return ""
        result = tk.Frame.bind(self, sequence, func, add)
        for w in getattr(self, "_click_parts", ()):
            try: w.bind(sequence, func, add)
            except Exception: pass
        return result

    def toggle_popup(self):
        self.close_popup() if self.popup is not None else self.open_popup()

    def open_popup(self):
        self.close_popup()
        values = list(self._values)
        if not values: return None
        th = current(); root = self.winfo_toplevel()
        win = tk.Toplevel(root); win.overrideredirect(True)
        win.configure(bg=field_border(is_dark()))
        body = tk.Frame(win, bg=th["panel"])
        body.pack(fill="both", expand=True, padx=1, pady=1)
        rows = min(len(values), VISIBLE_ROWS)
        box = RoundedListbox(body, height=rows, font=self._font_spec,
                             bg=th["bg"], fg=th["text"])
        box.pack(side="left", fill="both", expand=True)
        lb = box.listbox; lb.configure(activestyle="none")
        scroll = tk.Scrollbar(body, orient="vertical", command=lb.yview)
        scroll.pack(side="right", fill="y")
        lb.configure(yscrollcommand=scroll.set)
        for v in values: lb.insert(tk.END, v)
        zebra_listbox(box)
        if self.get() in values:
            idx = values.index(self.get())
            lb.selection_set(idx); lb.activate(idx); lb.see(idx)
        fnt = tkfont.Font(root=self, font=self._font_spec)
        text_w = max(fnt.measure(v) for v in values)
        win.update_idletasks()
        width = max(self.winfo_width(), text_w + scroll.winfo_reqwidth() + _PAD)
        height = max(win.winfo_reqheight(), 1)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        x = min(max(self.winfo_rootx(), 0), max(sw - width - 2, 0))
        y = self.winfo_rooty() + self.winfo_height()
        if y + height > sh:
            y = self.winfo_rooty() - height
        y = min(max(y, 0), max(sh - height, 0))
        win.geometry(f"{int(width)}x{int(height)}+{int(x)}+{int(y)}")
        win.update_idletasks()
        self.popup, self.popup_listbox = win, lb
        self.popup_width, self.popup_visible_rows = int(width), rows
        lb.bind("<ButtonRelease-1>", self._pick_current, add="+")
        lb.bind("<Double-Button-1>", self._pick_current, add="+")
        lb.bind("<Return>", self._pick_current, add="+")
        lb.bind("<Escape>", lambda _e: self.close_popup(), add="+")
        win.bind("<Escape>", lambda _e: self.close_popup(), add="+")
        self._popup_root = root
        self._root_bind_id = root.bind("<Button-1>", self._on_root_click, add="+")
        self._esc_bind_id = win.bind_all("<Escape>", lambda _e: self.close_popup(), add="+")
        lb.focus_force()  # popdown takes keyboard focus, as a combobox's does
        return win

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
        self.popup, self.popup_listbox = None, None

    def _on_root_click(self, event):
        """Click-outside: a Button-1 whose widget is neither the popup
        nor this control closes the popup, selection unchanged."""
        if self.popup is None: return
        w = event.widget
        while w is not None:
            if w is self.popup or w is self:
                return
            w = getattr(w, "master", None)
        self.close_popup()

    def _pick_current(self, _e=None):
        if self.popup_listbox is None: return
        sel = self.popup_listbox.curselection()
        if sel: self.select_value(self._values[sel[0]])

    def select_value(self, value):
        """The selection path: set the variable, close, then fire the
        same handlers the combobox's <<ComboboxSelected>> did."""
        self.set(value); self.close_popup()
        if self._on_select is not None:
            self._on_select()
        for handler in list(getattr(self, "_sel_handlers", [])):
            handler(None)

    def _on_destroy(self, event):
        if event.widget is self: self.close_popup()
