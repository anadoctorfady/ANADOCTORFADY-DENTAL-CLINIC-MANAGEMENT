"""Round 16 single-language Rx PDF (worker D, 2026-11-11).

build_rx_pdf() in src/reports/rx_report.py: ONE language only (the
app language), clinic name (setting `clinic_name`) on TOP with
ANADOCTORFADY under it, smaller, both black, B&W-clear. Text is
checked with pdftotext; tests skip the text check when it is absent.
The new strings themselves are covered by test_rx16_strings_bilingual."""
import shutil
import subprocess
from pathlib import Path

from src.config.strings_r16_rx import EN as RX16_EN, AR as RX16_AR, rx16_t
from src.reports.rx_report import build_rx_pdf

ITEMS = [{"generic": "Amoxicillin", "brand": "Amoxil", "dose": "500 mg",
          "frequency": "3x daily", "duration_days": "5", "instructions": ""},
         {"generic": "Ibuprofen", "brand": "", "dose": "200 mg",
          "frequency": "3x daily", "duration_days": "3", "instructions": ""}]


def _has_arabic(text):
    """Arabic in any form: logical (U+0600-U+06FF) or already-shaped
    presentation forms (U+FB50-U+FDFF, U+FE70-U+FEFF) -- the PDF
    builder reshapes, so extracted text is mostly presentation forms."""
    return any("\u0600" <= ch <= "\u06ff" or "\ufb50" <= ch <= "\ufdff"
               or "\ufe70" <= ch <= "\ufeff" for ch in str(text))


def _pdf_text(path):
    if not shutil.which("pdftotext"):
        print("SKIP pdf text check (no pdftotext)")
        return None
    r = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _build(lang):
    return build_rx_pdf({"file_number": 999, "full_name": "R16 PDF Test",
                         "age_years": 36},
                        {"date": "2026-11-11", "doctor": "fady"}, ITEMS,
                        lang=lang, clinic_name="Test Clinic XYZ")


def test_rx_pdf_single_language_en():
    out = _build("en")
    try:
        assert Path(out).exists() and Path(out).stat().st_size > 1000
        text = _pdf_text(out)
        if text is None:
            return
        for needle in ("Test Clinic XYZ", "ANADOCTORFADY", "Amoxicillin", "Ibuprofen"):
            assert needle in text, (needle, text[:500])
        assert not _has_arabic(text), text[:500]
    finally:
        Path(out).unlink(missing_ok=True)


def test_rx_pdf_single_language_ar():
    out = _build("ar")
    try:
        text = _pdf_text(out)
        if text is None:
            return
        assert "ANADOCTORFADY" in text and "Amoxicillin" in text, text[:800]
        assert "Test Clinic XYZ" in text, text[:800]
        assert _has_arabic(text), text[:500]
        assert "■" not in text, text[:800]  # no tofu boxes: Arabic must use the Arabic font
        for en_label in ("Patient", "Drug", "Doctor", "Prescription", "Duration"):
            assert en_label not in text, (en_label, text[:500])
    finally:
        Path(out).unlink(missing_ok=True)


def test_rx16_strings_bilingual():
    for key in RX16_EN:
        assert key in RX16_AR and RX16_AR[key], key
        assert rx16_t(key, "en") == RX16_EN[key]
        assert rx16_t(key, "ar") == RX16_AR[key]
        assert rx16_t(key, "en") != key  # real text, not a key fallback
