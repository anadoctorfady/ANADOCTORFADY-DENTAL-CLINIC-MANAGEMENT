"""Round 17 (worker W4), updated round 31 (item 5): templates follow
the doctor's template_lang CHOICE (app|ar|en, default app = the
round-17 behaviour); picker/manager show + insert ONE language only
(the effective one); Settings row = three-way selector; appointment
status renders translated, storage 'قادم'. GUI skips w/o display."""
import re
import tkinter as tk

from src.models.database import get_setting, set_setting
from tests.test_templates_edit import isolated_db, tmp_overrides, SEED_EN, SEED_AR

_AR = re.compile(r"[؀-ۿ]")

def _tk():
    try:
        return tk.Tk()
    except Exception:
        return None

def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)

def _restore_lang(prev):
    set_setting("language", prev if prev is not None else "en"); set_setting("template_lang", "app")

def test_resolve_follows_template_lang_choice_r31():
    prev = get_setting("language", "en")
    try:
        from src.models import specialty_templates as tpl
        for app_lang, cases in (("en", (("ar", "ar"), ("en", "en"), ("app", "en"), ("auto", "en"), ("", "en"), ("bogus", "en"))),
                                ("ar", (("en", "en"), ("ar", "ar"), ("app", "ar"), ("auto", "ar")))):
            set_setting("language", app_lang)
            for mode, want in cases:
                set_setting("template_lang", mode); assert tpl.resolve_template_lang() == want, mode
    finally:
        _restore_lang(prev)

def test_picker_gui_inserts_chosen_language_only():
    root = _tk()
    if root is None:
        print("SKIP picker GUI (no display)")
        return
    root.withdraw()
    prev = get_setting("language", "en")
    try:
        with tmp_overrides(), isolated_db():
            from src.ui.phrase_picker import open_template_picker
            # EN app + template_lang=ar (R31 choice): Arabic only.
            set_setting("language", "en")
            set_setting("template_lang", "ar")
            txt = tk.Text(root)
            txt.pack()
            win = open_template_picker(root, "complaint", txt,
                                       current_user="fady", lang="en")
            root.update_idletasks()
            box = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
            rows = box.get(0, tk.END)
            assert rows and all(_AR.search(r) for r in rows), rows[:5]
            assert any(SEED_AR in r for r in rows)
            assert not any(SEED_EN.upper() in r for r in rows)
            box.selection_set(0)
            btn = next(w for w in _walk(win)
                       if isinstance(w, tk.Button)
                       and str(w.cget("text")).startswith("Insert"))
            btn.invoke()
            root.update_idletasks()
            inserted = txt.get("1.0", tk.END).strip()
            assert inserted and _AR.search(inserted), inserted
            # AR app + template_lang=en: English only, ALL CAPS (R18).
            set_setting("language", "ar")
            set_setting("template_lang", "en")
            txt2 = tk.Text(root)
            txt2.pack()
            win = open_template_picker(root, "complaint", txt2,
                                       current_user="fady", lang="ar")
            root.update_idletasks()
            box = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
            rows = box.get(0, tk.END)
            assert rows and not any(_AR.search(r) for r in rows), rows[:5]
            assert any(SEED_EN.upper() in r for r in rows)
            assert all(r == r.upper() for r in rows), rows[:5]
            win.destroy()
    finally:
        _restore_lang(prev)
        root.destroy()

def test_manager_gui_shows_chosen_language_only():
    root = _tk()
    if root is None:
        print("SKIP manager GUI (no display)")
        return
    root.withdraw()
    prev = get_setting("language", "en")
    try:
        with tmp_overrides(), isolated_db():
            from src.ui.template_manager import open_template_manager
            set_setting("language", "en")
            set_setting("template_lang", "ar")  # R31: the choice wins
            win = open_template_manager(root, "fady", lang="en")
            root.update_idletasks()
            box = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
            rows = box.get(0, tk.END)
            assert rows and all(_AR.search(r) for r in rows), rows[:5]
            assert SEED_AR in rows
            win.destroy()
    finally:
        _restore_lang(prev)
        root.destroy()

def test_appointments_gui_status_translated_storage_unchanged():
    root = _tk()
    if root is None:
        print("SKIP appointments GUI (no display)")
        return
    root.withdraw()
    try:
        with isolated_db():
            from src.models.database import get_connection, init_db
            from src.ui.appointments import AppointmentsTab
            init_db()
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO patients(first_name,full_name,"
                        "birth_date_greg,nationality) VALUES(?,?,?,?)",
                        ("Stat", "Stat Test Patient", "1990-01-01", "Syrian"))
            fid = cur.lastrowid
            cur.execute("INSERT INTO appointments(patient_file,"
                        "appointment_date,appointment_time,reason,status,"
                        "created_at) VALUES(?,?,?,?,?,?)",
                        (fid, "2026-11-15", "10:00", "Check", "قادم",
                         "2026-11-12T10:00:00"))
            conn.commit()
            conn.close()
            for lang, want in (("en", "Upcoming"), ("ar", "قادم")):
                stub = type("Stub", (), {"lang": lang,
                                         "current_patient": None})()
                tab = AppointmentsTab(root, stub)
                tab.pack(fill="both", expand=True)
                root.update_idletasks()
                vals = [tab.tree.item(i, "values") for i in
                        tab.tree.get_children()]
                mine = [v for v in vals if str(v[0]) == str(fid)]
                assert mine, (lang, vals)
                assert mine[0][5] == want, (lang, mine)
                tab.destroy()
            # Storage was never rewritten by displaying it.
            conn = get_connection()
            row = conn.execute("SELECT status FROM appointments WHERE "
                               "patient_file=?", (fid,)).fetchone()
            conn.close()
            assert row[0] == "قادم"
    finally:
        root.destroy()

def test_settings_templates_row_is_three_way_selector_r31():
    root = _tk()
    if root is None:
        print("SKIP settings GUI (no display)")
        return
    root.withdraw()
    prev = get_setting("language", "en")
    import tkinter.messagebox as mb
    old_info = mb.showinfo
    mb.showinfo = lambda *a, **k: None
    try:
        with isolated_db():
            from src.config.strings import t as _t
            from src.models import specialty_templates as tpl
            from src.ui.settings_ui import SettingsTab

            class _App:
                lang = "en"
                def print_pdf(self, bilingual=False): return None
                def _rebuild(self): return None

            set_setting("language", "en")
            set_setting("template_lang", "app")
            tab = SettingsTab(root, _App())
            root.update_idletasks()
            # Default: the "app" option, labelled in the app language.
            assert tab.tpl_lang_var.get() == _t("tpl_lang_auto", "en")
            combos = [w for w in _walk(tab)
                      if w.winfo_class() == "TCombobox"
                      and str(w.cget("textvariable")) == str(tab.tpl_lang_var)]
            assert combos and str(combos[0].cget("state")) == "readonly"
            vals = str(combos[0].cget("values"))
            assert "English" in vals and "العربية" in vals, vals
            # Saving العربية persists "ar" and resolution follows it.
            tab.tpl_lang_var.set("العربية")
            tab.save_tpl_lang()
            assert get_setting("template_lang") == "ar"
            assert tpl.resolve_template_lang() == "ar"
            tab.destroy()
    finally:
        mb.showinfo = old_info
        _restore_lang(prev)
        root.destroy()
