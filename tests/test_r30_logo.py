"""Round 30 (worker B): editable centre logo — storage (setting
`centre_logo`, file in DATA_DIR as centre_logo.<ext>, PIL-validated),
Settings logo row (GUI, skips without a display), printed header on
all four documents (report via pdf_common.report_header, Rx, invoice,
referral) EN + AR; no logo -> no image. Image check = raw XObject
scan (no pypdf in the venv); name text via pdftotext when present."""
import contextlib, importlib, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image
from src.config.settings import DATA_DIR
from src.models.database import get_setting, init_db, set_setting
from src.reports.centre_logo import clear_logo, get_logo_path, logo_flowable, set_logo
from src.reports.invoice_pdf import build_invoice_pdf
from src.reports.pdf_report import create_patient_pdf
from src.reports.referral_pdf import build_referral_pdf
from src.reports.rx_report import build_rx_pdf
CLINIC = "Smile Clinic R30"
_TMP = Path(tempfile.mkdtemp(prefix="r30_logo_"))
PATIENT = {"file_number": 77, "full_name": "Test Patient", "birth_date_greg": "1990-05-15",
           "age_years": 36, "age_months": 5, "age_days": 21, "nationality": "Syrian",
           "mobile1": "0791234567", "mobile2": "", "emergency_phone": "", "address": "Damascus",
           "created_at": "2026-11-05", "diseases": ""}
_RX = {"date": "2026-11-19", "doctor": "fady"}
_ITEMS = [{"generic": "Amoxicillin", "dose": "500 mg", "frequency": "3x daily",
           "duration_days": "5", "instructions": "After food"}]
_ROWS = [{"visit_date": "2026-11-01", "updated_at": "2026-11-01 09:30:00", "tooth_number": "16",
          "total_cost": 400000, "paid_amount": 250000, "currency": "SYP", "id": 1}]
_TOTALS = {"total": 600000.0, "paid": 370000.0, "remaining": 230000.0}
_REF = {"id": 5, "patient_id": 77, "from_user": "fady", "to_doctor": "Dr. Sami Haddad",
        "note": "Please evaluate.", "created_at": "2026-11-17 09:15:00"}

def _img(name, size=(380, 110), fmt=None, color=(124, 58, 237)):
    p = _TMP / name
    Image.new("RGB", size, color).save(p, format=fmt)
    return p

def _has_image(path):
    return b"/Subtype /Image" in Path(path).read_bytes()

def _pdf_text(path):
    if not shutil.which("pdftotext"):
        return None
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout

@contextlib.contextmanager
def _logo(src=None):
    """Set clinic name (+ logo when src given); restore both after."""
    init_db()
    prev = get_setting("clinic_name", "") or ""
    clear_logo()
    set_setting("clinic_name", CLINIC)
    if src is not None:
        set_logo(src)
    try:
        yield
    finally:
        clear_logo(); set_setting("clinic_name", prev)

def _build_all(lang, root):
    root.mkdir(parents=True, exist_ok=True)
    return {"report": create_patient_pdf(PATIENT, [], [], [], [], [], language=lang, user_name="fady", out_dir=root / "rep"),
            "rx": build_rx_pdf(PATIENT, _RX, _ITEMS, lang=lang, clinic_name=CLINIC, out_dir=root / "rx"),
            "invoice": build_invoice_pdf(PATIENT, _ROWS, _TOTALS, "detailed", lang, CLINIC, root / "inv.pdf", currency="SYP"),
            "referral": build_referral_pdf(PATIENT, _REF, lang=lang, clinic_name=CLINIC, out_path=root / "ref")}

def _rejected(src):
    try:
        set_logo(src)
    except ValueError:
        return
    raise AssertionError(f"set_logo accepted {src.name}")

def test_logo_storage_roundtrip_persistence_and_jpg():
    src, jpg = _img("roundtrip.png"), _img("photo.jpg", fmt="JPEG")
    with _logo():
        assert set_logo(src) == "centre_logo.png"
        assert get_setting("centre_logo", "") == "centre_logo.png"
        path = get_logo_path()
        assert path is not None and path.read_bytes() == src.read_bytes()
        import src.reports.centre_logo as cl
        importlib.reload(cl)  # restart simulation: fresh module resolves
        assert cl.get_logo_path() is not None and cl.get_logo_path().read_bytes() == src.read_bytes()
        assert set_logo(jpg) == "centre_logo.jpg"  # extension switch
        assert get_logo_path().suffix == ".jpg"
        assert not (DATA_DIR / "centre_logo.png").exists()
        clear_logo()
        assert get_logo_path() is None and (get_setting("centre_logo", "") or "") == ""
        assert not (DATA_DIR / "centre_logo.jpg").exists()

def test_logo_corrupt_rejected_stores_nothing():
    bad = _TMP / "fake.png"
    bad.write_bytes(b"this is not an image at all")
    gif = _img("anim.gif", fmt="GIF")
    with _logo():
        for src in (bad, gif):
            _rejected(src)
            assert (get_setting("centre_logo", "") or "") == "" and get_logo_path() is None
        set_logo(_img("good.png"))  # corrupt re-pick keeps a working logo
        before = get_logo_path().read_bytes()
        _rejected(bad)
        assert get_setting("centre_logo", "") == "centre_logo.png"
        assert get_logo_path().read_bytes() == before

def test_logo_flowable_sizing_and_header_order():
    from reportlab.lib.units import mm
    from reportlab.platypus import Image as RLImage
    from src.reports.pdf_common import report_header
    from src.reports.pdf_styles import styles
    with _logo(_img("wide.png", size=(760, 440))):
        flow = logo_flowable()
        assert flow is not None and flow.hAlign == "CENTER"
        assert flow.drawWidth <= 38 * mm + 0.5 and flow.drawHeight <= 22 * mm + 0.5
        assert abs(flow.drawWidth - 38 * mm) < 0.5  # width is the cap
        st = styles()
        for lang, bil in (("en", False), ("ar", False), ("en", True)):
            assert isinstance(report_header(st, lang, bilingual=bil)[0], RLImage), (lang, bil)
    with _logo():
        assert logo_flowable() is None
        assert not isinstance(report_header(styles(), "en")[0], RLImage)

def test_pdfs_logo_image_and_name_en_ar():
    with _logo(_img("header.png")):
        for lang in ("en", "ar"):
            for kind, path in _build_all(lang, _TMP / f"with_{lang}").items():
                assert _has_image(path), (lang, kind, path)
                txt = _pdf_text(path)
                assert txt is None or CLINIC in txt, (lang, kind)
    with _logo():  # no logo -> documents exactly as before: no image
        for lang in ("en", "ar"):
            for kind, path in _build_all(lang, _TMP / f"no_{lang}").items():
                assert not _has_image(path), (lang, kind, path)
                txt = _pdf_text(path)
                assert txt is None or CLINIC in txt, (lang, kind)

def _tk_root():
    try:
        import tkinter as tk
        root = tk.Tk(); root.withdraw(); return root
    except Exception:
        return None

def test_print_preview_pdf_contains_logo():
    """PrintPreview._rebuild uses the patient builder; its PDF has the logo."""
    root = _tk_root()
    if root is None:
        print("SKIP preview logo test (no display)")
        return
    from src.reports.print_preview import PrintPreview
    with _logo(_img("preview.png")):
        def build(lang):
            return create_patient_pdf(PATIENT, [], [], [], [], [], language=lang, user_name="fady", out_dir=_TMP / "prev")
        win = PrintPreview(root, "Logo Patient", build, "en")
        try:
            root.update_idletasks()
            assert win.pdf_path and Path(win.pdf_path).exists()
            assert _has_image(win.pdf_path)
        finally:
            win.destroy()
            root.destroy()

def test_settings_logo_row_gui():
    """Settings row: pick stores + previews at once, an invalid pick
    errors and stores nothing, Remove clears (round 30)."""
    import src.ui.settings_storage_ui as SS
    from tests.test_settings_storage_r16 import _build_settings, isolated_db
    good, bad = _img("gui_logo.png"), _TMP / "gui_fake.png"
    bad.write_bytes(b"nope, not an image")
    with isolated_db():
        tab, root = _build_settings("en")
        if tab is None:
            print("SKIP settings logo GUI (no display)")
            return
        errors = []
        old_err, old_ask = SS.messagebox.showerror, SS.filedialog.askopenfilename
        SS.messagebox.showerror = lambda *a, **k: errors.append(a)
        try:
            SS.clear_logo()
            SS.refresh_logo_preview(tab)
            assert tab._logo_preview.cget("text") != ""  # 'No logo'
            assert "Add" in str(tab._logo_btn.cget("text"))
            SS.filedialog.askopenfilename = lambda *a, **k: str(bad)
            SS.pick_logo(tab)
            assert errors, "invalid logo pick showed no error"
            assert (get_setting("centre_logo", "") or "") == "" and SS.get_logo_path() is None
            SS.filedialog.askopenfilename = lambda *a, **k: str(good)
            SS.pick_logo(tab)
            assert get_setting("centre_logo", "") == "centre_logo.png"
            assert SS.get_logo_path() is not None
            assert "Change" in str(tab._logo_btn.cget("text"))
            SS.remove_logo(tab)
            assert (get_setting("centre_logo", "") or "") == "" and SS.get_logo_path() is None
        finally:
            SS.messagebox.showerror, SS.filedialog.askopenfilename = old_err, old_ask
            SS.clear_logo()
            with contextlib.suppress(Exception):
                root.destroy()
