"""Round 54, Sections E + F: the print PREVIEW shows exactly the
same centre-contact block as the PDF, for all four documents --
and the second centre mobile (centre_mobile2) appears in the
header block + previews iff non-empty.

Section E root cause (owner report 2026-11-25, referral print
preview): the referral and prescription PDFs already carried the
block since round 52, but their plain-text preview renderings
omitted it entirely -- the preview window the owner screenshotted
renders the preview lines, so the block was invisible even with
the fields filled. The report and invoice previews already had
it (round 52). Empty fields = no lines at all (round-51 shape).
"""
import tkinter as tk

from tests.test_r16_print import isolated_db

ADDR = "12 Rainbow Street, Amman"
MOB = "+962791234567"      # fictional sample (established pattern)
MOB2 = "+962791234568"     # fictional sample, R54 second mobile
LAND = "+96265123456"      # fictional sample
ALL = (ADDR, MOB, MOB2, LAND)


def _set_all():
    from src.models.database import set_setting
    set_setting("clinic_name", "Fady Dental Clinic")
    set_setting("centre_address", ADDR)
    set_setting("centre_phone", MOB)
    set_setting("centre_mobile2", MOB2)
    set_setting("centre_landline", LAND)


def _clear_all():
    from src.models.database import set_setting
    for k in ("centre_address", "centre_phone", "centre_mobile2",
              "centre_landline"):
        set_setting(k, "")


def _patient():
    return {"full_name": "Test Patient", "file_number": "F-1",
            "age_years": 30, "birth_date_greg": "1996-01-01"}


def _all_preview_lines(lang):
    from src.reports.referral_pdf import referral_preview_lines
    from src.ui.rx_print import rx_preview_lines
    from src.reports.report_text import patient_preview_lines
    from src.reports.invoice_pdf import invoice_preview_lines
    pat = _patient()
    ref = {"created_at": "2026-11-24", "from_user": "fady",
           "to_doctor": "Dr Other", "note": "Check"}
    rx = {"date": "2026-11-24", "doctor": "fady"}
    items = [{"generic": "Amoxicillin", "dose": "500 mg",
              "frequency": "3x daily", "duration_days": "5",
              "instructions": ""}]
    return {
        "referral": referral_preview_lines(pat, ref, lang),
        "rx": rx_preview_lines(pat, rx, items, lang,
                               "Fady Dental Clinic"),
        "report": patient_preview_lines(pat, language=lang),
        "invoice": invoice_preview_lines(pat, [], None, "detailed",
                                         lang, "Fady Dental Clinic"),
    }


def test_r54_previews_carry_contact_when_filled():
    with isolated_db():
        _set_all()
        try:
            for lang in ("en", "ar"):
                for name, lines in _all_preview_lines(lang).items():
                    joined = "\n".join(lines)
                    for value in ALL:
                        assert value in joined, (lang, name, value, lines)
        finally:
            _clear_all()


def test_r54_previews_empty_when_unset():
    with isolated_db():
        _clear_all()
        for lang in ("en", "ar"):
            previews = _all_preview_lines(lang)
            for name, lines in previews.items():
                joined = "\n".join(lines)
                for value in ALL:
                    assert value not in joined, (lang, name, value)
        # Shape pins (round-51 layout, no blank-line drift): the
        # referral starts with its title, the Rx with its heading.
        from src.config.strings_r19_referral import tr as _rt
        from src.config.strings_r16_rx import rx16_t
        from src.ui.rx_print import rx_preview_lines as _rx_lines
        assert _all_preview_lines("en")["referral"][0] == \
            _rt("refer.pdf_title", "en")
        # With no clinic name the Rx preview starts with its heading.
        assert _rx_lines(_patient(), {"date": "2026-11-24",
                                      "doctor": "fady"}, [],
                         "en", "")[0] == rx16_t("rx.pdf_heading", "en")


def test_r54_preview_header_tag():
    """The preview's leading non-empty run (clinic name + centre
    contact) renders centred and bold -- like the PDF header."""
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        print("SKIP test_r54_preview_header_tag (no display)")
        return
    try:
        from src.reports.print_preview import PrintPreview
        pv = PrintPreview(
            root, "T", lambda lang: "/nonexistent/r54.pdf", "en",
            preview_text=lambda lang: ["Test Clinic", ADDR, MOB, "",
                                       "Body line"])
        try:
            ranges = pv.text.tag_ranges("head")
            assert len(ranges) == 2, ranges
            assert str(ranges[0]) == "1.0" and str(ranges[1]) == "4.0", \
                ranges
        finally:
            pv.destroy()
    finally:
        root.destroy()
