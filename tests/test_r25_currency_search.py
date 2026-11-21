"""Round 25 item 5: currency selection has real search.
Before: SearchableCombobox filtered its values on <KeyRelease>
but NEVER opened the popdown (typed = no visible results); the
Finance selector + doctor overlay were readonly (no typing at
all). Now every currency control is ui.currency_picker.
CurrencyPicker: click opens a popup whose filter entry has
focus, typing narrows the VISIBLE list (code / EN / AR name via
filter_list; Finance filters its All + present-codes strings),
picking sets the host variable exactly as before (display ->
code_for(); bare code / All label on the Finance tab). Pinned
ranking (exact, starts-with, contains): 'eu' -> EUR first;
'\u064a\u0648\u0631\u0648' -> EUR only; 'd' -> DJF first, D-codes lead.
GUI tests skip gracefully with no display."""
import tkinter as tk
from types import SimpleNamespace

from src.utils.currencies import code_for, display_for_code

def _root():
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw()
    return root

def _pick(picker, display, root):
    """Pick `display` from the picker's open popup via its listbox,
    the way a mouse click does."""
    vis = picker.visible_values(); assert display in vis, (display, vis[:8])
    idx = vis.index(display)
    lb = picker.popup_listbox; lb.selection_clear(0, tk.END); lb.selection_set(idx); lb.activate(idx)
    picker._pick_current()
    root.update_idletasks()
    assert picker.popup is None, "picking did not close the popup"

def _type(picker, text, root):
    """Type into the popup's filter entry (real KeyRelease path)."""
    if picker.popup is None: picker.open_popup()
    entry = picker.popup_entry.widget  # RoundedEntry's inner Entry
    entry.focus_force(); root.update_idletasks()  # keys need settled focus
    entry.delete(0, tk.END); entry.insert(0, text)
    entry.event_generate("<KeyRelease>", when="now")
    root.update_idletasks()
    return picker.visible_values()

def _clinical(root, lang="en"):
    from src.ui.clinical import ClinicalTab
    from tests.test_clinical_save_gate import _stub_app
    tab = ClinicalTab(root, _stub_app(lang=lang)); root.update_idletasks(); return tab

def _finance_tab(root):
    from src.utils.finance_gate import FinanceGate

    class _StubApp:
        current_user = "fady"; current_role = "admin"
        current_patient = None; finance_gate = None; lang = "en"

    app = _StubApp(); app.finance_gate = FinanceGate(verify_fn=lambda u, p: True)
    from src.ui.finance import FinanceTab
    tab = FinanceTab(tk.Frame(root), app); root.update_idletasks()
    tab.e_gate_user.delete(0, tk.END); tab.e_gate_user.insert(0, "fady")
    tab.e_gate_pass.delete(0, tk.END); tab.e_gate_pass.insert(0, "x")
    tab._try_unlock(); root.update_idletasks()
    return tab

def test_clinical_currency_search_en():
    root = _root()
    if root is None:
        print("SKIP clinical currency search (no display)"); return
    try:
        tab = _clinical(root, "en")
        eur = display_for_code("EUR", "en")
        vis = _type(tab.cb_cur, "eu", root)
        assert eur in vis and vis[0] == eur, vis[:5]
        _pick(tab.cb_cur, eur, root)
        assert tab.cur_var.get() == eur
        assert tab.cur_code() == "EUR" and code_for(tab.cur_var.get()) == "EUR"
        # Arabic name finds EUR even in the EN display list (data-level).
        vis = tab.cb_cur.set_filter("يورو")
        assert vis == [eur], vis
        tab.cb_cur.close_popup()
        # First letter: D-currencies lead the visible list.
        vis = tab.cb_cur.set_filter("d")
        codes = [v.split(" - ")[0] for v in vis]
        assert codes[0] == "DJF", codes[:5]
        assert all(c.startswith("D") for c in codes[:4]), codes[:6]
        assert "DZD" in codes and "DKK" in codes
        tab.cb_cur.close_popup()
    finally:
        root.destroy()

def test_clinical_currency_search_ar():
    root = _root()
    if root is None:
        print("SKIP clinical currency search AR (no display)"); return
    try:
        tab = _clinical(root, "ar")
        eur = display_for_code("EUR", "ar")
        assert "يورو" in eur, eur
        vis = _type(tab.cb_cur, "يورو", root)
        assert vis == [eur], vis
        _pick(tab.cb_cur, eur, root)
        assert tab.cur_code() == "EUR"
    finally:
        root.destroy()

def test_finance_selector_search_and_all():
    root = _root()
    if root is None:
        print("SKIP finance selector search (no display)"); return
    try:
        from src.ui.finance_currency import refresh_currency_selector, selected_currency
        tab = _finance_tab(root)
        refresh_currency_selector(tab); root.update_idletasks()
        # The selector is no longer readonly: typing filters visibly.
        assert tab._cur_all_label in tab.cb_fin_cur.values
        vis = _type(tab.cb_fin_cur, "eu", root)
        assert all("eu" in v.lower() for v in vis), vis
        if "EUR" in tab.cb_fin_cur.values:  # EUR present only if seeded
            assert "EUR" in vis
            _pick(tab.cb_fin_cur, "EUR", root)
            assert selected_currency(tab) == "EUR"
        else:
            tab.cb_fin_cur.close_popup()
        # The 'All currencies' pseudo-entry stays selectable.
        vis = tab.cb_fin_cur.set_filter("")
        assert tab._cur_all_label in vis
        _pick(tab.cb_fin_cur, tab._cur_all_label, root)
        assert selected_currency(tab) is None
        # Doctor overlay shares the variable and is searchable too.
        assert tab.cb_doc_cur.get() == tab._cur_all_label
        vis = tab.cb_doc_cur.set_filter("eu")
        assert all("eu" in v.lower() for v in vis), vis
        tab.cb_doc_cur.close_popup()
    finally:
        root.destroy()

def test_finance_selector_eur_when_seeded():
    from tests.test_r21_finance_currencies import _setup, _teardown
    root = _root()
    if root is None:
        print("SKIP finance selector EUR (no display)"); return
    fid = _setup()
    try:
        from src.ui.finance_currency import refresh_currency_selector, selected_currency
        tab = _finance_tab(root)
        refresh_currency_selector(tab); root.update_idletasks()
        assert "EUR" in tab.cb_fin_cur.values
        vis = _type(tab.cb_fin_cur, "eu", root)
        assert "EUR" in vis, vis
        _pick(tab.cb_fin_cur, "EUR", root)
        assert tab.cur_var.get() == "EUR"
        assert selected_currency(tab) == "EUR"
    finally:
        _teardown(fid)
        root.destroy()

def test_rate_picker_search():
    root = _root()
    if root is None:
        print("SKIP rate picker search (no display)"); return
    try:
        tab = _finance_tab(root)
        eur = display_for_code("EUR", "en")
        vals = list(tab.cb_rate_from["values"])
        assert len(vals) >= 170 and eur in vals
        vis = _type(tab.cb_rate_from, "eu", root)
        assert eur in vis and vis[0] == eur, vis[:5]
        _pick(tab.cb_rate_from, eur, root)
        assert tab.rate_from_var.get() == eur
        assert tab.rate_from_code() == "EUR"
        vis = tab.cb_rate_from.set_filter("يورو")
        assert vis == [eur], vis
        tab.cb_rate_from.close_popup()
    finally:
        root.destroy()

def test_settings_currency_search():
    root = _root()
    if root is None:
        print("SKIP settings currency search (no display)"); return
    try:
        from src.ui.settings_ui import SettingsTab
        app = SimpleNamespace(lang="en", print_pdf=lambda bilingual=False: None, _rebuild=lambda: None)
        tab = SettingsTab(root, app)
        tab.pack(fill="both", expand=True); root.update_idletasks()
        eur = display_for_code("EUR", "en")
        vis = _type(tab.cb_cur, "eu", root)
        assert eur in vis and vis[0] == eur, vis[:5]
        _pick(tab.cb_cur, eur, root)
        assert tab.cur_var.get() == eur
        assert code_for(tab.cur_var.get()) == "EUR"
        vis = tab.cb_cur.set_filter("d")
        codes = [v.split(" - ")[0] for v in vis]
        assert codes[0] == "DJF" and "DZD" in codes, codes[:6]
        tab.cb_cur.close_popup()
    finally:
        root.destroy()
