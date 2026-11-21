"""Round 18 W1: EN templates/phrases ALL CAPS at display + insert.

The transform (phrases.template_display_text) applies ONLY to the
EN side AFTER single-language selection; AR text and ALL stored
data (seed JSONs, DB rows, auto-learned phrases) keep their case.
Covers every phrase category + the specialty-template pool, the
picker pool (combined_templates = what the picker displays and
inserts) and the template-manager pool (effective_pool)."""
import json
import re
import tkinter as tk
from pathlib import Path

from src.models.database import get_connection, get_setting, set_setting
from src.models.phrases import (CATEGORIES, save_phrase, delete_phrase,
                                search_phrases, single_language_text,
                                template_display_text)
from src.models import specialty_templates as tpl
from src.ui.phrase_picker import combined_templates
from tests.test_templates_edit import isolated_db, tmp_overrides

ROOT = Path(__file__).resolve().parent.parent
_AR_RE = re.compile(r"[؀-ۿ]")
SEED_EN, SEED_AR = "Toothache when chewing", "ألم في السن عند المضغ"


def test_transform_unit_and_purity_helper_unchanged():
    assert template_display_text("Mixed Case Text", "en") == "MIXED CASE TEXT"
    assert template_display_text("نص عربي", "ar") == "نص عربي"
    assert template_display_text("Mixed Case Text", "ar") == "Mixed Case Text"
    assert template_display_text("", "en") == ""
    assert template_display_text(None, "en") == ""
    assert template_display_text("123 / 45%", "en") == "123 / 45%"
    # Round-17 purity helper itself is NOT the caps transform.
    assert single_language_text("Sharp pain / ألم حاد", "en") == "Sharp pain"
    assert single_language_text("Sharp pain / ألم حاد", "ar") == "ألم حاد"
    assert single_language_text("ألم حاد", "en") == ""


def test_phrases_all_categories_en_caps_ar_unchanged():
    for cat in CATEGORIES:
        en = search_phrases(cat, "", limit=50, lang="en")
        assert en, cat
        assert all(r["text"] == r["text"].upper() for r in en), cat
        assert not any(_AR_RE.search(r["text"]) for r in en), cat
        ar = search_phrases(cat, "", limit=50, lang="ar")
        assert ar, cat
        assert all(_AR_RE.search(r["text"]) for r in ar), cat
    # A known seed phrase per language, exact expectations.
    comp_en = search_phrases("complaint", "", limit=50, lang="en")
    assert any(r["text"] == "SHARP TOOTH PAIN WHEN CHEWING"
               for r in comp_en)
    comp_ar = search_phrases("complaint", "", limit=50, lang="ar")
    assert any(r["text"] == "ألم حاد في السن عند المضغ" for r in comp_ar)


def test_stored_phrase_text_not_rewritten():
    pid = save_phrase("note", "Caps Storage Check Zqx Phrase")
    assert pid
    try:
        en = search_phrases("note", "Caps Storage", limit=5, lang="en")
        assert en and en[0]["text"] == "CAPS STORAGE CHECK ZQX PHRASE"
        conn = get_connection()
        try:
            raw = conn.execute("SELECT text FROM reusable_phrases "
                               "WHERE id=?", (pid,)).fetchone()[0]
        finally:
            conn.close()
        assert raw == "Caps Storage Check Zqx Phrase"  # DB keeps case
    finally:
        delete_phrase(pid)


def test_specialty_pool_en_caps_raw_sides_kept():
    with tmp_overrides(), isolated_db():
        conn = get_connection()
        try:
            en = tpl.effective_pool(conn, "complaint", "en")
            assert en and all(r["text"] == r["text"].upper() for r in en)
            hit = [r for r in en if r["text"] == SEED_EN.upper()]
            assert hit and hit[0]["en"] == SEED_EN  # raw side untouched
            ar = tpl.effective_pool(conn, "complaint", "ar")
            assert any(r["text"] == SEED_AR for r in ar)
            raw = conn.execute("SELECT text_en FROM specialty_templates "
                               "WHERE text_en=?", (SEED_EN,)).fetchone()
            assert raw and raw[0] == SEED_EN  # DB seed row not rewritten
            for cat in ("symptom", "diagnosis", "procedure"):
                rows = tpl.effective_pool(conn, cat, "en")
                assert rows and all(r["text"] == r["text"].upper()
                                    for r in rows), cat
            seeds = tpl.seed_templates("complaint", "en")
            assert any(r["text"] == SEED_EN.upper() for r in seeds)
            assert any(r["seed_en"] == SEED_EN for r in seeds)
        finally:
            conn.close()


def test_picker_pool_caps_for_phrases_and_specialties():
    with tmp_overrides(), isolated_db():
        en = combined_templates("complaint", "", lang="en")
        assert en and all(r["text"] == r["text"].upper() for r in en)
        assert all(r["display"] == r["text"] for r in en)
        # Specialty-sourced row (not a reusable phrase seed):
        assert any(r["text"] == SEED_EN.upper() for r in en)
        # Phrase-sourced row:
        assert any(r["text"] == "SHARP TOOTH PAIN WHEN CHEWING"
                   for r in en)
        ar = combined_templates("complaint", "", lang="ar")
        assert any(r["text"] == SEED_AR for r in ar)
        assert any(r["text"] == "ألم حاد في السن عند المضغ" for r in ar)


def test_seed_files_en_stay_normal_case():
    phrases = json.loads((ROOT / "src" / "data" / "phrases_seed.json")
                         .read_text(encoding="utf-8"))
    for cat, items in phrases.items():
        for t in items:
            if t.isascii() and len(t) > 3:
                assert t != t.upper(), (cat, t)  # seeds not caps-rewritten
    spec_raw = (ROOT / "src" / "data" / "specialties.json") \
        .read_text(encoding="utf-8")
    assert SEED_EN in spec_raw and SEED_EN.upper() not in spec_raw


def _tk():
    try:
        return tk.Tk()
    except Exception:
        return None


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def test_template_manager_gui_shows_en_caps():
    root = _tk()
    if root is None:
        print("SKIP manager caps GUI (no display)")
        return
    root.withdraw()
    prev = get_setting("language", "en")
    try:
        with tmp_overrides(), isolated_db():
            from src.ui.template_manager import open_template_manager
            set_setting("language", "en")
            win = open_template_manager(root, "fady", lang="en")
            root.update_idletasks()
            box = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
            rows = box.get(0, tk.END)
            assert rows and not any(_AR_RE.search(r) for r in rows)
            assert all(r == r.upper() for r in rows), rows[:3]
            assert SEED_EN.upper() in rows
            win.destroy()
    finally:
        set_setting("language", prev if prev is not None else "en")
        root.destroy()
