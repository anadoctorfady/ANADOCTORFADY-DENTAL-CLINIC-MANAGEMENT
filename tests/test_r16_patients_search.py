"""Round 16 worker A (patients): search-only list + advanced search.

Exercises the REAL App.load_patients() (via a stub holding the real
tree/search/panel attributes) and the REAL search_patients() model
helper. Helpers live in tests.test_r16_patients. Seeded rows are
cleaned up. GUI tests skip with no display; run with DISPLAY=:98
under Xvfb.
"""
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

from src.models.database import init_db
from src.models.patients import search_patients
from src.ui.patient_search import AdvancedSearchPanel
from src.ui.shell import App
from tests.test_r16_patients import _FakeApp, _cleanup, _row, _seed, _set


def _list_stub(root, current=None):
    tree = ttk.Treeview(root, columns=("file", "name", "mobile"),
                        show="headings")
    tree.pack()
    return SimpleNamespace(tree=tree, search_var=tk.StringVar(),
                           adv_search=None, current_patient=current)


def _tree_rows(stub):
    return [stub.tree.item(i, "values") for i in stub.tree.get_children()]


def test_list_empty_on_startup_until_search():
    """The real App.load_patients() with no criteria and no open
    patient shows NOTHING; with an open patient it shows only them;
    a quick-search query shows matches."""
    init_db()
    fid = _seed("R16List", "R16Dad", "R16Fam", m1="0791111111")
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        _cleanup(fid)
        print("SKIP test_list_empty_on_startup_until_search (no display)"); return
    try:
        stub = _list_stub(root)
        App.load_patients(stub)
        assert _tree_rows(stub) == [], "list loaded patients on startup"
        stub.current_patient = {"file_number": fid}
        App.load_patients(stub)
        rows = _tree_rows(stub)
        assert len(rows) == 1 and str(rows[0][0]) == str(fid), rows
        stub.current_patient = None
        stub.search_var.set("R16List")
        App.load_patients(stub)
        assert any(str(r[0]) == str(fid) for r in _tree_rows(stub)), _tree_rows(stub)
    finally:
        root.destroy(); _cleanup(fid)


def test_advanced_search_each_field():
    """Advanced search finds one patient by first / father / family /
    mobile1 / mobile2 / emergency phone, and ANDs criteria."""
    init_db()
    fid = _seed("R16Adv", "R16AdvDad", "R16AdvFam", m1="0791100011",
                m2="0792200022", em="0793300033")
    try:
        for kw in ({"first": "R16Adv"}, {"father": "R16AdvDad"},
                   {"family": "R16AdvFam"}, {"phone": "0791100011"},
                   {"phone": "0792200022"}, {"phone": "0793300033"},
                   {"first": "r16adv"}, {"phone": "92200022"}):
            got = [r["file_number"] for r in search_patients(**kw)]
            assert fid in got, (kw, got)
        assert fid not in [r["file_number"] for r in
                           search_patients(first="R16Adv", family="NoSuch")]
        assert fid not in [r["file_number"] for r in
                           search_patients(phone="0799999999")]
    finally:
        _cleanup(fid)


def test_advanced_search_panel_wires_into_list():
    """Typing into the real AdvancedSearchPanel and running the real
    App.load_patients() populates the tree; Clear empties it again."""
    init_db()
    fid = _seed("R16Pan", "R16Dad", "R16Fam", m2="0792200044")
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        _cleanup(fid)
        print("SKIP test_advanced_search_panel_wires_into_list (no display)"); return
    try:
        stub = _list_stub(root)
        panel = AdvancedSearchPanel(root, _FakeApp(),
                                    on_search=lambda: App.load_patients(stub))
        panel.pack(); stub.adv_search = panel; root.update_idletasks()
        App.load_patients(stub)
        assert _tree_rows(stub) == []
        _set(panel.e_phone, "0792200044")
        App.load_patients(stub)
        assert any(str(r[0]) == str(fid) for r in _tree_rows(stub)), _tree_rows(stub)
        panel.clear(); root.update_idletasks()
        assert _tree_rows(stub) == [], "Clear did not empty the list"
        assert panel.e_phone.get() == ""
    finally:
        root.destroy(); _cleanup(fid)
