"""Round 31, Item 4: Finance expense-picker selection unreadable.

ROOT CAUSE (reproduced + pixel-measured before the fix):
RoundedButton.configure() popped fg/font into _fg/_font but
never forwarded them to the tk.Button, and _sync() re-applied
only text+image -- so restyling changed the PIL background but
the label kept its CONSTRUCTION colour. The selected expense
chip therefore rendered the UNSELECTED fg on the selected bg:
light #2C241D on #7A3F16 = 1.85:1, dark #F5F0EB on #E07B39 =
2.63:1 (screenshot pixel samples, round-31 shots 80/81), while
the documented pairs (8.23:1 / 5.73:1) never reached the screen.

Fix: rounded.py _sync() re-applies fg/font/activeforeground on
every configure; the picker selects with the finance sel pair
(light = accent/btn_text, 8.23:1; dark = vivid amber #F59E0B +
#241A12, 7.94:1 -- the dark accent caps at 5.73:1 with any fg).

Audit of the other Finance selection states (round 31, all
measured from the configured/rendered pairs, no fix needed):
ttk Treeview selected = clam default #FFFFFF on #4A6984 =
5.76:1; Listbox selected (incl. the CurrencyPicker popup) =
#000000 on #C3C3C3 = 11.91:1; Notebook selected tab = accent
on panel = 5.89:1 light / 5.09:1 dark. GUI parts skip with no
display."""
import tkinter as tk
from tkinter import ttk

from src.config.theme import finance_tokens
from src.ui.clinical_table_style import contrast_ratio
from src.ui.expense_icons import ExpenseIconPicker, VALUES


def _root():
    try:
        root = tk.Tk()
    except tk.TclError:
        return None
    root.withdraw()
    return root


def _picker(root, dark):
    th = finance_tokens(dark)
    host = tk.Frame(root, bg=th["panel"]); host.pack()
    return ExpenseIconPicker(host, lang="en", th=th), th


def test_selected_pair_ratios_both_themes():
    """Configured sel pair >= 4.5:1 (target ~7:1) in BOTH themes;
    the pre-R31 finance pairs are untouched and still pass."""
    for dark in (False, True):
        th = finance_tokens(dark)
        r = contrast_ratio(th["sel_fg"], th["sel_bg"])
        assert r >= 7.0, (dark, r)  # light 8.23, dark 7.94
        assert contrast_ratio(th["btn_text"], th["accent"]) >= 4.5
        assert contrast_ratio(th["text"], th["card"]) >= 4.5


def test_rounded_button_configure_applies_fg_and_font():
    """The R31 regression itself: configure(fg/font) must reach
    the widget (cget), not only the _fg/_font internals."""
    root = _root()
    if root is None:
        print("SKIP r31 rounded fg (no display)"); return
    try:
        from src.ui.rounded import rounded_button
        b = rounded_button(root, text="X", bg="#EFE7D8", fg="#2C241D",
                           font=("Segoe UI", 9))
        b.pack(); root.update_idletasks()
        b.configure(bg="#7A3F16", fg="#FFFFFF", font=("Segoe UI", 9, "bold"))
        root.update_idletasks()
        assert b._fg == "#FFFFFF" and b._bg == "#7A3F16"
        assert str(b.cget("fg")).upper() == "#FFFFFF", b.cget("fg")
        assert "bold" in str(b.cget("font")), b.cget("font")
    finally:
        root.destroy()


def test_picker_selected_chip_widget_colours_both_themes():
    root = _root()
    if root is None:
        print("SKIP r31 picker colours (no display)"); return
    try:
        for dark in (False, True):
            p, th = _picker(root, dark)
            root.update_idletasks()
            for value in VALUES:
                p.set(value)
                root.update_idletasks()
                btn = p.buttons[value]
                assert btn._bg == th["sel_bg"] and btn._fg == th["sel_fg"]
                # Widget-level (what Tk actually draws):
                assert str(btn.cget("fg")).upper() == th["sel_fg"].upper(), \
                    (dark, value, btn.cget("fg"))
                assert "bold" in str(btn.cget("font")), (dark, value)
                for other, ob in p.buttons.items():
                    if other != value:
                        assert ob._bg == th["card"]
                        assert str(ob.cget("fg")).upper() == th["text"].upper()
            p.destroy()
    finally:
        root.destroy()


def test_picker_get_set_contract_unchanged():
    root = _root()
    if root is None:
        print("SKIP r31 picker contract (no display)"); return
    try:
        p, _th = _picker(root, False)
        assert p.get() == "Materials"  # stored English literal
        p.set("Rent"); assert p.get() == "Rent"
        p.set("Bogus"); assert p.get() == "Rent"  # unknown ignored
        p.buttons["Salary"].invoke(); assert p.get() == "Salary"
    finally:
        root.destroy()


def test_audit_treeview_and_listbox_selection_pairs():
    """The other Finance selection states, pinned at their
    measured configured pairs (see header): all >= 4.5:1."""
    root = _root()
    if root is None:
        print("SKIP r31 selection audit (no display)"); return
    try:
        from src.config.theme import tree_style
        from src.ui.rounded_lists import RoundedListbox
        for dark in (False, True):
            th = finance_tokens(dark)
            st = ttk.Style(root)
            try: st.theme_use("clam")
            except Exception: pass
            name = tree_style("Finance", th)
            sbg = st.lookup(name, "background", ["selected"])
            sfg = st.lookup(name, "foreground", ["selected"])
            assert contrast_ratio(sfg, sbg) >= 4.5, (dark, sfg, sbg)
            lbw = RoundedListbox(root, height=2); lb = lbw.listbox
            def _hex(c):
                r, g, b = lb.winfo_rgb(str(c))
                return "#%02X%02X%02X" % (r >> 8, g >> 8, b >> 8)
            pair = (_hex(lb.cget("selectforeground")),
                    _hex(lb.cget("selectbackground")))
            assert contrast_ratio(*pair) >= 4.5, (dark, pair)
            lbw.destroy()
    finally:
        root.destroy()
