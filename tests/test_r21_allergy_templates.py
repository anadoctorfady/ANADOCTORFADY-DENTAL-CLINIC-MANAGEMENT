"""Round 21 (item 12): 'allergy' phrase templates for the patient
form's Allergies field -- the round-19 diseases treatment applied
to allergies. Seeds stored ONCE per language in phrases_seed.json
(EN normal case; caps is display-only), merged idempotently into
already-seeded DBs like 'disease'; search/picker return ONE
language only (EN ALL CAPS). The form's Allergies field gets a
Templates button opening the picker for 'allergy' and APPENDING
the chosen phrase (comma-joined, app language only).
GUI parts skip gracefully without a display."""
import json, re, tkinter as tk
from pathlib import Path
from src.models.database import get_connection, get_setting, set_setting
from src.models.phrases import (CATEGORIES, get_categories, save_phrase,
                                search_phrases, seed_if_empty)
from tests.test_templates_edit import isolated_db
ROOT = Path(__file__).resolve().parent.parent
_AR_RE = re.compile(r"[؀-ۿ]")
ALLERGY_EN = ["Penicillin allergy", "Cephalosporin allergy", "NSAID allergy",
              "Aspirin allergy", "Local anaesthetic allergy", "Sulfa drug allergy",
              "Latex allergy", "Tetracycline allergy", "Macrolide allergy",
              "Opioid allergy", "Iodine allergy", "No known drug allergy"]
ALLERGY_AR = ["حساسية للبنسلين", "حساسية للسيفالوسبورينات",
              "حساسية لمضادات الالتهاب غير الستيرويدية", "حساسية للأسبرين",
              "حساسية للمخدرات الموضعية", "حساسية لأدوية السلفا",
              "حساسية للاتكس", "حساسية للتتراسيكلين", "حساسية للماكروليدات",
              "حساسية للأدوية الأفيونية", "حساسية لليود",
              "لا توجد حساسية معروفة للأدوية"]


def _seed_json():
    return json.loads((ROOT / "src" / "data" / "phrases_seed.json").read_text(encoding="utf-8"))


def test_seed_json_allergy_bilingual():
    items = _seed_json()["allergy"]
    assert len(items) == len(ALLERGY_EN) + len(ALLERGY_AR)
    for t in ALLERGY_EN + ALLERGY_AR:
        assert t in items, t
    assert all(" / " not in t for t in items)
    assert not any(t == t.upper() and len(t) > 3 for t in items if t.isascii())


def test_category_registered_and_merge_seeded():
    assert "allergy" in CATEGORIES and "allergy" in get_categories()
    with isolated_db():
        seed_if_empty()
        assert save_phrase("allergy", "TEST_R21_ALLERGY_XYZ") is not None
        conn = get_connection()
        try:
            conn.execute("DELETE FROM reusable_phrases WHERE category='allergy'")
            conn.commit()
            assert conn.execute("SELECT COUNT(*) FROM reusable_phrases").fetchone()[0] > 0
        finally:
            conn.close()
        seed_if_empty()  # merge path refills the category
        conn = get_connection()
        try:
            texts = {r[0] for r in conn.execute(
                "SELECT text FROM reusable_phrases WHERE category='allergy'")}
        finally:
            conn.close()
        for t in ALLERGY_EN + ALLERGY_AR:
            assert t in texts, t
        n1 = len(texts)
        seed_if_empty(); seed_if_empty()  # idempotent
        conn = get_connection()
        try:
            n2 = conn.execute("SELECT COUNT(*) FROM reusable_phrases WHERE category='allergy'").fetchone()[0]
        finally:
            conn.close()
        assert n2 == n1


def test_search_language_purity_and_caps():
    with isolated_db():
        seed_if_empty()
        en = search_phrases("allergy", "", limit=50, lang="en")
        assert en and all(r["text"] == r["text"].upper() for r in en)
        assert not any(_AR_RE.search(r["text"]) for r in en)
        assert any(r["text"] == "PENICILLIN ALLERGY" for r in en)
        assert any(r["text"] == "NO KNOWN DRUG ALLERGY" for r in en)
        ar = search_phrases("allergy", "", limit=50, lang="ar")
        assert ar and all(_AR_RE.search(r["text"]) for r in ar)
        assert any(r["text"] == "حساسية للبنسلين" for r in ar)


class _Stub:
    def __init__(self, lang):
        self.lang = lang; self.current_patient = None
    def on_teeth_select(self, *a): pass
    def print_pdf(self, *a): pass
    def load_patients(self): pass
    def select_patient(self, *a): pass


def _tk():
    try:
        return tk.Tk()
    except Exception:
        return None


def test_allergy_button_present_in_form():
    root = _tk()
    if root is None:
        print("SKIP allergy button GUI (no display)"); return
    root.withdraw()
    from src.config.settings import get_theme_mode, set_theme_mode
    from src.ui.patient_form import PatientForm
    prev = get_theme_mode(); set_theme_mode("light")
    try:
        with isolated_db():
            form = PatientForm(root, _Stub("en"))
            assert hasattr(form, "btn_allergy_templates")
            btn = form.btn_allergy_templates
            assert str(btn.cget("text")) == "📋 Templates", btn.cget("text")
            assert btn.winfo_manager() == "grid" and btn.allergy_entry is form.e_allergies
            form_ar = PatientForm(root, _Stub("ar"))
            assert str(form_ar.btn_allergy_templates.cget("text")) == "📋 قوالب"
    finally:
        try: root.destroy()
        except Exception: pass
        set_theme_mode(prev)


def test_allergy_picker_appends():
    root = _tk()
    if root is None:
        print("SKIP allergy picker GUI (no display)"); return
    root.deiconify(); root.geometry("900x700")
    from src.config.settings import get_theme_mode, set_theme_mode
    from src.ui.patient_allergies import append_phrase, open_allergy_picker
    from src.ui.rounded_widgets import RoundedEntry
    prev = get_theme_mode(); set_theme_mode("light")
    try:
        with isolated_db():
            seed_if_empty()
            set_setting("language", "en")
            entry = RoundedEntry(root); entry.pack()
            entry.insert(0, "Existing")
            append_phrase(entry, "PENICILLIN ALLERGY")
            assert entry.get() == "Existing, PENICILLIN ALLERGY", entry.get()
            win = open_allergy_picker(root, entry, lang="en")
            root.update()
            assert win is not None and win.winfo_viewable()
            win.destroy()
    finally:
        try: root.destroy()
        except Exception: pass
        set_theme_mode(prev)
        set_setting("language", "en")
