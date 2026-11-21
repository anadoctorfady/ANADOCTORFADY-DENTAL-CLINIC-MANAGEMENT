"""Round 25 (item 3, documents part): storage paths must never
appear in the UI. The patient report's old direct flow, the print
preview's Print/Save confirmations, the prescriptions tab's old
direct PDF build and the Rx no-preview fallback all showed the
FULL path of a generated file. Now the patient report opens the
print preview like every other document, the prescriptions
action routes through the same preview flow, and every remaining
confirmation shows the file NAME only. Each test captures every
messagebox argument of its flow and asserts none contains the
reports directory, a temp dir, or a "/"-joined path to the file
(the bare name is OK). GUI parts skip without a display."""
import sys
import tempfile
import tkinter as tk
import types
from pathlib import Path

from src.config.settings import REPORTS
from src.models.database import get_connection, init_db

_TMP = Path(tempfile.mkdtemp(prefix="r25_paths_"))
PAT = {"file_number": 0, "full_name": "R25 Path Test",
       "birth_date_greg": "1990-05-15", "birth_date_hijri": "",
       "age_years": 36, "age_months": 0, "age_days": 0,
       "nationality": "Syrian", "mobile1": "", "mobile2": "",
       "emergency_phone": "", "address": "", "created_at": "2026-11-18",
       "diseases": ""}


def _assert_clean(msgs, *paths):
    for m in msgs:
        s = str(m)
        assert str(REPORTS) not in s and str(_TMP) not in s, s
        assert "/tmp/" not in s and "/home/" not in s, s
        for p in paths:
            assert str(p) not in s, s


class _Msgs:
    """Swap tkinter.messagebox funcs for recorders; restore()."""
    def __init__(self):
        import tkinter.messagebox as mb
        self.mb = mb; self.calls = []
        self.old = {n: getattr(mb, n) for n in ("showinfo", "showwarning", "showerror")}
        for n in self.old:
            setattr(mb, n, lambda *a, _n=n, **k: self.calls.append((_n, a)))
    def restore(self):
        for n, f in self.old.items():
            setattr(self.mb, n, f)
    @property
    def args(self):
        return [a for _n, a in self.calls]


def _seed_patient():
    init_db(); conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name,"
                "birth_date_greg,nationality) VALUES(?,?,?,?)",
                ("R25", PAT["full_name"], "1990-05-15", "Syrian"))
    fid = cur.lastrowid; conn.commit(); conn.close(); return fid


def _cleanup_patient(fid):
    conn = get_connection()
    conn.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()


def test_print_pdf_direct_opens_preview_no_path():
    """The (bilingual) patient-report flow OPENS the preview; its
    build callback produces the PDF in a temp folder; no message
    is shown at all, so no path can leak."""
    import src.reports.print_preview as pp
    from src.ui.print_pdf_direct import print_pdf_direct
    fid = _seed_patient(); cap = {}; orig = pp.show_print_preview
    pp.show_print_preview = lambda *a, **k: cap.update(args=a, kwargs=k) or "PREVIEW"
    msgs = _Msgs()
    try:
        class App:
            current_patient = {"file_number": fid}
            lang = "en"; current_user = "fady"
            def chart_teeth(self): return []
        for bilingual in (True, False):
            cap.clear()
            assert print_pdf_direct(App(), bilingual=bilingual) == "PREVIEW"
            assert cap, bilingual
            built = Path(cap["args"][2]("en"))
            assert built.exists() and built.name.startswith("ANADOCTORFADY_R25"), built
            assert str(REPORTS) not in str(built), built  # temp folder
            lines = cap["kwargs"]["preview_text"]("en")
            assert any(PAT["full_name"] in ln for ln in lines)
            built.unlink(missing_ok=True)
        assert msgs.calls == [], msgs.calls  # the flow shows no dialog
        _assert_clean(msgs.args)
    finally:
        pp.show_print_preview = orig
        msgs.restore()
        _cleanup_patient(fid)


def test_print_preview_print_save_show_name_only():
    """PrintPreview._on_print / _on_save confirmations carry the
    file NAME only -- never the built file's full path."""
    try:
        root = tk.Tk()
    except tk.TclError:
        print("SKIP preview path test (no display)")
        return
    root.geometry("900x700+0+0")  # mapped: a withdrawn root unmaps the preview (r16)
    import src.reports.print_preview as pp
    from tests.test_r16_print import _make_pdf
    msgs = _Msgs()
    orig_print, orig_ask = pp.print_pdf_file, pp.filedialog.asksaveasfilename
    dest = _TMP / "chosen_name.pdf"
    pp.print_pdf_file = lambda p: ("ok", "")
    pp.filedialog.asksaveasfilename = lambda **k: str(dest)
    try:
        def build(lang):
            return _make_pdf(out_dir=_TMP, language=lang)
        win = pp.show_print_preview(root, "Test Patient", build, "en")
        root.update_idletasks()
        built = Path(win.pdf_path)
        assert built.exists()
        win._on_print()
        infos = [a for n, a in msgs.calls if n == "showinfo"]
        assert infos and infos[-1][1] == built.name, infos
        _assert_clean([x for a in msgs.args for x in a], built)
        win2 = pp.show_print_preview(root, "Test Patient", build, "en")
        root.update_idletasks()
        win2._on_save()
        infos = [a for n, a in msgs.calls if n == "showinfo"]
        assert infos and infos[-1][1] == dest.name, infos
        _assert_clean([x for a in msgs.args for x in a], dest)
        assert dest.exists()
    finally:
        pp.print_pdf_file, pp.filedialog.asksaveasfilename = orig_print, orig_ask
        msgs.restore()
        root.destroy()


def test_prescriptions_print_selected_uses_preview_flow():
    """PrescriptionsTab.print_selected delegates to the preview
    flow (rx_print.print_rx_preview); it builds nothing itself
    and shows no message (hence no path) of its own."""
    import src.ui.prescriptions as prx
    seen = []; orig = prx.print_rx_preview
    prx.print_rx_preview = lambda tab: seen.append(tab)
    msgs = _Msgs()
    try:
        dummy = object()
        prx.PrescriptionsTab.print_selected(dummy)
        assert seen == [dummy]
        assert msgs.calls == [], msgs.calls
        _assert_clean(msgs.args)
    finally:
        prx.print_rx_preview = orig
        msgs.restore()


def test_rx_print_fallback_shows_name_only():
    """rx_print's no-preview fallback formats the saved message
    with the file NAME only (was: the full path)."""
    import src.ui.rx_print as rp
    key = "src.reports.print_preview"; saved_mod = sys.modules.get(key)
    sys.modules[key] = types.ModuleType(key)  # importing the name fails
    msgs = _Msgs()
    orig_sel = rp._selected_rx
    rp._selected_rx = lambda tab: (
        {"date": "2026-11-18", "doctor": "fady"},
        [{"generic": "Amoxicillin", "dose": "500 mg",
          "frequency": "3x daily", "duration_days": "5", "instructions": ""}])
    before = set(Path(REPORTS).glob("ANADOCTORFADY_RX_R25*"))
    try:
        class Tab:
            lang = "en"
            def _patient(self): return dict(PAT, file_number=4242)
        rp.print_rx_preview(Tab())
        infos = [a for n, a in msgs.calls if n == "showinfo"]
        assert infos, msgs.calls
        msg = str(infos[-1][1])
        new = set(Path(REPORTS).glob("ANADOCTORFADY_RX_R25*")) - before
        assert new, "fallback built no PDF"
        name = new.pop().name
        assert name in msg and msg.endswith(name), msg
        assert "/" not in msg.replace(name, ""), msg
        _assert_clean([msg])
        for p in Path(REPORTS).glob("ANADOCTORFADY_RX_R25*"):
            p.unlink(missing_ok=True)
    finally:
        rp._selected_rx = orig_sel
        msgs.restore()
        if saved_mod is not None:
            sys.modules[key] = saved_mod
        else:
            sys.modules.pop(key, None)
