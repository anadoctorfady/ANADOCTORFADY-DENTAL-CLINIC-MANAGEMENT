"""Round 19 items 5 + 11 (seed work): 'disease' + 'referral' phrases.
Seeds stored ONCE per language in phrases_seed.json (never an 'EN / AR'
pair, EN normal case -- caps is display-only), merged idempotently into
already-seeded DBs like 'note' (round 18); search/picker return ONE
language only (EN ALL CAPS, AR unchanged). The patient form's Diseases
field gets a Templates button opening the existing picker for 'disease'
and APPENDING the chosen phrase (comma-joined, app language only).
GUI parts skip gracefully without a display."""
import json, re, tkinter as tk
from pathlib import Path
from src.models.database import get_connection, get_setting, set_setting
from src.models.phrases import (CATEGORIES, get_categories, save_phrase,
                                search_phrases, seed_if_empty)
from tests.test_templates_edit import isolated_db
ROOT = Path(__file__).resolve().parent.parent
_AR_RE = re.compile(r"[؀-ۿ]")
DISEASE_EN = ["Pregnancy", "Breastfeeding", "Diabetes", "Hypertension", "Asthma", "Heart disease", "Hepatitis", "Kidney disease", "Thyroid disorder", "Epilepsy", "Bleeding disorder", "Osteoporosis", "Rheumatoid arthritis", "Anaemia", "Liver disease", "Peptic ulcer", "Sinusitis"]
DISEASE_AR = ["الحمل", "الإرضاع", "داء السكري", "ارتفاع ضغط الدم", "الربو", "أمراض القلب", "التهاب الكبد", "أمراض الكلى", "اضطراب الغدة الدرقية", "الصرع", "اضطرابات النزف", "هشاشة العظام", "التهاب المفاصل الروماتويدي", "فقر الدم", "أمراض الكبد", "القرحة الهضمية", "التهاب الجيوب"]
REFERRAL_EN = ["Referral for orthodontic evaluation", "Referral for implant consultation", "Referral for endodontic treatment", "Referral for oral surgery assessment", "Referral for periodontal treatment", "Referral for prosthodontic treatment", "Referred to another doctor to continue treatment"]
REFERRAL_AR = ["تحويل لتقييم تقويم الأسنان", "تحويل لاستشارة زراعة الأسنان", "تحويل لعلاج العصب", "تحويل لتقييم جراحة الفم", "تحويل لعلاج اللثة", "تحويل لعلاج التعويضات السنية", "تحويل إلى طبيب آخر لاستكمال العلاج"]
OWNER_REFERRAL_AR = "تحويل إلى طبيب آخر لاستكمال العلاج"

def _seed_json():
    return json.loads((ROOT / "src" / "data" / "phrases_seed.json").read_text(encoding="utf-8"))

def test_seed_json_disease_and_referral_bilingual():
    data = _seed_json()
    for cat, en_list, ar_list in (("disease", DISEASE_EN, DISEASE_AR), ("referral", REFERRAL_EN, REFERRAL_AR)):
        items = data[cat]
        assert len(items) == len(en_list) + len(ar_list), cat
        for t in en_list + ar_list:
            assert t in items, (cat, t)
        assert all(" / " not in t for t in items), cat
        assert not any(t == t.upper() and len(t) > 3 for t in items if t.isascii()), cat  # EN stored normal case
    assert not any("penicillin" in t.lower() for t in data["disease"])  # allergy, NOT a disease

def test_categories_registered_and_saveable():
    assert "disease" in CATEGORIES and "referral" in CATEGORIES
    assert "disease" in get_categories() and "referral" in get_categories()
    with isolated_db():
        seed_if_empty()
        assert save_phrase("disease", "TEST_R19_DISEASE_XYZ") is not None
        assert save_phrase("referral", "TEST_R19_REFERRAL_XYZ") is not None

def test_merge_seed_fills_new_categories_on_seeded_db():
    with isolated_db():
        seed_if_empty()
        conn = get_connection()
        try:
            conn.execute("DELETE FROM reusable_phrases WHERE category IN ('disease','referral')"); conn.commit()
            assert conn.execute("SELECT COUNT(*) FROM reusable_phrases").fetchone()[0] > 0  # merge path
        finally:
            conn.close()
        seed_if_empty()
        conn = get_connection()
        try:
            texts = {r[0] for r in conn.execute("SELECT text FROM reusable_phrases WHERE category='disease'")}
            refs = {r[0] for r in conn.execute("SELECT text FROM reusable_phrases WHERE category='referral'")}
        finally:
            conn.close()
        for t in DISEASE_EN + DISEASE_AR:
            assert t in texts, t
        for t in REFERRAL_EN + REFERRAL_AR:
            assert t in refs, t
        n1 = len(texts) + len(refs)
        seed_if_empty(); seed_if_empty()  # idempotent: no duplicates
        conn = get_connection()
        try:
            n2 = conn.execute("SELECT COUNT(*) FROM reusable_phrases WHERE category IN ('disease','referral')").fetchone()[0]
        finally:
            conn.close()
        assert n2 == n1

def test_search_language_purity_and_caps():
    with isolated_db():
        seed_if_empty()
        en = search_phrases("disease", "", limit=50, lang="en")
        assert en and all(r["text"] == r["text"].upper() for r in en) and not any(_AR_RE.search(r["text"]) for r in en)
        assert any(r["text"] == "PREGNANCY" for r in en) and any(r["text"] == "DIABETES" for r in en)
        ar = search_phrases("disease", "", limit=50, lang="ar")
        assert ar and all(_AR_RE.search(r["text"]) for r in ar)
        assert any(r["text"] == "الحمل" for r in ar) and any(r["text"] == "داء السكري" for r in ar)
        ren = search_phrases("referral", "", limit=50, lang="en")
        assert ren and all(r["text"] == r["text"].upper() for r in ren)
        assert any(r["text"] == "REFERRED TO ANOTHER DOCTOR TO CONTINUE TREATMENT" for r in ren)
        rar = search_phrases("referral", "", limit=50, lang="ar")
        assert rar and all(_AR_RE.search(r["text"]) for r in rar) and any(r["text"] == OWNER_REFERRAL_AR for r in rar)

def _tk():
    try:
        return tk.Tk()
    except Exception:
        return None

def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)

class _Stub:
    def __init__(self, lang):
        self.lang = lang; self.current_patient = None
    def on_teeth_select(self, *a): pass
    def print_pdf(self, *a): pass
    def load_patients(self): pass
    def select_patient(self, *a): pass

def _make_form(root, lang):
    from src.ui.patient_form import PatientForm
    return PatientForm(root, _Stub(lang))

def test_diseases_button_present_in_form():
    root = _tk()
    if root is None:
        print("SKIP diseases button GUI (no display)"); return
    root.withdraw()
    from src.config.settings import get_theme_mode, set_theme_mode
    prev = get_theme_mode(); set_theme_mode("light")
    try:
        with isolated_db():
            form = _make_form(root, "en")
            assert hasattr(form, "btn_diseases_templates")
            btn = form.btn_diseases_templates
            assert str(btn.cget("text")) == "📋 Templates", btn.cget("text")
            assert btn.winfo_manager() == "grid" and btn.diseases_entry is form.e_diseases
            form_ar = _make_form(root, "ar")
            assert str(form_ar.btn_diseases_templates.cget("text")) == "📋 قوالب"
    finally:
        try: root.destroy()
        except Exception: pass
        set_theme_mode(prev)

def test_picker_insert_appends_en_then_ar():
    root = _tk()
    if root is None:
        print("SKIP disease picker GUI (no display)"); return
    root.withdraw()
    from src.config.settings import get_theme_mode, set_theme_mode
    from src.ui.patient_diseases import open_disease_picker
    prev_lang = get_setting("language", "en"); prev = get_theme_mode(); set_theme_mode("light")
    try:
        with isolated_db():
            seed_if_empty()
            set_setting("language", "en")
            form = _make_form(root, "en"); form.e_diseases.insert(0, "Existing note")
            win = open_disease_picker(form, form.e_diseases, "en"); root.update_idletasks()
            box = next(w for w in _walk(win) if isinstance(w, tk.Listbox)); rows = list(box.get(0, tk.END))
            assert rows and not any(_AR_RE.search(r) for r in rows), rows[:4]
            box.selection_set(next(i for i, r in enumerate(rows) if "PREGNANCY" in r))
            next(w for w in _walk(win) if isinstance(w, tk.Button) and str(w.cget("text")).startswith("Insert")).invoke()
            root.update_idletasks(); got = form.e_diseases.get()
            assert got == "Existing note, PREGNANCY", got
            assert not _AR_RE.search(got)
            set_setting("language", "ar")
            form_ar = _make_form(root, "ar"); form_ar.e_diseases.insert(0, "ملاحظة سابقة")
            win = open_disease_picker(form_ar, form_ar.e_diseases, "ar"); root.update_idletasks()
            box = next(w for w in _walk(win) if isinstance(w, tk.Listbox)); rows = list(box.get(0, tk.END))
            assert rows and all(_AR_RE.search(r) for r in rows), rows[:4]
            box.selection_set(next(i for i, r in enumerate(rows) if "الحمل" in r))
            next(w for w in _walk(win) if isinstance(w, tk.Button) and str(w.cget("text")).startswith("إدراج")).invoke()
            root.update_idletasks(); got = form_ar.e_diseases.get()
            assert got == "ملاحظة سابقة, الحمل", got
    finally:
        try: set_setting("language", prev_lang or "en")
        except Exception: pass
        try: root.destroy()
        except Exception: pass
        set_theme_mode(prev)
