"""Round 42 guard: MIT replaced by the owner's custom ANADOCTORFADY
Free Use License (owner decision 2026-11-22, approved bilingual text
in ~/workspace/license_draft_r42.md).

Pins: the shipped LICENSE carries the new title and the no-sale
clause in EN and AR; the About dialog text is identical to LICENSE;
the installer agreement file matches LICENSE and is UTF-8 with BOM;
the .iss wires LicenseFile inside [Setup], stays pure ASCII, and
keeps the destination-location page enabled; the About tab exposes
the license section and dialog in both languages; and no shipped
doc or source file still claims MIT as the current license.
<200 lines."""
import re
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
EN_NO_SALE = "You may not sell, rent, or charge any fee for this software"
AR_NO_SALE = "يُمنع بيع هذا البرنامج أو تأجيره"
TITLE = "ANADOCTORFADY — Free Use License"


def _license_file_text():
    return (ROOT / "LICENSE").read_text(encoding="utf-8")


def test_license_file_terms():
    text = _license_file_text()
    assert TITLE in text
    assert "Copyright (c) Fady Abdulkafy Dadoush" in text
    assert EN_NO_SALE in text                      # EN clause 4
    assert AR_NO_SALE in text                      # AR clause 4
    assert "sadaqah jariyah" in text               # EN clause 1
    assert "صدقةً جارية" in text                    # AR clause 1
    assert "not a medical device" in text          # EN clause 7
    assert "MIT License" not in text
    assert "Permission is hereby granted" not in text


def test_license_texts_all_identical():
    from src.config.license_text import LICENSE_TEXT
    lic = _license_file_text().strip()
    assert LICENSE_TEXT.strip() == lic
    raw = (ROOT / "installer" / "license_agreement.txt").read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf", "agreement file needs a UTF-8 BOM"
    assert raw[3:].decode("utf-8").strip() == lic


def test_iss_wires_license_agreement():
    iss = (ROOT / "installer" / "ANADOCTORFADY.iss").read_text(encoding="ascii")
    assert all(ord(c) < 128 for c in iss), ".iss must stay pure ASCII"
    setup = iss.split("[Setup]", 1)[1].split("\n[", 1)[0]
    assert "LicenseFile=license_agreement.txt" in setup
    assert (ROOT / "installer" / "license_agreement.txt").exists()
    active = [ln for ln in iss.splitlines()
              if not ln.lstrip().startswith(";")]
    assert not any("DisableDirPage" in ln for ln in active), \
        "destination page must stay enabled"


def _widget_texts(widget):
    out = []
    try:
        out.append(str(widget.cget("text")))
    except Exception:
        pass
    for child in widget.winfo_children():
        out.extend(_widget_texts(child))
    return out


def _dialog_text(win):
    found = []

    def walk(w):
        if isinstance(w, tk.Text):
            found.append(w.get("1.0", "end"))
        for c in w.winfo_children():
            walk(c)
    walk(win)
    return "\n".join(found)


def test_about_tab_exposes_license():
    from src.config.strings import t
    from src.ui.about_tab import AboutTab, show_license_text
    root = tk.Tk()
    root.withdraw()
    try:
        for lang in ("en", "ar"):
            tab = AboutTab(root, SimpleNamespace(lang=lang))
            texts = _widget_texts(tab)
            assert t("about.license_title", lang) in texts, lang
            assert t("about.license_view", lang) in texts, lang
            assert t("about.license_summary", lang) in texts, lang
            win = show_license_text(root, lang)
            body = _dialog_text(win)
            assert EN_NO_SALE in body and AR_NO_SALE in body, lang
            assert TITLE in body, lang
            win.destroy()
            tab.destroy()
    finally:
        root.destroy()


def test_no_mit_claims_remain():
    docs = list(ROOT.glob("*.md"))
    docs += list((ROOT / "installer").glob("*.md"))
    docs += list((ROOT / "installer").glob("*.bat"))
    docs += list((ROOT / "server").glob("*.md"))
    srcs = [p for p in (ROOT / "src").rglob("*.py")
            if "__pycache__" not in p.parts]
    hits = []
    for p in docs + srcs:
        for i, line in enumerate(
                p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if re.search(r"\bMIT\b", line):
                hits.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not hits, hits
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "ANADOCTORFADY Free Use License" in readme
    assert "ترخيص ANADOCTORFADY للاستخدام المجاني" in readme
