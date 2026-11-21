"""Round 16 prescriptions (worker D, 2026-11-11).

Item 12: add-drug dialog fits its content (was clipped at 480px) and
the category selector comes BEFORE the drug fields.
Item 13: (a) a saved prescription appears in the Rx history at
once (bug: it stayed empty until the patient was re-selected).
Round 22: the right-side Rx summary panel this originally pinned
is superseded by the full Prescriptions section, so the surface
asserted below is tab.rx_section.tree_hist (see _hist_rx). GUI
tests skip gracefully when no display is available. The
direct-print button and the single-language Rx PDF are covered
by tests/test_rx_print_r16.py and tests/test_rx_pdf_r16.py."""
import tkinter as tk

from src.models.database import get_connection, init_db
import src.ui.prescriptions as rxmod
import src.ui.rx_print as rxprint
from src.ui.add_drug import open_add_drug_dialog
from src.ui.clinical import ClinicalTab


def _seed_patient():
    init_db()
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name,current_medications,allergies) VALUES(?,?,?,?)",
                ("R16", "R16 Rx Test", "", ""))
    fid = cur.lastrowid; conn.commit(); conn.close()
    return fid


def _cleanup(fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM prescription_items WHERE prescription_id IN (SELECT id FROM prescriptions WHERE patient_file=?)", (fid,))
    cur.execute("DELETE FROM prescriptions WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()


def _make_tab(root, fid):
    class FakeApp:
        lang = "en"
        current_patient = {"full_name": "R16 Rx Test", "file_number": fid,
                           "current_medications": "", "allergies": ""}
        current_user = "fady"
        current_role = "admin"
        def chart_teeth(self):
            return []
        def refresh_clinical(self):
            pass
    tab = ClinicalTab(root, FakeApp())
    tab.pack()
    root.update_idletasks()
    tab.load(fid)
    root.update_idletasks()
    return tab


def _silence():
    orig = {}
    for mod in (rxmod, rxprint):
        for name in ("showinfo", "showwarning", "showerror"):
            orig[(mod, name)] = getattr(mod.messagebox, name)
            setattr(mod.messagebox, name, lambda *a, **k: None)
    return orig


def _restore(orig):
    for (mod, name), fn in orig.items():
        setattr(mod.messagebox, name, fn)


def _root():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP (no display)")
        return None
    root.withdraw()
    return root


def _hist_rx(tab):
    """Round 22 replacement for the old _panel_rx() helper, which
    read tab.panel_texts["rx"]: the joined values of the Rx
    section history rows (id, date, doctor, drugs), or "" when
    the history is empty."""
    tree = tab.rx_section.tree_hist
    return " ".join(str(v) for i in tree.get_children()
                    for v in tree.item(i, "values"))


def test_rx_save_refreshes_right_panel():
    """Bug 13a repro: before the fix the history stayed empty
    after saving, even though the Rx was in the DB. Round 22: the
    old premise ('No prescriptions yet' in the right-side panel)
    becomes 'tree_hist has no rows before saving' -- the panel
    itself no longer exists."""
    root = _root()
    if root is None:
        return
    fid = _seed_patient()
    orig = _silence()
    try:
        tab = _make_tab(root, fid)
        assert not tab.rx_section.tree_hist.get_children()
        assert _hist_rx(tab) == ""
        rx = tab.rx_section
        rx.drug_var.set("Amoxicillin")
        rx.add_item()
        assert rx.items and rx.items[0]["generic"] == "Amoxicillin"
        rx.save()
        root.update_idletasks()
        assert len(rx.tree_hist.get_children()) >= 1  # history refreshed
        assert "Amoxicillin" in _hist_rx(tab)
    finally:
        _restore(orig)
        _cleanup(fid)
        root.destroy()


def test_add_drug_dialog_fits_content():
    """Bug 12 (clipping): the old 480px window cut the Save/Cancel
    buttons (content needs ~536px). The Save button must lie fully
    inside the window now."""
    root = _root()
    if root is None:
        return
    try:
        win = open_add_drug_dialog(root)
        root.update_idletasks()
        btn = win._ad_save_btn
        bottom = btn.winfo_rooty() + btn.winfo_height()
        assert bottom <= win.winfo_rooty() + win.winfo_height(), \
            f"Save button bottom {bottom} outside window {win.winfo_height()}px"
        assert win.winfo_height() >= win._ad_body.winfo_reqheight()
        assert win._ad_body.winfo_reqheight() > 480  # content is tall
        win.destroy()
        root.update_idletasks()
    finally:
        root.destroy()


def test_add_drug_category_before_drug():
    """Bug 12 (order): the category selector must be created (and so
    tabbed to) BEFORE the first drug-name field."""
    root = _root()
    if root is None:
        return
    try:
        win = open_add_drug_dialog(root)
        root.update_idletasks()
        kids = win._ad_body.winfo_children()
        assert kids.index(win._ad_cat_combo) < kids.index(win._ad_entries["generic_en"])
        labels = [w.cget("text") for w in kids if type(w) is tk.Label]
        from src.config.strings import t
        assert labels.index(t("dlg.ad_category", "en")) < labels.index(t("dlg.ad_f_generic_en", "en"))
        win.destroy()
        root.update_idletasks()
    finally:
        root.destroy()


