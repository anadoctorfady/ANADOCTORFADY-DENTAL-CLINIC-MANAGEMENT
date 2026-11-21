"""Round 24, Item 5: expense category ICON picker replaces the
Finance-tab category dropdown. The picker is a drop-in for the old
RoundedCombobox: .get()/.set() with the STORED value always the exact
English literal ("Rent", ...), labels localized, default "Materials",
exactly one category selected at all times. GUI tests skip with no
display; exercised under Xvfb on the isolated DB copy."""
import tkinter as tk
from src.config.theme import finance_tokens
from src.ui.clinical_table_style import contrast_ratio
from src.ui.expense_icons import ExpenseIconPicker, VALUES

MARKER = "r24-icon-expense"


class _StubApp:
    current_user = "fady"
    current_role = "admin"
    current_patient = None
    finance_gate = None

    def __init__(self, lang="en"):
        self.lang = lang


def _root():
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw()
    return root


def _build_tab(lang="en"):
    """Unlocked admin FinanceTab, or (None, None) with no display."""
    from src.utils.finance_gate import FinanceGate
    root = _root()
    if root is None:
        return None, None
    app = _StubApp(lang)
    app.finance_gate = FinanceGate(verify_fn=lambda u, p: True)
    from src.ui.finance import FinanceTab
    tab = FinanceTab(tk.Frame(root), app)
    root.update_idletasks()
    tab.e_gate_user.delete(0, tk.END); tab.e_gate_user.insert(0, "fady")
    tab.e_gate_pass.delete(0, tk.END); tab.e_gate_pass.insert(0, "x")
    tab._try_unlock()
    assert tab.gate.is_unlocked, "stub gate should unlock"
    return tab, root


def _picker(root, lang="en", dark=False):
    th = finance_tokens(dark)
    host = tk.Frame(root, bg=th["panel"])
    host.pack()
    return ExpenseIconPicker(host, lang=lang, th=th)


def test_picker_defaults_and_clicks():
    root = _root()
    if root is None:
        print("SKIP test_picker_defaults_and_clicks (no display)")
        return
    try:
        p = _picker(root)
        root.update_idletasks()
        assert p.get() == "Materials"  # same default as the combobox
        assert set(p.buttons) == set(VALUES)
        for value in VALUES:
            p.buttons[value].invoke()
            root.update_idletasks()
            assert p.get() == value, (value, p.get())
    finally:
        root.destroy()


def test_picker_set_get_contract():
    root = _root()
    if root is None:
        print("SKIP test_picker_set_get_contract (no display)")
        return
    try:
        p = _picker(root)
        p.set("Rent")
        assert p.get() == "Rent"
        p.set("Other")
        assert p.get() == "Other"
        p.set("Bogus")  # unknown value: selection unchanged
        assert p.get() == "Other"
    finally:
        root.destroy()


def test_picker_exactly_one_selected_always():
    root = _root()
    if root is None:
        print("SKIP test_picker_exactly_one_selected_always (no display)")
        return
    try:
        th = finance_tokens(False)
        p = _picker(root)
        root.update_idletasks()
        for value in VALUES + ("Materials",):
            p.buttons[value].invoke()  # incl. re-clicking the selected
            root.update_idletasks()
            assert p.get() == value
            accented = [v for v, b in p.buttons.items()
                        if b._bg == th["accent"]]
            assert accented == [value], accented  # exactly one
            assert p.buttons[value]._fg == th["btn_text"]
            assert "bold" in str(p.buttons[value]._font)
            for other, b in p.buttons.items():
                if other != value:
                    assert b._bg == th["card"] and b._fg == th["text"]
    finally:
        root.destroy()


def test_picker_contrast_both_themes():
    """Selected (btn_text on accent) and unselected (text on card)
    label pairs are >= 4.5:1 in BOTH finance themes."""
    for dark in (False, True):
        th = finance_tokens(dark)
        assert contrast_ratio(th["btn_text"], th["accent"]) >= 4.5, dark
        assert contrast_ratio(th["text"], th["card"]) >= 4.5, dark


def test_picker_arabic_labels_english_values():
    root = _root()
    if root is None:
        print("SKIP test_picker_arabic_labels_english_values (no display)")
        return
    try:
        p = _picker(root, lang="ar")
        root.update_idletasks()
        assert p.labels["Rent"] == "إيجار"
        assert p.labels["Salary"] == "راتب"
        for value in VALUES:
            text = p.buttons[value]._text
            assert p.labels[value] in text, (value, text)
            assert value not in text.replace(p.labels[value], ""), text
        p.buttons["Rent"].invoke()
        assert p.get() == "Rent"  # stored value stays English
    finally:
        root.destroy()


def test_finance_tab_add_exp_stores_english_category():
    """End to end: unlocked admin tab, click the Rent icon, Add ->
    the expenses row's category is byte-identical 'Rent'."""
    from src.models.database import get_connection
    tab, root = _build_tab()
    if tab is None:
        print("SKIP test_finance_tab_add_exp_stores (no display)")
        return
    try:
        assert isinstance(tab.e_exp_cat, ExpenseIconPicker)
        assert tab.e_exp_cat.get() == "Materials"
        tab.e_exp_cat.buttons["Rent"].invoke()
        assert tab.e_exp_cat.get() == "Rent"
        tab.e_exp_desc.delete(0, tk.END); tab.e_exp_desc.insert(0, MARKER)
        tab.e_exp_amt.delete(0, tk.END); tab.e_exp_amt.insert(0, "12345")
        tab.add_exp()
        root.update_idletasks()
        conn = get_connection()
        row = conn.execute("SELECT category, amount FROM expenses "
                           "WHERE description=?", (MARKER,)).fetchone()
        conn.close()
        assert row is not None, "expense row not saved"
        assert row[0] == "Rent" and float(row[1]) == 12345.0
        shown = [tab.tree_exp.item(i, "values") for i in
                 tab.tree_exp.get_children()]
        assert any(v[1] == "Rent" and v[2] == MARKER for v in shown)
    finally:
        try: root.destroy()
        except Exception: pass
        conn = get_connection()
        conn.execute("DELETE FROM expenses WHERE description=?", (MARKER,))
        conn.commit(); conn.close()


def test_finance_tab_arabic_build_still_stores_english():
    tab, root = _build_tab(lang="ar")
    if tab is None:
        print("SKIP test_finance_tab_arabic_build (no display)")
        return
    try:
        assert tab.e_exp_cat.labels["Materials"] == "مواد"
        assert tab.e_exp_cat.get() == "Materials"
        tab.e_exp_cat.set("Salary")
        assert tab.e_exp_cat.get() == "Salary"
    finally:
        root.destroy()
