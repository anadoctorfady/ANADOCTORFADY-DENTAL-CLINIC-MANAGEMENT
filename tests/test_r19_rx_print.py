"""Round 19 Rx print gibberish (owner item 6). Root causes: (1) the
Rx preview had NO preview_text, so it fell back to extract_pdf_text(),
which needs the external pdftotext binary -- absent from the Windows
EXE, its raw-stream fallback scraped embedded font programs and
showed control-character gibberish in BOTH languages; (2) mixed-
script paragraphs were set in ONE font whose cmap lacks the other
script (NotoNaskhArabic has NO Latin glyphs; Helvetica no Arabic),
so Latin runs vanished from the AR PDF and Arabic values from the
bilingual PDF -- while pdftotext still extracted them, so the
round-16 text tests passed. Here: text layer, per-span FONT
assignment (PyMuPDF), cmap facts, extractor, owner's real button
with pdftotext simulated absent."""
import tempfile
import tkinter as tk
from pathlib import Path
from src.models.database import get_connection, init_db
from src.models.prescriptions import save_prescription
from src.reports.prescription_pdf import create_prescription_pdf
import src.reports.prescription_pdf as _old_mod
from src.reports.rx_report import build_rx_pdf, _para
from src.ui.clinical import ClinicalTab

ITEMS = [{"generic": "Amoxicillin", "brand": "Amoxil", "dose": "500 mg",
          "frequency": "3x daily", "duration_days": "5", "instructions": "After meals"},
         {"generic": "Diclofenac potassium", "brand": "", "dose": "50 mg",
          "frequency": "2x daily", "duration_days": "3", "instructions": "بعد الطعام"}]
PAT = {"file_number": 999, "full_name": "Ahmad Haddad", "age_years": 36, "nationality": "Syrian"}
PAT_AR = {"file_number": 998, "full_name": "أحمد حداد", "age_years": 36, "nationality": "سوري"}
RX = {"date": "2026-11-14", "doctor": "fady", "notes": "Take with water"}
_AR_CH = lambda c: "\u0600" <= c <= "\u06ff" or "\ufb50" <= c <= "\ufeff"  # noqa: E731

def _text(path):
    try:
        from pypdf import PdfReader
        return "\n".join(pg.extract_text() or "" for pg in PdfReader(str(path)).pages)
    except ImportError:
        import shutil, subprocess
        if not shutil.which("pdftotext"):
            return None
        return subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True).stdout

def _spans(path):
    try:
        import pymupdf
    except ImportError:
        return None
    doc = pymupdf.open(str(path)); out = []
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                out += [(s["font"], s["text"]) for s in line["spans"]]
    return out

def _build(lang):
    return build_rx_pdf(PAT, RX, ITEMS, lang=lang, clinic_name="", out_dir=tempfile.mkdtemp())

def test_r19_rx_pdf_en_text_layer():
    out = _build("en")
    try:
        text = _text(out)
        if text is None:
            return
        for needle in ("Amoxicillin", "Diclofenac potassium", "500 mg", "50 mg",
                       "3x daily", "2x daily", "After meals"):
            assert needle in text, (needle, text[:400])
    finally:
        Path(out).unlink(missing_ok=True)

def test_r19_rx_pdf_ar_text_layer():
    out = _build("ar")
    try:
        text = _text(out)
        if text is None:
            return
        for needle in ("Amoxicillin", "Diclofenac potassium", "500 mg", "3x daily"):
            assert needle in text, (needle, text[:400])
    finally:
        Path(out).unlink(missing_ok=True)

def test_r19_font_assignment_matches_cmap():
    """Every rendered span must sit in a font that HAS its glyphs."""
    from reportlab.pdfbase import pdfmetrics
    from src.reports.pdf_styles import FONT_AR, FONT_AR_B
    for name in (FONT_AR, FONT_AR_B):
        if name.startswith("Noto"):
            face = pdfmetrics.getFont(name).face
            assert face.charToGlyph.get(ord("A"), 0) == 0
            assert face.charToGlyph.get(ord("ا"), 0) != 0
    for lang in ("en", "ar"):
        out = _build(lang)
        try:
            spans = _spans(out)
            if spans is None:
                return
            for font, txt in spans:
                if "Noto" in font:
                    assert not any("A" <= c <= "Z" or "a" <= c <= "z" for c in txt), (lang, font, txt)
                if "Helvetica" in font:
                    assert not any(_AR_CH(c) for c in txt), (lang, font, txt)
            joined = "".join(t for _, t in spans)
            assert "ANADOCTORFADY" in joined and "Amoxicillin" in joined, lang
        finally:
            Path(out).unlink(missing_ok=True)

def test_r19_para_wraps_latin_runs():
    import re
    for raw, needle in (("Issued: fady | ANADOCTORFADY وصفة", "ANADOCTORFADY"),
                        ("Notes: Take with water ملاحظات", "Take with water")):
        p = _para(raw, "ar")
        segs = re.findall(r'<font name="Helvetica">(.*?)</font>', p.text)
        assert any(needle in s for s in segs), p.text

def test_r19_old_builder_arabic_patient():
    """Bilingual builder: Arabic name/instructions in the Arabic font."""
    old = _old_mod.REPORTS; _old_mod.REPORTS = Path(tempfile.mkdtemp())
    try:
        out = create_prescription_pdf(PAT_AR, RX, ITEMS, language="ar", user_name="fady")
    finally:
        _old_mod.REPORTS = old
    try:
        spans = _spans(out)
        if spans is None:
            return
        noto = "".join(t for f, t in spans if "Noto" in f)
        helv = "".join(t for f, t in spans if "Helvetica" in f)
        assert not any(_AR_CH(c) for c in helv), helv[:300]
        assert len([c for c in noto if _AR_CH(c)]) >= 8, noto[:200]
        assert "Amoxicillin" in helv, helv[:300]
    finally:
        Path(out).unlink(missing_ok=True)

def _seed():
    init_db(); conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO patients(first_name,full_name,current_medications,allergies) VALUES(?,?,?,?)",
                ("R19", "R19 Rx Test", "", ""))
    fid = cur.lastrowid; conn.commit(); conn.close()
    save_prescription(fid, ITEMS, doctor="fady")
    return fid

def _cleanup(fid):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM prescription_items WHERE prescription_id IN (SELECT id FROM prescriptions WHERE patient_file=?)", (fid,))
    cur.execute("DELETE FROM prescriptions WHERE patient_file=?", (fid,))
    cur.execute("DELETE FROM patients WHERE file_number=?", (fid,))
    conn.commit(); conn.close()

def test_r19_button_preview_without_pdftotext():
    """Owner's entry point with pdftotext ABSENT (Windows EXE)."""
    from src.reports import report_files
    fid = _seed(); orig = report_files.shutil.which
    report_files.shutil.which = lambda x: None
    try:
        for lang in ("en", "ar"):
            try:
                root = tk.Tk()
            except tk.TclError:
                print("SKIP (no display)"); return
            root.withdraw()

            class FakeApp:
                current_patient = {"full_name": "R19 Rx Test", "file_number": fid,
                                   "current_medications": "", "allergies": ""}
                current_user = "fady"; current_role = "admin"
                def chart_teeth(self): return []
                def refresh_clinical(self): pass
            FakeApp.lang = lang
            tab = ClinicalTab(root, FakeApp()); tab.pack(); root.update_idletasks()
            tab.load(fid); root.update_idletasks()
            rx = tab.rx_section
            rx.tree_hist.selection_set(rx.tree_hist.get_children()[0])
            rx.print_direct_btn.invoke(); root.update_idletasks()

            def _walk(w):
                yield w
                for ch in w.winfo_children():
                    yield from _walk(ch)
            wins = [w for w in _walk(root) if isinstance(w, tk.Toplevel) and hasattr(w, "pdf_path")]
            assert wins, f"no preview opened ({lang})"
            body = "\n".join(w.get("1.0", tk.END) for w in _walk(wins[0]) if isinstance(w, tk.Text))
            assert "Amoxicillin" in body and "500 mg" in body, (lang, body[:300])
            assert not [c for c in body if ord(c) < 32 and c not in "\n\t"], (lang, body[:300])
            Path(wins[0].pdf_path).unlink(missing_ok=True)
            wins[0].destroy(); root.destroy()
    finally:
        report_files.shutil.which = orig; _cleanup(fid)

def test_r19_extract_fallback_never_gibberish():
    """The extractor fallback must not return font-binary any more."""
    from src.reports import report_files
    out = _build("en"); orig = report_files.shutil.which
    report_files.shutil.which = lambda x: None
    try:
        txt = report_files.extract_pdf_text(out)
    finally:
        report_files.shutil.which = orig; Path(out).unlink(missing_ok=True)
    assert not [c for c in txt if ord(c) < 32 and c not in "\n\t"], txt[:200]
