"""Round 17, items 4 + 8b (worker W5): clinical finance boxes.
(1) At 1380px in EN and AR, the finance boxes + Add Payment are
fully inside the finance section at full requested width (before:
the AR section needed 768px inside a 654px frame - rate-date label
+ Add Payment squeezed, date box past the frame edge).
(2) Date / Total box backgrounds distinct, never white, never the
finance TABLE tint, text contrast >= 4.5:1 each. (3) The patient
balance line (lbl_pat_totals) tracks the balance state. (4)
Currency combobox initial value is single-language (no Arabic in
EN, no Latin name in AR). GUI tests skip gracefully with no display.
ROUND-38 SUPERSESSION: the section is now the PAYMENT entry —
boxes are Payment date / Amount / Rate / Rate-date; the balance
lives on lbl_pat_totals (CREDIT colour when in credit).
ROUND-40 RE-PIN: the payment-entry section is REMOVED — ONE
payment place. The boxes are the unified entry's Date / Paid +
the strip's Rate / Rate-date; no "Add Payment" button anymore."""
import re
import time
import tkinter as tk
from tkinter import ttk

from src.config.strings import t
from src.config.theme import TABLE
from src.models.database import save_financial, set_setting
from src.ui import patient_alerts
from src.ui.clinical_table_style import contrast_ratio
from tests.test_payments_e2e import _build_clinical, _seed_patient, _cleanup

AR_CHARS = re.compile(r"[\u0600-\u06FF]")
BOX_ATTRS = ("e_sess_date", "e_sess_paid", "e_rate", "e_rate_date")  # R40 unified entry + money strip

def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)

def _right(w, app):
    return w.winfo_rootx() - app.winfo_rootx() + w.winfo_width()

def _app():
    """Logged-in App at the default 1380x820, or None (no display)."""
    try:
        from src.ui.shell import App
        app = App()
    except Exception:
        return None
    app.update()
    time.sleep(0.6)  # login window appears after 100ms
    app.update()
    login = next((w for w in app.winfo_children()
                  if isinstance(w, tk.Toplevel) and hasattr(w, "e_user")), None)
    if login is not None:
        login.destroy()
    app._on_login("fady")
    app.update()
    return app

def _set_lang(app, lang):
    app.lang = lang
    set_setting("language", lang)
    app._rebuild()
    app.update()
    app._on_login("fady")
    app.update()
    for w in _walk(app):
        if isinstance(w, ttk.Notebook) and str(app.clinical) in w.tabs():
            w.select(0)
            break
    app.update()

def _check_fit(app, lang):
    tab = app.clinical
    fin_outer = tab.money_strip  # R40: the money strip is the fit surface
    assert app.winfo_width() == 1380, app.winfo_width()
    assert tab.money_strip.winfo_reqwidth() <= tab.money_strip.winfo_width(), (
        lang, tab.money_strip.winfo_reqwidth(), tab.money_strip.winfo_width())
    for attr in BOX_ATTRS:
        w = getattr(tab, attr)
        assert w.winfo_manager() == "pack", (lang, attr, "not packed/visible")
        assert w.winfo_width() >= 30, (lang, attr, w.winfo_width())
        assert w.winfo_width() >= w.winfo_reqwidth(), (
            lang, attr, w.winfo_width(), w.winfo_reqwidth())
        assert _right(w, app) <= 1380, (lang, attr, _right(w, app))
    # R40: no "Add Payment" button; the Save button must fit.
    btns = [w for w in _walk(tab) if isinstance(w, tk.Button)
            and str(w.cget("text")) == t("clinical.add_payment", lang)]
    assert len(btns) == 0, (lang, len(btns))
    btn = tab.btn_save_visit
    assert btn.winfo_width() >= btn.winfo_reqwidth(), (
        lang, "save squeezed", btn.winfo_width(), btn.winfo_reqwidth())
    for w in _walk(fin_outer):
        if isinstance(w, tk.Label) and str(w.cget("text")):
            assert w.winfo_width() >= w.winfo_reqwidth(), (
                lang, "label clipped", w.cget("text"),
                w.winfo_width(), w.winfo_reqwidth())

def test_finance_boxes_fit_1380_en():
    app = _app()
    if app is None:
        print("SKIP test_finance_boxes_fit_1380_en (no display)")
        return
    try:
        _check_fit(app, "en")
    finally:
        app.destroy()

def test_finance_boxes_fit_1380_ar():
    app = _app()
    if app is None:
        print("SKIP test_finance_boxes_fit_1380_ar (no display)")
        return
    try:
        _set_lang(app, "ar")
        _check_fit(app, "ar")
    finally:
        set_setting("language", "en")
        app.destroy()

def test_box_colors_distinct_and_contrast():
    root, tab = _build_clinical("fady", "admin", None)
    if tab is None:
        print("SKIP test_box_colors_distinct_and_contrast (no display)")
        return
    try:
        boxes = {"date": tab.e_sess_date, "total": tab.e_sess_paid,
                 "rate_date": tab.e_rate_date}
        bgs = {}
        for name, w in boxes.items():
            bg, fg = str(w.cget("bg")), str(w.cget("fg"))
            bgs[name] = bg.lower()
            assert bg.lower() not in ("#ffffff", "white"), (name, bg)
            assert bg.lower() != TABLE["finance"].lower(), (name, bg)
            ratio = contrast_ratio(fg, bg)
            assert ratio >= 4.5, (name, fg, bg, ratio)
        # R40: both DATE boxes share the date colour by design;
        # date vs amount ("total") colours stay distinct.
        assert bgs["date"] == bgs["rate_date"], bgs
        assert bgs["date"] != bgs["total"], bgs
    finally:
        root.destroy()

def test_patient_balance_line_states():
    """ROUND-38 SUPERSESSION: balance state lives on lbl_pat_totals
    — owed plain, zero when settled, CREDIT + colour after advance."""
    from src.config.theme import credit_color, is_dark
    from src.models import payments as _pay
    fid = _seed_patient("R17Rem")
    try:
        save_financial(fid, "11", 500, 300, "2026-11-12")
        root, tab = _build_clinical("fady", "admin", fid)
        if tab is None:
            print("SKIP test_patient_balance_line_states (no display)")
            return
        try:
            assert "200.00" in tab.lbl_pat_totals.cget("text"), \
                tab.lbl_pat_totals.cget("text")
            assert str(tab.lbl_pat_totals.cget("fg")) != credit_color(is_dark())
            # Pay in full in the model, reload -> balance 0.
            save_financial(fid, "11", 0, 200, "2026-11-12")
            from src.ui import clinical_finance_actions as _fin
            _fin.load_costs(tab, fid)
            root.update_idletasks()
            assert "0.00" in tab.lbl_pat_totals.cget("text")
            # Advance payment -> credit state on the same line.
            _pay.save_standalone_payment(fid, 50, "2026-11-12",
                                         doctor="fady", entered_by="fady")
            _fin.load_costs(tab, fid)
            root.update_idletasks()
            assert "Credit" in tab.lbl_pat_totals.cget("text")
            assert str(tab.lbl_pat_totals.cget("fg")) == credit_color(is_dark())
        finally:
            root.destroy()
    finally:
        _cleanup(fid)

def test_currency_combobox_single_language():
    for lang in ("en", "ar"):
        root, tab = _build_clinical("fady", "admin", None, lang)
        if tab is None:
            print("SKIP test_currency_combobox_single_language (no display)")
            return
        try:
            value = tab.cur_var.get()
            values = [str(v) for v in tab.cb_cur["values"]]
            assert values, lang
            if lang == "en":
                assert not AR_CHARS.search(value), value
                assert all(not AR_CHARS.search(v) for v in values)
            else:
                assert AR_CHARS.search(value), value
                assert not re.search(r"[A-Za-z]", value.split(" - ", 1)[-1]), value
                # Dropdown entries with a real Arabic name in the data
                # (105/178 codes have none - a pre-existing data gap,
                # not the threading) render Arabic, code stays Latin.
                for code in ("SYP", "USD"):
                    entry = next(v for v in values if v.startswith(code + " - "))
                    assert AR_CHARS.search(entry), entry
                    assert not re.search(r"[A-Za-z]", entry.split(" - ", 1)[-1]), entry
        finally:
            root.destroy()
