"""Round 31 (item 5): the doctor CHOOSES the template language.
Persisted setting template_lang = "app" (default, = round-17
behaviour exactly) | "ar" | "en", resolved by the ONE central
resolver specialty_templates.effective_template_lang(). The choice
applies to EVERY category; EN ALL-CAPS follows the EFFECTIVE
language; single-language customs (one side empty) show as-is in
any mode. GUI tests skip without a display; DB = isolated temp DB."""
import importlib, re, tkinter as tk
from src.models.database import get_connection, get_setting, set_setting
from src.models import specialty_templates as tpl
from src.models.phrases import search_phrases
from src.ui.phrase_picker import combined_templates
from tests.test_templates_edit import isolated_db, tmp_overrides, SEED_EN, SEED_AR
_AR = re.compile(r"[؀-ۿ]")
CATS8 = ("complaint", "symptom", "diagnosis", "procedure",
         "note", "disease", "allergy", "referral")

def _tk():
    try: return tk.Tk()
    except Exception: return None
def _walk(w):
    yield w
    for ch in w.winfo_children(): yield from _walk(ch)
def _set(app_lang, mode):
    set_setting("language", app_lang); set_setting("template_lang", mode)

def test_resolver_modes_default_and_legacy():
    with isolated_db():
        assert tpl.template_lang_mode() == "app"  # default, never written
        _set("en", "app"); assert tpl.effective_template_lang() == "en"
        _set("ar", "app"); assert tpl.effective_template_lang() == "ar"
        _set("en", "ar"); assert tpl.effective_template_lang() == "ar"
        _set("ar", "en"); assert tpl.effective_template_lang() == "en"
        _set("en", "app"); assert tpl.effective_template_lang("ar") == "ar"
        _set("en", "ar"); assert tpl.effective_template_lang("en") == "ar"
        for legacy in ("auto", "", "bogus"):  # legacy/junk -> "app"
            _set("ar", legacy)
            assert tpl.template_lang_mode() == "app", legacy
            assert tpl.effective_template_lang() == "ar", legacy
        _set("en", "ar"); assert tpl.resolve_template_lang() == "ar"  # alias

def test_setting_persists_across_simulated_restart():
    with isolated_db():
        tpl.set_template_lang_mode("ar")
        assert get_setting("template_lang") == "ar"  # in the settings store
        import src.models.specialty_templates as fresh
        importlib.reload(fresh)  # a fresh process re-reads the store
        try:
            assert fresh.template_lang_mode() == "ar"
            assert fresh.effective_template_lang() == "ar"
        finally: importlib.reload(tpl)
        tpl.set_template_lang_mode("app")
        assert get_setting("template_lang") == "app"

def test_every_category_follows_choice_model_level():
    with tmp_overrides(), isolated_db():
        conn = get_connection()
        try:
            for app_lang, mode, eff in (("en", "ar", "ar"), ("ar", "en", "en")):
                _set(app_lang, mode); assert tpl.effective_template_lang() == eff
                for cat in CATS8:
                    rows = search_phrases(cat, "", limit=50, lang=eff)
                    pool = combined_templates(cat, "", lang=eff)
                    assert rows and pool, (cat, eff)
                    if eff == "ar":
                        assert all(_AR.search(r["text"]) for r in rows), cat
                        assert all(_AR.search(r["text"]) for r in pool), cat
                    else:
                        assert all(r["text"] == r["text"].upper() for r in rows), cat
                        assert not any(_AR.search(r["text"]) for r in pool), cat
                        assert all(r["text"] == r["text"].upper() for r in pool), cat
                for cat in ("complaint", "symptom", "diagnosis", "procedure"):
                    rows = tpl.effective_pool(conn, cat)  # no lang: resolver decides
                    assert rows, (cat, eff)
                    if eff == "en":
                        assert all(r["text"] == r["text"].upper() for r in rows), cat
                    elif cat == "complaint":
                        assert any(r["text"] == SEED_AR for r in rows)
            _set("en", "app")  # mode "app" = round-17 expectations exactly
            rows = tpl.effective_pool(conn, "complaint")
            assert any(r["text"] == SEED_EN.upper() for r in rows)
            assert not any(r["text"] == SEED_AR for r in rows)
            _set("ar", "app")
            assert any(r["text"] == SEED_AR for r in tpl.effective_pool(conn, "complaint"))
        finally: conn.close()

def test_single_language_custom_shows_as_is_any_mode():
    # Pairs vs singles: a custom row stores ONE side (the other "");
    # _one() falls back to the stored side, so it shows as-is (no
    # caps transform in ar mode, no dropping in en mode).
    with tmp_overrides(), isolated_db():
        conn = get_connection()
        try:
            assert tpl.add_template(conn, "general", "complaint", "Only English Custom ZQX", "", created_by="fady")
            assert tpl.add_template(conn, "general", "complaint", "", "قالب عربي وحيد ZQX", created_by="fady")
            _set("en", "ar")
            texts = [r["text"] for r in tpl.effective_pool(conn, "complaint")]
            assert "Only English Custom ZQX" in texts  # as-is, NOT capped
            assert "قالب عربي وحيد ZQX" in texts
            _set("ar", "en")
            texts = [r["text"] for r in tpl.effective_pool(conn, "complaint")]
            assert "قالب عربي وحيد ZQX" in texts  # as-is in EN mode too
            assert "ONLY ENGLISH CUSTOM ZQX" in texts  # EN side caps (R18)
        finally: conn.close()

def _picker(root, category, app_lang, mode, lang):
    from src.ui.phrase_picker import open_template_picker
    _set(app_lang, mode)
    txt = tk.Text(root); txt.pack()
    win = open_template_picker(root, category, txt, current_user="fady", lang=lang)
    root.update_idletasks()
    box = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
    return win, box, txt, box.get(0, tk.END)

def test_gui_picker_complaint_arabic_in_en_app():
    root = _tk()
    if root is None: print("SKIP r31 picker GUI (no display)"); return
    root.withdraw()
    try:
        with tmp_overrides(), isolated_db():
            win, box, txt, rows = _picker(root, "complaint", "en", "ar", "en")
            assert rows and all(_AR.search(r) for r in rows), rows[:5]
            assert any(SEED_AR in r for r in rows)
            assert not any(SEED_EN.upper() in r for r in rows)
            box.selection_set(next(i for i, r in enumerate(rows) if SEED_AR in r))
            btn = next(w for w in _walk(win) if isinstance(w, tk.Button)
                       and str(w.cget("text")).startswith("Insert"))
            btn.invoke(); root.update_idletasks()
            inserted = txt.get("1.0", tk.END).strip()
            assert inserted == SEED_AR and _AR.search(inserted), inserted
    finally: root.destroy()

def test_gui_picker_note_en_caps_in_ar_app():
    root = _tk()
    if root is None: print("SKIP r31 note GUI (no display)"); return
    root.withdraw()
    try:
        with tmp_overrides(), isolated_db():
            win, box, txt, rows = _picker(root, "note", "ar", "en", "ar")
            assert rows and not any(_AR.search(r) for r in rows), rows[:5]
            assert all(r == r.upper() for r in rows), rows[:5]
            box.selection_set(0)
            btn = next(w for w in _walk(win) if isinstance(w, tk.Button)
                       and str(w.cget("text")).startswith("إدراج"))
            btn.invoke(); root.update_idletasks()
            inserted = txt.get("1.0", tk.END).strip()
            assert inserted and inserted == inserted.upper(), inserted
            assert not _AR.search(inserted)
    finally: root.destroy()

def test_gui_manager_and_settings_share_the_setting():
    root = _tk()
    if root is None: print("SKIP r31 manager GUI (no display)"); return
    root.withdraw()
    import tkinter.messagebox as mb
    old_info = mb.showinfo; mb.showinfo = lambda *a, **k: None
    try:
        with tmp_overrides(), isolated_db():
            from src.ui.template_manager import open_template_manager
            from src.ui.settings_ui import SettingsTab
            class _App:
                lang = "en"
                def print_pdf(self, bilingual=False): return None
                def _rebuild(self): return None
            _set("en", "app")
            win = open_template_manager(root, "fady", lang="en")
            root.update_idletasks()
            assert win.template_mode_var.get() == "Follow app language"
            win.template_mode_var.set("العربية")  # manager selector persists + relists
            win.template_mode_combo.combo.event_generate("<<ComboboxSelected>>")
            root.update_idletasks()
            assert get_setting("template_lang") == "ar"
            box = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
            rows = box.get(0, tk.END)
            assert rows and all(_AR.search(r) for r in rows), rows[:5]
            win.destroy()
            tab = SettingsTab(root, _App()); root.update_idletasks()
            assert tab.tpl_lang_var.get() == "العربية"  # Settings reflects it
            tab.tpl_lang_var.set("English"); tab.save_tpl_lang()
            assert get_setting("template_lang") == "en"
            tab.destroy()
            win = open_template_manager(root, "fady", lang="en")
            root.update_idletasks()
            assert win.template_mode_var.get() == "English"  # and vice versa
            box = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
            assert SEED_EN.upper() in box.get(0, tk.END)
            win.destroy()
    finally:
        mb.showinfo = old_info; root.destroy()
