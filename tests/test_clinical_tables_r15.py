"""Round 15 clinical tables restyle (2026-11-10): iOS27 main-colour
tables with progressive darkening, compact height-2 fields with
INTERNAL wheel scrolling. Round 19 (item 3) superseded the 2x2
grid: the four tables now sit ALL IN ONE ROW (1x4) at the top of
the clinical right area. Round 22: the tables sit in the main
scroll flow under the chart + pinned header, and only the
payments/procedures panels are built (see the no-patient test).
GUI tests skip gracefully when no display is available."""
import tkinter as tk

from src.config.strings_r15_clinical import AR as R15_AR, EN as R15_EN
from src.ui.clinical import ClinicalTab
from src.ui.clinical_table_style import ORDER, contrast_ratio, luminance, table_colors


def test_r15_table_colours_progressive_and_contrast():
    """Luminance strictly decreases complaint -> symptom -> diagnosis
    -> procedure in BOTH modes; body text, title text and the white
    Add-button label are all >= 4.5:1 on their table background."""
    for dark in (False, True):
        lums = [luminance(table_colors(k, dark)["bg"]) for k in ORDER]
        assert lums == sorted(lums, reverse=True), (dark, lums)
        assert len(set(lums)) == 4, (dark, lums)
        for kind in ORDER:
            c = table_colors(kind, dark)
            assert contrast_ratio(c["body_fg"], c["bg"]) >= 4.5, (dark, kind)
            assert contrast_ratio(c["title_fg"], c["bg"]) >= 4.5, (dark, kind)
            assert contrast_ratio("#FFFFFF", c["btn_bg"]) >= 4.5, (dark, kind)
    # Brown panel header (reference Overview header): white on it.
    assert contrast_ratio("#FFFFFF", "#7A3F16") >= 4.5


def test_r15_clinical_strings_bilingual():
    import re
    assert set(R15_EN) == set(R15_AR) and R15_EN
    for key in R15_EN:
        assert R15_EN[key].strip() and R15_AR[key].strip(), key
        # Format-only strings (placeholders + punctuation, e.g. the Rx
        # line) are legitimately identical in both languages; only
        # strings with real words must differ.
        words = re.sub(r"\{[^}]*\}", "", R15_EN[key])
        if re.search(r"[A-Za-z\u0600-\u06FF]", words):
            assert R15_EN[key] != R15_AR[key], key


class _FakeApp:
    lang = "en"
    current_patient = None
    current_user = "fady"
    current_role = "admin"

    def chart_teeth(self):
        return []

    def refresh_clinical(self):
        pass


def _build(lang="en", patient=None):
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.deiconify()
    root.geometry("1380x900")
    app = _FakeApp()
    app.lang = lang
    app.current_patient = patient
    tab = ClinicalTab(root, app)
    tab.pack(fill="both", expand=True)
    root.update()
    return root, tab


def _page_canvas(tab, widget):
    """The scrollable page canvas above `widget` (walk up masters)."""
    w = widget
    while w is not None:
        if isinstance(w, tk.Canvas):
            return w
        w = w.master
    return None


def test_r15_tables_one_row_layout_and_compact():
    root, tab = _build()
    if tab is None:
        print("SKIP test_r15_tables_one_row_layout (no display)")
        return
    try:
        assert hasattr(tab, "sections_grid") and hasattr(tab, "table_frames")
        assert set(tab.table_frames) == set(ORDER)
        expect = {"complaint": (0, 0), "symptom": (0, 1),
                  "diagnosis": (0, 2), "procedure": (0, 3)}
        grid_w = tab.sections_grid.winfo_width()
        assert grid_w > 400, grid_w
        for kind, (row, col) in expect.items():
            info = tab.table_frames[kind].grid_info()
            assert (int(info["row"]), int(info["column"])) == (row, col), kind
            # Quarter-width: each table is about a quarter of the row.
            fw = tab.table_frames[kind].winfo_width()
            assert 0.18 * grid_w < fw < 0.32 * grid_w, (kind, fw, grid_w)
        # ALL FOUR tables share ONE row (same top), in field order.
        tops = [getattr(tab, a).winfo_rooty() for a in
                ("txt_complaint", "txt_sym", "txt_diagnosis", "txt_procedure")]
        assert max(tops) - min(tops) < 5, tops
        xs = [tab.table_frames[k].winfo_rootx() for k in ORDER]
        assert xs == sorted(xs) and len(set(xs)) == 4, xs
        # Compact: every main field is height 2 (was 3 / 2).
        for attr in ("txt_complaint", "txt_sym", "txt_diagnosis", "txt_procedure"):
            assert int(getattr(tab, attr).cget("height")) == 2, attr
        # Picker buttons + clipboard bindings survived the restyle.
        assert set(tab.picker_buttons) == set(ORDER)
        from src.ui.clipboard_picker import CLIPBOARD_BINDING
        for name in ("complaint", "symptom", "diagnosis", "procedure"):
            assert tab.clipboard_fields[name].bind(CLIPBOARD_BINDING), name
    finally:
        root.destroy()


def test_r15_table_wheel_scrolls_internally_not_page():
    root, tab = _build()
    if tab is None:
        print("SKIP test_r15_table_wheel_scrolls_internally (no display)")
        return
    try:
        txt = tab.txt_complaint
        txt.delete("1.0", tk.END)
        txt.insert("1.0", "\n".join(f"line {i}" for i in range(20)))
        root.update()
        assert txt.yview()[1] < 1.0, "field not scrollable in test setup"
        canvas = _page_canvas(tab, txt)
        assert canvas is not None
        page_before, text_before = canvas.yview(), txt.yview()
        inner = txt.widget  # the real tk.Text under the pointer
        inner.event_generate("<MouseWheel>", delta=-120)
        root.update()
        assert txt.yview()[0] > text_before[0], "wheel did not scroll the field"
        assert canvas.yview() == page_before, "wheel scrolled the PAGE too"
        inner.event_generate("<Button-5>")
        root.update()
        assert txt.yview()[0] > text_before[0], "Button-5 did not scroll the field"
        assert canvas.yview() == page_before, "Button-5 scrolled the PAGE too"
        mid = txt.yview()
        inner.event_generate("<MouseWheel>", delta=120)
        root.update()
        assert txt.yview()[0] < mid[0], "wheel up did not scroll the field back"
        assert canvas.yview() == page_before, "wheel up scrolled the PAGE"
        inner.event_generate("<Button-4>")
        root.update()
        assert txt.yview()[0] < mid[0], "Button-4 did not scroll the field back"
        assert canvas.yview() == page_before, "Button-4 scrolled the PAGE"
    finally:
        root.destroy()


def test_r15_tables_build_with_no_patient():
    """No patient selected: tables build, no crash.
    Round 22 superseded the panel set to "payments" +
    "procedures" (Health -> pinned header, Rx summary -> the
    shell column's Prescriptions section); round 23 superseded
    it again (Recent Payments REMOVED). ROUND-24 SUPERSESSION
    (items 2+6): the Therapeutic Procedures panel is REMOVED
    too -- NO panels are built; the no-patient state is the
    unified table's empty record tree."""
    root, tab = _build()
    if tab is None:
        print("SKIP test_r15_tables_build_with_no_patient (no display)")
        return
    try:
        assert not hasattr(tab, "panel_texts")
        assert not hasattr(tab, "panel_frames")
        assert tab.tree_history.get_children() == ()
    finally:
        root.destroy()
