"""Rounded corners for EVERYTHING (Round 13, Item 2) - STATIC
checks: no square widget construction left in src/ui, every
Treeview wrapped or pinned, no LabelFrame left anywhere (the
Settings rename frame was the last one; round-13 final integration
rounded it too - the title lives on the RoundedFrame shell, so
refresh_role_sections() destroying .inner children is safe).
GUI checks live in tests/test_rounded_all.py.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "src" / "ui"


def _src(name):
    return (UI / name).read_text()


def test_no_square_fields_left_static():
    """No bare tk.Entry / tk.Text / tk.Listbox / ttk.Combobox /
    tk.Button construction left in src/ui (the wrappers build the
    real widgets themselves, in rounded_widgets.py / rounded_lists.py
    / rounded.py). SearchableCombobox (utils) and the guide's
    ScrolledText are the only other square text widgets, by design."""
    allowed = {"rounded.py", "rounded_widgets.py", "rounded_lists.py"}
    for path in sorted(UI.glob("*.py")):
        if path.name in allowed:
            continue
        src = path.read_text()
        for pat in ("tk.Entry(", "tk.Text(", "tk.Listbox(",
                    "ttk.Combobox(", "tk.Button("):
            assert pat not in src, f"{path.name}: square {pat} remains"


def test_trees_wrapped_or_pinned_static():
    """Every ttk.Treeview is either built by rounded_tree, a child of
    a RoundedFrame (.inner), or the ONE pinned exception: the scans
    tree, which tests/test_scans_upload.py requires as a direct
    child of its section frame."""
    for path in sorted(UI.glob("*.py")):
        if path.name in ("rounded_lists.py",):
            continue
        for i, line in enumerate(path.read_text().splitlines(), 1):
            if "ttk.Treeview(" not in line:
                continue
            ok = ("rounded_tree(" in line or ".inner" in line
                  or (path.name == "scans_tab.py")
                  # appointments.py: `frm` IS the RoundedFrame inner
                  # (reassigned from frm.inner two lines above _table).
                  or (path.name == "appointments.py" and "(frm," in line))
            assert ok, f"{path.name}:{i}: unwrapped Treeview: {line.strip()}"


def test_no_label_frames_left_static():
    """No tk.LabelFrame( anywhere in src/ui: the last one (Settings
    rename frame) was rounded in the round-13 final integration by
    keeping the RoundedFrame shell and pointing self.rn at its
    .inner - refresh_role_sections() destroys only .inner children,
    so the title label on the shell survives the rebuild."""
    for path in sorted(UI.glob("*.py")):
        n = path.read_text().count("tk.LabelFrame(")
        assert n == 0, f"{path.name}: {n} LabelFrame(s) remain"


def test_rounded_used_by_tabs_and_dialogs_static():
    for name, needle in (
            ("finance_views.py", "rounded_tree"),
            ("salaries_view.py", "rounded_tree"),
            ("users_tab.py", "rounded_tree"),
            ("prescriptions.py", "rounded_tree"),
            ("attendance_view.py", "rounded_tree"),
            ("clinical_tables.py", "RoundedText"),
            ("clinical_finance.py", "RoundedEntry"),
            ("appointments.py", "RoundedListbox"),
            ("template_manager.py", "RoundedListbox"),
            ("phrase_picker.py", "RoundedListbox")):  # R21 item 5: notes_tab.py deleted (was the RoundedText pair)
        assert needle in _src(name), f"{name}: no {needle}"
