"""Round 15 (2026-11-10): templates background = app main colour +
right-click menu (Edit / Delete / Add new) on the manager. Picker rows
carry no per-item identity (deduped display list), so the menu lives
in the manager only. GUI tests skip gracefully with no display."""
import contextlib
import tkinter as tk
import tkinter.messagebox as mb
from src.config.theme import current
from src.models.database import set_setting
from tests.test_templates_edit import (isolated_db, tmp_overrides,
    SEED_EN, _md5, SEED_FILE)
def _tk():
    try: return tk.Tk()
    except Exception: return None
@contextlib.contextmanager
def _root():
    root = _tk()
    if root is None:
        print("SKIP test_templates_r15 (no display)")
        yield None
        return
    root.withdraw()
    try: yield root
    finally: root.destroy()
@contextlib.contextmanager
def _mocked_mb(warnings=None):
    old_warn, old_yes = mb.showwarning, mb.askyesno
    mb.showwarning = lambda *a, **k: (warnings.append(a) if warnings is not None else None)
    mb.askyesno = lambda *a, **k: True
    try: yield
    finally: mb.showwarning, mb.askyesno = old_warn, old_yes
def _walk(w):
    yield w
    for ch in w.winfo_children(): yield from _walk(ch)
def _btn(win, prefix):
    for w in _walk(win):
        if isinstance(w, tk.Button) and str(w.cget("text")).startswith(prefix):
            return w
def _listbox(win):
    return next(w for w in _walk(win) if isinstance(w, tk.Listbox))
def _entry(win):
    # Round 21: manager has a SEARCH entry too, so EDIT = LAST Entry.
    return [w for w in _walk(win) if w.winfo_class() == "Entry"][-1]
def _lum(h):
    r, g, b = (int(h[i:i+2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
def _contrast(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)
def _assert_main_bg(win, need_entry=True):
    # Window + list (+ entry) on the app MAIN colour, no pure white
    # anywhere in the dialog, text contrast >= 4.5:1.
    th = current()
    assert win.cget("bg").lower() == th["bg"].lower()
    assert _listbox(win).cget("bg").lower() == th["bg"].lower()
    if need_entry:
        assert _entry(win).cget("bg").lower() == th["bg"].lower()
    for w in _walk(win):
        try: bg = w.cget("bg")
        except Exception: bg = ""
        assert not (isinstance(bg, str) and bg.lower() == "#ffffff"), type(w).__name__
    assert _contrast(th["text"], th["bg"]) >= 4.5
    assert _contrast(th["muted"], th["bg"]) >= 4.5
def _menu_idx(menu, prefix):
    for i in range(menu.index("end") + 1):
        if menu.type(i) == "command" and menu.entrycget(i, "label").startswith(prefix):
            return i
    raise AssertionError("no menu entry %r" % prefix)
def _menu_labels(menu):
    return [menu.entrycget(i, "label") for i in range(menu.index("end") + 1) if menu.type(i) == "command"]
def _rightclick_row(box, root, idx):
    root.update_idletasks()
    box.see(idx)
    root.update_idletasks()
    bb = box.bbox(idx)
    box.event_generate("<Button-3>", x=bb[0] + 2, y=bb[1] + bb[3] // 2)
    root.update_idletasks()
def _mgr(root, lang="en"):
    from src.ui.template_manager import open_template_manager
    win = open_template_manager(root, "fady", lang=lang)
    root.update_idletasks()
    return win
def test_manager_bg_main_colour_light_and_dark():
    with _root() as root:
        if root is None: return
        with tmp_overrides(), isolated_db():
            win = _mgr(root)
            _assert_main_bg(win)
            assert _listbox(win).size() > 40
            win.destroy()
            set_setting("theme_mode", "dark")
            win = _mgr(root)
            _assert_main_bg(win)
            win.destroy()
            set_setting("theme_mode", "light")
def test_picker_bg_main_colour_no_menu():
    with _root() as root:
        if root is None: return
        with tmp_overrides(), isolated_db():
            from src.ui.phrase_picker import open_template_picker, show_clipboard_panel
            txt = tk.Text(root); txt.pack()
            win = open_template_picker(root, "complaint", txt, current_user="fady", lang="en")
            root.update_idletasks()
            _assert_main_bg(win)
            assert not hasattr(win, "_r15_ctx_menu")
            win.destroy()
            win = show_clipboard_panel(root)
            root.update_idletasks()
            _assert_main_bg(win, need_entry=False)
            win.destroy()
def test_r15_strings_bilingual():
    from src.config.strings_r15_templates import EN, AR
    assert set(EN) == set(AR) and EN
    assert all(v.strip() and AR[k].strip() and AR[k] != v for k, v in EN.items())
def test_manager_ctx_menu_edit():
    before = _md5(SEED_FILE)
    with _root() as root:
        if root is None: return
        with _mocked_mb(), tmp_overrides(), isolated_db():
            win = _mgr(root)
            box, entry, menu = _listbox(win), _entry(win), win._r15_ctx_menu
            assert _menu_labels(menu) == ["Edit", "Delete", "Add new"]
            idx = next(i for i in range(box.size()) if box.get(i) == SEED_EN.upper())
            _rightclick_row(box, root, idx)
            assert box.curselection() == (idx,)
            win.focus_force(); root.update_idletasks()
            menu.invoke(_menu_idx(menu, "Edit"))
            root.update_idletasks()
            assert entry.get() == SEED_EN
            assert root.focus_get() == entry
            entry.delete(0, tk.END)
            entry.insert(0, "TEST_R15_CTX_EDIT_XYZ")
            _btn(win, "Edit").invoke()
            root.update_idletasks()
            assert "✎ TEST_R15_CTX_EDIT_XYZ" in box.get(0, tk.END)
            assert SEED_EN not in box.get(0, tk.END)
            assert _md5(SEED_FILE) == before  # seed edit is an override, never in place
            win.destroy()
            win = _mgr(root, lang="ar")
            assert _menu_labels(win._r15_ctx_menu) == ["تعديل", "حذف", "إضافة جديدة"]
            win.destroy()
def test_manager_ctx_menu_delete():
    before = _md5(SEED_FILE)
    with _root() as root:
        if root is None: return
        with _mocked_mb(), tmp_overrides(), isolated_db():
            win = _mgr(root)
            box, entry, menu = _listbox(win), _entry(win), win._r15_ctx_menu
            entry.delete(0, tk.END)
            entry.insert(0, "TEST_R15_CTX_DEL_XYZ")
            _btn(win, "Add").invoke()
            root.update_idletasks()
            assert "TEST_R15_CTX_DEL_XYZ" in box.get(0, tk.END)
            idx = next(i for i in range(box.size()) if box.get(i) == "TEST_R15_CTX_DEL_XYZ")
            _rightclick_row(box, root, idx)
            menu.invoke(_menu_idx(menu, "Delete"))
            root.update_idletasks()
            assert "TEST_R15_CTX_DEL_XYZ" not in box.get(0, tk.END)
            idx = next(i for i in range(box.size()) if box.get(i) == SEED_EN.upper())
            _rightclick_row(box, root, idx)
            menu.invoke(_menu_idx(menu, "Delete"))
            root.update_idletasks()
            assert SEED_EN not in box.get(0, tk.END)
            # Round 21 supersedes hiding: no Show-hidden checkbox, no
            # [hidden] rows - Restore built-ins revives the seed.
            assert not [w for w in _walk(win) if type(w).__name__ == "Checkbutton"]
            assert not any(r.startswith("[hidden]") for r in box.get(0, tk.END))
            _btn(win, "Restore built-in").invoke()
            root.update_idletasks()
            assert SEED_EN.upper() in box.get(0, tk.END)
            assert _md5(SEED_FILE) == before
            win.destroy()
def test_manager_ctx_menu_no_selection():
    warnings = []
    with _root() as root:
        if root is None: return
        with _mocked_mb(warnings), tmp_overrides(), isolated_db():
            win = _mgr(root)
            box, entry, menu = _listbox(win), _entry(win), win._r15_ctx_menu
            box.selection_clear(0, tk.END)
            n = box.size()
            menu.invoke(_menu_idx(menu, "Edit"))
            root.update_idletasks()
            assert warnings, "Edit with no selection must warn, not crash"
            assert box.size() == n
            menu.invoke(_menu_idx(menu, "Delete"))
            assert len(warnings) == 2
            assert box.size() == n
            win.focus_force(); root.update_idletasks()
            menu.invoke(_menu_idx(menu, "Add new"))
            assert entry.get() == ""
            assert root.focus_get() == entry
            entry.insert(0, "TEST_R15_CTX_ADD_XYZ")
            _btn(win, "Add").invoke()
            root.update_idletasks()
            assert "TEST_R15_CTX_ADD_XYZ" in box.get(0, tk.END)
            win.destroy()
