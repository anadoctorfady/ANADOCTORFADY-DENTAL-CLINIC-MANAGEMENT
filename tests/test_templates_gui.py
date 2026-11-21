"""Job 2 (2026-11-09): editable, single-language templates (GUI).
Template manager: edit a seed (override), delete it (round 21:
tombstone, no hiding / no Show hidden), restore the category's
built-ins, add + delete a custom template — all to completion, with
and without a row selected. Picker: single-language rows, insert into
the field. Settings tab: template-language combobox saves the setting.
GUI tests skip gracefully when no display is available."""
import tkinter as tk
from src.models.database import get_setting, set_setting
from tests.test_templates_edit import (isolated_db, tmp_overrides,
    SEED_EN, SEED_AR, _md5, SEED_FILE)

def _tk():
    try: return tk.Tk()
    except Exception: return None
def _walk(w):
    yield w
    for ch in w.winfo_children(): yield from _walk(ch)
def _btn(win, prefix):
    for w in _walk(win):
        if isinstance(w, tk.Button) and str(w.cget("text")).startswith(prefix):
            return w
    return None

def test_manager_gui_edit_delete_restore():
    # Round 21 supersedes the old hide spec: Delete tombstones a seed
    # (no Show hidden checkbox, no [hidden] marks) and the category
    # level "Restore built-in templates" button brings back the
    # ORIGINAL seed text (edit override cleared too).
    root = _tk()
    if root is None:
        print("SKIP test_manager_gui (no display)")
        return
    root.withdraw()
    before = _md5(SEED_FILE)
    import tkinter.messagebox as mb
    old_yes, old_warn, old_info = mb.askyesno, mb.showwarning, mb.showinfo
    mb.askyesno = lambda *a, **k: True
    mb.showwarning = lambda *a, **k: None
    mb.showinfo = lambda *a, **k: None
    try:
        with tmp_overrides(), isolated_db():
            from src.ui.template_manager import open_template_manager
            win = open_template_manager(root, "fady", lang="en")
            root.update_idletasks()
            box = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
            # winfo_class, not isinstance(tk.Entry): ttk.Combobox IS a
            # tk.Entry subclass. Round 21 added a SEARCH entry above
            # the list, so the EDIT entry is the LAST Entry now.
            entries = [w for w in _walk(win) if w.winfo_class() == "Entry"]
            assert len(entries) == 2  # search + edit
            entry = entries[-1]
            assert box.size() > 40
            # No hiding UI anywhere: no checkbutton at all.
            assert not [w for w in _walk(win) if type(w).__name__ == "Checkbutton"]
            # No selection: edit/delete only warn, never crash.
            for prefix in ("Edit", "Delete"):
                _btn(win, prefix).invoke()
                root.update_idletasks()
            assert box.size() > 40
            # Edit a seed: override stored, seed file untouched.
            idx = next(i for i in range(box.size()) if box.get(i) == SEED_EN.upper())
            box.selection_set(idx)
            box.event_generate("<<ListboxSelect>>")
            root.update_idletasks()
            assert entry.get() == SEED_EN
            entry.delete(0, tk.END)
            entry.insert(0, "TEST_GUI_EDIT_XYZ")
            _btn(win, "Edit").invoke()
            root.update_idletasks()
            assert "✎ TEST_GUI_EDIT_XYZ" in box.get(0, tk.END)
            assert SEED_EN not in box.get(0, tk.END)
            assert _md5(SEED_FILE) == before
            # Delete on a seed tombstones it: gone, with no way to
            # "show" it - only Restore built-ins brings it back.
            idx = next(i for i in range(box.size()) if box.get(i) == "✎ TEST_GUI_EDIT_XYZ")
            box.selection_set(idx)
            _btn(win, "Delete").invoke()
            root.update_idletasks()
            assert not any("TEST_GUI_EDIT_XYZ" in r for r in box.get(0, tk.END))
            assert not any(r.startswith("[hidden]") for r in box.get(0, tk.END))
            _btn(win, "Restore built-in").invoke()
            root.update_idletasks()
            assert SEED_EN.upper() in box.get(0, tk.END)
            assert not any("TEST_GUI_EDIT_XYZ" in r for r in box.get(0, tk.END))
            # Custom add + delete outright.
            entry.delete(0, tk.END)
            entry.insert(0, "TEST_GUI_CUSTOM_XYZ")
            _btn(win, "Add").invoke()
            root.update_idletasks()
            assert "TEST_GUI_CUSTOM_XYZ" in box.get(0, tk.END)
            idx = next(i for i in range(box.size()) if box.get(i) == "TEST_GUI_CUSTOM_XYZ")
            box.selection_set(idx)
            _btn(win, "Delete").invoke()
            root.update_idletasks()
            assert "TEST_GUI_CUSTOM_XYZ" not in box.get(0, tk.END)
            win.destroy()
    finally:
        mb.askyesno, mb.showwarning, mb.showinfo = old_yes, old_warn, old_info
        root.destroy()

def test_picker_gui_single_language_insert():
    root = _tk()
    if root is None:
        print("SKIP test_picker_gui (no display)")
        return
    root.withdraw()
    try:
        with tmp_overrides(), isolated_db():
            from src.ui.phrase_picker import open_template_picker
            # Round 31 item 5: mode "app" (default) = the round-17
            # behaviour (picker follows the APP language, en here);
            # mode "ar" makes the same picker show Arabic only.
            set_setting("language", "en")
            set_setting("template_lang", "app")
            txt = tk.Text(root)
            txt.pack()
            win = open_template_picker(root, "complaint", txt, current_user="fady", lang="en")
            root.update_idletasks()
            box = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
            rows = box.get(0, tk.END)
            assert rows and all(" — " not in r for r in rows)
            assert any(SEED_EN.upper() in r for r in rows)
            assert not any(SEED_AR in r for r in rows)
            box.selection_set(0)
            _btn(win, "Insert").invoke()
            root.update_idletasks()
            assert txt.get("1.0", tk.END).strip() != ""
            assert not win.winfo_exists()
            set_setting("template_lang", "ar")
            win = open_template_picker(root, "complaint", txt, current_user="fady", lang="en")
            root.update_idletasks()
            box = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
            rows = box.get(0, tk.END)
            assert any(SEED_AR in r for r in rows)
            assert not any(SEED_EN.upper() in r for r in rows)
            win.destroy()
            set_setting("template_lang", "app")
    finally:
        root.destroy()

def test_settings_template_lang_gui():
    root = _tk()
    if root is None:
        print("SKIP test_settings_gui (no display)")
        return
    root.withdraw()
    import tkinter.messagebox as mb
    old_info = mb.showinfo
    mb.showinfo = lambda *a, **k: None
    try:
        with isolated_db():
            from src.ui.settings_ui import SettingsTab
            class _App:
                lang = "en"
                def print_pdf(self, bilingual=False): return None
                def _rebuild(self): return None
            tab = SettingsTab(root, _App())
            root.update_idletasks()
            assert hasattr(tab, "tpl_lang_var")
            tab.tpl_lang_var.set("العربية")
            tab.save_tpl_lang()
            assert get_setting("template_lang") == "ar"
            tab.tpl_lang_var.set("English")
            tab.save_tpl_lang()
            assert get_setting("template_lang") == "en"
            tab.destroy()
    finally:
        mb.showinfo = old_info
        root.destroy()
