"""Searchable dropdown: type to filter by code / EN / AR name. <80 lines."""
import tkinter as tk
from tkinter import ttk

def filter_list(items, query, fields):
    """Case-insensitive substring match on any of fields (dict keys).
    Ranked: exact match first, then starts-with, then contains — so
    'سوري' finds Syrian (SY) before Surinamese (SR, 'سورينامي')."""
    q = (query or "").strip().lower()
    if not q:
        return list(items)
    scored = []
    for it in items:
        vals = [str(it.get(f, "") or "").lower() for f in fields]
        if any(v == q for v in vals):
            scored.append((0, it))
        elif any(v.startswith(q) for v in vals):
            scored.append((1, it))
        elif any(q in v for v in vals):
            scored.append((2, it))
    return [it for _s, it in sorted(scored, key=lambda t: t[0])]

class SearchableCombobox(ttk.Combobox):
    """ttk.Combobox whose values filter live as you type.
    items: list of dicts; display_fn(item) -> shown string."""
    def __init__(self, parent, items, display_fn, textvariable=None, **kw):
        self._items = list(items)
        self._display_fn = display_fn
        self._all = [display_fn(i) for i in self._items]
        kw.setdefault("values", self._all)
        super().__init__(parent, textvariable=textvariable, **kw)
        self.bind("<KeyRelease>", self._on_key, add="+")
        self.bind("<<ComboboxSelected>>", self._on_select, add="+")
        self.bind("<FocusIn>", lambda _e: self._set_values(self._all), add="+")

    def _set_values(self, values):
        try:
            self["values"] = values
        except Exception:
            pass

    def _on_key(self, _e=None):
        q = self.get()
        hits = filter_list(self._items, q, self._fields()) if hasattr(self, "_fields") else None
        if hits is None:
            hits = [i for i, d in zip(self._items, self._all) if q.lower() in d.lower()] if q else list(self._items)
        self._set_values([self._display_fn(i) for i in hits])

    def _fields(self):
        return list(self._items[0].keys()) if self._items else []

    def _on_select(self, _e=None):
        self._set_values(self._all)
