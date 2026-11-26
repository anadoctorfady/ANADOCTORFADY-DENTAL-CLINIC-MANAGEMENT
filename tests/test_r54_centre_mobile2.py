"""Round 54, Section F: a SECOND centre mobile (centre_mobile2)
in Settings, directly under the first mobile; empty by default;
shown in the print header block (all four PDFs + previews) as
its own line iff non-empty; absent when empty. The existing
mobile field (centre_phone) is untouched -- an addition, not a
rename. Values below are fictional samples (round-46 pattern).
"""
import tkinter as tk

from tests.test_r16_print import isolated_db

MOB = "+962791234567"
MOB2 = "+962791234568"
ADDR = "12 Rainbow Street, Amman"
LAND = "+96265123456"


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


def test_r54_mobile2_default_empty_and_label():
    with isolated_db():
        from src.models.database import get_setting
        assert get_setting("centre_mobile2", "X") == ""
        from src.ui.settings_storage_ui import _s
        assert _s("settings.centre_mobile2", "en") == "Centre mobile 2:"
        assert _s("settings.centre_mobile2", "ar") == "جوال المركز 2:"


def test_r54_mobile2_persists_via_settings():
    try:
        root = tk.Tk(); root.withdraw()
    except tk.TclError:
        print("SKIP test_r54_mobile2_persists_via_settings (no display)")
        return
    try:
        with isolated_db():
            from src.models.database import get_setting
            from src.ui.settings_centre_fields import (
                attach_centre_fields, save_centre_fields)
            tab = tk.Frame(root); tab.lang = "en"
            attach_centre_fields(tk.Frame(root), tab)
            assert hasattr(tab, "centre_mobile2_var"), \
                "second mobile field missing from Settings"
            tab.centre_phone_var.set(MOB)
            tab.centre_mobile2_var.set(MOB2)
            tab.centre_landline_var.set(LAND)
            tab.centre_address_var.set(ADDR)
            save_centre_fields(tab)
            assert get_setting("centre_phone", "") == MOB
            assert get_setting("centre_mobile2", "") == MOB2
            _clear_all()
    finally:
        root.destroy()


def test_r54_mobile2_in_header_iff_non_empty():
    with isolated_db():
        from src.reports.centre_contact import (
            centre_contact_flowables, centre_contact_lines)
        from src.reports.pdf_styles import styles
        st = styles()
        assert centre_contact_lines() == ("", "", "", "")
        assert centre_contact_flowables(st) == []
        from src.models.database import set_setting
        set_setting("centre_mobile2", MOB2)
        assert centre_contact_lines() == ("", "", MOB2, "")
        assert [f.getPlainText() for f in
                centre_contact_flowables(st)] == [MOB2]
        _set_all()
        assert [f.getPlainText() for f in
                centre_contact_flowables(st)] == [ADDR, MOB, MOB2, LAND]
        from src.reports.referral_pdf import referral_preview_lines
        pat = {"full_name": "T", "file_number": "F-1"}
        ref = {"created_at": "2026-11-24", "from_user": "fady",
               "to_doctor": "Dr O", "note": ""}
        assert MOB2 in "\n".join(referral_preview_lines(pat, ref, "en"))
        _clear_all()
        assert MOB2 not in "\n".join(referral_preview_lines(pat, ref, "en"))
