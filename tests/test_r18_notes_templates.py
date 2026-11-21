"""Round 18 W1: 'note' phrases - new seeds + idempotent merge-seed.

The baseline DB (and every existing install) already has a seeded
reusable_phrases table, so seed_if_empty() must MERGE the new note
seeds in (INSERT OR IGNORE), not skip them. Owner's example phrase
is stored verbatim, open-ended, once per language. The picker data
path (combined_templates / open_template_picker / attach_picker_button)
must work for category 'note' even though NO specialty templates
exist for 'note'. GUI parts skip gracefully without a display."""
import json
import re
import tkinter as tk
from pathlib import Path

from src.models.database import get_connection, get_setting, set_setting
from src.models.phrases import (search_phrases, seed_if_empty,
                                toggle_favorite, delete_phrase)
from src.ui.phrase_picker import combined_templates
from tests.test_templates_edit import isolated_db, tmp_overrides

ROOT = Path(__file__).resolve().parent.parent
OWNER_AR = "تم إعلام المريض/ة بسوء إنذار السن وأنه من الأفضل"
OWNER_EN = ("The patient was informed of the poor prognosis of the "
            "tooth and that it is better to")
NEW_AR = [OWNER_AR,
          "تم شرح خطة العلاج والاتفاق عليها مع المريض",
          "تم إعطاء المريض تعليمات العناية بعد العلاج",
          "يلزم تحديد موعد للمراجعة",
          "تم تنبيه المريض إلى احتمال حدوث ألم وتورم بعد العملية"]
NEW_EN = [OWNER_EN,
          "Treatment plan explained and agreed with the patient",
          "Post-treatment care instructions were given to the patient",
          "A review appointment is needed",
          "The patient was warned about possible post-operative pain and swelling"]
_AR_RE = re.compile(r"[؀-ۿ]")


def _note_texts_raw():
    conn = get_connection()
    try:
        return [r[0] for r in conn.execute(
            "SELECT text FROM reusable_phrases WHERE category='note'")]
    finally:
        conn.close()


def test_seed_json_has_owner_and_new_notes_normal_case():
    data = json.loads((ROOT / "src" / "data" / "phrases_seed.json")
                      .read_text(encoding="utf-8"))
    notes = data["note"]
    for t in NEW_AR + NEW_EN:
        assert t in notes, t
    # Stored ONCE per language, never an 'EN / AR' pair in one string,
    # and the EN seeds stay in NORMAL case (caps is display-only).
    assert all(" / " not in t for t in notes)
    assert OWNER_EN != OWNER_EN.upper()
    assert not any(t == t.upper() and len(t) > 3 for t in notes
                   if t.isascii())


def test_merge_seed_fills_notes_on_already_seeded_db():
    with isolated_db():
        seed_if_empty()  # first install: full seed
        conn = get_connection()
        try:
            # Simulate an OLD install: table seeded, new notes absent.
            for t in NEW_AR + NEW_EN:
                conn.execute("DELETE FROM reusable_phrases "
                             "WHERE category='note' AND text=?", (t,))
            conn.commit()
            before = conn.execute("SELECT COUNT(*) FROM "
                                  "reusable_phrases").fetchone()[0]
            assert before > 0  # table was NOT empty: merge path, not seed
        finally:
            conn.close()
        seed_if_empty()  # every init/use must merge the missing notes
        texts = _note_texts_raw()
        for t in NEW_AR + NEW_EN:
            assert t in texts, t
        assert OWNER_AR in texts  # owner's exact AR text, verbatim
        n1 = len(_note_texts_raw())
        seed_if_empty(); seed_if_empty()  # idempotent: no duplicates
        assert len(_note_texts_raw()) == n1


def test_note_search_ar_unchanged_en_caps():
    with isolated_db():
        seed_if_empty()
        ar = search_phrases("note", "", limit=50, lang="ar")
        assert ar and all(_AR_RE.search(r["text"]) for r in ar)
        assert any(r["text"] == OWNER_AR for r in ar)  # AR unchanged
        en = search_phrases("note", "", limit=50, lang="en")
        assert en and all(r["text"] == r["text"].upper() for r in en)
        assert any(r["text"] == OWNER_EN.upper() for r in en)
        # Searchable in the picker sense: a query finds the owner phrase.
        hit = search_phrases("note", "prognosis", limit=5, lang="en")
        assert any(r["text"] == OWNER_EN.upper() for r in hit)
        hit_ar = search_phrases("note", "إعلام", limit=5, lang="ar")
        assert any(r["text"] == OWNER_AR for r in hit_ar)


def test_note_favorite_still_works():
    with isolated_db():
        seed_if_empty()
        rows = search_phrases("note", "prognosis", limit=5)  # raw, no lang
        assert rows
        pid = rows[0]["id"]
        toggle_favorite(pid)
        try:
            en = search_phrases("note", "", limit=50, lang="en")
            fav = [r for r in en if r["text"] == OWNER_EN.upper()]
            assert fav and fav[0]["is_favorite"] == 1
            assert en[0]["text"] == OWNER_EN.upper()  # favorites first
        finally:
            toggle_favorite(pid)


def test_combined_templates_note_no_specialty_no_crash():
    # 'note' has NO specialty templates: the picker pool must simply
    # be the reusable phrases, in EN CAPS / AR unchanged, never crash.
    with tmp_overrides(), isolated_db():
        seed_if_empty()
        en = combined_templates("note", "", lang="en")
        assert en and all(r["text"] == r["text"].upper() for r in en)
        assert all(r["display"] == r["text"] for r in en)
        assert any(r["text"] == OWNER_EN.upper() for r in en)
        ar = combined_templates("note", "", lang="ar")
        assert ar and all(_AR_RE.search(r["text"]) for r in ar)
        assert any(r["text"] == OWNER_AR for r in ar)
        q = combined_templates("note", "prognosis", lang="en")
        assert [r["text"] for r in q] == [OWNER_EN.upper()]


def _tk():
    try:
        return tk.Tk()
    except Exception:
        return None


def _walk(w):
    yield w
    for ch in w.winfo_children():
        yield from _walk(ch)


def test_note_picker_gui_via_existing_entry_points():
    root = _tk()
    if root is None:
        print("SKIP note picker GUI (no display)")
        return
    root.withdraw()
    prev = get_setting("language", "en")
    try:
        with tmp_overrides(), isolated_db():
            from src.ui.phrase_picker import (open_template_picker,
                                              attach_picker_button)
            seed_if_empty()
            set_setting("language", "en")
            txt = tk.Text(root); txt.pack()
            # The exact entry point W3 wires for the Notes field.
            btn = attach_picker_button(root, "note", txt,
                                       current_user="fady")
            btn.invoke()
            root.update_idletasks()
            tops = [w for w in root.winfo_children()
                    if isinstance(w, tk.Toplevel)]
            assert tops, "picker did not open for category 'note'"
            box = next(w for w in _walk(tops[-1])
                       if isinstance(w, tk.Listbox))
            rows = box.get(0, tk.END)
            assert rows and all(r == r.upper() for r in rows), rows[:3]
            assert any(OWNER_EN.upper() in r for r in rows)
            idx = next(i for i, r in enumerate(rows)
                       if OWNER_EN.upper() in r)
            box.selection_set(idx)
            ins = next(w for w in _walk(tops[-1])
                       if isinstance(w, tk.Button)
                       and str(w.cget("text")).startswith("Insert"))
            ins.invoke()
            root.update_idletasks()
            assert txt.get("1.0", tk.END).strip() == OWNER_EN.upper()
            tops[-1].destroy()
            # AR: same picker, Arabic text inserted unchanged.
            set_setting("language", "ar")
            txt2 = tk.Text(root); txt2.pack()
            win = open_template_picker(root, "note", txt2,
                                       current_user="fady", lang="ar")
            root.update_idletasks()
            box = next(w for w in _walk(win) if isinstance(w, tk.Listbox))
            rows = box.get(0, tk.END)
            assert rows and all(_AR_RE.search(r) for r in rows), rows[:3]
            assert any(OWNER_AR in r for r in rows)
            win.destroy()
    finally:
        set_setting("language", prev if prev is not None else "en")
        root.destroy()
