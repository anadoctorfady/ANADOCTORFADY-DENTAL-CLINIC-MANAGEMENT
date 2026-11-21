"""Round 16 integration (W2-B): clinic_name seed + legacy-value fix.

- Fresh DBs seed clinic_name="" (no clinic name shown).
- A stored "ANADOCTORFADY" (the old seed, still in the owner's live
  DB) counts as UNSET in both report paths, so reports never print
  the app name twice (once as clinic name, once as app name).
- A distinct clinic name still prints on top, app name under it.
DB work runs on an isolated temp copy (never the live DB); PDFs go
to temp folders. <200 lines.
"""
from tests.test_r16_print import PATIENT, _TMP, _pdf_text, isolated_db


def _rx_pdf_text(clinic_setting=None, clinic_param="__unset__", lang="en"):
    """Build an Rx PDF under the given setting and return its text."""
    from src.models.database import set_setting
    from src.reports.rx_report import build_rx_pdf
    with isolated_db():
        if clinic_setting is not None:
            set_setting("clinic_name", clinic_setting)
        kw = {} if clinic_param == "__unset__" else {"clinic_name": clinic_param}
        out = build_rx_pdf(PATIENT, {"date": "2026-11-11", "doctor": "fady"},
                           [{"generic": "Amoxicillin", "dose": "500 mg",
                             "frequency": "3x daily", "duration_days": "5",
                             "instructions": "After food"}],
                           lang=lang, out_dir=_TMP, **kw)
        return _pdf_text(out)


def test_seed_clinic_name_empty():
    """Fresh DB: clinic_name seeds to '' (nothing shown)."""
    from src.models.database import get_setting
    with isolated_db():
        assert get_setting("clinic_name", "FALLBACK") == ""


def test_pdf_common_legacy_value_is_unset():
    """pdf_common.clinic_name(): legacy 'ANADOCTORFADY' -> '', a real
    name passes through, '' stays ''."""
    from src.models.database import set_setting
    from src.reports.pdf_common import clinic_name
    with isolated_db():
        assert clinic_name() == ""
        set_setting("clinic_name", "ANADOCTORFADY")
        assert clinic_name() == ""
        set_setting("clinic_name", "anadoctorfady")  # case-insensitive
        assert clinic_name() == ""
        set_setting("clinic_name", "Smile Clinic")
        assert clinic_name() == "Smile Clinic"
        set_setting("clinic_name", "")
        assert clinic_name() == ""


def test_rx_pdf_legacy_value_not_doubled():
    """Rx PDF with the legacy stored value: 'ANADOCTORFADY' appears
    exactly twice — header app name + footer. With the bug it was
    three times (clinic line + app line + footer)."""
    txt = _rx_pdf_text(clinic_setting="ANADOCTORFADY")
    if txt is None:
        return
    assert txt.count("ANADOCTORFADY") == 2, txt[:400]


def test_rx_pdf_unset_and_distinct_name():
    """Empty setting: app name once in the header + once in the
    footer. Distinct name: it prints on top, app name under it."""
    txt = _rx_pdf_text(clinic_setting="")
    if txt is None:
        return
    assert txt.count("ANADOCTORFADY") == 2, txt[:400]
    txt = _rx_pdf_text(clinic_setting="Smile Clinic")
    if txt is None:
        return
    assert "Smile Clinic" in txt
    assert txt.count("ANADOCTORFADY") == 2, txt[:400]
    # The clinic name comes before the app name in the header.
    assert txt.index("Smile Clinic") < txt.index("ANADOCTORFADY")


def test_rx_pdf_explicit_param_legacy_value():
    """build_rx_pdf(clinic_name='ANADOCTORFADY') also counts as
    unset — the rx_print.py caller passes the raw setting through."""
    txt = _rx_pdf_text(clinic_param="ANADOCTORFADY")
    if txt is None:
        return
    assert txt.count("ANADOCTORFADY") == 2, txt[:400]
    txt = _rx_pdf_text(clinic_param="Smile Clinic")
    if txt is None:
        return
    assert "Smile Clinic" in txt
