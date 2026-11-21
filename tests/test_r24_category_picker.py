"""Round 24 item 9: the Rx medication-CATEGORY list was clipped.

The old category control was a stock combobox: its dropdown
popdown measured 169px wide (listbox 152px) against a 179px
required width / 162px listbox requirement, and it showed only
10 of the 36 values ("All" + 35 categories), so long names such
as "Immunosuppressant" were cut off mid-word -- worst in the
narrow (~370px) shell Rx column and under Windows DPI scaling.

Now src/ui/category_picker.py CategoryPicker replaces it:
- cat_var still holds the selection and picking a value fires
  the same <<ComboboxSelected>> path (on_category re-filters
  the drug list); values are exactly categories();
- the popup lists ALL 36 values, shows >=15 rows at once, is
  wide enough for the longest name (measured text width <=
  listbox width), stays fully on screen, and Esc / click-outside
  close it without changing the selection.

GUI tests skip gracefully with no display; run with
DISPLAY=:104 against the isolated copy
(ANADOCTORFADY_DATA_DIR=/tmp/r24_cat).
"""
import tkinter as tk
from tkinter import font as tkfont

from src.models.database import set_setting
from src.ui.prescriptions import PrescriptionsTab
from src.utils.medications import categories, display, list_by_category
from tests.test_clinical_save_gate import _stub_app


def test_categories_contract():
    cats = categories()
    assert len(cats) == 36 and cats[0] == "All"
    assert cats[-1] == "Vitamin"
    assert "Immunosuppressant" in cats  # the clipped 17-char name


def _build(lang, narrow):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.geometry("1380x900")
    set_setting("language", lang)
    try:
        rx = PrescriptionsTab(root, _stub_app({"file_number": 0},
                                              lang=lang),
                              narrow=narrow)
        rx.pack(fill="both", expand=True)
        root.update_idletasks(); root.update()
        return root, rx
    except Exception:
        root.destroy()
        raise


def _open(root, rx):
    """Open the popup by clicking the control's label, as a user
    would, and return the popup's inner listbox."""
    rx.cb_cat._label.event_generate("<Button-1>")
    root.update_idletasks(); root.update()
    assert rx.cb_cat.popup is not None
    return rx.cb_cat.popup_listbox


def _pick(root, rx, lb, idx):
    lb.selection_clear(0, tk.END)
    lb.selection_set(idx)
    lb.activate(idx)
    lb.see(idx)
    rx.cb_cat._pick_current()  # the <ButtonRelease-1> handler
    root.update_idletasks(); root.update()


def _check(root, rx, lang):
    cats = categories()
    assert list(rx.cb_cat.values) == cats
    assert list(rx.cb_cat["values"]) == cats
    assert rx.cat_var.get() == "All"
    lb = _open(root, rx)
    try:
        # ALL 36 values, in order, in the popup list.
        assert lb.size() == 36
        assert [lb.get(i) for i in range(lb.size())] == cats
        # >=15 visible rows, and the view can reach the very end.
        assert int(lb.cget("height")) >= 15, lb.cget("height")
        assert rx.cb_cat.popup_visible_rows >= 15
        lb.yview_moveto(1.0); root.update()
        assert lb.yview()[1] == 1.0, lb.yview()
        lb.yview_moveto(0.0); root.update()
        # No clipping: the longest name's measured text fits the
        # listbox's actual pixel width; popup fully on screen.
        fnt = tkfont.Font(root=root, font=("Segoe UI", 10))
        longest = max(fnt.measure(c) for c in cats)
        assert longest <= lb.winfo_width(), (longest, lb.winfo_width())
        win = rx.cb_cat.popup
        assert win.winfo_rootx() >= 0 and win.winfo_rooty() >= 0
        assert win.winfo_rootx() + win.winfo_width() \
            <= win.winfo_screenwidth()
        assert win.winfo_rooty() + win.winfo_height() \
            <= win.winfo_screenheight()
        # First, a middle and the LAST category are each
        # selectable, land in cat_var and re-filter the drugs.
        for idx in (0, len(cats) // 2, len(cats) - 1):
            if rx.cb_cat.popup is None:
                lb = _open(root, rx)
            _pick(root, rx, lb, idx)
            assert rx.cb_cat.popup is None  # picking closes it
            assert rx.cat_var.get() == cats[idx], (idx, rx.cat_var.get())
            expected = list_by_category(cats[idx])
            assert rx.cb_drug._items == expected
            assert list(rx.cb_drug["values"]) == \
                [display(i, lang) for i in expected]
        # Esc closes without changing the selection (the focused
        # listbox is where a real Esc keypress lands).
        keep = rx.cat_var.get()
        lb = _open(root, rx)
        lb.event_generate("<Escape>")
        root.update_idletasks(); root.update()
        assert rx.cb_cat.popup is None
        assert rx.cat_var.get() == keep
        # Click-outside closes without changing the selection.
        lb = _open(root, rx)
        root.event_generate("<Button-1>")
        root.update_idletasks(); root.update()
        assert rx.cb_cat.popup is None
        assert rx.cat_var.get() == keep
        # Clicking the control again toggles the popup closed.
        rx.cb_cat._label.event_generate("<Button-1>")
        root.update(); assert rx.cb_cat.popup is not None
        rx.cb_cat._label.event_generate("<Button-1>")
        root.update(); assert rx.cb_cat.popup is None
        assert rx.cat_var.get() == keep
    finally:
        rx.cb_cat.close_popup()


def _run(lang, narrow):
    root, rx = _build(lang, narrow)
    if rx is None:
        print(f"SKIP r24 category picker {lang} narrow={narrow}"
              " (no display)")
        return
    try:
        _check(root, rx, lang)
    finally:
        root.destroy()
        set_setting("language", "en")


def test_popup_en_narrow_shell_host():
    _run("en", True)


def test_popup_en_standalone_host():
    _run("en", False)


def test_popup_ar_narrow_shell_host():
    _run("ar", True)


def test_popup_ar_standalone_host():
    _run("ar", False)
