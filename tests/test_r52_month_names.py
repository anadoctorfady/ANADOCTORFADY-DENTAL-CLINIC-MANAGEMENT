"""Round 52, Section D: regional Arabic month names + full
weekday names.

Pins: the three regional sets EXACTLY as the owner specified them;
Levant is the default (fresh DBs and invalid stored values alike);
the choice persists through the Settings storage section's own
save path; the appointments calendar header shows the chosen set's
month name and the FULL Arabic weekday names; Hijri month names
are untouched by the choice.
"""
import tempfile
from pathlib import Path

from src.config import month_names as MN
from tests.test_r16_print import isolated_db

_TMP = Path(tempfile.mkdtemp(prefix="r52_months_"))

LEVANT = ["كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران",
          "تموز", "آب", "أيلول", "تشرين الأول", "تشرين الثاني",
          "كانون الأول"]
EGYPT_GULF = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
              "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
MAGHREB = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
           "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
FULL_WEEKDAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس",
                 "الجمعة", "السبت", "الأحد"]


def test_sets_exact_and_default():
    assert MN.MONTH_SETS["levant"] == LEVANT
    assert MN.MONTH_SETS["egypt_gulf"] == EGYPT_GULF
    assert MN.MONTH_SETS["maghreb"] == MAGHREB
    assert MN.DEFAULT_SET == "levant"
    assert MN.months_ar() == LEVANT          # no key -> default
    assert MN.months_ar("bogus") == LEVANT   # invalid -> default
    assert MN.month_name_ar(2, "maghreb") == "فيفري"
    assert MN.month_name_ar(8, "levant") == "آب"
    assert len(MN.MONTHS_EN) == 12


def test_default_setting_and_persistence():
    with isolated_db():
        from src.models.database import get_setting, set_setting
        assert get_setting("ar_month_names", "") == "levant"
        assert MN.current_month_name_ar(1) == "كانون الثاني"
        set_setting("ar_month_names", "egypt_gulf")
        assert MN.current_month_name_ar(1) == "يناير"
        set_setting("ar_month_names", "maghreb")
        assert MN.current_month_name_ar(12) == "ديسمبر"
        assert MN.current_month_name_ar(1) == "جانفي"
        set_setting("ar_month_names", "levant")


def test_settings_save_path_persists_choice():
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    try:
        with isolated_db():
            from src.models.database import get_setting
            from src.ui.settings_centre_fields import (
                attach_centre_fields, save_centre_fields)
            tab = tk.Frame(root); tab.lang = "ar"
            frm = tk.Frame(root)
            attach_centre_fields(frm, tab)
            root.update()
            assert tab.ar_month_names_var.get() == "الشام"  # default
            tab.ar_month_names_var.set("المغرب العربي")
            save_centre_fields(tab)
            assert get_setting("ar_month_names", "") == "maghreb"
            tab.ar_month_names_var.set("مصر والخليج")
            save_centre_fields(tab)
            assert get_setting("ar_month_names", "") == "egypt_gulf"
    finally:
        root.destroy()


def test_calendar_uses_choice_and_full_weekdays():
    import tkinter as tk
    from src.ui.calendar_grid import (MonthCalendar, WEEKDAYS_AR,
                                      WEEKDAYS_SHORT_AR)
    assert WEEKDAYS_AR == FULL_WEEKDAYS
    assert WEEKDAYS_SHORT_AR == FULL_WEEKDAYS  # no abbreviations left
    root = tk.Tk(); root.withdraw()
    try:
        with isolated_db():
            from src.models.database import set_setting
            for key, expected in (("levant", "شباط"),
                                  ("egypt_gulf", "فبراير"),
                                  ("maghreb", "فيفري")):
                set_setting("ar_month_names", key)
                cal = MonthCalendar(root, lang="ar")
                cal.year, cal.month = 2026, 2
                assert cal.month_label() == f"{expected} 2026", \
                    (key, cal.month_label())
                labels = []

                def _walk(w):
                    for ch in w.winfo_children():
                        if isinstance(ch, tk.Label):
                            labels.append(ch.cget("text"))
                        _walk(ch)
                _walk(cal)
                head = [x for x in labels if x in FULL_WEEKDAYS]
                assert head == FULL_WEEKDAYS, (key, labels)
                cal.destroy()
            set_setting("ar_month_names", "levant")
    finally:
        root.destroy()


def test_hijri_names_untouched():
    with isolated_db():
        from src.models.database import set_setting
        from src.utils.hijri_age import format_hijri_date
        for key in ("levant", "egypt_gulf", "maghreb"):
            set_setting("ar_month_names", key)
            s = format_hijri_date("1990-05-15", "ar")
            assert "شوال" in s, (key, s)  # 20 Shawwal 1410
        set_setting("ar_month_names", "levant")


def run():
    test_sets_exact_and_default()
    test_default_setting_and_persistence()
    test_settings_save_path_persists_choice()
    test_calendar_uses_choice_and_full_weekdays()
    test_hijri_names_untouched()


if __name__ == "__main__":
    run()
    print("test_r52_month_names OK")
