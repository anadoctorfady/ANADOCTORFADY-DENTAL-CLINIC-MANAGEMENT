"""Round 52, Section E: centre address + mobile + landline in
Settings and in ALL FOUR printed documents.

Pins: centre_landline / centre_address start EMPTY on a fresh DB;
the centre_phone KEY is unchanged (only its label became "Centre
mobile"); the Settings save path persists all three; with sample
values set, the report, prescription, invoice AND referral PDFs
(EN + AR) carry the address + both numbers in the header block;
with all three empty, the header flowables are exactly the
round-51 ones (no contact flowables at all).
"""
import tempfile
from pathlib import Path

from tests.test_r16_print import _pdf_text, isolated_db

_TMP = Path(tempfile.mkdtemp(prefix="r52_centre_"))
ADDR = "12 Rainbow Street, Amman"
MOB = "+962791234567"      # fictional sample (established pattern)
MOB2 = "+962791234568"     # fictional sample, R54 second mobile
LAND = "+96265123456"      # fictional sample


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


def test_defaults_empty_and_key_unchanged():
    with isolated_db():
        from src.models.database import get_setting
        assert get_setting("centre_landline", "X") == ""
        assert get_setting("centre_address", "X") == ""
        assert get_setting("centre_phone", "X") == ""
        assert get_setting("centre_mobile2", "X") == ""  # R54: 2nd mobile
        from src.reports.centre_contact import centre_contact_lines
        assert centre_contact_lines() == ("", "", "", "")  # R54: 4-tuple


def test_settings_save_persists_all_three():
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    try:
        with isolated_db():
            from src.models.database import get_setting
            from src.ui.settings_centre_fields import (
                attach_centre_fields, save_centre_fields)
            tab = tk.Frame(root); tab.lang = "en"
            attach_centre_fields(tk.Frame(root), tab)
            tab.centre_phone_var.set(MOB)
            tab.centre_mobile2_var.set(MOB2)  # R54: second mobile
            tab.centre_landline_var.set(LAND)
            tab.centre_address_var.set(ADDR)
            save_centre_fields(tab)
            assert get_setting("centre_phone", "") == MOB  # same key
            assert get_setting("centre_mobile2", "") == MOB2
            assert get_setting("centre_landline", "") == LAND
            assert get_setting("centre_address", "") == ADDR
            _clear_all()
    finally:
        root.destroy()


def test_labels_say_mobile():
    from src.ui.settings_storage_ui import _s
    assert _s("settings.centre_phone", "en") == "Centre mobile:"
    assert _s("settings.centre_phone", "ar") == "جوال المركز:"
    assert _s("settings.centre_landline", "en") == "Centre landline:"
    assert _s("settings.centre_address", "ar") == "عنوان المركز:"


def test_flowables_appear_iff_non_empty():
    with isolated_db():
        from src.reports.centre_contact import centre_contact_flowables
        from src.reports.pdf_styles import styles
        st = styles()
        assert centre_contact_flowables(st) == []
        _set_all()
        flows = centre_contact_flowables(st)
        assert len(flows) == 4  # R54: address + 2 mobiles + landline
        texts = [f.getPlainText() for f in flows]
        assert texts == [ADDR, MOB, MOB2, LAND], texts
        from src.models.database import set_setting
        set_setting("centre_address", "")
        assert [f.getPlainText() for f in
                centre_contact_flowables(st)] == [MOB, MOB2, LAND]
        _clear_all()
        assert centre_contact_flowables(st) == []


def _patient():
    return {"full_name": "Test Patient", "file_number": "F-1",
            "age_years": 30, "birth_date_greg": "1996-01-01"}


def test_all_four_pdfs_carry_contact_en_ar():
    with isolated_db():
        _set_all()
        pat = _patient()
        from src.reports.pdf_report import create_patient_pdf
        from src.reports.rx_report import build_rx_pdf
        from src.reports.invoice_pdf import build_invoice_pdf
        from src.reports.referral_pdf import build_referral_pdf
        rx = {"date": "2026-11-24", "doctor": "fady"}
        items = [{"generic": "Amoxicillin", "dose": "500 mg",
                  "frequency": "3x daily", "duration_days": "5",
                  "instructions": ""}]
        ref = {"created_at": "2026-11-24", "from_user": "fady",
               "to_doctor": "Dr Other", "reason": "Check"}
        for lang in ("en", "ar"):
            docs = [
                create_patient_pdf(pat, language=lang,
                                   out_dir=_TMP / f"rep_{lang}"),
                build_rx_pdf(pat, rx, items, lang=lang,
                             out_dir=_TMP / f"rx_{lang}"),
                build_invoice_pdf(pat, [], None, lang=lang,
                                  out_path=_TMP / f"inv_{lang}" / "i.pdf"),
                build_referral_pdf(pat, ref, lang=lang,
                                   out_path=_TMP / f"ref_{lang}"),
            ]
            for path in docs:
                txt = _pdf_text(path)
                if txt is None:
                    continue
                assert MOB in txt, (lang, path, txt[:400])
                assert MOB2 in txt, (lang, path, txt[:400])
                assert LAND in txt, (lang, path, txt[:400])
                if lang == "en":
                    assert ADDR in txt, (path, txt[:400])
        _clear_all()
        txt = _pdf_text(create_patient_pdf(pat, language="en",
                                           out_dir=_TMP / "rep_empty"))
        if txt is not None:
            assert MOB not in txt and MOB2 not in txt and LAND not in txt


def run():
    test_defaults_empty_and_key_unchanged()
    test_settings_save_persists_all_three()
    test_labels_say_mobile()
    test_flowables_appear_iff_non_empty()
    test_all_four_pdfs_carry_contact_en_ar()


if __name__ == "__main__":
    run()
    print("test_r52_centre_contact OK")
