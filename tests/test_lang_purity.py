"""Language purity (round 16, owner rule): the app shows 100% of the
user's chosen language - no words/letters from the other language
anywhere in the UI.

Static scan over the merged strings (src/config/strings.py) plus
every strings_r16_*.py module: EN values must contain no Arabic
script; AR values must contain no Latin words outside the data
allowlist. Honest limits, kept by design: patient DATA (names),
the literal "PDF", currency codes, technical acronyms (CBCT/STL),
file extensions (.bak/.db), API paths (POST /users/...), usernames
(fady), date-format tokens (YYYY-MM-DD) and {placeholders} - none of
those is UI wording. The language-switcher button ("عربي / EN") is
the one intentional exception: it names both languages so the user
can find it in either mode.
"""
import importlib
import re
from pathlib import Path

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_R16_MODULES = ("strings_r16_clinical", "strings_r16_patients",
                "strings_r16_print", "strings_r16_rx",
                "strings_r16_settings")
# Latin tokens that are data, not wording.
_ALLOWED = re.compile(
    r"^(pdf|cbct|stl|ply|obj|sqlite|whatsapp|fady|post|get|api|ui|id|"
    r"in|out|rx|sql|bak|db|am|pm|2d|3d|en|ar|http|https|www|com|"
    r"anadoctorfady)$", re.I)  # + the app brand name (round 42)


def _all_strings():
    from src.config.strings import AR, EN
    en, ar = dict(EN), dict(AR)
    for name in _R16_MODULES:
        mod = importlib.import_module(f"src.config.{name}")
        en.update(mod.EN)
        ar.update(mod.AR)
    return en, ar


def _latin_words_outside_data(value):
    """Latin words in an AR value that are not placeholders, URLs,
    API paths, file extensions or other data tokens."""
    s = re.sub(r"\{[^}]*\}", " ", value)
    s = re.sub(r"https?://\S+|[\w./-]*\.(?:bak|db|sql)\b|"
               r"/(?:users|auth)/\S*", " ", s)
    words = re.findall(r"[A-Za-z]+(?:[._+-][A-Za-z0-9]+)*", s)
    bad = []
    for w in words:
        if _ALLOWED.match(w):
            continue
        if re.fullmatch(r"[A-Z]{2,4}", w):  # acronym / currency code
            continue
        if re.fullmatch(r"(?:YYYY|MM|DD|YYYY-MM|YYYY-MM-DD)", w):
            continue
        if re.fullmatch(r"\d+", w):
            continue
        bad.append(w)
    return bad


def test_en_values_contain_no_arabic():
    en, _ar = _all_strings()
    bad = {k: v for k, v in en.items()
           if isinstance(v, str) and _ARABIC_RE.search(v)}
    assert not bad, "EN values with Arabic:\n" + "\n".join(
        f"{k}: {v!r}" for k, v in sorted(bad.items()))


def test_ar_values_contain_no_english_words():
    _en, ar = _all_strings()
    bad = {}
    for k, v in ar.items():
        if not isinstance(v, str):
            continue
        words = _latin_words_outside_data(v)
        if words:
            bad[k] = (words, v)
    assert not bad, "AR values with English words:\n" + "\n".join(
        f"{k}: {w} :: {v!r}" for k, (w, v) in sorted(bad.items()))


def test_en_and_ar_values_differ():
    """Every key that carries wording actually translates (no key left
    showing the other language's text by accident). Pure format
    strings (placeholders/symbols only, e.g. '≈ {amt} {base} @ {rate}')
    and brand/data values ('💬 WhatsApp {number}') are exempt: they
    contain no wording in either language."""
    en, ar = _all_strings()
    assert set(en) == set(ar)
    same = []
    for k in en:
        if en[k] != ar[k]:
            continue
        # Strip placeholders: letters that only live inside {…} are
        # format, not wording (e.g. '≈ {amt} {base} @ {rate}').
        stripped = re.sub(r"\{[^}]*\}", "", en[k])
        if _ARABIC_RE.search(stripped):
            same.append(k)
        elif _latin_words_outside_data(stripped):
            same.append(k)
    assert not same, f"identical EN/AR values: {same}"


def _display_available():
    try:
        import tkinter as tk
        r = tk.Tk(); r.withdraw(); r.destroy()
        return True
    except Exception:
        return False


def _chrome_texts(app):
    """Notebook tab labels + tree headings + button texts (chrome only,
    never patient data values)."""
    out = []

    def walk(w):
        try:
            if w.winfo_class() == "TNotebook":
                for i in range(w.index("end")):
                    out.append(w.tab(i, "text"))
            if w.winfo_class() == "Treeview":
                for c in w["columns"]:
                    out.append(w.heading(c, "text") or "")
            if w.winfo_class() == "Button":
                out.append(str(w.cget("text") or ""))
        except Exception:
            pass
        for ch in w.winfo_children():
            walk(ch)

    walk(app)
    return out


def test_live_chrome_single_language():
    """GUI test under xvfb: the shell chrome in EN shows no Arabic
    (except the intentional عربي / EN switcher); in AR it shows no
    English words (same data allowlist)."""
    if not _display_available():
        return  # no display: skip GUI check
    from tkinter import messagebox
    from src.config.settings import get_setting, set_setting
    from src.ui.shell import App
    orig = get_setting("language", "en") or "en"
    set_setting("language", "en")
    app = App()
    messagebox.showinfo = lambda *a, **k: None
    try:
        texts = [t for t in _chrome_texts(app)
                 if t.strip() and t.strip() != "عربي / EN"]
        bad = [t for t in texts if _ARABIC_RE.search(t)]
        assert not bad, f"Arabic in EN chrome: {bad}"
        app._toggle_lang()
        assert app.lang == "ar"
        texts = [t for t in _chrome_texts(app)
                 if t.strip() and t.strip() != "عربي / EN"]
        bad = [(t, _latin_words_outside_data(t)) for t in texts
               if _latin_words_outside_data(t)]
        assert not bad, f"English in AR chrome: {bad}"
    finally:
        set_setting("language", orig)
        try:
            app.destroy()
        except Exception:
            pass


# --- Round 17: the app language is the ONLY language anywhere. ---
def test_template_insert_single_language_both_langs():
    from src.models.database import get_connection, get_setting, set_setting
    from src.models import specialty_templates as tpl
    from src.models.phrases import save_phrase, delete_phrase
    from src.ui.phrase_picker import combined_templates
    from tests.test_templates_edit import isolated_db, tmp_overrides
    prev = get_setting("language", "en")
    with tmp_overrides(), isolated_db():
        conn = get_connection()
        assert tpl.add_template(conn, "general", "complaint", "Bilingual pain ZQX / ألم ثنائي", "ألم ثنائي / Bilingual pain ZQX", created_by="fady"); conn.close()
        pid = save_phrase("complaint", "Sharp pain ZQX / ألم حاد"); assert pid
        for lang in ("en", "ar"):
            set_setting("language", lang); assert tpl.resolve_template_lang() == lang
            texts = [r["text"] for r in combined_templates("complaint", "", lang=lang)]; assert texts
            if lang == "en":
                assert not any(_ARABIC_RE.search(x) for x in texts) and "TOOTHACHE WHEN CHEWING" in texts and "BILINGUAL PAIN ZQX" in texts and "SHARP PAIN ZQX" in texts  # round 18: EN inserts are ALL CAPS
            else:
                assert not [x for x in texts if _latin_words_outside_data(x)] and "ألم في السن عند المضغ" in texts and "ألم ثنائي" in texts and "ألم حاد" in texts
        delete_phrase(pid); set_setting("language", prev or "en")
def test_currency_display_single_language_and_legacy_parse():
    from src.utils.currencies import display_for_code, code_for
    assert display_for_code("SYP", "en") == "SYP - Syrian Pound" and display_for_code("SYP", "ar") == "SYP - ليرة سورية"
    assert not _ARABIC_RE.search(display_for_code("USD", "en")) and not re.search(r"[A-Za-z]{3,}", display_for_code("USD", "ar").split(" - ", 1)[1])
    assert code_for("SYP - Syrian Pound / ليرة سورية") == "SYP" and code_for("USD - US Dollar / دولار أمريكي") == "USD"  # legacy bilingual
    assert code_for(display_for_code("USD", "en")) == "USD" and code_for(display_for_code("USD", "ar")) == "USD"
    assert code_for("US Dollar") == "USD" and code_for("دولار أمريكي") == "USD"
def test_appointment_status_translated_at_display():
    from src.models.appointments import translate_status  # storage stays 'قادم'
    assert translate_status("قادم", "en") == "Upcoming" and translate_status("قادم", "ar") == "قادم"
    assert translate_status("Upcoming", "ar") == "قادم" and translate_status("ملغي", "en") == "Cancelled" and translate_status("تم", "en") == "Completed"
