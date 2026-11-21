"""Round 16 worker C: reports_dir setting + save/print helpers.

Shares fixtures (PATIENT, _TMP, _make_pdf, isolated_db) with
tests/test_r16_print.py.
"""
from pathlib import Path

from tests.test_r16_print import (PATIENT, _TMP, _make_pdf, isolated_db)
def test_reports_dir_setting_changes_save_folder():
    from src.models.database import set_setting
    from src.reports.pdf_report import create_patient_pdf
    dest = _TMP / "custom_reports"
    with isolated_db():
        set_setting("reports_dir", str(dest))
        out = create_patient_pdf(PATIENT, [], [], [], [], [],
                                 language="en", user_name="fady")
        assert Path(out).parent == dest, out
        assert Path(out).exists()
        set_setting("reports_dir", "")


def test_pdf_helpers_and_print_fallback():
    from src.reports.report_files import (pdf_page_count, print_pdf_file,
                                          save_pdf_copy)
    out = _make_pdf(out_dir=_TMP)
    assert pdf_page_count(out) >= 1
    copy = save_pdf_copy(out, dest_path=str(_TMP / "copy.pdf"))
    assert Path(copy).exists()
    assert Path(copy).stat().st_size == Path(out).stat().st_size
    status, _msg = print_pdf_file(out)  # no printer here: must not raise
    assert status in ("ok", "no-printer", "error")
