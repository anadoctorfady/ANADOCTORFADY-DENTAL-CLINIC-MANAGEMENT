"""Round 52 Section F: the About tab speaks ONE language.

Owner's completed About item: "the message should follow the
selected language and not include both languages together."
Before R52 the tab stacked ABOUT_EN and ABOUT_AR (the dedication
in both languages at once). Now only the ACTIVE language's
dedication renders, and every other line already goes through
the i18n strings. Pins:
- EN tab: the English dedication is present, the Arabic one is
  absent, and NO Arabic-script character appears in any text on
  the tab.
- AR tab: the Arabic dedication is present, the English one is
  absent, and no Latin UI text remains once the allowed proper
  nouns are stripped (ANADOCTORFADY is the app name; Telegram is
  the service name; the contact number is digits).
- The license dialog's title + Close button follow the language
  too. Its BODY is the bilingual legal text pinned verbatim to
  the shipped LICENSE file (test_r42_license) -- a document, not
  UI text -- and is deliberately not language-filtered.
- End to end: an App started in Arabic builds an Arabic-only
  About tab; in English, an English-only one.
"""
import re
import tkinter as tk
from types import SimpleNamespace

from tests.test_templates_edit import isolated_db

_ARABIC = re.compile("[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
_LATIN = re.compile(r"[A-Za-z]")
_ALLOWED_LATIN = ("ANADOCTORFADY", "Telegram")


def _texts(widget, acc):
    try:
        txt = widget.cget("text")
    except Exception:
        txt = None
    if txt:
        acc.append(str(txt))
    for ch in widget.winfo_children():
        _texts(ch, acc)
    return acc


def _make_tab(root, lang):
    from src.ui.about_tab import AboutTab
    return AboutTab(root, SimpleNamespace(lang=lang))


def _check_tab(lang):
    from src.config.settings import ABOUT_EN, ABOUT_AR
    root = tk.Tk(); root.withdraw()
    try:
        tab = _make_tab(root, lang)
        root.update()
        texts = _texts(tab, [])
        joined = "\n".join(texts)
        if lang == "en":
            assert ABOUT_EN in texts, texts
            assert ABOUT_AR not in texts
            bad = [x for x in texts if _ARABIC.search(x)]
            assert not bad, f"Arabic text in EN About tab: {bad}"
        else:
            assert ABOUT_AR in texts, texts
            assert ABOUT_EN not in texts
            bad = []
            for x in texts:
                stripped = x
                for ok in _ALLOWED_LATIN:
                    stripped = stripped.replace(ok, "")
                if _LATIN.search(stripped):
                    bad.append(x)
            assert not bad, f"English text in AR About tab: {bad}"
        assert "ANADOCTORFADY" in joined  # the name stays as-is
    finally:
        root.destroy()


def test_about_tab_english_only():
    try:
        probe = tk.Tk(); probe.destroy()
    except Exception:
        print("SKIP test_r52_about_lang GUI (no display)"); return
    with isolated_db():
        _check_tab("en")


def test_about_tab_arabic_only():
    try:
        probe = tk.Tk(); probe.destroy()
    except Exception:
        print("SKIP test_r52_about_lang GUI (no display)"); return
    with isolated_db():
        _check_tab("ar")


def test_license_dialog_chrome_follows_language():
    try:
        probe = tk.Tk(); probe.destroy()
    except Exception:
        print("SKIP test_r52_about_lang GUI (no display)"); return
    from src.config.strings import t
    from src.ui.about_tab import show_license_text
    with isolated_db():
        for lang in ("en", "ar"):
            root = tk.Tk(); root.withdraw()
            try:
                win = show_license_text(root, lang)
                root.update()
                assert win.title() == t("about.license_title", lang)
                btns = _texts(win, [])
                assert t("about.license_close", lang) in btns, btns
                other = "ar" if lang == "en" else "en"
                assert t("about.license_close", other) not in btns
            finally:
                root.destroy()


def test_app_about_tab_matches_startup_language():
    try:
        probe = tk.Tk(); probe.destroy()
    except Exception:
        print("SKIP test_r52_about_lang GUI (no display)"); return
    from src.config.settings import ABOUT_EN, ABOUT_AR
    from src.models.database import set_setting
    from src.ui.shell import App
    with isolated_db():
        for lang, want, ban in (("en", ABOUT_EN, ABOUT_AR),
                                ("ar", ABOUT_AR, ABOUT_EN)):
            set_setting("language", lang)
            app = App()
            try:
                tab = app.about  # lazy build on attribute access
                texts = _texts(tab, [])
                assert want in texts, (lang, texts)
                assert ban not in texts, (lang, texts)
            finally:
                app.destroy()
