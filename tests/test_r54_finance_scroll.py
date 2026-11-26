"""Round 54, Section G: the Finance page is scrollable in Arabic
(at 1920x1080 the Arabic rows make it taller than the window --
the owner's AR screenshot shows the 3rd expense row and the
Edit/Delete buttons cut off below the fold, while EN fits), and
the Base USD-conversion line carries bidi isolation on every
Latin run (the bare "140" used to jump before "دخل").

Audit (probe_g.py, AR 1920x1080, scaling 1.5): Clinical,
Settings, Users, About and the sidebar all already reach their
bottom content by scrolling -- only Finance lacked a scroll
path, so only Finance changes. No fonts or rows were shrunk.

ROUND 56 UPDATE: the Amiri revert shrank the AR rows, so at
scaling 1.5 the Finance page now FITS (scrollregion 921px vs
972px canvas -- the good consequence the owner asked for).
The scroll-engagement pin moves to scaling 2.0 (region ~1227px
> viewport), and a new pin asserts the 1.5 fit.
"""
import re
import time
import tkinter as tk
from datetime import date
from tkinter import messagebox

from src.config.strings import t
from src.models.database import get_setting, set_setting
from src.ui import rounded as _rounded

TODAY = date.today().isoformat()


def _display_available():
    try:
        r = tk.Tk(); r.withdraw(); r.destroy()
        return True
    except Exception:
        return False


def _make_app(lang="ar", scaling=None):
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
    if scaling is not None:
        app.tk.call("tk", "scaling", scaling)
        _rounded._MEASURE_CACHE.clear()
        if hasattr(app, "_r51_font_cache"):
            delattr(app, "_r51_font_cache")
        app._rebuild()
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


def _seed():
    from src.models.database import get_connection, save_financial
    from src.models.finance import add_expense
    from src.models.currency import save_rate
    conn = get_connection()
    conn.execute("INSERT INTO patients(first_name,full_name) "
                 "VALUES(?,?)", ("R54G", "R54G Finance"))
    fid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit(); conn.close()
    save_financial(fid, "11", 1000, 1000, TODAY, currency="SYP",
                   rate=140, rate_date=TODAY, doctor="fady",
                   entered_by="fady")
    save_rate(TODAY, 140, "USD", "SYP")
    for d, cat, desc, amt in (("2026-11-10", "Materials", "لاب", 250.0),
                              ("2026-11-09", "Materials", "مواد", 400.0),
                              ("2026-11-08", "Rent", "إيجار", 900.0)):
        add_expense(d, cat, desc, amt)
    return fid


def _teardown(fid):
    from src.models.database import get_connection
    conn = get_connection()
    conn.execute("DELETE FROM financials WHERE patient_file=?", (fid,))
    conn.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.execute("DELETE FROM expenses WHERE description IN "
                 "('لاب','مواد','إيجار')")
    conn.execute("DELETE FROM exchange_rates WHERE from_currency='USD'")
    conn.commit(); conn.close()


def _unlock_fin(app):
    app.notebook.select(app.fin)
    app.update(); time.sleep(0.2); app.update()
    tab = app.fin
    tab.e_gate_user.delete(0, tk.END); tab.e_gate_user.insert(0, "fady")
    tab.e_gate_pass.delete(0, tk.END); tab.e_gate_pass.insert(0, "1234")
    tab._try_unlock()
    app.update(); time.sleep(0.2); app.update()
    return tab


def _win_bottom(app):
    return app.winfo_rooty() + app.winfo_height()


def test_r54_finance_scrollable_ar():
    if not _display_available():
        return
    fid = _seed()
    # R56: the scroll-engagement pin moves to scaling 2.0 -- at
    # 1.5 the Amiri revert shrank the AR rows so the page fits
    # (see test_r54_finance_fits_ar_15 below).
    app, orig = _make_app("ar", 2.0)
    try:
        tab = _unlock_fin(app)
        assert len(tab.tree_exp.get_children()) >= 3
        cv = tab._scroll_page
        assert cv.winfo_class() == "Canvas"
        region = str(cv.cget("scrollregion")).split()
        assert float(region[3]) > cv.winfo_height(), (
            "scroll never engages in AR at scaling 2.0", region,
            cv.winfo_height())
        cv.yview_moveto(1.0); app.update()
        assert tab.btn_expense_edit.winfo_ismapped() == 1
        assert tab.btn_expense_edit.winfo_rooty() + \
            tab.btn_expense_edit.winfo_height() <= _win_bottom(app), (
            "Edit button still below the fold after scrolling")
        assert tab.btn_expense_del.winfo_rooty() + \
            tab.btn_expense_del.winfo_height() <= _win_bottom(app)
        assert tab.tree_exp.winfo_rooty() + \
            tab.tree_exp.winfo_height() <= _win_bottom(app), (
            "expenses table still cut off after scrolling")
    finally:
        _teardown(fid)
        _close(app, orig)


def test_r54_finance_fits_ar_15():
    # R56 (Amiri revert): at scaling 1.5 the AR Finance page now
    # FITS -- scrollregion no taller than the canvas, and the
    # Edit/Delete buttons are reachable WITHOUT scrolling.
    if not _display_available():
        return
    fid = _seed()
    app, orig = _make_app("ar", 1.5)
    try:
        tab = _unlock_fin(app)
        assert len(tab.tree_exp.get_children()) >= 3
        cv = tab._scroll_page
        region = str(cv.cget("scrollregion")).split()
        assert float(region[3]) <= cv.winfo_height(), (
            "AR Finance should fit at scaling 1.5 after R56", region,
            cv.winfo_height())
        assert tab.btn_expense_edit.winfo_ismapped() == 1
        assert tab.btn_expense_edit.winfo_rooty() + \
            tab.btn_expense_edit.winfo_height() <= _win_bottom(app), (
            "Edit button below the fold at scaling 1.5")
        assert tab.btn_expense_del.winfo_rooty() + \
            tab.btn_expense_del.winfo_height() <= _win_bottom(app)
    finally:
        _teardown(fid)
        _close(app, orig)


def test_r54_finance_fits_en():
    if not _display_available():
        return
    fid = _seed()
    app, orig = _make_app("en")
    try:
        tab = _unlock_fin(app)
        assert tab.btn_expense_edit.winfo_ismapped() == 1
        assert tab.btn_expense_edit.winfo_rooty() + \
            tab.btn_expense_edit.winfo_height() <= _win_bottom(app)
    finally:
        _teardown(fid)
        _close(app, orig)


def test_r54_base_line_bidi_ar():
    # ROUND 55 RE-PIN (with cause): the string itself, with the
    # owner's own figures -- every Latin run now wrapped in LRM
    # (U+200E), NOT LRI/PDI (U+2066..U+2069): the isolates rendered
    # as small visible marks under Windows Segoe UI on his machine.
    got = t("fin.usd_equiv", "ar").format(base="SYP", inc=266.07,
                                         net=22.14, rate=140)
    want = ("الأساس: \u200eSYP\u200e  •  ≈ \u200e$266.07\u200e دخل / "
            "\u200e$22.14\u200e صافي بسعر \u200e140\u200e \u200eSYP\u200e")
    assert got == want, repr(got)
    # ...and the no-rate sibling wraps its currency code too.
    assert t("fin.usd_set_rate", "ar").format(base="SYP") == (
        "الأساس: \u200eSYP\u200e — حدّد سعر الدولار لعرض ما يعادله بالدولار")
    # ...and the live label after a real calc: the marks are the
    # ONLY difference from the un-marked rendering.
    if not _display_available():
        return
    fid = _seed()
    app, orig = _make_app("ar")
    try:
        tab = _unlock_fin(app)
        txt = tab.lbl_usd.cget("text")
        assert "\u200eSYP\u200e" in txt and "\u200e140\u200e" in txt
        assert re.search(r"\u200e\$[\d,]+\.\d{2}\u200e", txt), txt
        assert "\u2066" not in txt and "\u2069" not in txt, txt
        plain = txt.replace("\u200e", "")
        assert "دخل" in plain and "صافي" in plain and "بسعر" in plain
        assert plain.index("دخل") < plain.index("صافي") < \
            plain.index("بسعر"), plain
    finally:
        _teardown(fid)
        _close(app, orig)
