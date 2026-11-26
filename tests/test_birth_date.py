"""Birth date DD/MM/YYYY (ITEM 1, 2026-11-08): entry, display and PDF
show DD/MM/YYYY in both languages; the DB still stores ISO YYYY-MM-DD.
Hijri conversion must still work from the parsed date."""
import re
import zlib
from datetime import date
from pathlib import Path

from src.utils.hijri_age import (INVALID_BIRTH_MSG, format_birth_date,
    get_all_ages, parse_birth_date)


def test_parse_ddmmyyyy():
    assert parse_birth_date("15/02/2026") == date(2026, 2, 15)
    assert format_birth_date(date(2026, 2, 15)) == "15/02/2026"
    assert format_birth_date("2026-02-15") == "15/02/2026"
    assert format_birth_date("") == ""


def test_parse_iso_still_accepted():
    """Legacy ISO values already in the DB / old callers keep working."""
    assert parse_birth_date("1990-05-15") == date(1990, 5, 15)
    assert format_birth_date("1990-05-15") == "15/05/1990"


def test_invalid_dates_rejected():
    # Round 19: single-digit day/month ("15/2/2026") is NO LONGER
    # rejected -- the lenient front-door accepts it (see
    # test_r19_birth_date.py). Impossible calendar dates and other
    # separators / year shapes stay rejected.
    for bad in ("31/02/2026", "32/01/2026", "15/13/2026", "00/01/2026",
                "2026/02/15", "15-02-2026", "15/02/26",
                "", "not-a-date", "15/02/2026x"):
        try:
            parse_birth_date(bad)
        except ValueError as e:
            assert "DD/MM/YYYY" in str(e), bad
        else:
            raise AssertionError(f"{bad!r} was accepted")
    assert "DD/MM/YYYY" in INVALID_BIRTH_MSG
    assert "تاريخ ميلاد" in INVALID_BIRTH_MSG  # bilingual message


def test_hijri_from_parsed_date():
    # 1990-05-15 = 20 Shawwal 1410 — the pinned Hijri case, now entered
    # as DD/MM/YYYY.
    info = get_all_ages("15/05/1990")
    assert info["hijri_date"] == (1410, 10, 20), info["hijri_date"]
    assert "1410" in info["hijri_formatted"]
    assert get_all_ages("1990-05-15")["hijri_date"] == (1410, 10, 20)
    # A DD/MM/YYYY date also yields a Hijri age.
    assert get_all_ages("15/02/2026")["hijri_age"]["years"] >= 0


def test_get_all_ages_rejects_invalid():
    try:
        get_all_ages("31/02/2026")
    except ValueError:
        return
    raise AssertionError("31/02/2026 was accepted by get_all_ages")


def _pdf_text(path):
    """Page content is ASCII85+Flate; ToUnicode maps are Flate only.
    Decode both layers, then search the plain Latin text."""
    import base64
    raw = Path(path).read_bytes()
    texts = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        data = m.group(1).strip()
        for attempt in (data,):
            try:
                texts.append(zlib.decompress(attempt).decode("latin-1"))
                continue
            except Exception:
                pass
            try:
                texts.append(zlib.decompress(
                    base64.a85decode(attempt, adobe=True)).decode("latin-1"))
            except Exception:
                pass
    return "\n".join(texts)


def test_pdf_shows_ddmmyyyy():
    from src.reports.pdf_report import create_patient_pdf
    patient = {"file_number": 78, "full_name": "Birth Date Test",
        "birth_date_greg": "1990-05-15", "birth_date_hijri": "20 شوال 1410هـ",
        "age_years": 36, "age_months": 5, "age_days": 21,
        "nationality": "Syrian", "mobile1": "0791234567", "mobile2": "",
        "emergency_phone": "0799888777", "address": "Damascus",
        "created_at": "2026-11-05"}
    for language, bilingual in (("en", False), ("ar", False), ("ar", True)):
        out = create_patient_pdf(patient, [], [], [], [], [], language=language,
                                 bilingual=bilingual, user_name="fady")
        text = _pdf_text(out)
        assert "15/05/1990" in text, (language, bilingual, text[:500])
        assert "1990-05-15" not in text, (language, bilingual)


def test_form_label_and_no_old_format():
    src = Path("src/ui/patient_form.py").read_text(encoding="utf-8")
    # Label text moved into the strings module (i18n round, 2026-11-08);
    # the form now uses t("patient.birth") and the literal lives in EN.
    assert 't("patient.birth", self.lang)' in src
    assert "Birth (YYYY-MM-DD)" not in src
    assert "Birth format YYYY-MM-DD" not in src
    # Round 17: the form calls the lang-aware helper invalid_birth_msg()
    # (single-language message); the old bilingual constant is gone here.
    assert "invalid_birth_msg" in src
    from src.config.strings_clinical import EN as _CL_EN, AR as _CL_AR
    assert _CL_EN["patient.birth"] == "Birth (DD/MM/YYYY)"
    assert _CL_AR["patient.birth"] != ""
    assert "Birth (YYYY-MM-DD)" not in _CL_EN["patient.birth"]
    pdf_src = Path("src/reports/pdf_report.py").read_text(encoding="utf-8")
    assert "birth_display" in pdf_src
    assert 'str(p.get("birth_date_greg",""))' not in pdf_src
    # Round 20: the clinical tab no longer displays the birth date
    # at all (its info header block was removed on the owner's
    # request). The shell's Patient info panel is the display now,
    # and it formats the stored ISO value via format_birth_date --
    # never the raw string -- exactly as this test requires.
    clin_src = Path("src/ui/clinical.py").read_text(encoding="utf-8")
    assert 'p.get("birth_date_greg")' not in clin_src
    # Round 55 RE-PIN (with cause): the birth-line formatting moved
    # with the strip into header_strip.birth_lines (patient_info.py
    # builds the grid from there); the pin is the same -- the panel
    # formats the stored ISO value via format_birth_date, never
    # the raw string -- exactly as this test requires.
    info_src = Path("src/ui/header_strip.py").read_text(encoding="utf-8")
    assert "format_birth_date(birth)" in info_src
    assert 'lbl_pat_birth.config(text=p.get("birth_date_greg")' not in clin_src


def test_form_fill_shows_ddmmyyyy():
    """Real PatientForm under Xvfb: fill() converts stored ISO to
    DD/MM/YYYY and on_birth() normalises a typed DD/MM/YYYY date.
    Skips gracefully with no display (plain run_tests.py)."""
    try:
        import tkinter as tk
        from src.config.settings import get_theme_mode, set_theme_mode
        from src.ui.patient_form import PatientForm
    except Exception:
        return
    prev = get_theme_mode()
    set_theme_mode("light")
    try:
        root = tk.Tk()
    except tk.TclError:
        set_theme_mode(prev)
        return
    root.withdraw()

    class Stub:
        lang = "en"
        current_patient = None
        def on_teeth_select(self, *a): pass
        def print_pdf(self, *a): pass
        def load_patients(self): pass
        def select_patient(self, *a): pass

    try:
        form = PatientForm(root, Stub())
        row = {"first_name": "Test", "father_name": "F", "grand_name": "G",
            "last_name": "L", "birth_date_greg": "1990-05-15",
            "birth_date_hijri": "20 شوال 1410هـ", "mobile1": "", "mobile2": "",
            "emergency_phone": "", "address": "", "nationality": "Syrian",
            "current_medications": "", "allergies": "", "file_number": 999,
            "age_years": 36, "age_months": 5, "age_days": 21,
            "age_hijri_years": 37, "age_hijri_months": 0, "age_hijri_days": 0}
        form.fill(row)
        assert form.e_birth.get() == "15/05/1990", form.e_birth.get()
        form.e_birth.delete(0, tk.END)
        form.e_birth.insert(0, "15/02/2026")
        form.on_birth()
        assert form.e_birth.get() == "15/02/2026", form.e_birth.get()
        assert "1410" not in form.lbl_hijri.cget("text")  # new date, new Hijri
        assert form.lbl_hijri.cget("text") != "—"
    finally:
        try:
            root.destroy()
        except Exception:
            pass
        set_theme_mode(prev)
