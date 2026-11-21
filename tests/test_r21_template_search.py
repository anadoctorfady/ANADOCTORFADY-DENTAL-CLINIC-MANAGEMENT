"""Round 21 items 14/15 regression: template SEARCH actually filters.
Item 15 root cause: the picker filtered live all along, but the
template MANAGER had no search box at all, and Arabic queries typed
without hamza ("الم" for "ألم") matched nothing - the SQL LIKE
pre-filter and plain substring checks never normalized Arabic.
Pinned here: the shared normalizer (models/phrases.search_text_
matches), Arabic queries bypassing the SQL LIKE pre-filter, the
manager search row (live KeyRelease + Search button) and the picker
Search button. GUI pattern: VISIBLE root (never withdrawn),
focus_force() on the search entry, insert, event_generate
("<KeyRelease>", when="now"), root.update(), then the visible list
must equal the model-level expected matches exactly. DB work runs
on the isolated temp copy (never the live DB)."""
import tkinter as tk
from src.models.database import get_connection, set_setting
from src.models.phrases import (normalize_search_text, search_phrases,
                                search_text_matches)
from src.models import specialty_templates as tpl
from src.ui.phrase_picker import combined_templates
from tests.test_templates_edit import isolated_db, tmp_overrides
def _tk():
    try: return tk.Tk()
    except Exception: return None
def _walk(w):
    yield w
    for ch in w.winfo_children(): yield from _walk(ch)
def _box(win):
    return next(w for w in _walk(win) if isinstance(w, tk.Listbox))
def _entries(win):
    return [w for w in _walk(win) if w.winfo_class() == "Entry"]
def _btn(win, prefix):
    for w in _walk(win):
        if isinstance(w, tk.Button) and str(w.cget("text")).startswith(prefix):
            return w
    return None
def _type_and_fire(entry, root, text):
    entry.focus_force(); root.update()
    entry.insert(0, text)
    entry.event_generate("<KeyRelease>", when="now")
    root.update()
def test_normalizer_unit():
    assert normalize_search_text("ألم") == "الم"
    assert normalize_search_text("إشارة آلام") == "اشاره الام"
    assert search_text_matches("ألم حاد في السن", "الم")       # hamza-less query
    assert search_text_matches("حشوة مؤقتة", "حشوه")          # ة -> ه
    assert search_text_matches("ألمٌ شديد", "الم شديد")        # diacritics stripped
    assert search_text_matches("ألـــم في السن", "الم")        # tatweel stripped
    assert search_text_matches("بنى تحتية", "بني")             # ى -> ي
    assert search_text_matches("سائل لزج", "ساءل")             # ئ -> ء
    assert search_text_matches("PAIN When Chewing", "pain")    # Latin case-insensitive
    assert not search_text_matches("Bleeding gums", "pain")
    assert search_text_matches("anything at all", "")          # empty query matches all
def test_model_combined_templates_en_narrows():
    with tmp_overrides(), isolated_db():
        full = combined_templates("complaint", "", lang="en")
        hits = combined_templates("complaint", "pain", lang="en")
        assert 0 < len(hits) < len(full)
        assert all(search_text_matches(r["text"], "pain") for r in hits)
        assert {r["text"] for r in hits} == \
            {r["text"] for r in full if search_text_matches(r["text"], "pain")}
def test_model_combined_templates_ar_hamzaless():
    with tmp_overrides(), isolated_db():
        full = combined_templates("complaint", "", lang="ar")
        hits = combined_templates("complaint", "الم", lang="ar")
        assert hits and len(hits) < len(full)
        assert all(search_text_matches(r["text"], "الم") for r in hits)
        assert any("ألم" in r["text"] for r in hits)  # hamza text, hamza-less query
        assert {r["text"] for r in hits} == \
            {r["text"] for r in full if search_text_matches(r["text"], "الم")}
        # Reusable-phrase path: SQL LIKE '%الم%' could never match the
        # stored 'ألم...' rows; the Python filter must find them.
        rows = search_phrases("complaint", "الم", limit=50, lang="ar")
        assert rows and all(search_text_matches(r["text"], "الم") for r in rows)
        assert any("ألم" in r["text"] for r in rows)
def test_model_manager_pool_filter_ar():
    # Exactly what the manager's refresh() does with effective_pool.
    with tmp_overrides(), isolated_db():
        conn = get_connection()
        try: pool = tpl.effective_pool(conn, "complaint", "ar")
        finally: conn.close()
        hits = [r for r in pool if search_text_matches(r["text"], "الم")]
        assert hits and len(hits) < len(pool)
        assert all(search_text_matches(r["text"], "الم") for r in hits)
        assert any("ألم" in r["text"] for r in hits)
def test_gui_picker_search_en_and_button():
    root = _tk()
    if root is None:
        print("SKIP test_gui_picker_search_en (no display)"); return
    root.deiconify()
    try:
        with tmp_overrides(), isolated_db():
            set_setting("language", "en")
            from src.ui.phrase_picker import open_template_picker
            txt = tk.Text(root); txt.pack()
            expected = combined_templates("complaint", "pain", lang="en")
            win = open_template_picker(root, "complaint", txt, current_user="fady", lang="en")
            root.update()
            box, entry = _box(win), _entries(win)[0]
            assert box.size() > len(expected)
            _type_and_fire(entry, root, "pain")
            rows = box.get(0, tk.END)
            assert len(rows) == len(expected), (len(rows), len(expected))
            assert all(search_text_matches(r, "pain") for r in rows)
            # Search BUTTON applies the filter without any KeyRelease:
            # retype programmatically (no event), then click Search.
            expected2 = combined_templates("complaint", "gum", lang="en")
            assert expected2
            entry.delete(0, tk.END); entry.insert(0, "gum")
            _btn(win, "Search").invoke(); root.update()
            rows = box.get(0, tk.END)
            assert len(rows) == len(expected2), (len(rows), len(expected2))
            assert all(search_text_matches(r, "gum") for r in rows)
            win.destroy()
    finally:
        root.destroy()
def test_gui_picker_search_ar_hamzaless():
    root = _tk()
    if root is None:
        print("SKIP test_gui_picker_search_ar (no display)"); return
    root.deiconify()
    try:
        with tmp_overrides(), isolated_db():
            set_setting("language", "ar")
            from src.ui.phrase_picker import open_template_picker
            txt = tk.Text(root); txt.pack()
            expected = combined_templates("complaint", "الم", lang="ar")
            assert expected
            win = open_template_picker(root, "complaint", txt, current_user="fady", lang="ar")
            root.update()
            box, entry = _box(win), _entries(win)[0]
            assert box.size() > len(expected)
            _type_and_fire(entry, root, "الم")
            rows = box.get(0, tk.END)
            assert len(rows) == len(expected), (len(rows), len(expected))
            assert all(search_text_matches(r, "الم") for r in rows)
            assert any("ألم" in r for r in rows)
            win.destroy()
    finally:
        root.destroy()
def test_gui_manager_search_en_and_button():
    root = _tk()
    if root is None:
        print("SKIP test_gui_manager_search_en (no display)"); return
    root.deiconify()
    try:
        with tmp_overrides(), isolated_db():
            set_setting("language", "en")
            from src.ui.template_manager import open_template_manager
            conn = get_connection()
            try: pool = tpl.effective_pool(conn, "complaint", "en")
            finally: conn.close()
            expected = [r for r in pool if search_text_matches(r["text"], "pain")]
            assert 0 < len(expected) < len(pool)
            win = open_template_manager(root, "fady", lang="en")
            root.update()
            box = _box(win)
            entries = _entries(win)
            assert len(entries) == 2  # search (first) + edit (last)
            assert box.size() == len(pool)
            _type_and_fire(entries[0], root, "pain")
            rows = box.get(0, tk.END)
            assert len(rows) == len(expected), (len(rows), len(expected))
            assert all(search_text_matches(r, "pain") for r in rows)
            # Search button, no KeyRelease: retype + click.
            expected2 = [r for r in pool if search_text_matches(r["text"], "gum")]
            assert expected2
            entries[0].delete(0, tk.END); entries[0].insert(0, "gum")
            _btn(win, "Search").invoke(); root.update()
            rows = box.get(0, tk.END)
            assert len(rows) == len(expected2), (len(rows), len(expected2))
            assert all(search_text_matches(r, "gum") for r in rows)
            win.destroy()
    finally:
        root.destroy()
def test_gui_manager_search_ar_hamzaless():
    root = _tk()
    if root is None:
        print("SKIP test_gui_manager_search_ar (no display)"); return
    root.deiconify()
    try:
        with tmp_overrides(), isolated_db():
            set_setting("language", "ar")
            from src.ui.template_manager import open_template_manager
            conn = get_connection()
            try: pool = tpl.effective_pool(conn, "complaint", "ar")
            finally: conn.close()
            expected = [r for r in pool if search_text_matches(r["text"], "الم")]
            assert expected and len(expected) < len(pool)
            win = open_template_manager(root, "fady", lang="ar")
            root.update()
            box, entry = _box(win), _entries(win)[0]
            assert box.size() == len(pool)
            _type_and_fire(entry, root, "الم")
            rows = box.get(0, tk.END)
            assert len(rows) == len(expected), (len(rows), len(expected))
            assert all(search_text_matches(r, "الم") for r in rows)
            assert any("ألم" in r for r in rows)
            win.destroy()
    finally:
        root.destroy()
