"""Round 57, Sections A + B: (A) Settings month-names/logo grid
collision, (B) centre logo in the print preview. Isolated DB
only; GUI tests need a display (the gate provides :98)."""
import tempfile
import tkinter as tk
from pathlib import Path

from tests.test_r16_print import isolated_db
from tests.test_r30_logo import (_ITEMS, _REF, _ROWS, _TOTALS,
                                _has_image, _logo, CLINIC, PATIENT, _RX)
from tests.test_settings_storage_r16 import _build_settings

_TMP = Path(tempfile.mkdtemp(prefix="r57_"))
LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo_anadoctorfady.png"


def _tk():
    try:
        root = tk.Tk(); root.withdraw(); return root
    except tk.TclError:
        return None


def _bbox(w):
    return (w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height())


def _overlaps(a, b):
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def test_settings_grid_month_and_logo_no_overlap():
    """A: the month-names picker (row 7) and the centre-logo row
    must not share a grid cell -- round 56 gridded both onto row 7,
    so the logo label/thumbnail painted over the month label and
    the month combobox (the owner's 'month name mixed with the
    centre logo')."""
    for lang in ("en", "ar"):
        with isolated_db():
            tab, root = _build_settings(lang)
            assert tab is not None, "no display"
            try:
                root.update_idletasks(); root.update()
                store = tab.storage_wrap.inner
                cells = {}

                def walk(w):
                    gi = w.grid_info()
                    if gi:
                        cells.setdefault((gi.get("row"), gi.get("column")),
                                         []).append(w)
                    for ch in w.winfo_children():
                        walk(ch)

                walk(store)
                shared = {k: v for k, v in cells.items() if len(v) > 1}
                assert not shared, (lang, {k: [type(x).__name__ for x in v]
                                           for k, v in shared.items()})
                # Logo row is 8 now; month picker owns row 7 alone.
                assert tab._logo_preview.grid_info()["row"] == 8, \
                    tab._logo_preview.grid_info()
                month_box = cells[(7, 1)][0]
                assert month_box is not tab._logo_preview
                assert not _overlaps(_bbox(month_box),
                                     _bbox(tab._logo_preview)), \
                    (lang, _bbox(month_box), _bbox(tab._logo_preview))
                month_lbl = cells[(7, 0)][0]
                logo_lbl = cells[(8, 0)][0]
                assert "logo" in str(logo_lbl.cget("text")).lower() or \
                    "شعار" in str(logo_lbl.cget("text")), logo_lbl.cget("text")
                assert not _overlaps(_bbox(month_lbl), _bbox(logo_lbl))
                assert tab.ar_month_names_var.get(), "month choice blank"
            finally:
                root.destroy()


def _preview_builders(lang, root):
    """(build, preview_text) per document, mirroring _build_all."""
    from src.reports.invoice_pdf import (build_invoice_pdf,
                                         invoice_preview_lines)
    from src.reports.pdf_report import create_patient_pdf
    from src.reports.referral_pdf import (build_referral_pdf,
                                          referral_preview_lines)
    from src.reports.report_text import patient_preview_lines
    from src.reports.rx_report import build_rx_pdf
    from src.ui.rx_print import rx_preview_lines
    return {
        "report": (lambda l: create_patient_pdf(
            PATIENT, [], [], [], [], [], language=l, user_name="fady",
            out_dir=root / "rep"),
            lambda l: patient_preview_lines(
                PATIENT, [], [], [], [], [], language=l)),
        "rx": (lambda l: build_rx_pdf(
            PATIENT, _RX, _ITEMS, lang=l, clinic_name=CLINIC,
            out_dir=root / "rx"),
            lambda l: rx_preview_lines(PATIENT, _RX, _ITEMS, l, CLINIC)),
        "invoice": (lambda l: build_invoice_pdf(
            PATIENT, _ROWS, _TOTALS, "detailed", l, CLINIC,
            root / "inv.pdf", currency="SYP"),
            lambda l: invoice_preview_lines(
                PATIENT, _ROWS, _TOTALS, "detailed", l, CLINIC)),
        "referral": (lambda l: build_referral_pdf(
            PATIENT, _REF, lang=l, clinic_name=CLINIC, out_path=root / "ref"),
            lambda l: referral_preview_lines(PATIENT, _REF, l, CLINIC)),
    }


def test_preview_logo_all_four_docs():
    """B: with a logo set, every preview window shows the logo
    image AND its PDF embeds it; with no logo set, no preview
    shows a logo label and no PDF embeds an image."""
    from src.reports.print_preview import PrintPreview
    root = _tk()
    assert root is not None, "no display"
    try:
        with isolated_db():
            assert LOGO.exists(), LOGO
            with _logo(str(LOGO)):
                for lang in ("en", "ar"):
                    for kind, (build, lines) in _preview_builders(
                            lang, _TMP / f"pv_{lang}").items():
                        win = PrintPreview(root, kind, build, lang,
                                           preview_text=lines)
                        try:
                            root.update_idletasks()
                            assert win.logo_label is not None, (lang, kind)
                            assert win.logo_label.cget("image"), (lang, kind)
                            assert win.pdf_path and Path(win.pdf_path).exists()
                            assert _has_image(win.pdf_path), (lang, kind)
                        finally:
                            win.destroy()
            with _logo():
                for lang in ("en", "ar"):
                    for kind, (build, lines) in _preview_builders(
                            lang, _TMP / f"pv_no_{lang}").items():
                        win = PrintPreview(root, kind, build, lang,
                                           preview_text=lines)
                        try:
                            root.update_idletasks()
                            assert win.logo_label is None, (lang, kind)
                            assert not _has_image(win.pdf_path), (lang, kind)
                        finally:
                            win.destroy()
    finally:
        root.destroy()
