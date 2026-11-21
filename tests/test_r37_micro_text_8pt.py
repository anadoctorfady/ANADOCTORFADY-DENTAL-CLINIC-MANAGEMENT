"""Round 37 (owner decision 2026-11-21): the three pre-existing
7pt micro-texts rise to 8pt so the app-name footer line is the
UNIQUE smallest text in every printed document:
(1) the footer `small` style (pdf_styles) -- the footer report
    line, signature underscores and signature label in the patient
    report / invoice / referral (and the legacy bilingual Rx);
(2) the live Rx "Issued" line (rx_report);
(3) the top contact banner strip (canvas, report + invoice +
    legacy Rx; the live Rx and the referral carry no banner).
The app line itself stays exactly 7.0pt, once, last, in the
reading-direction corner (round 31 pins, unchanged); the round-31
spacers stay, so the signature -> app-line gaps must still measure
>= 14mm (Rx) / >= 10mm (others) on the rendered PDFs.
Geometry/size checks skip when pdftotext/pdftohtml are unavailable
(house pattern); the flowable-level checks always run. Isolated DB."""
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from tests.test_r16_print import isolated_db
from tests.test_r31_pdf_footer import (_TMP, _build_all, _drawn_sizes,
                                       _gap_mm, _pages_words, _app_group,
                                       _MIN_GAP)

APP_LINE = "ANADOCTORFADY DENTAL CLINIC MANAGEMENT"
BANNER = "ANADOCTORFADY • Dental Clinic • +963944234456"


def test_small_style_is_8pt_and_app_line_stays_7():
    from src.reports.pdf_styles import styles
    from src.reports.pdf_common import footer_block
    st = styles()
    assert st["small"].fontSize == 8, st["small"].fontSize
    for lang in ("en", "ar"):
        foot = footer_block(st, lang, bilingual=False)
        assert foot[-1].text.strip() == APP_LINE
        assert foot[-1].style.fontSize == 7, lang  # app line: still 7
        smalls = [f for f in foot if hasattr(f, "style")
                  and getattr(f, "text", "")]
        assert all(f.style.fontSize == 8 for f in smalls[:-1]), lang


def _xml_runs(pdf):
    subprocess.run(["pdftohtml", "-xml", "-zoom", "1", "-i", "-q",
                    str(pdf), str(pdf) + ".xml"],
                   capture_output=True, text=True, timeout=60, check=True)
    root = ET.parse(str(pdf) + ".xml").getroot()
    fonts = {f.get("id"): float(f.get("size"))
             for f in root.iter("fontspec")}
    return [(fonts[t.get("font")], "".join(t.itertext()))
            for t in root.iter("text")]


def test_rendered_unique_minimum_and_gaps():
    if not (shutil.which("pdftotext") and shutil.which("pdftohtml")):
        print("SKIP r37 rendered checks (no poppler tools)")
        return
    with isolated_db():
        from src.models.database import set_setting
        set_setting("clinic_name", "")
        for lang in ("en", "ar"):
            for kind, pdf in _build_all(lang, _TMP / "r37" / lang).items():
                tag = (kind, lang)
                runs = _xml_runs(pdf)
                sizes = sorted({s for s, _ in runs})
                assert sizes[0] == 7.0, (tag, sizes)
                at_min = {t.strip() for s, t in runs
                          if s == 7.0 and t.strip()}
                assert at_min == {APP_LINE}, (tag, at_min)
                banner = [s for s, t in runs if "963944234456" in t]
                if kind in ("report", "invoice"):
                    assert banner == [8.0], (tag, banner)
                else:  # live Rx + referral carry no banner strip
                    assert banner == [], (tag, banner)
                drawn = _drawn_sizes(pdf)
                assert drawn.get(APP_LINE) == 7.0, (tag, drawn.get(APP_LINE))
                if kind == "rx" and lang == "en":
                    issued = next(v for k, v in drawn.items()
                                  if k.startswith("Issued:"))
                    assert issued == 8.0, (tag, issued)
                npages, _w, words = _pages_words(pdf)
                assert npages == 1, tag
                gap = _gap_mm(words, _app_group(words))
                assert gap >= _MIN_GAP[kind], (tag, f"gap={gap:.2f}mm")
