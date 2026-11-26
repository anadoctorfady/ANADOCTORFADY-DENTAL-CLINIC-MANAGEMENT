"""Round 55: (A) the clinical header is a 3-ROW x 5-column STRIP
across the FULL main area (not the round-54 tall narrow card),
holding every old field + balance + the adherence reminder, with
father/grandfather/family still gone; (B) no two adjacent cells
share a colour (four-neighbour rule, both languages/themes);
(C) appointment adherence from the last 3 appointments colours
the patient's NAME in the patient list (green/amber/red, no
signal = default colours) and the header's adherence cell.
Adherence seeding lives in tests.test_r55_adherence_model.
"""
import time
import tkinter as tk
from tkinter import messagebox

from src.models.adherence import COLOURS
from src.models.database import get_setting, set_setting
from src.ui import rounded as _rounded
from src.ui.header_strip import _GRID, cell_bg
from src.ui.vivid_rows import TEXT_ON_VIVID
from tests.test_r55_adherence_model import BASE, _cleanup, _seed_adherence


def _display_available():
    try:
        r = tk.Tk(); r.withdraw(); r.destroy(); return True
    except Exception:
        return False


def _make_app(lang):
    from src.ui.shell import App
    orig = get_setting("language", "en") or "en"
    set_setting("language", lang)
    messagebox.showinfo = lambda *a, **k: None
    messagebox.showerror = lambda *a, **k: None
    app = App()
    login = [w for w in app.winfo_children()
             if isinstance(w, tk.Toplevel) and hasattr(w, "e_user")][0]
    login.do_login()
    app.update(); app.geometry("1920x1080+0+0")
    app.update(); time.sleep(0.2); app.update()
    return app, orig


def _close(app, orig):
    set_setting("language", orig); _rounded._MEASURE_CACHE.clear()
    # The EN test toggles the theme to dark for its contrast pin;
    # restore light so later tests in this process boot light.
    from src.config.settings import set_theme_mode
    set_theme_mode("light")
    try:
        app.destroy()
    except Exception:
        pass


def _load(app, fid):
    from src.models.database import get_connection
    conn = get_connection()
    row = dict(conn.execute(
        "SELECT * FROM patients WHERE file_number=?", (fid,)).fetchone())
    conn.close()
    app.current_patient = row; app.clinical.load(fid)
    app.update(); time.sleep(0.2); app.update()
    return row


def _check_strip(app, lang):
    """Exactly 3 grid rows, full main-area width, every old field
    present, father/grandfather/family gone, buttons beside
    Manage templates, chart still full width below the strip."""
    from src.config.strings import t
    panel = app.info_panel; tab = app.clinical
    assert panel._grid.grid_size() == (5, 3), panel._grid.grid_size()
    assert panel.winfo_width() >= 0.9 * tab.winfo_width(), (
        lang, panel.winfo_width(), tab.winfo_width())
    assert tab.chart.winfo_width() >= 0.9 * tab.winfo_width()
    gap = tab.chart.winfo_rooty() - (panel.winfo_rooty() + panel.winfo_height())
    assert 0 <= gap <= 40, (lang, gap)
    info = panel.info_text()
    assert "#1" in info and "Ahmed Mohammed Ali Hassan" in info
    for label in ("Father:", "Grandfather:", "Family:",
                  "الأب:", "الجد:", "الكنية:"):
        assert label not in info, (lang, label, info)
    for key in ("age", "birth", "hijri", "mobile1", "mobile2",
                "emergency_phone", "address", "nationality", "diseases",
                "current_medications", "allergies", "balance", "adherence"):
        assert panel._cell_lbls[key].cget("text"), (lang, key)
    bar = panel.edit_btn.master
    assert bar in tab.winfo_children(), "action buttons not in tab bar"
    assert panel.delete_btn.master is bar and panel.refer_btn.master is bar
    texts = [str(c.cget("text")) for c in bar.winfo_children()
             if c.winfo_class() == "Button"]
    assert t("clinical.manage_templates", lang) in texts, texts
    # (B) four-neighbour rule on the REAL painted label colours.
    # A spanned cell (Diseases, cols 0-1) is ONE cell: positions
    # belonging to the same label are never neighbours of it.
    occ = {}
    for r, c, span, _k, _col, _kind in _GRID:
        lbl = panel._cell_lbls[_kind if _col is None else _col]
        for cc in range(c, c + span):
            occ[(r, cc)] = (lbl.cget("bg"), id(lbl), r, c)
    for (r, c), (bg, ident, ar, ac) in occ.items():
        assert bg == cell_bg(ar, ac), ((r, c), bg)
        for nb in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if nb in occ and occ[nb][1] != ident:
                assert occ[nb][0] != bg, ((r, c), nb, bg)
    # Cell text is the dark vivid-rows colour (red only for a
    # non-empty diseases/allergies line or an owed balance; the
    # name cell keeps its own debt/credit rule, checked elsewhere).
    for key, lbl in panel._cell_lbls.items():
        if key == "full_name":
            continue
        fg = lbl.cget("fg")
        assert fg in (TEXT_ON_VIVID, panel._red) or fg in COLOURS.values(), (key, fg)


def test_r55_strip_ar():
    if not _display_available():
        return
    _seed_adherence()
    app, orig = _make_app("ar")
    try:
        _load(app, 1); _check_strip(app, "ar")
        panel = app.info_panel
        # Empty-fields patient: every value cell shows --.
        empty = dict(BASE, file_number=9105, full_name="R55 Empty",
                     birth_date_greg="", age_years=0, age_months=0,
                     age_days=0, mobile1="", mobile2="",
                     emergency_phone="", address="", nationality="",
                     current_medications="", allergies="", diseases="")
        panel.refresh(empty); app.update()
        for key in ("birth", "hijri", "mobile1", "mobile2",
                    "emergency_phone", "address", "nationality",
                    "diseases", "current_medications", "allergies",
                    "balance", "adherence"):
            assert panel._cell_lbls[key].cget("text").endswith("—"), (
                key, panel._cell_lbls[key].cget("text"))
        assert panel.winfo_height() < 175, panel.winfo_height()
    finally:
        _cleanup(); _close(app, orig)


def test_r55_strip_en_list_colours():
    if not _display_available():
        return
    _seed_adherence()
    app, orig = _make_app("en")
    try:
        _load(app, 1); _check_strip(app, "en")
        panel = app.info_panel
        # Header adherence cell: green + the last-3 dates.
        _load(app, 9101)
        adh = panel._cell_lbls["adherence"]
        assert "2026-11-20" in adh.cget("text") and "Attended" in adh.cget("text")
        assert adh.cget("fg") == COLOURS["green"], adh.cget("fg")
        assert "DIABETES" in panel._cell_lbls["diseases"].cget("text")
        assert panel._cell_lbls["diseases"].cget("fg") == panel._red
        # Patient-list name colours from the same last-3 signal.
        app.search_var.set("R55"); app.load_patients(); app.update()
        tags = {}
        for iid in app.tree.get_children():
            v = app.tree.item(iid, "values")
            tags[int(v[0])] = app.tree.item(iid, "tags")
        assert "adh_green" in tags[9101], tags[9101]
        assert "adh_amber" in tags[9102], tags[9102]
        assert "adh_red" in tags[9103], tags[9103]
        assert not [tg for tg in tags[9104] if tg.startswith("adh_")], tags[9104]
        # Dark theme: the strip cells stay pastel, so every cell
        # foreground must still read on pastel (shot 240 caught the
        # dark theme text at ~1.2:1 on the name cell).
        from tests.test_r55_adherence_model import _ratio
        app._toggle_theme(); app.update()
        _load(app, 1)
        panel = app.info_panel
        for key in ("full_name", "diseases", "allergies"):
            lbl = panel._cell_lbls[key]
            assert _ratio(lbl.cget("fg"), lbl.cget("bg")) >= 4.5, (
                key, lbl.cget("fg"), lbl.cget("bg"))
    finally:
        _cleanup(); _close(app, orig)
