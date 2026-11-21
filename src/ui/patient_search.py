"""Advanced patient search panel (round 16, worker A).

Sits in the shell's left column under the quick-search box: five
fields (first name, father's name, grandfather's name, family
name, ANY phone number) plus Search / Clear. Search matches
mobile1, mobile2 OR the emergency phone (format-tolerant since
round 18). Criteria are read by App.load_patients() via
get_criteria(); Clear empties the fields and re-runs the list
(which then shows only the open patient, or nothing).
"""
import tkinter as tk
from src.config.strings import t
from src.config.strings_r16_patients import tr as _tr16
from src.config.strings_r18_patients import tr as _tr18
from src.config.strings_r19_patients import tr as _tr19
from src.config.theme import current, mode, name_colors, debt_red, finance_tokens
from src.models.database import get_connection, init_db
from src.models.finance import patient_totals
from src.ui.rounded import rounded_button; from src.ui.zebra import zebra_tree
from src.ui.rounded_widgets import RoundedEntry


class AdvancedSearchPanel(tk.Frame):
    def __init__(self, parent, app, on_search, **kw):
        th = current()
        super().__init__(parent, bg=th["list_bg"], **kw)
        self.app = app; self.lang = getattr(app, "lang", "en")
        self._on_search = on_search
        tk.Label(self, text=_tr16("search.advanced", self.lang),
                 bg=th["list_bg"], fg=th["text"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 4))
        # Each entry lives INSIDE its label row (packing an entry
        # created with parent=self into the row would lay it out in
        # the panel instead -- the staircase bug seen in shot r16_01).
        for key, attr in (("search.first", "e_first"),
                          ("search.father", "e_father"),
                          ("search.grandfather", "e_grand"),
                          ("search.family", "e_family"),
                          ("search.phone", "e_phone")):
            row = tk.Frame(self, bg=th["list_bg"]); row.pack(fill="x", pady=1)
            tk.Label(row, text=_tr18(key, self.lang), bg=th["list_bg"],
                     fg=th["text"], font=("Segoe UI", 9),
                     width=14, anchor="w").pack(side="left")
            w = RoundedEntry(row, font=("Segoe UI", 9))
            w.pack(side="left", fill="x", expand=True)
            w.bind("<Return>", lambda e: self._on_search())
            setattr(self, attr, w)
        btns = tk.Frame(self, bg=th["list_bg"]); btns.pack(fill="x", pady=4)
        rounded_button(btns, text=_tr16("search.btn", self.lang),
                       bg=th["accent"], fg="white",
                       font=("Segoe UI", 9, "bold"), padx=14,
                       command=self._search_clicked).pack(side="left", padx=(0, 6))
        rounded_button(btns, text=_tr16("search.clear", self.lang),
                       bg=th["panel"], fg=th["text"],
                       font=("Segoe UI", 9), padx=14,
                       command=self.clear).pack(side="left")
        # Round 19 (R19-E): Debtors-only toggle. ON = the patient
        # list shows ONLY non-deleted patients whose remaining
        # balance (patient_totals, the one existing computation)
        # is > 0. OFF = the previous search/list behaviour exactly.
        self.debtors_only = False
        self.btn_debtors = rounded_button(
            self, text=_tr19("patients.debtors_only", self.lang),
            bg=th["panel"], fg=th["text"], font=("Segoe UI", 9), padx=14,
            command=self.toggle_debtors)
        self.btn_debtors.pack(fill="x", pady=(4, 0))
        self._wrap_load_patients()
        tk.Label(self, text=_tr16("search.hint", self.lang),
                 bg=th["list_bg"], fg=th["muted"],
                 font=("Segoe UI", 8), wraplength=340,
                 justify="left").pack(anchor="w", pady=(2, 0))

    def get_criteria(self):
        """Non-empty criteria as {first, father, grand, family, phone}."""
        out = {}
        for key, w in (("first", self.e_first), ("father", self.e_father),
                       ("grand", self.e_grand), ("family", self.e_family),
                       ("phone", self.e_phone)):
            v = w.get().strip()
            if v:
                out[key] = v
        return out

    def clear(self):
        """Empty all fields and refresh the list (open patient only)."""
        for w in (self.e_first, self.e_father, self.e_grand,
                  self.e_family, self.e_phone):
            w.delete(0, tk.END)
        self._search_clicked()

    # --- Round 19: debtors-only filter --------------------------------

    def _search_clicked(self):
        """Search/Clear path: normal refresh, then re-apply the
        debtors filter when the toggle is ON."""
        self._on_search()
        if self.debtors_only:
            self._fill_debtors()

    def _wrap_load_patients(self):
        """Wrap app.load_patients ONCE (the shell's own refreshes --
        quick-search typing, rebuilds -- call it directly, bypassing
        this panel) so an active debtors filter survives them. With
        the toggle OFF the wrapper is a pure pass-through, i.e. the
        previous behaviour byte-for-byte."""
        app = self.app
        if app is None or not hasattr(app, "load_patients"):
            return
        if getattr(app, "_load_patients_base", None) is not None:
            return  # already wrapped by an earlier panel (rebuild)
        app._load_patients_base = app.load_patients

        def _wrapped(*a, **k):
            app._load_patients_base(*a, **k)
            panel = getattr(app, "adv_search", None)
            if panel is not None and getattr(panel, "debtors_only", False):
                panel._fill_debtors()

        app.load_patients = _wrapped

    def debtor_rows(self):
        """Non-deleted patients whose remaining balance is > 0.
        The balance comes from patient_totals() -- the existing
        computation used by the clinical Cost section; no second
        balance formula is invented here."""
        init_db()
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT file_number, full_name, mobile1 FROM patients "
                    "WHERE COALESCE(deleted, 0)=0 ORDER BY file_number DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return [r for r in rows
                if patient_totals(r["file_number"])["remaining"] > 0]

    def _fill_debtors(self):
        """Replace the shell's patient tree content with debtors
        only (same row shape + rotating name colours as the shell)."""
        tree = getattr(self.app, "tree", None)
        if tree is None:
            return
        for i in tree.get_children():
            tree.delete(i)
        palette = name_colors(mode() == "dark")
        for idx, c in enumerate(palette):
            tree.tag_configure(f"name_{idx}", foreground=c,
                               font=("Segoe UI", 9, "bold"))
        # R21 item 1: every row here IS a debtor -> red name tag.
        tree.tag_configure("debt", foreground=debt_red(mode() == "dark"),
                           font=("Segoe UI", 9, "bold"))
        for i, r in enumerate(self.debtor_rows()):
            tree.insert("", "end", values=(r["file_number"], r["full_name"],
                                            r["mobile1"] or ""),
                        tags=(f"name_{i % len(palette)}", "debt"))
        zebra_tree(tree)  # R21 item 6

    def toggle_debtors(self):
        """Flip the toggle: ON fills the list with debtors only;
        OFF re-runs the normal search/list refresh exactly.
        Round 21 (item 4): the ON state uses the FINANCE accent /
        btn_text pair of the current mode -- white on the dark
        theme's accent (#D97736) was only ~2.9:1 and unreadable;
        the finance pair is >= 5.7:1 in both modes (asserted in
        tests/test_r21_debtors_btn.py)."""
        th = current()
        self.debtors_only = not self.debtors_only
        if self.debtors_only:
            fin = finance_tokens(mode() == "dark")
            self.btn_debtors.config(
                text=_tr19("patients.debtors_only_on", self.lang),
                bg=fin["accent"], fg=fin["btn_text"])
            self._fill_debtors()
        else:
            self.btn_debtors.config(
                text=_tr19("patients.debtors_only", self.lang),
                bg=th["panel"], fg=th["text"])
            self._on_search()
