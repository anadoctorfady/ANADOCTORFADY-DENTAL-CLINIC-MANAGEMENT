"""Round 25 (item 4): an Arabic patient name rendered word-REVERSED
(family first) in English PDF reports -- and, with the Latin font
the EN cells used, as unreadable boxes.

Root cause, verified by extraction (pdftotext -bbox): the stored
full_name is logical order "first father grandfather family", but
the EN cells passed the RAW string in a Helvetica paragraph
(pdf_report / invoice_pdf / referral_pdf): no Arabic glyphs (the
name extracted as boxes) and no reshaping/bidi, so the word order
followed the document's LTR direction instead of the name's RTL
script. The live Rx builder (rx_report._para) picked the Arabic
font by content but shaped each word SEPARATELY and joined them in
logical order, which also puts the first name leftmost (family
first for an Arabic reader).

Fix: pdf_common.name_value() -- a name holding any Arabic-script
character is _av()-reshaped as ONE string regardless of document
language; name_style() gives it the Arabic font in every document.
The observable for CORRECT order (pinned against the known-good AR
patient report): on the page, left -> right the words read
family, grandfather, father, first -- i.e. reading RTL, first ->
father -> grandfather -> family. The stored birth_date_hijri is
also no longer trusted: pdf_report re-derives it per cell language
via format_hijri_date (the patient below stores a deliberately
WRONG Hijri string; the PDFs must still show Shawwal)."""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from src.reports.pdf_common import _av, name_value
from src.utils.arabic import ar

_TMP = Path(tempfile.mkdtemp(prefix="r25_name_"))
NAME = "أحمد محمد علي حسن"
WORDS = ["أحمد", "محمد", "علي", "حسن"]  # first, father, grandfather, family
FORMS = {ar(w): w for w in WORDS}  # extracted (shaped) form -> logical word
PAT = {"file_number": 77, "full_name": NAME,
       "birth_date_greg": "1990-05-15",
       "birth_date_hijri": "1 محرم 1400هـ",  # WRONG on purpose (see above)
       "age_years": 36, "age_months": 5, "age_days": 21,
       "nationality": "Syrian", "mobile1": "0791234567", "mobile2": "",
       "emergency_phone": "0799888777", "address": "Damascus",
       "created_at": "2026-11-05", "diseases": ""}
LAT = dict(PAT, full_name="John Smith")
_RX = {"date": "2026-11-15", "doctor": "fady"}
_RX_ITEMS = [{"generic": "Amoxicillin", "dose": "500 mg",
              "frequency": "3x daily", "duration_days": "5",
              "instructions": "After food"}]
_INV_ROWS = [{"visit_date": "2026-11-01",
              "updated_at": "2026-11-01 09:30:00", "tooth_number": "16",
              "total_cost": 400000, "paid_amount": 250000,
              "currency": "SYP", "id": 1}]
_INV_TOTALS = {"total": 400000.0, "paid": 250000.0, "remaining": 150000.0}
_REF = {"id": 1, "patient_id": 77, "from_user": "fady",
        "to_doctor": "dr_x", "note": "note",
        "created_at": "2026-11-17 10:00:00"}


def _bbox_words(path):
    if not shutil.which("pdftotext"):
        return None
    r = subprocess.run(["pdftotext", "-bbox", str(path), "-"],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return [(float(m[0]), m[4]) for m in re.findall(
        r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" '
        r'yMax="([\d.]+)">([^<]+)</word>', r.stdout)]


def _pdf_text(path):
    if not shutil.which("pdftotext"):
        return None
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _ar_in(txt, s):
    """Arabic `s` as extracted PDF text may hold it (r24 pattern)."""
    cands = {s, ar(s)}
    try:
        import arabic_reshaper
        cands.add(arabic_reshaper.reshape(s))
    except ImportError:
        pass
    return any(c and c in txt for c in cands)


def _assert_name_order(path, repeats=1):
    """Left->right on the page: family .. first (repeats = name
    cells in the document); reading RTL that is first -> family."""
    words = _bbox_words(path)
    if words is None:
        print("SKIP bbox order check (no pdftotext)")
        return
    seq = [FORMS[w] for _x, w in sorted(words) if w in FORMS]
    assert seq == ["حسن", "علي", "محمد", "أحمد"] * repeats, seq
    txt = _pdf_text(path)
    assert "■" not in txt, "name still renders as boxes"


def test_name_value_helper():
    assert name_value(NAME) == _av(NAME)
    assert name_value(NAME) != NAME  # reshaped visual order, not raw
    assert name_value("John Smith") == "John Smith"
    assert name_value("") == "" and name_value(None) == ""


def test_patient_report_en_arabic_name_order():
    from src.reports.pdf_report import create_patient_pdf
    out = create_patient_pdf(PAT, [], [], [], [], [], language="en",
                             user_name="fady", out_dir=_TMP)
    _assert_name_order(out)


def test_patient_report_ar_arabic_name_order():
    from src.reports.pdf_report import create_patient_pdf
    out = create_patient_pdf(PAT, [], [], [], [], [], language="ar",
                             user_name="fady", out_dir=_TMP)
    _assert_name_order(out)


def test_patient_report_bilingual_arabic_name_order():
    from src.reports.pdf_report import create_patient_pdf
    out = create_patient_pdf(PAT, [], [], [], [], [], language="en",
                             bilingual=True, user_name="fady",
                             out_dir=_TMP)
    _assert_name_order(out, repeats=2)  # EN cell + AR cell


def test_patient_report_latin_name_unchanged():
    from src.reports.pdf_report import create_patient_pdf
    for lang in ("en", "ar"):
        out = create_patient_pdf(LAT, [], [], [], [], [], language=lang,
                                 user_name="fady", out_dir=_TMP)
        txt = _pdf_text(out)
        if txt is None:
            print("SKIP latin-name text check (no pdftotext)")
            continue
        assert "John Smith" in txt, lang
        words = _bbox_words(out)
        pos = {w: x for x, w in words if w in ("John", "Smith")}
        assert pos["John"] < pos["Smith"], (lang, pos)  # natural LTR


def test_patient_report_hijri_rederived_not_stored():
    """Stored Hijri says Muharram 1400; Greg 1990-05-15 is really
    20 Shawwal 1410 -- EN shows the transliteration, AR the Arabic."""
    from src.reports.pdf_report import create_patient_pdf
    en = _pdf_text(create_patient_pdf(PAT, [], [], [], [], [],
                                      language="en", user_name="fady",
                                      out_dir=_TMP))
    ar_t = _pdf_text(create_patient_pdf(PAT, [], [], [], [], [],
                                        language="ar", user_name="fady",
                                        out_dir=_TMP))
    if en is None or ar_t is None:
        print("SKIP hijri text checks (no pdftotext)")
        return
    assert "Shawwal" in en and "Muharram" not in en, en[:400]
    assert _ar_in(ar_t, "شوال") and not _ar_in(ar_t, "محرم")


def test_invoice_en_arabic_name_order():
    from src.reports.invoice_pdf import build_invoice_pdf
    out = build_invoice_pdf(PAT, _INV_ROWS, _INV_TOTALS, "detailed",
                            "en", "", _TMP / "inv_r25_en.pdf",
                            currency="SYP")
    _assert_name_order(out)


def test_referral_en_arabic_name_order():
    from src.reports.referral_pdf import build_referral_pdf
    out = build_referral_pdf(PAT, _REF, lang="en", clinic_name="",
                             out_path=_TMP / "ref_r25_en.pdf")
    _assert_name_order(out)


def test_rx_en_ar_arabic_name_order():
    from src.reports.rx_report import build_rx_pdf
    for lang in ("en", "ar"):
        out = build_rx_pdf(PAT, _RX, _RX_ITEMS, lang=lang,
                           clinic_name="", out_dir=_TMP)
        _assert_name_order(out)
