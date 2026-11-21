"""Round 21: red highlights (item 1) and the Debtors-only button
contrast fix (item 4). The item-2 two-section LAYOUT tests that
used to live here are superseded by ROUND 22 (owner redesign,
2026-11-16): the panels left the shell column (payments +
procedures moved into the clinical main scroll flow, the info
panel became the clinical tab's PINNED HEADER, prescriptions
took the shell slot under the list). Layout coverage now lives
in tests/test_r22_layout.py; this file keeps items 1 + 4.

Item 1: a patient with remaining > 0 carries the "debt" tag in
the list (red name) and a red name in the info panel -- since
round 22 that panel is the clinical tab's pinned header
(app.info_panel is tab.header_panel, same widget class and
refresh contract); the Diseases / Allergies lines are red when
non-empty. The reds are >= 4.5:1 on the list background in both
modes (pure-token asserts) -- the GUI asserts run on the gate
copy's debtor.

Item 4: the Debtors-only ON state uses the finance accent /
btn_text pair of the current mode, >= 4.5:1 in both modes
(the old white-on-accent pair was ~2.9:1 in dark mode).

Full-App tests run only on an isolated gate copy
(ANADOCTORFADY_DATA_DIR set); GUI parts skip with no display.
"""
import os
import tkinter as tk
from types import SimpleNamespace

from src.config.theme import DARK, LIGHT, debt_red, finance_tokens, mode
from src.config.settings import set_theme_mode
from src.models.finance import patient_totals
from src.ui.clinical_table_style import contrast_ratio
from src.ui.patient_search import AdvancedSearchPanel
from tests.test_r18_info_panel_visible import _display_available, _login


def _boot(geo="1380x1000"):
    from src.models.database import get_connection
    from src.ui.shell import App
    from src.utils.auth import hash_pw
    conn = get_connection()
    conn.execute("UPDATE users SET password_hash=? WHERE username='fady'",
                 (hash_pw("1234"),))
    conn.commit(); conn.close()
    app = App()
    _login(app)
    app.geometry(geo); app.update()
    return app


def _chain(w):
    out = []
    while w is not None:
        out.append(w); w = w.master
    return out


def _inside(app, w):
    top = w.winfo_rooty() - app.winfo_rooty()
    left = w.winfo_rootx() - app.winfo_rootx()
    return (0 <= top and top + w.winfo_height() <= app.winfo_height()
            and 0 <= left and left + w.winfo_width() <= app.winfo_width())


def test_red_tokens_contrast_both_modes():
    """Pure data: the debtor red clears 4.5:1 on the list bg."""
    assert contrast_ratio(debt_red(False), LIGHT["list_bg"]) >= 4.5
    assert contrast_ratio(debt_red(True), DARK["list_bg"]) >= 4.5


def test_debtors_button_contrast_both_modes():
    """Item 4, pure data + widget: the ON pair is the finance
    pair of the mode and clears 4.5:1 in BOTH modes."""
    for dark in (False, True):
        fin = finance_tokens(dark)
        assert contrast_ratio(fin["btn_text"], fin["accent"]) >= 4.5, dark
    if not _display_available():
        print("SKIP debtors button widget (no display)"); return
    root = tk.Tk(); root.withdraw()
    try:
        for dark in (False, True):
            set_theme_mode("dark" if dark else "light")
            stub = SimpleNamespace(lang="en", tree=None,
                                   load_patients=lambda: None)
            panel = AdvancedSearchPanel(root, stub, on_search=lambda: None)
            panel.toggle_debtors()
            fin = finance_tokens(dark)
            assert panel.btn_debtors._bg == fin["accent"], (dark, panel.btn_debtors._bg)
            assert panel.btn_debtors._fg == fin["btn_text"], (dark, panel.btn_debtors._fg)
            panel.destroy()
    finally:
        set_theme_mode("light")
        root.destroy()


def _debtor_fid():
    from src.models.database import get_connection
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT file_number FROM patients WHERE deleted=0")
    fids = [r[0] for r in cur.fetchall()]; conn.close()
    for fid in fids:
        if patient_totals(fid)["remaining"] > 0:
            return fid
    return None


def test_red_highlights_in_list_and_header():
    if not os.environ.get("ANADOCTORFADY_DATA_DIR"):
        print("SKIP (not an isolated gate copy)"); return
    if not _display_available():
        print("SKIP (no display)"); return
    app = _boot("1380x1000")
    try:
        tab = app.clinical
        # Round 22: the info panel is the tab's pinned header.
        assert app.info_panel is tab.header_panel
        assert tab.mid_paned is None  # one full-width section
        # Input row spans the full width of the tab.
        xs = [tab.table_frames[k].winfo_rootx() for k in
              ("complaint", "symptom", "diagnosis", "procedure")]
        rights = [tab.table_frames[k].winfo_rootx()
                  + tab.table_frames[k].winfo_width()
                  for k in ("complaint", "symptom", "diagnosis", "procedure")]
        assert max(rights) - min(xs) >= 800, (min(xs), max(rights))
        # --- Item 1: red highlights for the gate copy's debtor.
        fid = _debtor_fid()
        assert fid is not None, "gate copy has no debtor patient"
        app.search_var.set("a"); app.update()
        tags_by_fid = {}
        for iid in app.tree.get_children():
            v = app.tree.item(iid, "values")
            tags_by_fid[str(v[0])] = app.tree.item(iid, "tags")
        assert "debt" in tags_by_fid[str(fid)], tags_by_fid
        for other, tags in tags_by_fid.items():
            if other != str(fid) and patient_totals(int(other))["remaining"] <= 0:
                assert "debt" not in tags, (other, tags)
        red = debt_red(mode() == "dark")
        patient = dict(app.current_patient or {})
        patient.update({"file_number": fid, "diseases": "Diabetes",
                        "allergies": "Penicillin",
                        "current_medications": "Metformin"})
        app.info_panel.refresh(patient); app.update()
        assert app.info_panel._name_lbl.cget("fg") == red
        assert app.info_panel._health_lbls["diseases"].cget("fg") == red
        assert app.info_panel._health_lbls["allergies"].cget("fg") == red
        assert app.info_panel._health_lbls["current_medications"].cget("fg") != red
        clean = {"file_number": None, "full_name": "Clean",
                 "diseases": "", "allergies": "", "current_medications": ""}
        app.info_panel.refresh(clean); app.update()
        assert app.info_panel._name_lbl.cget("fg") != red
        assert app.info_panel._health_lbls["diseases"].cget("fg") != red
    finally:
        app.destroy()

# Round 22: the old test_panels_reachable_at_820_en_ar (Rx print
# buttons + Add-image reachable by scrolling the shell column)
# is superseded -- its coverage lives in tests/test_r22_layout.py
# (test_rx_panel_reachable_at_820_en_ar: the Rx section's compose
# controls + history + Print row in the shell column, EN + AR).
