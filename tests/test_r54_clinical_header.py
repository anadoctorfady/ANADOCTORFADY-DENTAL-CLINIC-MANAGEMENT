"""Round 54 header test, ROUND 55 RE-PINNED (with cause): the
round-54 narrow card is SUPERSEDED by the round-55 3-row x
5-column STRIP across the FULL main area (the owner found the
tall narrow card INCREASED the header's area). The assertions
below are the strip's: exactly 3 grid rows, full main-area
width, the redundant father / grandfather / family rows still
gone, the birth data as three cells (Age / Birth date / Hijri),
and the Edit / Delete / Refer buttons still beside Manage
templates in the tab's top bar. The dental chart below still
spans the full width, and the left sidebar is untouched
(round-53 rule).
"""
import time
import tkinter as tk
from tkinter import messagebox

from src.models.database import get_setting, set_setting
from src.ui import rounded as _rounded

SEED = {"file_number": 9001, "first_name": "R54", "father_name": "R54Dad",
        "grand_name": "R54Gpa", "last_name": "R54Fam",
        "full_name": "R54 Filled Patient", "birth_date_greg": "1980-03-10",
        "birth_date_hijri": "", "age_years": 45, "age_months": 9,
        "age_days": 3, "age_total_days": 0, "mobile1": "+962791234569",
        "mobile2": "", "emergency_phone": "+962791234570",
        "address": "1 Test Road, Amman, Jordan", "nationality": "Jordanian",
        "current_medications": "Metformin 500 mg",
        "allergies": "Penicillin, Sulfa",
        "diseases": ("DIABETES MELLITUS, HYPERTENSION, ASTHMA, EPILEPSY, "
                     "RHEUMATOID ARTHRITIS, OSTEOPOROSIS")}


def _display_available():
    try:
        r = tk.Tk(); r.withdraw(); r.destroy()
        return True
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
    app.update()
    app.geometry("1920x1080+0+0")
    app.update(); time.sleep(0.2); app.update()
    return app, orig


def _close(app, orig):
    set_setting("language", orig)
    _rounded._MEASURE_CACHE.clear()
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
    app.current_patient = row
    app.clinical.load(fid)
    app.update(); time.sleep(0.2); app.update()
    return row


def _seed():
    from src.models.database import get_connection
    conn = get_connection()
    cols = ", ".join(SEED)
    conn.execute(f"INSERT OR REPLACE INTO patients({cols}) VALUES("
                 + ", ".join("?" * len(SEED)) + ")",
                 tuple(SEED.values()))
    conn.commit(); conn.close()


def _unseed():
    from src.models.database import get_connection
    conn = get_connection()
    conn.execute("DELETE FROM patients WHERE file_number=9001")
    conn.commit(); conn.close()


def _check_header(app, lang):
    """(a) exactly 3 strip rows across the full main area, (b) no
    redundant rows, (c) the three birth cells, (d) the buttons
    live beside Manage templates, (e) no button left in the strip."""
    from src.config.strings import t
    panel = app.info_panel
    tab = app.clinical
    assert panel._grid.grid_size() == (5, 3), panel._grid.grid_size()
    assert panel.winfo_width() >= 0.9 * tab.winfo_width(), (
        lang, panel.winfo_width(), tab.winfo_width())
    assert tab.chart.winfo_width() >= 0.9 * tab.winfo_width(), (
        lang, tab.chart.winfo_width(), tab.winfo_width())
    info = panel.info_text()
    for label in ("Father:", "Grandfather:", "Family:",
                  "الأب:", "الجد:", "الكنية:"):
        assert label not in info, (lang, label, info)
    assert "#1" in info and "Ahmed Mohammed Ali Hassan" in info
    cells = panel._cell_lbls
    age_l, birth_l, hijri_l = (cells[k].cget("text") for k in
                               ("age", "birth", "hijri"))
    if lang == "ar":
        assert age_l.startswith("العمر:") and "36" in age_l, age_l
        assert birth_l.startswith("تاريخ الميلاد:") and "1990" in birth_l
        assert hijri_l.startswith("الهجري:") and "1410" in hijri_l
    else:
        assert age_l.startswith("Age:") and "36" in age_l, age_l
        assert birth_l.startswith("Birth date:") and "1990" in birth_l
        assert hijri_l.startswith("Hijri:") and "1410" in hijri_l
    # (d) buttons: same parent as the Manage-templates button, in
    # the tab's top bar -- and none left inside the header strip.
    bar = panel.edit_btn.master
    assert bar in tab.winfo_children(), "action buttons not in tab bar"
    assert panel.delete_btn.master is bar and panel.refer_btn.master is bar
    texts = [str(c.cget("text")) for c in bar.winfo_children()
             if c.winfo_class() == "Button"]
    assert t("clinical.manage_templates", lang) in texts, texts
    tmpl = [c for c in bar.winfo_children()
            if c.winfo_class() == "Button"
            and str(c.cget("text")) == t("clinical.manage_templates", lang)][0]
    assert tmpl.winfo_rootx() > panel.edit_btn.winfo_rootx(), (
        "templates button is not the rightmost in the bar")
    for w in panel.winfo_children():
        for sub in [w] + list(w.winfo_children()):
            assert sub.winfo_class() != "Button", "button left in header"


def test_r54_header_ar():
    if not _display_available():
        return
    app, orig = _make_app("ar")
    try:
        _load(app, 1)
        _check_header(app, "ar")
        # Filled patient: long disease list still wraps inside the
        # strip (width bound holds), then empty fields show —.
        _seed()
        try:
            _load(app, 9001)
            panel = app.info_panel
            assert panel.winfo_width() >= 0.9 * app.clinical.winfo_width()
            assert "OSTEOPOROSIS" in panel.info_text()
            empty = dict(SEED, file_number=9002, full_name="R54 Empty",
                         birth_date_greg="", age_years=0, age_months=0,
                         age_days=0, mobile1="", mobile2="",
                         emergency_phone="", address="", nationality="",
                         current_medications="", allergies="", diseases="")
            panel.refresh(empty)
            app.update()
            for key in ("birth", "hijri", "mobile1", "mobile2",
                        "emergency_phone", "address", "nationality",
                        "diseases", "current_medications", "allergies",
                        "balance", "adherence"):
                assert panel._cell_lbls[key].cget("text").endswith("—"), (
                    key, panel._cell_lbls[key].cget("text"))
        finally:
            _unseed()
    finally:
        _close(app, orig)


def test_r54_header_en():
    if not _display_available():
        return
    app, orig = _make_app("en")
    try:
        _load(app, 1)
        _check_header(app, "en")
    finally:
        _close(app, orig)
