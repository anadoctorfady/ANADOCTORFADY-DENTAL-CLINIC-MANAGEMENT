"""Round 16 Rx direct-print button (worker D, 2026-11-11).

With the printing worker's preview module present, the button calls
show_print_preview(parent, title, build_pdf_fn, lang); without it the
button must not crash -- it saves the prescription PDF and says where.
GUI tests skip gracefully when no display is available."""
import re
import sys
import tkinter as tk
import types
from pathlib import Path

from src.config.settings import REPORTS
from src.models.database import get_connection, init_db
from src.models.prescriptions import save_prescription
import src.ui.rx_print as rxprint
from src.ui.clinical import ClinicalTab

ITEMS = [{"generic": "Amoxicillin", "brand": "Amoxil", "dose": "500 mg",
          "frequency": "3x daily", "duration_days": "5", "instructions": ""},
         {"generic": "Ibuprofen", "brand": "", "dose": "200 mg",
          "frequency": "3x daily", "duration_days": "3", "instructions": ""}]


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


def _root():
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP (no display)")
        return None
    root.withdraw()
    return root


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


def _select_first_history(rx, fid):
    rx.load(fid)
    kids = rx.tree_hist.get_children()
    assert kids, "history empty"
    rx.tree_hist.selection_set(kids[0])


def test_rx_print_button_opens_preview():
    """Button 13b: with the preview module present, clicking Print
    Prescription calls show_print_preview(parent, title, build_pdf_fn,
    lang) with the app language -- and the builder makes a real PDF."""
    root = _root()
    if root is None:
        return
    fid = _seed_patient()
    save_prescription(fid, ITEMS, doctor="fady")
    calls = {}
    stub = types.ModuleType("src.reports.print_preview")

    def fake_preview(parent, title, build_pdf_fn, lang):
        calls.update(parent=parent, title=title, lang=lang)
        calls["pdf"] = build_pdf_fn(lang)
    stub.show_print_preview = fake_preview
    sys.modules["src.reports.print_preview"] = stub
    try:
        tab = _make_tab(root, fid)
        rx = tab.rx_section
        assert "Print Prescription" in rx.print_direct_btn.cget("text")
        _select_first_history(rx, fid)
        rx.print_direct_btn.invoke()
        root.update_idletasks()
        assert calls.get("lang") == "en", calls
        assert "Prescription" in calls.get("title", ""), calls
        assert calls.get("parent") is rx
        assert Path(calls["pdf"]).exists(), calls
        Path(calls["pdf"]).unlink(missing_ok=True)
    finally:
        sys.modules.pop("src.reports.print_preview", None)
        _cleanup(fid)
        root.destroy()


def test_rx_print_button_without_preview_saves_pdf():
    """Button 13b fallback: with NO preview module, the button must
    not crash -- it saves the prescription PDF and says where.
    (Simulated with a module object that has no show_print_preview,
    so the lazy `from ... import ...` raises ImportError -- the same
    as the module not having landed yet.)"""
    root = _root()
    if root is None:
        return
    fid = _seed_patient()
    save_prescription(fid, ITEMS, doctor="fady")
    seen = {}
    orig_info = rxprint.messagebox.showinfo
    rxprint.messagebox.showinfo = lambda *a, **k: seen.setdefault("msg", a[1] if len(a) > 1 else "")
    stub = types.ModuleType("src.reports.print_preview")  # no show_print_preview attr
    sys.modules["src.reports.print_preview"] = stub
    try:
        tab = _make_tab(root, fid)
        rx = tab.rx_section
        _select_first_history(rx, fid)
        rx.print_direct_btn.invoke()
        root.update_idletasks()
        m = re.search(r"(ANADOCTORFADY_RX_.*\.pdf)\s*$", seen.get("msg", ""))
        assert m, seen
        out = None
        for cand in (Path(REPORTS) / m.group(1), Path(m.group(1))):
            if cand.exists():
                out = cand
        assert out is not None, seen
        out.unlink(missing_ok=True)
    finally:
        sys.modules.pop("src.reports.print_preview", None)
        rxprint.messagebox.showinfo = orig_info
        _cleanup(fid)
        root.destroy()


def test_rx_print_button_opens_real_preview():
    """End-to-end with worker C's real preview module: the button opens
    a PrintPreview window whose text shows the prescribed drug."""
    root = _root()
    if root is None:
        return
    fid = _seed_patient()
    save_prescription(fid, ITEMS, doctor="fady")
    win = None
    try:
        tab = _make_tab(root, fid)
        rx = tab.rx_section
        _select_first_history(rx, fid)
        rx.print_direct_btn.invoke()
        root.update_idletasks()

        def _walk(w):
            yield w
            for ch in w.winfo_children():
                yield from _walk(ch)
        wins = [w for w in _walk(root)
                if isinstance(w, tk.Toplevel) and hasattr(w, "pdf_path")]
        assert wins, "no PrintPreview window opened"
        win = wins[0]
        texts = [w.get("1.0", tk.END) for w in _walk(win)
                 if isinstance(w, tk.Text)]
        assert any("Amoxicillin" in t for t in texts), texts
        assert Path(win.pdf_path).exists()
    finally:
        if win is not None:
            try:
                Path(win.pdf_path).unlink(missing_ok=True)
            except Exception:
                pass
            win.destroy()
            root.update_idletasks()
        _cleanup(fid)
        root.destroy()
